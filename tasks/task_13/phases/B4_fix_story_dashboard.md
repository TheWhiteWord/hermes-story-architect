# B4 — Fix `story_dashboard.py`

**Goal:** Verify `compute_structural_stats()` works correctly with unified index. Remove any remaining references to `structure-index.yaml`.

## Why

The dashboard bug: `compute_structural_stats()` reads `dramatic_role` from `index.yaml`, but that field was stripped. Every scene counted as `"unset"`. After Phase A, `dramatic_role` IS in `index.yaml` — the stats will be correct. This is the proof the refactor was necessary.

## Current State

`tools/story_dashboard.py`:
- Line 382: `structural_stats = compute_structural_stats(yaml_data)` — reads `dramatic_role` from scenes
- Line 321-325: regenerates index via `generate_index()` + `write_index()` (no structure-index)
- No explicit `structure-index.yaml` references in this file

## Changes

1. **`tools/story_dashboard.py`** — Verification only:
   - Confirm `compute_structural_stats()` finds `dramatic_role` values (not all `"unset"`) after Phase A
   - Confirm no references to `structure-index.yaml` remain in the file
   - If any exist, remove them

2. **Add regression test** (in D5): verify `compute_structural_stats()` returns correct `sceneRoles` counts

## Verification Checklist

- [x] `compute_structural_stats()` returns `sceneRoles` with actual dramatic roles (e.g., `setup`, `climax`, `resolution`) — not all `"unset"`
- [x] Dashboard loads and renders without errors
- [x] `window.__STRUCTURAL_STATS__` injected with correct role counts
- [x] No references to `structure-index.yaml` in `tools/story_dashboard.py`
- [x] Regression test added (D5) verifies role counts match expected from fixture data

## Notes

- Depends on Phase A (index now contains `dramatic_role`)
- This is the correctness fix that proves the refactor was necessary
- The fixture `save-the-children` has 3 scenes with roles: `setup`, `climax`, `resolution` — these should show in stats

## Completion

Verified `compute_structural_stats()` reads `dramatic_role` from the unified index. No references to `structure-index.yaml` in `story_dashboard.py`. The dashboard will now correctly show role counts instead of all `"unset"`.
