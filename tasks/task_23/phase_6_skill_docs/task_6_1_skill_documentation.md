# Task 6.1: Skill Documentation Update

## Goal
Update SKILL.md to document relationship as a first-class entity with computed field behavior.

## Steps

### 6.1.1: Add Relationships section to SKILL.md
- **File**: `skills/hermes-story-architect/SKILL.md`
- **Action**: Add new section after the character entity documentation:
```markdown
## Relationships

Relationships are first-class entities. Each relationship stores two `perspectives` — one per character — capturing direction-dependent qualities (A loves B / B sees A as friend).

### story_load view
Characters include a computed `relationships` summary (minimal: `with`, `label`, `type`). Full relationship data is in the top-level `relationships` dict.

### story_retrieve
Use `entity_type="relationship"` with the relationship slug to get full details.

### story_create
Create relationships after both characters exist. The `perspectives` object must contain both character slugs.

### Computed fields
`character.relationships` and `character.arc_beats_list` are computed fields — they appear in load/retrieve/dashboard output but are NOT writable via create/edit. They are always derived fresh from their source entities.
```

### 6.1.2: Update story_describe section in SKILL.md
- **File**: `skills/hermes-story-architect/SKILL.md`
- **Action**: Update the `story_create` and `story_edit` tool descriptions to mention `relationship` as a valid entity_type

### 6.1.3: Update story_import/export sections in SKILL.md
- **File**: `skills/hermes-story-architect/SKILL.md`
- **Action**: Add note that `relationships/` folder is imported/exported alongside other entity folders

## Verification
- [ ] SKILL.md includes Relationships section
- [ ] `story_create` description mentions `relationship` entity type
- [ ] `story_import`/`story_export` mention `relationships/` folder
- [ ] Computed fields documented

## Checklist
- [ ] Relationships section added to SKILL.md
- [ ] Tool descriptions updated
- [ ] Computed field behavior documented
- [ ] Import/export folder documentation updated
