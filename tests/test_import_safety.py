"""story_import must never silently destroy work.

The database is the source of truth; Markdown is the stale projection. An import
deletes every row and rebuilds from Markdown — so anything that exists only in
the database is lost. That was silent: a character created at runtime simply
disappeared after a re-import, and the tool reported success.

The guard is deliberately one-directional. A missed warning is acceptable; a
false "you will lose data" would block every legitimate re-import, which is why
this file also pins the no-false-positive cases.
"""
import json
import shutil
import sqlite3

import pytest

from tools.story_create import handler as create_handler
from tools.story_import import handler as import_handler


def _ids(project_path):
    conn = sqlite3.connect(str(project_path / ".story" / "story.db"))
    try:
        return {r[0] for r in conn.execute("SELECT id FROM entities").fetchall()}
    finally:
        conn.close()


def _run(args, vault):
    return json.loads(import_handler(args, root_path=vault))


@pytest.fixture
def imported(fixture_path, tmp_path):
    vault = tmp_path / "v"
    proj = vault / "save-the-children"
    proj.parent.mkdir(parents=True)
    shutil.copytree(str(fixture_path), str(proj))
    _run({"project": str(proj), "confirm": True}, vault)
    return proj, vault


class TestDryRun:
    def test_changes_nothing(self, imported):
        proj, vault = imported
        before = _ids(proj)
        result = _run({"project": str(proj), "dry_run": True}, vault)
        assert result["dry_run"] is True
        assert _ids(proj) == before

    def test_reports_what_would_be_lost(self, imported):
        proj, vault = imported
        create_handler({"entity_type": "character", "slug": "nova", "project": str(proj),
                        "frontmatter": {"name": "Nova", "story_role": "Supporting"}})
        result = _run({"project": str(proj), "dry_run": True}, vault)
        assert "nova" in result["would_be_destroyed"]
        assert "DESTROYED" in result["warning"]
        assert "nova" in _ids(proj), "dry_run must not delete anything"

    def test_no_false_positive_on_clean_project(self, imported):
        """A project that matches its Markdown must report nothing at risk."""
        result = _run({"project": str(imported[0]), "dry_run": True}, imported[1])
        assert result["would_be_destroyed"] == []


class TestGuard:
    def test_refuses_when_work_would_be_lost(self, imported):
        proj, vault = imported
        create_handler({"entity_type": "character", "slug": "nova", "project": str(proj),
                        "frontmatter": {"name": "Nova", "story_role": "Supporting"}})
        result = _run({"project": str(proj)}, vault)          # no confirm
        assert result["success"] is False
        assert "nova" in result["would_be_destroyed"]
        assert "nova" in _ids(proj), "refusal must not delete anything"

    def test_refusal_creates_a_backup(self, imported):
        proj, vault = imported
        create_handler({"entity_type": "character", "slug": "nova", "project": str(proj),
                        "frontmatter": {"name": "Nova", "story_role": "Supporting"}})
        result = _run({"project": str(proj)}, vault)
        assert (proj / ".story" / "backup_check").parent.exists()
        from pathlib import Path
        assert Path(result["backup_created"]).exists()

    def test_confirm_proceeds_and_really_destroys(self, imported):
        """The guard is a speed bump, not a wall — consent must still work."""
        proj, vault = imported
        create_handler({"entity_type": "character", "slug": "nova", "project": str(proj),
                        "frontmatter": {"name": "Nova", "story_role": "Supporting"}})
        result = _run({"project": str(proj), "confirm": True}, vault)
        assert result["success"] is True
        assert "nova" not in _ids(proj)
        assert result["backup_created"]

    def test_clean_import_needs_no_confirm(self, imported):
        """Nothing at risk → no friction. This is the common case."""
        result = _run({"project": str(imported[0])}, imported[1])
        assert result["success"] is True

    def test_first_import_of_empty_project_needs_no_confirm(self, fixture_path, tmp_path):
        vault = tmp_path / "v"
        proj = vault / "save-the-children"
        proj.parent.mkdir(parents=True)
        shutil.copytree(str(fixture_path), str(proj))
        (proj / ".story" / "story.db").unlink(missing_ok=True)
        assert _run({"project": str(proj)}, vault)["success"] is True
