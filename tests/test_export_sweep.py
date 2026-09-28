"""story_export must mirror the database — in both directions.

Writing notes was already correct: a full import → export → wipe → re-import
round trip is byte-identical on entities, sections and relations. What export
could not do was stop writing. An entity deleted from the database left its .md
behind, and the next story_import read that file and resurrected it.

The sweep is driven by a manifest of the paths the last export wrote, so it can
only ever remove files this tool created. A hand-authored note the database has
never seen is never a candidate — that is the property most worth protecting,
because the alternative is export silently eating a user's own writing.
"""
import json
import shutil
import sqlite3

import pytest

from tools.story_export import handler as export_handler
from tools.story_import import handler as import_handler

from test_round_trip import note_for, note_rel


def _export(project, vault):
    # Resolve by name against the vault so the tool's own path resolution runs.
    return json.loads(export_handler({"project": "save-the-children"}, root_path=str(vault)))


def _reimport(project, vault):
    (project / ".story" / "story.db").unlink()
    import_handler({"project": "save-the-children", "confirm": True}, root_path=str(vault))


def _delete(project, *ids):
    conn = sqlite3.connect(str(project / ".story" / "story.db"))
    marks = ",".join("?" * len(ids))
    conn.execute(f"DELETE FROM entities WHERE id IN ({marks})", ids)
    conn.execute(f"DELETE FROM sections WHERE entity_id IN ({marks})", ids)
    conn.commit()
    conn.close()


def _ids(project):
    conn = sqlite3.connect(str(project / ".story" / "story.db"))
    try:
        return {r[0] for r in conn.execute("SELECT id FROM entities")}
    finally:
        conn.close()


@pytest.fixture
def proj(fixture_path, tmp_path):
    # The vault layout the resolver expects: <vault>/projects/<project>.
    vault = tmp_path / "v"
    p = vault / "projects" / "save-the-children"
    p.parent.mkdir(parents=True)
    shutil.copytree(str(fixture_path), str(p))
    import_handler({"project": "save-the-children", "confirm": True}, root_path=str(vault))
    return p, vault


class TestIdempotent:
    def test_second_export_removes_nothing(self, proj):
        """The regression that deleted a whole project: absolute vs relative paths."""
        p, vault = proj
        assert _export(p, vault)["files_removed"] == []
        assert _export(p, vault)["files_removed"] == []
        assert _export(p, vault)["files_removed"] == []

    def test_repeated_exports_keep_every_note(self, proj):
        p, vault = proj
        for _ in range(3):
            _export(p, vault)
        assert note_for(p, "characters", "kael").exists()
        assert (p / "project.md").exists()
        assert note_for(p, "arcs", "kael-1").exists()
        assert (p / ".story" / "memory.md").exists()

    def test_first_export_never_removes(self, proj):
        """No manifest means nothing is known to have been written by us."""
        p, vault = proj
        assert not (p / ".story" / "exported.json").exists()
        assert _export(p, vault)["files_removed"] == []


class TestDeleteSurvivesRoundTrip:
    def test_deleted_note_is_swept(self, proj):
        p, vault = proj
        _export(p, vault)                       # establishes the manifest
        # The filename is the title, so the path is looked up by id before the
        # note is deleted — after that there is nothing left to find.
        kael_note = note_rel(p, "characters", "kael")
        _delete(p, "kael")
        assert kael_note in _export(p, vault)["files_removed"]
        assert not (p / kael_note).exists()

    def test_deleted_entity_stays_deleted(self, proj):
        p, vault = proj
        _export(p, vault)
        _delete(p, "kael", "kael-1")
        _export(p, vault)
        _reimport(p, vault)
        assert "kael" not in _ids(p)

    def test_untouched_entities_survive(self, proj):
        p, vault = proj
        _export(p, vault)
        _delete(p, "kael")
        _export(p, vault)
        _reimport(p, vault)
        ids = _ids(p)
        assert "mira" in ids and "dr-elena-voss" in ids

    def test_emptied_arc_folder_is_pruned(self, proj):
        p, vault = proj
        _export(p, vault)
        # The folder is the character's title, not their id. marcus-chen has two
        # beats; mira has none, so the folder cannot be found through her.
        marcus_dir = note_for(p, "arcs", "marcus-chen-1").parent
        conn = sqlite3.connect(str(p / ".story" / "story.db"))
        beats = [r[0] for r in conn.execute(
            "SELECT id FROM entities WHERE type='arc_beat' AND parent_id='marcus-chen'")]
        conn.close()
        _delete(p, *beats)
        _export(p, vault)
        assert not marcus_dir.exists()


class TestHandAuthoredNotesAreSafe:
    def test_unknown_note_survives_every_export(self, proj):
        """The property that keeps export from eating a user's own writing."""
        p, vault = proj
        (p / "characters" / "handwritten.md").write_text(
            "---\nname: Hand\n---\n\n## Personality\n\nBy a human.\n"
        )
        for _ in range(3):
            _export(p, vault)
        assert (p / "characters" / "handwritten.md").exists()

    def test_corrupt_manifest_is_ignored_not_fatal(self, proj):
        p, vault = proj
        (p / ".story" / "exported.json").write_text("{not json")
        result = _export(p, vault)
        assert result["success"] is True
        assert result["files_removed"] == []
        assert note_for(p, "characters", "kael").exists()

    def test_manifest_omits_its_own_and_story_dir(self, proj):
        p, vault = proj
        _export(p, vault)
        manifest = json.loads((p / ".story" / "exported.json").read_text())
        assert all(not m.startswith(".story/") or m == ".story/memory.md" for m in manifest)
