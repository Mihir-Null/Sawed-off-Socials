"""Shared fixtures.

Every test gets a fresh, empty data directory so nothing touches the real
``data/`` folder, and environment variables are reset between tests.
"""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest


@pytest.fixture()
def data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point ``sawed_off.config`` at a temp directory and reload dependants."""
    monkeypatch.setenv("SOS_DATA_DIR", str(tmp_path / "data"))
    for var in ("APP_PASSWORD", "DISCORD_BOT_TOKEN", "GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET",
                "INSTAGRAM_ACCESS_TOKEN", "INSTAGRAM_USER_ID", "CLOUDINARY_CLOUD_NAME",
                "CLOUDINARY_API_KEY", "CLOUDINARY_API_SECRET", "SOS_SECRET_KEY"):
        monkeypatch.delenv(var, raising=False)
    from sawed_off import config

    importlib.reload(config)
    config.ensure_data_dirs()
    return config.DATA_DIR


@pytest.fixture()
def client(data_dir: Path, monkeypatch: pytest.MonkeyPatch):
    """A TestClient for the FastAPI app bound to the temp data directory."""
    from fastapi.testclient import TestClient

    import backend.main as main
    from sawed_off import config

    # Modules cache path constants at import; patch the ones the app uses.
    monkeypatch.setattr(main.config, "DATA_DIR", config.DATA_DIR)
    monkeypatch.setattr(main.config, "UPLOAD_DIR", config.UPLOAD_DIR)
    monkeypatch.setattr(main.config, "EVENT_DETAILS_FILE", config.EVENT_DETAILS_FILE)
    monkeypatch.setattr(main.config, "CUSTOM_EMAILS_FILE", config.CUSTOM_EMAILS_FILE)
    monkeypatch.setattr(main.config, "GOOGLE_TOKEN_FILE", config.GOOGLE_TOKEN_FILE)
    with TestClient(main.app) as c:
        yield c


@pytest.fixture()
def sample_details() -> dict:
    return {
        "event_name": "General Body Meeting",
        "description": "Come learn about quantum computing.",
        "server_name": "My Club",
        "channel_name": "#announcements",
        "meeting_link": "Room 101",
        "event_date": "2099-03-04",
        "event_time": "18:00",
        "timezone": "EST",
        "event_duration": "1.5",
        "club_name": "Quantum Club",
        "email_column": "Email",
    }
