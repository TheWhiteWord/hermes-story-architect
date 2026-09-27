"""core.writes — the code that changes and deletes.

Three defects pinned here:

1. It kept its own copy of the field→column map, missing `project`. Editing a
   project's logline wrote into `extra` and reported success while the column
   stayed unchanged — a silently lost edit.
2. Delete was unguarded — it ran on a single call with no chance to see what
   would go. It is also soft now (`story_admin(action="restore")` undoes it),
   so the refusal must not claim otherwise.
3. A preview did not exist for any operation.
"""
import json
import shutil
import sqlite3

import pytest

from core.writes import current_values, delete_entity, edit_entity
from tools.story_import import handler as import_handler
from tools.story_retrieve import handler as retrieve_handler


@pytest.fixture
def proj(fixture_path, tmp_path):
    vault = tmp_path / "v"
    p = vault / "projects" / "save-the-children"
    p.parent.mkdir(parents=True)
    shutil.copytree(str(fixture_path), str(p))
    import_handler({"project": "save-the-children", "confirm": True}, root_path=str(vault))
    return p, vault


def _edit(project, entity_type, slug, data, summary="test"):
    return edit_entity(project, entity_type, slug, data, summary)


def _delete(project, entity_type, slug, confirm=None, summary="test"):
    return delete_entity(project, entity_type, slug, summary, confirm)


def _col(project, entity_id, column):
    conn = sqlite3.connect(str(project / ".story" / "story.db"))
    try:
        return conn.execute(f"SELECT {column} FROM entities WHERE id=?", (entity_id,)).fetchone()[0]
    finally:
        conn.close()


def _gone(project, entity_id):
    """Deleted means invisible to every reader, not erased from disk.

    The delete is a soft delete, so the row survives with is_deleted=1 — that
    is what makes `restore` an exact inverse.
    """
    conn = sqlite3.connect(str(project / ".story" / "story.db"))
    try:
        row = conn.execute(
            "SELECT is_deleted FROM entities WHERE id=?", (entity_id,)).fetchone()
        return row is not None and row[0] == 1
    finally:
        conn.close()


def _extra(project, entity_id):
    conn = sqlite3.connect(str(project / ".story" / "story.db"))
    try:
        return json.loads(conn.execute(
            "SELECT extra FROM entities WHERE id=?", (entity_id,)).fetchone()[0] or "{}")
    finally:
        conn.close()


class TestColumnMap:
    """The regression: a duplicated map that went stale and lost edits."""

    def test_project_logline_lands_in_the_column(self, proj):
        p, _ = proj
        assert _edit(p, "project", "ignored",
                     {"logline": "A NEW logline."})["success"] is True
        assert _col(p, "save-the-children", "one_sentence") == "A NEW logline."

    def test_project_logline_does_not_leak_into_extra(self, proj):
        p, _ = proj
        _edit(p, "project", "ignored", {"logline": "A NEW logline."})
        assert "logline" not in _extra(p, "save-the-children")

    def test_retrieve_sees_the_new_logline(self, proj):
        p, vault = proj
        _edit(p, "project", "ignored", {"logline": "A NEW logline."})
        r = json.loads(retrieve_handler(
            {"project": "save-the-children", "entity_type": "project", "id": ["stc"],
             "fields": ["logline"]}, root_path=str(vault)))
        assert r["entities"][0]["fields"]["logline"] == "A NEW logline."

    def test_no_local_map_remains(self):
        """The duplication is the bug; a test that only checks behaviour can
        regress to a second copy without noticing."""
        from core import writes
        assert not hasattr(writes, "ENTITY_COLUMN_MAP")

    def test_other_types_still_write_their_columns(self, proj):
        p, _ = proj
        _edit(p, "character", "kael", {"one_sentence": "Changed."})
        assert _col(p, "kael", "one_sentence") == "Changed."

    def test_scene_title_writes_the_name_column(self, proj):
        p, _ = proj
        _edit(p, "scene", "central-room-day", {"title": "Renamed"})
        assert _col(p, "central-room-day", "name") == "Renamed"


