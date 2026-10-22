# Phase 1: Shared Shape Validation

**Goal:** Rebuild `_validate_shapes` as a recursive, schema-driven validator. Add a generic reference check. Migrate all nine existing `sub_fields` fields onto it. No new fields yet — that's Phase 2.

**Plan reference:** §3.6

## Code verification findings

- `_validate_shapes` (core/entity.py:138-168) currently only checks container type (list vs dict). It does NOT check required keys, scalar types, enum membership, or nested sub_fields.
- Nine fields declare `sub_fields`:
  - Three use `{type, description}` dict form: `character.relationships`, `scene.plot_roles`, `relationship.perspectives`
  - Six use plain description strings: `plot.setups`, `plot.inciting_incident`, `plot.complications`, `plot.crisis`, `plot.climax`, `plot.resolutions`
- `validate_scene_plot_roles` (core/entity.py:656-692) does DB lookups to check plot existence and role validity — the structural parts (plot exists, role is valid) will be replaced by the reference check.
- `validate_plot_characters` (core/entity.py:759-774) does DB lookups to check character existence — replaced by the reference check.
- `validate_entity` (core/entity.py:33-108) calls `_validate_shapes` at line 41. The new recursive validator replaces this call.
- `core/drafts.py:206` calls `validate_entity` at stage time — the shape validator runs here too (no DB needed).
- The reference check needs DB access, so it runs at write time only (in `core/writes.py`).

## Tasks

### 1.1 — Convert the six plot beat sub_fields to dict form
- [x] In `core/constants.py`, convert the six plot beat fields' `sub_fields` from plain strings to `{type, description}` dicts
- [x] Each becomes: `{"scene_id": {"type": "string", "description": "Scene slug"}, "description": {"type": "string", "description": "What happens at this scene"}}`
- [x] Verify no test breaks (the shape is the same, only the declaration form changes)

### 1.2 — Add `required`, `enum`, `ref` to existing sub_fields declarations
- [x] `scene.plot_roles`: mark `plot` as `required: true`, add `ref: "plot"`; mark `role` as `required: true`, add `enum: PLOT_ROLES`
- [x] `character.relationships`: no required/enum/ref (all optional)
- [x] `relationship.perspectives`: no required/enum/ref (all optional)
- [x] The six plot beat fields: no required/enum/ref (entries are `{scene_id, description}`, both optional)
- [x] **Rule:** `required` is declared ONLY where a validator already requires it. Do not tighten existing behaviour.

### 1.3 — Write the recursive shape validator
- [x] New function in `core/entity.py`: `_validate_sub_fields(entity_type, field, value, meta, warnings, path="")`
- [x] Checks: container type (list vs dict), entries are objects, required keys present, scalar types match `type`, `enum` membership, nested `sub_fields` recursion
- [x] For object-type fields (`perspectives`): applies sub_fields to each value
- [x] Findings carry the full path, e.g. `value_turns[0].effects[1].levels[0].conflict_level`
- [x] Replaces the current `_validate_shapes` function
- [x] Runs wherever `validate_entity` runs (stage + write)

### 1.4 — Write the reference check
- [x] New function in `core/entity.py`: `check_references(entity_type, frontmatter, project_path)` (or similar)
- [x] Walks the schema recursively, finds every `ref` at any depth
- [x] For each `ref`, checks the value names an existing record in the DB
- [x] Raises `ValueError` on unresolvable references (write-time only)
- [x] Replaces the structural parts of `validate_scene_plot_roles` (plot existence check) and `validate_plot_characters` (character existence check)
- [x] The bespoke parts stay: `validate_scene_plot_roles` still checks role validity (enum), `validate_scene_dramatic_role` still checks the contradiction

### 1.5 — Wire the reference check into write paths
- [x] In `core/writes.py` `create_entity`: call the reference check for scene `plot_roles` (replacing the DB lookup in `validate_scene_plot_roles`)
- [x] In `core/writes.py` `create_entity`: call the reference check for plot `characters` (replacing `validate_plot_characters`)
- [x] In `core/writes.py` `edit_entity`: same for the `plot_roles` write block
- [x] Keep the bespoke validators for meaning rules (role enum, dramatic_role contradiction)

