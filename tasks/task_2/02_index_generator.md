# Subtask: Index Generator Script — RESOLVED

> Build the Python script that reads vault notes → produces `.story/index.yaml`. References: `task_2/01_index_schema.md` (structure), `03_section_parser.md` (parsing), `04_screenplay_integration.md` (screenplay).

---

## File structure decision

**Multiple files** — the section parser, entity extraction, and screenplay integration will be reused by Task 5 (Story Editor) for `edit_note` and `edit_screenplay` actions.

```
src/
├── __init__.py
├── section_parser.py      # list_sections, get_section, replace_section
├── entity_extraction.py   # extract_entity, validate_entity, update_sections
├── screenplay.py          # extract_scenes, match_character, match_location
└── index_generator.py     # generate_index, write_index (orchestrator)
```

---

## section_parser.py

```python
import re

SECTION_RE = re.compile(r'^##\s+(.+)$', re.MULTILINE)

def list_sections(body: str) -> list[str]:
    """Extract ## headings from note body."""
    return SECTION_RE.findall(body)

def get_section(body: str, section: str) -> str:
    """Get a single section by name."""
    parts = SECTION_RE.split(body)
    for i in range(1, len(parts), 2):
        heading = parts[i].strip().lstrip('#').strip()
        body_text = parts[i + 1].strip() if i + 1 < len(parts) else ""
        if heading.lower() == section.lower():
            return f"## {heading}\n{body_text}"
    return ""

def replace_section(body: str, section: str, new_body: str) -> str:
    """Replace a section's body."""
    parts = SECTION_RE.split(body)
    for i in range(1, len(parts), 2):
        heading = parts[i].strip().lstrip('#').strip()
        if heading.lower() == section.lower():
            parts[i + 1] = '\n\n' + new_body
            return ''.join(parts)
    return content
```

---

## entity_extraction.py

```python
import frontmatter
from pathlib import Path
from .section_parser import list_sections

REQUIRED_FIELDS = {
    "character": ["name", "story_role", "one_sentence"],
    "location": ["name", "one_sentence"],
    "world": ["name", "one_sentence"],
    "plot": ["name", "status"],
    "project": ["name", "logline"],
}

VALID_ROLES = ["Protagonist", "Antagonist", "Supporting", "Minor", "Cameo"]
VALID_STATUSES = ["active", "resolved", "abandoned"]

def extract_entity(note_path: Path, entity_type: str) -> dict:
    """Extract entity data from a note file."""
    post = frontmatter.load(note_path)
    body = post.content
    sections = list_sections(body)
    return {
        "id": note_path.stem,
        **dict(post.metadata),
        "sections": sections,
    }

def validate_entity(entity_type: str, frontmatter: dict) -> list[str]:
    """Validate entity frontmatter. Return list of warnings."""
    warnings = []
    for field in REQUIRED_FIELDS.get(entity_type, []):
        if field not in frontmatter:
            warnings.append(f"Missing required field: {field}")
    if entity_type == "character" and "story_role" in frontmatter:
        if frontmatter["story_role"] not in VALID_ROLES:
            warnings.append(f"Invalid story_role: {frontmatter['story_role']}")
    if entity_type == "plot" and "status" in frontmatter:
        if frontmatter["status"] not in VALID_STATUSES:
            warnings.append(f"Invalid status: {frontmatter['status']}")
    return warnings

def update_sections(note_path: Path, sections: list[str]) -> None:
    """Update the sections field in a note's frontmatter."""
    post = frontmatter.load(note_path)
    post["sections"] = sections
    frontmatter.dump(note_path, post)
```

---

## screenplay.py

