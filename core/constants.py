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

# The dramatic roles a plot can hold — the `plot_<role>` relation kinds and the
# `has_<role>` flags the dashboard reads. Declared here because `constants`
# cannot import `entity` (entity imports constants); the authoritative
# field↔kind map is `_RELATION_FIELDS["plot"]`, and tests/test_plot_roles.py
# pins the two together so they cannot drift.
PLOT_ROLES = ["setup", "complication", "crisis", "climax", "resolution"]
VALUE_ARCS = ["Maturation", "Redemption", "Education", "Punitive", "Disillusionment", "Testing"]
ARC_TYPES = ["positive", "negative", "flat", "ironic", "absent"]
FUZZY_THRESHOLD = 40

MEMORY_CATEGORIES = ("decisions", "directions", "open_questions", "continuity_warnings")
MEMORY_CHAR_LIMIT = 3000
MEMORY_ENTRY_LIMIT = 300

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
    "relationship": "Relationship",
}

# Full field schemas — used by the write path to ensure all fields
# are present. Each field carries type, default value, and description.
# This makes the schema self-documenting — the LLM can discover expected fields
# and their meanings from this dictionary alone, without external reference files.
ENTITY_SCHEMAS = {
    "character": {
        "name": {"type": "string", "default": "", "optional": False, "description": "Character display name"},
        "story_role": {"type": "string", "default": "", "optional": False, "description": "One of: Protagonist, Antagonist, Supporting, Minor, Cameo"},
        "one_sentence": {"type": "string", "default": "", "optional": False, "description": "One-sentence summary for index label"},
        "relationships": {
            "type": "list", "default": [], "optional": True, "computed": True,
            "description": "Computed summary of relationship entities (read-only, derived from relationships/)",
            # Declared because the load payload emits these objects and nothing
            # said what was in them. Read-only, so this is for interpretation,
            # not for writing — the draft validator rejects a write with a
            # "read-only" finding. `strength` appears only in the dashboard
            # view, which carries more than the load payload.
            "sub_fields": {
                "with": {"type": "string", "description": "Slug of the OTHER character in this relationship — never this one"},
                "label": {"type": "string", "description": "This character's label for the other (e.g. 'Colleague')"},
                "type": {"type": "string", "description": "How this character reads the bond. Observed: ally, rival, enemy, family, romantic. Free text — not a closed set."},
                "strength": {"type": "number", "description": "Signed tension: negative is antagonism (observed -0.6..0.9). Dashboard view only."},
            },
        },
        "goals_short": {"type": "string", "default": "", "optional": True, "description": "Short-term goal"},
        "goals_long": {"type": "string", "default": "", "optional": True, "description": "Long-term goal"},
        "knowledge": {"type": "list", "default": [], "optional": True, "description": "Facts the character knows. Each entry is a string."},
        "arc_type": {"type": "string", "default": "", "optional": True, "description": "One of: positive, negative, flat, ironic, absent"},
        "character_value": {"type": "string", "default": "", "optional": True, "description": "The value this character's arc explores (e.g. 'Freedom'). May differ from the story's."},
        "character_value_at_open": {"type": "string", "default": "", "optional": True, "description": "Charge on this character's value where their arc begins. One of: positive, negative, mixed, ironic."},
        "character_value_at_close": {"type": "string", "default": "", "optional": True, "description": "Charge on this character's value where their arc ends. One of: positive, negative, mixed, ironic."},
        "arc_complete": {"type": "boolean", "default": False, "optional": True, "description": "Whether this character's arc is complete"},
        "arc_beats_list": {"type": "list", "default": [], "optional": True, "computed": True, "description": "Computed list of arc beats for this character (read-only, derived from arc_beat entities)"},
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
        "one_sentence": {"type": "string", "default": "", "label": "Summary", "optional": True, "description": "One-sentence summary for index label"},
        "plot_type": {"type": "string", "default": "", "optional": True, "description": "One of: Contradictory, Resonant, Complicating, Setup"},
        "plot_scope": {"type": "string", "default": "", "optional": True, "description": "main or sub"},
        "value_arc": {"type": "string", "default": "", "optional": True, "description": "One of: Maturation, Redemption, Education, Punitive, Disillusionment, Testing"},
        "status": {"type": "string", "default": "active", "optional": True, "description": "One of: active, resolved, abandoned"},
        "characters": {"type": "list", "default": [], "optional": True, "description": "Character slugs involved in this plot (frontmatter-only)"},
        "setups": {"type": "list", "default": [], "optional": True, "description": "Scenes where plot is established", "sub_fields": {"scene_id": "Scene slug", "description": "What happens at this scene"}},
        "crisis": {"type": "list", "default": [], "optional": True, "description": "Scenes where plot reaches crisis point", "sub_fields": {"scene_id": "Scene slug", "description": "What happens at this scene"}},
        "climax": {"type": "list", "default": [], "optional": True, "description": "Scenes where plot reaches climax", "sub_fields": {"scene_id": "Scene slug", "description": "What happens at this scene"}},
        "complications": {"type": "list", "default": [], "optional": True, "description": "Scenes where plot is complicated or obstructed", "sub_fields": {"scene_id": "Scene slug", "description": "What happens at this scene"}},
        "resolutions": {"type": "list", "default": [], "optional": True, "description": "Scenes where plot resolves", "sub_fields": {"scene_id": "Scene slug", "description": "What happens at this scene"}},
    },
    "project": {
        "name": {"type": "string", "default": "", "optional": False, "description": "Project display name"},
        "logline": {"type": "string", "default": "", "optional": True, "description": "One-sentence summary of the story"},
        "genre": {"type": "string", "default": "", "optional": True, "description": "Story genre (e.g. Sci-fi thriller)"},
        "setting": {"type": "string", "default": "", "optional": True, "description": "Primary setting (e.g. Near-future city-state)"},
        "status": {"type": "string", "default": "active", "optional": True, "description": "One of: active, abandoned, archived"},
        "screenplay_title": {"type": "string", "default": "Default", "optional": True, "description": "Title page: screenplay title (center)"},
        "credit": {"type": "string", "default": "", "optional": True, "description": "Title page: credit line (e.g. 'Written by')"},
        "author": {"type": "string", "default": "", "optional": True, "description": "Title page: author name"},
        "contact": {"type": "string", "default": "", "optional": True, "description": "Title page: contact info (bottom-right)"},
        "draft_date": {"type": "string", "default": "", "optional": True, "description": "Title page: draft date (bottom-left)"},
        "draft": {"type": "string", "default": "", "optional": True, "description": "Title page: draft label (e.g. 'First Draft')"},
        "spine": {"type": "string", "default": "", "optional": True, "description": "Protagonist's desire (story-level spine)"},
        "controlling_idea": {"type": "string", "default": "", "optional": True, "description": "The story's controlling idea/argument"},
        "story_value": {"type": "string", "default": "", "optional": True, "description": "The story's thematic value (e.g. 'Trust'). Stated once, here; scenes inherit it."},
        "story_value_at_open": {"type": "string", "default": "", "optional": True, "description": "Charge on the story value as the story opens. One of: positive, negative, mixed, ironic."},
        "story_value_at_close": {"type": "string", "default": "", "optional": True, "description": "Charge on the story value as the story closes. One of: positive, negative, mixed, ironic."},
        "inciting_incident_scene_id": {"type": "string", "default": "", "label": "Inciting Incident", "optional": True, "description": "Scene slug of the inciting incident"},
        "story_climax_scene_id": {"type": "string", "default": "", "label": "Story Climax", "optional": True, "description": "Scene slug of the story climax"},
        "structure_type": {"type": "string", "default": "", "optional": True, "description": "One of: Classical, Miniplot, Antiplot"},
        "act_count": {"type": "number", "default": 3, "optional": True, "description": "Number of acts in story structure (default 3, auto-adjusts upward if more act files exist)"},
    },
    "scene": {
        "type": {"type": "string", "default": "scene", "optional": False, "description": "Always 'scene'"},
        "title": {"type": "string", "default": "", "optional": False, "description": "Display name (freely editable) reflecting dramatic function"},
        "one_sentence": {"type": "string", "default": "", "optional": True, "description": "One-sentence summary of the scene"},
        "order": {"type": "number", "default": 0, "optional": False, "description": "Position within parent sequence (float for insertions)"},
        "status": {"type": "string", "default": "planned", "optional": False, "description": "One of: planned, drafted, written, locked"},
        "heading": {"type": "string", "default": "", "optional": True, "description": "Fountain scene heading (for screenplay output)"},
        "location": {"type": "string", "default": "", "optional": True, "description": "Slug of an existing location"},
        "time_of_day": {"type": "string", "default": "", "optional": True, "description": "One of: DAY, NIGHT, DUSK, DAWN, CONTINUOUS, LATER"},
        "sequence_id": {"type": "string", "default": "", "optional": False, "description": "Parent sequence slug"},
        "act_id": {"type": "string", "default": "", "optional": False, "description": "Parent act slug (denormalized shortcut)"},
        "characters": {"type": "list", "default": [], "optional": True, "description": "Character slugs present in this scene"},
        "no_cast": {"type": "boolean", "default": False, "optional": True, "description": "Set true when this scene deliberately has no characters (e.g. an empty room). Clears the 'characters unfilled' gap so a decision is not flagged forever"},
        "value_at_open": {"type": "string", "default": "", "optional": True, "description": "Charge on the story value entering this scene. One of: positive, negative, mixed, ironic."},
        "value_at_close": {"type": "string", "default": "", "optional": True, "description": "Charge on the story value leaving this scene. One of: positive, negative, mixed, ironic."},
        "shift": {"type": "string", "default": "", "optional": True, "description": "How the story value turns here, in the story's language (e.g. 'trust → suspicion')."},
        "y": {"type": "number", "default": 0.0, "optional": True, "description": "Ending charge on the story value after this scene's turn, -1.0 to +1.0, signed like the charge word: positive is above zero, negative below, mixed and ironic in between. The point the story-value curve passes through."},
        "conflict_levels": {"type": "list", "default": [], "optional": True, "description": "Any of: inner, personal, extra-personal"},
        "dramatic_role": {"type": "string", "default": "", "optional": True, "description": "One of: setup, complication, crisis, climax, resolution, transition, non-event"},
        "is_inciting_incident": {"type": "boolean", "default": False, "optional": True, "description": "Marks the scene as the story's inciting incident"},
        "is_sequence_climax": {"type": "boolean", "default": False, "optional": True, "description": "Marks the scene as its sequence's climax"},
        "is_act_climax": {"type": "boolean", "default": False, "optional": True, "description": "Marks the scene as its act's climax"},
        "is_story_climax": {"type": "boolean", "default": False, "optional": True, "description": "Marks the scene as the story's climax"},
    },
    "sequence": {
        "type": {"type": "string", "default": "sequence", "optional": False, "description": "Always 'sequence'"},
        "title": {"type": "string", "default": "", "optional": False, "description": "Display name"},
        "order": {"type": "number", "default": 0, "optional": False, "description": "Position within parent act (float for insertions)"},
        "status": {"type": "string", "default": "planned", "optional": False, "description": "One of: planned, in-progress, complete"},
        "act_id": {"type": "string", "default": "", "optional": False, "description": "Parent act slug"},
        "value_at_open": {"type": "string", "default": "", "optional": True, "description": "Charge on the story value entering this sequence. One of: positive, negative, mixed, ironic."},
        "value_at_close": {"type": "string", "default": "", "optional": True, "description": "Charge on the story value leaving this sequence. One of: positive, negative, mixed, ironic."},
        "climax_scene_id": {"type": "string", "default": "", "optional": True, "description": "Scene slug where this sequence's reversal lands"},
        "primary_plot": {"type": "string", "default": "", "optional": True, "description": "Primary plot slug this sequence serves"},
        "purpose": {"type": "string", "default": "", "optional": True, "description": "Free text: dramatic purpose of this sequence"},
    },
    "act": {
        "type": {"type": "string", "default": "act", "optional": False, "description": "Always 'act'"},
        "title": {"type": "string", "default": "", "optional": False, "description": "Display name. Use 'Act I', 'Act II', 'Act III', etc."},
        "order": {"type": "number", "default": 0, "optional": False, "description": "Position within story (float for insertions)"},
        "status": {"type": "string", "default": "planned", "optional": False, "description": "One of: planned, in-progress, complete"},
        "value_at_open": {"type": "string", "default": "", "optional": True, "description": "Charge on the story value entering this act. One of: positive, negative, mixed, ironic."},
        "value_at_close": {"type": "string", "default": "", "optional": True, "description": "Charge on the story value leaving this act. One of: positive, negative, mixed, ironic."},
        "climax_scene_id": {"type": "string", "default": "", "optional": True, "description": "Scene slug where this act's major reversal lands"},
        "act_objective": {"type": "string", "default": "", "label": "Objective", "optional": True, "description": "Protagonist's immediate goal for this act"},
    },
    "arc_beat": {
        "character": {"type": "string", "default": "", "optional": False, "description": "Character slug this beat belongs to"},
        "scene": {"type": "string", "default": "", "optional": False, "description": "Scene slug where this beat occurs"},
        "order": {"type": "number", "default": 0, "optional": False, "description": "Position within character's arc"},
        "label": {"type": "string", "default": "", "optional": False, "description": "Human-readable label (e.g. 'First Doubt')"},
        "action": {"type": "string", "default": "", "optional": True, "description": "What the character does"},
        "gap": {"type": "string", "default": "", "optional": True, "description": "Expectation vs reality gap"},
        "choice": {"type": "string", "default": "", "optional": True, "description": "The choice the character makes"},
        "character_value_at_open": {"type": "string", "default": "", "optional": True, "description": "Charge on this character's value entering this beat. One of: positive, negative, mixed, ironic."},
        "character_value_at_close": {"type": "string", "default": "", "optional": True, "description": "Charge on this character's value leaving this beat. One of: positive, negative, mixed, ironic."},
        "shift": {"type": "string", "default": "", "optional": True, "description": "How this character's value turns at this beat, in dramatic language (e.g. 'suspicious doubt → active defiance')."},
        "y": {"type": "number", "default": 0.0, "optional": True, "description": "Ending charge on this character's value after this beat's turn, -1.0 to +1.0, signed like the charge word: positive is above zero, negative below, mixed and ironic in between. The point the arc curve passes through."},
        "is_crisis": {"type": "boolean", "default": False, "optional": True, "description": "Marks a crisis beat"},
        "is_climax": {"type": "boolean", "default": False, "optional": True, "description": "Marks a climax beat"},
    },
    "relationship": {
        "name": {"type": "string", "default": "", "optional": False, "description": "Display name (e.g. 'Kael & Mira')"},
        "type": {"type": "string", "default": "relationship", "optional": False, "description": "Always 'relationship'"},
        "characters": {"type": "list", "default": [], "optional": False, "description": "Exactly two character slugs"},
        "perspectives": {"type": "object", "default": {}, "optional": True, "description": "Per-character relationship view", "sub_fields": {
            "label": {"type": "string", "description": "Relationship label from this character's POV"},
            "feeling": {"type": "string", "description": "Emotional stance"},
            "type": {"type": "string", "description": "Category: ally/enemy/family/romantic/professional/mentor/rival/custom/neutral"},
            "strength": {"type": "number", "description": "Intensity -1.0 to 1.0"},
            "secret": {"type": "boolean", "description": "Hidden from other character"},
        }},
        "scenes": {"type": "list", "default": [], "optional": True, "description": "Scenes where this relationship is featured"},
        "status": {"type": "string", "default": "active", "optional": True, "description": "active/resolved/complex"},
        "history": {"type": "string", "default": "", "optional": True, "description": "How this relationship evolved"},
    },
}

