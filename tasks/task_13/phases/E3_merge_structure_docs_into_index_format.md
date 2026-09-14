# E3 — Merge `structure-index-format.md` into `index-format.md` (story-loader)

**Goal:** Merge the dramatic metadata documentation from `structure-index-format.md` into `index-format.md`. Delete `structure-index-format.md`.

## Why

With unified index, dramatic metadata fields live in `index.yaml`, not a sidecar. The docs should reflect this — one reference file for the full index.

## Current State

`skills/story-loader/references/structure-index-format.md`: 124 lines documenting dramatic metadata fields (story, acts, sequences, scenes value arcs, dramatic roles, etc.)

`skills/story-loader/references/index-format.md`:
- Line 127: note saying structural fields live in `structure-index.yaml`
- Line 251: reference to `structure-index-format.md`

## Changes

1. **`skills/story-loader/references/index-format.md`**:
   - Remove the "Note" on line 127 that says structural fields live in sidecar
   - Add structural fields to Project table: `spine`, `controlling_idea`, `value`, `value_open`, `value_close`, `inciting_incident_scene_id`, `story_climax_scene_id`, `structure_type` (all optional, from frontmatter)
   - Add dramatic metadata fields to Scene table: `value`, `value_open`, `value_close`, `conflict_levels`, `dramatic_role`, `is_inciting_incident`, `is_sequence_climax`, `is_act_climax`, `is_story_climax`
   - Add value/dramatic fields to Sequence table: `value`, `value_open`, `value_close`, `climax_scene_id`
   - Add value/dramatic fields to Act table: `value`, `value_open`, `value_close`, `climax_scene_id`
   - Remove line 251 (reference to `structure-index-format.md`)
   - Add a section explaining the value arc system (from `structure-index-format.md` lines 115-124)

2. **Delete** `skills/story-loader/references/structure-index-format.md`

## Verification Checklist
- [x] `index-format.md` includes all fields from `structure-index-format.md`
- [x] Project table includes structural fields
- [x] Scene table includes dramatic metadata fields
- [x] Value arc system documented
- [x] `structure-index-format.md` deleted
- [x] No references to `structure-index-format.md` remain in `index-format.md`

## Completed
- Removed "Note" about structural fields living in sidecar
- Added 8 structural fields to Project table
- Added 10 dramatic metadata fields to Scene table
- Added 4 value/dramatic fields to Sequence table
- Added 4 value/dramatic fields to Act table
- Added Value Arc System section
- Added Non-Event Scenes section
- Removed "Structure Index" section at end
- Deleted `structure-index-format.md`
