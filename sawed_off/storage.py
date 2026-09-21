"""Reading and writing the JSON files in the data directory.

Writes are atomic (write to a temp file, then rename) so a crash or a
concurrent read never sees a half-written ``event_details.json``.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any

from . import config
from .models import EventDetails

log = logging.getLogger(__name__)


def _read_json(path: Path) -> Any:
    if not path.is_file() or path.stat().st_size == 0:
        return None
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _write_json_atomic(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=path.name, suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=4, ensure_ascii=False)
            fh.write("\n")
        os.replace(tmp_name, path)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def load_details() -> EventDetails:
    """Load the saved event (or defaults). Corrupt files fall back to defaults with a log."""
    try:
        raw = _read_json(config.EVENT_DETAILS_FILE)
    except json.JSONDecodeError as exc:
        log.error("event_details.json is not valid JSON (%s); starting from defaults", exc)
        raw = None
    try:
        return EventDetails.from_raw(raw)
    except Exception as exc:  # pragma: no cover - defensive
        log.error("Saved event details are invalid (%s); starting from defaults", exc)
        return EventDetails()


def save_details(details: EventDetails) -> None:
    _write_json_atomic(config.EVENT_DETAILS_FILE, details.model_dump())


def load_custom_emails() -> dict[str, dict[str, str]]:
    """Return the custom email templates keyed by name.

    Each value has ``email``, ``subject`` and ``body``. Missing file -> ``{}``.
    """
    raw = _read_json(config.CUSTOM_EMAILS_FILE)
    if not raw:
        return {}
    if not isinstance(raw, dict):
        raise ValueError("custom_emails.json must be a JSON object of name -> {email, subject, body}")
    cleaned: dict[str, dict[str, str]] = {}
    for name, entry in raw.items():
        if not isinstance(entry, dict) or not all(k in entry for k in ("email", "subject", "body")):
            raise ValueError(f"custom_emails.json entry '{name}' needs 'email', 'subject' and 'body'")
        cleaned[str(name)] = {k: str(entry[k]) for k in ("email", "subject", "body")}
    return cleaned
