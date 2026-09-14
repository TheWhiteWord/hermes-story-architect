# A1 — Unify `generate_index()`

**Goal:** `generate_index()` produces the complete dict with all fields — no stashing, no stripping.

## Why

The navigation/structural split has no production expression. Same writer, same volatility, same consumer. Two artifacts that are always written together, read together, and have the same lifecycle are one artifact.

## Current State

`core/index.py` lines 33-40:
- Line 33: `index["_full_scenes"] = file_scenes`
- Line 34: `index["scenes"] = [_strip_scene_for_navigation(s) for s in file_scenes]`
- Line 39: `index["_full_project"] = dict(index["project"])`
- Line 40: `index["project"] = {k: v ... if k not in PROJECT_STRUCTURAL_FIELDS}`

`core/index.py` lines 177-186: `NAVIGATION_SCENE_FIELDS` constant + `_strip_scene_for_navigation()` function.

`core/constants.py` lines 20-29: `PROJECT_STRUCTURAL_FIELDS` constant.

## Changes

1. **`core/index.py`** — In `generate_index()`:
   - Remove lines 33-34, replace with: `index["scenes"] = file_scenes`
   - Remove lines 38-40 (the `from .constants import ...` and project stripping)
   - Remove `NAVIGATION_SCENE_FIELDS` constant (lines 177-181)
   - Remove `_strip_scene_for_navigation()` function (lines 184-186)

2. **`core/constants.py`** — Remove `PROJECT_STRUCTURAL_FIELDS` (lines 20-29).

## Verification Checklist

- [x] `generate_index()` returns scenes with all dramatic metadata fields (`value`, `value_open`, `value_close`, `conflict_levels`, `dramatic_role`, `is_inciting_incident`, `is_sequence_climax`, `is_act_climax`, `is_story_climax`)
- [x] `generate_index()` returns project with all structural fields (`spine`, `controlling_idea`, `value`, `value_at_open`, `value_at_close`, `inciting_incident_scene_id`, `story_climax_scene_id`, `structure_type`)
- [x] No `_full_scenes` or `_full_project` keys in the returned index
- [x] `NAVIGATION_SCENE_FIELDS` no longer importable from `core/index.py`
- [x] `_strip_scene_for_navigation` no longer importable from `core/index.py`
- [x] `PROJECT_STRUCTURAL_FIELDS` no longer importable from `core/constants.py`

## Notes

- This task MUST complete before A2 (deleting sidecar functions — they read `_full_scenes`/`_full_project`)
- Test `test_index_scenes_stripped_for_navigation` will break after this — that's expected, fixed in D1

## Completion Notes

**Completed:** 2026-09-14

**Changes:**
- Removed `_full_scenes` / `_full_project` stashing and navigation/structural split from `generate_index()`
- Removed `NAVIGATION_SCENE_FIELDS` constant and `_strip_scene_for_navigation()` helper from `core/index.py`
- Removed `PROJECT_STRUCTURAL_FIELDS` constant from `core/constants.py`
- `generate_index()` now returns complete scenes and project dicts with all fields
- Stale comments about split removed
