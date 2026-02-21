import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

def instagram_post(details):
    """
    Post an image and description to Instagram Feed & Story using the Instagram Graph API.
    """
    try:
        instagram_access_token = os.environ.get("INSTAGRAM_ACCESS_TOKEN")
        instagram_user_id = os.environ.get("INSTAGRAM_USER_ID")

        # Step 1: Upload the image for feed post
        image_upload_url = f"https://graph.facebook.com/v22.0/{instagram_user_id}/media"
        image_payload = {
            "image_url": f"{os.path.abspath(details['image'])}",
            "caption": details['event_name'] + "\n" + details['description'],
            "access_token": instagram_access_token
        }
        image_response = requests.post(image_upload_url, data=image_payload)
        image_response_data = image_response.json()

        if "id" not in image_response_data:
            print(f"Error uploading image to Instagram: {image_response_data}")
            return

        creation_id = image_response_data["id"]

        # Step 2: Publish the uploaded image to Feed
        publish_url = f"https://graph.facebook.com/v22.0/{instagram_user_id}/media_publish"
        publish_payload = {
            "creation_id": creation_id,
            "access_token": instagram_access_token
        }
        publish_response = requests.post(publish_url, data=publish_payload)
        publish_response_data = publish_response.json()

        if "id" not in publish_response_data:
            print(f"Error publishing post on Instagram: {publish_response_data}")
            return

        print("Post successfully published on Instagram Feed!")

        # Step 3: Upload the image for Story
        story_payload = {
            "image_url": f"{os.path.abspath(details['image'])}",
            "access_token": instagram_access_token
        }
        story_response = requests.post(image_upload_url, data=story_payload)
        story_response_data = story_response.json()

        if "id" not in story_response_data:
            print(f"Error uploading image to Instagram Story: {story_response_data}")
            return

        story_creation_id = story_response_data["id"]

        # Step 4: Publish the uploaded image as a Story
        story_publish_payload = {
            "creation_id": story_creation_id,
            "is_story": "true",  # Mark it as a story
            "access_token": instagram_access_token
        }
        story_publish_response = requests.post(publish_url, data=story_publish_payload)
        story_publish_response_data = story_publish_response.json()

        if "id" not in story_publish_response_data:
            print(f"Error publishing story on Instagram: {story_publish_response_data}")
            return

        print("Story successfully published on Instagram!")

    except Exception as e:
        print(f"An error occurred while posting to Instagram: {e}")
