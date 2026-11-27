"""The history API: `/api/projects/{slug}/history/`.

What is asserted here is the HTTP contract, not the merge rules — those live in
`core/history` and are tested there. So: the exact-slug rule, the confirm rule,
one error envelope, and the paths that make the workspace usable end to end.
"""

import shutil

import pytest
from fastapi.testclient import TestClient

from white_words.scriptwriting.app.config import Config
from white_words.scriptwriting.app.server import create_app
from white_words.scriptwriting.core.history import store
from white_words.scriptwriting.core.writes import edit_entity

SLUG = "save-the-children"
HDR = {"X-White-Words": "1", "Origin": "http://127.0.0.1:8731"}
NAME = "field:character:kael:name"


def _conflict(project):
    """`main` and `side` both changed kael's name; the `side` draft id comes back.

    The branch is created before either edit, because a draft frozen on `side` is
    what gives the merge a common ancestor to compare against.
    """
    store.adopt(project)
    base = store.head_state(project)["branch"]["base_snapshot_id"]
    branch = store.branch_from(project, base, "side")
    store.switch(project, branch["id"])
    edit_entity(project, "character", "kael", {"name": "Kael Theirs"}, "theirs")
    theirs = store.save_snapshot(project, "Theirs")["id"]
    store.switch(project, "main")
    edit_entity(project, "character", "kael", {"name": "Kael Ours"}, "ours")
    return theirs


def _merge(tc, project, selection=None):
    theirs = _conflict(project)
    return tc.post(
        f"/api/projects/{SLUG}/history/merges",
        json={
            "target": store.get_branch(project)["id"],
            "source": {"kind": "snapshot", "id": theirs},
            "selection": selection,
        },
        headers=HDR,
    )


@pytest.fixture
def client(fixture_path, tmp_path):
    root = tmp_path / "root"
    (root / "projects").mkdir(parents=True)
    project = root / "projects" / SLUG
    shutil.copytree(str(fixture_path), str(project))
    # A neighbouring project whose slug shares a prefix: the fuzzy resolver would
    # happily answer for it, which is exactly what an exact slug must not do.
    shutil.copytree(str(fixture_path), str(root / "projects" / (SLUG + "-old")))
    tc = TestClient(create_app(Config(root=root, port=8731)), base_url="http://127.0.0.1:8731")
    return tc, project


def _history(tc, slug=SLUG, **params):
    return tc.get(f"/api/projects/{slug}/history/", params=params, headers=HDR)


def test_the_graph_lists_branches_and_their_tips(client):
    tc, project = client
    store.adopt(project)

    body = _history(tc).json()

    assert body["current"]
    [branch] = body["branches"]
    assert branch["is_current"] is True
    assert branch["base_snapshot_id"]
    tip = body["head"][branch["id"]]
    assert tip["changed"] is False and tip["changes"] == 0
    assert tip["draft"]["label"] == "Draft 1"


def test_the_graph_counts_unsaved_changes_in_the_tip(client):
    tc, project = client
    store.adopt(project)
    edit_entity(project, "character", "kael", {"name": "Kael Renamed"}, "probe")

    tip = _history(tc).json()["head"][_history(tc).json()["current"]]

    assert tip["changed"] is True and tip["changes"] == 1


def test_a_project_with_no_history_shows_an_empty_graph_and_writes_nothing(client):
    tc, project = client

    body = _history(tc).json()

    assert body == {"branches": [], "snapshots": [], "current": None, "picked_from": []}
    assert not store.history_path(project).exists()


def test_a_slug_that_is_only_a_prefix_of_a_real_one_is_not_found(client):
    """`save-the-children-old` exists; asking for `save-the-child` must not reach it."""
    tc, _ = client

    for slug in ("save-the-child", "save-the-childrenx", "SAVE-THE-CHILDREN"):
        r = tc.get(f"/api/projects/{slug}/history/", headers=HDR)
        assert r.status_code == 404, slug
        assert r.json()["error"]["code"] == "not_found"


