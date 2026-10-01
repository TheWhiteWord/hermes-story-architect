"""Purge: the one irreversible operation, and the two guards that protect it.

A soft delete means nothing is ever truly lost, which quietly removes the need
for a safety net — and then quietly makes permanent deletion necessary, because
the database otherwise grows without bound. Purge closes that loop, so it has to
be harder to trigger than any other action:

  1. `purge_confirm` must contain the literal "DELETE <project slug>". The agent
     cannot guess that string, so it can only purge if a human handed it over.
  2. An age floor (default 30 days). Anything deleted in this session stays
     restorable, so tidying up can never destroy a fresh mistake.
"""

import json
import shutil
import sqlite3
from pathlib import Path

import pytest


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


TARGET = {"entity_type": "character", "id": "kael"}


def _edit(vault, action, **args):
    """The two admin-only actions that act on one entity: purge and restore."""
    from tools.story_admin import handler
    return json.loads(handler({
        "action": action, "target": TARGET, "project": "stc",
        "summary": "test", **args}, root_path=str(vault)))


def _exists(vault, entity_id):
    conn = sqlite3.connect(
        str(vault / "projects" / "stc" / ".story" / "story.db"))
    try:
        return bool(conn.execute(
            "SELECT 1 FROM entities WHERE id=?", (entity_id,)).fetchone())
    finally:
        conn.close()


def _delete(vault):
    from core.writes import delete_entity
    return delete_entity(vault / "projects" / "stc",
                         "character", "kael", "test", True)


class TestGuardOneTheConfirmPhrase:
    def test_refuses_without_it(self, vault):
        _delete(vault)
        r = _edit(vault, "purge")
        assert "error" in r
        assert _exists(vault, "kael"), "purge ran without consent"

    def test_refuses_with_the_wrong_project(self, vault):
        _delete(vault)
        r = _edit(vault, "purge", purge_confirm="DELETE some-other-film")
        assert "error" in r
        assert _exists(vault, "kael")

    def test_refuses_a_generic_confirmation(self, vault):
        """`confirm=true` must not be a substitute for the phrase."""
        _delete(vault)
        r = _edit(vault, "purge", confirm=True)
        assert "error" in r
        assert _exists(vault, "kael")

    def test_error_names_the_exact_string(self, vault):
        """So the user can be asked for it, rather than the agent guessing."""
        r = _edit(vault, "purge")
        assert 'DELETE stc' in r["action_required"]

    def test_points_at_restore_as_the_reversible_alternative(self, vault):
        r = _edit(vault, "purge")
        assert "restore" in r["hint"]

    def test_accepts_the_exact_phrase(self, vault):
        _delete(vault)
        r = _edit(vault, "purge", purge_confirm="DELETE stc", older_than_days=0)
        assert r["success"] is True
        assert not _exists(vault, "kael")


class TestGuardTwoTheAgeFloor:
    def test_recent_deletes_are_never_purged_by_default(self, vault):
        _delete(vault)
        r = _edit(vault, "purge", purge_confirm="DELETE stc")
        assert r["purged"] == []
        assert _exists(vault, "kael")

    def test_the_message_explains_why(self, vault):
        _delete(vault)
        r = _edit(vault, "purge", purge_confirm="DELETE stc")
        assert "restorable" in r["message"]

    def test_a_fresh_mistake_stays_recoverable(self, vault):
        """The whole point of the floor: purge cannot destroy this session's work."""
        _delete(vault)
        _edit(vault, "purge", purge_confirm="DELETE stc")
        assert _edit(vault, "restore")["success"] is True

    def test_lowering_the_floor_allows_the_purge(self, vault):
        _delete(vault)
        _edit(vault, "purge", purge_confirm="DELETE stc", older_than_days=0)
        assert not _exists(vault, "kael")

    def test_purged_entities_can_no_longer_be_restored(self, vault):
        _delete(vault)
        _edit(vault, "purge", purge_confirm="DELETE stc", older_than_days=0)
        assert "error" in _edit(vault, "restore")


