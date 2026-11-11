"""The idle watcher: exit once the last page goes away, never while one is busy."""
import time
from types import SimpleNamespace

import pytest

from story_architect.app import server


def _app(last_heartbeat, busy=False):
    return SimpleNamespace(state=SimpleNamespace(
        last_heartbeat=last_heartbeat, active_replies={"c": object()} if busy else {}))


def test_a_fresh_heartbeat_keeps_the_server():
    now = time.time()
    assert server._tick(_app(now), now) is False


def test_a_stale_heartbeat_lets_it_exit():
    now = time.time()
    assert server._tick(_app(now - server.IDLE_EXIT_SECONDS - 1), now) is True


def test_a_streaming_reply_refreshes_the_clock():
    now = time.time()
    app = _app(now - server.IDLE_EXIT_SECONDS - 1, busy=True)
    assert server._tick(app, now) is False
    assert app.state.last_heartbeat == now


@pytest.fixture
def client(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from story_architect.app.config import Config
    from story_architect.app.server import create_app
    monkeypatch.setattr("story_architect.app.token.load_api_key", lambda: "k")
    root = tmp_path / "root"
    (root / ".story").mkdir(parents=True)
    c = TestClient(create_app(Config(root=root)), base_url="http://127.0.0.1:8731")
    c.headers.update({"X-Story-Architect": "1"})
    return c


def test_the_page_ping_marks_it_present(client):
    client.app.state.last_heartbeat = 0
    assert client.get("/api/heartbeat").status_code == 200
    assert client.app.state.last_heartbeat > 0