class TestPreviews:
    def test_edit_preview_changes_nothing(self, proj):
        p, _ = proj
        before = _col(p, "kael", "one_sentence")
        r = current_values(p, "character", "kael", {"one_sentence": "PREVIEW ONLY"})
        assert r["dry_run"] is True
        assert r["changes"][0]["field"] == "one_sentence"
        assert r["changes"][0]["to"] == "PREVIEW ONLY"
        assert _col(p, "kael", "one_sentence") == before

    def test_preview_reports_no_change_when_identical(self, proj):
        p, _ = proj
        same = _col(p, "kael", "one_sentence")
        r = current_values(p, "character", "kael", {"one_sentence": same})
        assert r["changes"] == []

    def test_preview_covers_sections_and_extra(self, proj):
        p, _ = proj
        r = current_values(p, "character", "kael",
                           {"Background": "New voice.", "arc_type": "ironic"})
        stored = {c["field"]: c["stored_in"] for c in r["changes"]}
        assert stored["Background"] == "section"
        assert stored["arc_type"] == "extra"

    def test_delete_preview_deletes_nothing(self, proj):
        """The refusal is the preview, so this is the same call as the
        unguarded one — there is no separate dry-run path to get wrong."""
        p, _ = proj
        r = _delete(p, "character", "kael")
        assert "kael" in r["would_delete"]
        assert _col(p, "kael", "one_sentence") is not None


class TestDeleteGuard:
    def test_refused_without_confirm(self, proj):
        p, _ = proj
        r = _delete(p, "character", "kael")
        assert "refused" in r["error"]
        assert _col(p, "kael", "one_sentence") is not None

    def test_refusal_does_not_claim_the_delete_is_irreversible(self, proj):
        """The refusal once said "it cannot be undone", which is a lie now that
        a delete is soft. An agent reading it would tell the user so."""
        p, _ = proj
        r = _delete(p, "character", "kael")
        assert "cannot be undone" not in r["error"]
        assert "restore" in r["action_required"]

    def test_refusal_lists_the_cascade(self, proj):
        p, _ = proj
        r = _delete(p, "character", "kael")
        assert set(r["would_delete"]) == {"kael", "kael-1", "kael-2", "kael-3"}
        assert r["sections_deleted"] > 0

    def test_confirm_proceeds(self, proj):
        p, _ = proj
        assert _delete(p, "character", "mira", confirm=True)["success"] is True
        assert _gone(p, "mira")

    def test_confirm_cascades_arcs(self, proj):
        p, _ = proj
        _delete(p, "character", "kael", confirm=True)
        conn = sqlite3.connect(str(p / ".story" / "story.db"))
        try:
            # Beats are flagged, not erased, so restore brings them back too.
            left = [r[0] for r in conn.execute(
                "SELECT id FROM entities WHERE type='arc_beat' "
                "AND parent_id='kael' AND is_deleted=0")]
        finally:
            conn.close()
        assert left == []

    def test_structural_children_block_even_with_confirm(self, proj):
        """The guard is a hard stop, not a speed bump."""
        p, _ = proj
        r = _delete(p, "sequence", "seq-discovery", confirm=True)
        assert "Cannot delete" in r["error"]
        assert r["blocking_children"]
        assert _col(p, "seq-discovery", "name") is not None

    def test_unknown_entity_is_not_a_confirm_problem(self, proj):
        p, _ = proj
        with pytest.raises(ValueError, match="not found"):
            _delete(p, "character", "ghost", confirm=True)

    def test_deleting_a_scene_leaves_no_dangling_relations(self, proj):
        p, _ = proj
        _delete(p, "scene", "central-room-day", confirm=True)
        conn = sqlite3.connect(str(p / ".story" / "story.db"))
        try:
            dangling = conn.execute(
                "SELECT COUNT(*) FROM relations WHERE from_id='central-room-day' "
                "OR to_id='central-room-day'").fetchone()[0]
        finally:
            conn.close()
        assert dangling == 0
