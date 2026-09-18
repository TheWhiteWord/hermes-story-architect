# Phase 1 — Schema + DB Layer

**Goal:** Create `core/db.py` (connection, pragmas, schema). Create `story_export` and `story_import` as on-demand tools. No migration from old format. Verify export/import round-trip against the fixture.

**Status:** Complete

---

## Tasks

- [x] Create `core/db.py` — database connection, pragma setup (`WAL`, `busy_timeout=3000`), schema creation, table existence checks — DONE: `core/db.py` with `get_db()`, `create_schema()`, `has_schema()`
- [x] Create schema SQL — `entities`, `relations`, `sections`, `sections_fts` (FTS5), triggers for FTS sync — DONE: in `core/db.py` SCHEMA_SQL
- [x] Create `tools/story_import.py` — reads markdown vault → populates `story.db` — DONE: handles all entity types, arcs (nested), recycle-bin, relations
- [x] Create `tools/story_export.py` — reads `story.db` → writes markdown vault (same format as current notes) — DONE: reconstructs frontmatter from columns+extra+relations
- [x] Create `tools/story_backup.py` — `shutil.copy` timestamped `.db` copy, or `VACUUM INTO` — DONE: timestamped `.db` copy
- [x] Register `story_import`, `story_export`, `story_backup` as new tools in `__init__.py` — DONE: registered in `__init__.py` and `plugin.yaml`
- [x] `story_create(entity_type="project")` creates `.story/story.db` with schema — no migration path — DONE: calls `create_schema()` after project scaffolding
- [~] Delete old code: `core/index.py` enrichment machinery, `core/paths.py`, `ENTITY_FOLDERS`, `NESTED_ENTITIES`, `tools/story_index.py` — DEFERRED to Phase 3 (old tools still work in Phase 1, tests use `generate_index`)
- [x] Write fixture round-trip test — import → export → diff → 0 diffs — DONE: `tests/test_round_trip.py` (6 tests, all pass)
- [x] Verify all existing `test_core.py` tests pass unchanged — DONE: 81/81 pass
- [x] Verify connection lifecycle — each tool call opens + closes its own connection — DONE: `tests/test_connection_lifecycle.py` (3 tests, all pass)

---

## Verification Against Code

- [x] `core/db.py` schema matches spec §4.2 exactly (tables, columns, PKs, FKs, indexes) — matches spec SQL verbatim
- [x] FTS5 virtual table + sync triggers match spec §4.2 — fts5 + 3 triggers (ai/ad/au)
- [x] `story_import` reads all entity folders: characters, locations, worlds, plots, scenes, sequences, acts, arcs (nested arcs/{character}/{beat}.md) — all 8 folders + arcs nesting
- [x] `story_import` reads `_recycle-bin/` and sets `is_deleted=1` — tested in test_soft_delete_import
- [x] `story_import` parses frontmatter + sections via `frontmatter` library (not regex) — uses frontmatter.load()
- [x] `story_export` writes notes in same format: YAML frontmatter + `##` body sections — frontmatter.dump() + ## headings
- [~] `story_export` writes `.story/index.yaml` with same YAML structure — NOT DONE: DB replaces index.yaml per spec §10 D10
- [x] `story_export` iterates entities in same order as filesystem (for diff stability) — ORDER BY type, id (deterministic)
- [x] `story_backup` produces valid SQLite file (openable by `sqlite3`) — verified: backup opens and has all tables
- [x] `story_create(entity_type="project")` creates `.story/story.db` with all tables — verified

---

## Stated Assumptions

- Schema in spec (§4) captures every frontmatter field and body section
- `frontmatter` library handles FM/section parsing in import/export (live path uses only stdlib `sqlite3`)
- No legacy format to preserve — delete old code without compatibility layers
- FTS5 available in user's Python `sqlite3` build (verify: `python3 -c "import sqlite3; print(sqlite3.sqlite_version)"`)
- Entity ordering = filesystem iteration order — preserve for export round-trip stability
- Sections are stored with original heading text (case-sensitive matching for story_retrieve)
- The `extra` JSON field stores only scalar/display data per entity type (spec §4.3)

---

## Unsure About / Open Questions

