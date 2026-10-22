# Phase 1 — Fix `compute_value_lines` defects + add the shared turns helper

Refactor plan: `../Value Profile Ranking Values by Plot, Act, Sequence and Story.md`, §2 and §6 step 1.
Branch: `feature/issue-redesign`. Baseline: **1096 pass / 2 fail** (`test_plot_roles::test_the_identity_fields_come_before_the_roles`, `test_retrieve_reading::test_fields_come_back_in_schema_order`) — both pre-existing schema-ordering failures, unrelated. Do not "fix" them here.

Goal: one shared helper returns every scene's turns with plot, act, sequence and order. Fix the two defects the plan names. Everything downstream (`value_focus`, the values view) is built on this helper.

## Verification of the plan against code (done)

- **Defect 1 — no plot filter. CONFIRMED.** `core/db.py:330-338`: the loop iterates every scene's `value_turns` and matches only on the value name (`key`), never on the turn's `plot`. Two plots that both name `trust` each see the other's turns.
- **Defect 2 — story order ignores acts. CONFIRMED.** `compute_value_lines` (`core/db.py:321-356`) sorts by `(parent_order, order_key)` where `parent` is the *sequence* only (`LEFT JOIN entities p ON e.parent_id = p.id`). A scene in act 2's sequence can sort before an act 1 scene. The correct act→sequence→scene key exists at `core/db.py:1558-1564` (`get_screenplay_text`: `COALESCE(pp.order_key), COALESCE(p.order_key), e.order_key`, joining scene→sequence→act).
- **Assumption — a turn carries its plot. CONFIRMED.** `validate_scene_value_turns` (`core/entity.py:907-911`) requires `turn.plot`, and the live DB's 6 scenes all carry `('trust', 'the-resistance')`. So filtering by `turn.plot == plot_id` is sound.
- **No inconsistency or wrong assumption found in §2 / step 1.** Proceeding.

## Scope

One helper, owned by `core/db.py` next to `compute_value_lines`. Signature:

```python
def get_scene_value_turns(project_path: Path) -> list[dict]:
    """Every scene's value turns, each tagged with plot/act/sequence and story order."""
```

One row per turn: `{scene_id, plot, act_id, sequence_id, order (composite act→sequence→scene), value, from, to, effects}`. One pass over all scenes; callers filter in Python (same model as today — `compute_value_lines` already does a full scan per plot, so this is strictly fewer scans).

## Tasks

### T1.1 — Add `get_scene_value_turns` (`core/db.py`)
- [x] One `SELECT` joining `scene e → sequence p → act pp` (same shape as `get_screenplay_text:1558-1564`), `WHERE e.type='scene' AND e.is_deleted=0`.
- [x] Composite order key `(COALESCE(pp.order_key,0), COALESCE(p.order_key,0), e.order_key, e.id)` per row — this is the act→sequence→scene order the plan cites at line 1564. Keep it as the row's `order` so every caller sorts identically.
- [x] Carry `plot` from `turn["plot"]`, and `act_id`/`sequence_id` resolved from the join (`e.parent_id` is the sequence; its parent is the act). Drop turns whose `value` is empty; skip non-dict turns/effects exactly as the current code does (`db.py:333-334, 341-342`).
- [x] Keep the `effects` projection (`character`, `levels[].conflict_level/effect`) as-is — `value_focus` does not need it, but the values view does, so the helper stays the single source.
- [x] Docstring: one pass, filtered per plot by the caller; name the two defects it fixes.

### T1.2 — Rewrite `compute_value_lines` on the helper (`core/db.py:286-367`)
- [x] Replace the per-plot scene scan with `get_scene_value_turns(project_path)`.
- [x] **Fix 1:** filter turns `turn["plot"] == plot_id` before bucketing by value. A turn naming another plot never enters the line.
- [x] **Fix 2:** sort each value's turns by the row's `order` (act→sequence→scene), not `(sequence order, scene order)`.
- [x] Preserve every existing output shape: `{value, schema, turns:[{scene_id, from, to, effects}]}`, values emitted in `value_schemas` declaration order, a value with no turns omitted (`db.py:357-365`). The internal `_sort` temp key can go — sort the tagged rows before projecting.
- [x] `get_project_summary` (`db.py:688-689`) calls `compute_value_lines` once per plot. Leave the call sites; the helper just changes what's underneath. (The N-scans comment at 682-687 is now stale-ish but harmless — the helper is one scan, but summary still calls per plot; do not hoist in this phase, it is out of scope.)

