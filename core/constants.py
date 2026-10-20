"""Story Architect — shared constants and validation rules."""
from pathlib import Path

VALID_ROLES = ["Protagonist", "Antagonist", "Supporting", "Minor", "Cameo"]
VALID_STATUSES = ["active", "resolved", "abandoned"]
SCENE_STATUSES = ["planned", "drafted", "written", "locked"]
SEQUENCE_STATUSES = ["planned", "in-progress", "complete"]
ACT_STATUSES = ["planned", "in-progress", "complete"]
SCENE_TIMES_OF_DAY = ["DAY", "NIGHT", "DUSK", "DAWN", "CONTINUOUS", "LATER"]
# A scene's dramatic function. `plot_role` is the ordinary case: the role is
# defined per plot in the scene's `plot_roles`, never here. The other two are
# the only reasons a scene can serve NO plot — a bridge between beats, or a
# beat that moves nothing. They are mutually exclusive with `plot_roles`.
SCENE_DRAMATIC_ROLES = ["plot_role", "transition", "non-event"]
STRUCTURE_TYPES = ["Classical", "Miniplot", "Antiplot"]
PLOT_TYPES = ["Contradictory", "Resonant", "Complicating", "Setup"]
PLOT_SCOPES = ["main", "sub"]

# The dramatic roles a plot can hold — the `plot_<role>` relation kinds and the
# `has_<role>` flags the dashboard reads. Declared here because `constants`
# cannot import `entity` (entity imports constants); the authoritative
# field↔kind map is `_RELATION_FIELDS["plot"]`, and tests/test_plot_roles.py
# pins the two together so they cannot drift.
PLOT_ROLES = ["setup", "inciting_incident", "complication", "crisis", "climax", "resolution"]
# The value ladder — four rungs of opposition (design §3.1).
# The rung is looked up from the word and never stored. The codes are the
# field names on a `value` entity; the meanings are what the skill teaches.
# C and CD are defined per the source file; the notes in ISSUES.md have them
# swapped.
VALUE_LADDER = {
    "p": "Positive, the ideal",
    "c": "Contrary: opposite, not absolute negation",
    "cd": "Contradictory: direct negation of the positive",
    "nn": "Negation of negation: perversion or false version of the positive",
}

# Where the opposition comes from, relative to one character.
CONFLICT_LEVELS = ["inner", "personal", "extra-personal"]

# How many values are major in a unit. Ties at the cut are all major, so a
# unit can carry more than three (design §4).
VALUE_MAJOR_COUNT = 3

