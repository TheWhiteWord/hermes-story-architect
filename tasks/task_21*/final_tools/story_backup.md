# story_backup

**Role:** copy the project database to a timestamped file.

---

## What it protects, and what it does not

**The database is the source of truth.** Every `story_edit`, `story_create` and
`story_memory` write persists to `story.db` and nowhere else. The Markdown files
are a *derived export*, written by `story_export`, and go stale immediately:

```
story_edit(edit_note) → DB: 'ESCAPE OR DIE'   .md: (unchanged)
delete the .db + story_import → edit is gone
```

So a `.db` backup is the only thing standing between a disk problem and lost
work — including `story_memory` entries, which are never exported to Markdown at
all.

**Not protected:** a `.md` file damaged outside the tools. Backups cover the
database, not the vault folder.

## When it fires

| Trigger | Automatic? |
|---|---|
| explicit `story_backup` call | no — the agent must choose to |
| `story_import` refusing (DB-only entities would be destroyed) | **yes** |
| `story_import` immediately before the wipe | **yes** |
| `story_edit` `delete_entity` | **no** |
| `story_edit` / `create` / `memory` / `export` | no |

The coverage is worth stating plainly: the operation that *rebuilds from
Markdown* is protected, and the one that *permanently deletes prose* is not.
`story_edit`'s response suggests taking a backup first, but that is advice to
the agent, not behaviour.

## Two defects fixed

### 1. WAL — the copy was silently stale

`shutil.copy2` copies the database file only. The database runs in **WAL mode**,
so recent writes can sit in `story.db-wal` and not yet be in the main file:

```
writer open, data in WAL → backup contained "Kael", live db had "UNCHECKPOINTED"
```

A stale snapshot presented as current, with `success: true`. Now uses
`sqlite3.Connection.backup()`, which goes through SQLite and includes
everything committed. Verified: the uncheckpointed value is present, entity
counts match, and all tables including the FTS index come across.

### 2. Second-granularity timestamps — backups overwrote each other

```
call 1 → story_20260926_015528.db
call 2 → story_20260926_015528.db   ← destroyed call 1, still success: true
```

Two backups in the same second collapsed into one file. A manual backup taken
just before an import could be overwritten *by that import's own safety copy* —
the opposite of the intent. Now suffixed `_1`, `_2`, … so every snapshot
survives.

## One implementation, two callers

`story_import` has its own `_backup()`. Both defects were duplicated there, so
both now call **`core.db.backup_database()`** — one copy path that cannot drift.

## Known gap

**There is no restore tool.** A backup can be taken but not put back by any
tool. Restoring by hand means closing the DB, replacing `story.db` with the
backup, and deleting the `-wal` / `-shm` sidecars. Undo is a separate design
question — not decided here.

## Tests

`tests/test_backup_integrity.py` — 10 tests: WAL freshness, entity-count
parity, table completeness, three rapid backups all surviving, the live DB left
untouched, and backups staying inside `.story/`.
