Right now we have two separate issues with the draft card.

## AGENT EMITS DRAFT SUMMARY IN CHAT
The first issue is that the agent emist alos a summary in chat of the draft in markdown, which is unecessary since we automatically render the draft card.

We may need to refine the descriptions in the draft tool to avoid this duplication. The draft card should be the primary representation of the draft.
The agent should eb aware that:
- The draft card is already being rendered in the chat, so it should not emit a summary of the draft in markdown.
- It can still emit a comment or other information about the draft outside the card.

FILE: src/story_architect/tools/story_draft.py
```py
SCHEMA = {
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
                           "sorts them into create, edit, delete, reorder itself. Relations "
                           "such as a scene's characters ride INSIDE frontmatter, there is no "
                           "separate relations key. Staging again with the same draft_id "
                           "REPLACES the proposal, and the response says what was added, "
                           "dropped or changed.",
            "items": _op_schemas(),
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
```

We can also than consider to modify the bootstrap message to the agent as the tool description is already delivering the information about the draft card and how it should be used. The bootstrap message can be simplified to avoid redundancy:

FILE: src/story_architect/chat/context.py

``` py
def build_bootstrap(project_slug: str, project_name: str, attachments: list | None = None) -> str:
    attachments = attachments or []
    parts = [
        "You are working inside Story Architect, a local screenwriting and story-development app. "
        f'The user has the project "{project_name}" ({project_slug}) open in the app and is talking to you in its side panel. '
        'Read and change the project only through the story tools (MCP server "story"); don\'t guess project facts. '
        "Propose changes by staging a draft: the app shows each draft to the user as a card with Approve and Reject buttons. "
        "Commit only after the user approves (you will be told), unless they explicitly ask you to apply changes directly. "
        "Never claim a change was made unless a tool confirmed it. Use dashboard_link when pointing the user at a place in the app.",
    ]
    if attachments:
        labels = ", ".join(f"{a.get('kind', '')}:{a.get('id', '')} ({a.get('label', '')})" for a in attachments)
        parts.append(f"The user attached these parts of the app to their message: {labels}. Use the tools to read them if relevant.")
    return " ".join(parts)
```

## DRAFT CARD RENDERING IN CHAT
The second issue is that the draft card is not rendering all the data that the agent can provide in a draft. The draft card should be the primary representation of the draft, and it should include all relevant information.

Below is an example of this from a live test. Note, i have kept the tool_describe request and response from the agent as context of what the agent is sending to the backend, and what the backend is sending to the frontend. The draft card should be able to render all of this information.

