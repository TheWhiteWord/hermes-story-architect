# Story Architect — SQLite Migration Plan (Staged, Checkpointable)

> **Spec:** `tasks/task_18/spec.md` (schema, decisions, conflicts)
> **Working branch:** `sqlite-migration`
>
> Each phase is independently deliverable, checkpointable, and reversible. No phase is complete until its checkpoints pass. App is pre-publication — no user data, no backward compatibility, no migration from old format. All projects are test fixtures. Build clean, delete old code, no compatibility layers.
>
> Backup: a simple project-copy mechanism (timestamped `.db` copy via `shutil.copy` or `VACUUM INTO`) is sufficient. Not a migration concern — just a "save my project" tool.

---

## Phase 1 — Schema + DB Layer

**Goal:** Create `core/db.py` (connection, pragmas, schema). Create `story_export` and `story_import` as on-demand tools. No migration from old format — app is pre-publication, all projects are test fixtures. Verify export/import round-trip against the fixture.

**Scope:**
- New `core/db.py` — database connection, pragma setup (`WAL`, `busy_timeout=3000`), schema creation, table existence checks
- **Connection lifecycle** — open short-lived connection per tool call (open → execute → commit → close), never hold a process-lifetime connection
- New `tools/story_export.py` — reads `story.db` → writes markdown vault (same format as current notes, for git/backup/inspection)
- New `tools/story_import.py` — reads markdown vault → populates `story.db` (restoring from export or creating projects from shared markdown)
- Register `story_export` + `story_import` as new tools. Old tools untouched.
- `story_create(entity_type="project")` creates `.story/story.db` directly — no migration path
- Delete: `core/index.py` enrichment machinery, `core/paths.py`, `ENTITY_FOLDERS`, `NESTED_ENTITIES`, `tools/story_index.py`

**Backup:** `story_backup` tool — `shutil.copy` the `.db` file to a timestamped copy, or `VACUUM INTO` for a guaranteed-consistent snapshot. Simple, on-demand, no migration semantics.

**Verification:**
1. `story_create(entity_type="project", slug="test-proj")` → `.story/story.db` exists with schema
2. `story_import` populates DB from fixture `tests/fixtures/save-the-children/`
3. `story_export` writes vault to a temp dir
4. Import → export → diff → 0 diffs (modulo YAML formatting normalization)
5. All existing `test_core.py` tests pass — old tool paths still work (writes still go to markdown in Phase 1; DB is populated via import only)

**Assumptions:**
- Schema in spec (§4) captures every frontmatter field and body section
- `frontmatter` library handles FM/section parsing in import/export (live path uses only stdlib `sqlite3`)
- No legacy format to preserve — delete old code without compatibility layers
- FTS5 available in user's Python `sqlite3` build (verify: `python3 -c "import sqlite3; print(sqlite3.sqlite_version)"`)

**Open questions:**
- YAML formatting normalization (indentation, key quoting, multi-line strings) — acceptable to differ from original fixtures, or must match byte-for-byte?

**Checkpoint — must pass before starting Phase 2:**
- [ ] Fixture round-trip: import → export → diff → 0 diffs (modulo YAML formatting)
- [ ] All existing `test_core.py` tests still pass unchanged
- [ ] Connection lifecycle verified: each tool call opens + closes its own connection
- [ ] `story_export` + `story_import` registered and usable; no tool reads from DB yet
- [ ] `story_backup` creates timestamped copy of `.db` file

---

## Phase 2 — Swap Read Paths to DB (Shadow Reads)

**Goal:** `story_load`, `story_retrieve`, `story_search`, `story_dashboard` query the DB. `story_edit` + `story_create` still write markdown, then re-run `story_import` to repopulate DB. Deliberately awkward intermediate state — validates reads-from-DB behave identically to reads-from-files in real usage, without risking write-path bugs.

**Scope:**
- `story_load`: column-oriented summary query (project metadata + entities table + full relations table) instead of `index.yaml`
- `story_retrieve`: read from SELECT on `sections` instead of `frontmatter.load`
- `story_search`: FTS5 query on `sections_fts` + `entities` instead of folder glob
- `story_dashboard`: ingest from DB queries instead of YAML + raw note reads
- `story_edit`/`story_create` workflow: write markdown → `refresh_index` → auto-reimport to `.story/story.db`
- Keep old index generation machinery functional (still needed to produce source-of-truth data that reimport reads from)
- Add helper in `core/db.py`: `get_project_summary(project_path)` returning column-oriented payload
- Add helper in `core/db.py`: `get_entity_sections(project_path, entity_id)` for retrieve
- Add helper in `core/db.py`: `search_sections(project_path, query)` returning FTS5 hits
- Add helper in `core/db.py`: `get_dashboard_data(project_path)` returning all 6 injection shapes
- Test updates for coverage — old write path still tested in parallel with new read path

