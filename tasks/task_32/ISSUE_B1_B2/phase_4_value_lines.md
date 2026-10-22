# Phase 4: Computed `plot.value_lines` and Read-back

**Goal:** Implement the computed `plot.value_lines` field in `core/db.py`, expose it through plot retrieve, describe, and load. Make scene payload builders carry `value_turns`.

**Plan reference:** §3.4, §7 (core/db.py changes)

## Code verification findings

- `plot.value_lines` is computed, read-only, marked `computed: True` in the schema (Phase 2)
- For each value of the plot: its schema, and its turns in story order (scene id, from, to, and each affected character with their conflict levels)
- `story_retrieve.py` already handles computed fields — it iterates `_RELATION_FIELDS` for relation-backed fields. `value_lines` is NOT a relation field; it's computed from `value_schemas` (stored in extra) + `value_turns` (stored in scene extra). So it needs a bespoke block in `_entity_fields`.
- `story_describe.py` already handles computed fields — appends "read-only, computed" to the description. **Verified, and found a defect: the Phase 2 declaration already carried that suffix, so `_entity_schemas` appended it twice ("(read-only, computed — do not set) (read-only, computed — do not set)"). Fixed at the source — the schema description no longer repeats the suffix the describe builder adds.**
- `story_load.py` `_build_plot` in `get_project_summary` builds the plot payload. It would need to include `value_lines` — but the plan says the base load view stays small. The plan says "exposed through plot retrieve, describe and load." For load, this means the plot entry in the base map should carry `value_lines`.
- The scene payload builder `_build_scene` in `get_project_summary` copies specific fields. It needs to carry `value_turns` from extra.
- `get_dashboard_data` in `core/db.py` builds a denormalized projection. It would need to carry `value_turns` on scenes and `value_schemas`/`value_lines` on plots for the dashboard.
- The plan says "Make the scene payload builders carry `value_turns`" — this affects `_build_scene` in `get_project_summary` and the scene dict in `get_dashboard_data`.
- **`tools/story_load.py` has no `_build_scene`** — the base view is built entirely by `get_project_summary` in `core/db.py`. Task 4.5's third bullet refers to a function that does not exist.
- **`test_field_coverage.py:_sample_value`** — the Phase 2 note warned the plain-string list sample would be refused by the shape validator for a `sub_fields` field. That is exactly what happened on the plot create path ("'str' object has no attribute 'get'"): `value_schemas` sampled as `["item-1", "item-2"]`. Fixed with a real one-value sample entry.

## Tasks

