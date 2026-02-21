import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

def instagram_post(details):
    """
    Post an image and description to Instagram Feed & Story using the Instagram Graph API.
    """
    print(f"[Instagram] Initializing campaign broadcast...")
    try:
        instagram_access_token = os.environ.get("INSTAGRAM_ACCESS_TOKEN")
        instagram_user_id = os.environ.get("INSTAGRAM_USER_ID")
        
        if not instagram_access_token or not instagram_user_id:
            raise ValueError("Instagram credentials missing from .env")

        asset_path = details.get('image', '')
        if not os.path.exists(asset_path):
            raise FileNotFoundError(f"Image asset not found: {asset_path}")

        # Step 1: Upload the image for feed post
        print(f"[Instagram] [Feed] Uploading media: {os.path.basename(asset_path)}")
        image_upload_url = f"https://graph.facebook.com/v22.0/{instagram_user_id}/media"
        image_payload = {
            "image_url": f"{os.path.abspath(asset_path)}",
            "caption": f"{details['event_name']}\n\n{details['description']}",
            "access_token": instagram_access_token
        }
        image_response = requests.post(image_upload_url, data=image_payload)
        image_response_data = image_response.json()

        if "id" not in image_response_data:
            raise RuntimeError(f"Feed upload error: {image_response_data}")

        creation_id = image_response_data["id"]

        # Step 2: Publish the uploaded image to Feed
        print(f"[Instagram] [Feed] Publishing post...")
        publish_url = f"https://graph.facebook.com/v22.0/{instagram_user_id}/media_publish"
        publish_payload = {
            "creation_id": creation_id,
            "access_token": instagram_access_token
        }
        publish_response = requests.post(publish_url, data=publish_payload)
        publish_response_data = publish_response.json()

        if "id" not in publish_response_data:
            raise RuntimeError(f"Feed publish error: {publish_response_data}")

        print("[Instagram] Feed post successful!")

        # Step 3: Upload the image for Story
        print(f"[Instagram] [Story] Uploading media...")
        story_payload = {
            "image_url": f"{os.path.abspath(asset_path)}",
            "access_token": instagram_access_token
        }
        story_response = requests.post(image_upload_url, data=story_payload)
        story_response_data = story_response.json()

        if "id" not in story_response_data:
            raise RuntimeError(f"Story upload error: {story_response_data}")

        story_creation_id = story_response_data["id"]

        # Step 4: Publish the uploaded image as a Story
        print(f"[Instagram] [Story] Launching story...")
        story_publish_payload = {
            "creation_id": story_creation_id,
            "is_story": "true",
            "access_token": instagram_access_token
        }
        story_publish_response = requests.post(publish_url, data=story_publish_payload)
        story_publish_response_data = story_publish_response.json()

        if "id" not in story_publish_response_data:
            raise RuntimeError(f"Story publish error: {story_publish_response_data}")

        print("[Instagram] Story published successfully!")

    except Exception as e:
        print(f"[Instagram] ERROR: {e}")
        raise e
