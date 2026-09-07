# Subtask: Screenplay Integration — RESOLVED

> Integrate `screenplay-tools` for Fountain parsing and scene extraction. References: `task_1/04_decisions.md §7` (screenplay format), `task_2/01_index_schema.md` (scene representation).

---

## Decisions

| # | Decision | Choice | Why |
|---|----------|--------|-----|
| 1 | screenplay-tools API | Direct import | Library API is simple (Parser/Writer), no wrapper needed |
| 2 | Character name matching | Exact + fuzzy (rapidfuzz) | Handles aliases, extensions, typos |
| 3 | Similarity threshold | 85 (configurable) | Middle ground — catches variants, avoids false matches |
| 4 | Location matching | Fuzzy (rapidfuzz) | Headings use informal names ("KITCHEN") vs slugs ("kitchen") |
| 5 | Scene numbering | Hybrid | Sequential `id` for display, screenplay-tools `scene_number` as metadata |

---

## Implementation

### Scene Extraction (screenplay-tools)

```python
from screenplay_tools.fountain import FountainParser
from pathlib import Path
import re

LOCATION_RE = re.compile(
    r'^(?:INT\.|EXT\.|EST\.|INT\./EXT\.|I/E\.)\s+(.+?)(?:\s*-\s*(?:DAY|NIGHT|DUSK|DAWN|LATER|CONTINUOUS|MOMENTS LATER))?$'
)

def extract_scenes(screenplay_path: Path) -> list[dict]:
    """Extract scenes from screenplay.md using screenplay-tools."""
    parser = FountainParser()
    script = parser.load(screenplay_path.read_text()) if hasattr(parser, 'load') else parser.parse(screenplay_path.read_text())
    
    scenes = []
    current_scene = None
    
    for element in script.elements:
        if element.type == "HEADING":
            if current_scene:
                scenes.append(current_scene)
            current_scene = {
                "heading": element.text,
                "scene_number": getattr(element, "scene_number", ""),
                "characters": [],
                "location": extract_location(element.text),
            }
        elif element.type == "CHARACTER" and current_scene:
            name = element.name if hasattr(element, 'name') else element.get("name", "")
            if name and name not in current_scene["characters"]:
                current_scene["characters"].append(name)
    
    if current_scene:
        scenes.append(current_scene)
    
    # Assign sequential numbers
    for i, scene in enumerate(scenes, 1):
        scene["id"] = i
    
    return scenes

def extract_location(heading: str) -> str | None:
    """Extract location from scene heading: 'INT. KITCHEN - NIGHT' → 'KITCHEN'."""
    match = LOCATION_RE.match(heading)
    return match.group(1).strip() if match else None
```

### Character Name Matching (rapidfuzz)

```python
from rapidfuzz import fuzz, process

def match_character(name: str, characters: list[dict]) -> str | None:
    """Match dialogue character name to character slug. Returns slug or None."""
    # Build lookup: slug → name
    slug_to_name = {c["id"]: c["name"] for c in characters}
    names = list(slug_to_name.values())
    
    # Exact match (case-insensitive)
    for slug, char_name in slug_to_name.items():
        if name.lower() == char_name.lower():
            return slug
    
    # Fuzzy match against character names
    result = process.extractOne(name, names, scorer=fuzz.WRatio)
    if result and result[1] >= 85:
        matched_name = result[0]
        # Reverse lookup: name → slug
        for slug, char_name in slug_to_name.items():
            if char_name == matched_name:
                return slug
    
    return None
```

### Location Matching (rapidfuzz)

```python
def match_location(heading_location: str, locations: list[dict]) -> str | None:
    """Match extracted location to location slug. Returns slug or None."""
    if not heading_location:
        return None
    
    slug_to_name = {l["id"]: l["name"] for l in locations}
    names = list(slug_to_name.values())
    
    # Exact match
    for slug, loc_name in slug_to_name.items():
        if heading_location.lower() == loc_name.lower():
            return slug
    
    # Fuzzy match
    result = process.extractOne(heading_location, names, scorer=fuzz.WRatio)
    if result and result[1] >= 85:
        matched_name = result[0]
        for slug, loc_name in slug_to_name.items():
            if loc_name == matched_name:
                return slug
    
    return None
```

### Full Screenplay Sync

```python
def sync_screenplay(screenplay_path: Path, characters: list[dict], locations: list[dict]) -> list[dict]:
    """Sync screenplay with character/location data."""
    scenes = extract_scenes(screenplay_path)
    
    for scene in scenes:
        # Match characters
        matched_chars = []
        for char_name in scene["characters"]:
            slug = match_character(char_name, characters)
            if slug and slug not in matched_chars:
                matched_chars.append(slug)
        scene["characters"] = matched_chars
        
        # Match location
        if scene["location"]:
            slug = match_location(scene["location"], locations)
            if slug:
                scene["locations"] = [slug]
            else:
                scene["locations"] = []
    
    return scenes
```

---

## Key Design Points

### 1. screenplay-tools gives us scene numbers AND headings

We store both: `id` (sequential, for display) and `scene_number` (from `#1a#` syntax, for reference). Cross-references use headings.

### 2. rapidfuzz handles all fuzzy matching

Characters: dialogue name → character name → character slug
Locations: heading location → location name → location slug

Threshold: 85 (configurable constant).

### 3. Extensions ignored for matching

`COLIN (O.S.)` → `COLIN` → matched to "Colin Smith" slug.

### 4. No wrapper class

Direct import: `from screenplay_tools.fountain import FountainParser`. The library API is already minimal.

---

## What this means for other subtasks

- **02_index_generator.md**: Has all components ready — entity extraction, section parser, screenplay sync

---

## Status: RESOLVED
