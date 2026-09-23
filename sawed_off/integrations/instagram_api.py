"""Instagram: connect the club account with OAuth, then publish posts and stories.

Connecting ("Instagram API with Instagram Login")
-------------------------------------------------
1. ``authorization_url()`` sends the officer to Instagram's consent page for
   the club account, asking for ``instagram_business_basic`` and
   ``instagram_business_content_publish``.
2. Instagram redirects to ``/api/instagram/callback?code=...``.
   ``handle_callback`` swaps the code for a short-lived token, then for a
   *long-lived* one (60 days), looks up the account id/username, and stores
   it all in ``DATA_DIR/instagram_token.json``.
3. ``credentials()`` refreshes the long-lived token when it is getting old,
   so as long as the app posts at least once every 60 days nobody has to
   touch Instagram settings again.

The host registers a Meta app once and puts ``INSTAGRAM_APP_ID`` /
``INSTAGRAM_APP_SECRET`` in ``.env``.  A manually created
``INSTAGRAM_ACCESS_TOKEN`` + ``INSTAGRAM_USER_ID`` (the pre-2.1 way, via the
Facebook Graph API) still works as a fallback.

Publishing
----------
Two steps: create a *media container* from a public image URL, then publish
it once its ``status_code`` is FINISHED.  Local files are made public either
through Cloudinary or, when the app itself is on a public HTTPS domain, via a
temporary self-hosted link (``publicfiles``).
"""

from __future__ import annotations

import json
import logging
import secrets
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import requests

from .. import config, publicfiles
from ..config import env
from ..models import EventDetails

log = logging.getLogger(__name__)

API_VERSION = "v22.0"
IG_GRAPH = "https://graph.instagram.com"      # Instagram Login tokens
FB_GRAPH = "https://graph.facebook.com"       # legacy Facebook Login tokens
IG_AUTHORIZE_URL = "https://www.instagram.com/oauth/authorize"
IG_TOKEN_URL = "https://api.instagram.com/oauth/access_token"
OAUTH_SCOPES = ["instagram_business_basic", "instagram_business_content_publish"]

HTTP_TIMEOUT = 30
CONTAINER_TIMEOUT_SECONDS = 300
POLL_INTERVAL_SECONDS = 5
MAX_CAPTION = 2200
REFRESH_WHEN_OLDER_THAN = timedelta(days=1)      # Instagram refuses to refresh younger tokens
REFRESH_WHEN_EXPIRING_WITHIN = timedelta(days=20)

_pending_states: dict[str, float] = {}
STATE_TTL_SECONDS = 600


@dataclass
class IgCredentials:
    token: str
    user_id: str
    graph_base: str
    source: str  # "oauth" | "env"


# --- Configuration --------------------------------------------------------------

def app_configured() -> bool:
    return bool(env("INSTAGRAM_APP_ID") and env("INSTAGRAM_APP_SECRET"))


def env_token_configured() -> bool:
    return bool(env("INSTAGRAM_ACCESS_TOKEN") and env("INSTAGRAM_USER_ID"))


def redirect_uri() -> str:
    return env("INSTAGRAM_REDIRECT_URI", f"{config.public_base_url()}/api/instagram/callback")


def _cloudinary_configured() -> bool:
    return all(env(k) for k in ("CLOUDINARY_CLOUD_NAME", "CLOUDINARY_API_KEY", "CLOUDINARY_API_SECRET"))


def image_hosting() -> str:
    """How a local image gets a public URL: 'cloudinary', 'self' or 'none'."""
    if _cloudinary_configured():
        return "cloudinary"
    if publicfiles.available():
        return "self"
    return "none"


# --- OAuth connection ----------------------------------------------------------

def authorization_url() -> str:
    if not app_configured():
        raise ValueError("INSTAGRAM_APP_ID / INSTAGRAM_APP_SECRET are not set in .env")
    now = time.time()
    for state, issued in list(_pending_states.items()):
        if now - issued > STATE_TTL_SECONDS:
            _pending_states.pop(state, None)
    state = secrets.token_urlsafe(24)
    _pending_states[state] = now
    params = {
        "client_id": env("INSTAGRAM_APP_ID"),
        "redirect_uri": redirect_uri(),
        "response_type": "code",
        "scope": ",".join(OAUTH_SCOPES),
        "state": state,
        "force_reauth": "true",
    }
    return f"{IG_AUTHORIZE_URL}?{requests.compat.urlencode(params)}"


def _json(response: requests.Response, what: str) -> dict[str, Any]:
    try:
        data = response.json()
    except ValueError:
        raise RuntimeError(f"Instagram {what}: non-JSON response (HTTP {response.status_code})") from None
    if not response.ok or "error" in data or "error_type" in data:
        err = data.get("error") if isinstance(data.get("error"), dict) else data
        message = err.get("message") or err.get("error_message") or json.dumps(data)
        raise RuntimeError(f"Instagram {what} failed: {message}")
    return data


