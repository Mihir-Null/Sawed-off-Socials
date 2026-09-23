"""Google: OAuth login, Calendar events and Gmail sending.

Two OAuth flows share one Google client:

* purpose ``"club"``   - connect the club account whose Calendar and Gmail
  the app posts with.  Asks for calendar + gmail.send scopes and stores the
  refresh token in ``DATA_DIR/google_token.json``.
* purpose ``"operator"`` - an officer signing *in to the app* with their own
  Google account.  Asks only for their email; nothing is stored.  The caller
  checks the email against the operators list.

Both: ``authorization_url(purpose)`` remembers a random ``state`` so the
callback can verify the redirect came from us (CSRF protection), and
``handle_callback`` exchanges the code and returns the account email.
``get_credentials()`` loads/refreshes the club token for API calls and writes
the refreshed token back so we do not refresh on every single call.
"""

from __future__ import annotations

import base64
import csv
import json
import logging
import os
import secrets
import string
import time
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from .. import config, storage
from ..config import env
from ..models import EventDetails

log = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/userinfo.email",
    "openid",
]
OPERATOR_SCOPES = ["https://www.googleapis.com/auth/userinfo.email", "openid"]
PURPOSES = ("club", "operator")

# Google may return *more* scopes than requested (previously granted ones);
# without this the oauthlib client raises "Scope has changed" on callback.
os.environ.setdefault("OAUTHLIB_RELAX_TOKEN_SCOPE", "1")

# Outstanding OAuth ``state`` values -> (time issued, purpose, PKCE verifier).
# Single-process app, so a dict is enough; entries expire after 10 minutes.
# The PKCE code verifier is generated when the consent URL is built and must
# be presented again when the code is exchanged; since the callback builds a
# fresh Flow object we have to carry it across ourselves.
_pending_states: dict[str, tuple[float, str, str | None]] = {}
STATE_TTL_SECONDS = 600


# --- Configuration -----------------------------------------------------------

def redirect_uri() -> str:
    return env("GOOGLE_REDIRECT_URI", f"{config.public_base_url()}/api/auth/callback")


def client_config() -> dict[str, Any]:
    return {
        "web": {
            "client_id": env("GOOGLE_CLIENT_ID"),
            "project_id": env("GOOGLE_PROJECT_ID"),
            "client_secret": env("GOOGLE_CLIENT_SECRET"),
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "redirect_uris": [redirect_uri()],
        }
    }


def is_configured() -> bool:
    return bool(env("GOOGLE_CLIENT_ID") and env("GOOGLE_CLIENT_SECRET"))


def preflight(details: EventDetails) -> list[str]:  # noqa: ARG001 - signature shared by all integrations
    if not is_configured():
        return ["GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET are not set in .env"]
    if not config.GOOGLE_TOKEN_FILE.is_file():
        return ["Not logged in to Google. Use the 'Sign in with Google' button first."]
    return []


# --- OAuth -------------------------------------------------------------------

def _flow(purpose: str) -> Flow:
    if not is_configured():
        raise ValueError("GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET are not set in .env")
    scopes = SCOPES if purpose == "club" else OPERATOR_SCOPES
    flow = Flow.from_client_config(client_config(), scopes=scopes)
    flow.redirect_uri = redirect_uri()
    return flow


def authorization_url(purpose: str = "club") -> str:
    if purpose not in PURPOSES:
        raise ValueError(f"Unknown OAuth purpose '{purpose}'")
    now = time.time()
    for state, (issued, *_rest) in list(_pending_states.items()):
        if now - issued > STATE_TTL_SECONDS:
            _pending_states.pop(state, None)
    state = secrets.token_urlsafe(24)
    flow = _flow(purpose)
    if purpose == "club":
        # offline + consent: we need a refresh token, and Google only issues
        # one on a consent screen.
        url, _ = flow.authorization_url(
            access_type="offline", prompt="consent", include_granted_scopes="true", state=state
        )
    else:
        url, _ = flow.authorization_url(prompt="select_account", state=state)
    _pending_states[state] = (now, purpose, getattr(flow, "code_verifier", None))
    return url


def _fetch_email(creds: Credentials) -> str | None:
    try:
        info = build("oauth2", "v2", credentials=creds, cache_discovery=False).userinfo().get().execute()
        return info.get("email")
    except Exception as exc:  # noqa: BLE001
        log.warning("[Google] Could not read account email: %s", exc)
        return None


