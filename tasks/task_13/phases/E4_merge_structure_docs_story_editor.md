# E4 — Merge `structure-index-format.md` into `index-format.md` (story-editor)

**Goal:** Same as E3 but for the story-editor skill's reference files.

## Changes

1. **`skills/story-editor/references/index-format.md`**:
   - Remove the "Note" on line 127 that says structural fields live in sidecar
   - Add structural fields to Project table
   - Add dramatic metadata fields to Scene table
   - Add value/dramatic fields to Sequence and Act tables
   - Remove line 251 (reference to `structure-index-format.md`)
   - Add value arc system documentation

2. **Delete** `skills/story-editor/references/structure-index-format.md`

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
- Also removed duplicated content that was present from line 258 onward (file had been corrupted with duplicate Scene/Sequence/Act tables)
