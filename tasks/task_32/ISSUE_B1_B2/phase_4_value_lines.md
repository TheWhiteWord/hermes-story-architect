# Phase 4: Computed `plot.value_lines` and Read-back

**Goal:** Implement the computed `plot.value_lines` field in `core/db.py`, expose it through plot retrieve, describe, and load. Make scene payload builders carry `value_turns`.

**Plan reference:** §3.4, §7 (core/db.py changes)

## Code verification findings

- `plot.value_lines` is computed, read-only, marked `computed: True` in the schema (Phase 2)
- For each value of the plot: its schema, and its turns in story order (scene id, from, to, and each affected character with their conflict levels)
- `story_retrieve.py` already handles computed fields — it iterates `_RELATION_FIELDS` for relation-backed fields. `value_lines` is NOT a relation field; it's computed from `value_schemas` (stored in extra) + `value_turns` (stored in scene extra). So it needs a bespoke block in `_entity_fields`.
- `story_describe.py` already handles computed fields — appends "read-only, computed" to the description. No change needed.
- `story_load.py` `_build_plot` in `get_project_summary` builds the plot payload. It would need to include `value_lines` — but the plan says the base load view stays small. The plan says "exposed through plot retrieve, describe and load." For load, this means the plot entry in the base map should carry `value_lines`.
- The scene payload builder `_build_scene` in `get_project_summary` copies specific fields. It needs to carry `value_turns` from extra.
- `get_dashboard_data` in `core/db.py` builds a denormalized projection. It would need to carry `value_turns` on scenes and `value_schemas`/`value_lines` on plots for the dashboard.
- The plan says "Make the scene payload builders carry `value_turns`" — this affects `_build_scene` in `get_project_summary` and the scene dict in `get_dashboard_data`.

## Tasks

### 4.1 — Implement `value_lines` computation in `core/db.py`
- [ ] New function: `compute_value_lines(project_path, plot_id)` (or similar)
- [ ] Reads the plot's `value_schemas` from extra
- [ ] For each schema, finds all scenes with `value_turns` entries matching that plot+value
- [ ] Orders turns by story order (scene order_key within the plot's scenes)
- [ ] Returns: `[{value, schema: {p, c, cd, nn, note}, turns: [{scene_id, from, to, effects: [{character, levels: [{conflict_level, effect}]}]}]}]`
- [ ] Scenes are found by scanning all scenes' `value_turns` for entries where `plot` matches

### 4.2 — Expose `value_lines` through `story_retrieve`
- [ ] In `tools/story_retrieve.py` `_entity_fields`, add a bespoke block for `plot.value_lines`
- [ ] When `entity_type == "plot"` and `"value_lines"` in wanted: call `compute_value_lines` and inject the result
- [ ] Position in output follows schema order (like relation-backed fields)

### 4.3 — Expose `value_lines` through `story_describe`
- [ ] No code change needed — `story_describe` already copies computed fields from the schema
- [ ] Verify that `value_lines` appears in describe output with the "read-only, computed" suffix

### 4.4 — Expose `value_lines` through `story_load`
- [ ] In `core/db.py` `_build_plot`, add `value_lines` to the plot payload
- [ ] Compute it once per plot (not per scene)
- [ ] The base load view includes it — the plan says "exposed through plot retrieve, describe and load"

### 4.5 — Make scene payload builders carry `value_turns`
- [ ] In `core/db.py` `_build_scene`, add `value_turns` from extra to the scene payload
- [ ] In `core/db.py` `get_dashboard_data`, add `value_turns` to the scene dict
- [ ] In `tools/story_load.py` `_build_scene` (if it has one), add `value_turns`

### 4.6 — Verify `story_export` and `story_import` handle new fields
- [ ] `story_export.py` `_frontmatter_for` for plot: `value_schemas` is in extra, so it's exported automatically via `fm.update(extra)`
- [ ] `story_export.py` `_frontmatter_for` for scene: `value_turns` is in extra, so it's exported automatically
- [ ] `story_import.py` `_extra_for` for plot: `value_schemas` is in schema, so it's accepted automatically
- [ ] `story_import.py` `_extra_for` for scene: `value_turns` is in schema, so it's accepted automatically
- [ ] Verify with a round-trip test

### 4.7 — Run test suite
- [ ] All existing tests still pass
- [ ] `test_field_coverage.py` picks up new fields automatically
- [ ] Add a test that `story_retrieve` with `fields=['value_lines']` returns the computed field
- [ ] Add a test that `story_retrieve` with `fields=['value_schemas']` returns the stored field

## Checklist

- [ ] `compute_value_lines` implemented in `core/db.py`
- [ ] `value_lines` exposed through `story_retrieve`
- [ ] `value_lines` exposed through `story_describe` (no change needed, verified)
- [ ] `value_lines` exposed through `story_load`
- [ ] Scene payload builders carry `value_turns`
- [ ] Export/import handle new fields
- [ ] Full test suite passes
