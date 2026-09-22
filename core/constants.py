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
PLOT_SCOPES = ["main", "sub"]
VALUE_ARCS = ["Maturation", "Redemption", "Education", "Punitive", "Disillusionment", "Testing"]
ARC_TYPES = ["positive", "negative", "flat", "ironic", "absent"]
FUZZY_THRESHOLD = 40

REQUIRED_FIELDS = {
    "character": ["name", "story_role", "one_sentence"],
    "location": ["name", "one_sentence"],
    "world": ["name", "one_sentence"],
    "plot": ["name", "status"],
    "project": ["name", "logline"],
    "scene": ["title", "sequence_id", "act_id"],
    "sequence": ["title", "act_id"],
    "act": ["title"],
    "arc_beat": ["id", "character", "scene", "label", "action", "gap", "choice", "shift", "y", "order"],
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
    "arc_beat": "Arc Beat",
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
        "goals_short": {"type": "string", "default": "Goals not set", "optional": True, "description": "Short-term goal (flat form; nested goals.short also accepted)"},
        "goals_long": {"type": "string", "default": "Goals not set", "optional": True, "description": "Long-term goal (flat form; nested goals.long also accepted)"},
        "knowledge": {"type": "list", "default": [], "optional": True, "description": "Facts the character knows. Each entry is a string."},
        "arc_type": {"type": "string", "default": "Arc type not set", "optional": True, "description": "One of: positive, negative, flat, ironic, absent"},
        "arc_value": {"type": "string", "default": "Arc value not set", "optional": True, "description": "Value at stake across this character's arc"},
        "arc_value_at_open": {"type": "string", "default": "Not set", "optional": True, "description": "Value charge at arc open (positive/negative/mixed/ironic)"},
        "arc_value_at_close": {"type": "string", "default": "Not set", "optional": True, "description": "Value charge at arc close (positive/negative/mixed/ironic)"},
        "arc_complete": {"type": "boolean", "default": False, "optional": True, "description": "Whether this character's arc is complete"},
    },
    "location": {
        "name": {"type": "string", "default": "", "optional": False, "description": "Location display name"},
        "one_sentence": {"type": "string", "default": "", "optional": False, "description": "One-sentence summary for index label"},
        "mood": {"type": "string", "default": "", "optional": True, "description": "Emotional register of the place, generalized (e.g. 'oppressive domesticity')"},
        "dramatic_function": {"type": "string", "default": "", "optional": True, "description": "Why this place exists in the story (e.g. 'where the protagonist's past catches up')"},
        "world": {"type": "string", "default": "", "optional": True, "description": "World slug this location belongs to"},
        "variant_of": {"type": "string", "default": "", "optional": True, "description": "Slug of the base location this is a variant of. Empty on base locations."},
    },
    "world": {
        "name": {"type": "string", "default": "", "optional": False, "description": "World display name"},
        "one_sentence": {"type": "string", "default": "", "optional": False, "description": "One-sentence summary for index label"},
        "rules": {"type": "list", "default": [], "optional": True, "description": "World rules. Each entry is a string."},
        "period": {"type": "string", "default": "", "optional": True, "description": "When this world exists (e.g. '2040s', '+400y after the collapse')"},
        "values": {"type": "list", "default": [], "optional": True, "description": "What this world holds sacred/moral (e.g. 'truth is sacred')"},
        "power": {"type": "list", "default": [], "optional": True, "description": "Who holds power and how (e.g. 'the Church sanctions all tech')"},
        "variant_of": {"type": "string", "default": "", "optional": True, "description": "Slug of the base world this is a version of. Empty on base worlds."},
    },
    "plot": {
        "name": {"type": "string", "default": "", "optional": False, "description": "Plot display name"},
        "one_sentence": {"type": "string", "default": "Summary not set", "optional": True, "description": "One-sentence summary for index label"},
        "plot_type": {"type": "string", "default": "", "optional": True, "description": "One of: Contradictory, Resonant, Complicating, Setup"},
        "plot_scope": {"type": "string", "default": "", "optional": True, "description": "main or sub"},
        "value_arc": {"type": "string", "default": "Value arc not set", "optional": True, "description": "One of: Maturation, Redemption, Education, Punitive, Disillusionment, Testing"},
        "status": {"type": "string", "default": "active", "optional": True, "description": "One of: active, resolved, abandoned"},
        "characters": {"type": "list", "default": [], "optional": True, "description": "Character slugs involved in this plot (frontmatter-only)"},
        "setups": {"type": "list", "default": [], "optional": True, "description": "Scenes where plot is established", "sub_fields": {"scene_id": "Scene slug", "description": "What happens at this scene"}},
        "crisis": {"type": "list", "default": [], "optional": True, "description": "Scenes where plot reaches crisis point", "sub_fields": {"scene_id": "Scene slug", "description": "What happens at this scene"}},
        "climax": {"type": "list", "default": [], "optional": True, "description": "Scenes where plot reaches climax", "sub_fields": {"scene_id": "Scene slug", "description": "What happens at this scene"}},
        "payoffs": {"type": "list", "default": [], "optional": True, "description": "Scenes where plot resolves", "sub_fields": {"scene_id": "Scene slug", "description": "What happens at this scene"}},
    },
    "project": {
        "name": {"type": "string", "default": "", "optional": False, "description": "Project display name"},
        "logline": {"type": "string", "default": "logline not set", "optional": True, "description": "One-sentence summary of the story"},
        "genre": {"type": "string", "default": "genre not set", "optional": True, "description": "Story genre (e.g. Sci-fi thriller)"},
        "setting": {"type": "string", "default": "not set", "optional": True, "description": "Primary setting (e.g. Near-future city-state)"},
        "status": {"type": "string", "default": "active", "optional": True, "description": "One of: active, abandoned, archived"},
        "screenplay_title": {"type": "string", "default": "Default", "optional": True, "description": "Title page: screenplay title (center)"},
        "credit": {"type": "string", "default": "Credit N.A.", "optional": True, "description": "Title page: credit line (e.g. 'Written by')"},
        "author": {"type": "string", "default": "Author N.A.", "optional": True, "description": "Title page: author name"},
        "contact": {"type": "string", "default": "Contact N.A.", "optional": True, "description": "Title page: contact info (bottom-right)"},
        "draft_date": {"type": "string", "default": "Draft Date N.A.", "optional": True, "description": "Title page: draft date (bottom-left)"},
        "draft": {"type": "string", "default": "N.A.", "optional": True, "description": "Title page: draft label (e.g. 'First Draft')"},
        "spine": {"type": "string", "default": "Spine not set", "optional": True, "description": "Protagonist's desire (story-level spine)"},
        "controlling_idea": {"type": "string", "default": "Controlling Idea not set", "optional": True, "description": "The story's controlling idea/argument"},
        "value": {"type": "string", "default": "Value not set", "optional": True, "description": "Value at stake for the whole story"},
        "value_at_open": {"type": "string", "default": "Opening Value not set", "optional": True, "description": "One of: positive, negative, mixed, ironic"},
        "value_at_close": {"type": "string", "default": "Closing Value not set", "optional": True, "description": "One of: positive, negative, mixed, ironic"},
        "inciting_incident_scene_id": {"type": "string", "default": "Inciting Incident Scene not set", "optional": True, "description": "Scene slug of the inciting incident"},
        "story_climax_scene_id": {"type": "string", "default": "Story Climax Scene not set", "optional": True, "description": "Scene slug of the story climax"},
        "structure_type": {"type": "string", "default": "Structure Type not set", "optional": True, "description": "One of: Classical, Miniplot, Antiplot"},
        "act_count": {"type": "number", "default": 3, "optional": True, "description": "Number of acts in story structure (default 3, auto-adjusts upward if more act files exist)"},
    },
    "scene": {
        "id": {"type": "string", "default": "", "optional": False, "description": "Stable slug reflecting dramatic function (e.g., 'mara-discovers-files'), NOT the physical heading"},
        "type": {"type": "string", "default": "scene", "optional": False, "description": "Always 'scene'"},
        "title": {"type": "string", "default": "", "optional": False, "description": "Display name (freely editable) reflecting dramatic function"},
        "one_sentence": {"type": "string", "default": "", "optional": True, "description": "One-sentence summary of the scene"},
        "order": {"type": "number", "default": 0, "optional": False, "description": "Position within parent sequence (float for insertions)"},
        "status": {"type": "string", "default": "planned", "optional": False, "description": "One of: planned, drafted, written, locked"},
        "heading": {"type": "string", "default": "", "optional": True, "description": "Fountain scene heading (for screenplay output)"},
        "location": {"type": "string", "default": "Location not set", "optional": True, "description": "Location slug or free text"},
        "time_of_day": {"type": "string", "default": "", "optional": True, "description": "One of: DAY, NIGHT, DUSK, DAWN, CONTINUOUS, LATER"},
        "sequence_id": {"type": "string", "default": "", "optional": False, "description": "Parent sequence slug"},
        "act_id": {"type": "string", "default": "", "optional": False, "description": "Parent act slug (denormalized shortcut)"},
        "characters": {"type": "list", "default": [], "optional": True, "description": "Character slugs present in this scene"},
        "value": {"type": "string", "default": "Value not set", "optional": True, "description": "Value at stake in this scene"},
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
        "value": {"type": "string", "default": "Value not set", "optional": True, "description": "Value at stake in this sequence"},
        "value_open": {"type": "string", "default": "", "optional": True, "description": "One of: positive, negative, mixed, ironic"},
        "value_close": {"type": "string", "default": "", "optional": True, "description": "One of: positive, negative, mixed, ironic"},
        "climax_scene_id": {"type": "string", "default": "", "optional": True, "description": "Scene slug where this sequence's reversal lands"},
        "primary_plot": {"type": "string", "default": "", "optional": True, "description": "Primary plot slug this sequence serves"},
        "purpose": {"type": "string", "default": "Purpose not set", "optional": True, "description": "Free text: dramatic purpose of this sequence"},
    },
    "act": {
        "id": {"type": "string", "default": "", "optional": False, "description": "Stable slug"},
        "type": {"type": "string", "default": "act", "optional": False, "description": "Always 'act'"},
        "title": {"type": "string", "default": "", "optional": False, "description": "Display name. Use 'Act I', 'Act II', 'Act III', etc."},
        "order": {"type": "number", "default": 0, "optional": False, "description": "Position within story (float for insertions)"},
        "status": {"type": "string", "default": "planned", "optional": False, "description": "One of: planned, in-progress, complete"},
        "value": {"type": "string", "default": "Value not set", "optional": True, "description": "Value at stake in this act"},
        "value_open": {"type": "string", "default": "", "optional": True, "description": "One of: positive, negative, mixed, ironic"},
        "value_close": {"type": "string", "default": "", "optional": True, "description": "One of: positive, negative, mixed, ironic"},
        "climax_scene_id": {"type": "string", "default": "", "optional": True, "description": "Scene slug where this act's major reversal lands"},
        "act_objective": {"type": "string", "default": "Objective not set", "optional": True, "description": "Protagonist's immediate goal for this act"},
    },
    "arc_beat": {
        "id": {"type": "string", "default": "", "optional": False, "description": "Beat slug (unique within character)"},
        "character": {"type": "string", "default": "", "optional": False, "description": "Character slug this beat belongs to"},
        "scene": {"type": "string", "default": "", "optional": False, "description": "Scene slug where this beat occurs"},
        "order": {"type": "number", "default": 0, "optional": False, "description": "Position within character's arc"},
        "label": {"type": "string", "default": "", "optional": False, "description": "Human-readable label (e.g. 'First Doubt')"},
        "action": {"type": "string", "default": "Action not described", "optional": True, "description": "What the character does"},
        "gap": {"type": "string", "default": "Gap not defined", "optional": True, "description": "Expectation vs reality gap"},
        "choice": {"type": "string", "default": "Choice not recorded", "optional": True, "description": "The choice the character makes"},
        "shift": {"type": "string", "default": "Shift not recorded", "optional": True, "description": "Value shift (e.g. 'positive → mixed')"},
        "y": {"type": "number", "default": 0.0, "optional": True, "description": "Value charge (-1.0 to +1.0)"},
        "is_crisis": {"type": "boolean", "default": False, "optional": True, "description": "Marks a crisis beat"},
        "is_climax": {"type": "boolean", "default": False, "optional": True, "description": "Marks a climax beat"},
    },
}
