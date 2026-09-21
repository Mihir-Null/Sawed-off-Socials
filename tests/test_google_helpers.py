from pathlib import Path

import pytest

from sawed_off.integrations.google_apis import build_event_email, read_recipients, render_template
from sawed_off.models import EventDetails


def test_read_recipients_handles_bom_case_and_duplicates(tmp_path: Path):
    csv = tmp_path / "roster.csv"
    # utf-8-sig writes a BOM like Google Sheets / Excel exports do
    csv.write_text(
        "Name,Campus Email\n"
        "A,alice@umd.edu\n"
        "B, Bob@umd.edu \n"
        "C,alice@UMD.edu\n"
        "D,not-an-email\n"
        "E,\n"
        "F,\"carol@umd.edu; dan@umd.edu\"\n",
        encoding="utf-8-sig",
    )
    assert read_recipients(csv, "campus email") == ["alice@umd.edu", "Bob@umd.edu", "carol@umd.edu", "dan@umd.edu"]


def test_read_recipients_missing_column_lists_headers(tmp_path: Path):
    csv = tmp_path / "roster.csv"
    csv.write_text("Name,Email\nA,a@b.co\n")
    with pytest.raises(ValueError, match="Columns are: Name, Email"):
        read_recipients(csv, "Campus Email")


def test_read_recipients_missing_file(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        read_recipients(tmp_path / "nope.csv", "Email")


def test_render_template_is_forgiving():
    ctx = {"club_name": "UQA", "event_name": "GBM"}
    assert render_template("{club_name}: {event_name}", ctx) == "UQA: GBM"
    # unknown placeholder is left alone instead of raising KeyError
    assert render_template("Hi {nobody}", ctx) == "Hi {nobody}"
    # stray braces (e.g. JSON in the body) don't crash
    assert render_template("{ not a field", ctx) == "{ not a field"


def test_build_event_email(sample_details):
    d = EventDetails.from_raw({**sample_details, "more_info_link": "https://linktr.ee/x"})
    subject, body = build_event_email(d)
    assert subject == "Quantum Club Event: General Body Meeting"
    assert "Wednesday, March 04, 2099" in body
    assert "6:00 PM EST" in body
    assert "https://linktr.ee/x" in body
