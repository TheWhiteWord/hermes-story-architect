# Task 4: Add `scene.arc_beats` (Reverse from Arc Entities)

## Goal
Add `scene.arc_beats[]` to the dashboard output. Currently entirely missing — breaks arc visualization on scene panels.

## Spec (from `dev` branch `_enrich_scenes_with_arcs`)
```python
scene_beats[scene_id].append({
    "character": beat.get("character", ""),
    "beat_id": beat.get("id", ""),
    "label": beat.get("label", ""),
    "y": beat.get("y", 0.0),
    "is_crisis": beat.get("is_crisis", False),
    "is_climax": beat.get("is_climax", False),
})
```

## What Old Dashboard Reads (line ~2272, 3864)
```javascript
const arcBeatDots = (s.arc_beats || []).map(ab => {
    const c = (story.characters || []).find(x => x.id === ab.character || String(x.id) === String(ab.character));
    const label = c ? `${c.name}: ${ab.label || ''}` : '';
    ...
});
const hasBeats = scene.arc_beats && scene.arc_beats.length > 0;
```

Fields: `ab.character`, `ab.beat_id`, `ab.label`, `ab.y`, `ab.is_crisis`, `ab.is_climax`

## Implementation

### In `get_dashboard_data()` — Add `arc_beats` to scene dicts
After building the `arcs` list (and before the arc grouping for characters), build a scene_beats map:

```python
# Build scene.arc_beats from arc entities
scene_beats = {}
for e in ent_rows:
    if e[1] == "arc":
        extra = json.loads(e[8]) if e[8] else {}
        scene_id = extra.get("scene", "")
        if not scene_id:
            continue
        if scene_id not in scene_beats:
            scene_beats[scene_id] = []
        scene_beats[scene_id].append({
            "character": extra.get("character", e[6]) or "",
            "beat_id": e[0],
            "label": e[2] or extra.get("label", ""),
            "y": extra.get("y", 0.0),
            "is_crisis": extra.get("is_crisis", False),
            "is_climax": extra.get("is_climax", False),
        })

# Then in scene denormalization, add:
d["arc_beats"] = scene_beats.get(eid, [])
```

## Files
- `core/db.py` — `get_dashboard_data()` scene denormalization

## Verification (against old dashboard)
- [ ] Open dashboard on a project with arc beats
- [ ] Check `scene.arc_beats` in dashboard JSON: must be array of `{character, beat_id, label, y, is_crisis, is_climax}`
- [ ] Scene panel (line ~3864): `const hasBeats = scene.arc_beats && scene.arc_beats.length > 0;` — must be `true` for scenes with beats
- [ ] Scene arc dots (line ~2272): each beat must render as a dot with `${c.name}: ${ab.label}` tooltip

## Deferred Issues
None.
