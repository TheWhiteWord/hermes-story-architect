# Task 1: Add the sixth plot role — `inciting_incident`

## Goal

Add `inciting_incident` as a sixth plot role alongside the existing five
(`setup`, `complication`, `crisis`, `climax`, `resolution`). This is the
foundational change — every later task depends on it.

## Work

### 1.1 `core/constants.py`

- Add `"inciting_incident"` to `PLOT_ROLES` list. The list becomes:
  `["setup", "inciting_incident", "complication", "crisis", "climax", "resolution"]`
  (dramatic order — inciting incident comes after setup, before complication).

### 1.2 `core/entity.py` — `_RELATION_FIELDS["plot"]`

- Add `"inciting_incident": ("plot_inciting_incident", True)` to the plot
  entry in `_RELATION_FIELDS`. The field name is plural (like `setups`,
  `complications`, `resolutions`) because a plot can have multiple inciting
  incidents (though typically one).

### 1.3 `core/entity.py` — `ENTITY_SCHEMAS["plot"]`

- Add the `inciting_incident` field to the plot schema, in dramatic order
  (after `setups`, before `complications`):
  ```python
  "inciting_incident": {"type": "list", "default": [], "optional": True, "computed": True, "description": "Scenes where plot is incited (read-only — set it on the scene as plot_roles)", "sub_fields": {"scene_id": "Scene slug", "description": "What happens at this scene"}},
  ```

### 1.4 `core/entity.py` — `validate_scene_plot_roles`

- The validator already checks `role not in PLOT_ROLES`, so adding to
  `PLOT_ROLES` automatically makes `inciting_incident` valid. No change
  needed here — but verify the error message lists all six roles.

### 1.5 `src/dashboard/js/colors.js`

- Add `"inciting_incident"` to `DASH.PLOT_ROLES` array, in the same dramatic
  order as `PLOT_ROLES`.

### 1.6 `tests/test_plot_roles.py`

- Update `test_the_five_dramatic_roles` → rename to `test_the_six_dramatic_roles`
  and assert the new list.
- Update `test_the_plot_schema_declares_the_roles_in_dramatic_order` → assert
  the new field order including `inciting_incident`.
- Update `test_the_identity_fields_come_before_the_roles` → the identity fields
  slice may need adjustment (7 → 7, since `inciting_incident` is a role field).
- Update `test_the_dashboard_role_list_is_the_same_list` → no code change needed
  (it reads `PLOT_ROLES` and compares to the JS copy), but it will now check
  six roles.
- Update `test_field_names_are_not_role_names_pluralised` → no change needed.
- Update `TestHasRoleFlags.test_every_role_raises_its_flag` → automatically
  covers the new role via `PLOT_ROLES` iteration.
- Update `TestHasRoleFlags.test_flag_set_is_exactly_the_roles` → automatically
  covers the new role.

### 1.7 `tests/test_scene_plot_roles.py`

- Update `test_every_role_reaches_its_own_kind` → automatically covers the new
  role via `PLOT_ROLES` iteration.
- Update `test_a_role_outside_the_dramatic_five_is_refused` → rename to
  `test_a_role_outside_the_six_is_refused`.
- Update `test_the_message_lists_the_valid_roles` → automatically covers.

### 1.8 `tests/test_write_shape.py`

- Update `PLOT_ROLES` constant at line 110 → add `"inciting_incident"`.
- The parametrized test `test_create_writes_the_scene_slug_and_the_description`
  will automatically cover the new role.

### 1.9 `tests/test_field_coverage.py`

- Update `_sample_value` for plot role fields → the `if field in (...)` check
  at line 62 needs `"inciting_incident"` added to the tuple.

### 1.10 `tests/test_unfilled_fields.py`

- Update `test_computed_fields_are_skipped_except_the_plot_roles` → the test
  iterates `ENTITY_SCHEMAS` and checks `_RELATION_FIELDS`, so it automatically
  covers the new field. No change needed.

### 1.11 `tests/test_story_describe.py`

- Update `test_relation_backed_fields_are_flagged` → add `"inciting_incident"`
  to the asserted field list.
- Update `test_a_link_in_extra_is_still_marked_as_a_reference` → no change
  needed (it checks specific fields, not the new one).

## Checklist

- [x] `PLOT_ROLES` in constants has six roles in dramatic order
- [x] `_RELATION_FIELDS["plot"]` has `inciting_incident` entry
- [x] `ENTITY_SCHEMAS["plot"]` has `inciting_incident` computed field in dramatic order
- [x] `DASH.PLOT_ROLES` in colors.js matches
- [x] `test_plot_roles.py` updated and passing
- [x] `test_scene_plot_roles.py` updated and passing
- [x] `test_write_shape.py` updated and passing
- [x] `test_field_coverage.py` updated and passing
- [x] `test_story_describe.py` updated and passing
- [x] Full suite green

## Final Brief

Added `inciting_incident` as the sixth plot role. Changes:

- `core/constants.py`: `PLOT_ROLES` now has six roles; `ENTITY_SCHEMAS["plot"]` has
  `inciting_incident` computed field in dramatic order; `plot_roles.role` description
  updated.
- `core/entity.py`: `_RELATION_FIELDS["plot"]` has `inciting_incident` entry;
  comments updated from "five" to "six".
- `src/dashboard/js/colors.js`: `DASH.PLOT_ROLES` updated.
- Tests updated: `test_plot_roles.py`, `test_scene_plot_roles.py`,
  `test_write_shape.py`, `test_field_coverage.py`, `test_story_describe.py`,
  `test_story_load_views.py`, `test_phase2_db_reads.py`, `test_retrieve_reading.py`,
  `test_unfilled_fields.py`, `test_unfilled_truncation.py`, `test_core.py`.

Full suite: **1068 passed, 0 failed** (was 1067; +1 from the new parametrized role case).
