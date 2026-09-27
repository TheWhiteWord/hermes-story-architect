"""story_admin: the five operations that are not entity authoring.

Two things are worth guarding here, and they pull in opposite directions.

The confirmations must hold: `delete_project` destroys every entity in a
project, and nothing in the database can undo it. A test that only checked the
happy path would pass whether or not the guard worked.

And the list must stay a *listing*. `resolve_project` opens a database per
candidate to recover a display name, which is fine when there is one project to
resolve — copying that into an enumeration would mean a connection per project
on every call, on a root that may hold hundreds.
"""
import json
import shutil
import sqlite3
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from tools import story_admin  # noqa: E402


def _run(args, root):
    """Call the handler the way Hermes does, and parse what it returns."""
    return json.loads(story_admin.handler(args, root_path=str(root)))


@pytest.fixture
def root(tmp_path, fixture_path):
    """A story root holding one real project, copied from the fixture.

    Tests that need to touch the project database itself use
    `root / "projects" / "save-the-children"` — the same tree the tool reaches,
    so a delete staged through core.writes and undone through the tool are
    talking about one database.
    """
    projects = tmp_path / "projects"
    projects.mkdir()
    shutil.copytree(fixture_path, projects / "save-the-children")
    return tmp_path


# ─── list_projects ───

class TestListProjects:
    def test_finds_the_project(self, root):
        result = _run({"action": "list_projects"}, root)
        assert result["success"] is True
        assert result["count"] == 1
        assert result["projects"][0]["slug"] == "save-the-children"
        assert result["projects"][0]["has_database"] is True

    def test_opens_no_database(self, root, monkeypatch):
        """A listing must not connect. One connection per project is a trap
        on a large root, and it would happen on every single call."""
        opened = []
        real_connect = sqlite3.connect

        def spy(*args, **kwargs):
            opened.append(args[0] if args else kwargs.get("database"))
            return real_connect(*args, **kwargs)

        monkeypatch.setattr(sqlite3, "connect", spy)
        result = _run({"action": "list_projects"}, root)
        assert result["count"] == 1, "the listing still has to work"
        assert not opened, f"list_projects opened {len(opened)} database(s)"

    def test_reports_a_folder_with_no_database_rather_than_hiding_it(self, root):
        (root / "projects" / "half-made").mkdir()
        result = _run({"action": "list_projects"}, root)
        slugs = {p["slug"]: p for p in result["projects"]}
        assert slugs["half-made"]["has_database"] is False

    def test_empty_root_is_not_an_error(self, tmp_path):
        result = _run({"action": "list_projects"}, tmp_path)
        assert result["success"] is True and result["count"] == 0


# ─── create_project ───

class TestCreateProject:
    def test_creates_folder_and_database(self, root):
        result = _run({"action": "create_project", "project": "new-film",
                       "frontmatter": {"name": "New Film"}}, root)
        assert result["success"] is True
        assert (root / "projects" / "new-film" / ".story" / "story.db").exists()

    def test_appears_in_the_listing(self, root):
        _run({"action": "create_project", "project": "new-film",
              "frontmatter": {"name": "New Film"}}, root)
        assert _run({"action": "list_projects"}, root)["count"] == 2

    def test_missing_required_field_reports_and_creates_nothing(self, root):
        result = _run({"action": "create_project", "project": "thin"}, root)
        assert "error" in result
        assert not (root / "projects" / "thin").exists()

    def test_traversal_slug_refused(self, root):
        result = _run({"action": "create_project", "project": "../escape",
                       "frontmatter": {"name": "X"}}, root)
        assert "error" in result
        assert not (root.parent / "escape").exists()


# ─── delete_project ───

class TestDeleteProject:
    def test_refused_without_the_confirmation_string(self, root):
        """A boolean would be guessable. A string the agent cannot invent is
        the whole point — so a missing one must change nothing at all."""
        project = root / "projects" / "save-the-children"
        result = _run({"action": "delete_project",
                       "project": "save-the-children"}, root)
        assert "error" in result
        assert "DELETE save-the-children" in result["action_required"]
        assert project.exists(), "the project must survive a refused delete"
        assert (project / ".story" / "story.db").exists()

    def test_a_confirm_for_another_project_is_refused(self, root):
        """The string names the project, so a right-shaped string for the
        wrong project must not pass."""
        project = root / "projects" / "save-the-children"
        result = _run({"action": "delete_project", "project": "save-the-children",
                       "delete_confirm": "DELETE some-other-film"}, root)
        assert "error" in result
        assert project.exists()

    def test_with_the_confirmation_the_project_is_gone(self, root):
        project = root / "projects" / "save-the-children"
        result = _run({"action": "delete_project", "project": "save-the-children",
                       "delete_confirm": "DELETE save-the-children"}, root)
        assert result["success"] is True
        assert not project.exists()

    def test_the_backup_survives_the_delete(self, root):
        """A backup written inside the project folder would be destroyed by
        the very delete it was taken for, so it has to land outside."""
        result = _run({"action": "delete_project", "project": "save-the-children",
                       "delete_confirm": "DELETE save-the-children"}, root)
        backup = Path(result["backup"])
        assert backup.exists(), f"backup missing: {backup}"
        assert backup.parent == root / "backups", \
            "the backup must be outside the deleted tree"
        # And it must be a usable database, not an empty file.
        conn = sqlite3.connect(str(backup))
        try:
            n = conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0]
        finally:
            conn.close()
        assert n > 0, "the backup must contain the project's data"

    def test_a_folder_that_is_not_a_project_is_refused(self, root):
        (root / "projects" / "just-a-folder").mkdir()
        result = _run({"action": "delete_project", "project": "just-a-folder",
                       "delete_confirm": "DELETE just-a-folder"}, root)
        assert "error" in result
        assert (root / "projects" / "just-a-folder").exists(), \
            "rmtree must not run on something that is not a project"

    def test_unknown_project_reports_rather_than_deleting(self, root):
        result = _run({"action": "delete_project", "project": "no-such-film",
                       "delete_confirm": "DELETE no-such-film"}, root)
        assert "error" in result
        assert (root / "projects" / "save-the-children").exists()


