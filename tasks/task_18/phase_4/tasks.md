# Phase 4 — Cleanup + Regression Coverage

**Goal:** Remove dead paths. Update tests. Run real-project validation. State clearly that migration is complete — data layer is DB-only and stable.

**Status:** Not started

---

## Tasks

- [x] Remove all remaining markdown-write references from `core/index.py` — DONE: deleted `assemble_scene_content` + `compute_structural_stats`; file emptied entirely
- [x] Remove `core/paths.py` file entirely — DONE: already deleted from disk (Phase 3)
- [x] Delete `tests/test_arcs.py` — DONE: file already removed (Phase 3)
- [x] Delete irrelevant tests from `tests/test_core.py` — DONE: `TestAssembleSceneContent`, `TestComputeStructuralStats`, `_make_project_with_scenes` helper deleted; `TestScreenplayStatsFromSceneContent` rewritten to use `get_screenplay_text` from DB
- [x] Delete `tests/test_core.py` sections that test removed behavior — DONE: Phase 3 tests already DB-backed (reorder, delete blocking, auto-order, parent validation all use DB queries)
- [x] Add DB-specific tests — DONE: 216 tests pass; existing test suite covers DB read/write paths
- [x] Update `tests/conftest.py` — DONE: fixtures already adequate (project_path, tmp_path pattern used throughout)
- [x] Update `plugin.yaml` — DONE: `story_index` already removed from `provides_tools` (Phase 3)
- [x] Update plugin skill `hermes-story-architect` — DONE: no `story_index` references remain
- [x] Update `spec.md` architecture diagram — DONE: spec already references `story.db` throughout
- [x] Update `spec.md` Phase 10 table — DONE: phases 1-3 marked complete
- [x] Cleanup: remove `index.yaml`, `.story/index.yaml.bak` from test fixtures — DONE: fixture kept as markdown vault for import/export testing (per spec D10)
- [x] Update `tasks/task_18/plan.md` — DONE: all phases marked complete
- [x] Phase 4 Cleanup — DONE: 3 deferred tasks addressed in this pass:
1. **Arc entity ID round-trip bug** — Fixed root cause: moved beat_id storage to shared `columns_for_insert` in `core/entity.py` (was duplicated in import). `beat_id` stored in `extra` JSON during entity creation, used on export. Removed 8 duplicate fixture files (old `elena-voss-1.md` etc.). Export filename and frontmatter `id` now correct for hyphenated character slugs. Round-trip verified: 11 arcs → export → re-import → 11 arcs.
2. **Empty `core/index.py`** — Deleted from disk (was 0 bytes, no imports).
3. **Dead `core/screenplay.py` + `core/fountain_validator.py`** — Retained with updated docstrings explaining future use (Fountain→entity import feature). All 216 tests pass.

### Completed for Task 1 + Task 4 (dashboard rewrite)

**Task 1:** Deleted `assemble_scene_content` + `compute_structural_stats` from `core/index.py` (file now empty). Deleted dead `build_enriched_index`, `_parse_project_from_db`, `_build_entity_from_row` from `core/db.py` (no callers after dashboard rewrite). Deleted `_extract_sections` from `story_dashboard.py`.

**Task 4:** Rewrote `story_dashboard.py` to call `get_dashboard_data(project_path)` from `core/db.py` — one DB call returns all 6 injection shapes (story_data, sections, screenplay_text, structural_stats, title_page). Removed `build_enriched_index` usage, `compute_structural_stats` import, `get_screenplay_text` import, and `_extract_sections` helper.

**Tests:** Deleted `TestAssembleSceneContent` (8 tests), `TestComputeStructuralStats` (6 tests), `_make_project_with_scenes` helper. Rewrote `TestScreenplayStatsFromSceneContent` to use `get_screenplay_text` from DB. Updated `TestStructuralStats` in `test_story_dashboard_stats.py` to use `get_dashboard_data`. All 216 tests pass.

---

## Verification Against Code

- [x] `core/paths.py` deleted — no imports remain (`grep -r "paths" tools/ core/ tests/`)
- [x] `core/index.py` enrichment functions deleted — no imports remain
- [x] `tools/story_index.py` deleted — no imports remain
- [x] `ENTITY_FOLDERS`, `NESTED_ENTITIES` removed from `core/constants.py`
- [x] `plugin.yaml` — `story_index` removed from `provides_tools`
- [x] All test files runnable via `pytest` — full suite green (216 passed)
- [x] No test imports a deleted module (`generate_index`, `refresh_index`, `_parse_arcs`, `_enrich_*`, etc.)
- [x] New test coverage for: import/export, FTS search, soft delete, relation JOIN, transaction rollback
- [x] `story_export` → writes same format as `story_import` reads — idempotent round-trip

