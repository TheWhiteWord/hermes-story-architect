"""Story Architect — shared constants and validation rules."""
from pathlib import Path

VALID_ROLES = ["Protagonist", "Antagonist", "Supporting", "Minor", "Cameo"]
VALID_STATUSES = ["active", "resolved", "abandoned"]
FUZZY_THRESHOLD = 40

REQUIRED_FIELDS = {
    "character": ["name", "story_role", "one_sentence"],
    "location": ["name", "one_sentence"],
    "world": ["name", "one_sentence"],
    "plot": ["name", "status"],
    "project": ["name", "logline"],
}

ENTITY_FOLDERS = {
    "character": "characters",
    "location": "locations",
    "world": "worlds",
    "plot": "plots",
    "project": ".",
}

ENTITY_LABELS = {
    "character": "Character",
    "location": "Location",
    "world": "World",
    "plot": "Plot",
    "project": "Project",
}

# Full field schemas — used by story_create and story_edit to ensure all fields
# are present. Each field carries type, default value, and description.
# This makes the schema self-documenting — the LLM can discover expected fields
# and their meanings from this dictionary alone, without external reference files.
ENTITY_SCHEMAS = {
    "character": {
        "name": {"type": "string", "default": "", "description": "Character display name"},
        "story_role": {"type": "string", "default": "", "description": "One of: Protagonist, Antagonist, Supporting, Minor, Cameo"},
        "one_sentence": {"type": "string", "default": "", "description": "One-sentence summary for index label"},
        "relationships": {"type": "list", "default": [], "description": "Unidirectional relationships. Each: {id (char slug), label (e.g. Partner), feeling (e.g. Wary respect)}"},
        "goals_short": {"type": "string", "default": "", "description": "Short-term goal (flat form; nested goals.short also accepted)"},
        "goals_long": {"type": "string", "default": "", "description": "Long-term goal (flat form; nested goals.long also accepted)"},
        "knowledge": {"type": "list", "default": [], "description": "Facts the character knows. Each entry is a string."},
    },
    "location": {
        "name": {"type": "string", "default": "", "description": "Location display name"},
        "one_sentence": {"type": "string", "default": "", "description": "One-sentence summary for index label"},
    },
    "world": {
        "name": {"type": "string", "default": "", "description": "World display name"},
        "one_sentence": {"type": "string", "default": "", "description": "One-sentence summary for index label"},
        "rules": {"type": "list", "default": [], "description": "World rules. Each entry is a string."},
    },
    "plot": {
        "name": {"type": "string", "default": "", "description": "Plot display name"},
        "one_sentence": {"type": "string", "default": "", "description": "One-sentence summary for index label"},
        "status": {"type": "string", "default": "active", "description": "One of: active, resolved, abandoned"},
        "characters": {"type": "list", "default": [], "description": "Character slugs involved in this plot (frontmatter-only)"},
        "setups": {"type": "list", "default": [], "description": "Scenes where plot is established. Each: {heading (fountain heading), number (scene id), description (what happens)}"},
        "payoffs": {"type": "list", "default": [], "description": "Scenes where plot resolves. Each: {heading (fountain heading), number (scene id), description (what happens)}"},
    },
    "project": {
        "name": {"type": "string", "default": "", "description": "Project display name"},
        "logline": {"type": "string", "default": "", "description": "One-sentence summary of the story"},
        "genre": {"type": "string", "default": "", "description": "Story genre (e.g. Sci-fi thriller)"},
        "setting": {"type": "string", "default": "", "description": "Primary setting (e.g. Near-future city-state)"},
        "status": {"type": "string", "default": "active", "description": "One of: active, abandoned, archived"},
    },
}
