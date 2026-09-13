"""Story Architect — shared constants and validation rules."""
from pathlib import Path

VALID_ROLES = ["Protagonist", "Antagonist", "Supporting", "Minor", "Cameo"]
VALID_STATUSES = ["active", "resolved", "abandoned"]
SCENE_STATUSES = ["planned", "drafted", "written", "locked"]
SEQUENCE_STATUSES = ["planned", "in-progress", "complete"]
ACT_STATUSES = ["planned", "in-progress", "complete"]
SCENE_TIMES_OF_DAY = ["DAY", "NIGHT", "DUSK", "DAWN", "CONTINUOUS", "LATER"]
SCENE_DRAMATIC_ROLES = ["setup", "complication", "crisis", "climax", "resolution", "transition", "non-event"]
VALUE_CHARGES = ["positive", "negative", "mixed", "ironic"]
STRUCTURE_TYPES = ["Classical", "Miniplot", "Antiplot"]
PLOT_TYPES = ["Contradictory", "Resonant", "Complicating", "Setup"]
FUZZY_THRESHOLD = 40

# Project fields that are dramatic/structural — these go to structure-index.yaml
# under the "story" key. All other project fields stay in main index.yaml.
# Note: value_at_open/value_close in project.md map to value_open/value_close
# in structure-index for consistency with act/sequence/scene entries.
PROJECT_STRUCTURAL_FIELDS = frozenset([
    "spine",
    "controlling_idea",
    "value",
    "value_at_open",
    "value_at_close",
    "inciting_incident_scene_id",
    "story_climax_scene_id",
    "structure_type",
])

REQUIRED_FIELDS = {
    "character": ["name", "story_role", "one_sentence"],
    "location": ["name", "one_sentence"],
    "world": ["name", "one_sentence"],
    "plot": ["name", "status"],
    "project": ["name", "logline"],
    "scene": ["title", "sequence_id", "act_id"],
    "sequence": ["title", "act_id"],
    "act": ["title"],
}

ENTITY_FOLDERS = {
    "character": "characters",
    "location": "locations",
    "world": "worlds",
    "plot": "plots",
    "project": ".",
    "scene": "scenes",
    "sequence": "sequences",
    "act": "acts",
}

ENTITY_LABELS = {
    "character": "Character",
    "location": "Location",
    "world": "World",
    "plot": "Plot",
    "project": "Project",
    "scene": "Scene",
    "sequence": "Sequence",
    "act": "Act",
}

