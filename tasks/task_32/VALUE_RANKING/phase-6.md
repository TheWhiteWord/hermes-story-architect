# Phase 6 — The `values` view

Refactor plan: `../Value Profile Ranking Values by Plot, Act, Sequence and Story.md`, §5 and §6 step 6.
Depends on: **Phase 5** (`value_focus` + `core/value_focus.py`). Uses **Phase 1**'s `get_scene_value_turns` and **Phase 3**'s value entities.

`story_load view='values'`, built for three uses and nothing more.

## Verification against code (done)

- **Dispatch — CONFIRMED.** `_extended_view` (`load.py:106-117`) dispatches by `view`; add `if view == "values": return _view_values(conn, project_path, args)` and `"values"` to the SCHEMA `enum` (`load.py:21`) + description. Views get `project_path` already (`load.py:91`), so `core.db`/`core.value_focus` helpers are callable, same as `_view_arc`.
- **Scene → its plots — CONFIRMED.** `plot_roles` relations (`retrieve.py:151-158`), else the scene's sequence `extra.primary_plot` (`load.py:194`).
- **Turns in story order — CONFIRMED.** `get_scene_value_turns` rows carry `order` (act→sequence→scene) and `scene_id, plot, value, from, to`.
- **"Last left / next turn" per value for a scene — CONFIRMED computable.** For a plot's value, sort that plot's turns by `order`; the scene's position splits them into "before" (last = where it was last left) and "after" (first = the next turn). Rows carry everything needed.
- **Value entities for schemas — CONFIRMED.** `SELECT id,name,extra FROM entities WHERE type='value'` gives p/c/cd/nn per value.
- **No inconsistency found.** One sizing concern is a plan §7 verification item (below), not a blocker.

## The three calls (plan §5)

| Call | Returns |
| --- | --- |
| no arguments | Every value with its schema. The one command to see what exists. |
| `scene=<id>` | (1) major/minor of the scene's sequence and of its act; (2) for each plot the scene serves: the plot's values with schemas, and for each value where it was last left (scene, closing word) and the next turn after (scene, opening word). |
| `plot=`, `sequence=`, `act=` (opt. `value=`) | major/minor lists, and for each value its turns in story order (scene, plot, from, to). |

## Tasks

### T6.1 — Tool schema (`tools/story_load.py`)
- [ ] Add `"values"` to the `view` enum (`load.py:21`) and a description line ("the value schemas and their turns, for a scene, unit, or the whole project").
- [ ] Add properties: `scene`, `value` (strings) to the SCHEMA `properties` (the `plot`/`sequence`/`act`/`value` args). `plot`/`sequence`/`act` already exist as args for other views — confirm they are shared (`act` is at `load.py:34`); add `scene` and `value`.
- [ ] `_extended_view`: `if view == "values": return _view_values(conn, project_path, args)`.

### T6.2 — `_view_values` (`tools/story_load.py`)
One function, three branches on which arg is present. Reuse `get_scene_value_turns` (Phase 1) once at the top, and `core.value_focus` for the major/minor lists.

- [ ] **No `scene`/`plot`/`sequence`/`act`:** every value with its schema. `[{id, name, p, c, cd, nn, note}]`, sorted by name.
- [ ] **`scene=<id>`:**
  - [ ] Resolve the scene's sequence (`parent_id`) and act (sequence's `parent_id`).
  - [ ] Emit `sequence_focus` = `value_focus.for_sequence(seq)` and `act_focus` = `value_focus.for_act(act)` — each `{major, minor}`.
  - [ ] The plots the scene serves: `plot_roles` relations, else the sequence's `primary_plot`. For each such plot:
    - [ ] The plot's values with schemas (from value entities), only values that actually have turns in the plot.
    - [ ] For each value: split the plot's turns (story order) at this scene → `last_left {scene_id, to}` (the turn immediately before, its closing word) and `next {scene_id, from}` (the turn immediately after, its opening word). Omit either side when the scene is the first/last turn of that value.
  - [ ] Wrap each plot under its id: `plots: {plot_id: {values: [{value, schema, last_left, next}]}}`.
- [ ] **`plot=`/`sequence=`/`act=` (optional `value=`):**
  - [ ] major/minor from the matching `value_focus.for_*`.
  - [ ] For each major+minor value (or only `value` if given), its turns in story order: `{scene_id, plot, from, to}`, from the helper rows filtered to the unit. `plot` included per plan §5 ("scene, plot, from, to").
- [ ] Unknown/absent ids → the same "Unknown view / not found" style the other views use; a unit with no turns → empty `turns`, empty `value_focus`, no error.

### T6.3 — Tests (`tests/test_values_view.py`, new)
- [ ] **No args:** every value + schema, sorted by name.
- [ ] **`scene=`:** sequence_focus and act_focus present; for a plot the scene serves, `last_left`/`next` carry the right scene ids and closing/opening words; a value with no turn before the scene has no `last_left`.
- [ ] **`plot=` with and without `value=`:** major/minor + per-value turns in story order (scene, plot, from, to); `value=` filters to one.
- [ ] **`sequence=` and `act=`:** same shape, all plots aggregated.
- [ ] Scene with no `plot_roles` and no sequence `primary_plot` → `plots` empty, no crash.
- [ ] Empty project → all-empty view, no error.

### T6.4 — Sizing check (plan §7)
- [ ] Run `story_load view='values' plot=<main>` on the **live project** and on a synthetic long story (many scenes/turns); record the output size. Confirm it stays a usable "small, targeted view" (plan §1 goal). If a long story blows up, note the ceiling with a `ponytail:` comment and a cap — but only if a real measurement shows it, do not pre-optimize.

## Cleanup / legacy
- [ ] None additive. Ensure the old `value_lines` path is fully gone (Phase 4) so the view is the only read-back.

## Checklist
- [ ] `"values"` in the view enum + description; `scene`/`value` args added
- [ ] `_view_values` covers all three calls (no-arg, scene, unit±value)
- [ ] reuses `get_scene_value_turns` + `core.value_focus`, one helper pass
- [ ] view tests green for all three shapes + empty/no-plot edge cases
- [ ] sizing measured on a long story (no premature cap)
- [ ] full suite at baseline

## Notes for the implementer
- **Depends on Phase 5.** Parallel-safe with Phase 7 (skill doc) and Phase 8 (migration) — different files (`story_load.py` vs skill markdown vs a script). The `story_load.py` touch here and Phase 5's `retrieve.py` touch are disjoint.
- One `get_scene_value_turns` pass at the top of `_view_values`; all three branches filter it in memory. Do not re-query per value — that is the trap the old `compute_value_lines` fell into.
- `scene=` is the use before evaluating a scene; keep it tight (schemas + last/next only, no full turn history) — that is the plan's intent and the reason the view exists.