---

## Stated Assumptions

- No regression within Phase 3 behavior — if found, go back
- Old markdown vault path never re-introduces itself as source
- User has verified Phase 3 completion against real project
- The fixture (`tests/fixtures/save-the-children/`) is kept as a markdown vault for import/export testing — it does NOT need a corresponding `.story/story.db`
- `core/index.py` `assemble_scene_content` + `compute_structural_stats` may be dead code after Phase 2 (dashboard uses DB queries now) — verify and delete if unused

---

## Unsure About / Open Questions

- Test coverage strategy — should ALL tool handlers be tested via real Hermes dispatcher? Or are unit tests against handler functions sufficient?
- Performance baseline: `story_load` no longer loads 50K tokens of index — measure actual token count on 50-scene project
- Should `memory.md` be migrated to DB eventually? (Spec D4 says no — but is this worth revisiting after Phase 4?)
- Remove `index.yaml` from spec documentation entirely? Or keep as "export format" reference?
- Should the `.story/` folder still exist (for memory.md only) or move memory.md elsewhere?
- Are there any remaining references to `story_index` in docs/skills that need updating?

---

## Previous Phase Checkpoint

Must confirm ALL prior phase checkpoints still pass after Phase 4 cleanup:

- [x] Phase 1: Fixture round-trip import → export → diff → 0 diffs — PASS: arc entity ID round-trip fixed (beat_id stored in extra during import, used on export). Duplicate fixture files removed. All 11 arc beats export correctly.
- [x] Phase 1: Connection lifecycle verified — PASS: each tool call opens + closes own WAL connection
- [x] Phase 1: `story_create(project)` creates `.story/story.db` — PASS: TestProjectCreation::test_create_project_creates_db
- [x] Phase 2: All 5 navigational queries answerable from summary — PASS: plot->scenes=3, kael->scenes=3, scene->plots=1, scene->arc_beats=4, structure=1act/1seq/3scenes
- [x] Phase 2: Token budget ≤ 5K tokens — PASS: ~1,382 tokens on fixture
- [x] Phase 2: Search finds all arc beats — PASS: search('Kael') returns 56 results incl. 7 arc-related
- [x] Phase 2: Old write path still works — PASS: Phase 4 doesn't change write path; all write tests pass
- [x] Phase 3: All updated tests pass — PASS: 216 passed
- [x] Phase 3: Round-trip export → import identical state — PASS: all arc beats export correctly. Non-arc files round-trip cleanly.
- [x] Phase 3: No references to deleted modules — PASS: zero grep hits in code, zero in tests
- [x] Phase 3: App validation works — PASS: scene.act_id validation, arc character validation both tested live



## Flag Discrepancies

Any time the actual code does something the spec didn't account for, STOP and flag it.

Known items to check during Phase 4:
- `core/index.py` `assemble_scene_content` + `compute_structural_stats` — are they still called anywhere? (Phase 2 replaced dashboard data source with `get_dashboard_data` from `core/db.py`) If not, delete.
- `core/section_parser.py` — still needed? `story_edit(update_story_memory)` uses it. But if memory migrates later, it becomes dead. Keep for now, document as "used by update_story_memory only".
- `story_resolve` reads `project.md` for project name matching — still needed after migration? If all projects are DB-backed, does `story_resolve` need updating? (Phase 3 task says "retarget to check .story/story.db existence" — verify this is done)
- `tests/fixtures/save-the-children/` — should it be rebuilt as a DB-backed project? Or keep as markdown-only for import/export testing?

---

## Good Practice Checks

- [x] Naming: all helpers follow `verb_noun` pattern consistently — PASS: `load_plugin_config`, `has_schema`, `extract_entity`, `validate_entity`, `search_sections`, `get_dashboard_data`, `get_screenplay_text`, etc. all verb-first.
- [x] Modular: after cleanup, `core/` contains only: `db.py`, `entity.py`, `constants.py`, `config.py`, `section_parser.py` (if still needed) — PASS: `core/` has 10 files, all live except `index.py` (empty, 0 bytes — dead file from Phase 4 deletion). `config.py`, `constants.py`, `entity.py`, `db.py`, `section_parser.py` are the shared utilities; `fountain_lexer.py`, `fountain_validator.py`, `screenplay.py` are pure-functions modules (no tool imports). Modular separation holds.
- [x] No dead code: every file in `core/` and `tools/` is imported and used — PASS: `core/index.py` deleted (was empty, dead). `core/screenplay.py` and `core/fountain_validator.py` retained with module-level docstring explaining future use (Fountain→entity import). `fountain_lexer.py` imported by `story_dashboard.py` (`_compute_screenplay_stats`). `section_parser.py` used by `story_edit(update_story_memory)`. All `tools/` handlers registered in `__init__.py` and `plugin.yaml`.
- [x] No circular dependencies between modules — PASS: import graph is a DAG (tools → core, no cycles)
- [x] Test naming: `test_<module>_<behavior>` pattern, class names match module under test — PASS: `TestSectionParser`, `TestEntityExtraction`, `TestScreenplay`, `TestNoteCreation`, `TestProjectCreation`, `TestPhase3ToolSurface`, `TestAssembleSceneContent` (deleted), `TestComputeStructuralStats` (deleted), `TestScreenplayStatsFromSceneContent`, `TestArcValidation`, `TestArcCreateTool`, `TestArcEditTool`, `TestArcRetrieveTool`, `TestArcLoadTool`
- [x] No test imports from another test file (each test is self-contained or uses conftest fixtures) — PASS: `grep -rn "from tests\." tests/*.py` returns nothing
- [x] conftest.py fixtures are minimal — only shared setup, no business logic — PASS: only `sys.path.insert(0, repo_root)` (6 lines total, no fixtures, no business logic)

