"""Central place for paths, environment variables and small shared helpers.

Everything that used to be scattered across the old ``Jack_*.py`` files
(relative paths like ``"token.json"``, duplicated timezone maps, ad-hoc
``os.environ.get`` calls) lives here so there is exactly one answer to
"where does this file live?" and "what is this setting called?".

All persistent state lives under one directory, ``DATA_DIR`` (default:
``<repo>/data``, override with ``SOS_DATA_DIR``).  That makes self-hosting
simple: mount a single volume and you keep uploads, the saved event, the
Google login token and the custom email templates across restarts.
"""

from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from dotenv import load_dotenv

log = logging.getLogger(__name__)

# <repo root>  (this file is <repo>/sawed_off/config.py)
BASE_DIR = Path(__file__).resolve().parent.parent

# Load ``.env`` from the repo root first, then fall back to the current
# working directory (the old behaviour) so nothing existing breaks.
load_dotenv(BASE_DIR / ".env")
load_dotenv()


def env(name: str, default: str | None = None) -> str | None:
    """Read an environment variable, treating blank strings as unset."""
    value = os.environ.get(name)
    if value is None:
        return default
    value = value.strip().strip('"').strip("'")
    return value or default


def env_bool(name: str, default: bool = False) -> bool:
    value = env(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


# --- Data directory -------------------------------------------------------

DATA_DIR = Path(env("SOS_DATA_DIR", str(BASE_DIR / "data"))).resolve()
UPLOAD_DIR = DATA_DIR / "uploads"
EVENT_DETAILS_FILE = DATA_DIR / "event_details.json"
CUSTOM_EMAILS_FILE = DATA_DIR / "custom_emails.json"
GOOGLE_TOKEN_FILE = DATA_DIR / "google_token.json"
INSTAGRAM_TOKEN_FILE = DATA_DIR / "instagram_token.json"
OPERATORS_FILE = DATA_DIR / "operators.json"

FRONTEND_DIST = BASE_DIR / "frontend" / "dist"

# Files from the pre-2.0 layout that lived in the repo root / CWD.
# On first start we copy them into DATA_DIR so existing installs keep working.
_LEGACY_FILES = {
    "event_details.json": EVENT_DETAILS_FILE,
    "custom_emails.json": CUSTOM_EMAILS_FILE,
    "token.json": GOOGLE_TOKEN_FILE,
}


def ensure_data_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def migrate_legacy_files() -> list[str]:
    """Copy files from the old flat layout into ``DATA_DIR`` (never overwrite).

    Returns the list of files that were migrated so the caller can log them.
    """
    ensure_data_dirs()
    migrated: list[str] = []
    for old_name, new_path in _LEGACY_FILES.items():
        if new_path.exists():
            continue
        for candidate_dir in (BASE_DIR, Path.cwd()):
            old_path = candidate_dir / old_name
            if old_path.is_file():
                shutil.copy2(old_path, new_path)
                migrated.append(f"{old_path} -> {new_path}")
                break

    old_uploads = BASE_DIR / "uploads"
    if old_uploads.is_dir() and old_uploads.resolve() != UPLOAD_DIR.resolve():
        for item in old_uploads.iterdir():
            target = UPLOAD_DIR / item.name
            if item.is_file() and not target.exists():
                shutil.copy2(item, target)
                migrated.append(f"{item} -> {target}")
    return migrated


# --- Timezones ------------------------------------------------------------

# People type "EST"; APIs want IANA names. Abbreviations are ambiguous
# (CST is both Chicago and China) so this only covers the common US ones.
TIMEZONE_ALIASES = {
    "EST": "America/New_York",
    "EDT": "America/New_York",
    "ET": "America/New_York",
    "CST": "America/Chicago",
    "CDT": "America/Chicago",
    "CT": "America/Chicago",
    "MST": "America/Denver",
    "MDT": "America/Denver",
    "MT": "America/Denver",
    "PST": "America/Los_Angeles",
    "PDT": "America/Los_Angeles",
    "PT": "America/Los_Angeles",
    "GMT": "Europe/London",
    "BST": "Europe/London",
}


def normalize_timezone(tz_name: str | None) -> str:
    """Return a valid IANA timezone name for ``tz_name``.

    Raises ``ValueError`` if the name is not a known alias or IANA zone.
    """
    if not tz_name or not str(tz_name).strip():
        return "UTC"
    raw = str(tz_name).strip()
    candidate = TIMEZONE_ALIASES.get(raw.upper(), raw)
    try:
        ZoneInfo(candidate)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise ValueError(f"Unknown timezone '{raw}'. Use an IANA name like America/New_York.") from exc
    return candidate


# --- App settings -----------------------------------------------------------

def app_password() -> str | None:
    """Shared password protecting the web UI. ``None`` means no login required."""
    return env("APP_PASSWORD")


def public_url_is_https() -> bool:
    """True when the app is reachable over HTTPS from the internet (needed to
    hand Instagram a link to an uploaded image without Cloudinary)."""
    if env_bool("SOS_PUBLIC_IMAGE_HOSTING"):
        return True
    return public_base_url().startswith("https://")


def public_base_url() -> str:
    """Where the app is reachable from a browser (used for OAuth redirects)."""
    explicit = env("SOS_PUBLIC_URL")
    if explicit:
        return explicit.rstrip("/")
    redirect = env("GOOGLE_REDIRECT_URI")
    if redirect and "/api/auth/callback" in redirect:
        return redirect.split("/api/auth/callback")[0]
    return f"http://localhost:{env('SOS_PORT', '8000')}"
