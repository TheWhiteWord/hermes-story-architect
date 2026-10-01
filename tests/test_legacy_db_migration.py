"""A project DB created by an earlier build must still be readable.

Regression: story_load failed with "no such column: is_deleted" on a project
whose story.db predates the soft-delete commit. The migration lived only in
create_schema(), which read-only tools never call.

That repair stays: `is_deleted` and `deleted_at` are columns on `entities`, and
`ALTER TABLE ... ADD COLUMN` is the only way to add one to a table that already
exists. Both live in `ensure_soft_delete_columns` rather than inline in
get_db, so the rule can be tested and stated once.

The `drafts` *table* still needs no repair: create_schema makes it, and
create_project is the only way a real database comes into being, so no project
predates draft staging. That reasoning is unchanged.

What did change is the table's *shape*. B1 made a commit mark its row instead
of deleting it, adding a `status` column — and a drafts table created before
that has no such column. `ensure_draft_status_column` adds it, guarded on the
table existing, which is the same rule the soft-delete repair follows.
"""
import sqlite3


from core.db import ensure_soft_delete_columns, get_db


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


def test_get_db_on_a_fresh_project_does_not_fail(tmp_path):
    """No entities table yet — get_db must not try to migrate nothing."""
    conn = get_db(tmp_path / "brand-new")
    try:
        assert conn.execute("SELECT COUNT(*) FROM sqlite_master").fetchone() is not None
    finally:
        conn.close()


def test_migrations_are_idempotent(tmp_path):
    """get_db runs these on every connection, so running them twice must be a
    no-op rather than an error — that is the whole cost of doing them here.

    Needs a real project: get_db guards the repair on the table existing, and
    calling it directly on a brand-new project is calling it out of contract.
    """
    from core.writes import create_project
    root = tmp_path / "v"
    (root / "projects").mkdir(parents=True)
    create_project("stc", {"name": "STC", "logline": "L"}, root)

    conn = get_db(root / "projects" / "stc")
    try:
        ensure_soft_delete_columns(conn)
        ensure_soft_delete_columns(conn)
    finally:
        conn.close()


def test_a_drafts_table_without_status_gains_it(tmp_path):
    """The shape change B1 made: a drafts table predating it has no `status`.

    The table itself is assumed present — create_schema makes it — so this
    builds one in the old shape and checks the column is added.
    """
    proj = tmp_path / "old-drafts"
    db = proj / ".story" / "story.db"
    db.parent.mkdir(parents=True)
    legacy = sqlite3.connect(str(db))
    legacy.executescript(
        """
        CREATE TABLE drafts (
            id TEXT PRIMARY KEY,
            ops TEXT NOT NULL,
            prev_ops TEXT,
            summary TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL
        );
        """
    )
    legacy.commit()
    legacy.close()

    conn = get_db(proj)
    try:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(drafts)")}
        assert "status" in cols
    finally:
        conn.close()
