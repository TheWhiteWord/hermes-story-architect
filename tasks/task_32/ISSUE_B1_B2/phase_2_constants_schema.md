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
- **`test_plot_roles.py:58-61`** asserted `set(order[7:]) == set(PLOT_BEAT_FIELDS)` — adding the value fields to the plot schema breaks it; the assertion was rewritten to check the roles as an ordered subsequence plus the value fields' position after them
- **`test_field_coverage.py:_sample_value`** returns plain strings for any list — a `sub_fields` list fed strings is rejected by the shape validator; the fixture project never creates a scene with `value_turns`, so the suite passes, but a future test that samples the field will need a valid entry (see final brief)
- **`_validate_field`'s `object` branch** applied sub-fields to each VALUE of the dict, on the assumption every object is a keyed map (`perspectives`). A turn's inline `schema` is a fixed record, so the same validator rejected every valid `schema` with "p holds a str". Fixed by declaring `keyed: True` on `perspectives` and branching on it; the reference collector (`_collect_refs`) and `unfilled_fields`' per-entry rule got the same branch.
- `unfilled_fields` skips `computed` fields — `value_lines` is automatically not a gap
- `check_references` walks `ref` at any depth through `_collect_refs`/`_collect_refs_entry` — nested `plot`/`character` refs are checked at write time with no new code

## Tasks

### 2.1 — Add ladder and conflict level constants
- [x] In `core/constants.py`, add `VALUE_LADDER` — the four rungs: P, C, CD, NN with their codes and meanings
- [x] In `core/constants.py`, add `CONFLICT_LEVELS` — `["inner", "personal", "extra-personal"]`
- [x] These are used by `validate_scene_value_turns` (Phase 3) and the skill (Phase 6)

### 2.2 — Add `plot.value_schemas` field declaration
- [x] In `core/constants.py`, add to `ENTITY_SCHEMAS["plot"]`:
  - `value_schemas`: type `list`, optional, default `[]`
  - `sub_fields`: `value` (string, required), `p` (string, required), `c` (string, required), `cd` (string, required), `nn` (string, required), `note` (string, optional)
  - Description: "Value schemas defined on this plot. Each entry defines one value and its four ladder words."

### 2.3 — Add `scene.value_turns` field declaration
- [x] In `core/constants.py`, add to `ENTITY_SCHEMAS["scene"]`:
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
- [x] In `core/constants.py`, add to `ENTITY_SCHEMAS["plot"]`:
  - `value_lines`: type `list`, optional, computed: True, default `[]`
  - Description: "Computed read-back: for each value of the plot, its schema and its turns in story order."
  - This is computed in Phase 4 — for now, just declare it

### 2.5 — Narrow `plot.characters` description
- [x] Change description from "Character slugs of characters involved as protagonist/s in this plot" to "Character slugs of this plot's protagonists only"
- [x] This is a description-only change; the validation (reference check) already ensures they exist

### 2.6 — Verify schema-driven surfaces pick up the new fields
- [x] `story_describe` shows `value_schemas`, `value_turns`, `value_lines` in output
- [x] `story_retrieve` with `fields=['all']` includes them
- [x] `unfilled_fields` handles them correctly (value_turns is optional, value_lines is computed)
- [x] `REQUIRED_FIELDS` derivation still works (new required sub-fields don't affect top-level required)
- [x] Nested `value_turns` survives export → import (both `value_turns` and `value_schemas` round-trip identical)

### 2.7 — Run test suite
- [x] All existing tests still pass
- [x] `test_field_coverage.py` picks up the new fields automatically (it walks the schema)

## Checklist

- [x] `VALUE_LADDER` constant added
- [x] `CONFLICT_LEVELS` constant added
- [x] `plot.value_schemas` declared with sub_fields
- [x] `scene.value_turns` declared with nested effects/levels/schema
- [x] `plot.value_lines` declared as computed
- [x] `plot.characters` description narrowed
- [x] Schema-driven surfaces (describe, retrieve, unfilled) handle new fields
- [x] Full test suite passes

---

## Final Brief

Phase 2 complete. The new fields are declared in `core/constants.py`; every schema-driven surface picked them up with no code change. 1091 tests pass, 9 pre-existing failures unchanged (same set as the Phase 1 brief — all old-value-system tests Phase 5 removes/rewrites, plus the two out-of-scope ones).

**What changed:**
- `core/constants.py`: `VALUE_LADDER` (p/c/cd/nn → meaning), `CONFLICT_LEVELS`. `plot.value_schemas` (list, `value`/`p`/`c`/`cd`/`nn` required, `note` optional), `plot.value_lines` (computed, read-only), `scene.value_turns` (nested `schema` object + `effects[].levels[]` with the enum and refs). `plot.characters` description narrowed to protagonists. `relationship.perspectives` gained `keyed: True`.
- `core/entity.py`: `_validate_field`'s object branch splits on `keyed` — a keyed map (perspectives) applies sub-fields per value, a fixed record (inline `schema`) applies them to the dict itself. Without this, every valid turn `schema` was refused with "p holds a str" and export→import was broken. `_collect_refs` got the same branch (the reference check walks a record, not a keyed map, for `schema`). `unfilled_fields`' per-entry rule also keys on `keyed` (a record field with no missing-keys notion must not report `value_turns.<key>`).
- `tests/test_plot_roles.py`: `test_the_identity_fields_come_before_the_roles` no longer asserts `set(order[7:]) == set(PLOT_BEAT_FIELDS)` — that breaks the moment any non-role field follows the roles. Now checks the roles are an ordered subsequence and the value fields sit after `resolutions`.
- `tests/test_retrieve_reading.py`: the schema-order assertion extended with `value_schemas`, `value_lines`.
- `tests/test_scene_no_cast.py`: `gaps()` reads `view='unfilled'` with `field=` (a filtered answer is never truncated) instead of scanning the capped top-15 list. The two new gap rows (`value_turns`, `value_schemas`) pushed `characters` past the cap at count 2 — the exact regression this file pins — so the helper had to stop reading the capped list.
- `tests/test_write_shape.py`: new consistency test — every object-type field must declare `keyed`, or the record form silently fails its own validation.

**Verified by running, not by reading:** describe emits all three fields with nested sub_fields and the enum; retrieve `fields=['all']` includes them in schema order; `unfilled_fields` reports `value_turns`/`value_schemas` as gaps when empty and not when filled, and never reports the computed `value_lines`; `REQUIRED_FIELDS` is unchanged; a full nested turn (inline schema + two conflict levels) writes through `edit_entity`/`create_entity`, survives export → import byte-identical, and its nested refs are refused at write time when the plot or character does not exist.

**Note for Phase 3:** `test_field_coverage.py:_sample_value` returns `["item-1", "item-2"]` for any list without a special case, which the shape validator rejects for a `sub_fields` field. No current test samples `value_turns` or `value_schemas` on a create, so the suite is green — but any test that does will need a valid entry, same as `plot_roles` already has.

**Ready for Phase 3:** `validate_scene_value_turns` (schema words, protagonist membership, inline schema agreement) and inline schema registration on the plot.
