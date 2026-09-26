"""A backup that silently loses data is worse than no backup.

Two defects, both invisible at the call site because the tool reported
`success: true` either way:

1. `shutil.copy2` on a WAL database copies only the main file. Recent writes
   living in `story.db-wal` were simply absent from the backup — a stale
   snapshot presented as a current one. `Connection.backup()` fixes this.
2. The timestamp had one-second granularity, so two backups in the same second
   overwrote each other. The second destroyed the first, both reporting success.

Both `story_backup` and `story_import` take backups, so both now share one
implementation in `core.db.backup_database`.
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
                        lambda: {"vault_path": str(v)})
    from tools.story_import import handler
    handler({"project": "stc", "confirm": True}, vault_path=str(v))
    return v


def _backup(vault):
    from tools.story_backup import handler
    return json.loads(handler({"project": "stc"}, vault_path=str(vault)))


def _backups(project):
    return sorted(p.name for p in (project / ".story").glob("story_*.db"))


def _query(db_path, sql, args=()):
    conn = sqlite3.connect(str(db_path))
    try:
        return conn.execute(sql, args).fetchone()
    finally:
        conn.close()


class TestWalSafety:
    def test_backup_includes_committed_writes_still_in_the_wal(self, vault):
        """The defect: a writer holding the WAL, then a plain file copy.

        Everything below the file-copy line is the regression guard.
        """
        project = vault / "projects" / "stc"
        db = project / ".story" / "story.db"

        writer = sqlite3.connect(str(db), isolation_level=None)
        writer.execute("UPDATE entities SET name='UNCHECKPOINTED' WHERE id='kael'")
        try:
            assert (project / ".story" / "story.db-wal").exists()
            result = _backup(vault)
        finally:
            writer.close()

        name = _query(Path(result["backup"]),
                      "SELECT name FROM entities WHERE id='kael'")[0]
        assert name == "UNCHECKPOINTED", "backup is stale — it missed the WAL"

    def test_backup_holds_every_entity(self, vault):
        result = _backup(vault)
        project = vault / "projects" / "stc"
        live = _query(project / ".story" / "story.db",
                      "SELECT count(*) FROM entities")[0]
        assert _query(Path(result["backup"]),
                      "SELECT count(*) FROM entities")[0] == live

    def test_backup_is_a_complete_database(self, vault):
        """Usable, not just a byte copy: all tables, indexes and FTS present."""
        result = _backup(vault)
        conn = sqlite3.connect(result["backup"])
        try:
            tables = {r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")}
        finally:
            conn.close()
        assert {"entities", "relations", "sections"} <= tables
        assert any(t.startswith("sections_fts") for t in tables)


class TestNoCollisions:
    def test_repeated_backups_do_not_overwrite(self, vault):
        """Two in the same second used to write the same filename."""
        project = vault / "projects" / "stc"
        before = set(_backups(project))
        made = [Path(_backup(vault)["backup"]).name for _ in range(3)]
        assert len(set(made)) == 3, f"backups collided: {made}"
        assert set(_backups(project)) - before == set(made)

    def test_every_backup_file_still_exists_on_disk(self, vault):
        paths = [Path(_backup(vault)["backup"]) for _ in range(3)]
        assert all(p.exists() for p in paths)

    def test_imports_own_backup_does_not_clobber_a_manual_one(self, vault):
        """story_import backs up too — the two paths share one implementation."""
        from core.db import backup_database
        project = vault / "projects" / "stc"
        first = backup_database(project)
        second = backup_database(project)
        assert first != second
        assert Path(first).exists() and Path(second).exists()


class TestContract:
    def test_reports_where_the_backup_is(self, vault):
        result = _backup(vault)
        assert result["success"] is True
        assert Path(result["backup"]).exists()

    def test_missing_database_is_an_error(self, vault):
        (vault / "projects" / "empty").mkdir()
        from tools.story_backup import handler
        r = json.loads(handler({"project": "empty"}, vault_path=str(vault)))
        assert "error" in r

    def test_the_live_database_is_untouched(self, vault):
        """Copying must not checkpoint away or otherwise disturb the source."""
        before = _backups(vault / "projects" / "stc")
        _backup(vault)
        db = vault / "projects" / "stc" / ".story" / "story.db"
        assert db.exists()
        assert _query(db, "SELECT count(*) FROM entities")[0] > 0
        assert len(_backups(vault / "projects" / "stc")) > len(before)

    def test_backup_directory_stays_inside_the_project(self, vault):
        """Backups live in .story/, not scattered in the system temp dir."""
        result = _backup(vault)
        assert str(vault) in result["backup"]
        assert ".story" in result["backup"]
