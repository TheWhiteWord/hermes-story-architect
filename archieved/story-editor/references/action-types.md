# Action Types Reference

> Detailed procedures for each of the 7 action types.

---

## edit_note

Edit any entity note (frontmatter fields and/or body sections).

### Procedure

1. Retrieve current sections: `story_retrieve(entity_type, slug, ["all"])`
2. Identify what to change:
   - **Frontmatter field**: modify YAML field (e.g., `story_role`, `one_sentence`)
   - **Body section**: modify `##` section content (e.g., `## Voice`)
3. Check frontmatter ↔ body mapping:
   - `one_sentence` ↔ `## Personality`
   - `goals.short` ↔ `## Goals`
   - `goals.long` ↔ `## Arc`
   - `status` ↔ `## Summary` (plot)
4. Build proposal with changes array
5. Present for approval
6. On approval: apply via `story_edit`

### Example Proposal

```json
{
  "action": "edit_note",
  "target": {"entity_type": "character", "slug": "mara"},
  "changes": [
    {
      "type": "body_section",
      "section": "Voice",
      "old": "Precise, clinical. Rarely uses contractions.",
      "new": "Precise, clinical. Rarely uses contractions. Speaks in fragments when angry."
    }
  ],
  "summary": "Add speech pattern under stress to Mara's Voice section."
}
```

### Validation

- Character: `name`, `story_role`, `one_sentence` required
- Location/World: `name`, `one_sentence` required
- Plot: `name`, `status` required
- `story_role` must be: Protagonist, Antagonist, Supporting, Minor, Cameo
- `status` must be: active, resolved, abandoned

---



## delete_entity

Move entity to `_recycle-bin/` (never hard delete).

### Procedure

1. Confirm entity exists
2. Create `_recycle-bin/<type>/` if needed
3. Move note file
4. Update index
5. Note: screenplay prose referencing this character is NOT deleted

### Safety

- Always move, never delete
- Screenplay references remain (writer must clean up manually)
- Plot threads referencing this entity are flagged in index update

---

## update_story_memory

Regenerate Story Memory from current screenplay and entities.

### Procedure

1. Read screenplay, extract continuity data
2. Rebuild CHARACTERS & RELATIONSHIPS from character frontmatter
3. Rebuild CHARACTER KNOWLEDGE from character `knowledge` fields
4. Rebuild SETUPS & PAYOFFS from plot frontmatter
5. Flag continuity risks:
   - Character knows something they shouldn't
   - Timeline inconsistency
   - World rule violation
6. Write to `.story/memory.md`

### Output Format

```markdown
# Story Memory

## CHARACTERS & RELATIONSHIPS
Mara and Oak are allied but don't fully trust each other.

## CHARACTER KNOWLEDGE
- Mara: Her brother Daniel was murdered, Victor Hale is the cartel's CFO
- Oak: The cartel has a financial network

## SETUPS & PAYOFFS
- Scene 1: Account number introduced → Scene 22: Kitchen confrontation

## CONTINUITY RISKS
- Mara's skimming hasn't been discovered (ticking clock)
```

---

## answer

Read-only conversational response (no edit).

### Procedure

1. Use retrieved sections to inform response
2. Cite sources (scene headings, character names)
3. No tool calls that modify files

---

## suggest_ideas

Brainstorm possibilities (no edit).

### Procedure

1. Based on retrieved sections and story state
2. Present 3-5 options with pros/cons
3. User picks one, then use edit_note to implement

### Example

```
Here are 3 options for Mara's voice under stress:

1. **Fragments**: "Speaks in fragments when angry." — Simple, contrasts with clinical baseline.
2. **Silence**: "Goes silent when angry." — More dramatic, harder to write.
3. **Metaphors**: "Uses accounting metaphors when emotional." — Subtle, shows avoidance.

Which direction?
```