```python
from screenplay_tools.fountain import FountainParser
from rapidfuzz import fuzz, process
import re

LOCATION_RE = re.compile(
    r'^(?:INT\.|EXT\.|EST\.|INT\./EXT\.|I/E\.)\s+(.+?)(?:\s*-\s*(?:DAY|NIGHT|DUSK|DAWN|LATER|CONTINUOUS|MOMENTS LATER))?$'
)

def extract_scenes(screenplay_content: str) -> list[dict]:
    """Extract scenes from screenplay content using screenplay-tools."""
    parser = FountainParser()
    script = parser.parse(screenplay_content)
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
    for i, scene in enumerate(scenes, 1):
        scene["id"] = i
    return scenes

def extract_location(heading: str) -> str | None:
    """Extract location from scene heading."""
    match = LOCATION_RE.match(heading)
    return match.group(1).strip() if match else None

def match_character(name: str, characters: list[dict]) -> str | None:
    """Match dialogue character name to character slug."""
    slug_to_name = {c["id"]: c["name"] for c in characters}
    for slug, char_name in slug_to_name.items():
        if name.lower() == char_name.lower():
            return slug
    result = process.extractOne(name, slug_to_name.values(), scorer=fuzz.WRatio)
    if result and result[1] >= 85:
        for slug, char_name in slug_to_name.items():
            if char_name == result[0]:
                return slug
    return None

def match_location(heading_location: str, locations: list[dict]) -> str | None:
    """Match extracted location to location slug."""
    if not heading_location:
        return None
    slug_to_name = {l["id"]: l["name"] for l in locations}
    for slug, loc_name in slug_to_name.items():
        if heading_location.lower() == loc_name.lower():
            return slug
    result = process.extractOne(heading_location, slug_to_name.values(), scorer=fuzz.WRatio)
    if result and result[1] >= 85:
        for slug, loc_name in slug_to_name.items():
            if loc_name == result[0]:
                return slug
    return None
```

---

## index_generator.py

```python
import yaml
from pathlib import Path
from .entity_extraction import extract_entity, validate_entity, update_sections
from .screenplay import extract_scenes, match_character, match_location

def generate_index(project_path: Path) -> dict:
    """Main entry point: scan project folder, produce index dict."""
    index = {
        "project": _parse_project(project_path),
        "characters": _parse_entities(project_path / "characters", "character"),
        "locations": _parse_entities(project_path / "locations", "location"),
        "worlds": _parse_entities(project_path / "worlds", "world"),
        "plots": _parse_entities(project_path / "plots", "plot"),
    }
    
    # Sync screenplay
    screenplay_path = project_path / "screenplay.md"
    if screenplay_path.exists():
        scenes = extract_scenes(screenplay_path.read_text())
        for scene in scenes:
            scene["characters"] = [
                slug for char in scene["characters"]
                if (slug := match_character(char, index["characters"]))
            ]
            if scene["location"]:
                matched = match_location(scene["location"], index["locations"])
                scene["locations"] = [matched] if matched else []
            del scene["location"]
        index["scenes"] = scenes
    
    # Build cross-references (character scenes from screenplay)
    _enrich_from_screenplay(index)
    
    # Validate
    _validate_index(index)
    
    return index

def _parse_project(project_path: Path) -> dict:
    """Parse project.md."""
    fm = project_path / "project.md"
    return extract_entity(fm, "project") if fm.exists() else {}

def _parse_entities(folder: Path, entity_type: str) -> list[dict]:
    """Parse all entities in a folder."""
    if not folder.exists():
        return []
    entities = []
    for note in sorted(folder.glob("*.md")):
        if note.name.startswith("_"):
            continue
        entity = extract_entity(note, entity_type)
        warnings = validate_entity(entity_type, entity)
        if warnings:
            print(f"Warnings for {note}: {warnings}")
        entities.append(entity)
    return entities

def _enrich_from_screenplay(index: dict) -> None:
    """Update character scenes from screenplay data."""
    char_scenes = {c["id"]: [] for c in index["characters"]}
    for scene in index.get("scenes", []):
        for char_id in scene["characters"]:
            if char_id in char_scenes:
                char_scenes[char_id].append({
                    "number": scene["id"],
                    "heading": scene["heading"],
                })
    for char in index["characters"]:
        if char_scenes.get(char["id"]):
            char["scenes"] = char_scenes[char["id"]]

def _validate_index(index: dict) -> None:
    """Validate cross-references."""
    char_ids = {c["id"] for c in index["characters"]}
    loc_ids = {l["id"] for l in index["locations"]}
    plot_ids = {p["id"] for p in index["plots"]}
    
    for char in index["characters"]:
        for rel in char.get("related", []):
            if rel["id"] not in char_ids:
                print(f"Warning: {char['id']} references unknown character {rel['id']}")
    
    for plot in index["plots"]:
        for char_id in plot.get("characters", []):
            if char_id not in char_ids:
                print(f"Warning: {plot['id']} references unknown character {char_id}")

def write_index(index: dict, output_path: Path) -> None:
    """Write index to YAML."""
    with open(output_path, 'w') as f:
        yaml.dump(index, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
```

---

## Status: RESOLVED

All components designed. Ready for Task 2 implementation (or to proceed to decisions compilation).
