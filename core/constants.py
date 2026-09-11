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
        "story_role": {"type": "string", "default": "", "description": "Protagonist/Antagonist/Supporting/Minor/Cameo"},
        "one_sentence": {"type": "string", "default": "", "description": "One-line description for index"},
        "relationships": {"type": "list", "default": [], "description": "List of {id, label, feeling}"},
        "goals_short": {"type": "string", "default": "", "description": "Short-term goal"},
        "goals_long": {"type": "string", "default": "", "description": "Long-term goal"},
        "knowledge": {"type": "list", "default": [], "description": "Facts the character knows"},
    },
    "location": {
        "name": {"type": "string", "default": "", "description": "Location display name"},
        "one_sentence": {"type": "string", "default": "", "description": "One-line description for index"},
    },
    "world": {
        "name": {"type": "string", "default": "", "description": "World display name"},
        "one_sentence": {"type": "string", "default": "", "description": "One-line description for index"},
        "rules": {"type": "list", "default": [], "description": "World rules"},
    },
    "plot": {
        "name": {"type": "string", "default": "", "description": "Plot display name"},
        "one_sentence": {"type": "string", "default": "", "description": "One-line description for index"},
        "status": {"type": "string", "default": "active", "description": "active/resolved/abandoned"},
        "characters": {"type": "list", "default": [], "description": "Character slugs (frontmatter-only)"},
        "setups": {"type": "list", "default": [], "description": "Beats where plot is established"},
        "payoffs": {"type": "list", "default": [], "description": "Beats where plot resolves"},
    },
    "project": {
        "name": {"type": "string", "default": "", "description": "Project display name"},
        "logline": {"type": "string", "default": "", "description": "One-sentence summary"},
        "genre": {"type": "string", "default": "", "description": "Story genre"},
        "setting": {"type": "string", "default": "", "description": "Primary setting"},
        "status": {"type": "string", "default": "active", "description": "active/abandoned/archived"},
    },
}
