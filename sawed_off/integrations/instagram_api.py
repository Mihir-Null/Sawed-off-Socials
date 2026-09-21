"""Instagram: publish the event image as a feed post and as a story.

Instagram's content publishing API works in two steps: create a *media
container* from a public image URL, then *publish* it.  Processing is
asynchronous, so we poll the container's ``status_code`` instead of sleeping
a fixed 60 seconds - most images are ready in a few seconds.

Local files are first uploaded to Cloudinary, because Instagram fetches the
image itself and needs a public URL.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

import requests

from ..config import env
from ..models import EventDetails

log = logging.getLogger(__name__)

GRAPH_API = "https://graph.facebook.com/v22.0"
HTTP_TIMEOUT = 30
CONTAINER_TIMEOUT_SECONDS = 300
POLL_INTERVAL_SECONDS = 5
MAX_CAPTION = 2200


def _cloudinary_configured() -> bool:
    return all(env(k) for k in ("CLOUDINARY_CLOUD_NAME", "CLOUDINARY_API_KEY", "CLOUDINARY_API_SECRET"))


def preflight(details: EventDetails) -> list[str]:
    problems: list[str] = []
    if not env("INSTAGRAM_ACCESS_TOKEN") or not env("INSTAGRAM_USER_ID"):
        problems.append("INSTAGRAM_ACCESS_TOKEN / INSTAGRAM_USER_ID are not set in .env")
    if details.image and not details.image.startswith(("http://", "https://")):
        if not Path(details.image).is_file():
            problems.append(f"Image file not found: {details.image}")
        elif not _cloudinary_configured():
            problems.append(
                "Instagram needs a public image URL. Set the CLOUDINARY_* variables in .env "
                "so local images can be uploaded, or use an https:// image URL."
            )
    return problems


class GraphApiError(RuntimeError):
    def __init__(self, action: str, payload: Any) -> None:
        err = payload.get("error", {}) if isinstance(payload, dict) else {}
        message = err.get("message") or str(payload)
        hint = ""
        if "OAuth" in message or err.get("code") == 190:
            hint = " (Is INSTAGRAM_ACCESS_TOKEN a Facebook Graph API token with instagram_content_publish, and not expired?)"
        super().__init__(f"Instagram {action} failed: {message}{hint}")
        self.code = err.get("code")
        self.payload = payload


def _graph(method: str, path: str, **params: Any) -> dict[str, Any]:
    params["access_token"] = env("INSTAGRAM_ACCESS_TOKEN")
    url = f"{GRAPH_API}/{path}"
    try:
        if method == "GET":
            response = requests.get(url, params=params, timeout=HTTP_TIMEOUT)
        else:
            response = requests.post(url, data=params, timeout=HTTP_TIMEOUT)
    except requests.RequestException as exc:
        raise RuntimeError(f"Could not reach the Instagram API: {exc}") from exc
    try:
        data = response.json()
    except ValueError:
        raise RuntimeError(f"Instagram API returned non-JSON (HTTP {response.status_code})") from None
    return data


def _public_image_url(image: str) -> str:
    if image.startswith(("http://", "https://")):
        return image
    path = Path(image)
    if not path.is_file():
        raise FileNotFoundError(f"Image file not found: {image}")
    if not _cloudinary_configured():
        raise ValueError("Cloudinary is not configured; cannot give Instagram a public image URL.")
    import cloudinary
    import cloudinary.uploader

    cloudinary.config(
        cloud_name=env("CLOUDINARY_CLOUD_NAME"),
        api_key=env("CLOUDINARY_API_KEY"),
        api_secret=env("CLOUDINARY_API_SECRET"),
        secure=True,
    )
    log.info("[Instagram] Uploading %s to Cloudinary...", path.name)
    result = cloudinary.uploader.upload(str(path), folder="sawed-off-socials")
    url = result.get("secure_url")
    if not url:
        raise RuntimeError(f"Cloudinary upload did not return a URL: {result}")
    log.info("[Instagram] Public image URL: %s", url)
    return url


def _wait_for_container(container_id: str, label: str) -> None:
    deadline = time.monotonic() + CONTAINER_TIMEOUT_SECONDS
    while True:
        data = _graph("GET", container_id, fields="status_code,status")
        status = data.get("status_code")
        if status == "FINISHED":
            return
        if status in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"Instagram {label} media failed processing: {data.get('status', data)}")
        if "error" in data:
            raise GraphApiError(f"{label} status check", data)
        if time.monotonic() > deadline:
            raise TimeoutError(f"Instagram {label} media was not ready after {CONTAINER_TIMEOUT_SECONDS}s")
        log.info("[Instagram] %s media status: %s, waiting...", label, status or "IN_PROGRESS")
        time.sleep(POLL_INTERVAL_SECONDS)


def _publish(user_id: str, container_id: str, label: str) -> str:
    _wait_for_container(container_id, label)
    data = _graph("POST", f"{user_id}/media_publish", creation_id=container_id)
    if "id" not in data:
        raise GraphApiError(f"{label} publish", data)
    return data["id"]


def build_caption(details: EventDetails) -> str:
    parts = [details.event_name, "", details.description]
    try:
        start = details.start_datetime()
        parts += ["", f"{start.strftime('%A, %B %d')} at {start.strftime('%I:%M %p').lstrip('0')}"]
    except ValueError:
        pass
    if details.meeting_link:
        parts.append(f"Where: {details.meeting_link}")
    caption = "\n".join(parts)
    return caption if len(caption) <= MAX_CAPTION else caption[: MAX_CAPTION - 1] + "…"


def run_post_to_instagram(details: EventDetails, post_story: bool = True) -> dict:
    user_id = env("INSTAGRAM_USER_ID")
    if not user_id or not env("INSTAGRAM_ACCESS_TOKEN"):
        raise ValueError("INSTAGRAM_ACCESS_TOKEN / INSTAGRAM_USER_ID are not set in .env")

    image_url = _public_image_url(details.image)

    log.info("[Instagram] Creating feed post...")
    feed = _graph("POST", f"{user_id}/media", image_url=image_url, caption=build_caption(details))
    if "id" not in feed:
        raise GraphApiError("feed upload", feed)
    feed_id = _publish(user_id, feed["id"], "feed")
    log.info("[Instagram] Feed post published (id %s)", feed_id)

    result = {"feed_post_id": feed_id, "image_url": image_url}
    if post_story:
        log.info("[Instagram] Creating story...")
        story = _graph("POST", f"{user_id}/media", image_url=image_url, media_type="STORIES")
        if "id" not in story:
            raise GraphApiError("story upload", story)
        story_id = _publish(user_id, story["id"], "story")
        log.info("[Instagram] Story published (id %s)", story_id)
        result["story_id"] = story_id
    return result
