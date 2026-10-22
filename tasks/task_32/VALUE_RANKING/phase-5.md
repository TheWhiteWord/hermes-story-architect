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
- [x] `VALUE_MAJOR_COUNT = 3` — the cut constant (plan §4).
- [x] Declare `value_focus` as a **computed** list field on `plot`, `sequence`, `act`, and `project` schemas: `{"type": "list", "default": [], "optional": True, "computed": True, "description": "...", "sub_fields": {value: string, scenes: number}}`. `computed` makes write paths refuse it (same as the old `value_lines`) and retrieve emit it. Add the `major`/`minor` shape to the description or as a documented object.

**Brief:** `VALUE_MAJOR_COUNT = 3` added beside `CONFLICT_LEVELS`. `value_focus` declared as a computed **object** field (`{major, minor}` as `sub_fields`, each a list of `{value, scenes}`) on all four schemas — an object, not a list, because the shape is two named lists. The retrieve-order test pin in `tests/test_retrieve_reading.py` was extended with `value_focus` at the end of the plot schema.

### T5.2 — `core/value_focus.py`
- [x] `count_value_scenes(project_path) -> dict` — one pass via `get_scene_value_turns`, returns rows grouped so the four scopes filter cheaply. Dedupe `(scene_id, value)`.
- [x] `_major_minor(counts: dict[str,int]) -> {major, minor}` — the shared cut: sort by count desc (value name as tiebreak for determinism), take all with count ≥ the `VALUE_MAJOR_COUNT`-th value's count as major, rest minor. Emit `[{value, scenes}]` sorted by count desc then name.
- [x] Four public functions, each returning the `value_focus` dict:
  - [x] `for_plot(project_path, plot_id)` — rows where `plot == plot_id`.
  - [x] `for_sequence(project_path, seq_id)` — rows where `sequence_id == seq_id`.
  - [x] `for_act(project_path, act_id)` — rows where `act_id == act_id`.
  - [x] `for_project(project_path)` — read plot scopes; major = `_major_minor(main plot's value counts)`; minor = subplots' value counts, `_major_minor` each, union of their majors minus anything already in major, re-cut. (Plan: "subplots' major values that are not already major.")
- [x] Empty project / no turns → `{major: [], minor: []}`, never an error.

**Brief:** `count_value_scenes` was renamed `_counts(rows, key)` — it takes the rows the caller already loaded (one `get_scene_value_turns` per scope function, since four callers in one turn each re-read the DB otherwise) and returns `{value: distinct-scene-count}`, deduped on `(scene_id, value)` via a `defaultdict(set)`. `_plot_scopes` reads `plot_scope` from `entities.extra` on its own connection (it runs in a separate call from the turn scan, so reusing `get_scene_value_turns`' connection would mean extending that helper's contract for one field). `for_project`'s minor is the union of each subplot's majors not already in story major, sorted count desc then name — a subplot major keeps its scenes count even if that count would not survive a second cut, per plan §4's "subplots' major values". No main plot → every plot counts as a subplot, so a project with only subplots still reports them rather than empty. Ties at the cut: all values whose count ≥ the 3rd value's count are major.

### T5.3 — Retrieve read-back (`tools/story_retrieve.py`)
- [x] Replace the deleted `value_lines` branch (`retrieve.py:119-122`, removed in Phase 4) with a `value_focus` branch dispatching on `entity_type`:
  - [x] `plot` → `for_plot(conn-project-path, data["id"])`
  - [x] `sequence` → `for_sequence(..., data["id"])`
  - [x] `act` → `for_act(..., data["id"])`
  - [x] `project` → `for_project(...)` (project `_resolve` ignores id; use the single project row)
- [x] The first schema loop already reserves the key in schema position (`retrieve.py:108-114`) — `value_focus` fills it exactly as `value_lines` did. `fields=['value_focus']` and `fields=['all']` both work.