### T1.3 — Tests (`tests/test_value_turns.py`)
- [x] **Two plots sharing a value name:** main plot + subplot both define `trust`; scenes of each carry turns. Assert each plot's `value_lines` shows only its own turns. This is the defect-1 regression test.
- [x] **Scenes across acts:** a scene in act 2 whose `order_key` is lower than an act 1 scene's. Assert `value_lines` turns come out act-1-before-act-2 (defect-2 regression test). Reuse the `test_turns_read_in_story_order_not_write_order` structure (`test_value_turns.py:297`) but add the act dimension.
- [x] Add a direct unit test of `get_scene_value_turns`: rows carry `plot`, `act_id`, `sequence_id`, `order`; two plots are distinguishable.
- [x] **Keep `TestTheReadBack` / `TestRegistrationOnWrite` green as-is** — the plot-filter and order fixes must not change single-plot behavior.

### T1.4 — Verification
- [x] `python -m pytest tests/test_value_turns.py -q` — all green.
- [x] Full suite: no new failures vs the 1096/2 baseline. The 2 pre-existing failures may stay; nothing else may break.
- [x] Naming check: `get_scene_value_turns` reads as "the turns with their placement"; `compute_value_lines` unchanged name still accurate (it still builds the plot's lines). No rename needed.

## Cleanup / legacy
- [x] Remove the now-dead local `scenes` SELECT and `_sort`-tuple construction inside `compute_value_lines` — replaced by the helper, no compatibility shim.

## Checklist
- [x] Helper added, one pass, act→sequence→scene order
- [x] `compute_value_lines` filters by plot and sorts by act→sequence→scene
- [x] Two new regression tests (shared value across plots; scenes across acts)
- [x] Full suite at baseline (1096 pass, only the 2 pre-existing ordering failures)
- [x] Dead per-plot scan removed

## Notes for the implementer
- Do **not** touch `plot.value_schemas`, the inline `schema`, or `validate_scene_value_turns` here — those are Phase 4. Phase 1 only reads the schemas the plot still owns.
- The helper is deliberately general (every turn, all plots) because `value_focus` (Phase 5) needs exactly this and reuses it — build it once, don't parametrize by plot yet.
- Downstream phases depend on this helper's row shape (`plot/act_id/sequence_id/order`). Freeze it now.

## Final brief (implementation complete)

Both defects fixed via one shared helper; `compute_value_lines` is now a thin projection of it. The per-plot scene scan is gone — the helper's one pass replaces it. Row shape is frozen as the plan specifies: `{scene_id, plot, act_id, sequence_id, order (act→sequence→scene→scene_id), value, from, to, effects}`. Story order is the composite act→sequence→scene key (matching `get_screenplay_text`), so an act-2 scene can no longer sort before an act-1 scene. Turns are tagged with their plot and filtered `turn["plot"] == plot_id`, so a value two plots share reads only its own turns. Empty-value turns dropped; non-dict turns/effects skipped exactly as before.

One design note on the order key: the composite's final tiebreak is `scene_id`, not `rowid` — the existing `test_turns_read_in_story_order_not_write_order` (scenes s2/s3, both unparented, both order_key 0) relies on the id tiebreak to read s2-before-s3, and the old code's key ended on `scene_id` too. Keeping `scene_id` preserves that single-plot behavior while the act/sequence lead fixes the cross-act case. Unparented scenes COALESCE their missing act/sequence keys to 0 (sort first), matching `get_screenplay_text`.

Tests: 4 new (`TestSharedValueAcrossPlots` 1, `TestTurnsReadAcrossActs` 3). Full suite 1100 pass / 2 fail — the same 2 pre-existing schema-ordering failures (unrelated, per the plan's baseline note). Nothing else broke; `TestTheReadBack` and `TestRegistrationOnWrite` stay green as required.

Skipped: hoisting the helper scan out of `get_project_summary`'s per-plot loop — out of scope this phase (call sites unchanged); add when the values view/`value_focus` make it a hot path.
