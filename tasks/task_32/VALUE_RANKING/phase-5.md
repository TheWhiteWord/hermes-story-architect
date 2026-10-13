# Phase 5 — Computed `value_focus` on plot, sequence, act, project

Refactor plan: `../Value Profile Ranking Values by Plot, Act, Sequence and Story.md`, §4 and §6 step 5.
Depends on: **Phase 4** (turns name value entities; `compute_value_lines` deleted). Builds on **Phase 1**'s `get_scene_value_turns` helper.

A computed field `value_focus` = `{major: [...], minor: [...]}`, each item `{value, scenes}` — a value and the number of scenes in which it shifts, **inside the unit**. Nothing stored. Read via `story_retrieve(fields=['value_focus'])` on a plot, sequence, act or project.

## Verification of the plan against code (done)

- **Counting source — CONFIRMED.** A turn carries `plot` (`entity.py:907`), and each scene has exactly one sequence (`parent_id`) and each sequence one act. So "scenes in which a value shifts inside a unit" = distinct `scene_id` per `value`, filtered by the unit. The Phase 1 helper's rows (`scene_id, plot, act_id, sequence_id, value, order`) are exactly the input. Count distinct scenes per value.
- **A scene counts once per value — CONFIRMED feasible.** Two turns of the same value in one scene → count the scene once. Dedupe on `(scene_id, value)` before counting.
- **Plot unit — CONFIRMED.** Filter rows `plot == plot_id`.
- **Sequence unit — all plots together, no main/sub distinction — CONFIRMED.** Filter `sequence_id == seq_id`, ignore `plot`.
- **Act unit — CONFIRMED.** Filter `act_id == act_id` (all its sequences), ignore plot.
- **Story (project) unit — needs the main plot. CONFIRMED reachable.** Main plot is `plot_scope == 'main'` (`constants.py:18,123`). Rule: story major = main plot's major list; story minor = subplots' major values not already major. Plot scopes are read from `entities.extra.plot_scope`.
- **Ties at the cut — note.** "Major is the three most frequent values, with ties at the cut all major." A count-based top-3 with ties means: sort by count desc, take all values whose count ≥ the count of the 3rd-ranked value. If the 3rd and 4th tie, both are major (4 majors). `VALUE_MAJOR_COUNT = 3`.
- **No inconsistency or wrong assumption found.** One open detail flagged below.

## Open detail to settle while implementing (low impact, decide in code)

When **fewer than `VALUE_MAJOR_COUNT` values have any turns**, major = all of them, minor = empty. When **zero** values have turns, both lists empty. This is the natural reading of the rule; no user decision needed — just don't crash on the short list.

## Where `value_focus` lives

New module `core/value_focus.py` — one home for the counting + the four unit scopes, so the retrieve read-back and (later) the values view call the same code. Reuses `get_scene_value_turns` from `core/db.py`.

## Tasks

### T5.1 — Constants (`core/constants.py`)
- [ ] `VALUE_MAJOR_COUNT = 3` — the cut constant (plan §4).
- [ ] Declare `value_focus` as a **computed** list field on `plot`, `sequence`, `act`, and `project` schemas: `{"type": "list", "default": [], "optional": True, "computed": True, "description": "...", "sub_fields": {value: string, scenes: number}}`. `computed` makes write paths refuse it (same as the old `value_lines`) and retrieve emit it. Add the `major`/`minor` shape to the description or as a documented object.

