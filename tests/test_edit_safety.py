"""story_edit — the tool that changes and deletes.

Three defects pinned here:

1. It kept its own copy of the field→column map, missing `project`. Editing a
   project's logline wrote into `extra` and reported success while the column
   stayed unchanged — a silently lost edit.
2. Delete was unguarded — it ran on a single call with no chance to see what
   would go. It is also soft now (`action="restore"` undoes it), so the refusal
   must not claim otherwise.
3. `dry_run` did not exist for any action.
"""
import json
import shutil
import sqlite3

import pytest

from tools.story_edit import handler as edit_handler
from tools.story_import import handler as import_handler
from tools.story_retrieve import handler as retrieve_handler


@pytest.fixture
def proj(fixture_path, tmp_path):
    vault = tmp_path / "v"
    p = vault / "projects" / "save-the-children"
    p.parent.mkdir(parents=True)
    shutil.copytree(str(fixture_path), str(p))
    import_handler({"project": "save-the-children", "confirm": True}, vault_path=str(vault))
    return p, vault


def _edit(vault, action, entity_type, slug, **args):
    target = {"entity_type": entity_type, "slug": slug, "project": "save-the-children"}
    return json.loads(edit_handler(
        {"action": action, "target": target, "summary": "test", **args},
        vault_path=str(vault)))


def _col(project, entity_id, column):
    conn = sqlite3.connect(str(project / ".story" / "story.db"))
    try:
        return conn.execute(f"SELECT {column} FROM entities WHERE id=?", (entity_id,)).fetchone()[0]
    finally:
        conn.close()


