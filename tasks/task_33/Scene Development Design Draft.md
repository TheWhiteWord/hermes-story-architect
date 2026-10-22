DW# scene\_beats: Design Draft

Draft for review, 19 October 2026. Entity name: `scene_beats`. Nothing here is implemented.

## 1. Purpose

Replace `arc_beat` with `scene_beats`, a record of how a scene works: who drives it, how its beats of action and reaction unfold, and what they change. The scene entity keeps what happens (structure and results). `scene_beats` keeps how and why. Character state and escalation are read across scenes from this record. They are not stored on characters.

## 2. Scope

**In scope**

- The `scene_beats` entity.
- The scene fields it feeds.
- Retirement of `arc_beat` and the character arc fields that duplicate scene values.

**Deferred**

- Character field refinement (conscious and unconscious desire, worldview, goals).
- A `story_load` view that packages context for working on a scene’s beats.
- Relationship and world readers.
- Character-track readers and any visualisation.

## 3. Principles

1. **Scene holds conclusions, `scene_beats` holds dynamics.** The scene is structural position and recorded result. `scene_beats` is the mechanism behind it.
2. **Any writing direction.** Structure-first, content-first, or mixed. Scene fields may hold intent or observation, and the scene `status` says which.
3. **Duplication is allowed.** Fields shared by the scene and `scene_beats` keep identical names. Drift is not enforced. The skill tells the agent to reconcile after reworking `scene_beats`.
4. **Referenced entities must exist.** This forces the agent to retrieve them before writing.
5. **Computed over stored** for anything read across scenes, as with `value_focus`.
6. **Classify only what the theory requires.** `scene_beats` has no enums. Everything in it is prose or a reference.
7. **Elastic depth.** `scene_beats` can be absent, minimal or full. Readers report how much they covered.

## 4. Theory basis

| McKee step | Where it lives |
| --- | --- |
| 1. Define conflict: who drives, the objective | `scene_beats.driver`; `scene_objective` on the scene and on `scene_beats` |
| 2. Opening value | scene `value_turns[].from` |
| 3. Beats: action and reaction, surface and subtext | `scene_beats.beats` |
| Gap and risk: the escalation loop | `scene_beats.beats[].gap`, `risk` |
| 4. Closing value, compare | scene `value_turns[].to` |
| 5. Survey beats, locate the turning point | `scene_beats.turning_point`, read-only on the scene |
| The nature of choice: dilemma, true character | `scene_beats.true_character` |

- A beat changes behavior, not value. Every beat does, by definition.
- A scene turns a value once, at the turning point: the moment of the major gap between expectation and result.
- The source does not address several turning points in one scene, so the design allows one.
- The gap is the break between what the character expects and what comes back. Each gap raises the risk, and the next action is riskier. The adjustment is the next beat’s action.
- A true choice is a dilemma, and it is where true character shows. The source gives no count per scene, so the design allows none, one or several.

## 5. The scene\_beats entity

**Identity.** One per scene. Ids are global across types, so the id is derived from the scene id plus the suffix `-beats`, set by the write path and refused on a collision. **Export.** One flat directory named after the entity, as for scenes, with each note named by the scene’s title. The id and the `scene` link live in frontmatter.

### 5.1 Fields

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `scene` | ref: scene | yes | Must exist. |
| `driver` | ref: character | no | Who drives the scene. Must exist. |
| `scene_objective` | string | no | The driver’s immediate desire. One sentence. Same name and meaning as on the scene. |
| `turning_point` | string | no | The moment of the major gap, read from how the beats relate. One sentence. Surfaces on the scene as a computed field. |
| `true_character` | list | no | None, one or several. See 5.3. |
| `beats` | list | no | Ordered. See 5.2. |

### 5.2 Beat

```
beat
  action:    by?, surface, subtext
  reaction:  by?, surface, subtext
  gap?
  risk?
  changes?[] entity, change
```

| Field | Type | Notes |
| --- | --- | --- |
| `by` | ref | Optional. A character, location or world. Must exist. The same character on both sides means inner conflict. |
| `surface` | string | What is shown or said. |
| `subtext` | string | The underlying action, as an active gerund phrase. |
| `gap` | string | Evaluation of the exchange: what the character expected and what came back. One sentence. Empty when the beat is mere activity. |
| `risk` | string | Evaluation: what the character now stands to lose, carried into the next action. One sentence. Escalation is read from the sequence. |
| `changes[].entity` | ref | Character, relationship, location or world. Must exist. |
| `changes[].change` | string | One sentence: what this exchange changed for that entity. |

Surface and subtext describe the exchange. Gap, risk and `changes` evaluate it. All are optional and are filled where something moves. Opposition from an object, time or an institution is written in the prose, and what it changes goes in `changes`. A beat with no gap and no `changes` is mere activity, not action.

### 5.3 True character

```
true_character[]
  character
  dilemma
  choice_reveals
```

| Field | Type | Notes |
| --- | --- | --- |
| `character` | ref: character | Must exist. Who faces the choice. It may differ from `driver`: in an ultimatum, one character drives and another chooses. |
| `dilemma` | string | The alternatives and what choosing costs: irreconcilable goods, or the lesser of two evils. |
| `choice_reveals` | string | What the choice shows about who the character is. |

The source gives no count, so the list holds none, one or several. Most scenes have none.

### 5.4 Sections

Conflict, Findings, Notes.

