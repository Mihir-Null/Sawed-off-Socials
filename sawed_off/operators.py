"""The officers allowed to use the app ("operators").

The app has one *club identity* (the connected Google, Instagram and Discord
accounts).  Operators are the people allowed to press the buttons.  They can
sign in either with the shared ``APP_PASSWORD`` or with their own Google
account, if their email is on this list.  The Google account that is
connected as the club identity is always an operator.

Stored as a JSON list of emails in ``DATA_DIR/operators.json``.
"""

from __future__ import annotations

import json
import logging
import re

from . import config

log = logging.getLogger(__name__)

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _normalize(email: str) -> str:
    return (email or "").strip().lower()


def load() -> list[str]:
    path = config.OPERATORS_FILE
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        log.error("operators.json is unreadable (%s); treating as empty", exc)
        return []
    if not isinstance(data, list):
        return []
    return sorted({_normalize(e) for e in data if isinstance(e, str) and _normalize(e)})


def save(emails: list[str]) -> None:
    config.OPERATORS_FILE.parent.mkdir(parents=True, exist_ok=True)
    config.OPERATORS_FILE.write_text(json.dumps(sorted(set(emails)), indent=2) + "\n", encoding="utf-8")


def add(email: str) -> list[str]:
    email = _normalize(email)
    if not _EMAIL_RE.match(email):
        raise ValueError(f"'{email}' is not a valid email address")
    emails = load()
    if email not in emails:
        emails.append(email)
        save(emails)
        log.info("Operator added: %s", email)
    return sorted(emails)


def remove(email: str) -> list[str]:
    email = _normalize(email)
    emails = [e for e in load() if e != email]
    save(emails)
    log.info("Operator removed: %s", email)
    return emails


def club_email() -> str | None:
    """Email of the Google account connected as the club identity, if any."""
    from .integrations import google_apis  # local import: avoids a cycle at import time

    return _normalize(google_apis.auth_status().get("email") or "") or None


def any_configured() -> bool:
    return bool(load())


def is_operator(email: str | None) -> bool:
    email = _normalize(email or "")
    if not email:
        return False
    return email in load() or email == club_email()
