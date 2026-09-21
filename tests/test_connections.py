"""Instagram OAuth/refresh, Discord REST helpers, public file links and the
connections endpoint, all with the network mocked out."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest


class FakeResponse:
    def __init__(self, payload, status=200):
        self._payload, self.status_code, self.ok = payload, status, status < 400
        self.text = json.dumps(payload)

    def json(self):
        return self._payload


@pytest.fixture()
def ig_env(data_dir, monkeypatch):
    monkeypatch.setenv("INSTAGRAM_APP_ID", "app123")
    monkeypatch.setenv("INSTAGRAM_APP_SECRET", "shh")
    monkeypatch.setenv("SOS_PUBLIC_URL", "https://socials.club.edu")
    from sawed_off.integrations import instagram_api

    return instagram_api


def test_instagram_authorization_url_and_callback(ig_env, monkeypatch):
    ig = ig_env
    url = ig.authorization_url()
    assert url.startswith("https://www.instagram.com/oauth/authorize?")
    assert "client_id=app123" in url and "instagram_business_content_publish" in url
    state = url.split("state=")[1].split("&")[0]

    calls = []

    def fake_post(url, data=None, timeout=None):
        calls.append(("POST", url, data))
        return FakeResponse({"data": [{"access_token": "short", "user_id": 42}]})

    def fake_get(url, params=None, timeout=None):
        calls.append(("GET", url, params))
        if url.endswith("/access_token"):
            return FakeResponse({"access_token": "long", "expires_in": 5184000})
        if url.endswith("/me"):
            return FakeResponse({"user_id": "42", "username": "quantumclub"})
        raise AssertionError(url)

    monkeypatch.setattr(ig.requests, "post", fake_post)
    monkeypatch.setattr(ig.requests, "get", fake_get)

    with pytest.raises(ValueError, match="state mismatch"):
        ig.handle_callback("code#_", "wrong")
    status = ig.handle_callback("code#_", state)
    assert status["connected"] and status["username"] == "quantumclub" and status["source"] == "oauth"
    assert calls[0][2]["code"] == "code"  # '#_' suffix stripped
    creds = ig.credentials()
    assert (creds.token, creds.user_id, creds.graph_base, creds.source) == ("long", "42", ig.IG_GRAPH, "oauth")


def test_instagram_refresh_only_when_old_and_expiring(ig_env, monkeypatch):
    ig = ig_env
    now = datetime.now(timezone.utc)
    record = {"access_token": "t1", "user_id": "42", "username": "x",
              "obtained_at": (now - timedelta(days=45)).isoformat(),
              "expires_at": (now + timedelta(days=15)).isoformat()}
    ig._save_record(record)
    monkeypatch.setattr(ig.requests, "get", lambda url, params=None, timeout=None: FakeResponse(
        {"access_token": "t2", "expires_in": 5184000}))
    assert ig.credentials().token == "t2"  # refreshed: old enough and expiring soon

    fresh = {**record, "obtained_at": now.isoformat(), "expires_at": (now + timedelta(days=60)).isoformat()}
    ig._save_record(fresh)
    monkeypatch.setattr(ig.requests, "get", lambda *a, **k: (_ for _ in ()).throw(AssertionError("no refresh")))
    assert ig.credentials().token == "t1"

    expired = {**record, "expires_at": (now - timedelta(days=1)).isoformat()}
    ig._save_record(expired)
    with pytest.raises(ValueError, match="expired"):
        ig.credentials()
    assert ig.connection_status()["ok"] is False


def test_instagram_env_fallback_and_hosting(ig_env, monkeypatch):
    ig = ig_env
    with pytest.raises(ValueError, match="not connected"):
        ig.credentials()
    monkeypatch.setenv("INSTAGRAM_ACCESS_TOKEN", "fb")
    monkeypatch.setenv("INSTAGRAM_USER_ID", "7")
    creds = ig.credentials()
    assert creds.graph_base == ig.FB_GRAPH and creds.source == "env"
    assert ig.image_hosting() == "self"  # https public URL, no Cloudinary
    monkeypatch.setenv("SOS_PUBLIC_URL", "http://localhost:8000")
    assert ig.image_hosting() == "none"


def test_public_file_links(data_dir, monkeypatch, client):
    from sawed_off import publicfiles

    img = data_dir / "uploads" / "pic.png"
    img.write_bytes(b"\x89PNG")
    monkeypatch.setenv("SOS_PUBLIC_URL", "http://localhost:8000")
    with pytest.raises(ValueError):
        publicfiles.publish(img)
    monkeypatch.setenv("SOS_PUBLIC_URL", "https://socials.club.edu")
    url = publicfiles.publish(img)
    assert url.startswith("https://socials.club.edu/public/") and url.endswith(".png")
    token = url.rsplit("/", 1)[1]
    assert client.get(f"/public/{token}").content == b"\x89PNG"
    assert client.get("/public/nope.png").status_code == 404


def test_discord_rest_helpers(data_dir, monkeypatch):
    from sawed_off.integrations import discord_bot as d

    assert d.connection_status()["app_configured"] is False
    monkeypatch.setenv("DISCORD_BOT_TOKEN", "tok")

    def fake_get(url, headers=None, timeout=None):
        assert headers == {"Authorization": "Bot tok"}
        if url.endswith("/oauth2/applications/@me"):
            return FakeResponse({"id": "999", "name": "Jack", "bot": {"username": "AdminJack"}})
        if url.endswith("/users/@me/guilds"):
            return FakeResponse([{"id": "1", "name": "Quantum Club"}])
        if url.endswith("/guilds/1/channels"):
            return FakeResponse([
                {"id": "10", "name": "general", "type": 0, "position": 1},
                {"id": "11", "name": "voice", "type": 2, "position": 0},
                {"id": "12", "name": "announcements", "type": 5, "position": 0},
            ])
        raise AssertionError(url)

    monkeypatch.setattr(d.requests, "get", fake_get)
    status = d.connection_status(verify=True)
    assert status["bot_name"] == "AdminJack" and status["guilds"] == [{"id": "1", "name": "Quantum Club"}]
    assert status["invite_url"] == f"https://discord.com/oauth2/authorize?client_id=999&scope=bot&permissions={d.INVITE_PERMISSIONS}"
    assert d.list_text_channels("1") == [{"id": "12", "name": "announcements"}, {"id": "10", "name": "general"}]

    monkeypatch.setattr(d.requests, "get", lambda *a, **k: FakeResponse({"message": "401: Unauthorized"}, 401))
    with pytest.raises(ValueError, match="rejected the bot token"):
        d.list_guilds()


def test_connections_endpoint(client, monkeypatch):
    res = client.get("/api/connections").json()
    assert set(res) >= {"google", "instagram", "discord", "operators", "club_email", "public_url"}
    assert res["google"]["logged_in"] is False
    assert res["instagram"]["connected"] is False and res["instagram"]["app_configured"] is False
    assert res["discord"]["app_configured"] is False

    assert client.get("/api/discord/servers").status_code == 400  # no token configured
    assert client.get("/api/instagram/login").status_code == 400
    res = client.get("/api/instagram/callback?error=access_denied", follow_redirects=False)
    assert res.status_code == 307 and "instagram=error" in res.headers["location"]
