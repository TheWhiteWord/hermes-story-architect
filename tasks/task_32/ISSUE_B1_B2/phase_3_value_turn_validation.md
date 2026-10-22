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
- [x] New function in `core/entity.py`: `validate_scene_value_turns(project_path, value_turns, plot_characters=None)`
- [x] If `plot_characters` is None, read the plot's `characters` from the DB
- [x] Checks each turn:
  - [x] The plot exists (reference check from Phase 1 handles this)
  - [x] The value has a schema on that plot (existing in `plot.value_schemas` or supplied inline in `schema`)
  - [x] If inline `schema` is supplied for a value the plot already has: refused, identical or not (message shows the existing schema and says to remove `schema` from the turn)
  - [x] If no schema and no inline schema: refused with the plot's defined values and their words, saying to add a `schema`
  - [x] `from` and `to` are words of that schema (case-insensitive, trimmed)
  - [x] `effects` is not empty
  - [x] Each effect's `character` is in the plot's `characters` and appears exactly once across all effects
  - [x] Each effect has at least one level
  - [x] Each `conflict_level` is in `CONFLICT_LEVELS` and appears once per character
  - [x] Each `effect` sentence is present (non-empty)
  - [x] Inline schema has four distinct words (p, c, c, nn all different)
  - [x] Several inline schemas for the same value in one scene must agree
- [x] Raises `ValueError` with actionable messages

> **Implementation note (3.1):** the smoke harness caught two real bugs before any write path ran — `_schema_words` was returning a display string that the `from`/`to` check then called `.values()` on, and the `seen` agreement check stored a dict in a set (unhashable). `words` is now a dict end to end and the set carries `frozenset(words.items())`. A later turn in the same scene with no inline `schema` inherits the words an earlier turn in that scene defined, since registration (3.4) lands the schema on the plot only after the write.

### 3.2 — Wire into `create_entity`
- [x] In `core/writes.py` `create_entity`, after the existing scene validation block (line 190-203), add a call to `validate_scene_value_turns`
- [x] Pass the scene's `value_turns` from the merged frontmatter

### 3.3 — Wire into `edit_entity`
- [x] In `core/writes.py` `edit_entity`, in the scene validation section, add a call to `validate_scene_value_turns`
- [x] This needs to handle the merged state (stored + edited) the same way `dramatic_role`/`plot_roles` contradiction check does

### 3.4 — Implement inline schema registration
- [x] After validation passes, for each turn with an inline `schema` that is new (value not yet in `plot.value_schemas`):
  - [x] Append the schema to the plot's `value_schemas` in the same transaction
  - [x] This happens in `create_entity` and `edit_entity` after the scene INSERT/UPDATE
  - [x] Read the plot's current `value_schemas`, append the new one, write back
- [x] If the same value appears in multiple turns in one scene with the same inline schema, register once
- [x] If different inline schemas for the same value appear in one scene, refuse (validation catches this)

### 3.5 — Update the out-of-date docstring notes
- [x] In `core/entity.py`, `validate_scene_plot_roles` docstring: remove the note about "a plot created in the SAME draft is not visible here"
- [x] In `core/entity.py`, `validate_scene_location` docstring: same
- [x] The plan says these notes are out of date — the code shows creates are committed before edits

> **Implementation note (3.2–3.5):** verification corrected the task file's premises before any code landed. `edit_entity` has ONE scene validation section, not three sites: the "line 473-487 block" is the `plot_roles` relation write, not a validator. The stale ordering note exists only in `validate_scene_location` (verified by grep — `validate_scene_plot_roles`'s docstring carries none, Phase 1 rewrote it). The design's ordering claim was confirmed by running a same-draft create of location→scene through stage+commit: `location_id` lands, so the note was removed.
>
> Wiring detail: the task says "three call sites" but both writes now route through ONE helper, `_check_value_turns(conn, project_path, value_turns, register=True)` in `core/writes.py`, which validates then registers. `create_entity` was autocommit — its INSERT/sections/relations committed statement-by-statement, so the registration's plot UPDATE would have landed outside the scene write; the write block now wraps everything in one explicit `BEGIN`/`COMMIT`. On edit, validation runs pre-`BEGIN` (a refusal writes nothing) and registration runs inside the transaction after the scene's `extra` UPDATE.
>
> One real behavior gap choice (A) exposed, fixed here: re-validating stored turns on every scene edit would refuse every later edit with "already has a schema", because the stored turn still carries the `schema` key that registered the value. The pre-transaction pass strips `schema` from any turn whose plot already defines the value (`_as_stored`); new turns pass through unchanged so a duplicate definition is still refused.