def test_switching_a_branch_needs_confirm(client):
    tc, project = client
    store.adopt(project)
    base = store.head_state(project)["branch"]["base_snapshot_id"]
    branch = store.branch_from(project, base, "side")

    r = tc.post(f"/api/projects/{SLUG}/history/switch", json={"branch": branch["id"]}, headers=HDR)

    assert r.status_code == 422
    assert r.json()["error"]["code"] == "confirm_required"
    assert "confirm" in r.json()["error"]["message"]


def test_switching_a_branch_loads_its_head(client):
    tc, project = client
    store.adopt(project)
    base = store.head_state(project)["branch"]["base_snapshot_id"]
    branch = store.branch_from(project, base, "side")

    r = tc.post(
        f"/api/projects/{SLUG}/history/switch",
        json={"branch": branch["id"], "confirm": True},
        headers=HDR,
    )

    assert r.status_code == 200
    assert store.get_branch(project)["id"] == branch["id"]


def test_deleting_a_branch_needs_confirm(client):
    tc, project = client
    store.adopt(project)
    base = store.head_state(project)["branch"]["base_snapshot_id"]
    branch = store.branch_from(project, base, "side")

    r = tc.request(
        "DELETE", f"/api/projects/{SLUG}/history/branches/{branch['id']}", headers=HDR
    )

    assert r.status_code == 422 and r.json()["error"]["code"] == "confirm_required"
    assert store.get_branch(project, branch["id"])["name"] == "side"


def test_renaming_a_branch_does_not_need_confirm(client):
    tc, project = client
    store.adopt(project)
    base = store.head_state(project)["branch"]["base_snapshot_id"]
    branch = store.branch_from(project, base, "side")

    r = tc.patch(
        f"/api/projects/{SLUG}/history/branches/{branch['id']}",
        json={"name": "the heist"},
        headers=HDR,
    )

    assert r.status_code == 200
    assert store.get_branch(project, branch["id"])["name"] == "the heist"


def test_saving_a_draft_returns_it_and_a_second_save_without_edits_is_refused(client):
    tc, project = client
    store.adopt(project)
    edit_entity(project, "character", "kael", {"name": "Kael Renamed"}, "probe")

    first = tc.post(
        f"/api/projects/{SLUG}/history/snapshots", json={"label": "Draft 2"}, headers=HDR
    )
    assert first.status_code == 200 and first.json()["label"] == "Draft 2"

    second = tc.post(f"/api/projects/{SLUG}/history/snapshots", json={}, headers=HDR)
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "refused"


def test_a_diff_needs_two_refs(client):
    tc, project = client
    store.adopt(project)
    first = store.head_state(project)["branch"]["base_snapshot_id"]
    edit_entity(project, "character", "kael", {"name": "Kael Renamed"}, "probe")
    second = store.save_snapshot(project, "Draft 2")["id"]

    r = tc.get(
        f"/api/projects/{SLUG}/history/diff",
        params={"a": f"snapshot:{first}", "b": f"snapshot:{second}"},
        headers=HDR,
    )

    assert r.status_code == 200
    assert any("kael" in item["key"] for item in r.json()["items"])


def test_a_diff_refuses_a_ref_it_cannot_read(client):
    tc, _ = client

    r = tc.get(
        f"/api/projects/{SLUG}/history/diff",
        params={"a": "nonsense", "b": "also:nonsense"},
        headers=HDR,
    )

    assert r.status_code == 422 and r.json()["error"]["code"] == "invalid"


def test_reading_an_entity_from_a_state(client):
    tc, project = client
    store.adopt(project)
    draft = store.head_state(project)["branch"]["base_snapshot_id"]

    r = tc.get(
        f"/api/projects/{SLUG}/history/read/snapshot:{draft}/entities/character/kael",
        headers=HDR,
    )

    assert r.status_code == 200
    assert r.json()["type"] == "character" and r.json()["fields"]["name"]


