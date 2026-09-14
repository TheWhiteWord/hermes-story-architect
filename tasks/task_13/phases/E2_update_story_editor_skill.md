# E2 — Update `skills/story-editor/SKILL.md`

**Goal:** Remove `structure_only` references. Update tool description and procedure to reflect unified index.

## Why

Same as E1 — the editor skill also documents `structure_only` and references the deleted sidecar format.

## Current State

`skills/story-editor/SKILL.md`:
- Line 43: `structure_only` in tool table
- Line 74: `structure_only: true` in procedure
- Line 110: references `structure-index-format.md`

## Changes

1. **`skills/story-editor/SKILL.md`**:
   - Line 43: Remove `structure_only` from `story_load` description
   - Line 74: Remove the "If the edit involves story structure... also call `story_load` with `structure_only: true`" sentence
   - Line 110: Remove `structure-index-format.md` reference
   - Update procedure step 2 to not mention structure loading

## Verification Checklist
- [x] `structure_only` not mentioned in `story-editor/SKILL.md`
- [x] Procedure doesn't call `story_load` twice
- [x] No references to `structure-index-format.md`

## Completed
- Removed `structure_only` from tool table
- Removed the `structure_only: true` call from procedure
- Updated entity creation section: dramatic metadata now points to `index-format.md`
- Procedure step 2 simplified: single `story_load` call returns everything