### 3.6 — Write `tests/test_value_turns.py`
- [x] Test: a valid turn passes validation
- [x] Test: turn with no schema and no inline schema is refused with the plot's defined values
- [x] Test: turn with inline schema for an existing value — refused with the existing schema (identical or not)
- [x] Test: `from`/`to` not in schema words — refused
- [x] Test: empty `effects` — refused
- [x] Test: character not in plot's `characters` — refused
- [x] Test: duplicate character in effects — refused
- [x] Test: empty `levels` — refused
- [x] Test: invalid `conflict_level` — refused
- [x] Test: duplicate `conflict_level` per character — refused
- [x] Test: empty `effect` sentence — refused
- [x] Test: inline schema with non-distinct words — refused
- [x] Test: multiple inline schemas for same value in one scene, agreeing — accepted
- [x] Test: multiple inline schemas for same value in one scene, disagreeing — refused
- [x] Test: `from` equal to `to` — allowed
- [x] Test: inline schema is registered on the plot after write
- [x] Test: registration happens in the same transaction (scene + plot both updated)

> **Implementation note (3.6):** 24 tests in five classes — the validator's rules (unit), and the two write paths' registration + refusal atomicity (integration). The registration tests assert the plot's `value_schemas` list after a create and an edit; the refusal tests assert neither the scene nor the plot changed, which is what "same transaction" means on a path whose failure mode would otherwise be a registered schema with no turn.

### 3.7 — Run test suite
- [x] All existing tests still pass
- [x] New `test_value_turns.py` passes

> 1115 passed / 9 failed — the 9 are the pre-existing value-system failures Phase 5 removes/rewrites, unchanged from the Phase 2 baseline (1091 + 24 new). `test_field_coverage.py` needed one fix: `_sample_value` returns `["item-1", "item-2"]` for any list, which `scene.value_turns` rejects (a turn names a plot this bare-DB fixture has none of) — now special-cased to `[]`, exactly as `plot_roles` already is.

## Checklist

- [x] `validate_scene_value_turns` written with all checks
- [x] Wired into `create_entity`
- [x] Wired into `edit_entity`
- [x] Inline schema registration implemented
- [x] Out-of-date docstring notes fixed
- [x] `tests/test_value_turns.py` written and passing
- [x] Full test suite passes

---

## Final Brief

Phase 3 complete. `validate_scene_value_turns` (`core/entity.py`) checks every part of a turn against the plot it names — plot exists, value has a schema (registered or inline), `from`/`to` are schema words, effects name protagonists once each through one level per conflict circle with a present sentence — and both scene write paths validate the merged state and register new inline schemas on the plot in one transaction. 1115 tests pass; the 9 failures are the pre-existing value-system ones Phase 5 removes.

**What changed:**
- `core/entity.py`: `validate_scene_value_turns(project_path, value_turns)` — reads plots, `characters` and `value_schemas` from the DB, raises on the first violation with the plot's vocabulary in the message. Helpers `_schema_words`/`_defined_values` render that vocabulary. `validate_scene_location`'s stale "SAME draft is not visible" ordering note removed (verified by running a same-draft create of location→scene through stage+commit: it lands).
- `core/writes.py`: `_check_value_turns(conn, project_path, value_turns, register=True)` — one helper both writes route through: validate, then register each inline schema whose value the plot lacks, inside the caller's transaction. `create_entity`'s write block now runs in one explicit `BEGIN`/`COMMIT` (it was autocommit, so the registration's plot UPDATE would have committed alone); on edit, validation runs pre-`BEGIN` and registration inside, after the scene's `extra` UPDATE.
- `tests/test_value_turns.py`: 24 tests — validator rules plus registration/refusal atomicity on both write paths.
- `tests/test_field_coverage.py`: `_sample_value` special-cases `value_turns` to `[]` (a turn needs a plot the bare fixture has none of), mirroring `plot_roles`.

**Deviations from the task spec:**
- **Task file's "three scene call sites" is wrong.** `edit_entity` has ONE validation section; the "line 473-487 block" is the `plot_roles` relation write, not a second validator. Both writes route through one helper instead.
- **`validate_scene_value_turns` signature lost `plot_characters`.** The spec's param was unusable as written: it holds one plot's characters, but a scene's turns can span plots, and the validator already reads each turn's own plot. Removed rather than left dead.
- **Merged re-validation strips consumed `schema` keys.** Under choice (A) a stored turn still carrying its registration-time `schema` would refuse every later edit ("already has a schema"); the pre-transaction pass drops `schema` from turns whose plot already defines the value.
- **`create_entity` gained an explicit transaction.** Autocommit made "registration in the same transaction" impossible on create; the write block now wraps INSERT→sections→relations→registration in one BEGIN/COMMIT. Behavior otherwise unchanged (rollback path already existed).

**Verified by running, not by reading:** 19 validator cases via a direct-call harness (caught two real bugs: display-string `.values()` crash and an unhashable dict in the agreement set — both fixed before any test file existed); 7 end-to-end write cases (registration lands, refusals leave nothing, unrelated edits re-check stored turns); the same-draft ordering claim confirmed with a live stage+commit.

**Ready for Phase 4:** computed `plot.value_lines` and the scene payload builders carrying `value_turns`. Note: `value_lines`'s turns should read each scene's `value_turns` in story order — the registration above guarantees every turn's value has a schema on its plot, so the line can render `from`/`to` with no lookup.
