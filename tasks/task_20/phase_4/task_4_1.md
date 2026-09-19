# Task 4.1: Naming Convention Sweep — `core/db.py`

## Goal
Ensure the `get_project_summary()` builder uses nested/structural terminology and has zero references to old flat-relation field names. Verify all dead code from the old builder is removed.

**Scope:** `core/db.py` — grep-based verification + cleanup.

---

## Current State (after Phase 1 implementation)

The `get_project_summary()` function has been rewritten (Task 1.1) to produce nested output. Need to verify:

1. No references to old flat field names in the summary builder path
2. No dead code from the old builder remaining
3. Variable names use nested terminology

---

## Verification Checklist

### No old field names in load path:
- [ ] No `sequence_id` reference in `get_project_summary()`
- [ ] No `act_id` reference in `get_project_summary()`
- [ ] No `parent_id` reference in `get_project_summary()`
- [ ] No `order_key` reference in `get_project_summary()`
- [ ] No `location_id` reference in `get_project_summary()`
- [ ] No `location_scene` reference in `get_project_summary()`

### No dead code from old builder:
- [ ] No `ent_cols` / `ent_rows` flat-entity variables
- [ ] No `rel_cols` / `rel_rows` flat-relation variables
- [ ] No `scene_chars` merge into `extra["characters"]` for unfilled
- [ ] No `plot_beats` merge into extra for unfilled
- [ ] No old `confirmation` logic (counts_arc, counts_scene, etc.)
- [ ] No old `unfilled_map` keyed by entity_id

### Variable naming:
- [ ] Builder uses nested terminology (e.g., `acts`, `sequences`, `scenes`, `characters` dicts)
- [ ] No flat relation variable names in the new builder

---

## Code anchors

| What | Where |
|---|---|
| `get_project_summary()` | `core/db.py:84` (rewritten in Phase 1) |
| `get_dashboard_data()` | `core/db.py:204` (NOT touched — still uses old columns/relations) |

---

## Important

`get_dashboard_data()` is **separate** and should NOT be touched. It still uses column-oriented logic for the dashboard. Only verify that `get_project_summary()` is clean.

---

## Remediation (if issues found)

If any old references found in `get_project_summary()`:
- Replace with nested equivalents
- Remove dead code
- Rename variables to match nested terminology

---

## Final Brief

_To be filled after task completion._
