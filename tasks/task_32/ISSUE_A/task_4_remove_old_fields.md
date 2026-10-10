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
  `"inciting_incidents"` to the fields list.
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

- [ ] Milestone flags removed from `ENTITY_SCHEMAS["scene"]`
- [ ] Pointer fields removed from `ENTITY_SCHEMAS["project"]`
- [ ] Pointer fields removed from `ENTITY_SCHEMAS["act"]`
- [ ] Pointer fields removed from `ENTITY_SCHEMAS["sequence"]`
- [ ] Fixture updated (all milestone fields removed from markdown files)
- [ ] `test_phase2_db_reads.py` updated
- [ ] `test_core.py` updated (climax_scene_id checks removed)
- [ ] All other tests verified passing
- [ ] Full suite green
