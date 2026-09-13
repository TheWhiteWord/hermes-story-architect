---
name: story-editor
description: "Edit story entities, screenplay, and memory with review loop."
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

Edits story entities, screenplay, and memory through a review loop. Every edit
is proposed, reviewed for continuity, and applied only on explicit approval.

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
| `story_retrieve` | Get specific sections from a note | `entity_type`, `slug`, `sections` (list of section names, or `['all']`) |
| `story_edit` | Propose and apply edits | `action`, `target`, `data`, `order_context`, `summary` |
| `story_create` | Create new entity notes | `entity_type`, `slug`, `frontmatter` |
| `story_index` | Regenerate the project index | `project` |
| `story_search` | Search across all project notes | `query` |
| `story_dashboard` | Open the dashboard in preview | `project` |

### story_edit Actions

| Action | What it does |
|--------|--------------|
| `edit_note` | Edit an entity note using `data` bag (frontmatter fields + body sections) |
| `edit_screenplay` | Edit the screenplay.fountain file |
| `create_entity` | Create a new entity note — works for all entity types |
| `delete_entity` | Move entity to `_recycle-bin/` (blocks if structural types have children) |
| `update_story_memory` | Update `.story/memory.md` using `data` bag |
| `reorder` | Reorder scenes/sequences — batch renumber `order` fields by providing complete new ordering |

### story_edit Data Shape

For `edit_note` and `update_story_memory`, use the simplified `data` bag:

- **Key name** determines routing: if the key matches a schema field → frontmatter update. If it matches a standard section name → body section update via `replace_section()`.
- No `type` discriminator needed (old `changes` array with `type: "body_section"|"frontmatter"` is deprecated).

For `reorder`, provide `order_context`:
- `ordered_ids`: complete list of scene/sequence slugs in the desired order. Handler renumbers `order` fields as 1, 2, 3... All items must exist and belong to the same parent.

## Procedure

1. **Understand** — what entity, what change
2. **Retrieve** — get relevant sections via `story_retrieve`
3. **Formulate** — build the edit (action type + changes + continuity checks)
4. **Present** — show the proposed edit in chat, wait for approval
5. **Apply** — call `story_edit` on approval
6. **Index** — call `story_index` to regenerate the index
7. **Confirm** — report what changed

## Entity Creation

When creating entities, `story_create` auto-fills all expected fields with empty
defaults. A character with only `name` still gets `relationships`, `goals_short`, etc.

For structural types, additional rules apply:
- **Parent validation**: scenes require `sequence_id` (sequence must exist) and `act_id` (act must exist). Sequences require `act_id`.
- **Auto-order**: if `order` is omitted or 0, the next available position in the parent is assigned automatically.

**Required fields** (should be filled for a useful note):
- `name` — display name for the entity
- `story_role` (character) — role in the story (Protagonist/Antagonist/Supporting/Minor/Cameo)
- `one_sentence` — one-line summary for index labels
- `status` (plot/project) — defaults to `active` if omitted

**Optional fields** (can be filled as the story develops):
- `relationships`, `goals_short`, `goals_long`, `knowledge` (character)
- `rules` (world)
- `setups`, `payoffs`, `characters`, `status` (plot)
- `genre`, `setting`, `status` (project)

The tool schema documents each field's type and description. Load
`references/index-format.md` only if you need:
- The full field list for an entity type
- Sub-field structure (plot setups/payoffs use `{scene_id, description}`)
- To distinguish **frontmatter** (LLM-editable) vs **code** (derived) fields

### Entity Creation (Required Fields)

| Entity | Required Fields |
|--------|-----------------|
| Scene | `title`, `sequence_id`, `act_id` |
| Sequence | `title`, `act_id` |
| Act | `title` |

### Entity Quick Reference

| Entity | Key Frontmatter Fields |
| --- | --- |
| Character | `name`, `story_role`, `one_sentence`, `relationships` ({id, label, feeling}), `goals_short`, `goals_long`, `knowledge` |
| Location | `name`, `one_sentence` |
| World | `name`, `one_sentence`, `rules` |
| Plot | `name`, `status`, `setups` ({scene_id, description}), `payoffs` ({scene_id, description}), `characters`, `one_sentence` |
| Scene | `id`, `title`, `order`, `status`, `sequence_id`, `act_id`, `characters`, `plots` |
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