def test_reading_an_entity_that_state_does_not_hold_is_refused(client):
    tc, project = client
    store.adopt(project)
    draft = store.head_state(project)["branch"]["base_snapshot_id"]

    r = tc.get(
        f"/api/projects/{SLUG}/history/read/snapshot:{draft}/entities/character/nobody",
        headers=HDR,
    )

    assert r.status_code == 409 and r.json()["error"]["code"] == "refused"


def test_reading_the_script_of_a_state(client):
    tc, project = client
    store.adopt(project)
    draft = store.head_state(project)["branch"]["base_snapshot_id"]

    r = tc.get(f"/api/projects/{SLUG}/history/read/snapshot:{draft}/script", headers=HDR)

    assert r.status_code == 200
    assert r.json()["ref"] == f"snapshot:{draft}" and r.json()["text"].strip()


def test_a_percent_encoded_decision_key_reaches_the_route(client):
    """`#` ends a URL fragment, so the client must encode it — the route takes `path`."""
    tc, project = client
    started = _merge(tc, project, selection=[NAME]).json()

    r = tc.put(
        f"/api/projects/{SLUG}/history/merges/{started['id']}/decisions/{NAME}%23D2",
        json={"choice": "theirs"},
        headers=HDR,
    )

    assert r.status_code == 200
    assert r.json()["decisions"][f"{NAME}#D2"]["choice"] == "theirs"


def test_an_unencoded_decision_key_is_a_422_not_a_silent_success(client):
    tc, project = client
    started = _merge(tc, project, selection=[NAME]).json()

    # The `#` truncates the URL: the route sees the bare item key.
    r = tc.put(
        f"/api/projects/{SLUG}/history/merges/{started['id']}/decisions/{NAME}",
        json={"choice": "theirs"},
        headers=HDR,
    )

    assert r.status_code == 422
    assert "not a decision key" in r.json()["error"]["message"]


def test_applying_a_merge_needs_confirm(client):
    tc, project = client
    started = _merge(tc, project).json()

    r = tc.post(f"/api/projects/{SLUG}/history/merges/{started['id']}/apply", json={}, headers=HDR)

    assert r.status_code == 422 and r.json()["error"]["code"] == "confirm_required"


def test_preview_reports_open_decisions_with_the_keys_to_answer(client):
    """A dry run's verdict is a 200 even when the plan is incomplete — it IS the report."""
    tc, project = client
    started = _merge(tc, project, selection=[NAME]).json()

    r = tc.post(f"/api/projects/{SLUG}/history/merges/{started['id']}/preview", headers=HDR)

    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "blocked"
    assert f"{NAME}#D2" in body["open"]
    item = next(i for i in body["plan"]["items"] if i["key"] == NAME)
    assert (item["theirs"], item["ours"]) == ("Kael Theirs", "Kael Ours")
    decision = next(d for d in body["plan"]["decisions"] if d["key"] == f"{NAME}#D2")
    assert decision["choice"] == "mine" and decision["set_by"] == "default"


def test_preview_is_clean_once_the_decision_is_answered(client):
    tc, project = client
    started = _merge(tc, project, selection=[NAME]).json()
    tc.put(
        f"/api/projects/{SLUG}/history/merges/{started['id']}/decisions/{NAME}%23D2",
        json={"choice": "theirs"},
        headers=HDR,
    )

    r = tc.post(f"/api/projects/{SLUG}/history/merges/{started['id']}/preview", headers=HDR)

    assert r.status_code == 200
    assert r.json()["status"] == "clean"


def test_applying_a_merge_loads_the_source_value(client):
    """The whole workspace flow through HTTP: start, answer, apply."""
    tc, project = client
    started = _merge(tc, project, selection=[NAME]).json()
    tc.put(
        f"/api/projects/{SLUG}/history/merges/{started['id']}/decisions/{NAME}%23D2",
        json={"choice": "theirs"},
        headers=HDR,
    )

    r = tc.post(
        f"/api/projects/{SLUG}/history/merges/{started['id']}/apply",
        json={"confirm": True},
        headers=HDR,
    )

    assert r.status_code == 200 and r.json()["status"] == "applied"
    [row] = _rows(project, "select name from entities where id='kael'")
    assert row[0] == "Kael Theirs"