VALUE_ARCS = ["Maturation", "Redemption", "Education", "Punitive", "Disillusionment", "Testing"]
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
    "relationship": "Relationship",
    "value": "Value",
    "scene_beats": "Scene Beats",
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
        "goals_short": {"type": "string", "default": "", "optional": True, "description": "Short-term goal"},
        "goals_long": {"type": "string", "default": "", "optional": True, "description": "Long-term goal"},
        "knowledge": {"type": "list", "default": [], "optional": True, "description": "Facts the character knows. Each entry is a string."},
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
    # Field ORDER is part of the contract: a reader gets these fields in
    # reading order, not hash order. What a plot IS (name, one-sentence,
    # status), then WHO and WHAT SHAPE (cast, value arc, scope, type), then
    # its dramatic progression in the order the beats happen. The roles were
    # declared setups/crisis/climax/complications/resolutions, which is neither
    # the dramatic order (setup, complication, crisis, climax, resolution) nor
    # the order a reader scans them in.
    "plot": {
        "name": {"type": "string", "default": "", "optional": False, "description": "Plot display name"},
        "one_sentence": {"type": "string", "default": "", "label": "Summary", "optional": True, "description": "One-sentence summary for index label"},
        "status": {"type": "string", "default": "active", "optional": True, "description": "One of: active, resolved, abandoned"},
        "characters": {"type": "list", "default": [], "optional": True, "description": "Character slugs of this plot's protagonists only", "ref": "character"},
        "value_arc": {"type": "string", "default": "", "optional": True, "description": "One of: Maturation, Redemption, Education, Punitive, Disillusionment, Testing"},
        "plot_scope": {"type": "string", "default": "", "optional": True, "description": "main or sub"},
        "plot_type": {"type": "string", "default": "", "optional": True, "description": "One of: Contradictory, Resonant, Complicating, Setup (required for sub plots only)"},
        # The six role fields are READ-ONLY: they are the same `plot_<role>`
        # rows the scene writes as `plot_roles`, read back from the plot side.
        # The agent records a role where it is writing the scene, and never has
        # to reopen a plot to add one. `computed` is what makes every write
        # path refuse them — draft preview, create, edit, describe.
        #
        # Declared in dramatic order, which is the order they occur and the
        # order a reader scans them: setup → inciting_incident → complication →
        # crisis → climax → resolution. Note this is NOT `PLOT_ROLES`' order —
        # complications is plural and sits third, not last. A test pins the
        # two so they cannot drift, because the field names are not the role
        # names.
        "setups": {"type": "list", "default": [], "optional": True, "computed": True, "description": "Scenes where plot is established (read-only — set it on the scene as plot_roles)", "sub_fields": {"scene_id": {"type": "string", "description": "Scene slug"}, "description": {"type": "string", "description": "What happens at this scene"}}},
        "inciting_incident": {"type": "list", "default": [], "optional": True, "computed": True, "description": "Scenes where plot is incited (read-only — set it on the scene as plot_roles)", "sub_fields": {"scene_id": {"type": "string", "description": "Scene slug"}, "description": {"type": "string", "description": "What happens at this scene"}}},
        "complications": {"type": "list", "default": [], "optional": True, "computed": True, "description": "Scenes where plot is complicated or obstructed (read-only — set it on the scene as plot_roles)", "sub_fields": {"scene_id": {"type": "string", "description": "Scene slug"}, "description": {"type": "string", "description": "What happens at this scene"}}},
        "crisis": {"type": "list", "default": [], "optional": True, "computed": True, "description": "Scenes where plot reaches crisis point (read-only — set it on the scene as plot_roles)", "sub_fields": {"scene_id": {"type": "string", "description": "Scene slug"}, "description": {"type": "string", "description": "What happens at this scene"}}},
        "climax": {"type": "list", "default": [], "optional": True, "computed": True, "description": "Scenes where plot reaches climax (read-only — set it on the scene as plot_roles)", "sub_fields": {"scene_id": {"type": "string", "description": "Scene slug"}, "description": {"type": "string", "description": "What happens at this scene"}}},
        "resolutions": {"type": "list", "default": [], "optional": True, "computed": True, "description": "Scenes where plot resolves (read-only — set it on the scene as plot_roles)", "sub_fields": {"scene_id": {"type": "string", "description": "Scene slug"}, "description": {"type": "string", "description": "What happens at this scene"}}},
        "value_focus": {"type": "object", "keyed": False, "default": {"major": [], "minor": []}, "optional": True, "computed": True,
                        "description": "Computed: the values that shift in this plot's scenes, as {major: [{value, scenes}], minor: [{value, scenes}]}. Major is the most frequent, ties at the cut all major (VALUE_MAJOR_COUNT); scenes counts the scenes in which the value shifts. Read-only — derived from the scenes' value_turns.",
                        "sub_fields": {
                            "major": {"type": "list", "description": "The most frequent values in this unit, at most VALUE_MAJOR_COUNT, with ties at the cut included",
                                      "sub_fields": {"value": {"type": "string", "description": "The value's name"}, "scenes": {"type": "number", "description": "Scenes in which the value shifts"}}},
                            "minor": {"type": "list", "description": "The remaining values, by frequency",
                                      "sub_fields": {"value": {"type": "string", "description": "The value's name"}, "scenes": {"type": "number", "description": "Scenes in which the value shifts"}}},
                        }},
    },
    "project": {
        "name": {"type": "string", "default": "", "optional": False, "description": "Project display name"},
        "status": {"type": "string", "default": "active", "optional": True, "description": "One of: active, abandoned, archived"},
        "logline": {"type": "string", "default": "", "optional": True, "description": "One-sentence summary of the story"},
        "structure_type": {"type": "string", "default": "", "optional": True, "description": "One of: Classical, Miniplot, Antiplot"},
        "genre": {"type": "string", "default": "", "optional": True, "description": "Story genre (e.g. Sci-fi thriller)"},
        "act_count": {"type": "number", "default": 3, "optional": True, "description": "Number of acts in story structure (default 3, auto-adjusts upward if more act files exist)"},
        "screenplay_title": {"type": "string", "default": "Default", "optional": True, "description": "Title page: screenplay title (center)"},
        "setting": {"type": "string", "default": "", "optional": True, "description": "Primary setting (e.g. Near-future city-state)"},
        "spine": {"type": "string", "default": "", "optional": True, "description": "Protagonist's desire (story-level spine)"},
        "controlling_idea": {"type": "string", "default": "", "optional": True, "description": "The story's controlling idea/argument"},
        "credit": {"type": "string", "default": "", "optional": True, "description": "Title page: credit line (e.g. 'Written by')"},
        "author": {"type": "string", "default": "", "optional": True, "description": "Title page: author name"},
        "contact": {"type": "string", "default": "", "optional": True, "description": "Title page: contact info (bottom-right)"},
        "draft_date": {"type": "string", "default": "", "optional": True, "description": "Title page: draft date (bottom-left)"},
        "draft": {"type": "string", "default": "", "optional": True, "description": "Title page: draft label (e.g. 'First Draft')"},
        "value_focus": {"type": "object", "keyed": False, "default": {"major": [], "minor": []}, "optional": True, "computed": True,
                        "description": "Computed: the story's major and minor values, as {major: [{value, scenes}], minor: [{value, scenes}]}. Major is the main plot's major values; minor is the subplots' major values not already major (design §4). scenes counts the scenes in which the value shifts. Read-only — derived from the scenes' value_turns.",
                        "sub_fields": {
                            "major": {"type": "list", "description": "The main plot's most frequent values, at most VALUE_MAJOR_COUNT, with ties at the cut included",
                                      "sub_fields": {"value": {"type": "string", "description": "The value's name"}, "scenes": {"type": "number", "description": "Scenes in which the value shifts"}}},
                            "minor": {"type": "list", "description": "The subplots' major values not already major, by frequency",
                                      "sub_fields": {"value": {"type": "string", "description": "The value's name"}, "scenes": {"type": "number", "description": "Scenes in which the value shifts"}}},
                        }},
    },
    "scene": {
        "type": {"type": "string", "default": "scene", "optional": False, "description": "Always 'scene'"},
        "title": {"type": "string", "default": "", "optional": False, "description": "Display name (freely editable) reflecting dramatic function"},
        "status": {"type": "string", "default": "planned", "optional": False, "description": "One of: planned, drafted, written, locked"},
        "act_id": {"type": "string", "default": "", "optional": False, "description": "Parent act slug (denormalized shortcut)"},
        "sequence_id": {"type": "string", "default": "", "optional": False, "description": "Parent sequence slug"},
        "order": {"type": "number", "default": 0, "optional": False, "description": "Position within parent sequence (float for insertions)"},
        "heading": {"type": "string", "default": "", "optional": True, "description": "Fountain scene heading (for screenplay output)"},
        "location": {"type": "string", "default": "", "optional": True, "description": "Slug of an existing location"},
        "time_of_day": {"type": "string", "default": "", "optional": True, "description": "One of: DAY, NIGHT, DUSK, DAWN, CONTINUOUS, LATER"},
        "characters": {"type": "list", "default": [], "optional": True, "description": "Character slugs present in this scene"},
        "no_cast": {"type": "boolean", "default": False, "optional": True, "description": "Set true when this scene deliberately has no characters (e.g. an empty room). Clears the 'characters unfilled' gap so a decision is not flagged forever"},
        "one_sentence": {"type": "string", "default": "", "optional": True, "description": "One-sentence summary of the scene"},
        # The driver's immediate desire, written on the scene as the reasoning
        # behind it and on `scene_beats` as the mechanism's first step. The two
        # keep identical names and are allowed to drift: reconciling them is the
        # author's job after reworking `scene_beats`, not the reader's.
        "scene_objective": {"type": "string", "default": "", "optional": True, "description": "The driver's immediate desire. One sentence."},
        # Read from this scene's scene_beats, which is another entity and so has
        # nothing in this row's `extra` to read. `scene_beats` is the POINTER to
        # that record — a slug, not the record — because the id cannot be derived
        # from the scene id: it is caller-supplied, and the skill teaches
        # `{scene_id}-beats` as the convention. The full record is read with
        # `story_retrieve` on `scene_beats` and this id, which is what keeps the
        # base `story_load` map from growing with every beat. `ref` is
        # declaration only: the field is computed, so no write path ever carries
        # it into `check_references`.
        "turning_point": {"type": "string", "default": "", "optional": True, "computed": True, "description": "The moment of the major gap, read from this scene's scene_beats (read-only)"},
        "scene_beats": {"type": "string", "default": "", "optional": True, "computed": True, "ref": "scene_beats", "description": "Slug of this scene's scene_beats record (read-only). Read the record itself with story_retrieve on scene_beats and this id. Empty when the scene has none."},
        "dramatic_role": {"type": "string", "default": "", "optional": True, "description": "How this scene functions dramatically. One of: plot_role, transition, non-event. 'plot_role' (or empty) means the role is defined per plot in plot_roles — do NOT repeat it here. 'transition' and 'non-event' are the only values that serve no plot, and they are mutually exclusive with plot_roles: setting one requires plot_roles to be empty."},
        # The write side of a plot role. Every entry names its own plot, so one
        # scene can hold different roles in different plots — which is why the
        # role cannot live on the scene alone. Stored as `plot_<role>` rows
        # pointing AT this scene; the plot's five fields read them back.
        "plot_roles": {
            "type": "list", "default": [], "optional": True,
            "description": "Which plots run through this scene, and in what role. One entry per plot. This is where a plot role is written — never on the plot itself.",
            "sub_fields": {
                "plot": {"type": "string", "description": "Slug of an existing plot", "required": True, "ref": "plot"},
                "role": {"type": "string", "description": "One of: setup, inciting_incident, complication, crisis, climax, resolution", "required": True, "enum": PLOT_ROLES},
                "description": {"type": "string", "description": "What this scene does for that plot"},
            },
        },
        # The value pass, recorded after the scene exists: one entry per
        # shift of a value, with its effects on the protagonists nested
        # inside. A scene is created without it; the value pass fills it in
        # later by editing the scene. `value` names an existing value entity
        # (create it first with story_draft — it can go in the same draft);
        # `from`/`to` are words of THAT value's four rungs. A value has one
        # schema wherever it is used, so there is nothing to define here. See
        # VALUE_LADDER and CONFLICT_LEVELS.
        "value_turns": {"type": "list", "default": [], "optional": True,
                        "description": "Value turns recorded on this scene. Each entry is one shift of a value, with its effects on the protagonists.",
                        "sub_fields": {
                            "plot": {"type": "string", "required": True, "ref": "plot", "description": "Slug of an existing plot"},
                            "value": {"type": "string", "required": True, "description": "The name of an existing value entity — the value, named by its positive pole (e.g. 'trust')"},
                            "from": {"type": "string", "required": True, "description": "The state when the scene opens, as a word of that value's four rungs"},
                            "to": {"type": "string", "required": True, "description": "The state when the scene closes, as a word of that value's four rungs"},
                            "effects": {"type": "list", "required": True, "description": "The outcome of the value shift for a plot protagonist, by conflict level",
                                        "sub_fields": {
                                            "character": {"type": "string", "required": True, "ref": "character", "description": "A protagonist of the plot, whether or not present in the scene"},
                                            "levels": {"type": "list", "required": True, "description": "One entry per conflict level through which the shift reaches that character",
                                                       "sub_fields": {
                                                           "conflict_level": {"type": "string", "required": True, "enum": CONFLICT_LEVELS, "description": "Where the opposition comes from, relative to that character"},
                                                           "effect": {"type": "string", "required": True, "description": "One sentence: what the shift does to that character at that level"},
                                                       }},
                                        }},
                        }},
    },
    "sequence": {
        "type": {"type": "string", "default": "sequence", "optional": False, "description": "Always 'sequence'"},
        "title": {"type": "string", "default": "", "optional": False, "description": "Display name"},
        "order": {"type": "number", "default": 0, "optional": False, "description": "Position within parent act (float for insertions)"},
        "status": {"type": "string", "default": "planned", "optional": False, "description": "One of: planned, in-progress, complete"},
        "act_id": {"type": "string", "default": "", "optional": False, "description": "Parent act slug"},
        "primary_plot": {"type": "string", "default": "", "optional": True, "description": "Primary plot slug this sequence serves"},
        "value_focus": {"type": "object", "keyed": False, "default": {"major": [], "minor": []}, "optional": True, "computed": True,
                        "description": "Computed: the values that shift in this sequence's scenes, all plots together, as {major: [{value, scenes}], minor: [{value, scenes}]}. Major is the most frequent, ties at the cut all major (VALUE_MAJOR_COUNT); scenes counts the scenes in which the value shifts. Read-only — derived from the scenes' value_turns.",
                        "sub_fields": {
                            "major": {"type": "list", "description": "The most frequent values in this unit, at most VALUE_MAJOR_COUNT, with ties at the cut included",
                                      "sub_fields": {"value": {"type": "string", "description": "The value's name"}, "scenes": {"type": "number", "description": "Scenes in which the value shifts"}}},
                            "minor": {"type": "list", "description": "The remaining values, by frequency",
                                      "sub_fields": {"value": {"type": "string", "description": "The value's name"}, "scenes": {"type": "number", "description": "Scenes in which the value shifts"}}},
                        }},
        "purpose": {"type": "string", "default": "", "optional": True, "description": "Free text: dramatic purpose of this sequence"},
    },
    "act": {
        "type": {"type": "string", "default": "act", "optional": False, "description": "Always 'act'"},
        "title": {"type": "string", "default": "", "optional": False, "description": "Display name. Use 'Act I', 'Act II', 'Act III', etc."},
        "order": {"type": "number", "default": 0, "optional": False, "description": "Position within story (float for insertions)"},
        "status": {"type": "string", "default": "planned", "optional": False, "description": "One of: planned, in-progress, complete"},
        "act_objective": {"type": "string", "default": "", "label": "Objective", "optional": True, "description": "Protagonist's immediate goal for this act"},
        "value_focus": {"type": "object", "keyed": False, "default": {"major": [], "minor": []}, "optional": True, "computed": True,
                        "description": "Computed: the values that shift in this act's scenes, as {major: [{value, scenes}], minor: [{value, scenes}]}. Major is the most frequent, ties at the cut all major (VALUE_MAJOR_COUNT); scenes counts the scenes in which the value shifts. Read-only — derived from the scenes' value_turns.",
                        "sub_fields": {
                            "major": {"type": "list", "description": "The most frequent values in this unit, at most VALUE_MAJOR_COUNT, with ties at the cut included",
                                      "sub_fields": {"value": {"type": "string", "description": "The value's name"}, "scenes": {"type": "number", "description": "Scenes in which the value shifts"}}},
                            "minor": {"type": "list", "description": "The remaining values, by frequency",
                                      "sub_fields": {"value": {"type": "string", "description": "The value's name"}, "scenes": {"type": "number", "description": "Scenes in which the value shifts"}}},
                        }},
    },

    "scene_beats": {
        "scene": {"type": "string", "default": "", "optional": False, "description": "Slug of an existing scene", "ref": "scene"},
        "driver": {"type": "string", "default": "", "optional": True, "description": "Slug of the character who drives the scene", "ref": "character"},
        "scene_objective": {"type": "string", "default": "", "optional": True, "description": "The driver's immediate desire. One sentence."},
        "turning_point": {"type": "string", "default": "", "optional": True, "description": "The moment of the major gap, read from how the beats relate. One sentence. Surfaces on the scene as a computed field."},
        # A true choice is a dilemma; it is where true character shows. The
        # source gives no count per scene, so the list holds none, one or
        # several, and most scenes hold none. `character` may differ from
        # `driver`: in an ultimatum one character drives and another chooses.
        "true_character": {
            "type": "list", "default": [], "optional": True,
            "description": "True-character moments: the choices that reveal who the character is. None, one or several.",
            "sub_fields": {
                "character": {"type": "string", "required": True, "ref": "character", "description": "Slug of the character who faces the choice — may differ from the driver"},
                "dilemma": {"type": "string", "description": "The alternatives and what choosing costs: irreconcilable goods, or the lesser of two evils"},
                "choice_reveals": {"type": "string", "description": "What the choice shows about who the character is"},
            },
        },
        # The beats of action and reaction. Each side carries its own `by`,
        # because "the same character on both sides means inner conflict" is a
        # real, checkable fact and needs two `by` fields to express it — the
        # flattened reading of the design's diagram could not.
        # `by` and `changes[].entity` name three and four types respectively,
        # which no single `ref` value can express; validate_beat_references
        # resolves both.
        "beats": {
            "type": "list", "default": [], "optional": True,
            "description": "Ordered beats of action and reaction. A beat with no gap, risk, changes, surface or subtext is mere activity, not action.",
            "sub_fields": {
                "action": {"type": "object", "description": "The acting side of the beat",
                           "sub_fields": {
                               "by": {"type": "string", "description": "Slug of a character, location or world that acts"},
                               "surface": {"type": "string", "description": "What is shown or said"},
                               "subtext": {"type": "string", "description": "The underlying action, as an active gerund phrase"},
                           }},
                "reaction": {"type": "object", "description": "The reacting side of the beat",
                             "sub_fields": {
                                 "by": {"type": "string", "description": "Slug of a character, location or world that reacts"},
                                 "surface": {"type": "string", "description": "What is shown or said"},
                                 "subtext": {"type": "string", "description": "The underlying action, as an active gerund phrase"},
                             }},
                "gap": {"type": "string", "description": "What the character expected and what came back. One sentence. Empty when the beat is mere activity."},
                "risk": {"type": "string", "description": "What the character now stands to lose, carried into the next action. One sentence."},
                "changes": {"type": "list", "description": "What this exchange changed, for anyone or anything",
                            "sub_fields": {
                                "entity": {"type": "string", "description": "Slug of a character, relationship, location or world"},
                                "change": {"type": "string", "description": "One sentence: what this exchange changed for that entity"},
                            }},
            },
        },
    },
    "relationship": {
        "name": {"type": "string", "default": "", "optional": False, "description": "Display name (e.g. 'Kael & Mira')"},
        "type": {"type": "string", "default": "relationship", "optional": False, "description": "Always 'relationship'"},
        "characters": {"type": "list", "default": [], "optional": False, "description": "Exactly two character slugs"},
        "perspectives": {"type": "object", "default": {}, "optional": True, "description": "Per-character relationship view", "keyed": True, "sub_fields": {
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
    # One value, shared by every plot that uses it. The four rungs are
    # VALUE_LADDER, and a value names itself by its positive pole — the id is
    # the slug of `name`, which is what makes a scene's turn able to name it.
    "value": {
        "name": {"type": "string", "default": "", "optional": False,
                 "description": "The value, named by its positive pole (e.g. 'trust'). The id is the slug of this name."},
        "p": {"type": "string", "default": "", "optional": False,
              "description": "Positive: the story's word for the ideal (rung p)."},
        "c": {"type": "string", "default": "", "optional": False,
              "description": "Contrary: the story's word for the opposite, not absolute negation (rung c)."},
        "cd": {"type": "string", "default": "", "optional": False,
               "description": "Contradictory: the story's word for the direct negation of the positive (rung cd)."},
        "nn": {"type": "string", "default": "", "optional": False,
               "description": "Negation of negation: the story's word for the perversion or false version of the positive (rung nn)."},
        "note": {"type": "string", "default": "", "optional": True,
                 "description": "Optional: what this value means."},
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
# values — 10 false findings on a minimal character, plot or project.
# Nothing was ever stored in them: both real databases hold zero. The prose was
# never carrying information either, because `story_retrieve` reports unfilled
# fields *by name* through `unfilled_fields`.
UNFILLED = "N.A."

# ─── Required fields ───
# Derived from ENTITY_SCHEMAS rather than maintained beside it. Three notes on
# the rule:
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
