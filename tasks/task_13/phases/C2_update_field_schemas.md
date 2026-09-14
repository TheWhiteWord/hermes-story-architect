# C2 — Update `core/constants.py` Field Schemas

**Goal:** Verify `ENTITY_SCHEMAS["project"]` includes structural fields (spine, controlling_idea, value, etc.) — they should already be present since they're frontmatter fields.

## Why

After A1 removed `PROJECT_STRUCTURAL_FIELDS`, the project schema in `ENTITY_SCHEMAS["project"]` must still include all structural fields so that `story_create` and `story_edit` know about them. The plan assumes they're already there; this task verifies that assumption.

## Changes

None — verification only. `ENTITY_SCHEMAS["project"]` in `core/constants.py` lines 81-101 already includes all structural fields:

- `spine` (line 93)
- `controlling_idea` (line 94)
- `value` (line 95)
- `value_at_open` (line 96)
- `value_at_close` (line 97)
- `inciting_incident_scene_id` (line 98)
- `story_climax_scene_id` (line 99)
- `structure_type` (line 100)

## Verification Checklist

- [x] `ENTITY_SCHEMAS["project"]` includes `spine` ✓
- [x] `ENTITY_SCHEMAS["project"]` includes `controlling_idea` ✓
- [x] `ENTITY_SCHEMAS["project"]` includes `value` ✓
- [x] `ENTITY_SCHEMAS["project"]` includes `value_at_open` ✓
- [x] `ENTITY_SCHEMAS["project"]` includes `value_at_close` ✓
- [x] `ENTITY_SCHEMAS["project"]` includes `inciting_incident_scene_id` ✓
- [x] `ENTITY_SCHEMAS["project"]` includes `story_climax_scene_id` ✓
- [x] `ENTITY_SCHEMAS["project"]` includes `structure_type` ✓

## Final Brief

**Status:** Complete (no-op — schema already correct).

- All 8 structural fields are present in `ENTITY_SCHEMAS["project"]` at `core/constants.py` lines 81-101.
- No changes needed to `core/constants.py`.
- The schema was never modified when `PROJECT_STRUCTURAL_FIELDS` was removed (it was a separate constant used only in `generate_index()`).

## Notes

- Depends on C1 (which verified `PROJECT_STRUCTURAL_FIELDS` is gone)
- This is a verification/cleanup task — no code changes needed