def handle_callback(code: str, state: str | None) -> dict[str, Any]:
    """Exchange ``code`` for tokens. Returns ``{"purpose", "email"}``.

    For the club purpose the token is persisted; for an operator sign-in
    nothing is stored (the email is all the caller needs).
    """
    entry = _pending_states.pop(state, None) if state else None
    if entry is None:
        raise ValueError("OAuth state mismatch (login link expired or was not started here). Try again.")
    _, purpose, code_verifier = entry

    flow = _flow(purpose)
    if code_verifier:
        flow.code_verifier = code_verifier
    flow.fetch_token(code=code)
    creds = flow.credentials
    email = _fetch_email(creds)

    if purpose == "club":
        _save_token(creds, email)
        log.info("[Google] Club account connected: %s", email or "(unknown email)")
    else:
        if not email:
            raise ValueError("Google did not return an email address for this account.")
        log.info("[Google] Operator sign-in: %s", email)
    return {"purpose": purpose, "email": email or ""}


def _save_token(creds: Credentials, email: str | None) -> None:
    data = json.loads(creds.to_json())
    if email:
        data["account_email"] = email
    elif config.GOOGLE_TOKEN_FILE.is_file():
        try:
            data["account_email"] = json.loads(config.GOOGLE_TOKEN_FILE.read_text()).get("account_email")
        except (OSError, ValueError):
            pass
    config.GOOGLE_TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    config.GOOGLE_TOKEN_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    try:
        config.GOOGLE_TOKEN_FILE.chmod(0o600)
    except OSError:
        pass


def auth_status() -> dict[str, Any]:
    if not config.GOOGLE_TOKEN_FILE.is_file():
        return {"configured": is_configured(), "logged_in": False, "email": None}
    try:
        data = json.loads(config.GOOGLE_TOKEN_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"configured": is_configured(), "logged_in": False, "email": None}
    return {"configured": is_configured(), "logged_in": True, "email": data.get("account_email")}


def logout() -> None:
    if config.GOOGLE_TOKEN_FILE.is_file():
        config.GOOGLE_TOKEN_FILE.unlink()
        log.info("[Google] Club account disconnected (token removed)")


def connection_status(verify: bool = False) -> dict[str, Any]:
    """Status for the Connections panel. ``verify`` makes a real token check."""
    status = auth_status()
    status.update({"ok": status["logged_in"], "error": None})
    if verify and status["logged_in"]:
        try:
            get_credentials()
        except Exception as exc:  # noqa: BLE001
            status["ok"] = False
            status["error"] = str(exc)
    return status


def get_credentials() -> Credentials:
    if not config.GOOGLE_TOKEN_FILE.is_file():
        raise ValueError("Not logged in to Google. Use the 'Sign in with Google' button first.")
    creds = Credentials.from_authorized_user_file(str(config.GOOGLE_TOKEN_FILE), SCOPES)
    if creds.valid:
        return creds
    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except RefreshError as exc:
            raise ValueError(
                "Google login expired or was revoked. Sign in with Google again."
            ) from exc
        _save_token(creds, None)
        return creds
    raise ValueError("Google login is invalid. Sign in with Google again.")


# --- Calendar ----------------------------------------------------------------

def run_add_to_calendar(details: EventDetails) -> dict:
    creds = get_credentials()
    service = build("calendar", "v3", credentials=creds, cache_discovery=False)

    calendar_id = "primary"
    if details.calendar_name:
        calendars = service.calendarList().list().execute().get("items", [])
        match = next((c for c in calendars if c.get("summary") == details.calendar_name), None)
        if match:
            calendar_id = match["id"]
            log.info("[Calendar] Using calendar '%s'", details.calendar_name)
        else:
            names = ", ".join(c.get("summary", "?") for c in calendars)
            log.warning("[Calendar] No calendar named '%s' (have: %s); using primary",
                        details.calendar_name, names)

    start, end = details.start_datetime(), details.end_datetime()
    description = details.description
    if details.more_info_link:
        description += f"\n\nMore info: {details.more_info_link}"
    body = {
        "summary": details.event_name,
        "location": details.meeting_link,
        "description": description,
        "start": {"dateTime": start.isoformat(), "timeZone": details.timezone},
        "end": {"dateTime": end.isoformat(), "timeZone": details.timezone},
        "reminders": {"useDefault": True},
    }
    try:
        event = service.events().insert(calendarId=calendar_id, body=body).execute()
    except HttpError as exc:
        raise RuntimeError(f"Google Calendar rejected the event: {exc}") from exc
    log.info("[Calendar] Event created: %s", event.get("htmlLink"))
    return {"link": event.get("htmlLink"), "calendar": calendar_id}


# --- Gmail -------------------------------------------------------------------

def _send_email(service: Any, recipient: str, subject: str, body: str) -> str:
    message = MIMEText(body)
    message["to"] = recipient
    message["from"] = "me"
    message["subject"] = subject
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    sent = service.users().messages().send(userId="me", body={"raw": raw}).execute()
    return sent["id"]


