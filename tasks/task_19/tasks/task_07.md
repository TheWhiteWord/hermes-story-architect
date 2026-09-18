# Task 7: Fix `scene.plots` — Include Beat Info

## Goal
Change `scene.plots` from `[plot_id_strings]` to `[{id, beat}]` objects. Currently beat info is lost — scene panel shows plots without labels like "SETUP", "CRISIS", etc.

## The Problem
Current `core/db.py:get_dashboard_data()` scene denormalization (line ~291-302) collects bare plot IDs into `plot_ids` list. The old system included beat type with each reference.

## Spec (from `dev` branch `_enrich_scenes_with_plots`)
```python
# For each plot beat (setup/crisis/climax/payoff):
scene["plots"].append({"id": plot["id"], "beat": beat_type})
```

Where `beat_type` is one of: `"setup"`, `"crisis"`, `"climax"`, `"payoff"`.

## What Old Dashboard Reads (line ~2681-2700)
```javascript
const plotRefs = (scene.plots || []);
const plots = plotRefs.map(pref => {
    const pid = (typeof pref === 'object' && pref !== null) ? pref.id : pref;
    const beat = (typeof pref === 'object' && pref !== null) ? (pref.beat || '') : '';
    const pl = (story.plots || []).find(x => x.id === pid || String(x.id) === String(pid));
    if (!pl) return '';
    const beatLabel = beat ? ` · ${beat.toUpperCase()}` : '';
    // ... renders " · SETUP", " · CRISIS", etc.
});
```

## Fix

In `get_dashboard_data()` scene denormalization, replace the plot_ids collection:

```python
# plots from plot_setup/plot_payoff/plot_crisis/plot_climax relations (reverse lookup)
plot_beats = []  # (plot_id, beat_type)
for pid, kinds in rel_map.items():
    for kind in ("plot_setup", "plot_crisis", "plot_climax", "plot_payoff"):
        if kind in kinds:
            for rel in kinds[kind]:
                if isinstance(rel, dict):
                    if rel.get("to_id") == eid:
                        beat_type = kind.replace("plot_", "")  # setup/crisis/climax/payoff
                        plot_beats.append({"id": pid, "beat": beat_type})
                elif rel == eid:
                    beat_type = kind.replace("plot_", "")
                    plot_beats.append({"id": pid, "beat": beat_type})
d["plots"] = plot_beats
```

## Files
- `core/db.py` — `get_dashboard_data()` scene denormalization

## Verification (against old dashboard)
- [ ] Scene panel (line ~2681): `scene.plots` must be array of `{id, beat}` objects
- [ ] Scene panel plot buttons: must show beat labels (" · SETUP", " · CRISIS", etc.)
- [ ] Sequence/act plots (Task 5/6): aggregating from `scene.plots` with beat info must correctly set `has_setup`/`has_crisis`/`has_climax`/`has_payoff` flags

## Completed
- **`core/db.py:307-318`** — Changed scene plots from `[plot_id_strings]` to `[{id, beat}]` objects. Added `plot_crisis` and `plot_climax` to the relation kinds (was only setup/payoff). Dashboard now renders beat labels (SETUP, CRISIS, CLIMAX, PAYOFF) on scene plot buttons. Sequence/act plot aggregations (Tasks 5/6) now correctly set `has_*` flags.

## Verification Results
- [x] `scene.plots` is `[{id, beat}]` — no extra fields
- [x] Beat types correct: setup, crisis, climax, payoff
- [x] Multiple beats per plot on same scene handled (e.g., crisis + climax both listed)

Completed: 2026-09-18 — Verified live plugin output.