def _gone(project, entity_id):
    """Deleted means invisible to every reader, not erased from disk.

    The delete is a soft delete (task_18), so the row survives with
    is_deleted=1 — that is what makes `restore` an exact inverse.
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
        p, vault = proj
        assert _edit(vault, action="edit_note", entity_type="project", slug="ignored",
                     data={"logline": "A NEW logline."})["success"] is True
        assert _col(p, "save-the-children", "one_sentence") == "A NEW logline."

    def test_project_logline_does_not_leak_into_extra(self, proj):
        p, vault = proj
        _edit(vault, action="edit_note", entity_type="project", slug="ignored",
              data={"logline": "A NEW logline."})
        assert "logline" not in _extra(p, "save-the-children")

    def test_retrieve_sees_the_new_logline(self, proj):
        p, vault = proj
        _edit(vault, action="edit_note", entity_type="project", slug="ignored",
              data={"logline": "A NEW logline."})
        r = json.loads(retrieve_handler(
            {"project": "save-the-children", "entity_type": "project", "id": ["stc"],
             "fields": ["logline"]}, vault_path=str(vault)))
        assert r["entities"][0]["fields"]["logline"] == "A NEW logline."

    def test_no_local_map_remains(self):
        """The duplication is the bug; a test that only checks behaviour can
        regress to a second copy without noticing."""
        from tools import story_edit
        assert not hasattr(story_edit, "_ENTITY_COLUMN_MAP")

    def test_other_types_still_write_their_columns(self, proj):
        p, vault = proj
        _edit(vault, action="edit_note", entity_type="character", slug="kael",
              data={"one_sentence": "Changed."})
        assert _col(p, "kael", "one_sentence") == "Changed."

    def test_scene_title_writes_the_name_column(self, proj):
        p, vault = proj
        _edit(vault, action="edit_note", entity_type="scene", slug="central-room-day",
              data={"title": "Renamed"})
        assert _col(p, "central-room-day", "name") == "Renamed"


class TestDryRun:
    def test_edit_preview_changes_nothing(self, proj):
        p, vault = proj
        before = _col(p, "kael", "one_sentence")
        r = _edit(vault, action="edit_note", entity_type="character", slug="kael",
                  data={"one_sentence": "PREVIEW ONLY"}, dry_run=True)
        assert r["dry_run"] is True
        assert r["changes"][0]["field"] == "one_sentence"
        assert r["changes"][0]["to"] == "PREVIEW ONLY"
        assert _col(p, "kael", "one_sentence") == before

    def test_preview_reports_no_change_when_identical(self, proj):
        p, vault = proj
        same = _col(p, "kael", "one_sentence")
        r = _edit(vault, action="edit_note", entity_type="character", slug="kael",
                  data={"one_sentence": same}, dry_run=True)
        assert r["changes"] == []

    def test_preview_covers_sections_and_extra(self, proj):
        p, vault = proj
        r = _edit(vault, action="edit_note", entity_type="character", slug="kael",
                  data={"Background": "New voice.", "arc_type": "ironic"},
                  dry_run=True)
        stored = {c["field"]: c["stored_in"] for c in r["changes"]}
        assert stored["Background"] == "section"
        assert stored["arc_type"] == "extra"

    def test_delete_preview_deletes_nothing(self, proj):
        p, vault = proj
        r = _edit(vault, action="delete_entity", entity_type="character", slug="kael",
                  dry_run=True)
        assert "kael" in r["would_delete"]
        assert _col(p, "kael", "one_sentence") is not None

    def test_reorder_preview_changes_nothing(self, proj):
        p, vault = proj
        before = _col(p, "central-room-day", "order_key")
        r = _edit(vault, action="reorder", entity_type="scene", slug="central-room-day",
                  order_context={"ordered_ids": ["the-core-day", "central-room-night",
                                                 "central-room-day"]}, dry_run=True)
        assert r["dry_run"] is True
        assert r["changes"]
        assert _col(p, "central-room-day", "order_key") == before


class TestDeleteGuard:
    def test_refused_without_confirm(self, proj):
        p, vault = proj
        r = _edit(vault, action="delete_entity", entity_type="character", slug="kael")
        assert "refused" in r["error"]
        assert _col(p, "kael", "one_sentence") is not None

    def test_refusal_does_not_claim_the_delete_is_irreversible(self, proj):
        """The refusal once said "it cannot be undone", which is a lie now that
        a delete is soft. An agent reading it would tell the user so."""
        _, vault = proj
        r = _edit(vault, action="delete_entity", entity_type="character", slug="kael")
        assert "cannot be undone" not in r["error"]
        assert "restore" in r["action_required"]

    def test_dry_run_adds_nothing_to_delete(self, proj):
        """The consent gate already returns the full preview, so dry_run on a
        delete is dead weight — the refusal IS the preview. Pinned so the
        schema does not start advertising it again."""
        _, vault = proj
        plain = _edit(vault, "delete_entity", "character", "kael")
        dry = _edit(vault, "delete_entity", "character", "kael", dry_run=True)
        assert plain == dry
        assert "would_delete" in plain, "the refusal is the preview"

    def test_refusal_lists_the_cascade(self, proj):
        p, vault = proj
        r = _edit(vault, action="delete_entity", entity_type="character", slug="kael")
        assert set(r["would_delete"]) == {"kael", "kael-1", "kael-2", "kael-3"}
        assert r["sections_deleted"] > 0

    def test_confirm_proceeds(self, proj):
        p, vault = proj
        assert _edit(vault, action="delete_entity", entity_type="character",
                     slug="mira", confirm=True)["success"] is True
        assert _gone(p, "mira")

    def test_confirm_cascades_arcs(self, proj):
        p, vault = proj
        _edit(vault, action="delete_entity", entity_type="character", slug="kael",
              confirm=True)
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
        p, vault = proj
        r = _edit(vault, action="delete_entity", entity_type="sequence",
                  slug="seq-discovery", confirm=True)
        assert "Cannot delete" in r["error"]
        assert r["blocking_children"]
        assert _col(p, "seq-discovery", "name") is not None

    def test_unknown_entity_is_not_a_confirm_problem(self, proj):
        p, vault = proj
        r = _edit(vault, action="delete_entity", entity_type="character",
                  slug="ghost", confirm=True)
        assert "not found" in r["error"]

    def test_deleting_a_scene_leaves_no_dangling_relations(self, proj):
        p, vault = proj
        _edit(vault, action="delete_entity", entity_type="scene",
              slug="central-room-day", confirm=True)
        conn = sqlite3.connect(str(p / ".story" / "story.db"))
        try:
            dangling = conn.execute(
                "SELECT COUNT(*) FROM relations WHERE from_id='central-room-day' "
                "OR to_id='central-room-day'").fetchone()[0]
        finally:
            conn.close()
        assert dangling == 0
