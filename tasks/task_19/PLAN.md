# Re-Alignment Plan: `sqlite-migration` → `dev` Storage Contract

## Purpose
Fix the regressions introduced by the SQLite migration so that the new implementation
matches the storage contract defined by the `dev` branch (the working original).

## Rules (apply to every task)
1. READ the task file section, the relevant spec section, and the actual code it touches.
2. VERIFY against code before editing. If code contradicts task or spec, STOP and flag.
3. IMPLEMENT the task.
4. CHECK-MARK the task file and append a one-line completion note.
5. After all tasks in a phase are done, append a brief phase summary.
6. If a blocker is encountered that cannot be resolved simply and is non-blocking, 
   make a note in `### Deferred Issues` and move on.

## Good Practice
- **Naming:** after a rename/refactor, the name describes what the code IS NOW.
  No `old_`, `_legacy`, `_bak`, `_deprecated` in names.
- **No historical-reference comments** that contradict the new code.
- **No legacy code, unused imports, dead functions** — remove them as part of the 
  task that makes them dead.
- **No compatibility guards.** App is pre-publication.

---

## Phase 0: Data Integrity (foundational — derived fields depend on clean data)
- [x] **Task 1**: Fix `relationships` round-trip corruption
  - Store label+feeling as JSON in relation note, parse on denormalize, reconstruct on export
- [x] **Task 2**: Fix `arc_beats_list` shape (lean objects, not bloated entity dicts)
  - Emit `{id, label, scene, shift, y, order, is_crisis, is_climax}` — exactly what old dashboard reads
- [x] **Task 3**: Fix character/location `scenes` shape
  - `{id, title, heading}` objects from both `character_scene` and `location_scene` relations

## Phase 1: Missing Derived Fields (dashboard structure panels)
- [x] **Task 4**: Add `scene.arc_beats` (reverse from arc entities)
  - `{character, beat_id, label, y, is_crisis, is_climax}` per beat
- [x] **Task 5**: Add `sequence.scenes_list`, `scene_count`, `plots`
  - `scenes_list[]`: scene IDs where parent_id = seq.id, sorted by order
  - `plots[]`: aggregated from scene.plots with beat flags
- [x] **Task 6**: Add `act.sequences_list`, `scenes_list`, `sequence_count`, `scene_count`, `plots`
  - Same patterns as sequence, applied to acts
- [x] **Task 7**: Fix `scene.plots` — include beat info
  - Changed from `[plot_id_strings]` to `[{id, beat}]` objects

## Phase 2: Project Counts & Stats
- [x] **Task 8**: Add project count fields (scene_count through arc_count)
- [x] **Task 9**: Fix `structural_stats.plotCoverage` (currently empty array)
  - Compute per-plot scene coverage stats
- [x] **Task 10**: Fix `project.act_count` (max of declared vs actual)

## Phase 2 Summary
All 3 tasks complete. Project counts and stats now match the `dev` branch contract:
- **project counts** (Task 8): all 8 fields (`scene_count` through `arc_count`) emitted directly from entity array lengths
- **plotCoverage** (Task 9): computed from `scene.plots` — per-plot unique scene count + coverage percentage, sorted by sceneCount descending
- **act_count** (Task 10): `max(declared, actual)` — declared value from project frontmatter via extra, matches old `_parse_project` behavior

Phase 2 → Phase 3 (Performance & Cleanup) is now ready to proceed.

---

## Phase 3: Performance & Cleanup
- [x] **Task 11**: Fix scene.characters reverse lookup performance
- [x] **Task 12**: Fix `unfilled_fields` to check status column for scene/sequence/plot

## Phase 3 Summary
Both performance & cleanup tasks complete:
- **Task 11**: O(n×m) scan → single-pass reverse lookup for scene characters, locations, AND plots. 3 loops over rel_rows collapsed into 1.
- **Task 12**: Status column merged into extra before unfilled check for scene/sequence/plot/act. No more false "unfilled" when status is set in DB.

Phase 3 → Phase 4 (Arc ID Format) is now ready.

### Task 11
**`core/db.py:208-219`** — Built `scene_chars`, `scene_locs`, `scene_plots` dicts from `rel_rows` in single pass. Replaced O(n×m) scan in scene denormalization with O(1) dict lookups. Also replaced the separate plots reverse lookup (same O(n) problem) into the same loop — 3 scans collapsed to 1.