# Full field schemas — used by story_create and story_edit to ensure all fields
# are present. Each field carries type, default value, and description.
# This makes the schema self-documenting — the LLM can discover expected fields
# and their meanings from this dictionary alone, without external reference files.
ENTITY_SCHEMAS = {
    "character": {
        "name": {"type": "string", "default": "", "optional": False, "description": "Character display name"},
        "story_role": {"type": "string", "default": "", "optional": False, "description": "One of: Protagonist, Antagonist, Supporting, Minor, Cameo"},
        "one_sentence": {"type": "string", "default": "", "optional": False, "description": "One-sentence summary for index label"},
        "relationships": {"type": "list", "default": [], "optional": True, "description": "Unidirectional relationships", "sub_fields": {"id": "Character slug", "label": "Relationship label (e.g. Partner)", "feeling": "Feeling towards them (e.g. Wary respect)"}},
        "goals_short": {"type": "string", "default": "", "optional": True, "description": "Short-term goal (flat form; nested goals.short also accepted)"},
        "goals_long": {"type": "string", "default": "", "optional": True, "description": "Long-term goal (flat form; nested goals.long also accepted)"},
        "knowledge": {"type": "list", "default": [], "optional": True, "description": "Facts the character knows. Each entry is a string."},
    },
    "location": {
        "name": {"type": "string", "default": "", "optional": False, "description": "Location display name"},
        "one_sentence": {"type": "string", "default": "", "optional": False, "description": "One-sentence summary for index label"},
    },
    "world": {
        "name": {"type": "string", "default": "", "optional": False, "description": "World display name"},
        "one_sentence": {"type": "string", "default": "", "optional": False, "description": "One-sentence summary for index label"},
        "rules": {"type": "list", "default": [], "optional": True, "description": "World rules. Each entry is a string."},
    },
    "plot": {
        "name": {"type": "string", "default": "", "optional": False, "description": "Plot display name"},
        "one_sentence": {"type": "string", "default": "", "optional": True, "description": "One-sentence summary for index label"},
        "plot_type": {"type": "string", "default": "", "optional": True, "description": "One of: Contradictory, Resonant, Complicating, Setup"},
        "status": {"type": "string", "default": "active", "optional": True, "description": "One of: active, resolved, abandoned"},
        "characters": {"type": "list", "default": [], "optional": True, "description": "Character slugs involved in this plot (frontmatter-only)"},
        "setups": {"type": "list", "default": [], "optional": True, "description": "Scenes where plot is established", "sub_fields": {"scene_id": "Scene slug (e.g. mara-discovers-files)", "description": "What happens at this scene"}},
        "payoffs": {"type": "list", "default": [], "optional": True, "description": "Scenes where plot resolves", "sub_fields": {"scene_id": "Scene slug (e.g. mara-discovers-files)", "description": "What happens at this scene"}},
    },
    "project": {
        "name": {"type": "string", "default": "", "optional": False, "description": "Project display name"},
        "logline": {"type": "string", "default": "", "optional": False, "description": "One-sentence summary of the story"},
        "genre": {"type": "string", "default": "", "optional": True, "description": "Story genre (e.g. Sci-fi thriller)"},
        "setting": {"type": "string", "default": "", "optional": True, "description": "Primary setting (e.g. Near-future city-state)"},
        "status": {"type": "string", "default": "active", "optional": True, "description": "One of: active, abandoned, archived"},
        "screenplay_title": {"type": "string", "default": "", "optional": True, "description": "Title page: screenplay title (center)"},
        "credit": {"type": "string", "default": "", "optional": True, "description": "Title page: credit line (e.g. 'Written by')"},
        "author": {"type": "string", "default": "", "optional": True, "description": "Title page: author name"},
        "contact": {"type": "string", "default": "", "optional": True, "description": "Title page: contact info (bottom-right)"},
        "draft_date": {"type": "string", "default": "", "optional": True, "description": "Title page: draft date (bottom-left)"},
        "draft": {"type": "string", "default": "", "optional": True, "description": "Title page: draft label (e.g. 'First Draft')"},
        "spine": {"type": "string", "default": "", "optional": True, "description": "Protagonist's desire (story-level spine)"},
        "controlling_idea": {"type": "string", "default": "", "optional": True, "description": "The story's controlling idea/argument"},
        "value": {"type": "string", "default": "", "optional": True, "description": "Value at stake for the whole story"},
        "value_at_open": {"type": "string", "default": "", "optional": True, "description": "One of: positive, negative, mixed, ironic"},
        "value_at_close": {"type": "string", "default": "", "optional": True, "description": "One of: positive, negative, mixed, ironic"},
        "inciting_incident_scene_id": {"type": "string", "default": "", "optional": True, "description": "Scene slug of the inciting incident"},
        "story_climax_scene_id": {"type": "string", "default": "", "optional": True, "description": "Scene slug of the story climax"},
        "structure_type": {"type": "string", "default": "", "optional": True, "description": "One of: Classical, Miniplot, Antiplot"},
    },
    "scene": {
        "id": {"type": "string", "default": "", "optional": False, "description": "Stable slug reflecting dramatic function (e.g., 'mara-discovers-files'), NOT the physical heading"},
        "type": {"type": "string", "default": "scene", "optional": False, "description": "Always 'scene'"},
        "title": {"type": "string", "default": "", "optional": False, "description": "Display name (freely editable)"},
        "order": {"type": "number", "default": 0, "optional": False, "description": "Position within parent sequence (float for insertions)"},
        "status": {"type": "string", "default": "planned", "optional": False, "description": "One of: planned, drafted, written, locked"},
        "heading": {"type": "string", "default": "", "optional": True, "description": "Fountain scene heading (for screenplay output)"},
        "location": {"type": "string", "default": "", "optional": True, "description": "Location slug or free text"},
        "time_of_day": {"type": "string", "default": "", "optional": True, "description": "One of: DAY, NIGHT, DUSK, DAWN, CONTINUOUS, LATER"},
        "sequence_id": {"type": "string", "default": "", "optional": False, "description": "Parent sequence slug"},
        "act_id": {"type": "string", "default": "", "optional": False, "description": "Parent act slug (denormalized shortcut)"},
        "characters": {"type": "list", "default": [], "optional": True, "description": "Character slugs present in this scene"},
        "plots": {"type": "list", "default": [], "optional": True, "description": "Plot slugs this scene advances"},
        "value": {"type": "string", "default": "", "optional": True, "description": "Value at stake in this scene"},
        "value_open": {"type": "string", "default": "", "optional": True, "description": "One of: positive, negative, mixed, ironic"},
        "value_close": {"type": "string", "default": "", "optional": True, "description": "One of: positive, negative, mixed, ironic"},
        "conflict_levels": {"type": "list", "default": [], "optional": True, "description": "Any of: inner, personal, extra-personal"},
        "dramatic_role": {"type": "string", "default": "", "optional": True, "description": "One of: setup, complication, crisis, climax, resolution, transition, non-event"},
        "is_inciting_incident": {"type": "boolean", "default": False, "optional": True, "description": "Marks the scene as the story's inciting incident"},
        "is_sequence_climax": {"type": "boolean", "default": False, "optional": True, "description": "Marks the scene as its sequence's climax"},
        "is_act_climax": {"type": "boolean", "default": False, "optional": True, "description": "Marks the scene as its act's climax"},
        "is_story_climax": {"type": "boolean", "default": False, "optional": True, "description": "Marks the scene as the story's climax"},
    },
    "sequence": {
        "id": {"type": "string", "default": "", "optional": False, "description": "Stable slug"},
        "type": {"type": "string", "default": "sequence", "optional": False, "description": "Always 'sequence'"},
        "title": {"type": "string", "default": "", "optional": False, "description": "Display name"},
        "order": {"type": "number", "default": 0, "optional": False, "description": "Position within parent act (float for insertions)"},
        "status": {"type": "string", "default": "planned", "optional": False, "description": "One of: planned, in-progress, complete"},
        "act_id": {"type": "string", "default": "", "optional": False, "description": "Parent act slug"},
        "value": {"type": "string", "default": "", "optional": True, "description": "Value at stake in this sequence"},
        "value_open": {"type": "string", "default": "", "optional": True, "description": "One of: positive, negative, mixed, ironic"},
        "value_close": {"type": "string", "default": "", "optional": True, "description": "One of: positive, negative, mixed, ironic"},
        "climax_scene_id": {"type": "string", "default": "", "optional": True, "description": "Scene slug where this sequence's reversal lands"},
        "primary_plot": {"type": "string", "default": "", "optional": True, "description": "Primary plot slug this sequence serves"},
        "purpose": {"type": "string", "default": "", "optional": True, "description": "Free text: dramatic purpose of this sequence"},
    },
    "act": {
        "id": {"type": "string", "default": "", "optional": False, "description": "Stable slug"},
        "type": {"type": "string", "default": "act", "optional": False, "description": "Always 'act'"},
        "title": {"type": "string", "default": "", "optional": False, "description": "Display name"},
        "order": {"type": "number", "default": 0, "optional": False, "description": "Position within story (float for insertions)"},
        "status": {"type": "string", "default": "planned", "optional": False, "description": "One of: planned, in-progress, complete"},
        "value": {"type": "string", "default": "", "optional": True, "description": "Value at stake in this act"},
        "value_open": {"type": "string", "default": "", "optional": True, "description": "One of: positive, negative, mixed, ironic"},
        "value_close": {"type": "string", "default": "", "optional": True, "description": "One of: positive, negative, mixed, ironic"},
        "climax_scene_id": {"type": "string", "default": "", "optional": True, "description": "Scene slug where this act's major reversal lands"},
        "act_objective": {"type": "string", "default": "", "optional": True, "description": "Protagonist's immediate goal for this act"},
    },
}
