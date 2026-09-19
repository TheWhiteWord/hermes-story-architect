# Task 4.4: Verify `get_dashboard_data()` Unaffected

## Goal
Verify that `get_dashboard_data()` in `core/db.py` is completely unaffected by the Phase 1-3 changes. The dashboard uses column-oriented logic and must remain intact.

**Scope:** `core/db.py` — read-only verification of `get_dashboard_data()`.

---

## Current State

`get_dashboard_data()` at `core/db.py:204-742`:
- Uses its own entity query (separate from `get_project_summary()`)
- Builds column-oriented denormalized output for dashboard
- Uses `entities`, `relations` tables directly
- NOT touched by Phase 1-3 changes

---

## Verification Checklist

### `get_dashboard_data()` still works:
- [ ] Function still exists at `core/db.py:204`
- [ ] Still returns `story_data`, `sections`, `screenplay_text`, `structural_stats`, `title_page`
- [ ] Still uses `entities` and `relations` tables
- [ ] No imports from `get_project_summary()` (independent)

### Dashboard tests still pass:
- [ ] `tests/test_story_dashboard_stats.py` passes
- [ ] `tests/test_story_dashboard_integration.py` passes

---

## Code anchors

| What | Where |
|---|---|
| `get_dashboard_data()` | `core/db.py:204-742` |
| Dashboard tests | `tests/test_story_dashboard_stats.py`, `tests/test_story_dashboard_integration.py` |

---

## Important

This is a **read-only verification** task. Do NOT modify `get_dashboard_data()` or its tests. The dashboard is a separate consumer that still uses the column-oriented format.

---

## Final Brief

_To be filled after task completion._
