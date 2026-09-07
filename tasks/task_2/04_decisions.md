# Task 2: Index System — FINAL DECISIONS

> All subtasks resolved. This is the authoritative record of decisions made.

---

## Status: RESOLVED

| Subtask | Status |
|---------|--------|
| 01_index_schema.md | RESOLVED |
| 02_index_generator.md | RESOLVED |
| 03_section_parser.md | RESOLVED |
| 04_screenplay_integration.md | RESOLVED |

---

## 1. File Structure

```
src/
├── __init__.py
├── section_parser.py      # list_sections, get_section, replace_section
├── entity_extraction.py   # extract_entity, validate_entity, update_sections
├── screenplay.py          # extract_scenes, match_character, match_location
└── index_generator.py     # generate_index, write_index (orchestrator)
```

**Rationale**: Multiple files because Task 5 (Story Editor) will reuse `section_parser.py`, `entity_extraction.py`, and `screenplay.py` for editing actions.

---

## 2. Index Schema (`.story/index.yaml`)

### Structure

```yaml
project:
  slug: the-water-audit
  name: The Water Audit
  logline: "..."
  genre: Sci-fi thriller
  setting: Near-future city-state
  scene_count: 24
  character_count: 8
  world_count: 2
  plot_count: 3

characters:
  - id: mara
    name: Mara Chen
    role: Protagonist
    one_sentence: "..."
    sections: [Personality, Background, Voice, ...]
    scenes:
      - number: 1
        heading: "INT. MARA'S APARTMENT - NIGHT"
    related:
      - id: detective-oak
        feeling: Wary respect
    goals_short: "..."
    goals_long: "..."
    knowledge: [...]

locations:
  - id: kitchen
    name: The Kitchen
    sections: [Description, History, Scenes]
    scenes:
      - number: 7
        heading: "INT. KITCHEN - NIGHT"

worlds:
  - id: gilead
    name: Gilead
    sections: [Description, History, Conflict]
    rules: [...]

scenes:
  - id: 1
    heading: "INT. MARA'S APARTMENT - NIGHT"
    characters: [mara]
    locations: []
    plots: [brother-investigation]

plots:
  - id: brother-investigation
    name: Brother Investigation
    status: active
    setups:
      - number: 1
        heading: "INT. MARA'S APARTMENT - NIGHT"
    payoffs:
      - number: 22
        heading: "INT. KITCHEN - NIGHT"
    characters: [mara, detective-oak]

story_memory:
  last_updated: ...
  continuity_risks: 2
  headings: [...]
  summary: "..."
```

### Key Design Points

- **Scenes use both `number` AND `heading`** — numbers for display, headings for stable cross-refs
- **Relationships are unidirectional** — each character lists their own, no inference
- **Story Memory is summary-only** — full content in `.story/memory.md`

---

## 3. Dependencies Used

| Library | Used For |
|---------|----------|
| `screenplay-tools` | Fountain Parser (scene extraction, character names from dialogue, scene numbers) |
| `python-frontmatter` | YAML frontmatter load/dump (preserves formatting) |
| `rapidfuzz` | Fuzzy matching (character names, locations) with threshold 85 |
| `PyYAML` | YAML serialization for index output |

---

## 4. Entity Extraction

```python
def extract_entity(note_path: Path, entity_type: str) -> dict:
    post = frontmatter.load(note_path)
    body = post.content
    sections = list_sections(body)
    return {
        "id": note_path.stem,
        **dict(post.metadata),
        "sections": sections,
    }
```

- `python-frontmatter` handles frontmatter/body split
- `sections` auto-generated from `##` headings
- Validation is warn-only (resilient index generation)

---

## 5. Screenplay Integration

### Scene Extraction

```python
from screenplay_tools.fountain import FountainParser

parser = FountainParser()
script = parser.parse(screenplay_content)
# script.elements: HEADING, ACTION, CHARACTER, DIALOGUE, TRANSITION, etc.
```

### Character Matching (rapidfuzz)

```python
from rapidfuzz import fuzz, process

def match_character(name: str, characters: list[dict]) -> str | None:
    # Exact match first, then fuzzy (threshold 85)
    slug_to_name = {c["id"]: c["name"] for c in characters}
    for slug, char_name in slug_to_name.items():
        if name.lower() == char_name.lower():
            return slug
    result = process.extractOne(name, slug_to_name.values(), scorer=fuzz.WRatio)
    if result and result[1] >= 85:
        # reverse lookup name → slug
        ...
    return None
```

### Location Matching

```python
LOCATION_RE = re.compile(
    r'^(?:INT\.|EXT\.|EST\.|INT\./EXT\.|I/E\.)\s+(.+?)(?:\s*-\s*(?:DAY|NIGHT|DUSK|DAWN|LATER|CONTINUOUS|MOMENTS LATER))?$'
)

def match_location(heading_location: str, locations: list[dict]) -> str | None:
    # Same pattern: exact then fuzzy (threshold 85)
    ...
```

---

## 6. Section Parser (zero-dep)

```python
import re

SECTION_RE = re.compile(r'^##\s+(.+)$', re.MULTILINE)

def list_sections(body: str) -> list[str]:
    return SECTION_RE.findall(body)

def get_section(body: str, section: str) -> str:
    # Split by heading, return matching section
    ...

def replace_section(body: str, section: str, new_body: str) -> str:
    # Split by heading, replace matching section
    ...
```

---

## 7. Update Strategy

**Full regeneration** — always re-scan entire project. For now, projects are small. Partial update can be added later if needed.

---

## What happens next

1. Implement the 4 Python modules
2. Create a test project in the vault
3. Run the index generator against the test project
4. Verify output matches schema
5. Proceed to **Task 3 (Story Loader Skill)**