**Verification:**
1. Column-oriented format: `story_load` returns `{project, entities: {cols, rows}, relations: {cols, rows}}` — verify shape matches spec D2 exactly
2. Relations completeness: every relation from the fixture's markdown FM is present in the summary's `relations.rows` — no missing edges, no duplicates
3. No derived arrays: `story_load` response has no `scenes[]`, `plots[]`, `sequences_list[]`, `arc_beats_list[]` — only flat rows
4. No sections list: `story_load` response has no `sections` array — sections are schema, not data
5. Arc-beat search fix (Conflict 3): query keyword that only exists in arc beat body → new `story_search` finds it, old one misses it
6. "Which scenes does this plot touch?" — answerable from `story_load` summary alone, no `story_retrieve` needed
7. "What scenes has Kael been in?" — answerable from summary via `relations WHERE to_id='kael' AND kind='character_scene'`
8. Token budget: `story_load` on 50-scene fixture ≤ 5K tokens (target ~2K); verify by JSON-serializing the response and counting tokens
9. Save-the-children fixture: `story_retrieve` via DB path — match against existing YAML-path response (modulo YAML ↔ JSON serialization differences)
10. Write `story_edit` → change reflected in DB via new import (write path unchanged — still markdown + index)
11. Old tool sequence: `create_handler({type:"character",...})` → `load_handler(...)` → result imported → DB returns equivalent