def read_recipients(csv_path: str | Path, column: str) -> list[str]:
    """Return de-duplicated, trimmed email addresses from ``column`` of the CSV.

    Uses ``utf-8-sig`` so a BOM (which Google Sheets/Excel add) does not turn
    the first header into ``"\\ufeffEmail"`` and cause a "column missing" error.
    Column matching is case-insensitive and ignores surrounding whitespace.
    """
    path = Path(csv_path)
    if not path.is_file():
        raise FileNotFoundError(f"CSV file not found: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        headers = [h.strip() for h in (reader.fieldnames or [])]
        wanted = column.strip().lower()
        try:
            actual = next(h for h in headers if h.lower() == wanted)
        except StopIteration:
            raise ValueError(
                f"Column '{column}' not found in CSV. Columns are: {', '.join(headers) or '(none)'}"
            ) from None
        seen: set[str] = set()
        recipients: list[str] = []
        for row in reader:
            value = (row.get(actual) or "").strip()
            for candidate in value.replace(";", ",").split(","):
                candidate = candidate.strip()
                if "@" in candidate and "." in candidate.rsplit("@", 1)[-1]:
                    key = candidate.lower()
                    if key not in seen:
                        seen.add(key)
                        recipients.append(candidate)
    return recipients


def build_event_email(details: EventDetails) -> tuple[str, str]:
    start = details.start_datetime()
    subject = f"{details.club_name} Event: {details.event_name}"
    lines = [
        details.event_name,
        "",
        details.description,
        "",
        f"When: {start.strftime('%A, %B %d, %Y')} at {start.strftime('%I:%M %p %Z').lstrip('0')}",
        f"Where: {details.meeting_link}",
    ]
    if details.more_info_link:
        lines.append(f"More info: {details.more_info_link}")
    lines += ["", "Best regards,", f"The {details.club_name} Team"]
    return subject, "\n".join(lines)


def run_send_event_emails(details: EventDetails) -> dict:
    recipients = read_recipients(details.csv_file, details.email_column)
    if not recipients:
        raise ValueError("No valid email addresses found in the CSV.")
    log.info("[Gmail] Sending to %d recipient(s)", len(recipients))

    creds = get_credentials()
    service = build("gmail", "v1", credentials=creds, cache_discovery=False)
    subject, body = build_event_email(details)

    sent, failed = [], []
    for recipient in recipients:
        try:
            _send_email(service, recipient, subject, body)
            sent.append(recipient)
        except HttpError as exc:
            failed.append({"email": recipient, "error": str(exc)})
            log.warning("[Gmail] Could not send to %s: %s", recipient, exc)
            # A quota/auth problem will fail every remaining send; stop early.
            if exc.resp.status in (401, 403, 429):
                log.error("[Gmail] Stopping: Gmail returned HTTP %s", exc.resp.status)
                break
    log.info("[Gmail] Done: %d sent, %d failed", len(sent), len(failed))
    result = {"sent": len(sent), "failed": failed, "total": len(recipients)}
    if failed and not sent:
        raise RuntimeError(f"All {len(failed)} emails failed. First error: {failed[0]['error']}")
    return result


class _SafeFormat(dict):
    """``str.format_map`` helper: unknown ``{placeholders}`` are left as-is."""

    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


def render_template(template: str, context: dict[str, Any]) -> str:
    """Fill ``{field}`` placeholders; tolerate unknown names and stray braces."""
    try:
        return string.Formatter().vformat(template, (), _SafeFormat(context))
    except (ValueError, IndexError):
        # Unbalanced braces etc. - better to send the raw text than crash.
        return template


def run_send_custom_emails(details: EventDetails) -> dict:
    names = details.custom_email_names()
    if not names:
        raise ValueError("Custom emails list is empty.")
    templates = storage.load_custom_emails()
    if not templates:
        raise ValueError(f"No templates found. Create {config.CUSTOM_EMAILS_FILE} first.")
    unknown = [n for n in names if n not in templates]
    if unknown:
        raise ValueError(
            f"Unknown custom email name(s): {', '.join(unknown)}. "
            f"Available: {', '.join(templates) or '(none)'}"
        )

    creds = get_credentials()
    service = build("gmail", "v1", credentials=creds, cache_discovery=False)
    context = details.template_context()
    sent = []
    for name in names:
        entry = templates[name]
        subject = render_template(entry["subject"], context)
        body = render_template(entry["body"], context)
        _send_email(service, entry["email"], subject, body)
        log.info("[Gmail] Custom email '%s' sent to %s", name, entry["email"])
        sent.append({"name": name, "to": entry["email"]})
    return {"sent": sent}
