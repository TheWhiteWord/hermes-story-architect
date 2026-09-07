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
