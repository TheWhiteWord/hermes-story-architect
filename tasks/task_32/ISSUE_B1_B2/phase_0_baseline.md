# Phase 0: Baseline

**Goal:** Record the current state before any changes. Know exactly what passes, what fails, and which tests touch the fields being removed.

## Tasks

### 0.1 — Install pytest and run the full suite
- [x] Install pytest if not already available
- [x] Run `python -m pytest tests/ -v` on `feature/issue-redesign`
- [x] Record: total tests, passed, failed, errors, skipped
- [x] Record: wall-clock time

**Result (before migration):**
- 1073 tests, 1069 passed, 4 failed, 0 errors, 0 skipped
- Wall-clock: 42.05s
- Pre-existing failures (unrelated to value system):
  1. `test_phase2_db_reads.py::TestEmbeddedCrossReferences::test_character_has_rel`
  2. `test_relationship_subfields.py::test_declared_sub_fields_match_the_load_payload`
  3. `test_story_load_views.py::TestPlotBeatsLiveInTheirOwnView::test_scene_plot_entries_carry_no_description`
  4. `test_story_load_views.py::TestDramaticElementsView::test_the_role_is_derived_from_the_relation_kind`

**Result (after migration):**
- 1073 tests, 1057 passed, 16 failed, 0 errors, 0 skipped
- Wall-clock: 40.37s
- 12 new failures — all in `test_value_ownership.py` and `test_story_load_views.py`, testing the old value system. Expected; will be removed/rewritten in Phase 5.

### 0.2 — List every test that mentions removed fields
- [x] For each file, note which specific fields/tests will need updating or removal in Phase 5

| File | References | Action in Phase 5 |
|------|-----------|-------------------|
| `test_value_ownership.py` | 36 refs (entire file) | **Remove or rewrite** — tests `view='story_value'`, `story_value`, `value_at_open/close`, `shift`, `y` |
| `test_core.py` | 19 refs | Update schema assertions; remove `value_at_open/close` tests for scene/act/sequence/project |
| `test_story_load_views.py` | 8 refs | Remove `story_value` view tests; update `conflict_levels` assertions |
| `test_unfilled_truncation.py` | 8 refs | Remove `y` and `shift` from unfilled field assertions |
| `test_arcs.py` | 3 refs | Keep — arc beat `shift`/`y` are kept until B3 |
| `test_draft_preview.py` | 3 refs | Remove `shift`/`y` from draft preview assertions (scene fields) |
| `test_field_coverage.py` | 1 ref | Remove `value_at_open` from field coverage |
| `test_arc_graph_story_series.py` | 1 ref | Keep — arc beat field |

### 0.3 — Inspect the fixture database
- [x] Open `tests/fixtures/save-the-children/.story/story.db`
- [x] List all entities that carry removed fields in their `extra` JSON
- [x] Count how many scenes have `value_at_open`, `value_at_close`, `shift`, `y`, `conflict_levels`
- [x] Count how many acts/sequences have `value_at_open`/`value_at_close`
- [x] Note the project's `story_value`, `story_value_at_open`, `story_value_at_close`
- [x] This inventory feeds the one-time fixture migration script (Phase 5)

**Key discovery:** The fixture DB is a **build artifact**, not committed source. `conftest.py` (lines 32–61) builds it from markdown on every session. `.gitignore` excludes `*.db`. The markdown files are the source of truth.

**Entities with removed fields (in DB, confirmed from markdown):**
- `project/save-the-children`: `story_value: Trust`, `story_value_at_open: positive`, `story_value_at_close: negative`
- `act/act-1`: `value_at_open: positive`, `value_at_close: negative`
- `sequence/seq-discovery`: `value_at_open: positive`, `value_at_close: negative`
- `scene/central-room-day`: `value_at_open: positive`, `value_at_close: negative`, `shift: blind trust → first doubt`, `y: -0.3`, `conflict_levels: ['inner', 'personal']`
- `scene/central-room-night`: `value_at_open: negative`, `value_at_close: positive`, `shift: doubt → chosen trust`, `y: 0.6`, `conflict_levels: ['personal']`
- `scene/the-core-day`: `value_at_open: positive`, `value_at_close: positive`, `shift: fragile trust → trust earned`, `y: 0.4`, `conflict_levels: ['extra-personal']`

### 0.4 — Verify the test project (if one exists)
- [x] Check if there's a live test project with value data
- [x] If yes, inventory it the same way as the fixture

**Result:** No live test project found. The only fixture is `save-the-children`.

### 0.5 — Create the one-time fixture migration script
**This is a standalone script, NOT integrated into the application.**
- [x] Write `tests/migrate_fixture_b1_b2.py`
- [x] The script reads fixture **markdown** files (not the DB — see 0.3 discovery)
- [x] Strips removed fields from frontmatter
- [x] Writes updated files back
- [x] Idempotent (verified: second dry-run shows 0 changes)
- [x] Makes a backup of the fixture directory before modifying
- [x] Run it on the fixture — 6 files changed
- [x] Verify the fixture no longer contains removed fields (verified: all clean)
- [x] ~~Commit the migrated fixture~~ — will commit when user approces the phase

**Files changed by migration:**
1. `project.md` — removed `story_value`, `story_value_at_open`, `story_value_at_close`
2. `acts/Act One.md` — removed `value_at_open`, `value_at_close`
3. `sequences/The Discovery.md` — removed `value_at_open`, `value_at_close`
4. `scenes/Central Room - Day.md` — removed `value_at_open`, `value_at_close`, `shift`, `y`, `conflict_levels`
5. `scenes/Central Room - Night.md` — same
6. `scenes/The Core - Day.md` — same

**Note:** Arc beat files (`arcs/*`) also carry `shift` and `y`, but these are **kept until B3** (design §4). The script excludes them by path prefix.

## Checklist

- [x] Baseline test results recorded
- [x] All test files referencing removed fields identified
- [x] Fixture inventory complete
- [x] Fixture migration script written and run
- [x] Fixture verified clean of removed fields
- [x] No application code changed in this phase

---

## Final Brief

Phase 0 baseline is complete. The test suite has 1073 tests: 4 pre-existing failures (unrelated to value system) and 12 expected failures from the fixture migration (old value system tests that will be removed/rewritten in Phase 5). The migration script `tests/migrate_fixture_b1_b2.py` is idempotent, backed up, and verified. The fixture markdown is now clean of all B1/B2-removed fields. No application code was changed.

**Deviation from task spec:** Task 0.5 assumed the DB was the migration target. Inspection of `conftest.py` proved the DB is a build artifact — markdown is the source of truth. The script migrates markdown instead, which is correct: the DB will be rebuilt from the migrated markdown on the next test session.

**Ready for Phase 1:** Shared shape validation (design §3.6).