### T5.2 — `core/value_focus.py`
- [ ] `count_value_scenes(project_path) -> dict` — one pass via `get_scene_value_turns`, returns rows grouped so the four scopes filter cheaply. Dedupe `(scene_id, value)`.
- [ ] `_major_minor(counts: dict[str,int]) -> {major, minor}` — the shared cut: sort by count desc (value name as tiebreak for determinism), take all with count ≥ the `VALUE_MAJOR_COUNT`-th value's count as major, rest minor. Emit `[{value, scenes}]` sorted by count desc then name.
- [ ] Four public functions, each returning the `value_focus` dict:
  - [ ] `for_plot(project_path, plot_id)` — rows where `plot == plot_id`.
  - [ ] `for_sequence(project_path, seq_id)` — rows where `sequence_id == seq_id`.
  - [ ] `for_act(project_path, act_id)` — rows where `act_id == act_id`.
  - [ ] `for_project(project_path)` — read plot scopes; major = `_major_minor(main plot's value counts)`; minor = subplots' value counts, `_major_minor` each, union of their majors minus anything already in major, re-cut. (Plan: "subplots' major values that are not already major.")
- [ ] Empty project / no turns → `{major: [], minor: []}`, never an error.

### T5.3 — Retrieve read-back (`tools/story_retrieve.py`)
- [ ] Replace the deleted `value_lines` branch (`retrieve.py:119-122`, removed in Phase 4) with a `value_focus` branch dispatching on `entity_type`:
  - [ ] `plot` → `for_plot(conn-project-path, data["id"])`
  - [ ] `sequence` → `for_sequence(..., data["id"])`
  - [ ] `act` → `for_act(..., data["id"])`
  - [ ] `project` → `for_project(...)` (project `_resolve` ignores id; use the single project row)
- [ ] The first schema loop already reserves the key in schema position (`retrieve.py:108-114`) — `value_focus` fills it exactly as `value_lines` did. `fields=['value_focus']` and `fields=['all']` both work.

### T5.4 — Tests (`tests/test_value_focus.py`, new)
- [ ] Small project, **known counts**: main plot with values A×4 scenes, B×3, C×2, D×1 → major `[A,B,C]` (C at the cut), minor `[D]`. Assert `scenes` counts and order.
- [ ] **Tie at the cut:** A×4, B×3, C×2, D×2 → major `[A,B,C,D]` (C and D tie at 3rd), minor `[]`.
- [ ] **Scene counts once per value** even with two turns of that value in one scene.
- [ ] **Sequence unit** aggregates all plots (a value shifting in two plots' scenes within the sequence counts both scenes, no main/sub split).
- [ ] **Act unit** aggregates all the act's sequences.
- [ ] **Story unit:** main plot majors are story majors; a subplot major not in main is added to minor; a subplot value already major in main is not duplicated.
- [ ] Retrieve returns `value_focus` by name for all four types (plan §7 item 1) and via `fields=['all']`.
- [ ] Empty project → `{major:[], minor:[]}`.

### T5.5 — Verify plan §7 items
- [ ] `story_retrieve` returns a computed field requested by name for all four types (covered above).

## Cleanup / legacy
- [ ] No legacy left to remove here — `value_lines` was deleted in Phase 4; this phase adds the replacement computed field. Ensure the old `value_lines` retrieve branch is gone (Phase 4 owns that) and not resurrected.

## Checklist
- [ ] `VALUE_MAJOR_COUNT = 3` declared
- [ ] `value_focus` computed field on plot/sequence/act/project schemas
- [ ] `core/value_focus.py`: count + cut + four scopes; ties-at-cut correct
- [ ] retrieve read-back dispatches all four types; `fields=['value_focus']` and `['all']` work
- [ ] known-counts + tie + scene-once + sequence/act/prostory tests green
- [ ] full suite at baseline (1096 pass + the 2 pre-existing failures; Phase 8 may still be pending fixture conversion)

## Notes for the implementer
- **Depends on Phase 4, builds on Phase 1.** Run after Phase 4; parallel-safe with Phase 6 (view) and Phase 3 only if file regions stay disjoint (`core/value_focus.py` is new; `retrieve.py` is the shared touch point with Phase 4's deletion — sequence them to avoid a merge conflict on that branch).
- Reuse `get_scene_value_turns` (Phase 1) — do **not** re-scan scenes here. One helper, four scopes.
- Determinism: sort ties by value name so output is stable across calls (a set-ordered major list would make tests flaky).
