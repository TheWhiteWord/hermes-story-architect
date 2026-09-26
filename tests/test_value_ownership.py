"""Value lives in view='story_value', not in the base structural map.

Regression: acts and sequences both emitted value/value_open/value_close in
the base view, duplicating each other in the view whose stated job is to stay
small — and the value view only covered acts, so stripping the base first would
have lost sequences entirely.
"""
import json
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

FIXTURE = Path(__file__).parent / "fixtures" / "save-the-children"


@pytest.fixture
def project(tmp_path, monkeypatch):
    root = tmp_path / "root"
    shutil.copytree(FIXTURE, root / "projects" / "save-the-children")
    import core.config
    monkeypatch.setattr(core.config, "load_plugin_config", lambda: {"root_path": str(root)})
    from tools.story_import import handler as import_handler
    import_handler({"project": "save-the-children", "confirm": True}, root_path=str(root))
    return root / "projects" / "save-the-children"


def load(project, **args):
    from tools.story_load import handler
    return json.loads(
        handler({"project": "save-the-children", **args}, root_path=str(project.parent.parent))
    )


def test_base_map_carries_no_container_values(project):
    data = load(project)
    assert data["acts"], "fixture should have acts"
    for act in data["acts"]:
        assert not {"value", "value_at_open", "value_at_close"} & act.keys()
        for seq in act["sequences"]:
            assert not {"value", "value_at_open", "value_at_close"} & seq.keys()


def test_base_map_still_carries_the_project_value(project):
    """Stripping the containers must not strip the project's own value."""
    p = load(project)["project"]
    for k in ("value", "value_at_open", "value_at_close"):
        assert k in p


def test_story_value_view_carries_act_and_sequence_values(project):
    data = load(project, view="story_value")
    assert data["acts"], "expected at least one act"
    with_seq = 0
    for act in data["acts"]:
        assert "value_at_open" in act and "value_at_close" in act
        for seq in act["sequences"]:
            assert "value_at_open" in seq and "value_at_close" in seq
            with_seq += 1
    assert with_seq, "fixture should have sequences to prove they survive"


def test_sequences_are_titled(project):
    """A sequence id alone cannot be told from another without a lookup."""
    for act in load(project, view="story_value")["acts"]:
        for seq in act["sequences"]:
            assert seq.get("title"), f"sequence {seq['id']} has no title"


def test_scenes_are_included_with_their_values(project):
    """Scenes are where the value turns; without them the progression is a lie."""
    scenes = [
        (seq["id"], sc)
        for act in load(project, view="story_value")["acts"]
        for seq in act["sequences"]
        for sc in seq.get("scenes", [])
    ]
    assert scenes, "no scenes in the value view — the progression cannot be read"
    for seq_id, sc in scenes:
        assert sc.get("id")
        assert "value_at_open" in sc and "value_at_close" in sc


def test_every_scene_in_the_db_appears_in_the_value_view(project):
    """A scene dropped from the view is a value turn the reader cannot see."""
    from core.db import get_db
    conn = get_db(project)
    try:
        in_db = {r[0] for r in conn.execute(
            "SELECT id FROM entities WHERE type='scene' AND is_deleted=0")}
    finally:
        conn.close()
    in_view = {
        sc["id"]
        for act in load(project, view="story_value")["acts"]
        for seq in act["sequences"] for sc in seq.get("scenes", [])
    }
    assert in_db == in_view, f"missing from view: {in_db - in_view}"


def test_scene_titles_present(project):
    for act in load(project, view="story_value")["acts"]:
        for seq in act["sequences"]:
            for sc in seq.get("scenes", []):
                assert "title" in sc, f"scene {sc['id']} has no title"


def test_value_view_is_not_silently_empty(project):
    """The bug: acts stored value_open, the view read value_at_open, all blank.

    Keys present but always "" reads as "no value data", which is a different
    lie. At least one container must carry a real charge.
    """
    data = load(project, view="story_value")
    charges = [
        d[side]
        for act in data["acts"] for d in [act] + act["sequences"]
        for side in ("value_at_open", "value_at_close")
    ]
    assert any(charges), f"every value field empty — key mismatch again: {data}"


def test_act_filter_still_works_in_the_value_view(project):
    """seq_by_act is built before the filter, so a filtered act keeps its sequences."""
    all_acts = load(project, view="story_value")["acts"]
    target = next(a for a in all_acts if a["sequences"])
    one = load(project, view="story_value", act=target["id"])["acts"]
    assert [a["id"] for a in one] == [target["id"]]
    assert [s["id"] for s in one[0]["sequences"]] == [s["id"] for s in target["sequences"]]