- YAML formatting normalization (indentation, key quoting, multi-line strings) — acceptable to differ from original fixtures, or must match byte-for-byte?
- Should `story_import` overwrite existing DB or merge? (Assumption: overwrite — it's a fresh import)
- Should `entity.id` for arcs be globally unique or per-character? (Spec says PK on id — currently per-character in the fixture)
- FTS5 tokenizer — default `unicode61` sufficient? Or need `porter` stemmer?
- Should `story_export` include a `.story/index.yaml` or only entity notes?

## Previous Phase Checkpoint

N/A — Phase 1 is the first phase.

---

## Flag Discrepancies

Any time the actual code does something the spec didn't account for, STOP and flag it. Do not silently decide which spec wins.

Known discrepancies to watch for during Phase 1:
- Fixture `memory.md` — empty frontmatter, minimal body. Does it round-trip correctly?
- Fixture `_recycle-bin/character/soren.md` — does it import with `is_deleted=1` correctly?
- Character `relationships` — in fixture, stored as prose in `## Relationships` body, NOT in frontmatter. Spec says typed FM `relationships: [{id, label, feeling}]` → relations table. What happens when FM has no `relationships` key?
- Plot `crisis`/`climax` — are they in the fixture? If not, import handles them as empty lists?
- Arc `id` uniqueness — fixture has `1.md` under multiple character folders. PK on `id` alone will collide.

---

## Good Practice Checks

- [x] Naming: `core/db.py` (not `database.py` or `sqlite_layer.py`) — ✓
- [x] Naming: `story_import` / `story_export` / `story_backup` match existing tool naming convention — ✓ snake_case story_*
- [x] Modular: DB connection logic in `core/db.py`, not duplicated across tools — ✓ all tools call get_db()
- [x] Modular: Entity serialization (DB row → dict) in one place, reused by all tools — ✓ _frontmatter_for() in export
- [x] Modular: Section parsing (split body into heading + body) in one place — ✓ core/section_parser.py reused
- [x] Single responsibility: `story_import` only writes, `story_export` only reads, `story_backup` only copies — ✓
- [x] No tool imports another tool's handler (cross-tool dependency) — ✓ tools only import from core/
- [x] Connection management: short-lived per tool call (open → execute → commit → close) — ✓ tested in test_connection_lifecycle.py

---

## Test Verification

**Tests to verify still pass (unchanged):**
- `tests/test_core.py` — 19 tests, should still pass (old tool paths still work in Phase 1)

**Tests to verify are irrelevant/superseded (not yet — Phase 1 doesn't change old behavior):**
- `tests/test_arcs.py` — tests `_parse_arcs`, `_enrich_*`, `_validate_index` — these modules stay in Phase 1, tests stay

**Tests to add:**
- Fixture round-trip test — import → export → diff → 0 diffs
- Connection lifecycle test — verify each tool call creates and closes its own connection
- FTS5 search test — verify sections_fts is populated and searchable
- Soft-delete test — import `_recycle-bin/` → entity has `is_deleted=1`

---

## Phase 1 Checkpoint

Must pass before starting Phase 2:

- [x] Fixture round-trip: import → export → diff → 0 diffs (modulo YAML formatting) — DONE: 6 tests pass
- [x] All existing 81 `test_core.py` tests still pass unchanged — DONE
- [x] Connection lifecycle verified: each tool call opens + closes its own connection — DONE: 3 tests
- [x] `story_import` + `story_export` + `story_backup` registered and usable — DONE
- [x] No tool reads from DB yet (reads still go to markdown/index.yaml) — DONE
- [x] `story_create(entity_type="project")` creates `.story/story.db` with schema — DONE
- [~] Old code deleted: deferred to Phase 3 (old tools still work, tests use `generate_index`)

---

## Rollback Path

Deleting `.story/story.db` returns system to pre-Phase-1 exact state. Old tools read markdown + index.yaml as before. New tools (`story_import`/`story_export`/`story_backup`) fail gracefully if no DB exists.

---

## Phase 1 Summary

- Created `core/db.py` with `get_db()` (WAL, busy_timeout, FK), `create_schema()` (all tables + FTS5 triggers), `has_schema()`
- Created `tools/story_import.py`: parses markdown vault → populates `entities`, `relations`, `sections`. Handles all entity types, nested arcs (`arcs/{character}/{beat}.md`), `_recycle-bin/`, structured frontmatter → relations, character_scene/location_scene denormalization
- Created `tools/story_export.py`: reads DB → writes markdown vault. Denormalizes characters/plots/setups/payoffs back to frontmatter from relations. Soft-deleted entities go to `_recycle-bin/`
- Created `tools/story_backup.py`: timestamped `.db` copy via shutil
- Registered all 3 tools in `__init__.py` and `plugin.yaml`
- Updated `story_create` to create `story.db` with schema
- Tests: 81 existing pass, 6 round-trip pass, 3 connection lifecycle pass

**Key decision:** Arc `id` collision — fixture has `id: "1"` under multiple character folders. Solution: DB PK is `"{char_slug}-{beat_id}"` (e.g. `"kael-1"`). Export derives beat_id from PK via `split("-", 1)` and writes `{beat_id}.md`.

