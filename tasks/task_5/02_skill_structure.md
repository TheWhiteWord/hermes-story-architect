# Subtask: Story-Editor Skill Structure — RESOLVED

> Design the skill file structure for the story-editor skill. References: `task_3/02_skill_standards.md` (skill standards), `task_5/01_action_protocol.md` (action types).

---

## Decisions

| # | Decision | Choice | Why |
|---|----------|--------|-----|
| 1 | Skill file structure | `SKILL.md` + `references/action-types.md` + `references/continuity-checks.md` | Bulk material in references, lean main file |
| 2 | Reference content | Full action procedures + continuity check categories | SKILL.md points to them, keeps main file ~150 lines |
| 3 | No scripts/ | Uses core modules | No standalone scripts needed |

---

## Final Skill Structure

```
plugin/skills/story-editor/
├── SKILL.md                        # main skill file
└── references/
    ├── action-types.md             # detailed action type procedures
    └── continuity-checks.md        # continuity check categories + examples
```

---

## SKILL.md Frontmatter

```yaml
---
name: story-editor
description: "Edit story entities, screenplay, and memory with review loop."
version: 0.1.0
author: Davide, Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [story, editing, action, protocol]
    related_skills: [story-loader]
---
```

---

## SKILL.md Body Structure

```markdown
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

- Project loaded (story_load)
- Index in context
- Relevant sections retrieved (story_retrieve)

## Quick Reference

| Action | Tool | Core Module |
|--------|------|-------------|
| Edit entity | story_edit | section_parser, entity |
| Edit screenplay | story_edit | screenplay (Parser/Writer) |
| Create entity | story_create | entity, frontmatter |
| Delete entity | story_delete | entity |
| Update memory | story_update_memory | screenplay, entity |

## Procedure

1. Understand the request (what entity, what change)
2. Retrieve relevant sections (story_retrieve)
3. Formulate proposal (action type + changes + continuity checks)
4. Present for approval (formatted in chat)
5. On approval: apply edit via core modules
6. Update index (story_index)
7. Confirm changes to user

## Action Types

Seven action types: edit_note, edit_screenplay, create_entity, delete_entity,
update_story_memory, answer, suggest_ideas.

For detailed procedures, see `references/action-types.md`.

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
```

---

## Reference: `references/action-types.md`

**Content**:
- Detailed procedure for each of the 7 action types
- Which core modules to use (section_parser, entity, screenplay, frontmatter)
- Validation steps per action type
- Example proposals per action type

---

## Reference: `references/continuity-checks.md`

**Content**:
- Categories: character_knowledge, chronology, location, world_rules, setups_payoffs, voice
- Severity levels: critical, caution, suggestion
- Example checks per category
- How to cite evidence (scene headings, character names)

---

## Status: RESOLVED
