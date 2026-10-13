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
- [x] Add `"values"` to the `view` enum (`load.py:21`) and a description line ("the value schemas and their turns, for a scene, unit, or the whole project").
- [x] Add properties: `scene`, `value` (strings) to the SCHEMA `properties` (the `plot`/`sequence`/`act`/`value` args). `plot`/`sequence`/`act` already exist as args for other views — confirm they are shared (`act` is at `load.py:34`); add `scene` and `value`.
- [x] `_extended_view`: `if view == "values": return _view_values(conn, project_path, args)`.

### T6.2 — `_view_values` (`tools/story_load.py`)
One function, three branches on which arg is present. Reuse `get_scene_value_turns` (Phase 1) once at the top, and `core.value_focus` for the major/minor lists.

- [x] **No `scene`/`plot`/`sequence`/`act`:** every value with its schema. `[{id, name, p, c, cd, nn, note}]`, sorted by name.
- [x] **`scene=<id>`:**
  - [x] Resolve the scene's sequence (`parent_id`) and act (sequence's `parent_id`).
  - [x] Emit `sequence_focus` = `value_focus.for_sequence(seq)` and `act_focus` = `value_focus.for_act(act)` — each `{major, minor}`.
  - [x] The plots the scene serves: `plot_roles` relations, else the sequence's `primary_plot`. For each such plot:
    - [x] The plot's values with schemas (from value entities), only values that actually have turns in the plot.
    - [x] For each value: split the plot's turns (story order) at this scene → `last_left {scene_id, to}` (the turn immediately before, its closing word) and `next {scene_id, from}` (the turn immediately after, its opening word). Omit either side when the scene is the first/last turn of that value.
  - [x] Wrap each plot under its id: `plots: {plot_id: {values: [{value, schema, last_left, next}]}}`.
- [x] **`plot=`/`sequence=`/`act=` (optional `value=`):**
  - [x] major/minor from the matching `value_focus.for_*`.
  - [x] For each major+minor value (or only `value` if given), its turns in story order: `{scene_id, plot, from, to}`, from the helper rows filtered to the unit. `plot` included per plan §5 ("scene, plot, from, to").
- [x] Unknown/absent ids → the same "Unknown view / not found" style the other views use; a unit with no turns → empty `turns`, empty `value_focus`, no error.

### T6.3 — Tests (`tests/test_values_view.py`, new)
- [x] **No args:** every value + schema, sorted by name.
- [x] **`scene=`:** sequence_focus and act_focus present; for a plot the scene serves, `last_left`/`next` carry the right scene ids and closing/opening words; a value with no turn before the scene has no `last_left`.
- [x] **`plot=` with and without `value=`:** major/minor + per-value turns in story order (scene, plot, from, to); `value=` filters to one.
- [x] **`sequence=` and `act=`:** same shape, all plots aggregated.
- [x] Scene with no `plot_roles` and no sequence `primary_plot` → `plots` empty, no crash.
- [x] Empty project → all-empty view, no error.

### T6.4 — Sizing check (plan §7)
- [x] Run `story_load view='values' plot=<main>` on the **live project** and on a synthetic long story (many scenes/turns); record the output size. Confirm it stays a usable "small, targeted view" (plan §1 goal). If a long story blows up, note the ceiling with a `ponytail:` comment and a cap — but only if a real measurement shows it, do not pre-optimize.
  - Measured (270 scenes / 540 turns synthetic; live fixture beside): `scene=` ~1.5KB, `no args` ~0.6KB, `sequence=` ~6.8KB, `act=` ~18KB, `plot=main` ~45KB, `plot=main value=trust` ~9KB. The primary use (`scene=`) stays tight; unit views scale linearly with turn count — the content the call exists to return. `ponytail:` note recorded, no cap (no pre-optimization).

## Cleanup / legacy
- [x] None additive. Ensure the old `value_lines` path is fully gone (Phase 4) so the view is the only read-back.
  - Confirmed: `value_lines`/`value_schemas` read-back paths are absent from `core/` and `tools/`. The only remaining references are `tests/live_value_pass.py` (a manual one-off markdown migration script for the live project, not collected by pytest, not a read-back) and design docs under `tasks/`. Phase 8 converts fixtures; out of Phase 6 scope.

## Checklist
- [x] `"values"` in the view enum + description; `scene`/`value` args added
- [x] `_view_values` covers all three calls (no-arg, scene, unit±value)
- [x] reuses `get_scene_value_turns` + `core.value_focus`, one helper pass
- [x] view tests green for all three shapes + empty/no-plot edge cases
- [x] sizing measured on a long story (no premature cap)
- [x] full suite at baseline

## Notes for the implementer
- **Depends on Phase 5.** Parallel-safe with Phase 7 (skill doc) and Phase 8 (migration) — different files (`story_load.py` vs skill markdown vs a script). The `story_load.py` touch here and Phase 5's `retrieve.py` touch are disjoint.
- One `get_scene_value_turns` pass at the top of `_view_values`; all three branches filter it in memory. Do not re-query per value — that is the trap the old `compute_value_lines` fell into.
- `scene=` is the use before evaluating a scene; keep it tight (schemas + last/next only, no full turn history) — that is the plan's intent and the reason the view exists.

## Final brief (Phase 6 complete)

**Shipped.** `story_load view='values'` with all three calls from plan §5.

- **T6.1** — `"values"` added to the `view` enum + description; `plot`, `sequence`, `scene`, `value` args added to SCHEMA `properties`. **Discrepancy from the phase doc:** it claimed `plot`/`sequence`/`act` "already exist as args" — only `act` did (it was shared with `dramatic_elements`). `plot` and `sequence` were missing and were added. `act`'s description was broadened to name both views that use it.
- **T6.2** — `_view_values` + `_value_schemas` + `_values_for_scene` + `_values_for_unit` in `tools/story_load.py`. One `get_scene_value_turns` pass feeds all branches; `core.value_focus.for_*` supplies the major/minor lists. **One real bug caught by tests and fixed:** `last_left`/`next` were first split across *all* the plot's turns mixed together, so a value's "last left" could land on a *different* value's turn that sat nearer in story order. Fixed by grouping the plot's turns **per value** and splitting each value's own line at the scene (verified against the fixture, where central-room-day→night→core carry both freedom and trust interleaved).
- **T6.3** — `tests/test_values_view.py`, 15 tests on the save-the-children fixture (known ground truth) + a synthetic no-plot/no-primary_plot scene and empty-project cases. All green.
- **T6.4** — sized on a 270-scene / 540-turn synthetic story: `scene=` ~1.5KB (the primary use stays tight), `no args` ~0.6KB, `plot=main` ~45KB. Unit views scale linearly with turn count — the content the call exists to return. `ponytail:` note recorded, **no cap** (no pre-optimization per the brief).
- **Guard test updated** — `test_story_load_views.py::TestDispatch` pinned the view-enum set to the four old views; updated to include `values` in both the enum assertion and the unknown-view error check.

**Full suite: 1157 passed, 0 failed** (baseline + 15 new tests + 2 guard assertions reworked). No backward-compat shims, no legacy paths left — the values view is the sole read-back for value schemas and turns.