class TestWhatPurgeRemoves:
    @pytest.fixture
    def purged(self, vault):
        _delete(vault)
        r = _edit(vault, "purge", purge_confirm="DELETE stc", older_than_days=0)
        return vault, r

    def test_it_reports_everything_it_destroyed(self, purged):
        _, r = purged
        ids = {p["id"] for p in r["purged"]}
        assert {"kael", "kael-1", "kael-2", "kael-3"} <= ids

    def test_cascade_children_go_too(self, purged):
        vault, _ = purged
        assert not _exists(vault, "kael-1")

    def test_prose_goes_with_it(self, purged):
        vault, _ = purged
        conn = sqlite3.connect(
            str(vault / "projects" / "stc" / ".story" / "story.db"))
        try:
            n = conn.execute(
                "SELECT count(*) FROM sections WHERE entity_id='kael'"
            ).fetchone()[0]
        finally:
            conn.close()
        assert n == 0

    def test_a_backup_is_taken_first(self, purged):
        _, r = purged
        assert Path(r["backup"]).exists()

    def test_the_backup_actually_contains_the_purged_rows(self, purged):
        """Otherwise the safety net is decorative."""
        _, r = purged
        conn = sqlite3.connect(r["backup"])
        try:
            n = conn.execute(
                "SELECT count(*) FROM entities WHERE id='kael'").fetchone()[0]
        finally:
            conn.close()
        assert n == 1

    def test_live_entities_are_untouched(self, purged):
        vault, _ = purged
        assert _exists(vault, "mira")
        assert _exists(vault, "the-resistance")


class TestPurgeLeavesNoMarkdownToResurrect:
    """Purged rows must not come back through the Markdown either."""

    def test_the_note_is_swept_and_the_entity_stays_gone(self, vault):
        from tools.story_export import handler as export_handler
        from tools.story_import import handler as import_handler
        from tools.story_retrieve import handler as retrieve_handler
        from test_round_trip import note_for, note_rel

        # The sweep only touches files a previous export wrote, so the entity
        # has to be exported once while it still exists. The filename is the
        # title, so the path is only knowable after that first export.
        export_handler({"project": "stc", "confirm": True},
                       root_path=str(vault))
        proj = vault / "projects" / "stc"
        note = note_for(proj, "characters", "kael")
        assert note.exists()

        _delete(vault)
        _edit(vault, "purge", purge_confirm="DELETE stc", older_than_days=0)

        export_handler({"project": "stc", "confirm": True},
                       root_path=str(vault))
        assert not note.exists(), "purged entity's note survived"

        import_handler({"project": "stc", "confirm": True},
                       root_path=str(vault))
        r = json.loads(retrieve_handler({
            "project": "stc", "entity_type": "character", "id": ["kael"],
            "fields": ["one_sentence"]}, root_path=str(vault)))
        assert not r.get("entities"), "purged entity came back"


class TestSoftDeleteSurvivesAnExportImportRoundTrip:
    """A delete must not be undone by an ordinary export → import cycle."""

    def test_deleted_entity_is_not_resurrected(self, vault):
        from tools.story_export import handler as export_handler
        from tools.story_import import handler as import_handler
        from tools.story_retrieve import handler as retrieve_handler
        from test_round_trip import note_for, note_rel
        # Export first, so the manifest knows the file exists. The filename is
        # the title, so the path is captured while the note still exists.
        export_handler({"project": "stc", "confirm": True},
                       root_path=str(vault))
        proj = vault / "projects" / "stc"
        note = note_for(proj, "characters", "kael")
        _delete(vault)
        export_handler({"project": "stc", "confirm": True},
                       root_path=str(vault))
        assert not note.exists()
        import_handler({"project": "stc", "confirm": True},
                       root_path=str(vault))
        r = json.loads(retrieve_handler({
            "project": "stc", "entity_type": "character", "id": ["kael"],
            "fields": ["one_sentence"]}, root_path=str(vault)))
        assert not r.get("entities"), "story_import resurrected a deleted entity"

    def test_its_arc_beats_are_swept_too(self, vault):
        from tools.story_export import handler as export_handler
        from test_round_trip import note_for, note_rel
        export_handler({"project": "stc", "confirm": True},
                       root_path=str(vault))
        proj = vault / "projects" / "stc"
        kael_note = note_rel(proj, "characters", "kael")
        beat_notes = [note_rel(proj, "arcs", b) for b in ("kael-1", "kael-2", "kael-3")]
        _delete(vault)
        r = json.loads(export_handler({"project": "stc", "confirm": True},
                                      root_path=str(vault)))
        assert kael_note in r["files_removed"]
        assert all(b in r["files_removed"] for b in beat_notes)
