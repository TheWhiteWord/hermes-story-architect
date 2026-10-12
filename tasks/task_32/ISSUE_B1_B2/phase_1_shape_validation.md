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
- [ ] In `core/constants.py`, convert the six plot beat fields' `sub_fields` from plain strings to `{type, description}` dicts
- [ ] Each becomes: `{"scene_id": {"type": "string", "description": "Scene slug"}, "description": {"type": "string", "description": "What happens at this scene"}}`
- [ ] Verify no test breaks (the shape is the same, only the declaration form changes)

### 1.2 — Add `required`, `enum`, `ref` to existing sub_fields declarations
- [ ] `scene.plot_roles`: mark `plot` as `required: true`, add `ref: "plot"`; mark `role` as `required: true`, add `enum: PLOT_ROLES`
- [ ] `character.relationships`: no required/enum/ref (all optional)
- [ ] `relationship.perspectives`: no required/enum/ref (all optional)
- [ ] The six plot beat fields: no required/enum/ref (entries are `{scene_id, description}`, both optional)
- [ ] **Rule:** `required` is declared ONLY where a validator already requires it. Do not tighten existing behaviour.

### 1.3 — Write the recursive shape validator
- [ ] New function in `core/entity.py`: `_validate_sub_fields(entity_type, field, value, meta, warnings, path="")`
- [ ] Checks: container type (list vs dict), entries are objects, required keys present, scalar types match `type`, `enum` membership, nested `sub_fields` recursion
- [ ] For object-type fields (`perspectives`): applies sub_fields to each value
- [ ] Findings carry the full path, e.g. `value_turns[0].effects[1].levels[0].conflict_level`
- [ ] Replaces the current `_validate_shapes` function
- [ ] Runs wherever `validate_entity` runs (stage + write)

### 1.4 — Write the reference check
- [ ] New function in `core/entity.py`: `check_references(entity_type, frontmatter, project_path)` (or similar)
- [ ] Walks the schema recursively, finds every `ref` at any depth
- [ ] For each `ref`, checks the value names an existing record in the DB
- [ ] Raises `ValueError` on unresolvable references (write-time only)
- [ ] Replaces the structural parts of `validate_scene_plot_roles` (plot existence check) and `validate_plot_characters` (character existence check)
- [ ] The bespoke parts stay: `validate_scene_plot_roles` still checks role validity (enum), `validate_scene_dramatic_role` still checks the contradiction

### 1.5 — Wire the reference check into write paths
- [ ] In `core/writes.py` `create_entity`: call the reference check for scene `plot_roles` (replacing the DB lookup in `validate_scene_plot_roles`)
- [ ] In `core/writes.py` `create_entity`: call the reference check for plot `characters` (replacing `validate_plot_characters`)
- [ ] In `core/writes.py` `edit_entity`: same for the `plot_roles` write block
- [ ] Keep the bespoke validators for meaning rules (role enum, dramatic_role contradiction)

### 1.6 — Schema-driven tests
- [ ] Rewrite `tests/test_write_shape.py` to be schema-driven
- [ ] One test walks every declared field with `sub_fields` and checks that a wrong shape is reported
- [ ] A consistency test checks: every `sub_fields` entry has a `type`, every `enum` is non-empty, every `ref` names a valid entity type
- [ ] Keep the existing tests that verify specific behaviours (string where list is declared, non-object in list, etc.) but drive them from the schema
- [ ] Keep the create-path coverage test (`CREATE_PATH_CASES`) and update it if the schema changes

### 1.7 — Verify no regression
- [ ] Run the full test suite
- [ ] All tests that passed in Phase 0 still pass (except those intentionally changed)
- [ ] The stricter validator does not reject existing data (run it over the fixture)

## Checklist

- [ ] Six plot beat sub_fields converted to dict form
- [ ] `required`, `enum`, `ref` added to existing declarations
- [ ] Recursive shape validator written and wired in
- [ ] Reference check written and wired into write paths
- [ ] `validate_scene_plot_roles` structural parts removed (kept: role enum check)
- [ ] `validate_plot_characters` removed (replaced by reference check)
- [ ] Schema-driven tests written
- [ ] Full test suite passes
- [ ] Fixture data validates clean
