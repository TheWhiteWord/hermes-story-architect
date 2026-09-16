---
name: story-editor
description: "Edit story entities and memory with review loop."
version: 0.2.0
author: TWW, Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [story, editing, action, protocol]
    related_skills: [story-loader]
---

# Story Editor Skill

Edits story entities and memory through a review loop. Every edit
is proposed, reviewed for continuity, and applied only on explicit approval.

**Content model:** Scenes are individual files with `## Content` sections holding
Fountain text. The dashboard assembles the screenplay view from scenes in
sequence. To change scene content, use `edit_note` with `data: {Content: "..."}`.

## When to Use

- "Change Mara's voice to..."
- "Add a new character named..."
- "Delete the kitchen location"
- "Update scene 7"
- "Refresh story memory"

Don't use for: loading projects (use story-loader), simple questions (use answer).

## Prerequisites

- Project loaded (story_loader skill)
- Index in context
- Relevant sections retrieved (story_retrieve)

## Tools Available

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `story_load` | Load project index, memory, and dramatic metadata | `project` |
| `story_retrieve` | Get specific sections from a note | `entity_type`, `slug`, `sections` |
| `story_edit` | Propose and apply edits | `action`, `target`, `data`, `order_context`, `summary` |
| `story_create` | Create new entity notes | `entity_type`, `slug`, `frontmatter` |
| `story_index` | Regenerate the project index | `project` |
| `story_search` | Search across all project notes | `query` |
| `story_dashboard` | Open the dashboard in preview | `project` |

### story_edit Actions

| Action | What it does |
|--------|--------------|
| `edit_note` | Edit an entity note using `data` bag (frontmatter fields + body sections) |
| `delete_entity` | Move entity to `_recycle-bin/` (blocks if structural types have children) |
| `update_story_memory` | Update `.story/memory.md` using `data` bag |
| `reorder` | Reorder scenes/sequences — batch renumber `order` fields by providing complete new ordering |

### story_edit Data Shape

For `edit_note` and `update_story_memory`, use the simplified `data` bag:

- **Key name** determines routing: if the key matches a schema field → frontmatter update. If it matches a standard section name → body section update via `replace_section()`.

For `reorder`, provide `order_context`:
- `ordered_ids`: complete list of scene/sequence slugs in the desired order. Handler renumbers `order` fields as 1, 2, 3... All items must exist and belong to the same parent.

## Procedure

1. **Understand** — what entity, what change
2. **Load context** — if not already loaded:
   - Call `story_load` with `project` — this returns the full index (navigation + dramatic metadata) and memory
3. **Retrieve** — get relevant sections via `story_retrieve`
4. **Formulate** — build the edit (action type + changes + continuity checks)
5. **Present** — show the proposed edit in chat, wait for approval
6. **Apply** — call `story_edit` on approval
7. **Index** — call `story_index` to regenerate the index
8. **Confirm** — report what changed

## Entity Creation

When creating entities, `story_create` auto-fills all expected fields with schema
defaults. A character with only `name` still gets `relationships`, `goals_short`, etc.

For structural types, additional rules apply:
- **Parent validation**: scenes require `sequence_id` (sequence must exist) and `act_id` (act must exist). Sequences require `act_id`.
- **Auto-order**: if `order` is omitted or 0, the next available position in the parent is assigned automatically.

**Required fields** (must be filled for a valid note):
- `project`: `name` (only required field; `logline`, `genre`, etc. are optional)
- `character`: `name`, `story_role`, `one_sentence`
- `location`: `name`, `one_sentence`
- `world`: `name`, `one_sentence`
- `plot`: `name`, `status`
- `scene`: `title`, `sequence_id`, `act_id`
- `sequence`: `title`, `act_id`
- `act`: `title`

**Default values:** Core project fields like `logline`, `genre`, `setting`, `spine`, `value`, `value_at_open`, `value_at_close`, `structure_type` default to `"not set"`. Title page fields default to `""`.

The tool schema documents each field's type and description. Load
`references/index-format.md` only if you need:
- The full field list for an entity type
- Sub-field structure (plot setups/payoffs use `{scene_id, description}`)
- To distinguish **frontmatter** (LLM-editable) vs **code** (derived) fields

For dramatic metadata (value arcs, dramatic roles, conflict levels, climax flags),
see `references/index-format.md`.

### Entity Creation (Required Fields)

| Entity | Required Fields |
|--------|----------------|
| Project | `name` |
| Scene | `title`, `sequence_id`, `act_id` |
| Sequence | `title`, `act_id` |
| Act | `title` |

### Entity Quick Reference

| Entity | Key Frontmatter Fields |
| --- | --- |
| Project | `name`, `logline`, `genre`, `setting`, `status`, `structure_type`, `spine`, `value`, `value_at_open`, `value_at_close` |
| Character | `name`, `story_role`, `one_sentence`, `relationships` ({id, label, feeling}), `goals_short`, `goals_long`, `knowledge` |
| Location | `name`, `one_sentence` |
| World | `name`, `one_sentence`, `rules` |
| Plot | `name`, `status`, `setups` ({scene_id, description}), `payoffs` ({scene_id, description}), `characters`, `one_sentence` |
| Scene | `id` (dramatic-function slug, e.g. `mara-discovers-files`), `title` (display name), `order`, `status`, `sequence_id`, `act_id`, `characters`, `plots` |
| Sequence | `id`, `title`, `order`, `status`, `act_id`, `climax_scene_id` |
| Act | `id`, `title`, `order`, `status`, `climax_scene_id` |

## Continuity Checks

Before applying edits, self-audit against: character knowledge, timeline,
location, world rules, voice, setups/payoffs.

For categories and examples, see `references/continuity-checks.md`.

## Pitfalls

- Editing without retrieving relevant sections first
- Applying without approval
- Forgetting to update index after edit
- Deleting instead of moving to recycle bin
- Deleting a sequence that has scenes → blocked by cascade check
- Deleting an act that has sequences → blocked by cascade check

## Verification

- Confirm: "Applied: <summary of changes>"
- Cross-check: index updated, entity still validates