### 1.6 — Schema-driven tests
- [x] Rewrite `tests/test_write_shape.py` to be schema-driven
- [x] One test walks every declared field with `sub_fields` and checks that a wrong shape is reported
- [x] A consistency test checks: every `sub_fields` entry has a `type`, every `enum` is non-empty, every `ref` names a valid entity type
- [x] Keep the existing tests that verify specific behaviours (string where list is declared, non-object in list, etc.) but drive them from the schema
- [x] Keep the create-path coverage test (`CREATE_PATH_CASES`) and update it if the schema changes

### 1.7 — Verify no regression
- [x] Run the full test suite
- [x] All tests that passed in Phase 0 still pass (except those intentionally changed)
- [x] The stricter validator does not reject existing data (run it over the fixture)

## Checklist

- [x] Six plot beat sub_fields converted to dict form
- [x] `required`, `enum`, `ref` added to existing declarations
- [x] Recursive shape validator written and wired in
- [x] Reference check written and wired into write paths
- [x] `validate_scene_plot_roles` structural parts removed (kept: role enum check)
- [x] `validate_plot_characters` removed (replaced by reference check)
- [x] Schema-driven tests written
- [x] Full test suite passes
- [x] Fixture data validates clean

---

## Final Brief

Phase 1 complete. The shape validator is now recursive and schema-driven; the reference check replaces the bespoke DB lookups. 1082 tests pass, 13 pre-existing failures unchanged (Phase 5 will address the value-system ones; `test_relationship_subfields` and `test_phase2_db_reads` are out of scope).

**What changed:**
- `core/entity.py`: `_validate_shapes` replaced by `_validate_field` + `_validate_sub_field` (recursive, path-carrying findings). New `check_references` + `_collect_refs`/`_collect_refs_entry` walk the schema for `ref` declarations at any depth. `validate_scene_plot_roles` keeps the role enum and missing-plot-slug checks (bespoke meaning rules); plot existence check replaced by `check_references`. `validate_plot_characters` deleted.
- `core/constants.py`: `plot.characters` gained `ref: "character"` (flat list-of-slugs form). Six plot beat fields already converted to dict form (1.1). `plot_roles.plot`/`role` already have `required`/`ref`/`enum` (1.2).
- `core/writes.py`: `create_entity` calls `check_references` for scene and plot; `edit_entity` calls it for the `plot_roles` block.
- `tests/test_write_shape.py`: rewritten schema-driven — parametrized over every field with `sub_fields`, plus consistency tests (every sub_field has a `type`, every enum non-empty, every ref valid). Create-path coverage tests kept.
- `tests/test_scene_plot_roles.py`: `test_a_role_outside_the_six_is_not_caught_by_the_shape_check` inverted to `test_a_role_outside_the_six_is_caught_by_the_shape_check` (the enum is now declared, so the shape validator judges it).
- `tests/test_import_enum_validation.py`: fixed the pre-existing YAML helper bug (stripped only the `plot_roles:` line, leaving nested items → invalid YAML). `_strip_yaml_block` now drops the whole block value.

**Deviations from task spec:**
- Named the validator `_validate_field` (not `_validate_sub_fields`) — per user's preference for the cleaner name. The brief's exact signature is `(entity_type, field, value, meta, warnings, path="")`; the implementation matches.
- `check_references` handles two declaration forms: field-level `ref` (flat list of slugs, e.g. `plot.characters`) and sub-field `ref` (nested inside entries, e.g. `plot_roles.plot`). The brief only described the sub-field form; the field-level form is needed to replace `validate_plot_characters`.
- `validate_scene_plot_roles` keeps the "entry needs a plot slug" check: `check_references` skips absent keys, so an entry with no `plot` key would otherwise be silently accepted and produce no relation row. This is the required-key rule at write time, which the schema declares as `required: true` but the reference check cannot enforce.

**Pre-existing failures left as-is (out of Phase 1 scope):**
- `test_relationship_subfields.py::test_declared_sub_fields_match_the_load_payload` — compares `character.relationships.sub_fields` against `get_project_summary` (which emits bare slug strings), producing character-set garbage. Pre-existing on 77d2d89 and f045bf9.
- `test_phase2_db_reads.py::TestEmbeddedCrossReferences::test_character_has_rel` — pre-existing, unrelated to shape validation.
- Value-system failures in `test_arc_graph_story_series`, `test_story_load_views`, `test_value_ownership` — expected, Phase 5 removes/rewrites them.

**Ready for Phase 2:** Constants and schema (`plot.value_schemas`, `scene.value_turns` with nested `effects`/`levels`/`schema`).
