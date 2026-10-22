# Task 4: Remove old fields from schema and write paths

## Goal

Remove the milestone flags and pointer fields from `ENTITY_SCHEMAS`, the write
paths, and update all fixtures and tests. This is the cleanup task — after
this, the old fields no longer exist anywhere.

## Work

### 4.1 `core/constants.py` — `ENTITY_SCHEMAS`

Remove these fields from the schema:

- **Scene:** `is_inciting_incident`, `is_sequence_climax`, `is_act_climax`,
  `is_story_climax`
- **Project:** `inciting_incident_scene_id`, `story_climax_scene_id`
- **Act:** `act_climax_scene_id`
- **Sequence:** `seq_climax_scene_id`

### 4.2 `core/entity.py` — write paths

- The write paths (`create_entity`, `edit_entity`) use `ENTITY_SCHEMAS` to
  validate fields, so removing from the schema automatically prevents writing.
- Verify that `validate_entity` no longer checks for these fields (it checks
  `REQUIRED_FIELDS` which is derived from the schema).

### 4.3 `tools/story_import.py` — `_extra_for`

- The `skip` dict at line 480 already lists fields that go to columns or
  relations. The removed fields are no longer in `ENTITY_SCHEMAS`, so they
  will be caught by the "unknown field" check. But the migration script
  (Task 2) already strips them, so this is a safety net.
- Verify that importing an old file with these fields now reports them as
  unknown (which is correct — they are gone).

### 4.4 `tools/story_export.py`

- The export reads from `extra` and writes frontmatter. Since the fields are
  removed from the schema, they will not be in `extra` (the migration script
  stripped them). No change needed unless the export explicitly references
  these fields.

### 4.5 Fixture — `tests/fixtures/save-the-children`

- Update the fixture to remove all milestone flags and pointer fields from
  the markdown files.
- The fixture's `project.md` should no longer have `inciting_incident_scene_id`
  or `story_climax_scene_id`.
- The fixture's scene files should no longer have `is_inciting_incident`,
  `is_sequence_climax`, `is_act_climax`, `is_story_climax`.
- The fixture's act files should no longer have `act_climax_scene_id`.
- The fixture's sequence files should no longer have `seq_climax_scene_id`.
- **Important:** The fixture's `project.md` names `central-room-day` as the
  inciting incident in prose. After migration, this should be reflected as an
  `inciting_incident` role in the main plot's `plot_roles` for that scene.

### 4.6 Tests — update all affected tests

- **`test_plot_roles.py`:** Already updated in Task 1.
- **`test_scene_plot_roles.py`:** Already updated in Task 1.
- **`test_field_coverage.py`:** Already updated in Task 1.
- **`test_unfilled_fields.py`:** The `test_computed_fields_are_skipped_except_the_plot_roles`
  test iterates `ENTITY_SCHEMAS` — it will automatically skip the removed fields.
- **`test_story_describe.py`:** Already updated in Task 1.
- **`test_phase2_db_reads.py`:** The `test_plot_to_scenes` test reads
  `["setups", "complications", "crisis", "climax", "resolutions"]` — add
  `"inciting_incident"` to the fields list.
- **`test_draft_preview.py`:** No direct reference to milestone flags.
- **`test_write_shape.py`:** Already updated in Task 1.
- **`test_round_trip.py`:** No direct reference to milestone flags.
- **`test_core.py`:** The `climax_scene_id` checks near line 919 need to be
  removed or updated — these fields no longer exist.

### 4.7 `core/db.py` — `get_unfilled_map`

- The unfilled map is derived from `ENTITY_SCHEMAS`, so removing fields from
  the schema automatically removes them from the unfilled map. No change
  needed.

### 4.8 `tools/story_describe.py`

- The describe tool reads from `ENTITY_SCHEMAS`, so removed fields are
  automatically gone. No change needed.

## Checklist

- [x] Milestone flags removed from `ENTITY_SCHEMAS["scene"]`
- [x] Pointer fields removed from `ENTITY_SCHEMAS["project"]`
- [x] Pointer fields removed from `ENTITY_SCHEMAS["act"]`
- [x] Pointer fields removed from `ENTITY_SCHEMAS["sequence"]`
- [x] Fixture updated (all milestone fields removed from markdown files)
- [x] `test_phase2_db_reads.py` updated
- [x] `test_core.py` updated (climax_scene_id checks removed)
- [x] All other tests verified passing
- [x] Full suite green

## Final Brief

### Changes made

**`core/constants.py`** — Removed 7 fields from `ENTITY_SCHEMAS`:
- Scene: `is_inciting_incident`, `is_sequence_climax`, `is_act_climax`, `is_story_climax`
- Project: `inciting_incident_scene_id`, `story_climax_scene_id`
- Act: `act_climax_scene_id`
- Sequence: `seq_climax_scene_id`

**`tools/story_load.py`** — Removed dead reads of `act_climax_scene_id` and
`seq_climax_scene_id` from the `dramatic_elements` view. The project-level
`story_climax_scene_id` and `inciting_incident_scene_id` keys remain as
presentation-only output (derived from main-plot roles, not schema fields).

**Fixture — `tests/fixtures/save-the-children/`**:
- `project.md`: removed `inciting_incident_scene_id` and `story_climax_scene_id`
- `Act One.md`: removed `act_climax_scene_id`
- `The Discovery.md`: removed `seq_climax_scene_id`
- All 3 scene files: removed all 4 milestone flags
- `The Resistance.md`: added `plot_scope: main`
- `The Scientists Last Stand.md`: added `plot_scope: sub`
- `Central Room - Day.md`: changed role from `setup` to `inciting_incident`;
  added a `setup` entry for `the-scientists-last-stand`
- `Central Room - Night.md`: changed role from `setup` to `climax`

**`src/dashboard/js/data-load.js`** — Removed `inciting_incident_scene_id` and
`story_climax_scene_id` from the sample data.

**Tests updated** (all adjustments for fixture role changes):
- `test_core.py`: removed `act_climax_scene_id` from unfilled test
- `test_story_describe.py`: removed `story_climax_scene_id` from reference test
- `test_story_load_views.py`: updated 8 tests for new fixture roles
- `test_dashboard.py`: updated role assertion from SETUP to CLIMAX
- `test_draft_preview.py`: updated field count from 8 to 7
- `test_field_coverage.py`: updated plot beat assertions
- `test_retrieve_reading.py`: updated plot role assertions
- `test_scene_plot_roles.py`: updated role assertions
- `test_story_dashboard_stats.py`: updated role assertions
- `test_unfilled_column_fields.py`: updated plot_scope assertion

### Verification

Full test suite: **1073 passed** in 107.74s.

### No changes needed (verified)

- `core/entity.py` — write paths use `ENTITY_SCHEMAS` for validation; removed
  fields are automatically rejected
- `tools/story_import.py` — `_extra_for` already validates against
  `ENTITY_SCHEMAS`; removed fields are caught as "unknown field"
- `tools/story_export.py` — no direct references to removed fields
- `core/db.py` — `get_unfilled_map` derives from `ENTITY_SCHEMAS`
- `tools/story_describe.py` — reads from `ENTITY_SCHEMAS`
