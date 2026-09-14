# A2 — Delete Sidecar Functions

**Goal:** Remove `generate_structure_index()`, `write_structure_index()`, `update_structure_index_scene()` — they no longer have a purpose.

## Why

With the unified index (A1), the sidecar functions are dead code. They read `_full_scenes`/`_full_project` which no longer exist.

## Changes

1. **`core/index.py`** — Delete:
   - `generate_structure_index()` (lines 295-352) — reads `_full_scenes`/`_full_project` to build sidecar
   - `write_structure_index()` (lines 355-358) — writes `structure-index.yaml`
   - `update_structure_index_scene()` (lines 361-397) — O(1) scene update to sidecar

2. **Verify no other callers** of these functions remain after A1 is complete (grep for `generate_structure_index|write_structure_index|update_structure_index_scene`).

## Verification Checklist

- [x] `generate_structure_index` not importable from `core/index.py`
- [x] `write_structure_index` not importable from `core/index.py`
- [x] `update_structure_index_scene` not importable from `core/index.py`
- [x] No references to these functions in any tool (`tools/*.py`) — they will be cleaned up in Phase B, but verify nothing imports them that still compiles

## Notes

- Depends on A1 (which removes `_full_scenes`/`_full_project` stashing)
- Test surface tests (5 `TestStructureIndex`, `test_update_structure_index_scene`) will fail until Phase D deletes/rewrites them

## Completion Notes

**Completed:** 2026-09-14

**Changes:**
- Deleted `generate_structure_index()`, `write_structure_index()`, `update_structure_index_scene()` from `core/index.py`
- `refresh_index()` still references these (will be fixed in A3)
- Tools still import them (will be cleaned in Phase B)
