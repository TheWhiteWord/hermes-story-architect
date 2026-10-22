# Phase 4 — Move the schemas off the plot; turns name value entities

Refactor plan: `../Value Profile Ranking Values by Plot, Act, Sequence and Story.md`, §3 ("Removed") and §6 step 4.
Depends on: **Phase 2 + Phase 3** (value entities exist and round-trip). This is the deletion phase — after it, `plot.value_schemas`, `plot.value_lines`, and the inline `schema` on a turn no longer exist. No backward compatibility (project rule).

## Verification against code — full cut list (done)

Every site that reads/writes the three removed things, confirmed:

**`plot.value_schemas` (stored on plot, registered on scene write):**
- `core/constants.py:151-160` — schema declaration + sub_fields → **remove**
- `core/db.py:312` — read in `compute_value_lines` → replaced in Phase 1; **now reads value entities instead**
- `core/db.py:1174` — dashboard/plot payload builder → **remove line**
- `core/entity.py:896` — `validate_scene_value_turns` reads plot schemas → **rewrite to read value entities**
- `core/writes.py:885,907,912-919` — `_check_value_turns` registration block → **remove the registration half**
- `tools/story_export.py:189` — pops PLOT_BEAT_FIELDS only, not value_schemas; value_schemas flows to the note via extra → **confirm it no longer exports** (it won't, once the field is gone from the schema/extra)

**`plot.value_lines` (computed read-back):**
- `core/constants.py:164-165` — declaration → **remove**
- `core/db.py:286-367` `compute_value_lines` → **delete the function** (superseded: schemas now live on value entities; the "lines" read-back is replaced by the values view, Phase 6)
- `core/db.py:688-689,702,709` — `get_project_summary` per-plot `value_lines` → **remove**
- `core/db.py:1175` — dashboard builder → **remove line**
- `tools/story_retrieve.py:119-122` — computed-field branch for plot `value_lines` → **remove**

**Inline `schema` on a turn:**
- `core/constants.py:224` — turn's `schema` sub-field declaration → **remove**
- `core/entity.py:918-967` — the entire inline-schema acceptance + "already has a schema" + "words must agree" logic → **remove**
- `core/writes.py:866-888` (`_as_stored`) and `895-919` (registration) → **remove**

**No inconsistency found.** The plan's "Removed" list is exactly the consumer list. One downstream consequence is flagged below (Phase 5 dependency).

## New rule after this phase

A turn's `value` must name an existing `value` entity. No inline definition, no per-plot registration. `validate_scene_value_turns` becomes: plot exists → value entity exists (by case-insensitive name match against `value` entities) → `from`/`to` are words of **that value entity's** p/c/cd/nn → effects name plot protagonists (unchanged).

## Tasks

### T4.1 — `validate_scene_value_turns` rewrite (`core/entity.py:867-967`)
- [x] Load `value` entities once: `SELECT id, name, extra FROM entities WHERE type='value' AND is_deleted=0` → map `name.lower() → {p,c,cd,nn}`.
- [x] Per turn: keep the plot-exists and effects/conflict-level checks unchanged.
- [x] Replace the schema lookup: resolve the turn's `value` (trimmed, case-insensitive) against the value-entity map.
  - [x] **Unknown value → refuse.** Message lists the defined values and their words and says to create the value first (plan §3). Format like the existing "Defined values: ..." message (`entity.py:928-931`).
  - [x] `from`/`to` must be words of the resolved value entity's four rungs (reuse the `words` dict the current code builds, now sourced from the entity).
- [x] Delete: the `inline`/`registered` branching, the "already has a schema on {plot}" refusal, the "four distinct words" inline check (now only on the value entity, Phase 2), and the same-scene "words must agree" `seen` bookkeeping (a value has one schema now, so two turns can't disagree).
- [x] `VALUE_LADDER` (`constants.py:29`) still names the rungs — reference it, don't restate.

### T4.2 — `_check_value_turns` strip (`core/writes.py:844-919`)
- [x] Delete `_as_stored` (`866-888`) and the registration loop (`895-919`). The function collapses to: validate via `validate_scene_value_turns`, nothing else. If it becomes a one-liner, inline the call at its three call sites (`writes.py:270,414,476`) and delete the helper.
- [x] Update the `register=False` pre-transaction pass reasoning in the docstring — there is no registration to defer anymore. The edit-path re-check at `writes.py:475-476` stays (re-validation of stored turns is still wanted, minus the schema-stripping).

### T4.3 — Delete `compute_value_lines` and its consumers (`core/db.py`, `tools/story_retrieve.py`)
- [x] Remove the function (`db.py:286-367`).
- [x] `get_project_summary`: remove `plot_value_lines` (`688-689`), the `value_lines` key in `_build_plot` (`702`), and `"value_lines": []` from `_omit` (`709`).
- [x] Dashboard builder `db.py:1174-1175`: remove both `value_schemas` and `value_lines` lines.
- [x] `tools/story_retrieve.py:119-122`: remove the plot `value_lines` computed-field branch.
- [x] Confirm `get_scene_value_turns` (Phase 1) has no remaining caller in `db.py` — it is now used only by Phase 5's `value_focus`. If nothing calls it after this deletion, that is expected; do not delete the helper.

### T4.4 — Schema declarations (`core/constants.py`)
- [x] Remove `plot.value_schemas` (`151-160`) and `plot.value_lines` (`164-165`) blocks.
- [x] Remove the turn's `schema` sub-field (`224`).
- [x] Update the `value_turns` description (`218-221`) to say the value must name an existing value entity, no inline schema.

### T4.5 — Tests: delete and rewrite
- [x] **Delete** `TestTheSchema`, `TestTheInlineSchema`, `TestRegistrationOnWrite` in `tests/test_value_turns.py` — they test the removed inline/registration behavior. (Plan rule: refactor or replace, and here replacement is the honest option.)
- [x] **Rewrite** the value-resolution tests against value entities:
  - [x] A turn naming an existing `value` entity passes.
  - [x] A turn naming an unknown value → refused, message lists defined values + words + "create the value first."
  - [x] `from`/`to` outside the value entity's words → refused (keep the two existing assertions, retargeted).
  - [x] Case/whitespace-insensitive name match to the value entity.
  - [x] A value defined in the **same draft** as the scene edit commits (creates-before-edits, `drafts.py:22` OP_ORDER) — the plan §7 verification item.
- [x] **Keep** `TestTheEffects` unchanged (character/level checks are untouched).
- [x] Delete `TestTheReadBack` tests that assert `value_lines` shape (`284,297,307,313,325,332`) — the read-back is gone; the values view (Phase 6) replaces it. Any pure "story order" assertion moves to the Phase 1 helper test if not already there.
- [x] Grep the whole suite for `value_lines`/`value_schemas`/`"schema"` and remove/adjust stragglers (`tests/test_core.py`, `test_export_sweep.py`, `test_field_coverage.py`, `test_story_describe.py`, `test_write_shape.py`, `live_value_pass.py`, `value_pass_b1_b2.py`).

### T4.6 — Verify no orphan references
- [x] `grep -rn "value_schemas\|value_lines\|compute_value_lines\|turn.*schema\|\"schema\"" core/ tools/ tests/` returns nothing (outside unrelated `SCHEMA`/tool-schema hits).

## Cleanup / legacy
- [x] This phase **is** the cleanup: three removed fields, one deleted function, one gutted validator, one deleted test class. No compatibility shim — `plot.value_schemas` in an existing DB is simply ignored after this (the migration in Phase 8 handles the live project and fixture).
- [x] After deletion, the fixture's `The Resistance.md` still carries `value_schemas` in frontmatter → import will now **refuse unknown plot fields**. That is expected and fixed in Phase 8 (fixture conversion). Note it here so the suite red-until-Phase-8 is understood, not a surprise.
  - **Resolved in this phase.** Per the implementer note, Phase 8's fixture conversion landed with Phase 4 so the branch is never left red: `tests/fixtures/save-the-children/values.md` created (`freedom`, `trust`), `value_schemas` stripped from `plots/The Resistance.md`. The suite is fully green (1123 passed). The live-project conversion (T8.3) remains Phase 8's work.

## Checklist
- [x] `validate_scene_value_turns` resolves turns against value entities; unknown value refused with a teaching message
- [x] `_check_value_turns` registration + `_as_stored` gone; edit-path re-validation retained
- [x] `compute_value_lines`, `value_schemas`, `value_lines`, inline `schema` fully deleted across db/retrieve/constants
- [x] value-resolution tests rewritten against value entities; same-draft create+edit commits
- [x] obsolete test classes deleted, suite grepped clean of the three removed names
- [x] full suite green **except** fixture-frontmatter refusals that Phase 8 fixes (document which)
  - No fixture-refusal red state: the fixture conversion landed with this phase. Full suite **1123 passed, 0 failed**.

## Notes for the implementer
- **Depends on Phases 2 + 3.** Not parallel — it deletes what 2/3 build on and must land after them.
- **Phase 5 dependency:** `value_focus` counts "scenes in which a value shifts," reading turns' `value` names — exactly what `get_scene_value_turns` (Phase 1) already returns. Phase 5 does not need `value_lines`. So deleting `compute_value_lines` here is safe; the helper survives.
- The suite will be red between this phase and Phase 8 (fixture still carries `value_schemas`). Land Phase 8's fixture conversion in the same PR, or sequence Phase 4 immediately before Phase 8, so the branch is never left failing.

## Final brief (implementation complete)

The schemas are off the plot. A turn's `value` now names a `value` entity; the plot registers nothing, and `compute_value_lines` is gone.

**The validator (`core/entity.py`).** `validate_scene_value_turns` loads the plots (`characters`) and every `value` entity once, keyed `name.lower() → {p, c, cd, nn}` (the name is a column, `p/c/cd/nn` are extra — the first version read `name` from extra and the tests caught it). Per turn: plot exists → value resolves against the map (case/whitespace-insensitive) → `from`/`to` are words of that value's rungs → effects/conflict-levels unchanged. An unknown value is refused with the defined values, their words, and "Create the value first (story_draft create type='value')". The inline/registered branching, the "already has a schema" refusal, the inline distinct-words check, and the same-scene "words must agree" `seen` bookkeeping are all deleted. `VALUE_LADDER` still names the rungs; `_schema_words`/`_defined_values` now take the words map directly.

**The write path (`core/writes.py`).** `_check_value_turns` became exactly `validate_scene_value_turns(project_path, turns)` — a pass-through — so per the task's own instruction it is deleted and the validator is called directly at the three call sites (create inside the transaction; edit's pre-BEGIN merged-state re-check; edit's inside-transaction pass). The dead `conn` parameter goes with it. Edit-path re-validation of stored turns is retained.

**Deletions.** `compute_value_lines` (`core/db.py`); `get_project_summary`'s `plot_value_lines` + the `value_lines` key and its `_omit` entry in `_build_plot`; the dashboard builder's `value_schemas`/`value_lines` lines; `story_retrieve`'s computed-field branch (and its now-orphaned `_project_path` helper). `get_scene_value_turns` survives with no `db.py` caller, as planned — Phase 5's `value_focus` will use it.

**Constants (`core/constants.py`).** `plot.value_schemas` and `plot.value_lines` blocks removed; the turn's `schema` sub-field removed; `value_turns`/`value` descriptions now say the value must name an existing value entity. The `VALUE_LADDER` comment updated off `plot.value_schemas`.

**Tests.** `tests/test_value_turns.py` rewritten: `TestTheValueEntity` (defined-value pass, unknown-value refusal with the teaching message, case/whitespace match, the §7 same-draft create+edit commit, refused create writes nothing, unrelated-edit re-check, orphaned-turn refusal), `TestTheWords` (from/to outside the value, missing plot), `TestTheEffects` kept unchanged. `TestTheSchema`/`TestTheInlineSchema`/`TestRegistrationOnWrite`/`TestTheReadBack` deleted. Stragglers fixed: `test_plot_roles` (schema-order assertion retargeted — the plot no longer carries value fields), `test_export_sweep` (value_schemas export-order test removed with the field), `test_field_coverage` (value_schemas sample branch removed), `test_core`/`test_write_shape` (comments off the removed model), `test_retrieve_reading` (plot field-order list), `test_story_describe` (value_lines/schema known-keys), `test_edit_silent_success` (the value.name probe renames to a name that slugs to the sample id — Phase 2's id==slug invariant makes a bare "PROBE" a correct refusal), `test_values_export_import` (dropped the manual freedom create — the fixture now supplies it). `value_pass_b1_b2.py` deleted (superseded harness); `live_value_pass.py` left for Phase 8 (it migrates the live project and is a `__main__` script, not in the suite).

**Fixture converted with this phase.** Per the implementer note ("never leave the branch red"), Phase 8's fixture conversion landed here: `tests/fixtures/save-the-children/values.md` created with `freedom` and `trust` (id/name/p/c/cd/nn/note), `value_schemas` stripped from `plots/The Resistance.md`. Without it the fixture import refused the now-unknown plot field and ~340 tests errored at fixture setup. The 3 fixture scenes' `freedom`/`trust` turns resolve against the new entities by name, untouched. The live-project conversion (T8.3) remains Phase 8's work.

**Verification.** Full suite **1123 passed, 0 failed** (baseline was 1142 before this phase's test deletions; net −19 from removed obsolete classes/tests, +1 fixture value import). Orphan grep clean across `core/ tools/ src/ tests/` for `value_schemas`/`value_lines`/`compute_value_lines`; the only remaining hits are in `tests/live_value_pass.py` (the Phase 8 live-project harness). Also deleted a now-dead non-keyed `object` branch in `_validate_field` (`perspectives` is the only `object` field and it is keyed).

**Skipped:** the Phase 8 migration script (`tools/migrate_values.py`) — Phase 8's T8.1, not needed for the fixture (two values, hand-converted) or the live project until Phase 8 runs. `live_value_pass.py` left intact for Phase 8's T8.3.
