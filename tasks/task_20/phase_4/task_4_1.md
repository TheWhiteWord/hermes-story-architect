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
- [x] No `sequence_id` reference in `get_project_summary()` — only in `get_dashboard_data()` (out of scope)
- [x] No `act_id` reference in `get_project_summary()` — only in `get_dashboard_data()` (out of scope)
- [x] No `parent_id` reference in `get_project_summary()` — used internally as DB column to build nesting, never emitted as output field
- [x] No `order_key` reference in `get_project_summary()` — used internally for sorting, never emitted as output field
- [x] No `location_id` reference in `get_project_summary()` — only in `get_dashboard_data()` (out of scope)
- [x] No `location_scene` reference in `get_project_summary()` — used as relation kind to build `scene_loc`, not an output field

### No dead code from old builder:
- [x] No `ent_cols` / `ent_rows` flat-entity variables — `ent_rows` is a query result tuple list, not a flat-entity structure
- [x] No `rel_cols` / `rel_rows` flat-relation variables — `rel_rows` is a query result tuple list
- [x] No `scene_chars` merge into `extra["characters"]` for unfilled — `scene_chars` correctly used for nested cross-references
- [x] No `plot_beats` merge into extra for unfilled — not present
- [x] No old `confirmation` logic (counts_arc, counts_scene, etc.) — not present
- [x] No old `unfilled_map` keyed by entity_id — not present

### Variable naming:
- [x] Builder uses nested terminology (e.g., `acts`, `sequences`, `scenes`, `characters` dicts)
- [x] No flat relation variable names in the new builder

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

### Summary
`get_project_summary()` in `core/db.py` is fully aligned with the new nested payload design:

1. **No old flat field names emitted** — `sequence_id`, `act_id`, `parent_id`, `order_key`, `location_id` are never present in the output. They only exist as internal DB columns used to build nesting (parent_id for tree construction, order_key for sorting) or in the separate `get_dashboard_data()` function (out of scope).

2. **No dead code from old builder** — No `ent_cols`/`rel_cols` structures, no `plot_beats` merge blocks, no old confirmation logic, no old `unfilled_map`. The `ent_rows`/`rel_rows` variables are query result tuples, not legacy flat-entity/relation structures.

3. **Variable naming is consistent** — All builder variables use nested terminology: `scene_chars`, `scene_loc`, `char_rels`, `plot_scenes`, `arcs_by_char`, `acts`, `sequences`, `scenes`, `characters`, `plots`, `locations`, `worlds`.

4. **One cleanup applied** — Removed unused `proj_id` variable from project metadata unpacking (line 140). It was assigned but never referenced.

5. **Historical/legacy comments** — None found in `get_project_summary()`.

### Code changes
- `core/db.py:140` — Removed dead `proj_id` variable from tuple unpacking.

### Verification method
- Grep-based search for all old field names, dead code patterns, and flat-relation variable names within `get_project_summary()` scope.
- Manual trace of all variable names in builder functions.

### Deferred issues
None.
