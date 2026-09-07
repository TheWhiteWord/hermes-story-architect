# Task 5: Action Protocol — FINAL DECISIONS

> All subtasks resolved. This is the authoritative record of decisions made.

---

## Status: RESOLVED

| Subtask | Status |
|---------|--------|
| 01_action_protocol.md | RESOLVED |
| 02_skill_structure.md | RESOLVED |

---

## 1. Action Type Taxonomy (7 types)

| Action | Description | Target |
|--------|-------------|--------|
| `edit_note` | Edit any entity note (frontmatter + body) | characters/, locations/, worlds/, plots/, project.md |
| `edit_screenplay` | Add/replace/delete screenplay content | screenplay.md |
| `create_entity` | Create new character/location/world/plot | characters/, locations/, worlds/, plots/ |
| `delete_entity` | Move entity to _recycle-bin/ | any entity type |
| `update_story_memory` | Regenerate Story Memory | .story/memory.md |
| `answer` | Read-only conversational response | — |
| `suggest_ideas` | Brainstorm possibilities | — |

**Why 7, not 18 (STARC)**: Enough for targeted skill instructions without near-duplicates. `edit_note` covers all entity editing (character/location/world/plot), `edit_screenplay` covers all screenplay edits.

---

## 2. Proposal Format

```json
{
  "action": "edit_note",
  "target": {"entity_type": "character", "slug": "mara"},
  "changes": [
    {
      "type": "body_section",
      "section": "Voice",
      "old": "Precise, clinical.",
      "new": "Precise, clinical. Speaks in fragments when angry."
    }
  ],
  "summary": "Add speech pattern under stress to Mara's Voice.",
  "continuity_checks": [
    {
      "severity": "suggestion",
      "category": "voice",
      "finding": "Adding 'fragments when angry' creates contrast — consider if this fits.",
      "evidence": "## Personality: Avoids conflict until cornered."
    }
  ],
  "requires_approval": true
}
```

---

## 3. Review Loop

```
1. User request
2. Hermes retrieves relevant sections (story_retrieve)
3. Hermes formulates proposal (action + changes + continuity checks)
4. Proposal presented in chat
5. User: "Approve" / "reject" / "modify: ..."
6. On approve: apply edit → update index → confirm
```

---

## 4. Continuity Checks

LLM self-audit against:
- Character knowledge
- Timeline/chronology
- Location consistency
- World rules
- Voice consistency
- Setups/payoffs

Returned as part of proposal. User reviews before approving.

---

## 5. Skill Structure

```
plugin/skills/story-editor/
├── SKILL.md                        # main skill file
└── references/
    ├── action-types.md             # detailed action procedures
    └── continuity-checks.md        # check categories + examples
```

---

## What happens next

1. Implement `plugin/skills/story-editor/SKILL.md`
2. Implement `plugin/skills/story-editor/references/action-types.md`
3. Implement `plugin/skills/story-editor/references/continuity-checks.md`
4. Implement `plugin/tools/story_edit.py` (tool handler)
5. Implement `plugin/tools/story_create.py` (tool handler)
6. Test with a real project
7. Proceed to **Task 6 (Dashboard)**
