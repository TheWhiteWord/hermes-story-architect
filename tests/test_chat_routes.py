import os
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from story_architect.app.server import create_app
from story_architect.app.config import Config
from story_architect.chat import store
from story_architect.chat.service import ChatService
from story_architect.chat.fake_backend import FakeBackend


def _proj(tmp):
    p = Path(tmp) / "proj"
    (p / ".story").mkdir(parents=True)
    (p / "project.md").write_text("---\nname: Test\n---\n")
    return p


@pytest.fixture
def client(tmp_path, monkeypatch):
    # ensure API key present
    monkeypatch.setattr("story_architect.app.token.load_api_key", lambda: "fake-key")
    root = tmp_path / "root"
    root.mkdir()
    cfg = Config(root=root, port=8731)
    app = create_app(cfg)
    # create a project on disk so resolve works
    proj = _proj(tmp_path)
    # register project in root? resolve_project expects slug under root/projects maybe. Check.
    # We'll instead monkeypatch resolve by creating under root/projects/<slug>
    slug = "testproj"
    (root / "projects" / slug).mkdir(parents=True, exist_ok=True)
    import shutil
    for f in proj.iterdir():
        if f.is_dir():
            shutil.copytree(f, root / "projects" / slug / f.name, dirs_exist_ok=True)
        else:
            shutil.copy2(f, root / "projects" / slug / f.name)
    app.state.chat_service = ChatService(FakeBackend(replies=["hi"]))
    return TestClient(app, base_url="http://127.0.0.1:8731"), slug, root / "projects" / slug


def test_messages_streams_text_done(client):
    tc, slug, pp = client
    r = tc.post(f"/api/projects/{slug}/messages", json={"text": "hello"}, headers={"X-Story-Architect": "1", "Origin": "http://127.0.0.1:8731"})
    assert r.status_code == 200
    assert "text" in r.text and "done" in r.text


def test_missing_header_rejected(client):
    tc, slug, pp = client
    r = tc.post(f"/api/projects/{slug}/messages", json={"text": "hello"}, headers={"Origin": "http://127.0.0.1:8731"})
    assert r.status_code == 403


def test_foreign_origin_rejected(client):
    tc, slug, pp = client
    r = tc.post(f"/api/projects/{slug}/messages", json={"text": "hello"}, headers={"X-Story-Architect": "1", "Origin": "http://evil.com"})
    assert r.status_code == 403


def test_missing_key_503(tmp_path, monkeypatch):
    monkeypatch.setattr("story_architect.app.token.load_api_key", lambda: None)
    root = tmp_path / "root"
    root.mkdir()
    cfg = Config(root=root, port=8731)
    app = create_app(cfg)
    slug = "p"
    (root / "projects" / slug).mkdir(parents=True, exist_ok=True)
    (root / "projects" / slug / ".story").mkdir(exist_ok=True)
    tc = TestClient(app, base_url="http://127.0.0.1:8731")
    r = tc.post(f"/api/projects/{slug}/messages", json={"text": "hi"}, headers={"X-Story-Architect": "1"})
    assert r.status_code == 503