# The one phrase that means "the user has not set this". It lives here, beside
# the schema, because it is a *display* concern and the schema is where a field
# declares what it is — but it is never stored. A field the user has not filled
# holds `""` (or `0`, `False`, `[]`), and a surface that wants to say so renders
# `f"{label}: {UNFILLED}"`.
#
# It was 34 strings before this, one per field: 'Goals not set', 'Action not
# described', 'Shift not recorded', 'Credit N.A.'. They were defaults written
# into the data on create, and the enum check then rejected them as invalid
# values — 10 false findings on a minimal character, plot, project or arc beat.
# Nothing was ever stored in them: both real databases hold zero. The prose was
# never carrying information either, because `story_retrieve` reports unfilled
# fields *by name* through `unfilled_fields`.
UNFILLED = "N.A."

# ─── Required fields ───
# Derived from ENTITY_SCHEMAS rather than maintained beside it. A hand-written
# copy drifted: it demanded an arc_beat `id` the write path never reads (the id
# is built from the slug), listed five fields the schema marks optional, and
# listed two more — plot.status, project.logline — that survived only because
# their defaults happen to be truthy. Three notes on the rule:
#
#   * `id` and `type` are in FIELDS_TO_SKIP, so the write path discards them.
#   * `order` is auto-numbered by create_entity.
#   * `status` defaults to a valid value.
#
# All four are supplied here, so requiring them asks for something the caller
# cannot meaningfully provide. Duplicating ENTITY_SCHEMAS is what created the
# bug; this is the one place the answer is written down.
WRITE_PATH_SUPPLIED = {"id", "type", "order", "status"}

REQUIRED_FIELDS = {
    entity_type: [field for field, meta in schema.items()
                  if not meta.get("optional", True) and field not in WRITE_PATH_SUPPLIED]
    for entity_type, schema in ENTITY_SCHEMAS.items()
}
