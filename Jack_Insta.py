import os
import asyncio
import logging

import requests
import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("sawed-off.instagram")

# Configure Cloudinary if credentials exist
CLOUDINARY_CLOUD_NAME = os.environ.get("CLOUDINARY_CLOUD_NAME")
CLOUDINARY_API_KEY = os.environ.get("CLOUDINARY_API_KEY")
CLOUDINARY_API_SECRET = os.environ.get("CLOUDINARY_API_SECRET")

if CLOUDINARY_CLOUD_NAME and CLOUDINARY_API_KEY and CLOUDINARY_API_SECRET:
    cloudinary.config(
        cloud_name=CLOUDINARY_CLOUD_NAME,
        api_key=CLOUDINARY_API_KEY,
        api_secret=CLOUDINARY_API_SECRET,
        secure=True,
    )


async def _post(url, data):
    """Run a blocking requests.post in a thread to avoid blocking the event loop."""
    return await asyncio.to_thread(requests.post, url, data=data)


async def _upload_and_publish(instagram_user_id, instagram_access_token, image_url, label, payload_extra=None):
    """Upload media to Instagram and publish it with retry logic."""
    upload_url = f"https://graph.facebook.com/v22.0/{instagram_user_id}/media"
    publish_url = f"https://graph.facebook.com/v22.0/{instagram_user_id}/media_publish"

    upload_payload = {
        "image_url": image_url,
        "access_token": instagram_access_token,
    }
    if payload_extra:
        upload_payload.update(payload_extra)

    logger.info("[Instagram] [%s] Uploading media...", label)
    response = await _post(upload_url, upload_payload)
    response_data = response.json()

    if "id" not in response_data:
        error_msg = response_data.get("error", {}).get("message", "Unknown error")
        if "Invalid OAuth access token" in error_msg:
            error_msg += " (Ensure you are using a Facebook Graph API token, not a Basic Display token)"
        raise RuntimeError(f"{label} upload error: {error_msg}\nFull Response: {response_data}")

    creation_id = response_data["id"]

    logger.info("[Instagram] [%s] Waiting 60s for media processing...", label)
    await asyncio.sleep(60)

    logger.info("[Instagram] [%s] Publishing post...", label)
    publish_payload = {
        "creation_id": creation_id,
        "access_token": instagram_access_token,
    }
    if payload_extra and "is_story" in payload_extra:
        publish_payload["is_story"] = "true"

    retries = 5
    while retries > 0:
        pub_response = await _post(publish_url, publish_payload)
        pub_data = pub_response.json()

        if "id" in pub_data:
            logger.info("[Instagram] %s published successfully!", label)
            return pub_data["id"]

        error_code = pub_data.get("error", {}).get("code")
        if error_code == 9007:
            logger.info(
                "[Instagram] [%s] Media still not ready. Retrying in 15s... (%d retries left)",
                label, retries,
            )
            await asyncio.sleep(15)
            retries -= 1
        else:
            raise RuntimeError(f"{label} publish error: {pub_data}")

    raise RuntimeError(f"{label} publish timed out: Media was never ready for {creation_id}")


async def instagram_post(details):
    """Post an image to Instagram Feed & Story using the Instagram Graph API."""
    logger.info("[Instagram] Initializing campaign broadcast...")
    try:
        instagram_access_token = os.environ.get("INSTAGRAM_ACCESS_TOKEN")
        instagram_user_id = os.environ.get("INSTAGRAM_USER_ID")

        if not instagram_access_token or not instagram_user_id:
            raise ValueError("Instagram credentials missing from .env")

        if instagram_access_token.startswith("IGAAT"):
            logger.warning(
                "[Instagram] WARNING: Detected an Instagram Basic Display token (starts with IGAAT)."
            )
            logger.warning(
                "[Instagram] WARNING: Content publishing requires a Facebook Graph API token."
            )

        asset_path = details.get("image", "")
        if not asset_path:
            raise ValueError("No image provided in event details")

        image_url = asset_path

        # If local file, upload to Cloudinary for a public URL
        if os.path.exists(asset_path):
            if CLOUDINARY_CLOUD_NAME:
                logger.info("[Instagram] Local file detected: %s. Uploading to Cloudinary...", asset_path)
                upload_result = await asyncio.to_thread(cloudinary.uploader.upload, asset_path)
                image_url = upload_result.get("secure_url")
                logger.info("[Instagram] Successfully uploaded to Cloudinary: %s", image_url)
            else:
                logger.warning("[Instagram] Local file detected but Cloudinary is not configured.")
                logger.warning("[Instagram] Instagram API requires a publicly accessible URL.")
                image_url = os.path.abspath(asset_path)

        caption = f"{details.get('event_name', 'Event')}\n\n{details.get('description', '')}"

        # Post to Feed
        await _upload_and_publish(
            instagram_user_id,
            instagram_access_token,
            image_url,
            "Feed",
            payload_extra={"caption": caption},
        )

        # Post to Story
        await _upload_and_publish(
            instagram_user_id,
            instagram_access_token,
            image_url,
            "Story",
            payload_extra={"is_story": "true"},
        )

    except Exception as e:
        logger.error("[Instagram] ERROR: %s", e)
        raise
