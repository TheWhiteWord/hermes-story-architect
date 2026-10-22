# Phase 6 — Legacy

A self-contained deletion: `arc_beat`, its markdown tree, and the character
arc fields that duplicate scene values.

Verified against code on `feature/issue-redesign`.

---

## Tasks

- [ ] **T6.1** Remove `arc_beat` from all schema declarations.

  - `ENTITY_SCHEMAS` in `core/constants.py`
  - `ENTITY_LABELS` in `core/constants.py`
  - `ENTITY_COLUMN_MAP` in `core/entity.py:308`
  - `_RELATION_FIELDS` in `core/entity.py`
  - `standard_sections` in `core/entity.py:501`
  - `REQUIRED_FIELDS` (derived from `ENTITY_SCHEMAS`)
  - The `validate_entity` enum checks in `core/entity.py:82-85`

  **Verify:** `story_describe` no longer lists it, and `story_draft` refuses it.

- [ ] **T6.2** Remove the character arc fields from `ENTITY_SCHEMAS`.

  Remove: `arc_type`, `character_value`, `character_value_at_open`,
  `character_value_at_close`, `arc_complete`, `arc_beats_list`.

  **Verify:** the schema has no field whose name starts with `arc` except
  `scene_beats`-side names.

- [ ] **T6.3** Remove the `arc_beat` read model from `core/db.py`.

  Remove:
  - `get_character_arcs` function (`:851`)
  - The `arc_beat` branch in the unfilled loop (`:829`)
  - The `arc_beat` branch in `_build_all` (`:1180`)
  - The `arc_beats_list` grouping (`:1222-1250`)
  - The `scene.arc_beats` block (`:1272-1289`, dead since T0.2)

  **Verify:** `git grep -n arc core/` returns nothing.

- [ ] **T6.4** Remove the `arc_beat` write model from `core/entity.py`.

  Remove:
  - `validate_arc_parents`
  - The `columns_for_insert` special case (`:567`)
  - The `ENTITY_COLUMN_MAP` entry (`:308`)
  - The `_purge_references` arc case (`:1054`)
  - The `_validate_y` helper

  **Verify:** `git grep -n arc_beat core/` returns nothing.

- [ ] **T6.5** Remove `view="arc"` from `story_load`, and the
      `get_character_arcs` import.

  **Verify:** the view enum no longer lists it.

- [ ] **T6.6** Remove the nested-tree import and export.

  **Import** (`tools/story_import.py`):
  - `_import_arcs` (`:370`)
  - The `arcs/` walk in the safety guard (`:87-92`)
  - The `_columns_for` branch (`:502`)
  - The `_extra_for` skip set (`:567`)
  - The `_insert_entity` `char_slug` parameter

  **Export** (`tools/story_export.py`):
  - The `arc_beat` branch (`:237`)
  - The `_frontmatter_for` branch (`:379`)
  - The `_sweep_stale` parent-folder cleanup (`:122-128`)

  **Verify:** a `scene_beats/` folder imports and exports flat.

- [ ] **T6.7** Remove the restore cascade and the `LIKE` fallback.

  - `tools/story_admin.py:324-333` — restore cascade for beats
  - `tools/story_retrieve.py:73-86` — `LIKE` fallback for bare beat label

  **Verify:** `restore` on a character no longer touches beats, and a bare
  beat label is simply not an id.

- [ ] **T6.8** Remove the fixture's `arcs/` directory and its 11 beat notes.

  **Verify:** `build_fixture_db` imports the fixture with no `arcs/` folder
  and every test that depended on it passes.

- [ ] **T6.9** Remove `tests/migrate_fixture_b1_b2.py`.

  It is a one-time migration whose only remaining target is arc beat fields.

  **Verify:** it is not imported by any test.

- [ ] **T6.10** Remove `tests/test_arcs.py` and
      `tests/test_arc_graph_story_series.py`.

  **Verify:** the suite passes without them.

- [ ] **T6.11** Remove the arc assertions from the remaining test files.

  Files: `test_core.py`, `test_writes.py`, `test_edit_safety.py`,
  `test_soft_delete.py`, `test_purge.py`, `test_phase3_scenario.py`,
  `test_phase2_db_reads.py`, `test_field_coverage.py`,
  `test_story_load_views.py`, `test_story_describe.py`,
  `test_retrieve_reading.py`, `test_id_is_not_a_field.py`,
  `test_import_enum_validation.py`, `test_unfilled_fields.py`,
  `test_export_sweep.py`, `test_round_trip.py`.

  **Verify:** `git grep -ln arc_beat tests/` returns nothing.

- [ ] **T6.12** Migrate the live project.

  Delete the 6 `arc_beat` rows from
  `/media/theww/AI/TWW/hermes-story-architect/projects/browser-verification-test/.story/story.db`,
  delete `arcs/`, and rebuild from markdown with `story_import`.

  **Verify:** the project loads and the scene count is unchanged.

---

## Findings

**F6.1 — the `arc_complete` flag has no reader.** It appears in `ENTITY_SCHEMAS`
and in two tests; no dashboard, tool or skill reads it. Removing it is a
deletion with no behavioural change.

**F6.2 — `tests/test_arc_graph_story_series.py` is the only node-based test.**
It runs `arc-graph.js` against a stub DOM. The design defers a new
visualisation, so this test file is deleted rather than replaced. Recorded
as a known gap: when a new visualisation lands, it needs a test of the same
kind.

---

## Parallel work

T6.1–T6.4 (the schema and core) are one logical change and must land together.
T6.5–T6.7 (the tools) are independent of each other and can be picked up in
parallel once T6.1–T6.4 land. T6.8–T6.12 (tests, fixture, live project) depend
on T6.1–T6.7 and are one task file.

## Dependencies

Phases 1–5 must be complete (nothing reads a field that is about to go).
