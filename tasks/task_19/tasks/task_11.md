# Task 11: Fix Scene Characters Reverse Lookup Performance

## Goal
Fix the O(n) scan over all relations for `scene.characters` in `get_dashboard_data()`. The old system used `scene.characters` directly from frontmatter (O(1)), but the new DB-based system iterates all relations to find characters for each scene.

## The Problem
Current `core/db.py:get_dashboard_data()` scene denormalization (lines 269-279):
```python
char_ids = []
for cid, kinds in rel_map.items():  # iterates ALL entities
    if "character_scene" in kinds:
        for rel in kinds["character_scene"]:
            if isinstance(rel, dict):
                if rel.get("to_id") == eid:
                    char_ids.append(cid)
            elif rel == eid:
                char_ids.append(cid)
d["characters"] = char_ids
```

This iterates over every entity's relations to find characters for one scene. If there are N entities and M relations total, this is O(N*M).

## Fix
Build a reverse lookup once, then use it for all scenes:

```python
# Build reverse lookup: scene_id -> character_ids (from character_scene relations)
scene_chars = {}
for from_id, to_id, kind, note in rel_rows:
    if kind == "character_scene":
        if to_id not in scene_chars:
            scene_chars[to_id] = []
        scene_chars[to_id].append(from_id)

# Then in scene denormalization:
d["characters"] = scene_chars.get(eid, [])
```

Do the same for locations:
```python
scene_locs = {}
for from_id, to_id, kind, note in rel_rows:
    if kind == "location_scene":
        if to_id not in scene_locs:
            scene_locs[to_id] = []
        scene_locs[to_id].append(from_id)

d["locations"] = scene_locs.get(eid, [])
```

## Files
- `core/db.py` — `get_dashboard_data()` relation reverse lookups

## Verification
- [x] Scene characters and locations still populate correctly in dashboard JSON — 60/60 tests pass
- [x] Performance: O(n) scan replaced with single-pass reverse lookup (O(M) total for all scenes)
- [x] Scene panel (line ~2772): `scene.characters` array resolves to correct character list

## Completed
**`core/db.py:208-219`** — Build `scene_chars`, `scene_locs`, `scene_plots` dicts from `rel_rows` in single pass. Replaced O(n) scan in scene denormalization (lines 286-306) with O(1) dict lookups. Also replaced the separate `plots` reverse lookup (which had the same O(n) problem) with `scene_plots`. All three are computed in one loop over `rel_rows`.

## Verification Results (live plugin)
- [x] Scene characters populated: `['kael', 'mira']`
- [x] Scene locations populated: `['the-central-room']`
- [x] Reverse lookup works correctly (not the O(n) scan)

Completed: 2026-09-18 — Verified live plugin output.
