# Values: Shared Schemas and Major and Minor Lists

Design document, Draft 2, October 12, 2026. Repository: hermes-story-architect, branch `feature/issue-redesign`. Replaces the earlier ranking draft.

## 1. Goal

Answer, from the scenes alone, which values are major and minor in a plot, sequence, act and story, and give an agent a small, targeted view for evaluating values. Schemas move out of the plot into their own entity, so viewing a plot loads none.

## 2. Fix first

Two defects in `compute_value_lines` (`core/db.py`), found by running it. The counts below depend on both.

1. It does not filter turns by plot. A main plot and a subplot that both define `trust` each showed the other's scenes.
2. Its story order ignores acts, because sequence order keys restart in each act. An act 2 scene sorted before act 1 scenes. The correct act, sequence, scene order is already used near line 1564.

One shared helper returns every scene's turns with plot, act, sequence and order. Everything below uses it.

## 3. The value entity

A new entity type, one per value. The id is the slug of the name.

| Field | Meaning |
| --- | --- |
| `name` | The value, named by its positive pole (trust) |
| `p`, `c`, `cd`, `nn` | The story's words for the four rungs. Four distinct words. |
| `note` | Optional |

- A value has one schema wherever it is used. A different meaning needs a different value (loyalty rather than trust). Names match case-insensitively and trimmed.
- **Export and import:** all values are one file, `values.md`, at the project root, with one entry per value. The database holds one entity per value.
- **Creating a value:** a value must exist before a shift can name it. It is created like any entity, with `story_draft`, and can go in the same draft as the scene edit, since a draft applies creates before edits. There is no schema on the scene.
- **A shift naming an unknown value** is refused. The message lists the defined values and their words and says to create the value first.
- **Removed:** `plot.value_schemas`, `plot.value_lines` (their content moves to the values view) and the inline `schema` on a turn.

## 4. Major and minor values

A computed field `value_focus` with two lists, `major` and `minor`. Each item is a value and the number of scenes in which it shifts. Nothing is stored.

- **Count** the scenes in which a value has a shift, inside the unit. A scene counts once per value.
- **Major** is the three most frequent values, with ties at the cut all major. **Minor** is the rest. The cut is a constant, `VALUE_MAJOR_COUNT`.
- **Plot:** the shifts in that plot's scenes only.
- **Sequence:** the shifts in the scenes of that sequence, all plots together, with no main or sub distinction.
- **Act:** the shifts in the scenes of all the act's sequences, all plots together, with no main or sub distinction.
- **Story (project):** major is the main plot's major list. Minor is the subplots' major values that are not already major.

Read with `story_retrieve` on a plot, sequence, act or project, with `fields=['value_focus']`.

## 5. The values view

`story_load view='values'`, built for three uses and nothing more.

| Call | Returns |
| --- | --- |
| no arguments | Every value with its schema. The one command to see what exists. |
| `scene=<id>` | First, the major and minor values of the scene's sequence and of its act. Then, for each plot the scene serves (its `plot_roles`, else its sequence's primary plot): the plot's values with schemas, and for each value where it was last left (scene, closing word) and the next turn after (scene, opening word). Used before evaluating a scene. |
| `plot=<id>`, `sequence=<id>` or `act=<id>`, optionally `value=<name>` | The major and minor lists, and for each value its turns in story order (scene, plot, from, to). |

## 6. Plan

| Step | Work |
| --- | --- |
| 1 | Fix the two defects and add the shared helper. Tests: two plots sharing a value name; scenes across acts. |
| 2 | The `value` entity type: constants, validation (four distinct words), create, edit, retrieve, describe, admin. About eight files, as `arc_beat` shows. |
| 3 | Export and import of `values.md` (`tools/story_export.py`, `tools/story_import.py`), with a round-trip test. |
| 4 | Move the schemas: `validate_scene_value_turns` (`core/entity.py`) and `_check_value_turns` (`core/writes.py`) read value entities and no longer register anything on write. Remove `plot.value_schemas`, `plot.value_lines`, the inline `schema` handling and the payload builders that carry them. |
| 5 | Computed `value_focus` on plot, sequence, act and project, with unit tests on a small project with known counts. |
| 6 | The values view (section 5). |
| 7 | Skill: use the view with `scene` before recording, `value_focus` before writing into a sequence or act, and the rule for values: check the existing ones first, and if none fits, create the value, then record the shift. |
| 8 | Convert the `save-the-children` fixture and the test project: move each plot's schemas into `values.md`, merging identical ones. |

## 7. To verify

- That `story_retrieve` returns a computed field requested by name for all four types, and fetches value entities by id.
- That a draft with a `create` of a value followed by an `edit` of a scene naming it commits, since creates are applied before edits.
- The size of the values view on a long story.

## 8. Later

- Top values in the `story_load` plot, act and sequence entries.
- Weigh by size of shift if counts prove misleading.
- A dashboard view.