def handle_callback(code: str, state: str | None) -> dict[str, Any]:
    """Exchange the code, upgrade to a long-lived token, store it, return status."""
    if not state or _pending_states.pop(state, None) is None:
        raise ValueError("OAuth state mismatch (link expired or was not started here). Try again.")
    code = code.split("#")[0]  # Instagram sometimes appends '#_' to the redirect

    resp = requests.post(
        IG_TOKEN_URL,
        data={
            "client_id": env("INSTAGRAM_APP_ID"),
            "client_secret": env("INSTAGRAM_APP_SECRET"),
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri(),
            "code": code,
        },
        timeout=HTTP_TIMEOUT,
    )
    data = _json(resp, "code exchange")
    # The Instagram Login flow wraps the result in {"data": [ {...} ]}.
    if isinstance(data.get("data"), list) and data["data"]:
        data = data["data"][0]
    short_token = data.get("access_token")
    user_id = str(data.get("user_id") or "")
    if not short_token:
        raise RuntimeError(f"Instagram code exchange returned no access token: {data}")

    long_token, expires_in = _exchange_long_lived(short_token)
    info = _me(long_token)
    record = {
        "access_token": long_token,
        "user_id": str(info.get("user_id") or user_id or info.get("id") or ""),
        "username": info.get("username"),
        "obtained_at": _now_iso(),
        "expires_at": _iso_in(expires_in),
    }
    _save_record(record)
    log.info("[Instagram] Connected as @%s (id %s)", record["username"], record["user_id"])
    return connection_status()


def _exchange_long_lived(short_token: str) -> tuple[str, int]:
    resp = requests.get(
        f"{IG_GRAPH}/access_token",
        params={
            "grant_type": "ig_exchange_token",
            "client_secret": env("INSTAGRAM_APP_SECRET"),
            "access_token": short_token,
        },
        timeout=HTTP_TIMEOUT,
    )
    data = _json(resp, "long-lived token exchange")
    return data["access_token"], int(data.get("expires_in", 60 * 24 * 3600))


def _refresh_long_lived(token: str) -> tuple[str, int]:
    resp = requests.get(
        f"{IG_GRAPH}/refresh_access_token",
        params={"grant_type": "ig_refresh_token", "access_token": token},
        timeout=HTTP_TIMEOUT,
    )
    data = _json(resp, "token refresh")
    return data["access_token"], int(data.get("expires_in", 60 * 24 * 3600))


def _me(token: str) -> dict[str, Any]:
    resp = requests.get(
        f"{IG_GRAPH}/{API_VERSION}/me",
        params={"fields": "user_id,username", "access_token": token},
        timeout=HTTP_TIMEOUT,
    )
    return _json(resp, "account lookup")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _iso_in(seconds: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(seconds=seconds)).isoformat(timespec="seconds")


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _load_record() -> dict[str, Any] | None:
    path = config.INSTAGRAM_TOKEN_FILE
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _save_record(record: dict[str, Any]) -> None:
    config.INSTAGRAM_TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    config.INSTAGRAM_TOKEN_FILE.write_text(json.dumps(record, indent=2), encoding="utf-8")
    try:
        config.INSTAGRAM_TOKEN_FILE.chmod(0o600)
    except OSError:
        pass


def disconnect() -> None:
    if config.INSTAGRAM_TOKEN_FILE.is_file():
        config.INSTAGRAM_TOKEN_FILE.unlink()
        log.info("[Instagram] Disconnected (token removed)")


def refresh_if_needed(force: bool = False) -> dict[str, Any] | None:
    """Refresh the stored long-lived token when it is old enough and near expiry."""
    record = _load_record()
    if not record:
        return None
    now = datetime.now(timezone.utc)
    obtained = _parse_iso(record.get("obtained_at")) or now
    expires = _parse_iso(record.get("expires_at")) or now
    old_enough = now - obtained >= REFRESH_WHEN_OLDER_THAN
    expiring = expires - now <= REFRESH_WHEN_EXPIRING_WITHIN
    if force or (old_enough and expiring):
        token, expires_in = _refresh_long_lived(record["access_token"])
        record.update({"access_token": token, "obtained_at": _now_iso(), "expires_at": _iso_in(expires_in)})
        _save_record(record)
        log.info("[Instagram] Token refreshed; now valid until %s", record["expires_at"])
    return record


def credentials() -> IgCredentials:
    """Prefer the OAuth connection; fall back to the manual .env token."""
    record = _load_record()
    if record and record.get("access_token") and record.get("user_id"):
        expires = _parse_iso(record.get("expires_at"))
        if expires and expires <= datetime.now(timezone.utc):
            raise ValueError("The Instagram connection has expired. Reconnect Instagram in the Connections panel.")
        try:
            record = refresh_if_needed() or record
        except RuntimeError as exc:
            log.warning("[Instagram] Token refresh failed (will keep using current token): %s", exc)
        return IgCredentials(record["access_token"], str(record["user_id"]), IG_GRAPH, "oauth")
    if env_token_configured():
        return IgCredentials(env("INSTAGRAM_ACCESS_TOKEN"), env("INSTAGRAM_USER_ID"), FB_GRAPH, "env")
    raise ValueError("Instagram is not connected. Use 'Connect Instagram' in the Connections panel.")


