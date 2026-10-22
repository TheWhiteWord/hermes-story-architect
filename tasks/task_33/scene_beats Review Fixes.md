# scene\_beats: Review Fixes and Views

Draft, 20 October 2026. Issues 1 to 5 are findings from reviewing the `feature/issue-redesign` branch. Issues 6 and 7 propose the views that read the data. Each issue gives the problem or purpose, the change and what it touches. Nothing is changed yet.

## Issue 1. The scene carries the whole beat list

**Problem.** The scene’s computed `scene_beats` field is typed `object` and holds the full record. It is embedded in the base `story_load` map and in `story_retrieve` on a scene, so scene payloads grow with every beat.

**Change.** Make it a pointer: a string field with `ref: scene_beats`, computed, empty when the scene has no record. It has the same shape as the plot’s computed role fields.

- The id cannot be derived from the scene id. The plan (F1.7) made the id caller-supplied, with `{scene_id}-beats` as a convention the skill teaches. The pointer tells the agent where to look.
- The full record is read with `story_retrieve` on `scene_beats` and that id.
- Unfilled is unaffected, because `get_unfilled_map` checks existence directly. Confirm that `story_retrieve._unfilled` treats an empty pointer as unfilled.

**Touches.** `constants.py` (scene schema), `core/db.py` (`_build_scene`), `tools/story_retrieve.py` (`_scene_beats` and the scene branch), tests.

## Issue 2. The base map must stay small

**Problem.** The default `story_load` map embeds each scene’s `scene_beats` record. The map is meant to stay small, and the `values` view already notes about 45KB at 270 scenes.

**Change.**

- Base map: carries only the pointer from Issue 1, and nothing when it is absent.
- `scene_objective` and `turning_point`: not in the base map. They go in the `dramatic_elements` rows, which already walk act, sequence and scene with milestones and can be filtered by act. If they are wanted in the base map later, that is one sentence each, only when filled.

**Touches.** `core/db.py`, `tools/story_load.py` (`_view_dramatic_elements`), the tool description.

## Issue 3. Slim the beat: drop `risk`, move `changes` up

**Problem.** `risk` records a trend as if it were a datum. The theory records expectation, gap, adjustment and the next action, and risk rising is read from that chain. `risk` also repeats the gap and the next action’s subtext, is the least objective field, and adds verbosity. Separately, beat-level `changes` is a third statement of what the `reaction` and `gap` already say, and it mixes two levels: a beat changes behavior, while what is different for an entity is a scene-level fact.

**Change.** Remove `risk`. Remove `changes` from the beat and move it to the top level of `scene_beats` (Issue 5). The beat is `action`, `reaction`, `gap`. The adjustment needs no field of its own: it is the next beat’s action, and its result shows in the scene’s `changes`.

**Touches.** `constants.py` (beat sub-fields), the `scene_beats` validation (entity references move with `changes`), the skill (`scene-design`), tests, fixtures.

## Issue 4. The gap and the turning point must not read as closed

**Problem.** The `gap` description, “what the character expected and what came back”, reads as a finished comparison. LLMs tend to add how the character responded, which closes the gap inside the beat and swallows the next action. A turning point written from such gaps becomes a self-contained event.

**Model.**

| Term | What it is |
| --- | --- |
| Gap | The break between expectation and result at a beat. It opens there and is not closed there. The next action responds to it and opens a larger one. |
| Turning point | The moment the scene’s largest gap opens and the value turns. It starts the closing state and does not resolve the gap. |
| Escalation | The pattern of successive gaps, each larger. It is read across steps and never stored. |

Mere activity is an exchange where the expectation is met. Nothing opens, so `gap` stays empty.

**Change.** Descriptions only, no schema change.

- `gap`: “The break between what was expected and what came back, at the moment it opens. One sentence. Stop at the break: what follows from it is the next beat’s action. Empty when the beat is mere activity.”
- `turning_point`, on `scene_beats` and on the computed scene field: “The moment the scene’s largest gap opens and the value turns. One sentence. It starts the scene’s closing state and does not resolve the gap.”
- Neither has a structured owner. A character may appear in the sentence, but whose gap it is is not recorded.
- The skill gets one good and one bad example. Good: “Expects the key to be handed over; is refused.” Bad: “Expects the key to be handed over; is refused, so she backs down.”

**Touches.** `constants.py` (two descriptions on `scene_beats`, one on the scene), the skill.

## Issue 5. A scene-level record of what changed

