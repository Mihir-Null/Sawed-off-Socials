import json
import time

import pytest


def test_health_and_session_open_when_no_password(client):
    assert client.get("/api/health").json()["status"] == "ok"
    s = client.get("/api/auth/session").json()
    assert s["auth_required"] is False and s["authenticated"] is True
    assert s["subject"] is None
    assert s["login_methods"] == {"password": False, "google": False}


def test_details_roundtrip_with_coercion(client, sample_details):
    res = client.post("/api/details", json=sample_details)
    assert res.status_code == 200
    saved = res.json()["details"]
    assert saved["event_duration"] == 1.5
    assert saved["timezone"] == "America/New_York"
    assert client.get("/api/details").json()["channel_name"] == "announcements"


def test_details_validation_error_is_readable(client):
    res = client.post("/api/details", json={"timezone": "Nowhere/Land"})
    assert res.status_code == 422
    assert "Unknown timezone" in res.json()["detail"]


def test_upload_sanitizes_name_and_rejects_bad_types(client, data_dir):
    res = client.post("/api/upload", files={"file": ("../../evil.png", b"png", "image/png")})
    assert res.status_code == 200
    assert res.json()["filename"] == "evil.png"
    assert (data_dir / "uploads" / "evil.png").read_bytes() == b"png"

    res = client.post("/api/upload", files={"file": ("x.exe", b"MZ", "application/octet-stream")})
    assert res.status_code == 400

    # Same name twice keeps both files
    res = client.post("/api/upload", files={"file": ("evil.png", b"png2", "image/png")})
    assert res.json()["filename"] != "evil.png"


def test_action_preflight_blocks_run(client, sample_details):
    client.post("/api/details", json=sample_details)
    check = client.get("/api/actions/discord/check").json()
    assert check["ok"] is False
    assert any("DISCORD_BOT_TOKEN" in p for p in check["problems"])

    res = client.post("/api/actions/discord")
    assert res.status_code == 400
    assert res.json()["detail"]["problems"] == check["problems"]

    assert client.post("/api/actions/nope").status_code == 404


def test_action_runs_as_background_job(client, sample_details, monkeypatch):
    from sawed_off import actions

    def fake_run(action, details):
        import logging
        logging.getLogger("test").info("hello from %s", action)
        time.sleep(0.2)
        return {"ok": action}

    monkeypatch.setattr(actions, "run_action", fake_run)
    monkeypatch.setattr(actions, "preflight", lambda action, details: [])
    monkeypatch.setenv("DISCORD_BOT_TOKEN", "x")

    res = client.post("/api/actions/discord")
    assert res.status_code == 202
    job = res.json()["job"]
    assert job["status"] == "running"

    # a second job while one is running is refused
    assert client.post("/api/actions/calendar").status_code == 409

    for _ in range(50):
        job = client.get(f"/api/jobs/{job['id']}").json()["job"]
        if job["done"]:
            break
        time.sleep(0.05)
    assert job["status"] == "succeeded"
    assert job["result"] == {"ok": "discord"}
    assert any("hello from discord" in line for line in job["log"])
    assert any("hello from discord" in line for line in client.get("/api/logs").json()["logs"])


def test_failed_job_reports_error(client, monkeypatch):
    from sawed_off import actions

    def boom(action, details):
        raise ValueError("Bot is not in a server named 'x'")

    monkeypatch.setattr(actions, "run_action", boom)
    monkeypatch.setattr(actions, "preflight", lambda action, details: [])
    job = client.post("/api/actions/discord").json()["job"]
    for _ in range(50):
        job = client.get(f"/api/jobs/{job['id']}").json()["job"]
        if job["done"]:
            break
        time.sleep(0.05)
    assert job["status"] == "failed"
    assert "Bot is not in a server" in job["error"]


def test_custom_emails_listing(client, data_dir):
    (data_dir / "custom_emails.json").write_text(json.dumps({
        "room": {"email": "rooms@example.edu", "subject": "s", "body": "b"}
    }))
    res = client.get("/api/custom-emails").json()
    assert res["names"] == ["room"]
    assert res["templates"]["room"]["email"] == "rooms@example.edu"

    (data_dir / "custom_emails.json").write_text(json.dumps({"bad": {"email": "x"}}))
    res = client.get("/api/custom-emails").json()
    assert res["names"] == [] and "needs 'email', 'subject' and 'body'" in res["error"]


def test_google_callback_without_code_redirects(client):
    res = client.get("/api/auth/callback?error=access_denied", follow_redirects=False)
    assert res.status_code == 307
    assert "google=error" in res.headers["location"]


@pytest.mark.usefixtures("data_dir")
def test_legacy_files_are_migrated(tmp_path, monkeypatch):
    from sawed_off import config

    legacy_root = tmp_path / "legacy"
    legacy_root.mkdir()
    (legacy_root / "event_details.json").write_text(json.dumps({"event_name": "old"}))
    (legacy_root / "uploads").mkdir()
    (legacy_root / "uploads" / "pic.png").write_bytes(b"x")
    monkeypatch.setattr(config, "BASE_DIR", legacy_root)
    monkeypatch.chdir(tmp_path)  # the CWD fallback must not see the real repo

    moved = config.migrate_legacy_files()
    assert len(moved) == 2
    assert json.loads(config.EVENT_DETAILS_FILE.read_text())["event_name"] == "old"
    assert (config.UPLOAD_DIR / "pic.png").exists()
    assert config.migrate_legacy_files() == []  # idempotent


def test_run_all_skips_unready_steps(client, sample_details, monkeypatch):
    """'all' runs what it can; unfilled steps are skipped, not fatal."""
    from sawed_off import actions

    monkeypatch.setenv("DISCORD_BOT_TOKEN", "x")
    monkeypatch.setattr(actions, "RUNNERS", {**actions.RUNNERS, "discord": lambda d: {"event_url": "https://discord/e"}})
    client.post("/api/details", json=sample_details)  # discord fields filled, nothing else

    assert client.get("/api/actions/all/check").json()["ok"] is True
    job = client.post("/api/actions/all").json()["job"]
    for _ in range(50):
        job = client.get(f"/api/jobs/{job['id']}").json()["job"]
        if job["done"]:
            break
        time.sleep(0.05)
    assert job["status"] == "succeeded"
    assert job["result"]["discord"] == {"event_url": "https://discord/e"}
    assert "skipped" in job["result"]["instagram"]
    assert "skipped" in job["result"]["email"]


def test_run_all_blocked_when_nothing_ready(client):
    check = client.get("/api/actions/all/check").json()
    assert check["ok"] is False
    assert check["problems"][0] == "Nothing is ready to run:"
    assert client.post("/api/actions/all").status_code == 400
