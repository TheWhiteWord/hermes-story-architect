# Subtask: Screenplay Format & Storage — CORRECTED

> Decide how the screenplay is stored, parsed, and indexed. Goal: Fountain-compatible, section-targetable, index-friendly.

---

## Key decisions

| # | Decision | Choice | Why |
|---|----------|--------|-----|
| 1 | Fountain parsing | `screenplay-tools` library | Mature (142 commits), handles edge cases (scene numbers, extensions, multi-line dialogue), provides Parser AND Writer for round-trip editing |
| 2 | Frontmatter parsing | `python-frontmatter` | Standard library, proven |
| 3 | Fuzzy name matching | `rapidfuzz` | Standard library, fast |
| 4 | Scene numbering | From screenplay if present, else sequential | Library extracts scene numbers (e.g., `#1a#`); we supplement with sequential for display |
| 5 | Character extraction | From dialogue via `screenplay-tools` Parser | More reliable than regex; handles extensions, parentheticals, multi-line dialogue |
| 6 | Screenplay editing | `screenplay-tools` Writer for round-trip | Parser → modify Script → Writer → Fountain. Preserves formatting. |
| 7 | Treatment/synopsis format | Plain Markdown, no frontmatter | Prose-only, no structure needed |

---

## Dependencies (all three)

```python
rapidfuzz>=3.0
python-frontmatter>=1.0
screenplay-tools>=0.0.10
```

- `screenplay-tools`: Fountain Parser + Writer (round-trip editing, scene/character extraction)
- `python-frontmatter`: YAML frontmatter load/modify/dump
- `rapidfuzz`: Fuzzy name matching (typo tolerance for character name resolution)

---

## Fountain parsing with screenplay-tools

```python
from screenplay_tools.fountain import FountainParser, FountainWriter

def parse_screenplay(content: str) -> list[dict]:
    """Parse screenplay into list of scene dicts using screenplay-tools."""
    parser = FountainParser()
    script = parser.parse(content)
    
    scenes = []
    current_scene = None
    
    for element in script.elements:
        if element.type == "HEADING":
            if current_scene:
                scenes.append(current_scene)
            current_scene = {
                "heading": element.text,
                "scene_number": element.get("scene_number", ""),
                "characters": [],
                "body": "",
            }
        elif element.type == "CHARACTER" and current_scene:
            char_name = element.name
            if char_name not in current_scene["characters"]:
                current_scene["characters"].append(char_name)
        elif current_scene:
            # Accumulate body text
            current_scene["body"] += str(element) + "\n"
    
    if current_scene:
        scenes.append(current_scene)
    
    return scenes

def extract_location(heading: str) -> str:
    """Extract location from scene heading: 'INT. KITCHEN - NIGHT' → 'KITCHEN'."""
    import re
    match = re.match(
        r'^(?:INT\.|EXT\.|EST\.|INT\./EXT\.|I/E\.)\s+(.+?)(?:\s*-\s*(?:DAY|NIGHT|DUSK|DAWN|LATER|CONTINUOUS|MOMENTS LATER))?$',
        heading
    )
    return match.group(1).strip() if match else ""
```

---

## Character extraction from dialogue

`screenplay-tools` gives us character names directly from `CHARACTER` elements:

```python
parser = FountainParser()
script = parser.parse(screenplay_content)

characters = set()
for element in script.elements:
    if element.type == "CHARACTER":
        characters.add(element.name)
```

This handles:
- `DAVE` → DAVE
- `COLIN (O.S.)` → COLIN
- Multi-line dialogue (character only listed once)
- Character extensions ignored for name matching

---

## Index ↔ Screenplay sync

1. Parse `screenplay.md` with `FountainParser`
2. For each scene:
   - Extract heading, scene_number, characters (from CHARACTER elements)
   - Extract location from heading via regex
   - Match location against `locations/` folder slugs (using rapidfuzz for fuzzy match)
   - Match characters against `characters/` folder slugs (using rapidfuzz)
3. Cross-reference with frontmatter `scenes` lists
4. Write `scenes` section of `.story/index.yaml`

---

## Scene numbering

`screenplay-tools` extracts scene numbers if present (`#1a#`). Otherwise, we use sequential numbering for display. Cross-references use scene **headings** (not numbers), so shifting numbers don't break anything.

---

## Screenplay editing (Task 5)

`screenplay-tools` provides round-trip editing:

```python
from screenplay_tools.fountain import FountainParser, FountainWriter

# Parse
parser = FountainParser()
script = parser.parse(screenplay_content)

# Modify (e.g., add scene, replace dialogue)
# ... manipulate script.elements ...

# Write back
writer = FountainWriter()
output = writer.write(script)
```

This preserves Fountain formatting, handles all edge cases, and lets us focus on the action protocol instead of string manipulation.

---

## Treatment and synopsis format

**`synopsis.md`**: Plain Markdown prose. No frontmatter.

**`treatment.md`**: Plain Markdown, one paragraph per beat. No frontmatter.

---

## What this means for other subtasks

- **04_decisions.md**: All screenplay format decisions resolved
- **Task 2 (Index System)**: Uses screenplay-tools for parsing
- **Task 5 (Action Protocol)**: Uses screenplay-tools for round-trip editing

---

## Status: RESOLVED (corrected)

All libraries retained. Ready to proceed to decisions compilation (04).
