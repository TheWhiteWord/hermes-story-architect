# Scene design

*The smallest unit the system records, and the one where "a lot of content"
and "a scene" are easiest to confuse.* → `references/theory/scene-and-beat.md`

**Two things are called a beat, and they live in different records.** A scene's
beats — the theory's exchange of behavior inside the scene — are held by a
`scene_beats` record, one per scene. A character's arc is their change over the
story, and it is not a series of these. → `references/craft/character-arc.md`

**The screenplay is the `Content` sections, in order.** Nothing else reaches
the script: the concatenation is by act → sequence → scene `order`, so scene
order *is* the screenplay. → `references/mechanics/screenplay-format.md`

## Before and after

A scene is where everything in the story meets: the cast, the value, the turn,
the place in the structure. So it is worth reading before deciding it, and
worth reading back after.

**Read before deciding what the scene turns.** These are what the turn is made
from, and they are considerations rather than instructions — what the story
needs here may be one of these or none of them:

- **The arcs of the characters in it.** They show where each character's value
  has been and what it has done so far, so the scene can pick up where the
  last turn left them — what state they are in, and what would be a change
  from it.
- **The character values themselves.** A character's value is what the scene
  serves for them, and it points at what would be relevant to that character
  here.
- **The plots' value schemas.** The words each plot has for its values — the
  four rungs of each — and where each stands, read from the values view. This is
  the vocabulary the scene's turns will be recorded in.
  → `references/craft/value-pass.md`

**Other things may rightly drive the scene instead** — the story value, the
structure, what the scene has to accomplish technically. A story progresses on
more than one front, and **not everything progresses at the same pace in every
scene.** A scene that moves the story's value and leaves every character's arc
where it was is correct, not incomplete.

**Read back after.** The scene turns the value — is that visible? Does the
cast have someone to happen to? Are the people present the ones the turn
belongs to?

## Requisites

- **The sequence, and the act that matches it.** `sequence_id` is required and
  a missing sequence is refused by name. The act comes from the sequence, not
  from a choice — a scene whose `act_id` disagrees with its sequence's act is
  refused too. Do not stage a scene before its sequence exists.
- **The location, if it is set.** Empty is a field not yet set and is reported
  as unfilled. A value that is set must name a location that exists, so create
  the location and commit it first. → `references/craft/location.md`
- **The `scene_beats` record, if the scene is to have one.** It cannot exist
  before the scene does — `scene` is required, and a record whose scene is
  missing is refused. One scene, one record: a second is refused, and the
  refusal names the first.

## Deciding it

**Where it sits.** `order` is a fraction, not an integer, so a scene can be
inserted between two others without renumbering anything; a reordering is a
separate operation that renumbers the whole list. → `../craft/plot-and-structure.md`

**Who is in it — `characters`.** The cast present. An empty list on a scene
that genuinely has nobody in it is recorded with `no_cast`, so the absence
reads as chosen rather than as an oversight.

**What turns here — the value.** The scene's job is the turn, and it is
**recorded after the scene exists**, as `value_turns` — never while creating the
scene. One entry per shift of a value, with its effects on the protagonists. How
and when to record it, how to choose the opening state, and how to read the
value line back, are the whole of `references/craft/value-pass.md`.

**A scene that does not turn is not a scene.** If nothing shifts, the scene is
exposition, and that is a thing to find out before writing it rather than after.
The turn need not be the loudest thing in the scene — it is the point where the
value differs on the way out.

**What the scene is for — `dramatic_role` and `plot_roles`.** These answer
different questions and are not interchangeable:
- `dramatic_role` is whether this scene serves a plot at all: `plot_role`,
  `transition`, or `non-event`. Exactly one. It carries no structural role.
- `plot_roles` is where the structural role lives — one entry per plot, with
  role from the six: setup, inciting_incident, complication, crisis, climax,
  resolution. A scene can hold different roles in different plots.
- **A scene whose role is `climax` is a climax of something.** A climax is the
  culmination of a level, and it is defined by being greater than everything
  inside that level. A scene with the role `climax` is the culmination of
  whatever contains it; which one is decided by the container, not by the
  role. → `../theory/structure-and-plot.md`
- **Climaxes nest, so a scene can carry several, or one, or none.** The story
  has one climax, each act one, each sequence one. Which level a climax belongs
  to is decided by the container, not stored on the scene.
  → `../theory/structure-and-plot.md`
- **A climax is as large as its level, and no larger.** A scene that is only its
  sequence's climax must be a smaller turn than its act's climax, and the act's
  smaller than the story's — same value, different magnitude. → `references/theory/values.md`