**Problem.** Tracking characters needs what changed for each of them, and for other entities. The scene’s `effects` cover plot protagonists only, with a value and a level. Nothing records the state of other characters, relationships, locations or worlds. Beat-level entries are too granular for higher levels and mix behavior with state.

**Change.** Add a top-level `changes` list on `scene_beats`: one entry per entity whose state is different at the end of the scene. It is the scene’s closing state against its opening, assessed over the beats. Scene `effects` stay as they are. They tie the value shift to a plot protagonist and a level, while `changes` records the state of any entity.

**Field descriptions.** These carry the meaning, so they are written out in full.

| Field | Description |
| --- | --- |
| `changes` | One entry per entity whose state is different at the end of the scene. Only where something changed. No entry means unchanged. |
| `changes[].entity` | The character, relationship, location or world whose state changed. Must exist. |
| `changes[].change` | One sentence, readable without the beats: the new state, not the event. For a character: what they now believe or know, want or are willing to do, or how their situation, standing or bond with another has shifted. For a relationship, location or world: its changed condition. |

**Skill guidance.**

- Write the beats first and derive `changes` from them.
- Include secondary characters and antagonists whenever their state shifts.
- Write the state, not the event. “Now willing to confront the board” is a change. “Confronts the board” is an action.
- Do not pad. No entry means unchanged.

**Reading.** Higher-level views build a character’s row from `driver`, `changes`, `true_character` and, for protagonists, the scene `effects`. They never need the beats. Attribution to a specific exchange stays in the beat prose.

**Soft finding.** Scene `effects` that disagree with `changes` for a plot protagonist.

**Touches.** `constants.py` (the new field and the `effects` description), `core/entity.py` (validation, reference resolution, the soft finding), the skill, tests, fixtures.

## Issue 6. `dramatic_elements` carries the escalation spine

**Purpose.** At plot, sequence, act or story scope, escalation is read from the promoted scenes: the chain of each milestone scene’s `scene_objective` and `turning_point`. The view already walks act, sequence and scene with milestones and plot roles, so it is extended and no new view is added. At scene scope the beats are read with `story_retrieve` on `scene_beats`.

**Change.**

- Scene rows gain `scene_objective`, `turning_point` and `scene_beats` (the pointer from Issue 1). Each is emitted only when filled.
- New argument `plot`: limit the view to one plot. The `project` header narrows to that plot.
- New argument `milestones_only`: keep only scenes carrying a role of the filtered plot, with trimmed rows: `id`, the role, `scene_objective`, `turning_point`. For a subplot the row carries that plot’s own role, since `milestone` is the main plot’s.
- Unchanged: the `act` argument, the `project` header, and `title`, `status`, `dramatic_role`, `milestone`, `plots` on each row.

**Rows by case.** The sentences are illustrative.

```
# a) milestone scene, beats and turning point written
{ "id":"central-room-day", "title":"…", "status":"drafted",
  "dramatic_role":"plot_role", "milestone":["inciting_incident"], "plots":[…],
  "scene_objective":"to get the door open without being seen",
  "turning_point":"the handle turns and the lock was never engaged",
  "scene_beats":"central-room-day-beats" }

# b) a record exists, nothing stated yet
{ …, "scene_beats":"central-room-night-beats" }

# c) plot_role scene with no record: no new keys, and `unfilled` reports it
{ "id":"…", "status":"drafted", "dramatic_role":"plot_role", "plots":[…] }

# d) transition: no plots or milestone, never reported as missing
{ "id":"corridor-walk", "status":"drafted", "dramatic_role":"transition" }
```

With `plot` and `milestones_only`:

```
{"view":"dramatic_elements","plot":"the-resistance","milestones_only":true,
 "acts":[{"id":"act-1","sequences":[{"id":"seq-discovery","scenes":[
   {"id":"central-room-day","milestone":["inciting_incident"],"scene_objective":"…","turning_point":"…"},
   {"id":"central-room-night","milestone":["climax"],"scene_objective":"…","turning_point":"…"},
   {"id":"the-core-day","milestone":["resolution"],"scene_objective":"…","turning_point":"…"}]}]}]}
```

**Touches.** `tools/story_load.py` (`_view_dramatic_elements`, the argument schema and the tool description), `core/db.py` (reading `scene_beats` for the view), tests.

## Issue 7. `view="track"`: one entity across the story

**Purpose.** Read a character’s journey, or the changing state of a location, world or relationship, across scenes. It serves analysis and is built for context, not completeness.

**Arguments.**

