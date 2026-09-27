"""story_draft tool — propose a batch of entity changes, write them on confirmation.

Entity work is iterative: an entity is discussed, half-formed, revised, and
only then agreed. This tool lets the agent propose the whole batch, show it,
and write nothing until the user says so — so "save it" means the user is
looking at the thing that was saved.

Per-entity staging would not work here. A new scene implies a location, two
character-appearance relations, a sequence order_key and a value_at_close:
one decision, six changes, five entities, and five confirmations.

A dedicated tool rather than a `draft` param on story_create/story_edit,
because a batch draft spans a create, an edit and a reorder — it has no valid
`target` for story_edit and no valid `action` on either. Design of record:
tasks/task_28/draft-staging-design.md.
"""
import json

SCHEMA = {
    "name": "story_draft",
    "description": "Propose a batch of entity changes, show them to the user, and write them "
                   "only when the user confirms. Use this instead of story_create / story_edit "
                   "whenever the user is still deciding — a draft is inert: staging writes one "
                   "row in the project's drafts table and nothing else. RELAY preview_md "
                   "VERBATIM to the user; it is the whole message, and it is what they are "
                   "approving — do not summarise it away. Report anything in `validation` "
                   "alongside it, and fix a finding before asking for confirmation rather "
                   "than after. Call action=\"list\" at the start of a session to find drafts "
                   "left open by a previous one. Deleting is reversible, so a delete op is a "
                   "soft delete. Projects themselves cannot be drafted — call story_create for "
                   "those.",
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
                           "sorts them. Four kinds. create: {op, type, slug, frontmatter, "
                           "sections?, summary} — relations such as a scene's characters ride "
                           "INSIDE frontmatter, there is no separate relations key. edit: {op, "
                           "entity_type, entity_id, data, summary} where data is flat "
                           "{field: value} or {Section Name: prose}. delete: {op, entity_type, "
                           "entity_id, summary} — reversible. reorder: {op, entity_type, "
                           "ordered_ids, summary} to renumber the order of scenes or sequences. "
                           "Staging again with the same draft_id REPLACES the proposal, and the "
                           "response says what was added, dropped or changed.",
            "items": {"type": "object"},
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
