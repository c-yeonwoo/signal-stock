import importlib

from fastapi.testclient import TestClient


def _fresh_client(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from signal_desk import db as db_module
    importlib.reload(db_module)
    from signal_desk import api as api_module
    importlib.reload(api_module)
    return TestClient(api_module.app)


def test_index_served(tmp_path, monkeypatch):
    client = _fresh_client(tmp_path, monkeypatch)
    r = client.get("/")
    assert r.status_code == 200
    assert "Signal Desk" in r.text


def test_api_requires_auth(tmp_path, monkeypatch):
    client = _fresh_client(tmp_path, monkeypatch)
    r = client.get("/api/signals")
    assert r.status_code == 401


def test_signup_login_profile_flow(tmp_path, monkeypatch):
    client = _fresh_client(tmp_path, monkeypatch)
    r = client.post("/api/auth/signup", json={"email": "a@b.com", "pw": "abcdef"})
    assert r.status_code == 200 and r.json()["ok"]

    r = client.get("/api/auth/me")
    assert r.status_code == 200
    assert r.json()["auth"] is True

    r = client.put("/api/profile", json={"투자성향": "balanced"})
    assert r.status_code == 200

    r = client.get("/api/profile")
    assert r.json()["투자성향"] == "balanced"

    r = client.post("/api/favorites", json={"kind": "ticker", "key": "005930", "label": ""})
    assert r.status_code == 200
    r = client.get("/api/favorites")
    assert {"kind": "ticker", "key": "005930", "label": ""} in r.json()["favorites"]

    r = client.get("/api/signals")
    assert r.status_code == 200
    assert r.json() == {"ready": False, "items": []}
