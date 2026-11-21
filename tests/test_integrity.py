"""The orphan checker: the net under the write paths.

No foreign keys are declared, so nothing in the schema stops a write from
leaving a section, revision or relation pointing at a missing entity.
`core.integrity.find_orphans` is the read-only oracle for that. These tests
hold it to a clean fixture, one hand-broken database per category, and every
kind of write the app can do.
"""
import json
import sqlite3

import pytest

import twin_helpers as twin
from story_architect.core import drafts
from story_architect.core.integrity import find_orphans
from story_architect.core.trash import purge_deleted
from story_architect.core.writes import create_entity, delete_entity, edit_entity
from story_architect.tools.story_admin import handler as admin
from story_architect.tools.story_import import handler as import_handler


def _orphans(p):
    conn = sqlite3.connect(str(p / ".story" / "story.db"))
    try:
        return find_orphans(conn)
    finally:
        conn.close()


def _restore(p, etype, eid):
    return json.loads(admin({"action": "restore", "project": str(p),
                             "target": {"entity_type": etype, "id": eid},
                             "summary": "t"}, root_path=str(p.parent)))


# ─── the oracle itself ───

def test_a_clean_fixture_has_no_orphans(fixture_path):
    assert _orphans(fixture_path) == {}


BREAKS = [
    ("sections",
     "INSERT INTO sections(entity_id, heading, body) VALUES('ghost','Content','x')"),
    ("revisions",
     "INSERT INTO revisions(entity_id, heading, body, replaced_at) "
     "VALUES('ghost','Content','x','2026-01-01T00:00:00')"),
    ("relations_from",
     "INSERT INTO relations(from_id, to_id, kind) VALUES('ghost','kael','character_scene')"),
    ("relations_to",
     "INSERT INTO relations(from_id, to_id, kind) VALUES('kael','ghost','character_scene')"),
    ("parent_id", "UPDATE entities SET parent_id='ghost' WHERE id='kael'"),
    ("location_id", "UPDATE entities SET location_id='ghost' WHERE id='kael'"),
]


@pytest.mark.parametrize("key,sql", BREAKS, ids=[b[0] for b in BREAKS])
def test_a_broken_category_reports_only_itself(fixture_path, key, sql):
    twin.sql(fixture_path, sql)
    out = _orphans(fixture_path)
    assert set(out) == {key}
    assert any("ghost" in row for row in out[key])


def test_null_and_empty_links_are_not_orphans(fixture_path):
    twin.sql(fixture_path, "UPDATE entities SET parent_id=NULL, location_id=NULL WHERE id='kael'")
    twin.sql(fixture_path, "UPDATE entities SET parent_id='', location_id='' WHERE id='mira'")
    assert _orphans(fixture_path) == {}


def test_a_live_child_of_a_trashed_parent_is_not_an_orphan(fixture_path):
    """A flagged-deleted row still exists; only a missing row is an orphan."""
    assert delete_entity(fixture_path, "scene", "central-room-day", "t", True)["success"]
    # Bring only the scene_beats back: a live child under a trashed parent.
    twin.sql(fixture_path, "UPDATE entities SET is_deleted=0, deleted_at=NULL "
                           "WHERE parent_id='central-room-day'")
    assert twin.sql(fixture_path, "SELECT is_deleted FROM entities "
                                  "WHERE id='central-room-day'") == [(1,)]
    assert twin.sql(fixture_path, "SELECT count(*) FROM entities "
                                  "WHERE parent_id='central-room-day' AND is_deleted=0")[0][0]
    assert _orphans(fixture_path) == {}


def test_an_fts_index_out_of_step_is_reported(fixture_path):
    # Remove a sections row behind the FTS triggers' back: the index keeps a
    # stale entry. The rank=1 integrity-check is what compares index to content.
    twin.sql(fixture_path, "DROP TRIGGER sections_ad")
    twin.sql(fixture_path, "DELETE FROM sections WHERE entity_id='kael'")
    assert set(_orphans(fixture_path)) == {"fts"}


# ─── every kind of write, with the oracle after it ───

def _delete_and_restore(etype, eid):
    def scenario(p):
        assert delete_entity(p, etype, eid, "t", True)["success"]
        twin.assert_no_orphans(p)
        assert _restore(p, etype, eid)["success"]
    return scenario


def _targeted_purge(p):
    delete_entity(p, "character", "kael", "t", True)
    out = purge_deleted(p, target={"entity_type": "character", "id": "kael"})
    assert [i["id"] for i in out["purged"]] == ["kael"]


def _bulk_purge(p):
    delete_entity(p, "character", "kael", "t", True)
    delete_entity(p, "scene", "central-room-day", "t", True)
    out = purge_deleted(p, older_than_days=0)
    assert len(out["purged"]) >= 3      # kael, the scene, its scene_beats


def _create_edit_delete(p):
    create_entity(p, "character", "newcomer", {"name": "Newcomer"})
    edit_entity(p, "character", "newcomer", {"one_sentence": "Arrives."}, "e")
    assert delete_entity(p, "character", "newcomer", "t", True)["success"]


def _draft_commit(p):
    staged = drafts.stage(p, [
        {"op": "create", "type": "character", "id": "newcomer",
         "frontmatter": {"name": "Newcomer"}, "summary": "c"},
        {"op": "edit", "entity_type": "character", "entity_id": "mira",
         "data": {"one_sentence": "Mira's own line."}, "summary": "e"},
        {"op": "delete", "entity_type": "character", "entity_id": "kael", "summary": "d"},
    ])
    report = drafts.commit(p, staged["draft_id"])
    # All three ops must land: on success `committed` is True and `applied`
    # lists them; a partial landing also reads as truthy `committed`.
    assert report["success"] is True and len(report["applied"]) == 3, report


def _reimport(p):
    out = json.loads(import_handler({"project": str(p), "confirm": True},
                                    root_path=str(p.parent)))
    assert out.get("success"), out


SCENARIOS = [
    ("delete-restore-character", _delete_and_restore("character", "kael")),
    ("delete-restore-scene", _delete_and_restore("scene", "central-room-day")),
    ("delete-restore-plot", _delete_and_restore("plot", "the-resistance")),
    ("delete-restore-location", _delete_and_restore("location", "the-garden")),
    ("delete-restore-world", _delete_and_restore("world", "the-i")),
    ("targeted-purge", _targeted_purge),
    ("bulk-purge", _bulk_purge),
    ("create-edit-delete", _create_edit_delete),
    ("draft-commit", _draft_commit),
    ("reimport", _reimport),
]


@pytest.mark.parametrize("name,scenario", SCENARIOS, ids=[s[0] for s in SCENARIOS])
def test_no_write_leaves_orphans(fixture_path, name, scenario):
    scenario(fixture_path)
    twin.assert_no_orphans(fixture_path)
