# Value Tracking: Design for B1 and B2

Design document, Draft 2, October 12, 2026. Repository: hermes-story-architect, branch `feature/issue-redesign`, after Issue A. Scope: B1 and B2. Character arcs (B3) are out of scope.

## 1. Summary

Values are recorded on scenes as **turns**, defined by a **schema stored on the plot**, and read back on the plot. A turn is one shift of a value, plus how it lands on one protagonist. Nothing above the scene is stored or derived: the scene is the unit of observation.

## 2. Principles

1. Planning lives in entity sections. Execution is recorded on scenes. Verification is reasoning by the user and assistant, guided by the skill. No program judges the story.
2. Each turn states its own opening (`from`) and closing (`to`). Continuity between scenes is examined, not computed or enforced.
3. A value is defined once per plot, when it is identified there. A turn can only use words of that plot's schema.
4. A plot is edited only to introduce a value. Recording a turn never touches it.
5. No new entity types.

## 3. Data model

### 3.1 Ladder

| Rung | Code | Meaning | Example |
| --- | --- | --- | --- |
| 0 | P | Positive, the ideal | justice |
| 1 | C | Contrary: opposite, not absolute negation | unfairness |
| 2 | CD | Contradictory: direct negation of the positive | injustice |
| 3 | NN | Negation of negation: perversion or false version of the positive | tyranny |

The rung is looked up from the word and never stored. The source file defines C and CD as above. The notes in `ISSUES.md` have the two swapped.

### 3.2 Value schema: `plot.value_schemas` (stored)

| Field | Meaning |
| --- | --- |
| `value` | The value at stake (trust) |
| `p`, `c`, `cd`, `nn` | The story's words for the four rungs |
| `note` | Optional: what the value means in this plot |

Example: value trust, p loyalty, c complicity, cd betrayal, nn fanatic love.

- The four words are distinct. Words match case-insensitively and trimmed.
- Two plots that share a value each keep their own copy, on purpose.
- Renaming a word that turns use is a skill rule: update those turns in the same draft.

### 3.3 Value turn: `scene.value_turns` (stored)

A list on the scene, optional and empty by default. A scene is created without it, and the value pass fills it in later by editing the scene. Each entry is one shift of a value, with its effects on the protagonists nested inside. The Required column below applies inside an entry only: a recorded turn must be complete, but a scene needs no turns to exist.

| Field | Required | Meaning |
| --- | --- | --- |
| `plot` | yes | Slug of an existing plot |
| `value` | yes | A value with a schema on that plot, existing or supplied in `schema` |
| `from` | yes | The state when the scene opens, as a schema word |
| `to` | yes | The state when the scene closes, as a schema word |
| `schema` | no | Defines the value on the plot when it has none: `p`, `c`, `cd`, `nn` and an optional `note` |
| `effects` | yes | A list with one entry per protagonist the shift affects |
| `effects[].character` | yes | A protagonist of the plot, whether or not present in the scene |
| `effects[].levels` | yes | A list with one entry per conflict level through which the shift reaches that character |
| `effects[].levels[].conflict_level` | yes | Where the opposition comes from, relative to that character: `inner`, `personal` or `extra-personal` |
| `effects[].levels[].effect` | yes | One sentence: what the shift does to that character at that level |

Example: plot `main-plot`, value `trust`, from `loyalty`, to `betrayal`, with two effects. `marco`: level `personal`, effect `Marco feels betrayed by Dana`; level `inner`, effect `Marco doubts his own judgment of people`. `dana` (if she is also a protagonist): level `inner`, effect `Dana is consumed by guilt`.

- One entry per shift of a value in the scene. Characters who undergo exactly that shift share the entry. A different value, or a different shift of the same value, is another entry.
- An effect is one character. A character reached through several circles lists one level per circle, each with an effect focused on that level. A character appears once per entry, and a level once per character.
- `from` equal to `to` is allowed.
- To introduce a value, put its `schema` on the first turn that uses it. The write registers it on the plot. Later turns just name the value.
- `plot.characters` lists the plot's protagonists only. If protagonists diverge, each has the value that applies to them.

### 3.4 Read-back: `plot.value_lines` (computed, read-only)

For each value of the plot: its schema, and its turns in story order (scene id, from, to, and each affected character with their conflict levels). One retrieve of the plot tells the assistant which values exist, their vocabulary and where each stands. It is marked `computed: True`, so every write path refuses it.

### 3.5 Validation

Errors on write: the plot exists, the value has a schema on that plot (existing or supplied inline), `from` and `to` are words of that schema, `effects` is not empty, each effect's character is in the plot's `characters` and appears once, each effect has at least one level, each `conflict_level` is valid and appears once per character, and each `effect` sentence is present.

