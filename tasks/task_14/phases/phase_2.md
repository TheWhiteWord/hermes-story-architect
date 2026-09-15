# Phase 2: Index Derivation — Parse Arcs & Enrich Characters/Scenes

## Prerequisite

Phase 1 must be complete. This phase assumes `ENTITY_SCHEMAS["arc"]` exists and `_parse_entities("arc", ...)` can validate arc beats.

## Files to modify

| File | Change |
|------|--------|
| `core/index.py` | Add `_parse_arcs()` — recursive glob for `arcs/{character}/{beat_id}.md` |
| `core/index.py` | Add `index["arcs"]` to `generate_index()` output |
| `core/index.py` | Add `_enrich_characters_with_arcs(index)` — builds `arc_beats_list` and `arc_beat_count` |
| `core/index.py` | Add `_enrich_scenes_with_arcs(index)` — builds `scene["arc_beats"]` |
| `core/index.py` | Add arc validation to `_validate_index()` — character/scene exists, y range, order numeric |
| `core/index.py` | Add `arc_count` to `_parse_project()` |

## Step-by-step

### Step 2.1 — Add `_parse_arcs()` function

```python
def _parse_arcs(arcs_folder: Path) -> list[dict]:
    """Parse arc beats from nested arcs/{character}/{beat_id}.md structure."""
    if not arcs_folder.exists():
        return []
    beats = []
    for char_folder in sorted(arcs_folder.iterdir()):
        if not char_folder.is_dir() or char_folder.name.startswith("_") or char_folder.name.startswith("."):
            continue
        for note in sorted(char_folder.glob("*.md")):
            if note.name.startswith("_"):
                continue
            beat = extract_entity(note, "arc")
            # Inherit character from folder name if not in frontmatter
            if "character" not in beat or not beat["character"]:
                beat["character"] = char_folder.name
            warnings = validate_entity("arc", beat)
            if warnings:
                print(f"Warnings for {note}: {warnings}")
            beats.append(beat)
    return beats
```

### Step 2.2 — Wire arcs into `generate_index()`

Add after line 15 (`acts = _parse_entities(...)`):
```python
arcs = _parse_arcs(project_path / "arcs")
```

Add to index dict (after `"scenes"` key, around line 30):
```python
index["arcs"] = arcs
```

Add after existing enrichment calls (around line 49):
```python
# Enrich characters with arc beats
_enrich_characters_with_arcs(index)

# Enrich scenes with arc beats (reverse lookup)
_enrich_scenes_with_arcs(index)
```

### Step 2.3 — Add `_enrich_characters_with_arcs()`

```python
def _enrich_characters_with_arcs(index: dict) -> None:
    """Build character.arc_beats_list and set arc_beat_count."""
    char_beats = {c["id"]: [] for c in index["characters"]}
    for beat in index.get("arcs", []):
        char_id = beat.get("character")
        if char_id in char_beats:
            char_beats[char_id].append({
                "id": beat.get("id", ""),
                "label": beat.get("label", ""),
                "scene": beat.get("scene", ""),
                "y": beat.get("y", 0.0),
                "order": beat.get("order", 0),
                "is_crisis": beat.get("is_crisis", False),
                "is_climax": beat.get("is_climax", False),
            })
    for char in index["characters"]:
        beats = char_beats.get(char["id"], [])
        if beats:
            char["arc_beats_list"] = sorted(beats, key=lambda b: b.get("order", 0))
            char["arc_beat_count"] = len(beats)
        else:
            char["arc_beats_list"] = []
            char["arc_beat_count"] = 0
```

### Step 2.4 — Add `_enrich_scenes_with_arcs()`

```python
def _enrich_scenes_with_arcs(index: dict) -> None:
    """Build scene.arc_beats[] by reverse lookup from beats."""
    scene_beats = {s.get("id"): [] for s in index.get("scenes", [])}
    for beat in index.get("arcs", []):
        scene_id = beat.get("scene")
        if scene_id in scene_beats:
            scene_beats[scene_id].append({
                "character": beat.get("character", ""),
                "beat_id": beat.get("id", ""),
                "label": beat.get("label", ""),
                "y": beat.get("y", 0.0),
                "is_crisis": beat.get("is_crisis", False),
                "is_climax": beat.get("is_climax", False),
            })
    for scene in index.get("scenes", []):
        beats = scene_beats.get(scene.get("id"), [])
        if beats:
            scene["arc_beats"] = beats
```

### Step 2.5 — Add arc validation to `_validate_index()`

Add at the end (before closing `}`):
```python
# Arc beat validation
char_ids_set = {c["id"] for c in index["characters"]}
scene_ids_set = {s.get("id") for s in index.get("scenes", [])}
for beat in index.get("arcs", []):
    beat_char = beat.get("character", "")
    if beat_char and beat_char not in char_ids_set:
        print(f"Warning: arc beat {beat.get('id')} references unknown character {beat_char}")
    beat_scene = beat.get("scene", "")
    if beat_scene and beat_scene not in scene_ids_set:
        print(f"Warning: arc beat {beat.get('id')} references unknown scene {beat_scene}")
    y_val = beat.get("y", 0)
    if isinstance(y_val, (int, float)) and not (-1.0 <= float(y_val) <= 1.0):
        print(f"Warning: arc beat {beat.get('id')} y out of range: {y_val}")
    order_val = beat.get("order", 0)
    if not isinstance(order_val, (int, float)):
        print(f"Warning: arc beat {beat.get('id')} order is not numeric: {order_val}")
```

### Step 2.6 — Add `arc_count` to `_parse_project()`

Add to `_parse_project` signature:
```python
def _parse_project(..., arcs_count=0):
```

Add inside:
```python
project["arc_count"] = arcs_count
```

Update call site:
```python
"project": _parse_project(
    ..., arcs_count=len(arcs)
),
```

## Legacy cleanup

None — this is additive.

## Naming convention check

- `_parse_arcs` (follows `_parse_entities` pattern)
- `arc_beats_list` (follows `scenes_list` pattern — lightweight dicts)
- `arc_beats` (follows `plots` pattern on scene — reverse lookup list)
- `arc_count` (follows `scene_count` pattern on project)
- `arc_beat_count` (follows `scene_count` pattern on character)

## Final checklist (unmarked)

- [ ] `_parse_arcs()` handles nested `arcs/{character}/{beat_id}.md` structure
- [ ] `_parse_arcs()` skips hidden files/folders (leading `_` or `.`)
- [ ] `_parse_arcs()` inherits character from folder name if missing in frontmatter
- [ ] `generate_index()` includes `arcs` key in returned index
- [ ] `_enrich_characters_with_arcs()` populates `arc_beats_list` sorted by order
- [ ] `_enrich_characters_with_arcs()` sets `arc_beat_count`
- [ ] `_enrich_characters_with_arcs()` handles characters with no beats (empty list, count 0)
- [ ] `_enrich_scenes_with_arcs()` populates `scene["arc_beats"]`
- [ ] `_validate_index()` warns on unknown character slug in beat
- [ ] `_validate_index()` warns on unknown scene slug in beat
- [ ] `_validate_index()` warns on y out of range
- [ ] `_validate_index()` warns on non-numeric order
- [ ] `arc_count` added to project metadata
- [ ] Tests added to `test_arcs.py` for index derivation
- [ ] Tests added to `test_arcs.py` for validation warnings
- [ ] `pytest tests/test_arcs.py` passes
- [ ] Existing `test_core.py` tests still pass
