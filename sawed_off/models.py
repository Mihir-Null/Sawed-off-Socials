"""The event schema and per-action validation.

The UI edits one blob of "event details".  Historically that was an untyped
dict, so a missing key or a duration typed as ``"1.5"`` surfaced as a
``KeyError``/``TypeError`` deep inside an API call.  ``EventDetails`` gives
every field a type and a default, coerces what it can (``"1.5"`` -> ``1.5``)
and rejects what it cannot (an unknown timezone) with a readable message.

``problems_for(action, details)`` is the second half: *before* we touch
Discord/Google/Instagram we check that the fields that action needs are
filled in, so the user gets "Discord needs: server_name, channel_name"
instead of a stack trace.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .config import normalize_timezone

ACTIONS = ("discord", "calendar", "email", "instagram", "custom", "all")

# Human labels for error messages ("Event Name" instead of "event_name").
FIELD_LABELS = {
    "event_name": "Event name",
    "description": "Description",
    "image": "Event image",
    "server_name": "Discord server",
    "channel_name": "Discord channel",
    "meeting_link": "Location / meeting link",
    "event_date": "Event date",
    "event_time": "Event time",
    "timezone": "Timezone",
    "calendar_name": "Calendar name",
    "csv_file": "Email list CSV",
    "email_column": "Email column",
    "event_duration": "Duration (hours)",
    "club_name": "Club name",
    "custom_emails": "Custom emails list",
    "more_info_link": "More info link",
}

# Old saved files used this key; we silently rename it on load.
LEGACY_KEYS = {"custom emails list": "custom_emails"}


class EventDetails(BaseModel):
    """Everything the user fills in for one event.

    ``extra="allow"`` keeps any additional keys a user adds (the README
    documents adding fields for use in custom email templates).
    """

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    event_name: str = ""
    description: str = ""
    image: str = ""
    server_name: str = ""
    channel_name: str = ""
    server_id: str = ""   # Discord snowflake ids, set by the dropdowns; names stay
    channel_id: str = ""  # for display and as a fallback when ids are absent
    meeting_link: str = ""
    event_date: str = ""  # YYYY-MM-DD
    event_time: str = ""  # HH:MM (24h)
    timezone: str = "UTC"
    calendar_name: str = ""
    csv_file: str = ""
    email_column: str = "Email"
    event_duration: float = Field(default=1.0, ge=0.25, le=24 * 7)
    club_name: str = ""
    custom_emails: str = ""
    more_info_link: str = ""
    mention_everyone: bool = True

    # -- coercion ---------------------------------------------------------

    @field_validator(
        "event_name", "description", "image", "server_name", "channel_name",
        "server_id", "channel_id", "meeting_link", "event_date", "event_time", "calendar_name", "csv_file",
        "email_column", "club_name", "custom_emails", "more_info_link",
        mode="before",
    )
    @classmethod
    def _strip_strings(cls, value: Any) -> str:
        if value is None:
            return ""
        return str(value).strip()

    @field_validator("channel_name", mode="after")
    @classmethod
    def _strip_hash(cls, value: str) -> str:
        # People copy "#announcements" from Discord; the API wants "announcements".
        return value.lstrip("#").strip()

    @field_validator("event_duration", mode="before")
    @classmethod
    def _coerce_duration(cls, value: Any) -> float:
        # The HTML number input sends a string; an empty box means "default".
        if value is None or (isinstance(value, str) and not value.strip()):
            return 1.0
        try:
            return float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError("Duration must be a number of hours, e.g. 1.5") from exc

    @field_validator("timezone", mode="before")
    @classmethod
    def _normalize_tz(cls, value: Any) -> str:
        return normalize_timezone(value)

    @field_validator("mention_everyone", mode="before")
    @classmethod
    def _coerce_bool(cls, value: Any) -> bool:
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "on"}
        return bool(value)

    # -- derived values ---------------------------------------------------

    def start_datetime(self) -> datetime:
        """Timezone-aware start of the event. Raises ValueError if date/time are malformed."""
        try:
            naive = datetime.strptime(f"{self.event_date} {self.event_time}", "%Y-%m-%d %H:%M")
        except ValueError as exc:
            raise ValueError(
                "Event date must be YYYY-MM-DD and time must be HH:MM (24-hour)."
            ) from exc
        return naive.replace(tzinfo=ZoneInfo(self.timezone))

    def end_datetime(self) -> datetime:
        return self.start_datetime() + timedelta(hours=self.event_duration)

    def custom_email_names(self) -> list[str]:
        return [name.strip() for name in self.custom_emails.split(",") if name.strip()]

    def template_context(self) -> dict[str, Any]:
        """Values available as ``{placeholders}`` in custom email templates."""
        data = self.model_dump()
        # Keep the old key working for anyone with existing templates.
        data["custom emails list"] = self.custom_emails
        try:
            start = self.start_datetime()
            data["event_date_long"] = start.strftime("%A, %B %d, %Y")
            data["event_time_12h"] = start.strftime("%I:%M %p %Z").lstrip("0")
        except ValueError:
            pass
        return data

    @classmethod
    def from_raw(cls, raw: dict[str, Any] | None) -> "EventDetails":
        """Build from a possibly-old JSON dict, renaming legacy keys."""
        raw = dict(raw or {})
        for old, new in LEGACY_KEYS.items():
            if old in raw and new not in raw:
                raw[new] = raw.pop(old)
            else:
                raw.pop(old, None)
        return cls.model_validate(raw)


# --- Per-action requirements ------------------------------------------------

REQUIRED_FIELDS: dict[str, tuple[str, ...]] = {
    "discord": ("event_name", "description", "server_name", "channel_name",
                "meeting_link", "event_date", "event_time"),
    "calendar": ("event_name", "event_date", "event_time"),
    "email": ("event_name", "club_name", "csv_file", "email_column",
              "event_date", "event_time"),
    "instagram": ("event_name", "image"),
    "custom": ("custom_emails",),
}


def problems_for(action: str, details: EventDetails) -> list[str]:
    """Return human readable reasons why ``action`` cannot run yet.

    Only checks the *event details*; credentials/config are checked by each
    integration's ``preflight`` so this stays free of I/O.
    """
    if action == "all":
        problems: list[str] = []
        for sub in ("discord", "calendar", "email", "instagram", "custom"):
            problems.extend(f"[{sub}] {p}" for p in problems_for(sub, details))
        return problems
    if action not in REQUIRED_FIELDS:
        return [f"Unknown action '{action}'"]

    problems = []
    missing = [FIELD_LABELS.get(f, f) for f in REQUIRED_FIELDS[action]
               if not str(getattr(details, f, "")).strip()]
    if missing:
        problems.append("Missing: " + ", ".join(missing))

    needs_time = any(f in REQUIRED_FIELDS[action] for f in ("event_date", "event_time"))
    if needs_time and details.event_date and details.event_time:
        try:
            details.start_datetime()
        except ValueError as exc:
            problems.append(str(exc))
    return problems