### 4.1 — Implement `value_lines` computation in `core/db.py`
- [x] New function: `compute_value_lines(project_path, plot_id)`
- [x] Reads the plot's `value_schemas` from extra
- [x] For each schema, finds all scenes with `value_turns` entries matching that plot+value
- [x] Orders turns by story order (scene order_key within the plot's scenes)
- [x] Returns: `[{value, schema: {p, c, cd, nn, note}, turns: [{scene_id, from, to, effects: [{character, levels: [{conflict_level, effect}]}]}]}]`
- [x] Scenes are found by scanning all scenes' `value_turns` for entries where `plot` matches

> **Implementation note (4.1):** one pass over every scene per call, and turns are keyed by VALUE (not plot) — a value is defined once per plot, so every turn naming this plot's value belongs to that value's line regardless of which plot the turn declares. Story order is the composite `(parent sequence order_key, scene order_key, scene id)` that `_build_scene` already sorts by, so an inserted scene reads where it happens rather than where it was written. A turn whose value the plot no longer defines is dropped: the line reads the plot's current vocabulary, and an orphan turn is not a line. A value with a schema but no turns yields no line at all — the read-back lists what exists.

### 4.2 — Expose `value_lines` through `story_retrieve`
- [x] In `tools/story_retrieve.py` `_entity_fields`, add a bespoke block for `plot.value_lines`
- [x] When `entity_type == "plot"` and `"value_lines"` in wanted: call `compute_value_lines` and inject the result
- [x] Position in output follows schema order (like relation-backed fields)

> **Implementation note (4.2):** `compute_value_lines` needs the project path, which the connection carries via `PRAGMA database_list` — the same trick `story_load.project_path_of` uses. Added the same helper here rather than routing the path through the call chain.

### 4.3 — Expose `value_lines` through `story_describe`
- [x] No code change needed — `story_describe` already copies computed fields from the schema
- [x] Verify that `value_lines` appears in describe output with the "read-only, computed" suffix

> **Verified by running, and it found a defect:** the suffix was doubled. `core/constants.py` carried `value_lines`' description ending in "(read-only, computed — do not set)" while `_entity_schemas` appends the same suffix to every `computed` field's description. Every other computed field's description ends clean. Fixed by removing the hardcoded suffix from the declaration; the builder's rule is now the only source.

### 4.4 — Expose `value_lines` through `story_load`
- [x] In `core/db.py` `_build_plot`, add `value_lines` to the plot payload
- [x] Compute it once per plot (not per scene)
- [x] The base load view includes it — the plan says "exposed through plot retrieve, describe and load"

> **Implementation note (4.4):** `plot_value_lines = {pid: compute_value_lines(...) for pid in plots}` runs once before the plot builders, so the line is computed per plot rather than per payload call. The `_omit` defaults list gained `"value_lines": []`, so a plot with no turns drops the key — the same rule `characters` already follows. `compute_value_lines` opens its own connection, so this is a second connection over the same file inside the summary's transaction-less read; `ponytail:` comment marks the ceiling (hoist the scan into one shared pass) rather than building the indirection now.

### 4.5 — Make scene payload builders carry `value_turns`
- [x] In `core/db.py` `_build_scene`, add `value_turns` from extra to the scene payload
- [x] In `core/db.py` `get_dashboard_data`, add `value_turns` to the scene dict
- [x] In `tools/story_load.py` `_build_scene` (if it has one), add `value_turns`

> **Deviation from the task spec:** `tools/story_load.py` has no `_build_scene` — the base view is built entirely inside `get_project_summary` in `core/db.py`. Only the two `core/db.py` builders exist. Also added `value_schemas` and `value_lines` to the dashboard plot dict: `_entity_dict` merges extra, so `value_schemas` would have flowed automatically — but `value_lines` is computed and would have been silently absent from the dashboard, which the task's own findings called for. Both are explicit now.

### 4.6 — Verify `story_export` and `story_import` handle new fields
- [x] `story_export.py` `_frontmatter_for` for plot: `value_schemas` is in extra, so it's exported automatically via `fm.update(extra)`
- [x] `story_export.py` `_frontmatter_for` for scene: `value_turns` is in extra, so it's exported automatically
- [x] `story_import.py` `_extra_for` for plot: `value_schemas` is in schema, so it's accepted automatically
- [x] `story_import.py` `_extra_for` for scene: `value_turns` is in schema, so it's accepted automatically
- [x] Verify with a round-trip test

> **Verified by running** (export → delete DB → reimport → compare extras): both fields round-trip identical. Export writes `value_schemas:` / `value_turns:` into the frontmatter (checked in the written .md), and the reimport stores them back unchanged. During the probe the importer surfaced a PRE-EXISTING, unrelated refusal — a character note with an empty `story_role` is refused with "Invalid story_role: ." — which blocked the round trip until the test character was given a role. Not touched here (out of scope, and the fixture has no such character); worth an issue if it is not already known.

### 4.7 — Run test suite
- [x] All existing tests still pass
- [x] `test_field_coverage.py` picks up new fields automatically — **fixed one thing it caught**: `_sample_value` now returns a real `value_schemas` entry instead of `["item-1", "item-2"]`, which the shape validator refuses (the failure was "'str' object has no attribute 'get'" on the plot create path). This is the exact failure the Phase 2 note predicted.
- [x] Add a test that `story_retrieve` with `fields=['value_lines']` returns the computed field
- [x] Add a test that `story_retrieve` with `fields=['value_schemas']` returns the stored field

> **Implementation note (4.7):** `TestTheReadBack` in `tests/test_value_turns.py` — 6 tests on the fixture that Phase 3 already built (two protagonists, one plot defining `trust`): the line's shape, story order (scenes created in reverse still read in order), a value with no turns yields no line, both retrieve exposures (computed and stored), and a value the plot no longer defines drops its turns. End-to-end on the real fixture (`save-the-children`) was verified by a temporary probe: after a value pass on the main plot, `story_load` carries `value_lines` on the plot and `value_turns` on the scene, and both disappear when empty (the `_omit` contract). The probe was deleted after confirming.

## Checklist

- [x] `compute_value_lines` implemented in `core/db.py`
- [x] `value_lines` exposed through `story_retrieve`
- [x] `value_lines` exposed through `story_describe` (no change needed, verified — doubled suffix fixed)
- [x] `value_lines` exposed through `story_load`
- [x] Scene payload builders carry `value_turns`
- [x] Export/import handle new fields
- [x] Full test suite passes

---

## Final Brief

Phase 4 complete. `compute_value_lines` (`core/db.py`) reads a plot's `value_schemas` and collects each value's turns across the scenes in story order — the same composite `(sequence order, scene order, id)` the load payload already sorts by — and it is exposed through retrieve, load and the dashboard. Scene payloads now carry `value_turns`; plot payloads carry `value_lines`. 1121 tests pass; the 9 failures are the pre-existing old-value-system ones Phase 5 removes (unchanged from the Phase 3 baseline of 1115, plus 6 new).

**What changed:**
- `core/db.py`: `compute_value_lines(project_path, plot_id)` — the computed read-back. `get_project_summary`'s `_build_plot` carries `value_lines` (computed once per plot, before the builders) and `_build_scene` carries `value_turns`; `get_dashboard_data`'s scene and plot dicts carry `value_turns` and `value_schemas`/`value_lines`. `_omit` defaults gained `value_lines: []` and `value_turns: []` so empty ones drop the key.
- `tools/story_retrieve.py`: a bespoke block in `_entity_fields` builds `value_lines` when a plot retrieve asks for it, in schema position; `_project_path(conn)` recovers the project folder from the connection (the `story_load.project_path_of` trick).
- `core/constants.py`: removed the hardcoded "(read-only, computed — do not set)" suffix from `value_lines`' description — `story_describe._entity_schemas` appends it, and Phase 2's declaration made it appear twice.
- `tests/test_value_turns.py`: `TestTheReadBack` — 6 tests on the Phase 3 fixture: the line's shape, story order, no-turns-no-line, both retrieve exposures, and a value the plot no longer defines dropping its turns.
- `tests/test_field_coverage.py`: `_sample_value` returns a real `value_schemas` entry; the plain-string sample was refused by the shape validator (the predicted failure, now fixed).

**Deviations from the task spec:**
- **`tools/story_load.py` has no `_build_scene`.** The base view is built entirely by `get_project_summary` in `core/db.py`; only that one exists. Task 4.5's third bullet named a function that does not exist.
- **The dashboard plot dict gained `value_schemas` and `value_lines`.** `_entity_dict` merges `extra`, so `value_schemas` would have flowed silently — but `value_lines` is computed and would have been absent, which contradicts the task's own finding that the dashboard needs both. Both are explicit now.
- **Story order is the load payload's composite, not "scene order_key within the plot's scenes".** `order_key` is per parent sequence, so a plot spanning several sequences needs the sequence's key in front. The task's phrasing ("within the plot's scenes") would have sorted across sequences by the scene's own key alone.

**Verified by running, not by reading:** the computed line's shape and story order via `compute_value_lines` directly (scenes created in reverse still read in order); retrieve returning both the computed and the stored field; describe emitting the read-only suffix exactly once; export → reimport round-trip of both fields on real writes (a temporary probe, since the probe caught a pre-existing, unrelated importer refusal on an empty `story_role`); the full fixture loading with a value pass applied and `value_lines`/`value_turns` present in `story_load` (temporary probe, deleted after confirming).

**Ready for Phase 5:** removal of the old fields and code (`get_value_drift`, `_has_charge`, `view='story_value'`, `_SCENE_CURVE`, the old scene/project value fields) and updating the fixtures. The 9 remaining failures are all in those files.
