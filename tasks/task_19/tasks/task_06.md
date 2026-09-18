# Task 6: Add `act.sequences_list`, `scenes_list`, `sequence_count`, `scene_count`, `plots`

## Goal
Add all missing derived fields for acts. Currently all absent — act panel shows no sequences/plots.

## Spec (from `dev` branch `_enrich_structure` and `_enrich_acts_with_plots`)

### _enrich_structure (acts):
```python
for act in acts:
    seqs_in_act = sorted(
        [s for s in sequences if s.get("act_id") == act["id"]],
        key=lambda s: s.get("order", 0)
    )
    act["sequences_list"] = [s["id"] for s in seqs_in_act]
    act["scenes_list"] = sorted(
        [s["id"] for s in scenes if s.get("act_id") == act["id"]],
        key=lambda sid: next((s.get("order", 0) for s in scenes if s.get("id") == sid), 0)
    )
    act["sequence_count"] = len(act["sequences_list"])
    act["scene_count"] = len(act["scenes_list"])
```

### _enrich_acts_with_plots:
Same logic as sequence.plots (see Task 5 spec).

## What Old Dashboard Reads (line ~2967-3003)
```javascript
const seqRows = (act.sequences_list || []).map(sid => { ... });
const plotRows = (act.plots || []).map(p => {
    // reads p.id, p.plot_scope, p.plot_type
    // reads p.has_setup, p.has_crisis, p.has_climax, p.has_payoff
});
// line 3003: act.sequence_count
```

## Implementation

```python
# Act.sequences_list, scenes_list, counts
for act in acts:
    seqs_in_act = sorted(
        [s for s in sequences if s.get("parent_id") == act["id"]],
        key=lambda s: s.get("order", 0)
    )
    act["sequences_list"] = [s["id"] for s in seqs_in_act]
    act["scenes_list"] = sorted(
        [s["id"] for s in scenes if s.get("parent_id") == act["id"]],
        key=lambda sid: next((s.get("order", 0) for s in scenes if s.get("id") == sid), 0)
    )
    act["sequence_count"] = len(act["sequences_list"])
    act["scene_count"] = len(act["scenes_list"])

# Act.plots (same pattern as sequence)
plot_lookup = {p["id"]: p for p in plots}
for act in acts:
    act_plots = {}
    for scene in scenes:
        if scene.get("parent_id") != act["id"]:
            continue
        for p in scene.get("plots", []):
            pid = p.get("id") if isinstance(p, dict) else p
            if pid not in act_plots:
                meta = plot_lookup.get(pid, {})
                act_plots[pid] = {
                    "id": pid,
                    "has_setup": False, "has_crisis": False,
                    "has_climax": False, "has_payoff": False,
                    "plot_scope": meta.get("plot_scope", "sub"),
                    "plot_type": meta.get("plot_type", ""),
                    "value_arc": meta.get("value_arc", ""),
                }
            beat = p.get("beat", "") if isinstance(p, dict) else ""
            if beat == "setup": act_plots[pid]["has_setup"] = True
            elif beat == "crisis": act_plots[pid]["has_crisis"] = True
            elif beat == "climax": act_plots[pid]["has_climax"] = True
            elif beat == "payoff": act_plots[pid]["has_payoff"] = True
    act["plots"] = sorted(act_plots.values(), key=lambda x: (0 if x["plot_scope"] == "main" else 1, x["id"]))
```

## Files
- `core/db.py` — `get_dashboard_data()` act enrichment

## Verification (against old dashboard)
- [ ] Act panel (line ~2967): `act.sequences_list` must render sequence rows
- [ ] Act panel (line ~2976): `act.plots` must render plot rows with beat labels
- [ ] Act panel (line ~3003): `act.sequence_count` must show correct count

## Verification Results
- [x] `act.sequences_list` populated
- [x] `act.scenes_list` populated via act→sequences→scenes traversal (fix applied after initial verification found empty lists)
- [x] `act.sequence_count` and `act.scene_count` correct
- [x] `act.plots` has beat flags

Completed: 2026-09-18 — Fixed traversal + verified live plugin output.

## Completed
- **`core/db.py:488-524`** — Act enrichment block: `sequences_list`, `scenes_list` (via sequences), `sequence_count`, `scene_count`, and `plots` aggregation with beat flags. Reuses `plot_lookup` from Task 5.

## Fix Applied
- **Bug**: `act.scenes_list` was empty because scenes point to sequences (`parent_id`), not acts directly.
- **Fix**: Changed traversal to `act → sequences → scenes` — gather scene IDs from child sequences' `scenes_list` (already sorted by scene.order). Plot aggregation updated to use the same traversal path.
