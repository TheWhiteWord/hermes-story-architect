# Subtask: Section Parser & Entity Extraction — RESOLVED

> Build the section parser for `##` headings and the entity extraction logic. References: `task_1/04_decisions.md §8` (standard sections), `§5` (entity schemas).

---

## Decisions

| # | Decision | Choice | Why |
|---|----------|--------|-----|
| 1 | Section parser location | Inline in index generator | YAGNI — no separate module until reused |
| 2 | Entity extraction | Function, not class | Simple data extraction, no state |
| 3 | Frontmatter update | `python-frontmatter` dumps | Library handles formatting, atomic write unnecessary (single-user) |
| 4 | Validation strictness | Warn, don't fail | Index generator should be resilient |

---

## Implementation

### Section Parser (regex, zero-dep)

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
    return body
```

### Entity Extraction (using python-frontmatter)

```python
import frontmatter
from pathlib import Path

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
    
    # Get frontmatter
    fm = dict(post.metadata)
    
    # Get body (python-frontmatter handles the split)
    body = post.content
    
    # Extract sections from body
    sections = list_sections(body)
    
    # Build entity dict
    entity = {
        "id": note_path.stem,
        **fm,
        "sections": sections,
    }
    
    return entity

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
```

### Frontmatter Update (using python-frontmatter)

```python
def update_sections(note_path: Path, sections: list[str]) -> None:
    """Update the sections field in a note's frontmatter."""
    post = frontmatter.load(note_path)
    post["sections"] = sections
    frontmatter.dump(note_path, post)
```

---

## Key Design Points

### 1. python-frontmatter handles frontmatter/body split

No need for manual YAML delimiter parsing. `frontmatter.load()` returns:
- `post.metadata` → dict of frontmatter
- `post.content` → body string

### 2. Section parser is regex-only

`##` headings are simple enough for regex. No Markdown library needed.

### 3. Validation is warn-only

The index generator logs warnings but continues. Broken notes don't crash the index.

### 4. No separate module

For a plugin this size, inline functions in the index generator are cleaner. Extract to a module only when reused.

---

## What this means for other subtasks

- **02_index_generator.md**: Has entity extraction and section parser ready to use
- **04_screenplay_integration.md**: Independent — no dependency on this subtask

---

## Status: RESOLVED
