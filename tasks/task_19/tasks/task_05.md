# Task 5: Add `sequence.scenes_list`, `scene_count`, `plots`

## Goal
Add the three missing derived fields for sequences: `scenes_list[]`, `scene_count`, `plots[]`. Currently all absent — sequence panel shows no scenes.

## Spec (from `dev` branch)
```python
# _enrich_structure
for seq in sequences:
    scenes_in_seq = sorted(
        [s for s in scenes if s.get("sequence_id") == seq["id"]],
        key=lambda s: s.get("order", 0)
    )
    seq["scenes_list"] = [s["id"] for s in scenes_in_seq]
    seq["scene_count"] = len(seq["scenes_list"])

# _enrich_sequences_with_plots
for seq in sequences:
    seq_plots = {}
    for scene in scenes:
        if scene.get("sequence_id") != seq["id"]:
            continue
        for p in scene.get("plots", []):
            pid = p.get("id") if isinstance(p, dict) else p
            if pid not in seq_plots:
                meta = plot_lookup.get(pid, {})
                seq_plots[pid] = {
                    "id": pid,
                    "has_setup": False, "has_crisis": False,
                    "has_climax": False, "has_payoff": False,
                    "plot_scope": meta.get("plot_scope", "sub"),
                    "plot_type": meta.get("plot_type", ""),
                    "value_arc": meta.get("value_arc", ""),
                }
            beat = p.get("beat", "") if isinstance(p, dict) else ""
            if beat == "setup": seq_plots[pid]["has_setup"] = True
            elif beat == "crisis": seq_plots[pid]["has_crisis"] = True
            elif beat == "climax": seq_plots[pid]["has_climax"] = True
            elif beat == "payoff": seq_plots[pid]["has_payoff"] = True
    seq["plots"] = sorted(seq_plots.values(), key=lambda x: (0 if x["plot_scope"] == "main" else 1, x["id"]))
```

## What Old Dashboard Reads (line ~2922-2943)
```javascript
const sceneRows = (seq.scenes_list || []).map((sid, i) => { ... });
const plotRows = (seq.plots || []).map(p => {
    // reads p.id, p.plot_scope, p.plot_type
    // reads p.has_setup, p.has_crisis, p.has_climax, p.has_payoff
});
```

## Implementation

In `get_dashboard_data()`, after all entity dicts are built and `scene.plots` is populated with beat info:

```python
# Build sequence.scenes_list and scene_count
for seq in sequences:
    scenes_in_seq = sorted(
        [s for s in scenes if s.get("parent_id") == seq["id"]],
        key=lambda s: s.get("order", 0)
    )
    seq["scenes_list"] = [s["id"] for s in scenes_in_seq]
    seq["scene_count"] = len(seq["scenes_list"])

# Build sequence.plots (depends on scene.plots with beat info — Task 7)
plot_lookup = {p["id"]: p for p in plots}
for seq in sequences:
    seq_plots = {}
    for scene in scenes:
        if scene.get("parent_id") != seq["id"]:
            continue
        for p in scene.get("plots", []):
            pid = p.get("id") if isinstance(p, dict) else p
            if pid not in seq_plots:
                meta = plot_lookup.get(pid, {})
                seq_plots[pid] = {
                    "id": pid,
                    "has_setup": False, "has_crisis": False,
                    "has_climax": False, "has_payoff": False,
                    "plot_scope": meta.get("plot_scope", "sub"),
                    "plot_type": meta.get("plot_type", ""),
                    "value_arc": meta.get("value_arc", ""),
                }
            beat = p.get("beat", "") if isinstance(p, dict) else ""
            if beat == "setup": seq_plots[pid]["has_setup"] = True
            elif beat == "crisis": seq_plots[pid]["has_crisis"] = True
            elif beat == "climax": seq_plots[pid]["has_climax"] = True
            elif beat == "payoff": seq_plots[pid]["has_payoff"] = True
    seq["plots"] = sorted(seq_plots.values(), key=lambda x: (0 if x["plot_scope"] == "main" else 1, x["id"]))
```

## Files
- `core/db.py` — `get_dashboard_data()` sequence enrichment

## Verification (against old dashboard)
- [ ] Sequence panel (line ~2922): `seq.scenes_list` must be an array of scene IDs
- [ ] Sequence panel (line ~2932): `seq.plots` must have beat info rendered as labels
- [ ] Sequence count badge (line ~2950): `seq.scene_count` must show correct number
- [ ] Sequence plot rows (line ~2940-2943): `p.has_setup`, `p.has_crisis`, `p.has_climax`, `p.has_payoff` must render beat labels

## Verification Results
- [x] `sequence.scenes_list` populated with sorted scene IDs
- [x] `sequence.scene_count` matches len(scenes_list)
- [x] `sequence.plots` has `{id, has_setup, has_crisis, has_climax, has_payoff, plot_scope, plot_type, value_arc}`
- [x] Beat flags correctly derived from scene.plots

Completed: 2026-09-18 — Verified live plugin output.
