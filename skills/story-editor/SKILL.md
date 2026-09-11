---
name: story-editor
description: "Edit story entities, screenplay, and memory with review loop."
version: 0.1.0
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

## Creating a New Project

Same as story-loader: create folder + run `story_index`. Then use `story_create` for entities.

## Entity Frontmatter

When creating or editing entities, `story_create` auto-fills all expected fields with empty
defaults — so a new character with only `name` still gets `relationships`, `goals_short`, etc.

Load `references/index-format.md` when you need:
- The full list of fields for an entity type
- Sub-field structure (e.g. plot setups/payoffs use `{heading, number, description}`)
- To understand which fields are **frontmatter** (LLM-editable) vs **code** (derived)

### Quick Reference
| Entity | Key Frontmatter Fields |
| --- | --- |
| Character | `name`, `story_role`, `one_sentence`, `relationships` ({id, label, feeling}), `goals_short`, `goals_long`, `knowledge` |
| Location | `name`, `one_sentence` |
| World | `name`, `one_sentence`, `rules` |
| Plot | `name`, `status`, `setups` ({heading, number, description}), `payoffs` ({heading, number, description}), `characters`, `one_sentence` |
## Quick Reference
| Action | Tool | Core Module |
|--------|------|-------------|
| Edit entity | story_edit (action: edit_note) | section_parser, entity |
| Edit screenplay | story_edit (action: edit_screenplay) | screenplay (Parser/Writer) |
| Create entity | story_create | entity, frontmatter |
| Delete entity | story_edit (action: delete_entity) | entity |
| Update memory | story_edit (action: update_story_memory) | screenplay, entity |

## Procedure

1. Understand the request (what entity, what change)
2. Retrieve relevant sections (story_retrieve)
3. Formulate proposal (action type + changes + continuity checks)
4. Present for approval (formatted in chat)
5. On approval: apply edit via core modules
6. Update index (story_index)
7. Confirm changes to user

## Action Types

Five action types: edit_note, edit_screenplay, create_entity, delete_entity, update_story_memory.

For detailed procedures, see `references/action-types.md`.

## Fountain Format

When writing or editing screenplays, follow Fountain syntax conventions so
the screenplay parses correctly and renders properly in the dashboard.

For complete formatting rules, see `references/screenplay-format.md`.

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