- **Every other scene is trajectory toward a culmination.** A scene that is
  not a climax is not a failed climax: it moves the value toward the one that
  is coming, and the size of its turn is set by that distance. → `references/theory/values.md`

**The prose.** `Objective` is the immediate desire in this time and place, and
it is also a field on the scene, `scene_objective`. `Value Turn` is the turn
above, in words. `Dramatic Function` is why the scene exists, and `Production`
is what it needs to be made. The beats and the conflict are not here — they
live on the scene's `scene_beats` record, below.

**`status`** runs planned → drafted → written → locked, and is the user's to
move.

## The scene's beats

*A scene carries at most one `scene_beats` record, and it is where the scene's
beats, its conflict, and the evaluation of it are held.*

**Two ways to arrive at it, and both are normal.** They differ in what is
written first, not in what ends up true:

- **Structure first.** The scene is created with its intent — `scene_objective`
  and `value_turns`. The `scene_beats` record then designs the beats and decides
  the turning point *before* the script is written. The script is written, and
  the record is revised against what was actually written. The scene's fields
  are reconciled with it.
- **Content first.** The script is written. The `scene_beats` record is read
  back out of the text — the beats are the exchanges that are actually there,
  not the ones that were planned. The scene's fields are derived from it.

Either way the two records describe one scene, so **after writing or reworking
`scene_beats`, check whether the scene's own fields still hold.** The ones that
can move are `scene_objective`, `effects` (on the value turns), and `changes`
(on the beats); fill `gap` and `risk` where something moved, and **leave the
rest empty** — a field that did not change is not a field to fill.

**What the record holds.** `scene` (its link to the scene, required), the
driver, the objective, the turning point, the true-character choices, and the
ordered beats. Named: `driver`,
`scene_objective`, `turning_point` (read back onto the scene as a computed
field), `true_character` (a `character` with a `dilemma` and what the
`choice_reveals`), and `beats` — each beat with an `action` side and a
`reaction` side, each of those with a `by`, a `surface` and a `subtext`, plus
the beat's `gap`, `risk`, and `changes` (each a `change` for an `entity`).
Field shapes are in `story_describe`; what a beat is for is
`references/theory/scene-and-beat.md`.

**Reading the record: the scene gives you its id, not its contents.** A
scene's `scene_beats` field is the *slug* of the record, because the id is
chosen when the record is created and cannot be derived from the scene id
(`{scene_id}-beats` is the convention, not a rule). So the read is two calls:

1. `story_retrieve` on the **scene**, `fields: ["scene_beats"]` — the pointer.
   Empty when the scene has no record.
2. `story_retrieve` on **`scene_beats`**, `id: [<that slug>]` — the record.

The base `story_load` map carries the pointer and nothing more; the beats are
never in it. `view="dramatic_elements"` carries the pointer beside the scene's
`scene_objective` and `turning_point` (each only when filled), so a scene's
dramatic spine is one view and its beats are one retrieve.

**What the sections hold.** `Conflict` is what resists the objective and from
which circle; `Findings` is the evaluation of the scene; `Notes` is free-form.
→ `../model/entity-sections.md`

**The soft rules, and where they go.** A value turn with no turning point, a
turning point in a flat scene, scene `effects` that disagree with beat
`changes`, a character the record names who is not in the cast — none of these
is refused by a write. They are judgements, and `Findings` is where they are
written. → `../model/entity-sections.md`

## The couplings

- **A beat's scene should contain the beat's character.** The beat says where
  the scene's conflict turns; the scene says who is in it. Nothing compares
  them. → `references/craft/character-arc.md`

- **`heading` and the Content's first line are two different things.** The
  field is a slug-friendly heading for the user's own organisation, and it is
  optional. The script reads the *first line of the `Content` section*, and
  that line must be a Fountain scene heading — one beginning `INT`, `EXT`,
  `EST` or `I/E`. A scene whose Content does not open with one is simply
  absent from the screenplay, with no error. The field and the line can
  disagree and nothing checks it.

## Consistency

**A scene's cast against what the scene does.** The turn happens to someone.
A scene whose `characters` is empty but whose `Value Turn` moves a particular
character's value is two records disagreeing about who is present — and
`no_cast` does not cover it, because that flag records a scene with nobody in
it, not a scene whose turn belongs to someone who is absent.

**A scene's value turns against its beats and its objective.** The turn is what
the gap and the choice add up to. A `Value Turn` that no `Conflict` produces is
a turn the scene has not earned, and reading the scene's turns and its
`scene_beats` record together is the cheapest way to find it.
