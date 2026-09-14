# D3 — Simplify `_make_project_with_structure` Helper

**Goal:** Remove `with_structure_index` parameter and `refresh_index()` call from the test helper.

## Why

The `with_structure_index=True` branch calls `refresh_index()` which (after Phase A) generates a unified index, not a sidecar. The helper name and param are misleading — it should just create a minimal project for tool surface tests.

## Current State

`tests/test_core.py` lines 886-895:
```python
def _make_project_with_structure(tmp, with_structure_index=False):
    """Create a project with acts/sequences/scenes folders for structural tests."""
    project_path = _make_minimal_project(tmp)
    (project_path / "scenes").mkdir(parents=True, exist_ok=True)
    (project_path / "sequences").mkdir(parents=True, exist_ok=True)
    (project_path / "acts").mkdir(parents=True, exist_ok=True)
    if with_structure_index:
        from core.index import refresh_index
        refresh_index(project_path)
    return project_path
```

Callers that pass `with_structure_index=True`:
- `test_update_structure_index_scene` (line 1087) — deleted in D2, no longer needs it

## Changes

1. **`tests/test_core.py`**:
   - Remove `with_structure_index` parameter
   - Remove the `if with_structure_index:` block
   - Simplify to just create folders

   ```python
   def _make_project_with_structure(tmp):
       """Create a project with acts/sequences/scenes folders for tool surface tests."""
       project_path = _make_minimal_project(tmp)
       (project_path / "scenes").mkdir(parents=True, exist_ok=True)
       (project_path / "sequences").mkdir(parents=True, exist_ok=True)
       (project_path / "acts").mkdir(parents=True, exist_ok=True)
       return project_path
   ```

## Verification Checklist

- [x] `_make_project_with_structure` accepts no `with_structure_index` parameter
- [x] No `refresh_index()` call in the helper
- [x] All callers updated to use new signature (they already do — none pass `with_structure_index=True`)
- [x] Helper still creates folders for tool surface tests

## Final Notes

Removed `with_structure_index` parameter and `refresh_index()` call from `_make_project_with_structure`. Updated docstring from "structural tests" to "tool surface tests" to reflect actual usage.

## Notes

- Depends on D2 (which removes the only caller that used `with_structure_index=True`)
- This is a cleanup task — no behavior change
