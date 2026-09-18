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
- [ ] Open dashboard
- [ ] Check `story_data.project` in dashboard JSON: must have all count fields
- [ ] Stats row (line ~2437-2443): each count must display correctly (not fall back to array lengths)

## Deferred Issues
- `act_count`: declared count is not stored in DB. The old system read `project.act_count` from frontmatter (the `act_count` field in `project.md`). Need to either import `act_count` into extra or derive from entity count. Currently deriving from entity count only — if user declares 3 acts but only 2 files exist, old showed 3. **Deferred: import `act_count` from project frontmatter.**
