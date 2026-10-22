"""A scene's location must be visible to the relation-based readers.

`scene.location` is stored twice: in the `location_id` column, and in a
`location_scene` relation that is the same fact pointing the other way. Four
readers in core/db.py use the relation. Only the importer ever wrote it, so a
scene authored through story_draft wrote the column alone and every one of
those readers went blind.

The cost is measurable: the dashboard's location→scenes view reports 0 for a
location that two scenes are set in. Asserted below, with and without the
relation, so the test cannot pass by accident.
"""
import shutil
import sqlite3
from pathlib import Path

import pytest


FIXTURE = Path(__file__).parent / "fixtures" / "save-the-children"


def _db(proj):
    return sqlite3.connect(str(proj / ".story" / "story.db"))


def _location_scenes(proj):
    """{location_id: number of scenes the dashboard reports for it}."""
    from core.db import get_dashboard_data

    out = {}

    def walk(node):
        if isinstance(node, list):
            for x in node:
                walk(x)
        elif isinstance(node, dict):
            if "scenes" in node and "id" in node and "name" in node:
                scenes = node["scenes"] or []
                out[node["id"]] = len(scenes) if isinstance(scenes, list) else 0
            for v in node.values():
                walk(v)

    walk(get_dashboard_data(proj)["story_data"])
    return out


@pytest.fixture
def proj(tmp_path, _built_fixture):
    dest = tmp_path / "b8"
    shutil.copytree(str(_built_fixture), str(dest))
    return dest


class TestLocationSceneRelationIsWritten:
    def test_creating_a_scene_writes_the_relation(self, proj):
        from core.writes import create_entity

        create_entity(proj, "scene", "new-scene",
                      {"title": "New", "location": "the-central-room"})
        rows = _db(proj).execute(
            "SELECT from_id, to_id FROM relations WHERE kind='location_scene' "
            "AND to_id='new-scene'").fetchall()
        assert rows == [("the-central-room", "new-scene")]

    def test_moving_a_scene_replaces_the_relation(self, proj):
        """The stale row is the dangerous half: it keeps a location looking used."""
        from core.writes import create_entity, edit_entity

        create_entity(proj, "location", "cellar", {"name": "Cellar"})
        create_entity(proj, "scene", "moving", {"title": "M", "location": "the-central-room"})
        edit_entity(proj, "scene", "moving", {"location": "cellar"}, "move")
        rows = _db(proj).execute(
            "SELECT from_id FROM relations WHERE kind='location_scene' AND to_id='moving'"
        ).fetchall()
        assert rows == [("cellar",)]

    def test_clearing_the_location_clears_the_relation(self, proj):
        from core.writes import create_entity, edit_entity

        create_entity(proj, "scene", "clearing", {"title": "C", "location": "the-central-room"})
        edit_entity(proj, "scene", "clearing", {"location": ""}, "clear")
        assert _db(proj).execute(
            "SELECT count(*) FROM relations WHERE kind='location_scene' AND to_id='clearing'"
        ).fetchone()[0] == 0


class TestTheRelationIsLoadBearing:
    """The reason the above matters: a reader that only sees the relation."""

    def test_dashboard_location_scenes_is_empty_without_the_relation(self, proj):
        db = _db(proj)
        db.execute("DELETE FROM relations WHERE kind='location_scene'")
        db.commit()
        db.close()
        assert _location_scenes(proj)["the-central-room"] == 0

    def test_dashboard_location_scenes_is_correct_with_it(self, proj):
        db = _db(proj)
        db.execute("DELETE FROM relations WHERE kind='location_scene'")
        rows = db.execute(
            "SELECT id, location_id FROM entities "
            "WHERE type='scene' AND location_id IS NOT NULL").fetchall()
        for sid, lid in rows:
            db.execute(
                "INSERT INTO relations (from_id,to_id,kind,note,\"order\") "
                "VALUES (?,?,'location_scene','',1)", (lid, sid))
        db.commit()
        db.close()
        assert _location_scenes(proj)["the-central-room"] > 0
