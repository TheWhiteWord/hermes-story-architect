"""Delete must leave nothing pointing at what it removed.

The cascade handled relation *rows* and `parent_id`, but several reference sites
live in the `extra` JSON blob instead. A relationship is a first-class entity, not
a relation row, so deleting a character left relationship entities still naming
them — perspectives and all:

    kael-mira  {"characters": ["kael", "mira"], "perspectives": {"kael": {...}}}

Every reference site in the schema, and what happens to it:
    extra.characters     list of ids  → dead ids removed
    extra.scenes         list of ids  → key kept, dead ids removed
    extra.scene          single id     → key kept, value ""
    extra.perspectives   dict keyed by character id → dead keys removed
    location_id          column        → set to ""
    parent_id            column        → set to ""
    relations rows       both directions → deleted
"""
import json
import shutil
import sqlite3

import pytest

from tools.story_edit import handler as edit_handler
from tools.story_import import handler as import_handler


def _setup(fixture_path, tmp_path, name):
    vault = tmp_path / name
    p = vault / "projects" / "save-the-children"
    p.parent.mkdir(parents=True)
    shutil.copytree(str(fixture_path), str(p))
    import_handler({"project": "save-the-children", "confirm": True}, root_path=str(vault))
    return p, vault


def _delete(vault, entity_type, slug):
    return json.loads(edit_handler(
        {"action": "delete_entity",
         "target": {"entity_type": entity_type, "slug": slug, "project": "save-the-children"},
         "summary": "t", "confirm": True}, root_path=str(vault)))


def _references_to(project, target):
    """Every surviving reference to `target`, of any kind."""
    conn = sqlite3.connect(str(project / ".story" / "story.db"))
    found = []
    try:
        for eid, parent, location, extra_json in conn.execute(
                "SELECT id, parent_id, location_id, extra FROM entities "
                "WHERE is_deleted=0"):
            extra = json.loads(extra_json or "{}")
            if parent == target:
                found.append((eid, "parent_id"))
            if location == target:
                found.append((eid, "location_id"))
            if target in (extra.get("characters") or []):
                found.append((eid, "extra.characters"))
            if target in (extra.get("scenes") or []):
                found.append((eid, "extra.scenes"))
            if extra.get("scene") == target:
                found.append((eid, "extra.scene"))
            if target in (extra.get("perspectives") or {}):
                found.append((eid, "extra.perspectives"))
        # Relations *owned by* the deleted entity survive on purpose — restore
        # has to put them back, and reconstructing them would be guesswork.
        # What must not survive is a live entity pointing at a dead one.
        for from_id, kind in conn.execute(
                "SELECT from_id, kind FROM relations "
                "WHERE (from_id=? OR to_id=?) AND from_id NOT IN "
                "(SELECT id FROM entities WHERE is_deleted=1)",
                (target, target)):
            found.append((from_id, f"relation:{kind}"))
    finally:
        conn.close()
    return found


def _extra(project, entity_id):
    conn = sqlite3.connect(str(project / ".story" / "story.db"))
    try:
        return json.loads(conn.execute(
            "SELECT extra FROM entities WHERE id=?", (entity_id,)).fetchone()[0] or "{}")
    finally:
        conn.close()


@pytest.mark.parametrize("entity_type,slug", [
    ("character", "kael"),
    ("character", "mira"),
    ("scene", "central-room-day"),
    ("scene", "the-core-day"),
    ("world", "the-i"),
    ("location", "the-garden"),
    ("location", "the-central-room"),
    ("plot", "the-resistance"),
    ("relationship", "kael-mira"),
])
class TestNothingDangles:
    def test_no_reference_of_any_kind_survives(self, fixture_path, tmp_path, entity_type, slug):
        p, vault = _setup(fixture_path, tmp_path, f"v-{entity_type}-{slug}")
        result = _delete(vault, entity_type, slug)
        assert result.get("success") is True
        assert _references_to(p, slug) == []


