"""HTTP surface of the script editor, including the middleware it must sit behind."""
import pytest
from fastapi.testclient import TestClient

from story_architect.app.config import Config
from story_architect.app.server import create_app
from story_architect.core.writes import create_entity, edit_entity

H = {"X-Story-Architect": "1"}


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr("story_architect.app.token.load_api_key", lambda: "k")
    root = tmp_path / "root"
    proj = root / "projects" / "demo"
    (proj / ".story").mkdir(parents=True)
    create_entity(proj, "act", "act-1", {"title": "A"})
    create_entity(proj, "sequence", "seq-1", {"title": "S", "act_id": "act-1"})
    create_entity(proj, "world", "w", {"name": "W", "one_sentence": "T"})
    create_entity(proj, "location", "kitchen", {"name": "Kitchen", "one_sentence": "T", "world": "w"})
    create_entity(proj, "scene", "s1", {"title": "S1", "sequence_id": "seq-1", "act_id": "act-1", "order": 1,
                                        "location": "kitchen", "time_of_day": "NIGHT"},
                  sections={"Content": "INT. KITCHEN - NIGHT\n\nRain.\n"})
    tc = TestClient(create_app(Config(root=root, port=8731)), base_url="http://127.0.0.1:8731")
    return tc, proj


def _body(s, **over):
    b = {"base_hash": s["hash"], "blocks": s["blocks"],
         "heading": {"mode": "structured", "int_ext": "INT.", "location": "kitchen", "time_of_day": "NIGHT"},
         "extra_cast": []}
    b.update(over)
    return b


def test_get_then_put_round_trip(client):
    tc, _ = client
    s = tc.get("/api/projects/demo/scenes/s1/script").json()
    assert s["heading"]["location"] == "kitchen" and s["blocks"][0]["text"] == "Rain."
    r = tc.put("/api/projects/demo/scenes/s1/script", headers=H,
               json=_body(s, blocks=[{"type": "action", "text": "Heavy rain."}]))
    assert r.status_code == 200 and "Heavy rain." in r.json()["content"]


def test_write_needs_the_custom_header(client):
    """The one browser write path is behind the same middleware as the rest."""
    tc, _ = client
    s = tc.get("/api/projects/demo/scenes/s1/script").json()
    assert tc.put("/api/projects/demo/scenes/s1/script", json=_body(s)).status_code == 403


def test_foreign_origin_is_refused(client):
    tc, _ = client
    s = tc.get("/api/projects/demo/scenes/s1/script").json()
    r = tc.put("/api/projects/demo/scenes/s1/script", json=_body(s),
               headers={**H, "Origin": "http://evil.example"})
    assert r.status_code == 403


def test_conflict_is_409_with_the_current_hash(client):
    tc, proj = client
    s = tc.get("/api/projects/demo/scenes/s1/script").json()
    edit_entity(proj, "scene", "s1", {"Content": "INT. KITCHEN - NIGHT\n\nAgent.\n"}, "agent")
    r = tc.put("/api/projects/demo/scenes/s1/script", headers=H, json=_body(s))
    assert r.status_code == 409
    err = r.json()["error"]
    assert err["code"] == "conflict" and err["current_hash"] != s["hash"]


@pytest.mark.parametrize("path,status", [
    ("/api/projects/demo/scenes/nope/script", 404),
    ("/api/projects/ghost/scenes/s1/script", 404),
])
def test_missing_things_are_404(client, path, status):
    tc, _ = client
    assert tc.get(path).status_code == status


def test_locked_is_423_and_invalid_is_422(client):
    tc, proj = client
    s = tc.get("/api/projects/demo/scenes/s1/script").json()
    bad = tc.put("/api/projects/demo/scenes/s1/script", headers=H,
                 json=_body(s, heading={"mode": "structured", "int_ext": "INT.", "location": "ghost"}))
    assert bad.status_code == 422
    edit_entity(proj, "scene", "s1", {"status": "locked"}, "lock")
    s = tc.get("/api/projects/demo/scenes/s1/script").json()
    assert tc.put("/api/projects/demo/scenes/s1/script", headers=H, json=_body(s)).status_code == 423


def test_parse_pasted_text(client):
    tc, _ = client
    r = tc.post("/api/projects/demo/script/parse", headers=H,
                json={"text": "MARA\nHi.\n\nShe leaves."}).json()
    assert [b["type"] for b in r["blocks"]] == ["character", "dialogue", "action"]
    assert tc.post("/api/projects/demo/script/parse", headers=H, json={"text": 5}).status_code == 422


def test_check_route_is_a_pure_read(client):
    tc, _ = client
    s = tc.get("/api/projects/demo/scenes/s1/script").json()
    r = tc.post("/api/projects/demo/scenes/s1/script/check", headers=H, json={
        "blocks": [{"type": "character", "text": "ZED"}, {"type": "dialogue", "text": "x"}],
        "heading": {"mode": "structured", "int_ext": "INT.", "location": "kitchen", "time_of_day": "NIGHT"}})
    assert r.status_code == 200
    assert any(f["code"] == "character_unregistered" for f in r.json()["findings"])
    assert tc.get("/api/projects/demo/scenes/s1/script").json()["hash"] == s["hash"]
    assert tc.post("/api/projects/demo/scenes/nope/script/check", headers=H,
                   json={"blocks": []}).status_code == 404
