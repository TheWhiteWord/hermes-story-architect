# Task 8: Add Project Count Fields

## Goal
Add the missing count fields to the project entity in dashboard data: `scene_count`, `character_count`, `location_count`, `world_count`, `plot_count`, `sequence_count`, `act_count`.

## Spec (from `dev` branch `_parse_project`)
```python
project["scene_count"] = scenes_count
project["character_count"] = len(characters)
project["location_count"] = len(locations)
project["world_count"] = len(worlds)
project["plot_count"] = len(plots)
project["sequence_count"] = sequences_count
project["act_count"] = max(declared, acts_count)
project["arc_count"] = arcs_count
```

## What Old Dashboard Reads (line ~2437-2443)
```javascript
{ v: p.scene_count     || (story.scenes     || []).length, l: 'Scenes' },
{ v: p.character_count || (story.characters || []).length, l: 'Characters' },
{ v: p.location_count  || (story.locations  || []).length || null, l: 'Locations' },
{ v: p.world_count     || (story.worlds     || []).length || null, l: 'Worlds' },
{ v: p.plot_count      || (story.plots      || []).length || null, l: 'Plots' },
{ v: p.sequence_count  || (story.sequences  || []).length, l: 'Sequences' },
{ v: p.act_count       || (story.acts       || []).length, l: 'Acts' },
```

## Implementation

In `get_dashboard_data()`, after building all entity dicts and before `story_data` dict is created:

```python
# Project counts
project_counts = {
    "scene_count": len(scenes),
    "character_count": len(characters),
    "location_count": len(locations),
    "world_count": len(worlds),
    "plot_count": len(plots),
    "sequence_count": len(sequences),
    "act_count": max(
        next((a.get("act_count", 0) for a in acts), 0),  # declared (not stored in DB)
        len(acts)
    ),
    "arc_count": len(story_arcs),
}
proj_dict.update(project_counts)
```

## Files
- `core/db.py` — `get_dashboard_data()` project counts

## Verification (against old dashboard)
- [x] Added all 8 count fields to `proj_dict` before `story_data` is created
- [x] Lint passes (no errors)

Completed: 2026-09-19 — All 8 project counts (`scene_count`, `character_count`, `location_count`, `world_count`, `plot_count`, `sequence_count`, `act_count`, `arc_count`) added to `get_dashboard_data()` in `core/db.py:557-566`. Direct `len()` of already-built entity arrays — single source of truth, no extra DB queries needed.

## Verification Results
- [x] All 8 project count fields present: scene_count, character_count, location_count, world_count, plot_count, sequence_count, act_count, arc_count
- [x] Values match entity counts (scene=4, char=6, loc=2, world=2, plot=2, seq=2, arc=6)

Completed: 2026-09-18 — Verified live plugin output.
- `act_count`: declared count is not stored in DB. The old system read `project.act_count` from frontmatter (the `act_count` field in `project.md`). Need to either import `act_count` into extra or derive from entity count. Currently deriving from entity count only — if user declares 3 acts but only 2 files exist, old showed 3. **Deferred: import `act_count` from project frontmatter.**
