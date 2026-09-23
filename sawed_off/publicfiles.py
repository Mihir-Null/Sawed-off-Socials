"""Temporarily expose an uploaded file at an unguessable public URL.

Instagram fetches images itself, so it needs a URL it can reach.  When the
app is hosted on a public HTTPS domain we can serve the file ourselves for a
short while instead of requiring a Cloudinary account.  Each link is a random
token that expires after ``TTL_SECONDS``; the route is unauthenticated on
purpose (Meta's servers are the client), but nothing is listable and nothing
persists.
"""

from __future__ import annotations

import secrets
import threading
import time
from pathlib import Path

from . import config

TTL_SECONDS = 60 * 60

_lock = threading.Lock()
_files: dict[str, tuple[Path, float]] = {}


def available() -> bool:
    return config.public_url_is_https()


def publish(path: str | Path) -> str:
    """Return a public URL for ``path`` valid for one hour."""
    file = Path(path)
    if not file.is_file():
        raise FileNotFoundError(f"Image file not found: {path}")
    if not available():
        raise ValueError(
            "Self-hosted image links need SOS_PUBLIC_URL to be an https:// address "
            "(or SOS_PUBLIC_IMAGE_HOSTING=true)."
        )
    token = secrets.token_urlsafe(24)
    now = time.time()
    with _lock:
        for key, (_, expires) in list(_files.items()):
            if expires < now:
                _files.pop(key, None)
        _files[token] = (file, now + TTL_SECONDS)
    return f"{config.public_base_url()}/public/{token}{file.suffix.lower()}"


def resolve(token_with_suffix: str) -> Path | None:
    token = token_with_suffix.split(".", 1)[0]
    with _lock:
        entry = _files.get(token)
        if entry is None:
            return None
        path, expires = entry
        if expires < time.time():
            _files.pop(token, None)
            return None
        return path