- **Conflict:** what resists the objective, and from which circle.
- **Findings:** the evaluation of the scene (missing conflict, repetition, misplaced turning point, on-the-nose dialogue).

## 6. Scene entity changes

| Field | Kind | Notes |
| --- | --- | --- |
| `scene_objective` | stored, optional | Same name and meaning as on `scene_beats`. |
| `turning_point` | computed, read-only | Returns the `turning_point` of the scene’s `scene_beats`. Empty when none exists. |
| `scene_beats` | computed, read-only | The scene’s `scene_beats` record, or empty. Reported as unfilled under 8.1. |

- Scene sections: the Conflict and Beats sections move to `scene_beats` (Beats is replaced by `beats`). Objective stays as the reasoning behind the field, as on the act.
- `value_turns` and its `effects` stay. Only the `effects` description changes: the outcome of the value shift for a plot protagonist, by conflict level. When `scene_beats` exists, it aggregates that scene’s beat `changes`.

### 6.1 Effects and changes

| Aspect | Scene `value_turns[].effects` | Beat `changes` |
| --- | --- | --- |
| Answers | What the value shift does to a plot protagonist | What this exchange changes, for anyone or anything |
| Grain | The whole scene, per value turn | One beat |
| Entities | Plot protagonists only | Characters, relationships, locations, worlds |
| Conflict level | Yes, per level | None |
| Needs `scene_beats` | No | It is part of it |

When both exist, the scene `effects` should agree with the beat `changes` for the plot’s protagonists. A divergence is a finding for the author, not an error. A reader may show the beat `changes` behind an effect as a drill-down.

## 7. Retired

- Entity `arc_beat`, and the computed `character.arc_beats_list`.
- Character fields `character_value`, `character_value_at_open`, `character_value_at_close` and `arc_type`.
- Beat fields `shift`, `y`, `is_crisis` and `is_climax`.
- The `arc_complete` flag.

`arc_type` becomes a reading of a character’s path across scenes, compared against the plan in the Arc section. It is not stored.

## 8. Rules

**Hard (refused on write)**

- The scene exists, and has no other `scene_beats`.
- Every referenced entity exists.
- `by` is a character, location or world. `changes[].entity` is a character, relationship, location or world.
- A beat has content.

**Soft (reported as findings)**

- A character in `by`, `driver` or `true_character` who is not in the scene’s cast.
- A recorded value turn with no turning point, or a turning point in a flat scene.
- Scene `effects` that disagree with beat `changes` for the plot’s protagonists.
- `scene_beats` older than the scene’s script.
- A reference left dangling by a later delete.

### 8.1 Unfilled and completeness

- A beat list is allowed on any scene.
- `scene_beats` itself is exempt from unfilled checks. Depth is elastic.
- The scene’s computed `scene_beats` field is reported as unfilled when empty, by the same route as a plot’s computed crisis and climax.
- It is reported only for scenes that are `drafted` or later and whose `dramatic_role` is `plot_role` or empty. A `planned` scene is a stub and is skipped. A `transition` or `non-event` scene is never reported.
- Completeness is existence. `scene_beats` has no status, and the scene decides.

## 9. Workflow

| Direction | Sequence |
| --- | --- |
| Structure-first | Scene created with intent (`scene_objective`, `value_turns`). `scene_beats` designs the beats and decides the turning point before the script is written. Script written. `scene_beats` revised. Scene fields reconciled. |
| Content-first | Script written. `scene_beats` read from the text. Scene fields derived. |

Skill guidance: after writing or reworking `scene_beats`, check whether the scene’s `scene_objective` and `effects` still hold. Fill gap, risk and `changes` where something moves, and leave the rest empty.

## 10. Outputs the record enables

Not built now. This is the design test that the data supports them.

- A character’s path in story order: where they act, each gap and the risk they carried, what changed for them, their `true_character` moments, and the objectives they drove. Their conflict levels and value path come from the scene `effects`.
- Escalation, read from the sequence of gaps and risks. There is no numeric size.
- `changes` entries on relationships, locations and worlds as soft continuity, by reverse lookup. Nothing is written into those entities.

## 11. Impact

- **Schema and validation:** `constants.py`, `entity.py`, the write and draft path, and the `value_turns.effects` description.
- **Storage and reads:** `core/db.py` (arc reads, `arc_beats_list`, scene `arc_beats`, the computed `turning_point`).
- **Import, export, delete cascade:** the `arcs/<character>/` handling in export, import and the sweep is removed. `scene_beats` is one flat directory like `scenes/`. A scene delete removes its `scene_beats`.
- **Unfilled:** `unfilled_fields` exempts `scene_beats`. The scene’s computed `scene_beats` field is reported through `_RELATION_FIELDS`, under the rule in 8.1.
- **Tools:** `story_describe`, `story_load` (`view='arc'`), `story_retrieve`.
- **Dashboard:** arc panels and graph retired. New visualisation is designed later from the data.
- **Skill:** `scene-design`, `character-arc`, `value-system` and `value-pass` references.
- **Tests:** about 18 test files and the fixture `arcs/` directory.

## 12. Open points

1. Confirming the `-beats` id suffix.
2. Audience knowledge (mystery, suspense, dramatic irony) as an optional three-value field on `scene_beats`. Not decided.
3. The hinge between adjacent scenes, and imagery tracking. Deferred.
4. Telling order versus story time, so character readers handle flashbacks. A scene property, outside this entity.
