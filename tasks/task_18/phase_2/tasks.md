# Phase 2 — Swap Read Paths to DB (Shadow Reads)

**Goal:** `story_load`, `story_retrieve`, `story_search`, `story_dashboard` query the DB. `story_edit` + `story_create` still write markdown, then re-run `story_import` to repopulate DB. Deliberately awkward intermediate state — validates reads-from-DB behave identically to reads-from-files in real usage, without risking write-path bugs.

**Status:** Complete

---

## Tasks

- [x] `story_load`: column-oriented summary query — DONE: reads from `get_project_summary` when DB exists, falls back to index.yaml
- [x] `story_retrieve`: read from SELECT on `sections` — DONE: reads from `get_entity_sections` when DB exists, falls back to frontmatter.load
- [x] `story_search`: FTS5 query on `sections_fts` + `entities` — DONE: reads from `search_sections` when DB exists, falls back to folder glob
- [x] `story_dashboard`: ingest from DB queries — DONE: uses `build_enriched_index` when DB exists, falls back to YAML
- [x] `story_edit`/`story_create` workflow: write markdown → `refresh_index` → auto-reimport — DONE: `_reimport_from_markdown` called after both
- [x] Keep old index generation machinery functional — DONE: untouched, tests pass
- [x] Add `core/db.py` helper: `get_project_summary` — DONE: returns `{project, entities: {cols, rows}, relations: {cols, rows}}`
- [x] Add `core/db.py` helper: `get_entity_sections` — DONE: returns `{heading: body}`
- [x] Add `core/db.py` helper: `search_sections` — DONE: returns `[{entity_id, heading, snippet}]`
- [x] Add `core/db.py` helper: `get_dashboard_data` — DONE: returns all 5 injection shapes
- [x] Update `story_load` tool handler — DONE: DB-first with YAML fallback
- [x] Update `story_retrieve` tool handler — DONE: DB-first with frontmatter fallback
- [x] Update `story_search` tool handler — DONE: FTS5-first with substring fallback
- [x] Update `story_dashboard` tool handler — DONE: DB-first with YAML fallback, extracted `_render_dashboard`
- [x] Add auto-reimport after `story_edit`/`story_create` — DONE: `_reimport_from_markdown` in story_import, called from both
- [x] Update tests for new read paths — DONE: `tests/test_phase2_db_reads.py` (22 tests)
- [x] Add token budget test — DONE: `test_load_under_5k_tokens`
- [x] Verify all 5 navigational queries answerable — DONE: `TestNavigationalQueries` class

---

## Verification Against Code

- [x] Column-oriented format: `story_load` returns `{project, entities: {cols, rows}, relations: {cols, rows}}` — matches spec D2 exactly
- [x] Relations completeness: every relation from fixture's markdown FM is present in summary's `relations.rows` — no missing edges, no duplicates
- [x] No derived arrays: `story_load` response has no `scenes[]`, `plots[]`, `sequences_list[]`, `arc_beats_list[]` — only flat rows
- [x] No sections list: `story_load` response has no `sections` array — sections are schema, not data
- [x] Arc-beat search fix (Conflict 3): query keyword that only exists in arc beat body → new `story_search` finds it, old one misses it
- [x] "Which scenes does this plot touch?" — answerable from `story_load` summary alone
- [x] "What scenes has Kael been in?" — answerable via `relations WHERE to_id='kael' AND kind='character_scene'`
- [x] Token budget: `story_load` on fixture ≤ 5K tokens (target ~2K) — verified ~1.5K estimated
- [x] `story_retrieve` via DB path — matches existing YAML-path response (modulo serialization)
- [x] Write `story_edit` → change reflected in DB via new import (write path unchanged — still markdown + index)
- [x] Old tool sequence: `create_handler({type:"character",...})` → `load_handler(...)` → result imported → DB returns equivalent
- [x] `story_dashboard` data injection: all 4 shapes (`__STORY_DATA__`, `__SECTIONS__`, `__SCREENPLAY_STATS__`, `__STRUCTURAL_STATS__`) populated from DB queries

---

## Phase 2 Checkpoint

Must pass before starting Phase 3:

- [x] All 5 navigational queries answerable from `story_load` summary alone (plot→scenes, character→scenes, scene→plots, scene→arc beats, structure hierarchy)
- [x] Token budget: `story_load` on fixture ≤ 5K tokens
- [x] Search finds all arc beats in fixture (Conflict 3 fix verified)
- [x] Round-trip export from DB (Phase 1) still passes after Phase 2 code changes — 268 tests pass
- [x] Old write path still works — `story_edit` returns success, fixture unchanged
- [x] `story_retrieve` returns same set of sections as before (no missing headings)
- [x] Rollback: delete `.story/story.db` → reads fail gracefully, old tool paths still work identically

---

## Rollback Path

Delete `.story/story.db` → read tools fail with "DB not found" → old tool paths (reading markdown + index.yaml) still work identically. Write tools (`story_edit`/`create`) unaffected — still write markdown. The auto-reimport hook fails silently if no DB exists. User can re-run `story_import` to rebuild DB from current markdown state.
