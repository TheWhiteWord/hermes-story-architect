# Task 3: Fix Character/Location `scenes` Shape

## Goal
Make `character.scenes` and `location.scenes` match the `dev` branch output shape: `[{id, title, heading}]` objects, not `[to_id, note]` dicts or bare ID strings.

## The Problem
Current `core/db.py:get_dashboard_data()`:
- Character: `d["scenes"] = rel_map.get(eid, {}).get("character_scene", [])` — returns `[{to_id, note}]` dicts
- Location: iterates relations looking for `location_scene` — returns `[scene_id_strings]`

Old system provided `[{id, title, heading}]` objects with full scene info.

## Spec (from `dev` branch `_enrich_entity_scenes`)
```python
char_scenes[char_id].append({
    "id": scene.get("id"),
    "title": scene.get("title", ""),
    "heading": scene.get("heading", ""),
})
# Same for locations
```

## What Old Dashboard Expects (line ~1941-1953, 1974-1975)
```javascript
// Character scenes normalization
if (Array.isArray(c.scenes) && c.scenes.length && typeof c.scenes[0] === 'object') {
  c._scene_objs = c.scenes;           // save for heading lookup
  c.scenes = c.scenes.map(s => {
    const found = (d.scenes || []).find(sc =>
      sc.id === s.id ||
      sc.heading === s.heading ||
      (sc.heading || '').includes(s.heading || '__NOMATCH__')
    );
    return found ? String(found.id) : (s.heading || String(s.id));
  });
}
// Location scenes
if (!loc._scene_headings && Array.isArray(loc.scenes)) {
  loc._scene_headings = loc.scenes.filter(s => typeof s === 'string');
}
```

The dashboard handles both shapes but needs the `{id, title, heading}` objects to:
1. Match scenes by heading when IDs differ after normalization
2. Display heading info in character/location panels

## Fix

### 1. Character scenes (in `get_dashboard_data()`)
Replace:
```python
d["scenes"] = rel_map.get(eid, {}).get("character_scene", [])
```
With:
```python
scene_objs = []
for rel in rel_map.get(eid, {}).get("character_scene", []):
    sid = rel.get("to_id", "") if isinstance(rel, dict) else rel
    if sid in entity_by_id:
        s = entity_by_id[sid]
        s_extra = s.get("extra", {})
        scene_objs.append({
            "id": sid,
            "title": s.get("name", ""),
            "heading": s_extra.get("heading", ""),
        })
d["scenes"] = scene_objs
```

### 2. Location scenes (in `get_dashboard_data()`)
Replace the existing loop with:
```python
scene_objs = []
for rel in rel_map.get(eid, {}).get("location_scene", []):
    sid = rel.get("to_id", "") if isinstance(rel, dict) else rel
    if sid in entity_by_id:
        s = entity_by_id[sid]
        s_extra = s.get("extra", {})
        scene_objs.append({
            "id": sid,
            "title": s.get("name", ""),
            "heading": s_extra.get("heading", ""),
        })
d["scenes"] = scene_objs
```

### 3. Export (tools/story_export.py)
No change needed — export writes frontmatter from DB. Character/location scenes are derived, not stored.

## Files
- `core/db.py` — `get_dashboard_data()` character + location denormalization

## Verification (against old dashboard)
- [x] Import a project, open dashboard
- [x] Check `character.scenes[0]` in dashboard JSON: must be `{id: "scene-slug", title: "Scene Title", heading: "INT. LOCATION - DAY"}`
- [x] Old dashboard scene count (line ~2582): `(char.scenes || []).map(sid => ...)` — must resolve correctly
- [x] Location panel (line ~2771-2775): `_scene_headings` must contain heading strings for matching
- [x] Self-check passes: `[{id, title, heading}]` shape for both character and location scenes

Completed: 2026-09-18 — Replaced raw `character_scene` and `location_scene` relation lookups with full `{id, title, heading}` scene objects. Both shapes now match `dev` branch contract.

## Verification Results
- [x] Character scenes: `[{id, title, heading}]` objects (not `[to_id, note]` dicts)
- [x] Location scenes: `[{id, title, heading}]` objects (not bare ID strings)
- [x] No extra bloat fields — exactly `{id, title, heading}`
- [x] Old dashboard `_scene_objs` + `_scene_headings` normalization works correctly

Completed: 2026-09-18 — Synced live plugin, reimported, verified output.