**The messages teach the vocabulary.** A turn whose value has no schema and no inline `schema` is refused with the plot's defined values and their words, and says to add a `schema`. An inline `schema` for a value the plot already defines is accepted if identical and refused if different. The refusal gives the existing one, for example: `trust already has a schema on main-plot: p loyalty, c complicity, cd betrayal, nn fanatic love. Remove schema from this turn and use these words.` A schema needs four distinct words, and several inline schemas for the same value in one scene must agree.

**Registration.** After validation, the scene write appends each new schema to the plot's `value_schemas` in the same transaction. The delete cascade in `core/writes.py` already updates other entities' stored data inside a transaction.

Order of writes: a draft's operations are applied one at a time, in order, each committed before the next (creates first, then edits). A plot edit that adds a schema, placed before the scene edit that uses it, is therefore visible to that edit's validator. This was checked by running such drafts on the branch. The ordering notes in the docstrings of `core/entity.py` (`validate_scene_plot_roles`, `validate_scene_location`) say otherwise and are out of date.

### 3.6 Shared shape validation

Today `_validate_shapes` (`core/entity.py`) only checks that a field with `sub_fields` is a list or an object. Nine fields declare `sub_fields`, in two forms: `character.relationships`, `scene.plot_roles` and `relationship.perspectives` use `{type, description}`, while the six plot beat fields use plain description strings. Nothing checks what is inside an entry, and enum and reference checks are written by hand per field (`validate_scene_plot_roles`, `validate_plot_characters`). `value_turns` needs all of this at three levels of depth, so the validation is rebuilt once and the existing fields move onto it.

**One declaration form.** Every sub-field is `{type, description}` plus optional `required`, `enum`, `ref` (an entity type) and its own `sub_fields`, recursively. The six plot beat declarations are converted from plain strings.

**One recursive shape validator** (`core/entity.py`, no database): the container type, that entries are objects, required keys, scalar types, `enum` membership, and the nested `sub_fields`. For an object-type field (`perspectives`) it applies the sub-fields to each value. Findings carry the path, for example `value_turns[0].effects[1].levels[0].conflict_level`. It runs wherever `validate_entity` runs, at stage and at write.

**One reference check** (reads the database, at write): every `ref` at any depth must name an existing record. It replaces the structural parts of `validate_scene_plot_roles` and `validate_plot_characters`.

**What stays bespoke.** Rules about meaning, not shape: `validate_scene_value_turns` (schema words, protagonist membership, inline schema), `validate_scene_dramatic_role`, and the relation checks `validate_scene_act_id`, `validate_scene_location` and `validate_arc_parents`.

**Existing behaviour does not tighten.** `required` is declared only where a validator already requires it (`plot` and `role` in `plot_roles`).

**Tests become schema-driven.** One test walks every declared field and checks that a wrong shape is reported, so a future nested field is covered automatically. A consistency test checks that every `sub_fields` entry has a `type`, every `enum` is non-empty and every `ref` names an entity type. `test_story_describe.py` recurses into nested sub-fields, and a nested round trip through export and import is added.

## 4. Removals

| Remove | Replaced by |
| --- | --- |
| `project.story_value`, `story_value_at_open`, `story_value_at_close` | The values of the main plot (`value_lines`) |
| `act.value_at_open`, `act.value_at_close` | Nothing stored. Read from the scenes. |
| `sequence.value_at_open`, `sequence.value_at_close` | Nothing stored. Read from the scenes. |
| `scene.value_at_open`, `value_at_close`, `shift`, `y`, `conflict_levels` | `scene.value_turns` |
| `get_value_drift`, `_has_charge` (`core/db.py`), `view='story_value'`, `_SCENE_CURVE` (`tools/story_load.py`) | Nothing |

Kept until B3: `character_value*`, the arc beat fields and `VALUE_CHARGES`. The story curve in the current graph goes empty, which is accepted.

No migration script. The app is not deployed, so strip the old fields and run the value pass on the fixture and the test project.

## 5. Skill guidance

**Value pass.** A separate step, never part of creating the scene. Before writing: brainstorm from the plot's schemas and lines, recording nothing. During writing: advice only. After the scene exists: record the turns.

**Before recording.** Retrieve the plots the scene serves in one call: `story_retrieve` with `entity_type` plot, the plot ids, and `fields` set to `value_schemas` (add `value_lines` to see where each value stands). For each value in the scene, use an existing value if it genuinely fits and say why. A near match is not a reason to define a new one. If none fits, define it by adding `schema` (the four words) to the first turn that uses it. The write registers it on the plot.

**Opening states.** Default to the last recorded state of that value. Open elsewhere only when the scene itself shows a different state: a flashback or nonlinear telling, a time skip, a different counterpart or place, or a scene that reveals an earlier change. Say which in `effect`. An unexplained difference is a break to fix.

**After inserting, moving or deleting scenes.** Compare the neighbouring turns' `from` and `to` in `value_lines`, read the scenes that may need a rewrite, and note them as `continuity_warnings`.