class TestRelationshipEntities:
    """The case that motivated the fix."""

    def test_deleting_a_character_strips_it_from_relationships(self, fixture_path, tmp_path):
        p, vault = _setup(fixture_path, tmp_path, "rel")
        _delete(vault, "character", "kael")
        extra = _extra(p, "kael-mira")
        assert "kael" not in extra["characters"]
        assert "mira" in extra["characters"], "the surviving character must remain"

    def test_perspectives_of_the_dead_character_are_removed(self, fixture_path, tmp_path):
        p, vault = _setup(fixture_path, tmp_path, "persp")
        _delete(vault, "character", "kael")
        perspectives = _extra(p, "kael-mira")["perspectives"]
        assert "kael" not in perspectives
        assert "mira" in perspectives, "the other perspective must be untouched"

    def test_the_relationship_entity_itself_survives(self, fixture_path, tmp_path):
        """Kael and Mira still have a relationship; only Kael's half is gone."""
        p, vault = _setup(fixture_path, tmp_path, "survive")
        _delete(vault, "character", "kael")
        conn = sqlite3.connect(str(p / ".story" / "story.db"))
        try:
            assert conn.execute(
                "SELECT 1 FROM entities WHERE id='kael-mira'").fetchone()
        finally:
            conn.close()

    def test_unrelated_relationships_are_untouched(self, fixture_path, tmp_path):
        p, vault = _setup(fixture_path, tmp_path, "unrelated")
        before = _extra(p, "mira-the-administrator")
        _delete(vault, "character", "kael")
        assert _extra(p, "mira-the-administrator") == before

    def test_scene_removal_strips_relationship_scene_lists(self, fixture_path, tmp_path):
        p, vault = _setup(fixture_path, tmp_path, "scenes")
        _delete(vault, "scene", "central-room-day")
        assert "central-room-day" not in _extra(p, "kael-mira")["scenes"]


class TestColumnReferences:
    def test_location_id_is_emptied(self, fixture_path, tmp_path):
        """Emptied to "", not NULL: the field still exists and reads as a gap."""
        p, vault = _setup(fixture_path, tmp_path, "loc")
        _delete(vault, "location", "the-garden")
        conn = sqlite3.connect(str(p / ".story" / "story.db"))
        try:
            row = conn.execute(
                "SELECT location_id FROM entities WHERE id='the-core-day'").fetchone()
        finally:
            conn.close()
        assert row[0] == ""

    def test_the_scene_itself_survives_the_location_removal(self, fixture_path, tmp_path):
        p, vault = _setup(fixture_path, tmp_path, "loc2")
        _delete(vault, "location", "the-garden")
        conn = sqlite3.connect(str(p / ".story" / "story.db"))
        try:
            assert conn.execute("SELECT 1 FROM entities WHERE id='the-core-day'").fetchone()
        finally:
            conn.close()


class TestFieldsSurviveAsBlanks:
    """A reference that lost its target keeps its key.

    `unfilled_fields` treats a missing key and an empty value the same, but the
    difference is visible to a reader: `scene: ""` in the Markdown says "this
    beat has no scene", whereas a vanished key just looks like a field that was
    never part of the schema.
    """

    def test_arc_beat_keeps_an_empty_scene_key(self, fixture_path, tmp_path):
        p, vault = _setup(fixture_path, tmp_path, "blank-beat")
        _delete(vault, "scene", "central-room-day")
        extra = _extra(p, "dr-elena-voss-1")
        assert "scene" in extra
        assert extra["scene"] == ""

    def test_beat_prose_is_untouched(self, fixture_path, tmp_path):
        p, vault = _setup(fixture_path, tmp_path, "blank-prose")
        before = _extra(p, "dr-elena-voss-1")
        _delete(vault, "scene", "central-room-day")
        after = _extra(p, "dr-elena-voss-1")
        assert after["action"] == before["action"]
        assert after["gap"] == before["gap"]
        assert after["choice"] == before["choice"]
        assert after["y"] == before["y"]

    def test_retrieve_shows_the_field_as_empty(self, fixture_path, tmp_path):
        from tools.story_retrieve import handler as retrieve_handler
        p, vault = _setup(fixture_path, tmp_path, "blank-read")
        _delete(vault, "scene", "central-room-day")
        r = json.loads(retrieve_handler(
            {"project": "save-the-children", "entity_type": "arc_beat", "id": ["dr-elena-voss-1"],
             "fields": ["scene", "action"]}, root_path=str(vault)))
        fields = r["entities"][0]["fields"]
        assert "scene" in fields and fields["scene"] == ""
        assert fields["action"]

    def test_relationship_keeps_an_empty_scenes_list(self, fixture_path, tmp_path):
        p, vault = _setup(fixture_path, tmp_path, "blank-scenes")
        _delete(vault, "scene", "central-room-day")
        assert _extra(p, "kael-mira")["scenes"] == ["central-room-night"]

    def test_character_keeps_an_empty_characters_list(self, fixture_path, tmp_path):
        p, vault = _setup(fixture_path, tmp_path, "blank-chars")
        _delete(vault, "character", "kael")
        assert _extra(p, "kael-mira")["characters"] == ["mira"]

    def test_perspectives_key_is_removed_not_emptied(self, fixture_path, tmp_path):
        """The one genuine removal: a dead viewpoint has no blank form."""
        p, vault = _setup(fixture_path, tmp_path, "blank-persp")
        _delete(vault, "character", "kael")
        perspectives = _extra(p, "kael-mira")["perspectives"]
        assert "kael" not in perspectives
        assert "mira" in perspectives


