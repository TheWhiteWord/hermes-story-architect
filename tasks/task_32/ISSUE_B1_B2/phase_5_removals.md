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
- [ ] `core/constants.py`: remove `project.story_value`, `story_value_at_open`, `story_value_at_close`
- [ ] `core/constants.py`: remove `act.value_at_open`, `value_at_close`
- [ ] `core/constants.py`: remove `sequence.value_at_open`, `value_at_close`
- [ ] `core/constants.py`: remove `scene.value_at_open`, `value_at_close`, `shift`, `y`, `conflict_levels`
- [ ] Keep: `arc_beat.character_value_at_open`, `character_value_at_close`, `shift`, `y` (B3)
- [ ] Keep: `character.character_value`, `character_value_at_open`, `character_value_at_close` (B3)
- [ ] Keep: `VALUE_CHARGES` constant (used by character_value* and arc_beat fields)

### 5.2 — Remove code from `core/db.py`
- [ ] Remove `get_value_drift` function
- [ ] Remove `_has_charge` function
- [ ] Remove the `value_drift` output from `_view_unfilled` in `tools/story_load.py`

### 5.3 — Remove code from `tools/story_load.py`
- [ ] Remove `view='story_value'` from the SCHEMA enum
- [ ] Remove `_view_story_value` function
- [ ] Remove `_CONTAINER_CHARGES`, `_SCENE_CURVE`, `_value_fields` helpers
- [ ] Remove the `value_drift` block from `_view_unfilled`
- [ ] Update the error message for unknown views (remove `story_value` from the list)

### 5.4 — Remove code from `core/entity.py`
- [ ] Remove `value_at_open`/`value_at_close` enum validators from `validate_entity` (scene, sequence, act, project sections)
- [ ] Remove `_validate_y` function (only used by scene and arc_beat; scene's `y` is removed, arc_beat's `y` is kept)
- [ ] Wait — `_validate_y` is also used by `arc_beat.y` which is KEPT. So `_validate_y` stays, but the call for `scene.y` is removed.
- [ ] Remove the `_validate_y` call from the scene section of `validate_entity`

### 5.5 — Update `story_import.py` to tolerate removed keys
- [ ] In `_extra_for`, when a key is not in the schema: instead of raising an error, check if it's a known removed field
- [ ] If it's a removed field: log a warning (or silently skip) and continue
- [ ] If it's an unknown field: still raise an error (as today)
- [ ] This allows older markdown with `value_at_open`, `story_value`, etc. to import without error

### 5.6 — Update tests
- [ ] `test_value_ownership.py`: rewrite to test the new value system, or remove if fully superseded by `test_value_turns.py`
- [ ] `test_core.py`: remove tests for `value_at_open`/`value_at_close` on scene/sequence/act/project
- [ ] `test_story_load_views.py`: remove `view='story_value'` tests
- [ ] `test_unfilled_truncation.py`: remove `value_drift` tests
- [ ] `test_draft_preview.py`: remove `value_at_open` enum validation test
- [ ] `test_field_coverage.py`: remove `conflict_levels` from the sample value generator
- [ ] `test_arc_graph_story_series.py`: update `story_value` reference if needed

### 5.7 — Update the fixture
- [ ] The one-time migration script from Phase 0 should have already stripped removed fields
- [ ] Verify the fixture is clean
- [ ] If the fixture has markdown files (not just DB), update them too

### 5.8 — Update sample data in `data-load.js` (if applicable)
- [ ] Check if the dashboard's `data-load.js` has sample data with removed fields
- [ ] Update if needed

### 5.9 — Run test suite
- [ ] All tests pass
- [ ] No references to removed fields in test files (grep to verify)

## Checklist

- [ ] All removed fields deleted from `ENTITY_SCHEMAS`
- [ ] `get_value_drift`, `_has_charge` removed from `core/db.py`
- [ ] `view='story_value'`, `_SCENE_CURVE`, `_value_fields` removed from `tools/story_load.py`
- [ ] `value_at_open`/`value_at_close` enum validators removed from `validate_entity`
- [ ] `_validate_y` call removed from scene section (function kept for arc_beat)
- [ ] `story_import.py` tolerates removed keys with warning
- [ ] All tests updated and passing
- [ ] Fixture verified clean
- [ ] No dangling references to removed fields
