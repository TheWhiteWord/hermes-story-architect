# Phase 5: Removals and Cleanup

**Goal:** Remove the old value fields and code. Update fixtures, tests, and sample data. Make `story_import` tolerate older markdown with removed keys.

**Plan reference:** §4

## Code verification findings

Fields to remove from `ENTITY_SCHEMAS`:
- `project.story_value`, `story_value_at_open`, `story_value_at_close`
- `act.value_at_open`, `act.value_at_close`
- `sequence.value_at_open`, `sequence.value_at_close`
- `scene.value_at_open`, `value_at_close`, `shift`, `y`, `conflict_levels`

Code to remove:
- `get_value_drift`, `_has_charge` (core/db.py)
- `view='story_value'`, `_SCENE_CURVE`, `_CONTAINER_CHARGES`, `_value_fields` (tools/story_load.py)
- `value_at_open`/`value_at_close` enum validators and `_validate_y` (core/entity.py)
- The `y` field from `arc_beat` (kept until B3, but the plan says "Kept until B3: character_value*, the arc beat fields and VALUE_CHARGES")

Wait — re-reading the plan: "Kept until B3: `character_value*`, the arc beat fields and `VALUE_CHARGES`." So `arc_beat.character_value_at_open`, `character_value_at_close`, `shift`, `y` are KEPT. And `character.character_value`, `character_value_at_open`, `character_value_at_close` are KEPT.

The `y` field on `scene` is removed. The `y` field on `arc_beat` is kept.

Tests to update:
- `test_value_ownership.py` — entire file tests the old system; needs rewrite or removal
- `test_core.py` — 19 references to removed fields
- `test_story_load_views.py` — 8 references
- `test_unfilled_truncation.py` — 8 references
- `test_arcs.py` — 3 references (character_value* — KEPT, so these may not need changes)
- `test_draft_preview.py` — 3 references
- `test_field_coverage.py` — 1 reference (conflict_levels)
- `test_arc_graph_story_series.py` — 1 reference (story_value — may just be a sample value)

## Tasks

### 5.1 — Remove fields from `ENTITY_SCHEMAS`
- [x] `core/constants.py`: remove `project.story_value`, `story_value_at_open`, `story_value_at_close`
- [x] `core/constants.py`: remove `act.value_at_open`, `value_at_close`
- [x] `core/constants.py`: remove `sequence.value_at_open`, `value_at_close`
- [x] `core/constants.py`: remove `scene.value_at_open`, `value_at_close`, `shift`, `y`, `conflict_levels`
- [x] Keep: `arc_beat.character_value_at_open`, `character_value_at_close`, `shift`, `y` (B3)
- [x] Keep: `character.character_value`, `character_value_at_open`, `character_value_at_close` (B3)
- [x] Keep: `VALUE_CHARGES` constant (used by character_value* and arc_beat fields)

### 5.2 — Remove code from `core/db.py`
- [x] Remove `get_value_drift` function
- [x] Remove `_has_charge` function
- [x] Remove the `value_drift` output from `_view_unfilled` in `tools/story_load.py`

### 5.3 — Remove code from `tools/story_load.py`
- [x] Remove `view='story_value'` from the SCHEMA enum
- [x] Remove `_view_story_value` function
- [x] Remove `_CONTAINER_CHARGES`, `_SCENE_CURVE`, `_value_fields` helpers
- [x] Remove the `value_drift` block from `_view_unfilled`
- [x] Update the error message for unknown views (remove `story_value` from the list)

### 5.4 — Remove code from `core/entity.py`
- [x] Remove `value_at_open`/`value_at_close` enum validators from `validate_entity` (scene, sequence, act, project sections)
- [x] Remove `_validate_y` function (only used by scene and arc_beat; scene's `y` is removed, arc_beat's `y` is kept)
- [x] Wait — `_validate_y` is also used by `arc_beat.y` which is KEPT. So `_validate_y` stays, but the call for `scene.y` is removed.
- [x] Remove the `_validate_y` call from the scene section of `validate_entity`

### 5.5 — Update `story_import.py` to tolerate removed keys
- [x] ~~In `_extra_for`, when a key is not in the schema: instead of raising an error, check if it's a known removed field~~
- [x] ~~If it's a removed field: log a warning (or silently skip) and continue~~
- [x] ~~If it's an unknown field: still raise an error (as today)~~
- [x] ~~This allows older markdown with `value_at_open`, `story_value`, etc. to import without error~~

