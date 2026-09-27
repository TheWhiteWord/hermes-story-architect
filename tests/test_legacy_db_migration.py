"""A project DB created by an earlier build must still be readable.

Regression: story_load failed with "no such column: is_deleted" on a project
whose story.db predates the soft-delete commit. The migration lived only in
create_schema(), which read-only tools never call.
"""
import sqlite3
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from core.db import get_db  # noqa: E402


def test_get_db_migrates_a_legacy_database(tmp_path):
    """A DB with the pre-soft-delete entities table is repaired on open."""
    proj = tmp_path / "legacy"
    db = proj / ".story" / "story.db"
    db.parent.mkdir(parents=True)

    legacy = sqlite3.connect(str(db))
    legacy.executescript(
        """
        CREATE TABLE entities (
            id TEXT PRIMARY KEY,
            type TEXT NOT NULL,
            name TEXT
        );
        INSERT INTO entities VALUES ('a1', 'character', 'Old Hero');
        """
    )
    legacy.commit()
    legacy.close()

    conn = get_db(proj)
    try:
        assert conn.execute("SELECT name FROM entities WHERE is_deleted=0").fetchall() == [
            ("Old Hero",)
        ]
    finally:
        conn.close()


def test_get_db_creates_the_drafts_table_on_a_legacy_database(tmp_path):
    """A DB written before draft staging exists gains the drafts table on open.

    Drafts live in their own table, so a project created by an earlier build
    has no such table — and read-only tools never call create_schema(). Same
    regression as the soft-delete columns, same fix: migrate in get_db.
    """
    proj = tmp_path / "legacy-drafts"
    db = proj / ".story" / "story.db"
    db.parent.mkdir(parents=True)

    legacy = sqlite3.connect(str(db))
    legacy.executescript(
        """
        CREATE TABLE entities (
            id TEXT PRIMARY KEY,
            type TEXT NOT NULL,
            name TEXT
        );
        INSERT INTO entities VALUES ('a1', 'character', 'Old Hero');
        """
    )
    legacy.commit()
    legacy.close()

    conn = get_db(proj)
    try:
        tables = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )}
        assert "drafts" in tables
    finally:
        conn.close()


def test_get_db_on_a_fresh_project_does_not_fail(tmp_path):
    """No entities table yet — get_db must not try to migrate nothing."""
    conn = get_db(tmp_path / "brand-new")
    try:
        assert conn.execute("SELECT COUNT(*) FROM sqlite_master").fetchone() is not None
    finally:
        conn.close()
