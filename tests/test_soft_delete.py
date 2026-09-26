"""A delete you cannot undo is a different tool from a delete you can.

task_18 specified the soft delete — `UPDATE entities SET is_deleted=1,
deleted_at=?` — and the schema already carried the columns, but the
implementation hard-deleted instead. This pins the specified behaviour:

  * delete flags the row; prose and owned relations are left intact
  * every reader treats a deleted entity as nonexistent
  * `restore` is an exact inverse — the round trip is byte-identical

The dangerous half is the middle one. A soft delete is only safe if no reader
can see through it, and the reference sites are scattered across `entities`,
`relations` and the FTS index.
"""

import json
import shutil
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

FIXTURE = Path(__file__).parent / "fixtures" / "save-the-children"


@pytest.fixture
def vault(tmp_path, monkeypatch):
    v = tmp_path / "v"
    dest = v / "projects" / "stc"
    dest.parent.mkdir(parents=True)
    shutil.copytree(str(FIXTURE), str(dest))
    import core.config
    monkeypatch.setattr(core.config, "load_plugin_config",
                        lambda: {"root_path": str(v)})
    from tools.story_import import handler
    handler({"project": "stc", "confirm": True}, root_path=str(v))
    return v


def _db(vault):
    return vault / "projects" / "stc" / ".story" / "story.db"


def _edit(vault, action, entity_type="character", slug="kael", **extra):
    from tools.story_edit import handler
    return json.loads(handler({
        "action": action,
        "target": {"entity_type": entity_type, "slug": slug, "project": "stc"},
        "summary": "test", **extra}, root_path=str(vault)))


def _q(vault, sql, args=()):
    conn = sqlite3.connect(str(_db(vault)))
    try:
        return conn.execute(sql, args).fetchall()
    finally:
        conn.close()


def _delete(vault, entity_type="character", slug="kael"):
    return _edit(vault, "delete_entity", entity_type, slug, confirm=True)


class TestDeleteFlagsRatherThanErases:
    def test_row_survives_with_the_flag_set(self, vault):
        _delete(vault)
        assert _q(vault, "SELECT is_deleted FROM entities WHERE id='kael'") == [(1,)]

    def test_deleted_at_is_recorded(self, vault):
        _delete(vault)
        stamp = _q(vault, "SELECT deleted_at FROM entities WHERE id='kael'")[0][0]
        assert stamp and "T" in stamp

    def test_prose_survives_so_restore_can_be_exact(self, vault):
        before = _q(vault, "SELECT count(*) FROM sections WHERE entity_id='kael'")[0][0]
        _delete(vault)
        assert _q(vault, "SELECT count(*) FROM sections WHERE entity_id='kael'")[0][0] == before

    def test_owned_relations_survive(self, vault):
        before = _q(vault, "SELECT count(*) FROM relations WHERE from_id='kael'")[0][0]
        _delete(vault)
        assert _q(vault, "SELECT count(*) FROM relations WHERE from_id='kael'")[0][0] == before

    def test_cascade_children_are_also_flagged(self, vault):
        _delete(vault)
        live = _q(vault, "SELECT id FROM entities WHERE type='arc_beat' "
                        "AND parent_id='kael' AND is_deleted=0")
        assert live == []

    def test_response_advertises_how_to_undo(self, vault):
        """The agent must learn reversibility from the response, not guess."""
        r = _delete(vault)
        assert r["reversible"] is True
        assert "restore" in r["how_to_undo"]