```json

//Here agent calls tool_describe to get the schema for the character entity type
event: tool
data: {"type": "tool", "id": "call-d1c2cda8-3439-401b-a3ce-675f02e05403", "name": "mcp__story__describe", "status": "started", "label": "mcp__story__describe"}

event: tool
data: {"type": "tool", "id": "ef73a13624c841cdbe610a5cff2b153c", "name": "describe", "status": "started", "args": {"entity_type": "character"}, "result_preview": null, "duration_ms": null}

event: tool
data: {"type": "tool", "id": "ef73a13624c841cdbe610a5cff2b153c", "name": "describe", "status": "finished", "args": null, "result_preview": "{\"success\": true, \"entity_schemas\": {\"character\": {\"name\": {\"type\": \"string\", \"default\": \"\", \"optional\": false, \"description\": \"Character display name\"}, \"story_role\": {\"type\": \"string\", \"default\": \"\", \"optional\": false, \"description\": \"One of: Protagonist, Antagonist, Supporting, Minor, Cameo\"}, \"one_sentence\": {\"type\": \"string\", \"default\": \"\", \"optional\": false, \"description\": \"One-sentence summary for index label\"}, \"goals_short\": {\"type\": \"string\", \"default\": \"\", \"optional\": true, \"description\": \"Short-term goal\"}, \"goals_long\": {\"type\": \"string\", \"default\": \"\", \"optional\": true, \"description\": \"Long-term goal\"}, \"knowledge\": {\"type\": \"list\", \"default\": [], \"optional\": true, \"description\": \"Facts the character knows. Each entry is a string.\"}, \"relationships\": {\"type\": \"list\", \"default", "duration_ms": 0}

event: tool
data: {"type": "tool", "id": "call-d1c2cda8-3439-401b-a3ce-675f02e05403", "name": "mcp__story__describe", "status": "finished", "label": null}


//Here agent calls the draft tool to stage a new character entity
event: tool
data: {"type": "tool", "id": "call-b821993e-e855-4c50-af72-71776b2171f1", "name": "mcp__story__draft", "status": "started", "label": "mcp__story__draft"}

event: tool
data: {"type": "tool", "id": "599313928d504bacb50be11cddbf582d", "name": "draft", "status": "started", "args": {"action": "stage", "ops": [{"frontmatter": {"goals_long": "Find out who he is if Kael's world turns out to be a lie.", "goals_short": "Stay close to Kael; keep things simple.", "name": "Lio", "one_sentence": "Kael's childhood companion \u2014 the one person whose trust Kael is afraid of losing.", "story_role": "Supporting"}, "id": "lio", "op": "create", "sections": {"Arc": "From follower to someone who must decide for himself whether Kael's doubt is worth following.", "Background": "Grew up alongside Kael in the Institute. No memory of parents; the Institute is the only home he knows.", "Contradictions": "Loyal to Kael but also believes the Institute; if those conflict, he freezes rather than chooses.", "Desires": "Wants Kael's approval and a stable, simple world. Fears being left behind more than being deceived.", "Identity": "A child of the Institute, a few years younger than Kael. Quiet, watchful, physically small. Has been Kael's shadow since they were small.", "Notes": "Side companion for Kael; intended to ground Kael's stakes in a person, not an idea.", "Psychology": "Attachment-first; reads people by proximity and tone. Avoids abstraction.", "Relationships": "Kael: best friend and older sibling figure. Mira: wary of her, senses she pulls Kael away.", "Voice": "Short sentences, concrete words, questions instead of statements."}, "summary": "Create character Lio", "type": "character"}], "project": "Save the Children", "summary": "Add Lio \u2014 Kael's childhood side companion"}, "result_preview": null, "duration_ms": null}

event: tool
data: {"type": "tool", "id": "599313928d504bacb50be11cddbf582d", "name": "draft", "status": "finished", "args": null, "result_preview": "{\"success\": true, \"draft_id\": \"d-20261031-124809\", \"op_count\": 1, \"preview_md\": \"### \\ud83d\\udcdd Draft `d-20261031-124809` \\u2014 *Add Lio \\u2014 Kael's childhood side companion*\\n\\n**Save the Children** \\u00b7 1 change\\n\\n---\\n\\n**\\uff0b NEW CHARACTER** \\u00b7 `character/lio`  \\u00b7  5 of 6 fields set\\n\\n| field | value |\\n|---|---|\\n| goals_long | Find out who he is if Kael's world turns out to be a lie. |\\n| goals_short | Stay close to Kael; keep things simple. |\\n| name | Lio |\\n| one_sentence | Kael's childhood companion \\u2014 the one person whose trust Kael is afraid of losing. |\\n| story_role | Supporting |\\n\\n**Arc**\\n```text\\nFrom follower to someone who must decide for himself whether Kael's doubt is worth following.\\n```\\n\\n**Background**\\n```text\\nGrew up alongside Kael in t", "duration_ms": 14}


//Here the backend emits an event to the frontend with the draft summary and details
event: draft
data: {"type": "draft", "draft": {"id": "d-20261031-124809", "status": "open", "summary": "Add Lio \u2014 Kael's childhood side companion", "created_at": "2026-10-31T12:48:09", "changes": [{"kind": "create", "entity_type": "character", "entity_id": "lio", "summary": "Create character Lio", "fields": [{"field": "goals_long", "before": null, "after": "Find out who he is if Kael's world turns out to be a lie."}, {"field": "goals_short", "before": null, "after": "Stay close to Kael; keep things simple."}, {"field": "name", "before": null, "after": "Lio"}, {"field": "one_sentence", "before": null, "after": "Kael's childhood companion \u2014 the one person whose trust Kael is afraid of losing."}, {"field": "story_role", "before": null, "after": "Supporting"}]}], "warnings": []}}
```

As you can see, in the draft card , in this specific instance we are not rendering all the sections.

We need to ensure that the draft card can render all the relevant information provided by the agent, including all fields and sections of the entity being drafted if they are available. This will provide a complete and accurate representation of the draft for the user.
This has to be done in a way that is flexible and can accommodate different entity types and their respective fields and sections, as the agent may provide different data depending on the context of the draft.

Also we should make sure to consider the cases of edit, delete, and reorder operations in the draft card rendering, as these may have different requirements for how the information is displayed to the user.

RELEVANT FILES:
- src/story_architect/chat/chat_render.js
- src/story_architect/chat/chat_app.js
- src/story_architect/core/drafts.py