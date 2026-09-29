"""story_draft tool — propose a batch of entity changes, write them on confirmation.

Entity work is iterative: an entity is discussed, half-formed, revised, and
only then agreed. This tool lets the agent propose the whole batch, show it,
and write nothing until the user says so — so "save it" means the user is
looking at the thing that was saved.

Per-entity staging would not work here. A new scene implies a location, two
character-appearance relations, a sequence order_key and a value_at_close:
one decision, six changes, five entities, and five confirmations.

A batch draft spans a create, an edit and a reorder at once, so it has no
single target entity and no single action — which is why staging is a tool
of its own rather than a parameter on any one write. Design of record:
tasks/task_28/draft-staging-design.md.
"""
import json

from core.constants import ENTITY_SCHEMAS
from core.drafts import OP_ORDER, REQUIRED_OP_KEYS
from core.writes import REORDERABLE_TYPES


def _op_schemas() -> list[dict]:
    """One schema branch per op kind, so the model is told the shape.

    Built from the validator's own tables rather than typed out here: the model
    has to be handed the same grammar `validate_ops` enforces, and a second
    hand-written copy of the required-key lists is exactly how the two drift
    apart. `frontmatter` and `data` stay free-form objects on purpose — their
    keys are the entity's fields, which `story_describe` reports and a JSON
    Schema cannot enumerate across ten entity types.
    """
    summary = {"type": "string", "description": "One line naming this op, shown in the preview"}
    entity = {
        "entity_type": {
            "type": "string",
            "enum": list(ENTITY_SCHEMAS),
            "description": "Type of the entity this op targets",
        },
    }
    branches = {
        "create": {
            "op": {"type": "string", "enum": ["create"]},
            "type": {
                "type": "string",
                "enum": list(ENTITY_SCHEMAS),
                "description": "Entity type to create. Projects cannot be drafted — "
                               "call story_admin(action=\"create_project\") instead.",
            },
            "id": {
                "type": "string",
                "description": "The new entity's id — the slug every other op and "
                               "every link refers to it by. Alphanumeric, hyphens "
                               "and underscores only.",
            },
            "frontmatter": {
                "type": "object",
                "description": "Field values for the entity. Relations such as a "
                               "scene's characters ride IN here, not in a separate "
                               "key. Call story_describe for the fields this type "
                               "has; omit the ones the user has not decided yet.",
            },
            "sections": {
                "type": "object",
                "description": "Optional section prose, as {Section Name: body}. "
                               "Standard headings per type are in "
                               "references/model/entity-sections.md.",
            },
            "summary": summary,
        },
        "edit": {
            "op": {"type": "string", "enum": ["edit"]},
            **entity,
            "entity_id": {"type": "string", "description": "Id of the entity to edit"},
            "data": {
                "type": "object",
                "description": "Flat {field: value} for frontmatter, and/or "
                               "{Section Name: prose} for body sections. Only the "
                               "keys that change — this is a patch, not a "
                               "replacement.",
            },
            "summary": summary,
        },
        "delete": {
            "op": {"type": "string", "enum": ["delete"]},
            **entity,
            "entity_id": {"type": "string", "description": "Id of the entity to delete"},
            "summary": summary,
        },
        "reorder": {
            "op": {"type": "string", "enum": ["reorder"]},
            "entity_type": {
                "type": "string",
                "enum": list(REORDERABLE_TYPES),
                "description": "Only these types can be reordered",
            },
            "ordered_ids": {
                "type": "array",
                "items": {"type": "string"},
                "description": "The COMPLETE new order, every id included. This "
                               "renumbers; it does not move one item.",
            },
            "summary": summary,
        },
    }
    return [
        {
            "type": "object",
            "properties": props,
            "required": ["op", *REQUIRED_OP_KEYS[kind]],
        }
        for kind, props in sorted(branches.items(), key=lambda kv: OP_ORDER[kv[0]])
    ]


SCHEMA = {
    "name": "story_draft",
    "description": "Propose a batch of entity changes, show them to the user, and write them "
                   "only when the user confirms. This is the only way to create, edit or "
                   "reorder an entity — every write goes through a draft, so use it "
                   "whenever the user is still deciding, and commit once they agree. A draft "
                   "is inert: staging writes one row in the project's drafts table and "
                   "nothing else. RELAY preview_md "
                   "VERBATIM to the user; it is the whole message, and it is what they are "
                   "approving — do not summarise it away. Report anything in `validation` "
                   "alongside it, and fix a finding before asking for confirmation rather "
                   "than after. Call action=\"list\" at the start of a session to find drafts "
                   "left open by a previous one. Deleting is reversible, so a delete op is a "
                   "soft delete. Projects themselves cannot be drafted — call "
                   "story_admin(action=\"create_project\") for those.",
    "type": "object",
    "properties": {
        "action": {
            "type": "string",
            "enum": ["stage", "commit", "discard", "list"],
            "description": "stage (propose ops and get a draft_id back — writes nothing to the "
                           "story), commit (write a staged draft; only ever call this once the "
                           "user has confirmed), discard (drop a draft; nothing it proposed was "
                           "ever written), list (every open draft in the project)",
        },
        "project": {
            "type": "string",
            "description": "Project slug or path",
        },
        "ops": {
            "type": "array",
            "description": "For action=\"stage\": the changes to propose, in any order — commit "
                           "sorts them into create, edit, delete, reorder itself. The four "
                           "kinds and their fields are in `items`. Relations such as a "
                           "scene's characters ride INSIDE frontmatter, there is no separate "
                           "relations key. Staging again with the same draft_id REPLACES the "
                           "proposal, and the response says what was added, dropped or changed.",
            "items": {"oneOf": _op_schemas()},
        },
        "draft_id": {
            "type": "string",
            "description": "For commit, discard, and re-staging: the draft to act on, as returned "
                           "by stage or list.",
        },
        "summary": {
            "type": "string",
            "description": "For action=\"stage\": one line naming the whole batch, e.g. 'Mira "
                           "tells Kael — goes badly'.",
        },
    },
    "required": ["action", "project"],
}


def handler(args: dict, **kwargs) -> str:
    from core.config import resolve_root
    from core.drafts import DraftError, commit, discard, list_drafts, stage
    from .story_resolve import resolve_project

    action = args["action"]
    project = args.get("project", "")

    try:
        project_path = resolve_project(project, resolve_root(kwargs))
    except ValueError as e:
        return json.dumps({"error": str(e)})

    try:
        if action == "stage":
            return json.dumps(stage(
                project_path,
                args.get("ops"),
                summary=args.get("summary", ""),
                draft_id=args.get("draft_id"),
            ))
        if action == "commit":
            return json.dumps(commit(project_path, args.get("draft_id", "")))
        if action == "discard":
            return json.dumps(discard(project_path, args.get("draft_id", "")))
        if action == "list":
            return json.dumps(list_drafts(project_path))
        return json.dumps({"error": f"Unknown action: {action}"})
    except DraftError as e:
        return json.dumps({"error": str(e)})
