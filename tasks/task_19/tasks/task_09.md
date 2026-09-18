# Task 9: Fix `structural_stats.plotCoverage`

## Goal
Implement the plot coverage calculation that was hardcoded to `[]`. Currently the plot coverage chart in the dashboard is permanently empty.

## Spec (from `dev` branch `compute_structural_stats`)
```python
# Plot coverage: count unique scenes per plot (not beat entries)
plot_scene_sets = {}
for scene in scenes:
    for p in scene.get("plots", []):
        pid = p.get("id") if isinstance(p, dict) else p
        if pid not in plot_scene_sets:
            plot_scene_sets[pid] = set()
        plot_scene_sets[pid].add(scene.get("id"))

plots_lookup = {p["id"]: p for p in plots}
total_scenes = len(scenes)
plot_coverage = []
for pid, scene_set in sorted(plot_scene_sets.items(), key=lambda x: len(x[1]), reverse=True):
    pl = plots_lookup.get(pid, {})
    plot_coverage.append({
        "id": pid,
        "name": pl.get("name", pid),
        "plot_scope": pl.get("plot_scope", "sub"),
        "plot_type": pl.get("plot_type", ""),
        "value_arc": pl.get("value_arc", ""),
        "sceneCount": len(scene_set),
        "coveragePct": round((len(scene_set) / total_scenes) * 100) if total_scenes else 0,
    })
```

## What Old Dashboard Reads (line ~3425)
```javascript
const coverage = ss.plotCoverage || [];
```

Fields: `id`, `name`, `plot_scope`, `plot_type`, `value_arc`, `sceneCount`, `coveragePct`

## Implementation

In `get_dashboard_data()`, replace:
```python
"plotCoverage": [],
```

With:
```python
# Plot coverage: count unique scenes per plot
plot_scene_sets = {}
for scene in scenes:
    for p in scene.get("plots", []):
        pid = p.get("id") if isinstance(p, dict) else p
        if pid not in plot_scene_sets:
            plot_scene_sets[pid] = set()
        plot_scene_sets[pid].add(scene["id"])

total_scenes = len(scenes)
plot_coverage = []
for pid, scene_set in sorted(plot_scene_sets.items(), key=lambda x: len(x[1]), reverse=True):
    pl = plot_lookup.get(pid, {})
    plot_coverage.append({
        "id": pid,
        "name": pl.get("name", pid),
        "plot_scope": pl.get("plot_scope", "sub"),
        "plot_type": pl.get("plot_type", ""),
        "value_arc": pl.get("value_arc", ""),
        "sceneCount": len(scene_set),
        "coveragePct": round((len(scene_set) / total_scenes) * 100) if total_scenes else 0,
    })
```

Then:
```python
structural_stats = {
    ...
    "plotCoverage": plot_coverage,
    ...
}
```

## Files
- `core/db.py` — `get_dashboard_data()` structural_stats

## Verification (against old dashboard)
- [ ] Plot coverage chart (line ~3425): `ss.plotCoverage || []` must not be empty when plots exist
- [ ] Each coverage entry must have: `id`, `name`, `plot_scope`, `plot_type`, `value_arc`, `sceneCount`, `coveragePct`

## Deferred Issues
None.
