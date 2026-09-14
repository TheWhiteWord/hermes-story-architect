# E1 — Update `skills/story-loader/SKILL.md`

**Goal:** Remove `structure_only` references. Update tool description and procedure to reflect unified index.

## Why

The skill documents `structure_only` parameter and a "Load structure (when needed)" step. With unified index, one `story_load` call returns everything.

## Current State

`skills/story-loader/SKILL.md`:
- Line 39: `structure_only` in tool table
- Lines 67-73: "Load structure (when needed)" section
- Line 102: references `structure-index-format.md`

## Changes

1. **`skills/story-loader/SKILL.md`**:
   - Line 39: Remove `structure_only` from `story_load` description
   - Lines 67-73: Remove "Load structure (when needed)" section entirely
   - Line 102: Remove `structure-index-format.md` reference, update to point to `index-format.md` for dramatic metadata fields
   - Update procedure step 3 to remove the "load structure" step

## Verification Checklist
- [x] `structure_only` not mentioned in `story-loader/SKILL.md`
- [x] No "Load structure (when needed)" section
- [x] Procedure has 3 steps (not 4)
- [x] References `index-format.md` for all field docs (including dramatic metadata)

## Completed
- Removed `structure_only` from tool table
- Removed "Load structure (when needed)" section
- Procedure has 3 steps (was 4)
- Updated pitfalls: all dramatic metadata now points to `index-format.md`