**Brief:** The phase file's `retrieve.py:119-122` reference is stale — Phase 4 already deleted the `value_lines` branch, so this adds a new one, it replaces nothing. A `VALUE_FOCUS_SCOPES` dispatch table maps entity_type → scope function; `_project_path` (deleted in Phase 4 along with its only caller) was restored, since the computed field needs the project folder from the connection. `for_project` takes no id — the project row is a singleton, matching `_resolve` — so the branch special-cases it rather than passing `data["id"]` it would ignore. Verified: `fields=['all']` emits `value_focus` in schema position (test pin extended); `fields=['value_focus']` works (T5.4 tests).

### T5.4 — Tests (`tests/test_value_focus.py`, new)
- [x] Small project, **known counts**: main plot with values A×4 scenes, B×3, C×2, D×1 → major `[A,B,C]` (C at the cut), minor `[D]`. Assert `scenes` counts and order.
- [x] **Tie at the cut:** A×4, B×3, C×2, D×2 → major `[A,B,C,D]` (C and D tie at 3rd), minor `[]`.
- [x] **Scene counts once per value** even with two turns of that value in one scene.
- [x] **Sequence unit** aggregates all plots (a value shifting in two plots' scenes within the sequence counts both scenes, no main/sub split).
- [x] **Act unit** aggregates all the act's sequences.
- [x] **Story unit:** main plot majors are story majors; a subplot major not in main is added to minor; a subplot value already major in main is not duplicated.
- [x] Retrieve returns `value_focus` by name for all four types (plan §7 item 1) and via `fields=['all']`.
- [x] Empty project → `{major:[], minor:[]}`.

**Brief:** 19 tests in `tests/test_value_focus.py`, all on a synthetic project with known counts (values named words — a single letter is a scene column, and a turn naming one silently reads as that column; caught while writing the fixtures, not by a reviewer). Covers: known counts with major at the cut; the tie-at-the-cut (4 majors); scene-counts-once; the two scopes that aggregate (sequence, act); a plot never seeing another plot's turns (the defect §2 fixed); the story scope's both rules; the empty project; and retrieve read-back by name and via `['all']` for all four types. Suite: **1142 passed** (baseline 1123 + 19; the one existing schema-order pin extended with `value_focus`).

### T5.5 — Verify plan §7 items
- [x] `story_retrieve` returns a computed field requested by name for all four types (covered above).
- [x] (Also verified, belongs to earlier phases but pinned here by the same test file:) a `value` entity reads back by id through retrieve — already working since Phase 2, exercised by `TestRetrieveReadBack`'s four-type sweep via the shared fixture pattern.

## Cleanup / legacy
- [x] No legacy left to remove here — `value_lines` was deleted in Phase 4; this phase adds the replacement computed field. Ensure the old `value_lines` retrieve branch is gone (Phase 4 owns that) and not resurrected.

**Brief:** confirmed — `git show 2b693d7` (Phase 4) removed the `value_lines` branch and `compute_value_lines`; no `value_lines` reference remains in `core/` or `tools/` (the hits under `tasks/task_32/ISSUE_B1_B2/` and `task_30/` are phase-history docs, not code).

## Checklist
- [x] `VALUE_MAJOR_COUNT = 3` declared
- [x] `value_focus` computed field on plot/sequence/act/project schemas
- [x] `core/value_focus.py`: count + cut + four scopes; ties-at-cut correct
- [x] retrieve read-back dispatches all four types; `fields=['value_focus']` and `['all']` work
- [x] known-counts + tie + scene-once + sequence/act/project tests green
- [x] full suite at baseline (1142 passed: 1123 baseline + 19 new; no pre-existing failures)

## Notes for the implementer
- **Depends on Phase 4, builds on Phase 1.** Run after Phase 4; parallel-safe with Phase 6 (view) and Phase 3 only if file regions stay disjoint (`core/value_focus.py` is new; `retrieve.py` is the shared touch point with Phase 4's deletion — sequence them to avoid a merge conflict on that branch).
- [x] Reuse `get_scene_value_turns` (Phase 1) — do **not** re-scan scenes here. One helper, four scopes.
- [x] Determinism: sort ties by value name so output is stable across calls (a set-ordered major list would make tests flaky).
