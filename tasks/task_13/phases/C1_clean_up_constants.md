# C1 — Clean Up `core/constants.py`

**Goal:** Remove `PROJECT_STRUCTURAL_FIELDS` constant (already done in A1) — this task verifies the constant is gone and no other code references it.

## Why

`PROJECT_STRUCTURAL_FIELDS` was used only in `generate_index()` to strip structural fields from project dict. After A1, fields stay in place. The constant is dead.

## Changes

1. **`core/constants.py`** — Already removed in A1 step 2. Verify:
   - No `PROJECT_STRUCTURAL_FIELDS` definition
   - No import of `PROJECT_STRUCTURAL_FIELDS` in `core/index.py`
   - No references anywhere in codebase

## Verification Checklist

- [x] `PROJECT_STRUCTURAL_FIELDS` not defined in `core/constants.py` ✓
- [x] No imports of `PROJECT_STRUCTURAL_FIELDS` in any file ✓
- [x] `from .constants import PROJECT_STRUCTURAL_FIELDS` removed from `core/index.py` ✓
- [x] No references to `PROJECT_STRUCTURAL_FIELDS` in tests ✓

## Final Brief

**Status:** Complete (no-op — A1 already removed everything correctly).

- `PROJECT_STRUCTURAL_FIELDS` is not defined in `core/constants.py` (confirmed by reading the file).
- `NAVIGATION_SCENE_FIELDS` is not defined in `core/index.py` (confirmed by reading the file).
- Zero `.py` files import or reference either constant.
- Only remaining references are in task documentation (`plan.md`, `A1_unify_generate_index.md`, `C1_clean_up_constants.md`, `task_12/phase 2/plan.md`) — expected historical records.
- No code changes needed.
