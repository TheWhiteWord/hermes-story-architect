# Phase 3: Value Turn Validation and Registration

**Goal:** Write `validate_scene_value_turns`, wire it into the three scene call sites in `core/writes.py`, and implement inline schema registration on the plot.

**Plan reference:** §3.5

## Code verification findings

- The three scene validation call sites in `core/writes.py`:
  1. `create_entity` (line 190-203): validates `plot_roles`, `dramatic_role`, `location`, `act_id`
  2. `edit_entity` (line 366-386): merged `dramatic_role`/`plot_roles` contradiction check
  3. `edit_entity` (line 473-487): `plot_roles` write block re-validates
- `validate_scene_value_turns` needs to run at create and edit time, checking:
  - The plot exists (reference check from Phase 1 handles this)
  - The value has a schema on that plot (existing or supplied inline)
  - `from` and `to` are words of that schema
  - `effects` is not empty
  - Each effect's character is in the plot's `characters` and appears once
  - Each effect has at least one level
  - Each `conflict_level` is valid and appears once per character
  - Each `effect` sentence is present
- **Registration:** After validation, the scene write appends each new inline schema to the plot's `value_schemas` in the same transaction. This is a cross-entity write — the scene write must also update the plot.
- **Order of writes:** A draft's operations are applied one at a time, each committed before the next. A plot edit that adds a schema, placed before the scene edit that uses it, is visible to that edit's validator.
- The plan notes that the ordering notes in `core/entity.py` docstrings (`validate_scene_plot_roles`, `validate_scene_location`) are out of date — they say a plot created in the same draft is not visible, but the code shows it is (creates are committed before edits).

## Tasks

### 3.1 — Write `validate_scene_value_turns`
- [ ] New function in `core/entity.py`: `validate_scene_value_turns(project_path, value_turns, plot_characters=None)`
- [ ] If `plot_characters` is None, read the plot's `characters` from the DB
- [ ] Checks each turn:
  - [ ] The plot exists (reference check from Phase 1 handles this)
  - [ ] The value has a schema on that plot (existing in `plot.value_schemas` or supplied inline in `schema`)
  - [ ] If inline `schema` is supplied for a value that already has one: accepted if identical, refused if different (with a message showing the existing schema)
  - [ ] If no schema and no inline schema: refused with the plot's defined values and their words, saying to add a `schema`
  - [ ] `from` and `to` are words of that schema (case-insensitive, trimmed)
  - [ ] `effects` is not empty
  - [ ] Each effect's `character` is in the plot's `characters` and appears exactly once across all effects
  - [ ] Each effect has at least one level
  - [ ] Each `conflict_level` is in `CONFLICT_LEVELS` and appears once per character
  - [ ] Each `effect` sentence is present (non-empty)
  - [ ] Inline schema has four distinct words (p, c, c, nn all different)
  - [ ] Several inline schemas for the same value in one scene must agree
- [ ] Raises `ValueError` with actionable messages

### 3.2 — Wire into `create_entity`
- [ ] In `core/writes.py` `create_entity`, after the existing scene validation block (line 190-203), add a call to `validate_scene_value_turns`
- [ ] Pass the scene's `value_turns` from the merged frontmatter

### 3.3 — Wire into `edit_entity`
- [ ] In `core/writes.py` `edit_entity`, in the scene validation section, add a call to `validate_scene_value_turns`
- [ ] This needs to handle the merged state (stored + edited) the same way `dramatic_role`/`plot_roles` contradiction check does

### 3.4 — Implement inline schema registration
- [ ] After validation passes, for each turn with an inline `schema` that is new (value not yet in `plot.value_schemas`):
  - [ ] Append the schema to the plot's `value_schemas` in the same transaction
  - [ ] This happens in `create_entity` and `edit_entity` after the scene INSERT/UPDATE
  - [ ] Read the plot's current `value_schemas`, append the new one, write back
- [ ] If the same value appears in multiple turns in one scene with the same inline schema, register once
- [ ] If different inline schemas for the same value appear in one scene, refuse (validation catches this)

### 3.5 — Update the out-of-date docstring notes
- [ ] In `core/entity.py`, `validate_scene_plot_roles` docstring: remove the note about "a plot created in the SAME draft is not visible here"
- [ ] In `core/entity.py`, `validate_scene_location` docstring: same
- [ ] The plan says these notes are out of date — the code shows creates are committed before edits

### 3.6 — Write `tests/test_value_turns.py`
- [ ] Test: a valid turn passes validation
- [ ] Test: turn with no schema and no inline schema is refused with the plot's defined values
- [ ] Test: turn with inline schema for an existing value, identical — accepted
- [ ] Test: turn with inline schema for an existing value, different — refused with the existing schema
- [ ] Test: `from`/`to` not in schema words — refused
- [ ] Test: empty `effects` — refused
- [ ] Test: character not in plot's `characters` — refused
- [ ] Test: duplicate character in effects — refused
- [ ] Test: empty `levels` — refused
- [ ] Test: invalid `conflict_level` — refused
- [ ] Test: duplicate `conflict_level` per character — refused
- [ ] Test: empty `effect` sentence — refused
- [ ] Test: inline schema with non-distinct words — refused
- [ ] Test: multiple inline schemas for same value in one scene, agreeing — accepted
- [ ] Test: multiple inline schemas for same value in one scene, disagreeing — refused
- [ ] Test: `from` equal to `to` — allowed
- [ ] Test: inline schema is registered on the plot after write
- [ ] Test: registration happens in the same transaction (scene + plot both updated)

### 3.7 — Run test suite
- [ ] All existing tests still pass
- [ ] New `test_value_turns.py` passes

## Checklist

- [ ] `validate_scene_value_turns` written with all checks
- [ ] Wired into `create_entity`
- [ ] Wired into `edit_entity`
- [ ] Inline schema registration implemented
- [ ] Out-of-date docstring notes fixed
- [ ] `tests/test_value_turns.py` written and passing
- [ ] Full test suite passes