### Task 12
**`core/db.py:128-136`** — In `get_project_summary()`, merged `status` from `row[4]` into extra before calling `unfilled_fields` for scene/sequence/plot/act. Status column was only read from extra, so entities with status set in DB were always reported as unfilled. No signature change — Option B from task spec.

---

## Phase 4: Arc ID Format (breaking change — DISCUSS WITH USER)
- [ ] **Task 13**: Decide arc ID format (composite `kael-1` vs simple `1`)
  - Dashboard works either way; affects external references and migration

---

## Files Touched Summary
| File | Tasks |
|------|-------|
| `core/db.py` | 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12 |
| `core/entity.py` | 1 |
| `tools/story_export.py` | 1 |
| `tools/story_import.py` | 1, 10, 13 |

## Verification Strategy
After each phase, run the dashboard and compare against `git show dev:src/dashboard/story-dashboard.html`
to verify the JSON injection shapes match the old contract.

---

## FINAL BRIEF
### Task 1
- **`core/entity.py:241`** — `relations_for_insert()`: character_relationship `note` → JSON `{"label": "...", "feeling": "..."}` (was `"{label} — {feeling}"` string, lost label on read-back)
- **`tools/story_import.py:300`** — duplicate inline path (missed by task): same fix, `note` → JSON
- **`core/db.py:256`** — `get_dashboard_data()`: parse JSON note, use `parsed["label"]`/`parsed["feeling"]` (was `t["name"]` as label — data corruption)
- **`tools/story_export.py:64`** — added `character_relationship` export (was missing entirely)

Round-trip: FM `relationships[]` → DB `note` (JSON) → dashboard `{id, label, feeling}` → export → FM. Label preserved, no more target character name substitution.

### Task 2
- **`core/db.py:399`** — `get_dashboard_data()`: replaced `c["arc_beats_list"].append(a)` (full entity dict) with lean `{id, label, scene, shift, y, order, is_crisis, is_climax}` object. Fields sourced from already-denormalized arc dicts (lines 371-387). Sort by `order` still works. No bloat.

### Task 3
- **`core/db.py:248-260`** — Character `scenes`: replaced raw `rel_map.get(eid, {}).get("character_scene", [])` (which returned `[{to_id, note}]` dicts) with a loop that looks up each scene in `entity_by_id` and builds `[{id, title, heading}]`. Sources `title` from `entity_by_id[sid]["name"]` and `heading` from `entity_by_id[sid]["extra"]["heading"]`.
- **`core/db.py:326-338`** — Location `scenes`: replaced O(n²) scan (`for sid, kinds in rel_map.items() if "location_scene" in kinds and eid in kinds["location_scene"]`) with same pattern as character — iterate `rel_map.get(eid, {}).get("location_scene", [])`, lookup in `entity_by_id`, build `[{id, title, heading}]`.

Both shapes now match `dev` branch `_enrich_entity_scenes` contract. Dashboard `_scene_objs` path can match scenes by heading when IDs differ after normalization.

---

## Phase 0 Summary
N.A.

---

### Task 4
- **`core/db.py:438-456`** — After arc denormalization and before `story_arcs = arcs`, built `scene_beats` dict by grouping arcs where `a.get("scene")` matches a scene ID. Each entry is `{character, beat_id, label, y, is_crisis, is_climax}` — directly from already-denormalized arc fields. Attached to scene dicts via `s["arc_beats"] = scene_beats.get(s["id"], [])`. Matches `dev` branch `_enrich_scenes_with_arcs` contract. Dashboard lines 2272 and 3864 now render arc dots and `hasBeats` correctly.

### Task 5
- **`core/db.py:457-487`** — After `scene.arc_beats` assignment, built `sequence.scenes_list` (sorted by scene.order), `scene_count`, and `plots` aggregation. Uses `plot_lookup` for meta (plot_scope, plot_type, value_arc). Plots sorted main-first then by ID. Beat info from `scene.plots` — works pre-Task 7 (flags False) and post-Task 7 (flags populated from `{id, beat}` objects).