# ─── restore ───

class TestRestore:
    def test_undoes_a_soft_delete_exactly(self, root):
        from core.db import get_db
        from core.writes import delete_entity

        project = root / "projects" / "save-the-children"
        conn = get_db(project)
        try:
            sections_before = conn.execute(
                "SELECT COUNT(*) FROM sections WHERE entity_id='the-garden'"
            ).fetchone()[0]
        finally:
            conn.close()
        assert sections_before > 0, "the fixture must have prose to lose"

        delete_entity(project, "location", "the-garden", "s", confirm=True)

        result = _run({"action": "restore", "project": "save-the-children",
                       "target": {"entity_type": "location", "slug": "the-garden"},
                       "summary": "the garden"}, root)
        assert result["success"] is True
        assert result["entity_id"] == "the-garden"

        conn = get_db(project)
        try:
            assert conn.execute(
                "SELECT is_deleted FROM entities WHERE id='the-garden'"
            ).fetchone()[0] == 0
            assert conn.execute(
                "SELECT COUNT(*) FROM sections WHERE entity_id='the-garden'"
            ).fetchone()[0] == sections_before, "prose must come back intact"
        finally:
            conn.close()

    def test_restoring_a_live_entity_reports_rather_than_pretending(self, root):
        result = _run({"action": "restore", "project": "save-the-children",
                       "target": {"entity_type": "location",
                                  "slug": "the-central-room"}}, root)
        assert "error" in result
        assert "not deleted" in result["error"]

    def test_unknown_entity_reports(self, root):
        result = _run({"action": "restore", "project": "save-the-children",
                       "target": {"entity_type": "location", "slug": "nowhere"}}, root)
        assert "error" in result


# ─── purge ───

class TestPurge:
    def test_refused_without_the_confirmation_string(self, root):
        result = _run({"action": "purge", "project": "save-the-children"}, root)
        assert "error" in result
        assert "DELETE save-the-children" in result["action_required"]

    def test_age_floor_keeps_recent_deletes_restorable(self, root):
        """A delete from this session must never be purgeable, however the
        caller words the confirmation."""
        from core.writes import delete_entity
        delete_entity(root / "projects" / "save-the-children",
                      "location", "the-garden", "s", confirm=True)

        result = _run({"action": "purge", "project": "save-the-children",
                       "purge_confirm": "DELETE save-the-children"}, root)
        assert result["success"] is True
        assert result["purged"] == [], "nothing is old enough yet"
        assert "restorable" in result["message"]

    def test_purges_once_past_the_floor(self, root):
        from core.db import get_db
        from core.writes import delete_entity

        project = root / "projects" / "save-the-children"
        delete_entity(project, "location", "the-garden", "s", confirm=True)
        # Backdate past the floor.
        conn = get_db(project)
        try:
            conn.execute("UPDATE entities SET deleted_at='2000-01-01T00:00:00' "
                         "WHERE is_deleted=1")
        finally:
            conn.close()

        result = _run({"action": "purge", "project": "save-the-children",
                       "purge_confirm": "DELETE save-the-children"}, root)
        assert result["success"] is True
        assert [p["id"] for p in result["purged"]] == ["the-garden"]
        assert Path(result["backup"]).exists(), "purge takes a backup first"

        conn = get_db(project)
        try:
            assert conn.execute(
                "SELECT COUNT(*) FROM entities WHERE id='the-garden'"
            ).fetchone()[0] == 0
        finally:
            conn.close()


# ─── the tool boundary ───

def test_unknown_action_reports_rather_than_crashing(root):
    result = _run({"action": "delete_everything"}, root)
    assert "error" in result


def test_authoring_is_not_reachable_here():
    """story_admin must not become a back door around story_draft.

    The whole point of the tool split is that entity content cannot be written
    without the user seeing a preview. A create/edit action appearing here
    would quietly reopen the path this design closed.
    """
    actions = set(story_admin.SCHEMA["properties"]["action"]["enum"])
    assert not actions & {"create", "edit", "edit_note", "delete_entity", "reorder"}
