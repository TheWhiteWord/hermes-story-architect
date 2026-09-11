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
| `story_edit` | Propose and apply edits | `action`, `target`, `changes`, `summary` |
| `story_create` | Create new entity notes | `entity_type`, `slug`, `frontmatter` |
| `story_index` | Regenerate the project index | `project` |
| `story_search` | Search across all project notes | `query` |
| `story_dashboard` | Open the dashboard in preview | `project` |

### story_edit Actions

| Action | What it does |
|--------|--------------|
| `edit_note` | Edit an entity note's frontmatter or body sections |
| `edit_screenplay` | Edit the screenplay.fountain file |
| `create_entity` | Create a new entity note |
| `delete_entity` | Move entity to `_recycle-bin/` |
| `update_story_memory` | Update `.story/memory.md` |

### story_edit Changes Shape

For `edit_note`, each change object has:
- `type`: `"body_section"` or `"frontmatter"`
- For `"body_section"`: `section` (name), `new` (content)
- For `"frontmatter"`: `field` (name), `value` (new value)

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

The tool schema documents each field's type and description. Load
`references/index-format.md` only if you need:
- The full field list for an entity type
- Sub-field structure (plot setups/payoffs use `{heading, number, description}`)
- To distinguish **frontmatter** (LLM-editable) vs **code** (derived) fields

### Entity Quick Reference

| Entity | Key Frontmatter Fields |
| --- | --- |
| Character | `name`, `story_role`, `one_sentence`, `relationships` ({id, label, feeling}), `goals_short`, `goals_long`, `knowledge` |
| Location | `name`, `one_sentence` |
| World | `name`, `one_sentence`, `rules` |
| Plot | `name`, `status`, `setups` ({heading, number, description}), `payoffs` ({heading, number, description}), `characters`, `one_sentence` |

## Continuity Checks

Before applying edits, self-audit against: character knowledge, timeline,
location, world rules, voice, setups/payoffs.

For categories and examples, see `references/continuity-checks.md`.

## Pitfalls

- Editing without retrieving relevant sections first
- Applying without approval
- Forgetting to update index after edit
- Deleting instead of moving to recycle bin

## Verification

- Confirm: "Applied: <summary of changes>"
- Cross-check: index updated, entity still validates
