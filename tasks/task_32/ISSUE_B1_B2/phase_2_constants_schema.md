# Phase 2: Constants and Schema Declarations

**Goal:** Add the new fields to `ENTITY_SCHEMAS` — `plot.value_schemas`, `scene.value_turns`, and the computed `plot.value_lines`. Add the ladder and conflict level constants. Narrow `plot.characters` description.

**Plan reference:** §3.1, §3.2, §3.3, §3.4

## Code verification findings

- `ENTITY_SCHEMAS` in `core/constants.py` is the single source of truth for field declarations
- `REQUIRED_FIELDS` is derived from `ENTITY_SCHEMAS` (line 268-272) — new required fields automatically become required
- `unfilled_fields` in `core/entity.py` iterates `ENTITY_SCHEMAS` — new fields automatically appear in unfilled checks
- `story_describe.py` copies all schema keys — new fields automatically appear in describe output
- `story_retrieve.py` iterates schema for field values — new fields automatically appear in retrieve
- `story_export.py` uses `_frontmatter_for` which has per-type branches — new fields on plot/scene need export handling
- `story_import.py` uses `_extra_for` which validates against schema — new fields automatically validated on import
- The six plot beat fields are `computed: True` — they are read-only, written on the scene as `plot_roles`

## Tasks

### 2.1 — Add ladder and conflict level constants
- [ ] In `core/constants.py`, add `VALUE_LADDER` — the four rungs: P, C, CD, NN with their codes and meanings
- [ ] In `core/constants.py`, add `CONFLICT_LEVELS` — `["inner", "personal", "extra-personal"]`
- [ ] These are used by `validate_scene_value_turns` (Phase 3) and the skill (Phase 6)

### 2.2 — Add `plot.value_schemas` field declaration
- [ ] In `core/constants.py`, add to `ENTITY_SCHEMAS["plot"]`:
  - `value_schemas`: type `list`, optional, default `[]`
  - `sub_fields`: `value` (string, required), `p` (string, required), `c` (string, required), `cd` (string, required), `nn` (string, required), `note` (string, optional)
  - Description: "Value schemas defined on this plot. Each entry defines one value and its four ladder words."

### 2.3 — Add `scene.value_turns` field declaration
- [ ] In `core/constants.py`, add to `ENTITY_SCHEMAS["scene"]`:
  - `value_turns`: type `list`, optional, default `[]`
  - `sub_fields`:
    - `plot` (string, required, ref: "plot")
    - `value` (string, required)
    - `from` (string, required)
    - `to` (string, required)
    - `schema` (object, optional) — inline schema definition with `p`, `c`, `cd`, `nn`, `note`
    - `effects` (list, required)
      - `sub_fields`:
        - `character` (string, required, ref: "character")
        - `levels` (list, required)
          - `sub_fields`:
            - `conflict_level` (string, required, enum: CONFLICT_LEVELS)
            - `effect` (string, required)
  - Description: "Value turns recorded on this scene. Each entry is one shift of a value, with its effects on the protagonists."

### 2.4 — Add `plot.value_lines` computed field declaration
- [ ] In `core/constants.py`, add to `ENTITY_SCHEMAS["plot"]`:
  - `value_lines`: type `list`, optional, computed: True, default `[]`
  - Description: "Computed read-back: for each value of the plot, its schema and its turns in story order."
  - This is computed in Phase 4 — for now, just declare it

### 2.5 — Narrow `plot.characters` description
- [ ] Change description from "Character slugs of characters involved as protagonist/s in this plot" to "Character slugs of this plot's protagonists only"
- [ ] This is a description-only change; the validation (reference check) already ensures they exist

### 2.6 — Verify schema-driven surfaces pick up the new fields
- [ ] `story_describe` shows `value_schemas`, `value_turns`, `value_lines` in output
- [ ] `story_retrieve` with `fields=['all']` includes them
- [ ] `unfilled_fields` handles them correctly (value_turns is optional, value_lines is computed)
- [ ] `REQUIRED_FIELDS` derivation still works (new required sub-fields don't affect top-level required)

### 2.7 — Run test suite
- [ ] All existing tests still pass
- [ ] `test_field_coverage.py` picks up the new fields automatically (it walks the schema)

## Checklist

- [ ] `VALUE_LADDER` constant added
- [ ] `CONFLICT_LEVELS` constant added
- [ ] `plot.value_schemas` declared with sub_fields
- [ ] `scene.value_turns` declared with nested effects/levels/schema
- [ ] `plot.value_lines` declared as computed
- [ ] `plot.characters` description narrowed
- [ ] Schema-driven surfaces (describe, retrieve, unfilled) handle new fields
- [ ] Full test suite passes
