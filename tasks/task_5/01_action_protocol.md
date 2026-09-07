# Subtask: Action Protocol Design — RESOLVED

> Define the action types, proposal format, and review loop. References: `task_1/04_decisions.md §5` (entity schemas), `task_2/04_decisions.md` (core modules).

---

## Decisions

| # | Decision | Choice | Why |
|---|----------|--------|-----|
| 1 | Action granularity | 7 specific types | Enough for targeted skill instructions without STARC's 18-action sprawl |
| 2 | Proposal format | STARC V3 simplified | Structured data + human-readable summary + continuity checks |
| 3 | Review loop | Chat message + text approval | "Approve" / "reject" / "modify" in chat — no buttons needed |
| 4 | Continuity checks | LLM self-audit | Simpler than rule-based; LLM already has full context |
| 5 | Frontmatter ↔ body sync | Auto-sync for mapped fields, ask for unmapped | Sensible default, user can override |

---

## Action Type Taxonomy

```yaml
edit_note:
  description: Edit any entity note (frontmatter + body sections)
  targets: character, location, world, plot, project
  skill_sections:
    - Frontmatter field editing (via python-frontmatter)
    - Body section editing (via replace_section)
    - Section parser: get_section for read, replace_section for write
    - Entity-specific sections: Character has Personality/Voice/Arc, Location has Description/History, etc.
    - Validation against REQUIRED_FIELDS and vocabularies

edit_screenplay:
  description: Add/replace/delete screenplay content (Fountain)
  targets: screenplay.md
  skill_sections:
    - Use screenplay-tools Parser → modify Script → Writer for round-trip
    - Scene extraction via HEADING elements
    - Character extraction via CHARACTER elements
    - Scene insertion: find scene by number, insert before/after
    - Dialogue editing: find CHARACTER element, modify following DIALOGUE

create_entity:
  description: Create new character/location/world/plot note
  targets: characters/, locations/, worlds/, plots/
  skill_sections:
    - Validate slug (unique, no special characters)
    - Generate frontmatter from template with required fields
    - Create note file with standard section headings
    - Add to index automatically
    - Character: include all standard sections (Personality, Background, Voice, etc.)
    - Location/World/Plot: include type-specific sections

delete_entity:
  description: Move entity to _recycle-bin/ (never hard delete)
  targets: characters/, locations/, worlds/, plots/
  skill_sections:
    - Move note file to _recycle-bin/<type>/<slug>.md
    - Remove from index
    - Note: screenplay prose referencing this character is NOT deleted
    - Update any plot threads referencing this entity

update_story_memory:
  description: Regenerate Story Memory from current screenplay and entities
  targets: .story/memory.md
  skill_sections:
    - Read screenplay, extract continuity data
    - Rebuild CHARACTERS & RELATIONSHIPS section
    - Rebuild CHARACTER KNOWLEDGE from character frontmatter
    - Rebuild SETUPS & PAYOFFS from plot frontmatter
    - Flag continuity risks (knowledge mismatches, timeline issues)

answer:
  description: Read-only conversational response (no edit)
  skill_sections:
    - Use retrieved sections to inform response
    - Cite sources (scene headings, character names)
    - No tool calls that modify files

suggest_ideas:
  description: Brainstorm possibilities (no edit)
  skill_sections:
    - Based on retrieved sections and story state
    - Present 3-5 options with pros/cons
    - User picks one, then use edit_note to implement
```

---

## Proposal Format (simplified STARC V3)

```json
{
  "action": "edit_note",
  "target": {
    "entity_type": "character",
    "slug": "mara"
  },
  "changes": [
    {
      "type": "body_section",
      "section": "Voice",
      "old": "Precise, clinical. Rarely uses contractions.",
      "new": "Precise, clinical. Rarely uses contractions. Speaks in fragments when angry."
    }
  ],
  "summary": "Add speech pattern under stress to Mara's Voice section.",
  "continuity_checks": [
    {
      "severity": "suggestion",
      "category": "voice",
      "finding": "Mara's voice is already 'clinical and precise'. Adding 'fragments when angry' creates contrast — consider if this fits her character.",
      "evidence": "## Personality: Avoids conflict until cornered."
    }
  ],
  "requires_approval": true
}
```

---

## Review Loop

```
1. User: "Make Mara angrier in her voice"
2. Hermes: retrieves Mara's Voice + Personality sections
3. Hermes: returns proposal (as JSON in tool result)
4. Proposal rendered in chat (formatted, readable)
5. User: "Approve" / "reject" / "modify: make it more subtle"
6. On approve: apply edit → update index → confirm
7. On reject: explain why, ask for alternative direction
8. On modify: return revised proposal
```

---

## Continuity Checks (LLM self-audit)

Before applying any edit, the LLM checks:
- **Character knowledge**: Does this contradict what a character knows?
- **Timeline**: Does this fit the chronological order?
- **Location**: Does this match the location's description/rules?
- **World rules**: Does this violate established world rules?
- **Voice**: Does this match the character's established voice?
- **Setups/payoffs**: Does this break a setup without payoff?

The LLM returns these checks as part of the proposal. User reviews them before approving.

---

## Frontmatter ↔ Body Sync

```python
# Mapped fields: editing one auto-updates the other
FRONTMATTER_BODY_MAP = {
    "one_sentence": "Personality",  # Character
    "goals.short": "Goals",
    "goals.long": "Arc",
    "status": "Summary",  # Plot
}

# When editing frontmatter field that has a mapped body section:
# → Ask: "Update body section too?" (default: yes)

# When editing body section that has a mapped frontmatter field:
# → Ask: "Update frontmatter label too?" (default: yes)
```

For unmapped fields, no sync — edit what the user asked to edit.

---

## What this means for the skill

Each action type gets its own section in `story-editor/SKILL.md` with:
- Specific procedure
- Which core modules to use (section_parser, entity, screenplay, frontmatter)
- Validation steps
- Continuity check reminders

This gives the LLM targeted instructions without 18 nearly-identical action definitions.

---

## Status: RESOLVED