> **REMOVED after review (owner's call): the app was never deployed, so there is no older markdown to tolerate — the tolerance was backward-compatibility code for a migration that will never run. The importer's existing unknown-key refusal stands; a note carrying a removed key is refused, as before. The fixture is the only project, and it already conforms (see 5.7).** `story_import.py` is back to its pre-phase state.

### 5.6 — Update tests
- [x] `test_value_ownership.py`: rewrite to test the new value system, or remove if fully superseded by `test_value_turns.py`
- [x] `test_core.py`: remove tests for `value_at_open`/`value_at_close` on scene/sequence/act/project
- [x] `test_story_load_views.py`: remove `view='story_value'` tests
- [x] `test_unfilled_truncation.py`: remove `value_drift` tests
- [x] `test_draft_preview.py`: remove `value_at_open` enum validation test
- [x] `test_field_coverage.py`: remove `conflict_levels` from the sample value generator
- [x] `test_arc_graph_story_series.py`: update `story_value` reference if needed

### 5.7 — Update the fixture
- [x] The one-time migration script from Phase 0 should have already stripped removed fields
- [x] Verify the fixture is clean
- [x] If the fixture has markdown files (not just DB), update them too

> **Verified by running:** the fixture DB was deleted and rebuilt from markdown by conftest; the full suite passes (1094), which means every fixture note imports clean under the strict (no-tolerance) importer. The fixture markdown already conforms to the new code — no migration needed beyond Phase 0's.

### 5.8 — Update sample data in `data-load.js` (if applicable)
- [x] Check if the dashboard's `data-load.js` has sample data with removed fields
- [x] Update if needed

> **Scope note (5.8):** only `data-load.js` was touched — it is sample data in "the REAL backend schema", so the retired keys were removed from it. The live dashboard views (`story.js`, `entity-panels.js`) were reverted to their original state: their reads of the removed fields degrade gracefully (guarded `if`s), and the value graph that should display values and their shifts is a **separate future build** (a new graph, not the existing arc graph, which stays for characters and is itself awaiting its B3 redesign). No pre-wiring of `value_turns`/`value_lines` into existing views.

### 5.9 — Run test suite
- [x] All tests pass
- [x] No references to removed fields in test files (grep to verify)

## Checklist

- [x] All removed fields deleted from `ENTITY_SCHEMAS`
- [x] `get_value_drift`, `_has_charge` removed from `core/db.py`
- [x] `view='story_value'`, `_SCENE_CURVE`, `_value_fields` removed from `tools/story_load.py`
- [x] `value_at_open`/`value_at_close` enum validators removed from `validate_entity`
- [x] `_validate_y` call removed from scene section (function kept for arc_beat)
- [x] `story_import.py` tolerates removed keys with warning
- [x] All tests updated and passing
- [x] Fixture verified clean
- [x] No dangling references to removed fields

---

## Final Brief

Phase 5 complete, then corrected after owner review. **1094 tests pass** with the fixture DB rebuilt from markdown under the strict importer.

**What was removed (the actual work)**
- `core/constants.py`: `project.story_value*`, `act/sequence/scene.value_at_open|close`, `scene.shift/y/conflict_levels`. Kept (B3): `character.character_value*`, `arc_beat.character_value_*|shift|y`, `VALUE_CHARGES`.
- `core/db.py`: `get_value_drift`, `_has_charge`, the `value_drift` output in `_view_unfilled`.
- `tools/story_load.py`: `view='story_value'` (enum + dispatch + error list), `_view_story_value`, `_CONTAINER_CHARGES`, `_SCENE_CURVE`, `_value_fields`, and the orphaned comment block describing the removed view.
- `core/entity.py`: the four `value_at_open/close` enum validators and the scene `_validate_y` call (`_validate_y` itself kept — `arc_beat.y` still uses it; docstring updated to say so).
- `tests/test_value_ownership.py`: deleted — every test asserted the removed view; fully superseded by `test_value_turns.py`.
- Six other test files: removed/rewrote the tests of removed behavior; `_CURVE_ENTITIES` is now `("arc_beat",)` only.

**What was reverted after review (owner's corrections)**
- **`story_import.py` back to its pre-phase state.** The tolerance for pre-redesign notes (`RETIRED_FIELDS`, the dropped-keys report) was backward-compatibility code for a migration that will never run — the app was never deployed. The importer's existing unknown-key refusal stands: a note carrying a removed key is refused, as it always was.
- **`story.js` and `entity-panels.js` reverted.** I had pre-wired `value_turns`/`value_lines` into the existing scene panel and project view. That was wrong: the display of values and their shifts belongs to a **new value graph, a separate future build** — not the existing arc graph (which stays for characters and awaits its own B3 redesign). The original reads of the removed fields are left in place; they degrade gracefully behind their guards.
- **`data-load.js` keeps its change** — it is sample data in "the REAL backend schema", so dropping the retired keys keeps the sample truthful. That is data, not a compat layer.

**Fixture (5.7)** — verified by running, not assumed: the fixture DB was deleted and rebuilt from markdown by conftest; the full suite passes, which is the proof that every fixture note imports clean under the strict importer. The fixture markdown already conforms — Phase 0's migration was sufficient.

**Working tree:** 14 files changed (+~130/−~560). Python side carries no reference to any retired field.

**Verified by running:** full suite 1094 passed on a from-scratch fixture rebuild; grep confirms zero retired-field references in `core/`, `tools/`, `src/` Python/JS (the only four left are the original, gracefully-degrading dashboard reads in `story.js`/`entity-panels.js`, left for the future value graph).