- `entity` (required): an entity id. `unfilled` already uses the same argument.
- `act`, `sequence`: narrow the scope. The default is the whole story. The shape is the same at every scope.
- `value`: narrow `effects` and the header `values` to one value.

**Output.** Rows are grouped by act and sequence, so those ids appear once. A row exists only for scenes where something is recorded. Appearances with nothing recorded are counted, not listed. The header carries:

- `coverage`: scenes the entity appears in, how many have `scene_beats`, how many record a change.
- `values`: for a protagonist, per value, the first state, the deepest rung and the last state within the scope.
- `plots`: the plots the character is protagonist of.

Row keys, each only when it applies:

| Key | Meaning |
| --- | --- |
| `scene` | The scene id. |
| `driver` | True when the character drives the scene. |
| `scene_objective` | Only when the character drives the scene and it is filled. |
| `change` | The entity’s entry in the scene’s `changes`. More than one entry is joined into one string. |
| `true_character` | This character’s entry: `dilemma`, `choice_reveals`. |
| `effects` | Protagonists only: value, then conflict level, then the effect sentence. |

**Shape of `effects`.** The keys are the value names, then the levels `inner`, `personal`, `extra-personal`. The values are the effect sentences. These are left out as repetition: `character` (it is the entity), `plot` (it is in the header; if the same value turns under two plots in one scene, the key is suffixed with the plot id), `from` and `to` (they belong to the turn, and are in the header `values` and `view=values`), and the `levels` and `conflict_level` keys. The alternative, lists with the real field names, repeats `conflict_level` on every entry.

**Examples.** The effect sentences are fixture text, abbreviated. The rest is illustrative.

```
{"view":"track","entity":"kael","scope":{"act":"act-1"},
 "coverage":{"appears":14,"with_scene_beats":6,"with_change":5},
 "values":[{"value":"freedom","from":"imprisoned","deepest":"…","to":"…"}],
 "acts":[{"act":"act-1","sequences":[
   {"sequence":"seq-discovery","scenes":[
     {"scene":"central-room-day","driver":true,
      "scene_objective":"to get the door open without being seen",
      "change":"now suspects the lock was never engaged",
      "effects":{
        "freedom":{"inner":"Kael realises the lock was never engaged, …",
                   "personal":"Kael’s hand on the handle is a public refusal to stay."},
        "trust":{"inner":"Every guard Kael had been told about is a lie; …",
                 "personal":"The Institute’s authority over Kael collapses with the lock."}}},
     {"scene":"central-room-night",
      "change":"now willing to refuse Mira in public",
      "true_character":{"dilemma":"…","choice_reveals":"…"},
      "effects":{
        "freedom":{"inner":"Refusing the offer is the deepening: …"}}}]}]}]}
```

A location, world or relationship reduces to `scene` and `change`:

```
{"view":"track","entity":"the-core","scope":"story",
 "coverage":{"appears":9,"with_change":3},
 "acts":[{"act":"act-2","sequences":[{"sequence":"seq-flood","scenes":[
   {"scene":"core-night","change":"now flooded to the second level"}]}]}]}
```

**Reading the evidence.** Escalation is not computed. It is read from the trajectory of `change` sentences, the `scene_objective`s of driven scenes, the `effects` by level and the value path. The code orders and groups, and the reader judges.

**How.**

- One reader in `core/`, in the style of `value_focus`, returns the ordered rows for an entity. `story_load` calls it now and the dashboard can later.
- A shared story-order helper. `get_scene_value_turns` builds the (act, sequence, scene) key, because sequence order keys restart in each act, but only for scenes that have turns. The ordering is lifted into a helper both use.
- The reader never reads `beats`.
- Scenes with nothing recorded are skipped, and coverage is always reported.

**Limits.**

- Circle levels exist only for plot protagonists.
- There is no `time_note` yet, so tracks read in telling order and a flashback reads as a step backwards.
- Secondary characters are only as visible as the `changes` discipline allows. The coverage line shows it.

**Touches.** `core/` (the reader and the ordering helper), `tools/story_load.py` (the new view, its arguments, the tool description and the unknown-view message), tests.

## Deferred

- Per-beat `changes`, as optional evidence under the top-level summary, if attribution to a specific exchange proves useful.
- A scene pre-write pack. The existing calls cover it for now.
- A separate escalation view. Issue 6 covers the spine.
- A `time_note` on scenes, so that `track` can place flashbacks and time jumps.

## Not in this document

The dashboard visuals. They are discussed separately and will use the same reader as `track`.
