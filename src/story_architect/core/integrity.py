"""Read-only integrity check: rows that point at something that is not there.

No foreign keys are declared — adding them would mean rebuilding `sections`,
which carries an external-content FTS5 index and three triggers — so this is
the net under the write paths: tests run it after every kind of write. A
flagged-deleted entity still exists, so a reference to it is not an orphan;
only a reference to a *missing row* is.
"""
from __future__ import annotations

import sqlite3

# key -> SQL returning the offending rows. `entities.id` is a primary key and
# never NULL, so NOT IN is safe; the referencing column may be NULL or ''
# (parent_id, location_id), which mean "no link", not a dangling one.
_CHECKS = {
    "sections":
        "SELECT entity_id, heading FROM sections "
        "WHERE entity_id NOT IN (SELECT id FROM entities)",
    "revisions":
        "SELECT id, entity_id FROM revisions "
        "WHERE entity_id NOT IN (SELECT id FROM entities)",
    "relations_from":
        "SELECT from_id, to_id, kind FROM relations "
        "WHERE from_id NOT IN (SELECT id FROM entities)",
    "relations_to":
        "SELECT from_id, to_id, kind FROM relations "
        "WHERE to_id NOT IN (SELECT id FROM entities)",
    "parent_id":
        "SELECT id, parent_id FROM entities "
        "WHERE parent_id IS NOT NULL AND parent_id != '' "
        "AND parent_id NOT IN (SELECT id FROM entities)",
    "location_id":
        "SELECT id, location_id FROM entities "
        "WHERE location_id IS NOT NULL AND location_id != '' "
        "AND location_id NOT IN (SELECT id FROM entities)",
}


def find_orphans(conn: sqlite3.Connection) -> dict[str, list]:
    """Rows that point at something that is not there. Empty dict = clean.

    Read-only; reports only non-empty categories. `fts` means the full-text
    index is out of step with `sections` (FTS5's own integrity-check raises).
    """
    found = {}
    for key, sql in _CHECKS.items():
        rows = conn.execute(sql).fetchall()
        if rows:
            found[key] = rows
    try:
        # rank=1 is what compares the index against the content table: without
        # it, an external-content FTS5 table only gets its internal structure
        # checked, and a desynced index reads as clean.
        conn.execute("INSERT INTO sections_fts(sections_fts, rank) VALUES('integrity-check', 1)")
    except sqlite3.DatabaseError as e:
        found["fts"] = [str(e)]
    return found
