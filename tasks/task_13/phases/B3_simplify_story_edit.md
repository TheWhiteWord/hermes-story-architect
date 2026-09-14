# B3 — Simplify `story_edit.py`

**Goal:** Remove `update_structure_index_scene` import and call. Index refresh is handled by `refresh_index()`.

## Why

`story_edit` currently calls `update_structure_index_scene()` for O(1) structure-index update after editing a scene. That function is deleted in A2. The edit already calls `refresh_index()` which regenerates the unified index. No separate structure-index update needed.

## Current State

`tools/story_edit.py`:
- Line 123: imports `update_structure_index_scene`
- Lines 121-124: calls it after editing a scene

## Changes

1. **`tools/story_edit.py`**:
   - Remove line 123: `from core.index import update_structure_index_scene`
   - Remove lines 121-124: the entire `if entity_type == "scene":` block that calls `update_structure_index_scene()`

2. **Verify** `_refresh_index()` (which calls `refresh_index()`) is still called after edit — it is, on lines 77-79.

## Verification Checklist

- [x] `story_edit` with `edit_note` on a scene still succeeds
- [x] `story_edit` with `edit_note` on a scene triggers `refresh_index()` (full rebuild)
- [x] No `update_structure_index_scene` import in `story_edit.py`
- [x] No `update_structure_index_scene` calls in `story_edit.py`

## Notes

- Depends on A2 (deletes `update_structure_index_scene`)
- O(N) rebuild for story-scale projects (~50 scenes) is sub-millisecond — YAGNI
- If rebuild ever becomes measurable, the O(1) path can be re-added to the unified index later

## Completion

Removed `update_structure_index_scene` import and the O(1) scene-index update block. The edit flow already calls `_refresh_index()` which does a full rebuild via `refresh_index()`.
