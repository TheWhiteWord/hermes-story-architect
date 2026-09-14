# D2 — Remove `test_index_scenes_stripped_for_navigation` and `test_update_structure_index_scene`

**Goal:** Delete tests that assert the old behavior (scenes stripped, O(1) sidecar update).

## Why

- `test_index_scenes_stripped_for_navigation` (line 834): asserts scenes DON'T have dramatic metadata — after A1 they DO.
- `test_update_structure_index_scene` (line 1087): tests `update_structure_index_scene()` — function deleted in A2.

## Changes

1. **`tests/test_core.py`**:
   - Delete `test_index_scenes_stripped_for_navigation` method (lines 834-850)
   - Delete `test_update_structure_index_scene` method (lines 1087-1151)

## Verification Checklist

- [x] `test_index_scenes_stripped_for_navigation` removed
- [x] `test_update_structure_index_scene` removed
- [x] No references to `update_structure_index_scene` in tests
- [x] All remaining tests pass (67/67)

## Final Notes

`test_index_scenes_stripped_for_navigation` (17 lines) and `test_update_structure_index_scene` (67 lines) deleted. Zero references to `update_structure_index_scene` or `structure-index.yaml` remain in test file.

## Notes

- Depends on A1 (index now includes all fields) and A2 (function deleted)
- These tests were asserting the SPLIT behavior — now we assert UNIFIED behavior (covered in D1's new test)
