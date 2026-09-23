import pytest


@pytest.fixture()
def locked_client(data_dir, monkeypatch):
    monkeypatch.setenv("APP_PASSWORD", "hunter2")
    from fastapi.testclient import TestClient

    import backend.main as main

    with TestClient(main.app) as c:
        yield c


def test_protected_routes_need_login(locked_client):
    c = locked_client
    assert c.get("/api/health").status_code == 200
    s = c.get("/api/auth/session").json()
    assert s["auth_required"] is True and s["authenticated"] is False and s["subject"] is None
    assert s["login_methods"]["password"] is True
    assert c.get("/api/details").status_code == 401
    assert c.post("/api/actions/discord").status_code == 401
    assert c.get("/uploads/anything.csv").status_code == 401
    # The UI shell itself is served so the login page can render
    assert c.get("/").status_code == 200


def test_login_sets_cookie_and_logout_clears_it(locked_client):
    c = locked_client
    assert c.post("/api/auth/login", json={"password": "nope"}).status_code == 401
    res = c.post("/api/auth/login", json={"password": "hunter2"})
    assert res.status_code == 200
    assert "sos_session" in res.cookies
    assert c.get("/api/details").status_code == 200
    s = c.get("/api/auth/session").json()
    assert s["authenticated"] is True and s["subject"] == "password"

    c.post("/api/auth/logout")
    assert c.get("/api/details").status_code == 401


def test_forged_cookie_is_rejected(locked_client):
    c = locked_client
    c.cookies.set("sos_session", "0" * 64)
    assert c.get("/api/details").status_code == 401


def test_login_rate_limited(locked_client):
    c = locked_client
    codes = [c.post("/api/auth/login", json={"password": "bad"}).status_code for _ in range(12)]
    assert 429 in codes


def test_session_tokens_are_signed_and_expire(monkeypatch):
    from sawed_off import auth

    token = auth.make_session("alice@example.edu")
    assert auth.parse_session(token) == "alice@example.edu"
    payload, sig = token.rsplit(".", 1)
    assert auth.parse_session(payload + "." + "0" * len(sig)) is None  # bad signature
    assert auth.parse_session("garbage") is None
    monkeypatch.setattr(auth.time, "time", lambda: 10**10)  # far future
    assert auth.parse_session(token) is None  # expired


def test_operator_google_signin(data_dir, monkeypatch):
    """Officers on the list get a session; strangers are refused; removal logs them out."""
    from fastapi.testclient import TestClient

    import backend.main as main
    from sawed_off import operators
    from sawed_off.integrations import google_apis

    operators.save(["officer@club.edu"])
    monkeypatch.setattr(google_apis, "is_configured", lambda: True)
    monkeypatch.setattr(google_apis, "authorization_url", lambda purpose="club": f"https://google/{purpose}")
    outcomes = {}
    monkeypatch.setattr(google_apis, "handle_callback", lambda code, state: outcomes[code])

    with TestClient(main.app) as c:
        s = c.get("/api/auth/session").json()
        assert s["auth_required"] is True  # operators exist, even without APP_PASSWORD
        assert s["login_methods"] == {"password": False, "google": True}
        assert c.get("/api/auth/google").json() == {"auth_url": "https://google/operator"}

        outcomes["stranger"] = {"purpose": "operator", "email": "rando@example.com"}
        res = c.get("/api/auth/callback?code=stranger&state=x", follow_redirects=False)
        assert res.status_code == 307 and "login=denied" in res.headers["location"]
        assert c.get("/api/details").status_code == 401

        outcomes["officer"] = {"purpose": "operator", "email": "Officer@Club.edu"}
        res = c.get("/api/auth/callback?code=officer&state=x", follow_redirects=False)
        assert "login=ok" in res.headers["location"]
        assert c.get("/api/details").status_code == 200
        assert c.get("/api/auth/session").json()["subject"] == "officer@club.edu"

        # Adding/removing officers through the API
        assert c.post("/api/operators", json={"email": "not-an-email"}).status_code == 400
        assert c.post("/api/operators", json={"email": "Second@club.edu"}).json()["operators"] == [
            "officer@club.edu", "second@club.edu"]
        c.delete("/api/operators/officer@club.edu")
        assert c.get("/api/details").status_code == 401  # session invalid immediately


def test_club_google_account_is_always_an_operator(data_dir, monkeypatch):
    import json

    from sawed_off import config, operators

    config.GOOGLE_TOKEN_FILE.write_text(json.dumps({"token": "x", "account_email": "Club@Uni.edu"}))
    assert operators.club_email() == "club@uni.edu"
    assert operators.is_operator("club@uni.edu")
    assert not operators.is_operator("other@uni.edu")
    assert operators.any_configured() is False  # the club email alone does not lock the app
