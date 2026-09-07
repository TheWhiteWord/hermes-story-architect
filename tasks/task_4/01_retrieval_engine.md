# Subtask: Retrieval Engine Design — RESOLVED

> Design the retrieval loop that loads only the needed `##` sections. References: `task_1/04_decisions.md` (frontmatter→body mapping), `task_2/04_decisions.md` (section parser, index schema).

---

## Decisions

| # | Decision | Choice | Why |
|---|----------|--------|-----|
| 1 | Tool schema | Entity type + slug + section(s) | Semantic — matches how the LLM thinks about entities |
| 2 | Multiple sections | List of sections + `"all"` | Reduces tool calls for multi-section queries |
| 3 | Error handling | Missing section → return available sections | Helps LLM recover from wrong section names |
| 4 | Integration | Direct tool call | No separate skill needed — retrieval is simple |

---

## Tool Schema

```python
{
    "name": "story_retrieve",
    "description": "Retrieve specific sections from a story project note. Loads only the requested sections, not the full note.",
    "parameters": {
        "type": "object",
        "properties": {
            "entity_type": {
                "type": "string",
                "enum": ["character", "location", "world", "plot", "project"],
                "description": "Type of entity to retrieve from"
            },
            "slug": {
                "type": "string",
                "description": "Entity slug (e.g., 'mara', 'kitchen')"
            },
            "sections": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Section names to retrieve (e.g., ['Personality', 'Voice']). Use ['all'] for all sections."
            }
        },
        "required": ["entity_type", "slug", "sections"]
    }
}
```

---

## Retrieval Flow

```
User: "What's Mara's voice like?"

1. LLM reads index (already in context from story_load)
   → finds: characters/mara.md has sections [Personality, Background, Voice, ...]

2. LLM calls: story_retrieve(entity_type="character", slug="mara", sections=["Voice"])

3. Tool handler:
   a. Reads characters/mara.md
   b. Calls get_section(body, "Voice") from section_parser.py
   c. Returns: "## Voice\nPrecise, clinical. Rarely uses contractions..."

4. LLM answers based on retrieved content
```

---

## Implementation

```python
from pathlib import Path
from .section_parser import get_section, list_sections
import frontmatter

ENTITY_FOLDERS = {
    "character": "characters",
    "location": "locations",
    "world": "worlds",
    "plot": "plots",
    "project": ".",
}

def story_retrieve(entity_type: str, slug: str, sections: list[str]) -> dict:
    """Retrieve specific sections from a story project note."""
    # Resolve file path
    folder = ENTITY_FOLDERS[entity_type]
    if entity_type == "project":
        file_path = Path(f"project.md")
    else:
        file_path = Path(f"{folder}/{slug}.md")
    
    if not file_path.exists():
        return {"error": f"Entity not found: {entity_type}/{slug}"}
    
    # Read file
    post = frontmatter.load(file_path)
    body = post.content
    
    # Retrieve sections
    if sections == ["all"]:
        return {
            "entity_type": entity_type,
            "slug": slug,
            "sections": list_sections(body),
            "content": body
        }
    
    results = {}
    for section in sections:
        content = get_section(body, section)
        if content:
            results[section] = content
        else:
            # Section not found — list available
            available = list_sections(body)
            results[section] = f"Section '{section}' not found. Available: {available}"
    
    return {
        "entity_type": entity_type,
        "slug": slug,
        "sections": results
    }
```

---

## Error Handling

| Error | Response |
|-------|----------|
| Entity not found | `{"error": "Entity not found: character/mara"}` |
| Section not found | `{"Section Name": "Section 'X' not found. Available: [...]"}` |
| File read error | `{"error": "Failed to read file: <reason>"}` |

---

## Key Design Points

### 1. Reuses section_parser.py

No reinvention. `get_section()` from Task 2 does the extraction.

### 2. Semantic API

`entity_type + slug` instead of file paths. The LLM thinks "I want Mara's voice", not "I want characters/mara.md section 3".

### 3. Multiple sections in one call

`sections: ["Personality", "Voice"]` → one tool call, two sections. Reduces round-trips.

### 4. `"all"` shortcut

`sections: ["all"]` → returns full body. Useful for "tell me everything about X".

### 5. Missing section recovery

When a section isn't found, return the list of available sections so the LLM can retry.

---

## What this means for implementation

- `plugin/tools/story_retrieve.py` — tool handler (thin wrapper)
- `plugin/core/section_parser.py` — reused from Task 2
- No separate skill — retrieval is a tool, not a skill

---

## Status: RESOLVED