**Assumptions:**
- DB imported from current markdown is byte-equivalent to markdown data (Phase 1 checkpoint guarantees round-trip on fixture)
- `story_retrieve` returns only `##` headings that exist — same set in DB as in files
- `story_search` FTS5 matches same set as old substring search (except arc beats — improvement, not regression)
- Dashboard HTML + JS are agnostic to whether data came YAML or SQL
- Column-oriented encoding is acceptable to the agent — the agent can parse `cols` + `rows` without issue (it's an LLM, it handles arrays)
- No new data can enter system without a markdown write first (new writes not allowed in Phase 2 either)

**Open questions:**
- Performance of reimport-on-every-edit for large projects — should batch debounce?
- Two index.yaml writes per edit (one for old code, one for DB refresh) — acceptable overhead?

**Checkpoint — must pass before starting Phase 3:**
- [ ] All 5 verification queries answerable from `story_load` summary alone
- [ ] Token budget: ` story_load` on fixture ≤ 5K tokens
- [ ] Search finds all arc beats in fixture
- [ ] Round-trip export from DB (Phase 1) still passes after Phase 2 code changes
- [ ] Old write path still works — `story_edit` returns success, fixture unchanged
- [ ] Rollback: delete `.story/story.db` → reads fail gracefully, old tool paths still work identically

**Checking prior phases at each step:**
- [ ] Phase 1 round-trip verifier still passes after Phase 2 code changes

---

## Phase 3 — Swap Write Paths to DB + Retire Markdown

**Goal:** `story_edit` + `story_create` write directly to DB. Delete `index.yaml` machinery, `.story/` folder as source of truth, `story_index` tool. Export/import become the only bridges between DB and markdown vault (for git, manual inspection, restoration from backup). Verify against a copy of real project, not just the synthetic fixture.

**Scope:**
- `story_edit` → DB transactions (entities UPDATE, sections INSERT/UPDATE, relations write)
- `story_create` → DB INSERT + auto-order + parent validation
- `story_delete_entity` → soft delete flag (`is_deleted=1`)
- Remove: `core/index.py` enrichment machinery, `core/paths.py`, `ENTITY_FOLDERS`, `NESTED_ENTITIES`, `write_index` / `refresh_index` code
- Remove: `tools/story_index.py` registered tool
- Remove: `index.yaml` source — kept only as `index.yaml.bak` during Phase 3 itself, deleted after verification
- `story_resolve` — retarget to `<project>/.story/story.db` existence check (if not found → marks project for migration on next read)
- Import/export tools become permanent bridge — not throwaway
- `story_create(entity_type="project")` scaffolding creates `.story/story.db` with schema + seed data instead of folders + index.yaml
- Second queue: Phase 2 reimport machinery removed — the world after Phase 3 has exactly one source of truth: DB

**Verification:**
1. Copy of real project → `story_import` once → all 3 phases of behavior preserved:
   - Read tools return identical entities
   - Edit tools persist to DB, immediately visible via read tools
   - `write` → next `database` read (content visible)
   - Delete → `load` excludes deleted item → `search` excludes deleted prose
   - Recycle bin semantics: deleted entity detectable via `is_deleted`
2. Full regression — all 19 `test_core.py` tests (now updated for DB writes) pass
3. Round-trip: `export` the modified DB → re-import cleanly
4. `story_load` and `story_retrieve` on new-real fixture equivalent (minus any YAML ↔ JSON formatting differences alone)
5. Search FTS performance — 200-note project search returns under 50ms
6. Open dashboard → verify no missing entities or sections compared to Phase 2 DB-path behavior

**Assumptions:**
- Write transactions are atomic (any failure → rollback, no partial writes)
- Auto-order computed correctly — matches existing order sequence for scenes with existing siblings
- `_get_next_order` verified to match new DB query (current: max+1 from file system; new: max+1 from DB)
- Soft delete does not affect deleted entity's historical relations/references (they remain queryable via `is_deleted=1` for audit review)
- Phase 2 write-then-import loop is no longer needed (write to DB is the source of truth, no intermediate representation)

**Open questions:**
- Soft-deleted relations from deleted entity — preserve or cascade? (current behavior: file moved to recycle-bin absorbs relations implicitly)
- Dashboard upsert on new entity write — should `story_dashboard` hook fire on every DB write?
- Old `index.yaml` deletion — archive in git permanently, only `.story/story.db` remains live?

**Final Checkpoint — must pass before considering Phase 3 complete:**
- [ ] All updated tests pass
- [ ] 3-edit scenario on real-project-copy: each `story_edit` → next `story_load` + `story_retrieve` shows change immediately and consistently
- [ ] Round-trip export → re-import produces same DB state
- [ ] Search query covering all entity types finds expected results
- [ ] Existing fixture: full regression pass (19/19 tests)
- [ ] Real project copy: at least `story_load` + `story_edit` + `story_retrieve` verified manually
- [ ] Rollback path: `.story/story.db` deleted (after copy/handoff) → system no longer starts — needs clear migration message to user (view only via `story_import` tool)

**Checking prior phases at each step:**
- [ ] Phase 1 schema verifier still passes on any exported fixture after Phase 3
- [ ] Phase 2 compatibility test (old write + new read) is now obsolete — removed
- [ ] Re-confirm: search finds all arc beats (Phase 2 test case)

---

## Phase 4 — Cleanup + Regression Coverage

**Goal:** Remove dead paths. Update tests. Run real-project validation. State clearly that migration is complete — data layer is DB-only and stable.

**Scope:**
- Remove all remaining markdown-write references from `core/index.py` (keep `assemble_scene_content` + `compute_structural_stats` rewrite as SQL-based helpers)
- Remove `core/paths.py` file entirely — no longer referenced
- Remove all old test fixtures that tested removed functionality (e.g., `_parse_arcs`, `_enrich_*`)
- Add DB-specific tests: import round-trip + relations query + search FTS
- Update `plan/plan.md` task tracking to remove D10 migration section (that's what this plan replaces)
- `story_export` — promote from "migration tool" to first-class "for git/backups" tool

**Verification:**
- All old tests rewritten or deleted — no references to removed modules
- New tests pass: import/export round-trip test, search arc beat test, soft-delete test, relation JOIN test
- `core/index.py` enrichment functions gone — no stale references in codebase
- `tools/story_index.py` removed from plugin.yaml + __init__.py
- Project test fixture: all new and old tests agree — 100% coverage of DB read/write paths
- Real user project test: edit/search/report verified clean by user before branch consolidation

**Assumptions:**
- No regression within Phase 3 behavior — if found, go back
- Old markdown vault path never re-introduces itself as source
- User has verified Phase 3 completion against real project

**Open questions:**
- Test coverage strategy — 100% of tool handlers tested via real Hermes dispatcher?
- Performance baseline: `story_load` no longer loaded with 50K tokens of index — full summary only
- Remove `index.yaml` test coverage — delete entirely, including all tests verifying consistency

**Final Checkpoint — must pass before merge to dev:**
- [ ] All tests pass — new + remaining legacy (excluding explicitly removed features)
- [ ] No references to `core/index.py` enrichment, `core/paths.py`, `tools/story_index.py`, `write_index`, `refresh_index`
- [ ] Real project test passed by user
- [ ] README / spec documentation updated to reflect new architecture
- [ ] Rollback plan documented

**Checking prior phases at each step:**
- [ ] Phase 1 round-trip still passes against any new schema exports (if schema evolved)

---

## Cross-Phase Rules

1. **Each phase is independently shippable.** If a later phase reveals a schema flaw, fix the schema and re-run ALL prior checkpoints — the fix is part of that phase, not postponed.
2. **No silent deviations.** Code behavior that doesn't match the spec must surface as a conflict for user review, not be silently absorbed into the implementation.
3. **Round-trip test must remain green at every phase.** If a phase breaks Phase 1 round-trip, fix it as part of that phase.
4. **No backward compatibility.** App is pre-publication. Delete old code without compatibility layers. No migration paths, no legacy format retention.
5. **Each phase documents its assumptions explicitly before starting.**
6. **Each phase's checkpoint must pass before the next phase starts. No exceptions.**
7. **Conflict flag verification:** before each phase merges, re-run the code-vs-spec conflict check. Any new discovery → surface to user immediately and pause.
8. **Modular design.** Each tool handler is self-contained. Shared logic (DB access, entity serialization, relation queries) belongs in `core/`, not in individual tools. A tool never imports another tool's handler.
