import os
import json
import requests
import time
import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv

load_dotenv()

# Configure Cloudinary if credentials exist
CLOUDINARY_CLOUD_NAME = os.environ.get("CLOUDINARY_CLOUD_NAME")
CLOUDINARY_API_KEY = os.environ.get("CLOUDINARY_API_KEY")
CLOUDINARY_API_SECRET = os.environ.get("CLOUDINARY_API_SECRET")

if CLOUDINARY_CLOUD_NAME and CLOUDINARY_API_KEY and CLOUDINARY_API_SECRET:
    cloudinary.config(
        cloud_name=CLOUDINARY_CLOUD_NAME,
        api_key=CLOUDINARY_API_KEY,
        api_secret=CLOUDINARY_API_SECRET,
        secure=True
    )

def instagram_post(details):
    """
    Post an image and description to Instagram Feed & Story using the Instagram Graph API.
    Supports local images by uploading them to Cloudinary first if configured.
    """
    print(f"[Instagram] Initializing campaign broadcast...")
    try:
        instagram_access_token = os.environ.get("INSTAGRAM_ACCESS_TOKEN")
        instagram_user_id = os.environ.get("INSTAGRAM_USER_ID")
        
        if not instagram_access_token or not instagram_user_id:
            raise ValueError("Instagram credentials missing from .env")

        # Proactive check for common token error (Basic Display vs Graph API)
        if instagram_access_token.startswith("IGAAT"):
            print("[Instagram] WARNING: Detected an Instagram Basic Display token (starts with IGAAT).")
            print("[Instagram] WARNING: Content publishing requires a Facebook Graph API token.")

        asset_path = details.get('image', '')
        if not asset_path:
            raise ValueError("No image provided in event details")

        image_url = asset_path

        # If it's a local file, we MUST upload it to a public URL for Instagram to see it
        if os.path.exists(asset_path):
            if CLOUDINARY_CLOUD_NAME:
                print(f"[Instagram] Local file detected: {asset_path}. Uploading to Cloudinary...")
                upload_result = cloudinary.uploader.upload(asset_path)
                image_url = upload_result.get("secure_url")
                print(f"[Instagram] Successfully uploaded to Cloudinary: {image_url}")
            else:
                print(f"[Instagram] WARNING: Local file detected but Cloudinary is not configured.")
                print(f"[Instagram] WARNING: Instagram API requires a publicly accessible URL.")
                # We'll try to use the path anyway to let the API return the specific error if it fails
                image_url = os.path.abspath(asset_path)

        # Step 1: Upload the image for feed post
        print(f"[Instagram] [Feed] Uploading media: {os.path.basename(asset_path)}")
        image_upload_url = f"https://graph.facebook.com/v22.0/{instagram_user_id}/media"
        image_payload = {
            "image_url": image_url,
            "caption": f"{details.get('event_name', 'Event')}\n\n{details.get('description', '')}",
            "access_token": instagram_access_token
        }
        image_response = requests.post(image_upload_url, data=image_payload)
        image_response_data = image_response.json()

        if "id" not in image_response_data:
            error_msg = image_response_data.get("error", {}).get("message", "Unknown error")
            if "Invalid OAuth access token" in error_msg:
                error_msg += " (Ensure you are using a Facebook Graph API token, not a Basic Display token)"
            raise RuntimeError(f"Feed upload error: {error_msg}\nFull Response: {image_response_data}")

        creation_id = image_response_data["id"]

        # Step 2: Publish the uploaded image to Feed (with retry for processing delay)
        print(f"[Instagram] [Feed] Waiting 60s for initial media processing...")
        time.sleep(60)
        print(f"[Instagram] [Feed] Publishing post...")
        publish_url = f"https://graph.facebook.com/v22.0/{instagram_user_id}/media_publish"
        publish_payload = {
            "creation_id": creation_id,
            "access_token": instagram_access_token
        }
        
        retries = 5
        while retries > 0:
            publish_response = requests.post(publish_url, data=publish_payload)
            publish_response_data = publish_response.json()

            if "id" in publish_response_data:
                print("[Instagram] Feed post successful!")
                break
            
            error_code = publish_response_data.get("error", {}).get("code")
            if error_code == 9007:
                print(f"[Instagram] [Feed] Media still not ready. Retrying in 15s... ({retries} retries left)")
                time.sleep(15)
                retries -= 1
            else:
                raise RuntimeError(f"Feed publish error: {publish_response_data}")
        else:
            raise RuntimeError(f"Feed publish timed out: Media was never ready for {creation_id}")

        # Step 3: Upload the image for Story
        print(f"[Instagram] [Story] Uploading media...")
        story_payload = {
            "image_url": image_url,
            "access_token": instagram_access_token
        }
        story_response = requests.post(image_upload_url, data=story_payload)
        story_response_data = story_response.json()

        if "id" not in story_response_data:
            raise RuntimeError(f"Story upload error: {story_response_data}")

        story_creation_id = story_response_data["id"]

        # Step 4: Publish the uploaded image as a Story (with retry for processing delay)
        print(f"[Instagram] [Story] Waiting 60s for initial media processing...")
        time.sleep(60)
        print(f"[Instagram] [Story] Launching story...")
        story_publish_payload = {
            "creation_id": story_creation_id,
            "is_story": "true",
            "access_token": instagram_access_token
        }
        
        retries = 5
        while retries > 0:
            story_publish_response = requests.post(publish_url, data=story_publish_payload)
            story_publish_response_data = story_publish_response.json()

            if "id" in story_publish_response_data:
                print("[Instagram] Story published successfully!")
                break
            
            error_code = story_publish_response_data.get("error", {}).get("code")
            if error_code == 9007:
                print(f"[Instagram] [Story] Media still not ready. Retrying in 15s... ({retries} retries left)")
                time.sleep(15)
                retries -= 1
            else:
                raise RuntimeError(f"Story publish error: {story_publish_response_data}")
        else:
            raise RuntimeError(f"Story publish timed out: Media was never ready for {story_creation_id}")

    except Exception as e:
        print(f"[Instagram] ERROR: {e}")
        raise e
