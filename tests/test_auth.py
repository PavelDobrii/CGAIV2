import importlib
import os
from pathlib import Path

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient


def _get_app(monkeypatch):
    monkeypatch.setenv("API_USERNAME", "alice")
    monkeypatch.setenv("API_PASSWORD", "secret")
    import orchestrator.main as main
    importlib.reload(main)
    monkeypatch.setattr(main, "run_story", lambda **kwargs: (Path("story.md"), Path("story.mp3")))
    return main.app


def test_login_success(monkeypatch):
    app = _get_app(monkeypatch)
    client = TestClient(app)
    resp = client.post("/login", json={"username": "alice", "password": "secret"})
    assert resp.status_code == 200
    assert "token" in resp.json()


def test_login_failure(monkeypatch):
    app = _get_app(monkeypatch)
    client = TestClient(app)
    resp = client.post("/login", json={"username": "alice", "password": "bad"})
    assert resp.status_code == 401


def test_story_requires_token(monkeypatch):
    app = _get_app(monkeypatch)
    client = TestClient(app)
    login = client.post("/login", json={"username": "alice", "password": "secret"})
    token = login.json()["token"]
    resp = client.post(
        "/story",
        json={"prompt": "p", "language": "en", "style": "fun"},
        headers={"X-Token": token},
    )
    assert resp.status_code == 200

    resp2 = client.post(
        "/story",
        json={"prompt": "p", "language": "en", "style": "fun"},
        headers={"X-Token": "wrong"},
    )
    assert resp2.status_code == 401