def connection_status(verify: bool = False) -> dict[str, Any]:
    status: dict[str, Any] = {
        "app_configured": app_configured(),
        "connected": False,
        "source": None,
        "username": None,
        "user_id": None,
        "expires_at": None,
        "image_hosting": image_hosting(),
        "ok": False,
        "error": None,
    }
    record = _load_record()
    if record and record.get("access_token"):
        status.update({
            "connected": True,
            "source": "oauth",
            "username": record.get("username"),
            "user_id": record.get("user_id"),
            "expires_at": record.get("expires_at"),
            "ok": True,
        })
        expires = _parse_iso(record.get("expires_at"))
        if expires and expires <= datetime.now(timezone.utc):
            status.update({"ok": False, "error": "Connection expired; reconnect."})
    elif env_token_configured():
        status.update({"connected": True, "source": "env", "user_id": env("INSTAGRAM_USER_ID"), "ok": True})
    if verify and status["ok"]:
        try:
            creds = credentials()
            me = _graph(creds, "GET", "me", fields="username" if creds.source == "oauth" else "username,id")
            status["username"] = me.get("username") or status["username"]
        except Exception as exc:  # noqa: BLE001
            status.update({"ok": False, "error": str(exc)})
    return status


# --- Preflight -------------------------------------------------------------------

def preflight(details: EventDetails) -> list[str]:
    problems: list[str] = []
    try:
        credentials()
    except ValueError as exc:
        problems.append(str(exc))
    if details.image and not details.image.startswith(("http://", "https://")):
        if not Path(details.image).is_file():
            problems.append(f"Image file not found: {details.image}")
        elif image_hosting() == "none":
            problems.append(
                "Instagram needs a public image URL. Either set the CLOUDINARY_* variables, "
                "or host the app at an https:// address (SOS_PUBLIC_URL) so it can serve the image itself."
            )
    return problems


# --- Graph API -----------------------------------------------------------------------

class GraphApiError(RuntimeError):
    def __init__(self, action: str, payload: Any) -> None:
        err = payload.get("error", {}) if isinstance(payload, dict) else {}
        message = err.get("message") or str(payload)
        hint = ""
        if "OAuth" in message or err.get("code") == 190:
            hint = " (The Instagram token is invalid or expired; reconnect Instagram.)"
        super().__init__(f"Instagram {action} failed: {message}{hint}")
        self.code = err.get("code")
        self.payload = payload


def _graph(creds: IgCredentials, method: str, path: str, **params: Any) -> dict[str, Any]:
    params["access_token"] = creds.token
    url = f"{creds.graph_base}/{API_VERSION}/{path}"
    try:
        if method == "GET":
            response = requests.get(url, params=params, timeout=HTTP_TIMEOUT)
        else:
            response = requests.post(url, data=params, timeout=HTTP_TIMEOUT)
    except requests.RequestException as exc:
        reason = str(exc).split("(Caused by")[0].strip().rstrip(":") or exc.__class__.__name__
        raise RuntimeError(f"Could not reach the Instagram API: {reason[:160]}") from exc
    try:
        return response.json()
    except ValueError:
        raise RuntimeError(f"Instagram API returned non-JSON (HTTP {response.status_code})") from None


def _public_image_url(image: str) -> str:
    if image.startswith(("http://", "https://")):
        return image
    path = Path(image)
    if not path.is_file():
        raise FileNotFoundError(f"Image file not found: {image}")
    hosting = image_hosting()
    if hosting == "cloudinary":
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
    elif hosting == "self":
        url = publicfiles.publish(path)
        log.info("[Instagram] Serving %s at a temporary public link", path.name)
    else:
        raise ValueError("No way to give Instagram a public image URL (configure Cloudinary or an https public URL).")
    log.info("[Instagram] Public image URL: %s", url)
    return url


def _wait_for_container(creds: IgCredentials, container_id: str, label: str) -> None:
    deadline = time.monotonic() + CONTAINER_TIMEOUT_SECONDS
    while True:
        data = _graph(creds, "GET", container_id, fields="status_code,status")
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


def _publish(creds: IgCredentials, container_id: str, label: str) -> str:
    _wait_for_container(creds, container_id, label)
    data = _graph(creds, "POST", f"{creds.user_id}/media_publish", creation_id=container_id)
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
    creds = credentials()
    image_url = _public_image_url(details.image)

    log.info("[Instagram] Creating feed post...")
    feed = _graph(creds, "POST", f"{creds.user_id}/media", image_url=image_url, caption=build_caption(details))
    if "id" not in feed:
        raise GraphApiError("feed upload", feed)
    feed_id = _publish(creds, feed["id"], "feed")
    log.info("[Instagram] Feed post published (id %s)", feed_id)

    result = {"feed_post_id": feed_id, "image_url": image_url}
    if post_story:
        log.info("[Instagram] Creating story...")
        story = _graph(creds, "POST", f"{creds.user_id}/media", image_url=image_url, media_type="STORIES")
        if "id" not in story:
            raise GraphApiError("story upload", story)
        story_id = _publish(creds, story["id"], "story")
        log.info("[Instagram] Story published (id %s)", story_id)
        result["story_id"] = story_id
    return result