class TestDetachedReporting:
    """Required fields are skipped by unfilled_fields, so the delete must say so.

    `arc_beat.scene` is optional: False, and unfilled_fields deliberately skips
    required fields — an empty required field is a schema violation, not a
    "needs filling" hint. Without this report the gap is invisible.
    """

    def test_delete_reports_detached_beats(self, fixture_path, tmp_path):
        p, vault = _setup(fixture_path, tmp_path, "det-1")
        result = _delete(vault, "scene", "central-room-day")
        beats = {d["entity_id"] for d in result["detached"] if d["field"] == "scene"}
        assert beats == {"dr-elena-voss-1", "kael-1", "marcus-chen-1",
                         "the-administrator-1"}

    def test_detached_names_what_it_pointed_at(self, fixture_path, tmp_path):
        p, vault = _setup(fixture_path, tmp_path, "det-2")
        result = _delete(vault, "scene", "central-room-day")
        assert all(d["was_pointing_at"] == "central-room-day" for d in result["detached"])

    def test_detached_carries_the_entity_type(self, fixture_path, tmp_path):
        p, vault = _setup(fixture_path, tmp_path, "det-3")
        result = _delete(vault, "location", "the-garden")
        assert result["detached"] == [{"entity_id": "the-core-day",
                                       "entity_type": "scene", "field": "location",
                                       "was_pointing_at": "the-garden"}]

    def test_nothing_detached_when_nothing_pointed(self, fixture_path, tmp_path):
        p, vault = _setup(fixture_path, tmp_path, "det-4")
        assert _delete(vault, "plot", "the-resistance")["detached"] == []

    def test_detach_is_reported_on_the_dry_run_too(self, fixture_path, tmp_path):
        p, vault = _setup(fixture_path, tmp_path, "det-5")
        result = json.loads(edit_handler(
            {"action": "delete_entity",
             "target": {"entity_type": "scene", "slug": "central-room-day", "project": "save-the-children"},
             "summary": "t", "dry_run": True}, root_path=str(vault)))
        assert "would_delete" in result


class TestDefaultsOnReset:
    """A reset field takes the schema default, so a placeholder survives."""

    def test_arc_beat_scene_resets_to_its_default(self, fixture_path, tmp_path):
        from core.constants import ENTITY_SCHEMAS
        p, vault = _setup(fixture_path, tmp_path, "def-1")
        _delete(vault, "scene", "central-room-day")
        assert _extra(p, "dr-elena-voss-1")["scene"] == ENTITY_SCHEMAS["arc_beat"]["scene"]["default"]

    def test_optional_location_still_lands_in_unfilled_fields(self, fixture_path, tmp_path):
        """location_id is a column so it reads "", but location is optional —
        so unfilled_fields reports it and the UI has its signal."""
        from tools.story_retrieve import handler as retrieve_handler
        p, vault = _setup(fixture_path, tmp_path, "def-2")
        _delete(vault, "location", "the-garden")
        r = json.loads(retrieve_handler(
            {"project": "save-the-children", "entity_type": "scene", "id": ["the-core-day"],
             "fields": ["location"]}, root_path=str(vault)))
        assert r["entities"][0]["fields"]["location"] == ""
        assert "location" in r["entities"][0]["unfilled_fields"]


class TestReporting:
    def test_reports_what_it_purged(self, fixture_path, tmp_path):
        p, vault = _setup(fixture_path, tmp_path, "report")
        result = _delete(vault, "character", "kael")
        assert "kael-mira" in result["references_purged"]

    def test_reports_the_cascade(self, fixture_path, tmp_path):
        p, vault = _setup(fixture_path, tmp_path, "cascade")
        result = _delete(vault, "character", "kael")
        assert set(result["cascade_deleted"]) == {"kael-1", "kael-2", "kael-3"}

    def test_nothing_purged_when_nothing_referenced(self, fixture_path, tmp_path):
        p, vault = _setup(fixture_path, tmp_path, "nopurge")
        result = _delete(vault, "plot", "the-resistance")
        assert result["references_purged"] == []