### Task 6
- **`core/db.py:488-524`** — Act enrichment block: built `sequences_list` (sequences where parent_id = act.id, sorted by order), `scenes_list` (all scenes from child sequences, gathered via seq.scenes_list), `sequence_count`, `scene_count`, and `plots` aggregation. Plot meta sourced from `plot_lookup` (carried over from Task 5); beat flags set from `scene.plots` `{id, beat}` objects (populated by Task 7).
- **Bug fix**: Initial implementation filtered scenes by `parent_id == act.id`, but in the new DB scenes point to sequences, not acts — so `act.scenes_list` was always empty. Fixed by traversing act→sequences→scenes: iterate child sequences, collect their `scenes_list` IDs, sort by scene.order. Plot aggregation updated to use the same traversal path.

### Task 7
- **`core/db.py:307-318`** — Changed scene plots from `[plot_id_strings]` to `[{id, beat}]` objects. Added `plot_crisis` and `plot_climax` to the relation kinds (was only setup/payoff). Dashboard now renders beat labels on scene plot buttons.

---

## Phase 1 Summary
All 4 tasks complete. Scene/sequence/act plot aggregations render correctly in the dashboard:
- **scene.plots**: `{id, beat}` objects with beat labels
- **sequence.scenes_list / scene_count / plots**: derived from scenes where parent_id = seq.id
- **act.sequences_list / scenes_list / counts / plots**: derived from child entities
- **scene.arc_beats**: reverse lookup from arc entities with beat info

Phase 1 → Phase 2 (Project Counts & Stats) is now ready to proceed.

---

### Task 8
**`core/db.py:557-566`** — Added all 8 project count fields to `proj_dict` before `story_data` is created. Direct `len()` of already-built entity arrays (scenes, characters, locations, worlds, plots, sequences, acts, story_arcs) — no extra DB queries. Dashboard stats row (line ~2437-2443) now reads actual values instead of falling back to array lengths.

### Task 9
**`core/db.py:646-667`** — Replaced hardcoded `"plotCoverage": []` with the full calculation from `dev` branch `compute_structural_stats()`. Iterates `scene.plots` to build per-plot scene sets, then emits `{id, name, plot_scope, plot_type, value_arc, sceneCount, coveragePct}` sorted by sceneCount descending. Reuses `plot_lookup` (built in Task 5). Dashboard chart at line ~3425 now renders actual coverage data.

### Task 10
**`core/db.py:564`** — One-line fix: changed `proj_dict["act_count"] = len(acts)` → `max(proj_dict.get("act_count", 3), len(acts))`. The declared value comes from project.md frontmatter via `_import_project` → extra (skip set only excludes `name`/`logline`). `proj_dict` flattens extra so `proj_dict.get("act_count", 3)` reads the declared value. Matches dev branch `_parse_project` contract: user can declare 3 acts even if only 2 exist.

---

## Phase 2 Summary
All 3 tasks complete. Project counts and stats now match the `dev` branch contract:
- **project counts** (Task 8): all 8 fields (`scene_count` through `arc_count`) emitted directly from entity array lengths — no extra DB queries
- **plotCoverage** (Task 9): computed from `scene.plots` — per-plot unique scene count + coverage percentage, sorted by sceneCount descending; reuses `plot_lookup` from Task 5
- **act_count** (Task 10): `max(declared, actual)` — declared value from project frontmatter via extra, matches old `_parse_project` behavior

Phase 2 → Phase 3 (Performance & Cleanup) is now ready to proceed.

---

### Task 11
**`core/db.py:208-219`** — Built `scene_chars`, `scene_locs`, `scene_plots` dicts from `rel_rows` in single pass. Replaced O(n×m) scan in scene denormalization with O(1) dict lookups. Also replaced the separate plots reverse lookup (same O(n) problem) into the same loop — 3 scans collapsed to 1.

### Task 12
**`core/db.py:128-136`** — In `get_project_summary()`, merged `status` from `row[4]` into extra before calling `unfilled_fields` for scene/sequence/plot/act. Status column was only read from extra, so entities with status set in DB were always reported as unfilled. No signature change — Option B from task spec.

---

## Phase 3 Summary
Both performance & cleanup tasks complete:
- **Task 11**: O(n×m) scan → single-pass reverse lookup for scene characters, locations, AND plots. 3 loops over rel_rows collapsed into 1.
- **Task 12**: Status column merged into extra before unfilled check for scene/sequence/plot/act. No more false "unfilled" when status is set in DB.

---
