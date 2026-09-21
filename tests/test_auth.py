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
    assert c.get("/api/auth/session").json() == {"auth_required": True, "authenticated": False, "version": c.get("/api/auth/session").json()["version"]}
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
    assert c.get("/api/auth/session").json()["authenticated"] is True

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