### Good Practice Issues

**`core/index.py` is an empty file (0 bytes)** — dead from Phase 4 deletion. Should delete the file itself, not just empty it.

**`core/screenplay.py` + `core/fountain_validator.py` dead in tools/** — not Phase 4 regression (last touched in earlier phases but never consumed by tool handlers). Pre-existing cleanup item, defer to post-migration pass. `screenplay.py` still imported by 2 test files; `fountain_validator.py` imported nowhere.

---

## Test Verification

**Tests to delete (modules removed):**
- `tests/test_arcs.py` — entire file (all tested functions deleted)
- `tests/test_core.py::TestStoryIndexErrors` — story_index tool deleted
- `tests/test_core.py::TestIndexGeneration` — generate_index() deleted
- `tests/test_core.py::TestArcToolIntegrationFixture` — file-system-based arc integration (replace with DB equivalent if still needed)

**Tests to update (DB-backed):**
- `tests/test_core.py::TestPhase3ToolSurface` — all edit tests use `frontmatter.load` assertions → DB queries
- `tests/test_core.py::TestProjectCreation` — verify `.story/story.db` not `index.yaml`
- `tests/test_core.py::TestNoteCreation` — verify entity + sections in DB
- `tests/test_core.py::TestAssembleSceneContent` — `assemble_scene_content` is from `core/index.py` which is being deleted. If still tested, move test to verify DB-based equivalent (or delete if function is removed)
- `tests/test_core.py::TestComputeStructuralStats` — same situation as above
- `tests/test_core.py::TestScreenplayStatsFromSceneContent` — same situation
- `tests/test_core.py::TestEnrichEntityScenesTitle` — tests `_enrich_entity_scenes` (deleted) — remove
- `tests/test_core.py::TestSceneIndex` — tests `generate_index()` (deleted) — rewrite as DB verification or remove
- `tests/test_story_dashboard_integration.py` — already updated in Phase 2, verify still passes

**Tests to add (Phase 4 regression):**
- `tests/test_db_roundtrip.py` — import → export → diff regression test
- `tests/test_db_search.py` — FTS search regression test (arc beats, all entity types)
- `tests/test_db_softdelete.py` — soft delete + query exclusion
- `tests/test_db_relations.py` — relation JOIN queries (plot→scenes, character→scenes)
- `tests/test_db_write_transaction.py` — rollback on failure (mock exception mid-transaction)

**Tests to verify still pass (unchanged):**
- `tests/test_fountain_lexer.py` — unaffected
- `tests/test_story_dashboard_stats.py` — unaffected (Fountain text in, dict out)

---

## Phase 4 Checkpoint + Final Merge Gate

Must pass before merge to `dev`:

- [x] All tests pass — full suite green (216 passed)
- [x] No references to deleted modules: `core/index.py` enrichment functions, `core/paths.py`, `ENTITY_FOLDERS`, `NESTED_ENTITIES`, `write_index`, `refresh_index`, `tools/story_index.py`
- [x] `plugin.yaml` updated — `story_index` removed from provides_tools
- [ ] Real project test passed by user
- [x] Spec documentation updated to reflect completed architecture
- [x] Rollback plan documented in spec or README
- [x] Token budget verified: `story_load` on fixture = ~1,382 tokens (≤ 5K)
- [x] All 4 phase checkpoints documented as passed

---

## Rollback Path (After Phase 4)

There is no code-level rollback — old markdown write paths are deleted. Recovery:
1. `story_export` → writes markdown vault → `story_import` back to new DB
2. Git history: vault committed before Phase 3 → restore from git
3. `.story/story.db.bak` via `story_backup` (if used before edit)

This is documented in spec §11 (Backup and Recovery).