class TestDeletedEntitiesAreInvisible:
    """The half that makes a soft delete safe."""

    def test_retrieve_cannot_find_it(self, vault):
        from tools.story_retrieve import handler
        _delete(vault)
        r = json.loads(handler({
            "project": "stc", "entity_type": "character", "id": ["kael"],
            "fields": ["one_sentence"]}, root_path=str(vault)))
        assert r.get("entities", []) == []
        assert r.get("not_found"), "a deleted id must not read as found"

    def test_story_load_omits_it(self, vault):
        from tools.story_load import handler
        _delete(vault)
        assert "kael" not in json.dumps(
            json.loads(handler({"project": "stc"}, root_path=str(vault))))

    def test_search_cannot_reach_its_prose(self, vault):
        from tools.story_search import handler
        from core.db import search_sections
        # A term that occurs in Kael's own sections.
        own = _q(vault, "SELECT body FROM sections WHERE entity_id='kael' "
                        "AND body LIKE '%curriculum%' LIMIT 1")
        assert own, "fixture no longer contains the probe term"
        _delete(vault)
        found = search_sections(vault / "projects" / "stc", "curriculum")
        assert all(x["entity_id"] != "kael" for x in found["results"])

    def test_search_total_excludes_deleted(self, vault):
        """A count that included invisible rows would mislead the agent."""
        from core.db import search_sections
        before = search_sections(vault / "projects" / "stc", "curriculum")["total_matches"]
        _delete(vault)
        after = search_sections(vault / "projects" / "stc", "curriculum")["total_matches"]
        assert after < before

    def test_dashboard_omits_it(self, vault):
        from core.db import get_dashboard_data
        _delete(vault)
        data = get_dashboard_data(vault / "projects" / "stc")

        def ids(node):
            if isinstance(node, dict):
                if node.get("id"):
                    yield node["id"]
                for v in node.values():
                    yield from ids(v)
            elif isinstance(node, list):
                for v in node:
                    yield from ids(v)

        assert "kael" not in set(ids(data))

    def test_it_is_not_an_edit_target(self, vault):
        _delete(vault)
        r = _edit(vault, "edit_note", data={"goals_short": "x"})
        assert "error" in r

    def test_story_load_arc_view_omits_its_beats(self, vault):
        from tools.story_load import handler
        _delete(vault)
        r = json.loads(handler({"project": "stc", "view": "arc"},
                               root_path=str(vault)))
        assert "kael" not in {a["character"] for a in r.get("arcs", [])}

    def test_unfilled_view_omits_it(self, vault):
        from tools.story_load import handler
        _delete(vault)
        r = json.loads(handler({"project": "stc", "view": "unfilled"},
                               root_path=str(vault)))
        listed = {e for item in r["unfilled"] for e in item["entities"]}
        assert "kael" not in listed


class TestRestore:
    def test_round_trip_is_byte_identical(self, vault):
        """The whole point: nothing is reconstructed, so nothing is lost."""
        from tools.story_retrieve import handler

        def snap():
            r = json.loads(handler({
                "project": "stc", "entity_type": "character", "id": ["kael"],
                "fields": ["goals_short", "character_value", "one_sentence"],
                "sections": ["all"]}, root_path=str(vault)))
            return r["entities"][0]

        before = snap()
        _delete(vault)
        _edit(vault, "restore")
        assert snap() == before

    def test_restores_its_cascade_children(self, vault):
        _delete(vault)
        _edit(vault, "restore")
        live = _q(vault, "SELECT id FROM entities WHERE type='arc_beat' "
                        "AND parent_id='kael' AND is_deleted=0 ORDER BY id")
        assert [r[0] for r in live] == ["kael-1", "kael-2", "kael-3"]

    def test_restoring_something_live_is_an_error(self, vault):
        r = _edit(vault, "restore")
        assert "not deleted" in r["error"]

    def test_restoring_something_absent_is_an_error(self, vault):
        r = _edit(vault, "restore", slug="never-existed")
        assert "error" in r

    def test_restore_reports_when_it_was_deleted(self, vault):
        _delete(vault)
        assert _edit(vault, "restore")["was_deleted_at"]


class TestSchema:
    def test_columns_exist_in_a_freshly_created_project(self, vault):
        cols = {r[1] for r in _q(vault, "PRAGMA table_info(entities)")}
        assert {"is_deleted", "deleted_at"} <= cols

    def test_an_older_database_is_migrated(self, tmp_path):
        """CREATE TABLE IF NOT EXISTS leaves an old table alone; the readers
        filter on these columns, so an un-migrated project would break them."""
        import sqlite3 as sq
        old = tmp_path / "old.db"
        conn = sq.connect(str(old))
        conn.executescript(
            "CREATE TABLE entities (id TEXT PRIMARY KEY, type TEXT, name TEXT,"
            " one_sentence TEXT, order_key REAL, status TEXT, parent_id TEXT,"
            " location_id TEXT, extra TEXT);"
            "CREATE TABLE relations (from_id TEXT, to_id TEXT, kind TEXT,"
            " note TEXT, \"order\" INTEGER);"
            "CREATE TABLE sections (rowid_ INTEGER, entity_id TEXT,"
            " heading TEXT, body TEXT);")
        conn.commit()
        conn.close()

        from core.db import SCHEMA_SQL, ensure_soft_delete_columns
        conn = sq.connect(str(old))
        conn.executescript(SCHEMA_SQL)
        ensure_soft_delete_columns(conn)
        cols = {r[1] for r in conn.execute("PRAGMA table_info(entities)")}
        conn.close()
        assert {"is_deleted", "deleted_at"} <= cols

    def test_migration_is_idempotent(self, vault):
        from core.db import get_db, ensure_soft_delete_columns
        conn = get_db(vault / "projects" / "stc")
        try:
            ensure_soft_delete_columns(conn)
            ensure_soft_delete_columns(conn)
        finally:
            conn.close()
