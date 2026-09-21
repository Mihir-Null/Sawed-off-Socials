from datetime import timedelta

import pytest

from sawed_off.config import normalize_timezone
from sawed_off.models import EventDetails, problems_for


def test_timezone_aliases_and_validation():
    assert normalize_timezone("EST") == "America/New_York"
    assert normalize_timezone("pst") == "America/Los_Angeles"
    assert normalize_timezone("Europe/Paris") == "Europe/Paris"
    assert normalize_timezone("") == "UTC"
    assert normalize_timezone(None) == "UTC"
    with pytest.raises(ValueError, match="Unknown timezone"):
        normalize_timezone("Mars/Olympus")


def test_details_coercion(sample_details):
    d = EventDetails.from_raw(sample_details)
    assert d.event_duration == 1.5  # "1.5" string -> float
    assert d.timezone == "America/New_York"  # EST -> IANA
    assert d.channel_name == "announcements"  # leading '#' stripped
    start = d.start_datetime()
    assert start.tzinfo is not None
    assert d.end_datetime() - start == timedelta(hours=1.5)


def test_empty_duration_defaults_and_bad_duration_rejected():
    assert EventDetails.from_raw({"event_duration": ""}).event_duration == 1.0
    with pytest.raises(ValueError):
        EventDetails.from_raw({"event_duration": "an hour"})


def test_legacy_key_renamed_and_extra_keys_kept():
    d = EventDetails.from_raw({"custom emails list": "a, b", "website": "https://x"})
    assert d.custom_emails == "a, b"
    assert d.custom_email_names() == ["a", "b"]
    assert d.model_dump()["website"] == "https://x"
    assert "custom emails list" not in d.model_dump()
    # ...but templates written against the old name still work
    assert d.template_context()["custom emails list"] == "a, b"


def test_problems_for_reports_missing_fields_with_labels():
    d = EventDetails.from_raw({"event_name": "x"})
    problems = problems_for("discord", d)
    assert len(problems) == 1
    assert problems[0].startswith("Missing: ")
    assert "Discord server" in problems[0]
    assert "Event date" in problems[0]


def test_problems_for_bad_date_format():
    d = EventDetails.from_raw({"event_name": "x", "event_date": "03/04/2099", "event_time": "6pm"})
    problems = problems_for("calendar", d)
    assert any("YYYY-MM-DD" in p for p in problems)


def test_problems_for_all_prefixes_each_step(sample_details):
    d = EventDetails.from_raw(sample_details)
    problems = problems_for("all", d)
    assert any(p.startswith("[email]") for p in problems)  # csv_file missing
    assert any(p.startswith("[instagram]") for p in problems)  # image missing
    assert not any(p.startswith("[discord]") for p in problems)