**The positive side.** The ladder grades antagonism, so P has nothing above it.

- Earned or naive: a P reached after visiting C, CD or NN is earned, and its depth is the deepest rung visited. Read it from `value_lines`.
- Beyond P: the value usually changes (justice becomes mercy). Define a successor value on the plot.
- Deepening: before recording `from` equal to `to`, check whether the change is in how it lands on the character (the conflict level and `effect`) and not in the value.

**Planning.** Discuss the values at play when creating plots, acts, sequences and scenes, and record the plan in the entity's sections.

**Roll-up and irony.** Sequence, act and story summaries are read from `value_lines` by reasoning. Irony needs B3 (what the character believes versus what is true).

## 6. Work plan

| Step | Work |
| --- | --- |
| 0 | Install pytest, run the suite on the branch, record the baseline, and list every test that mentions the removed fields. |
| 1 | Shared shape validation (section 3.6): the single declaration form, the recursive validator, the reference check, migration of the nine existing `sub_fields` fields and `plot.characters`, and the schema-driven tests. |
| 2 | Constants: add `plot.value_schemas` and `scene.value_turns` (with the optional `schema` and nested `effects` and `levels`), the ladder and level constants, and narrow the description of `plot.characters` to protagonists. |
| 3 | `validate_scene_value_turns` and the three scene call sites in `core/writes.py` (section 3.5), the registration of inline schemas on the plot, and `tests/test_value_turns.py`. |
| 4 | Computed `plot.value_lines` in `core/db.py`, exposed through plot retrieve, describe and load. Make the scene payload builders carry `value_turns`. |
| 5 | Remove the old fields and code (section 4). Update fixtures, tests and sample data. |
| 6 | Update the skill (section 5). |
| 7 | Run the value pass over the fixture and the test project. Note anything the model cannot express. |

## 7. Files affected

- `core/constants.py`: convert the six plot beat `sub_fields` declarations to the dict form, declare `required`, `enum` and `ref` on the existing fields, add the plot, scene, project, act and sequence changes with the nested `effects`, `levels` and `schema` declarations, and the ladder and level constants.
- `core/entity.py`: the recursive shape validator replacing `_validate_shapes`, the reference check, `validate_scene_value_turns`, and the removal of the structural parts of `validate_scene_plot_roles` and `validate_plot_characters`. Remove the `value_at_open` and `value_at_close` enum validators and `_validate_y`.
- `core/writes.py`: the three scene validation call sites, the call to the reference check, and the registration of inline schemas on the plot inside the scene's transaction.
- `core/db.py`: add `value_lines`, and make the payload builders that copy scene fields one by one (around lines 800 and 1175) carry `value_turns`. Remove `get_value_drift`, `_has_charge` and the old payload fields.
- `tools/story_load.py`: remove `view='story_value'`, `_SCENE_CURVE` and the `unfilled` drift output.
- `tools/story_describe.py`: no change expected, since it copies nested `sub_fields` and the new keys. Confirm in the tests.
- Dashboard: no changes planned. The story curve and the `conflict_levels` tag (`entity-panels.js`, line 454) go empty. The plots view and entity panel show `plot.characters` as tags, which now list protagonists only. Check that the page still loads with the sample data in `data-load.js`.
- Tests: rewrite `test_write_shape.py` as schema-driven, add the consistency test and `tests/test_value_turns.py`, update `test_story_describe.py`, `test_field_coverage.py` and `test_scene_plot_roles.py`, add a nested round trip through export and import, and update the `save-the-children` fixtures that carry the removed fields.

## 8. To verify during implementation

- That the stricter validator does not reject existing data: run it over the fixture and the test project before declaring any `required`.
- That `story_retrieve` with `fields=['value_schemas']` and with `fields=['value_lines']` returns the stored and the computed plot fields.
- That nested `effects` and `levels` survive markdown export and import, `unfilled` and draft preview (the nested round-trip test).
- That `unfilled` treats `value_turns` as expected.
- That importing older markdown with removed keys is tolerated with a warning (`tools/story_import.py`).
- The size of `value_lines` on a long plot. If it is too large, add a narrow per-scene view.
- That narrowing `plot.characters` to protagonists breaks nothing else.

## 9. Later

- Use the new `ref` declaration to replace the description-word heuristic in `story_describe._is_reference`, which its own comment says a real flag would retire.
- A guard on direct edits of `value_schemas`: refuse removing a value, or changing a word, that existing turns use.
- Compact schemas in the `story_load` plot entries, so no retrieve is needed to see them.
- A narrow per-scene view (`values_context`): the schemas and neighbouring turns for one scene.
- An overview view: roll-up per sequence, act and story, jumps in opening states, earned depth.
- Warnings: a turn's plot with no `plot_roles` entry on the scene, and turns on planned scenes.
- The new value graph (UI).
- B3: the arc beat built on the per-character effect, including irony.