def _rows(project, sql):
    import sqlite3

    conn = sqlite3.connect(str(project / ".story" / "story.db"))
    try:
        return conn.execute(sql).fetchall()
    finally:
        conn.close()


def test_a_session_that_does_not_exist_is_refused(client):
    tc, project = client
    store.adopt(project)

    r = tc.get(f"/api/projects/{SLUG}/history/merges/nope", headers=HDR)

    assert r.status_code == 409 and r.json()["error"]["code"] == "refused"


def test_the_status_is_the_current_branch_and_what_a_save_would_be_called(client):
    tc, project = client
    store.adopt(project)
    edit_entity(project, "character", "kael", {"name": "Kael Renamed"}, "probe")

    body = tc.get(f"/api/projects/{SLUG}/history/status", headers=HDR).json()

    assert body["current_branch"] == "main"
    assert body["current_draft"] == "Draft 1"
    assert body["changes_since_save"] == 1
    assert body["next_draft_number"] == 2


def test_the_status_of_a_project_with_no_history_writes_nothing(client):
    tc, project = client

    body = tc.get(f"/api/projects/{SLUG}/history/status", headers=HDR).json()

    assert body["branch_count"] == 0 and body["next_draft_number"] == 1
    assert not store.history_path(project).exists()


def test_the_status_needs_the_exact_slug(client):
    tc, _ = client

    assert tc.get(f"/api/projects/{SLUG}/history/status", headers=HDR).status_code == 200
    assert tc.get("/api/projects/save-the-child/history/status", headers=HDR).status_code == 404


def test_a_states_entity_index_names_every_entity(client):
    tc, project = client
    store.adopt(project)
    base = store.head_state(project)["branch"]["base_snapshot_id"]
    edit_entity(project, "character", "kael", {"name": "Kael Renamed"}, "probe")

    live = tc.get(f"/api/projects/{SLUG}/history/read/branch:main/entities", headers=HDR).json()
    saved = tc.get(
        f"/api/projects/{SLUG}/history/read/snapshot:{base}/entities", headers=HDR
    ).json()

    def names(body):
        return {e["id"]: e["name"] for e in body["entities"]}

    assert names(live)["kael"] == "Kael Renamed"
    assert names(saved)["kael"] != "Kael Renamed"
    assert {e["type"] for e in live["entities"]} >= {"scene", "character", "act"}
    assert all(e["name"] for e in live["entities"])


def test_a_scenes_beats_borrow_its_title_in_the_index(client):
    tc, project = client
    store.adopt(project)

    body = tc.get(f"/api/projects/{SLUG}/history/read/branch:main/entities", headers=HDR).json()

    beats = [e for e in body["entities"] if e["type"] == "scene_beats"]
    assert beats and all(e["name"].endswith("(beats)") for e in beats)


def test_the_entity_index_rejects_a_malformed_ref(client):
    tc, project = client
    store.adopt(project)

    resp = tc.get(f"/api/projects/{SLUG}/history/read/oops:x/entities", headers=HDR)

    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "invalid"


def test_the_read_script_route_returns_formatted_html_with_scene_numbers(client):
    tc, project = client
    store.adopt(project)

    body = tc.get(f"/api/projects/{SLUG}/history/read/branch:main/script", headers=HDR).json()

    assert body["text"]
    assert 'data-scenenumber="1"' in body["html"]
    assert "fountain-scene_heading" in body["html"]


def test_scene_text_cannot_become_markup_in_the_read_script_route(client):
    tc, project = client
    store.adopt(project)
    edit_entity(
        project,
        "scene",
        "central-room-day",
        {"Content": "He reads <script>alert(1)</script>."},
        "x",
    )

    body = tc.get(f"/api/projects/{SLUG}/history/read/branch:main/script", headers=HDR).json()

    assert "<script>" not in body["html"]
