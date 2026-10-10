# Scene design

*The smallest unit the system records, and the one where "a lot of content"
and "a scene" are easiest to confuse.* → `theory/scene-and-beat.md`

**Two things are called a beat.** A scene's `Beats` section holds the theory's
exchange of behavior inside the scene. An `arc_beat` is one moment in one
character's arc, a different record entirely. → `character-arc.md`

**The screenplay is the `Content` sections, in order.** Nothing else reaches
the script: the concatenation is by act → sequence → scene `order`, so scene
order *is* the screenplay. → `screenplay-format.md`

## Before and after

A scene is where everything in the story meets: the cast, the value, the turn,
the place in the structure. So it is worth reading before deciding it, and
worth reading back after.

**Read before deciding what the scene turns.** These are what the turn is made
from, and they are considerations rather than instructions — what the story
needs here may be one of these or none of them:

- **The arc beats of the characters in it.** They show where each character's
  value has been and what it has done so far, so the scene can pick up where
  the last turn left them — what state they are in, and what would be a change
  from it. A curve that has been flat is information too: a protagonist's
  wants a more dynamic line than a supporting character's, and a scene is
  where a stalled arc can be moved.
- **The character values themselves.** A character's value is what the scene
  serves for them, and it points at what would be relevant to that character
  here.

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
  the location and commit it first. → `location.md`

## Deciding it

**Where it sits.** `order` is a fraction, not an integer, so a scene can be
inserted between two others without renumbering anything; a reordering is a
separate operation that renumbers the whole list. → `plot-and-structure.md`

**Who is in it — `characters`.** The cast present. An empty list on a scene
that genuinely has nobody in it is recorded with `no_cast`, so the absence
reads as chosen rather than as an oversight.

**What turns here — the value pair and the shift.** The scene's job is the
turn, and it is three records of that one fact:
- `value_at_open` and `value_at_close` are the charge entering and leaving.
- `shift` is how the value turns *in the story's language* — the finding, the
  thing a writer uses. It is not the pair of charge words restated.
- `y` is that shift measured, read only to draw the curve.

**A scene that does not turn is not a scene.** If the two charges are the
same, the scene is exposition, and that is a thing to find out before writing
it rather than after. The turn need not be the loudest thing in the scene —
it is the point where the value differs on the way out.

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
  role. → `structure-and-plot.md`
- **Climaxes nest, so a scene can carry several, or one, or none.** The story
  has one climax, each act one, each sequence one. Which level a climax belongs
  to is decided by the container, not stored on the scene. → `structure-and-plot.md`
- **A climax is as large as its level, and no larger.** A scene that is only
  its sequence's climax must be smaller than its act's climax, and the act's
  smaller than the story's. So the `shift` of a lower climax is a smaller turn
  than the `shift` of a higher one — same field, different magnitude. → `values.md`
- **Every other scene is trajectory toward a culmination.** A scene that is
  not a climax is not a failed climax: it moves the value toward the one that
  is coming, and the size of its turn is set by that distance. → `values.md`

**The prose.** `Objective` is the immediate desire in this time and place;
`Conflict` is what resists it, from one of the concentric levels — inner,
personal, extra-personal, and more than one at once is normal. `Value Turn`
is the turn above, in words. `Dramatic Function` is why the scene exists, and
`Production` is what it needs to be made.

**`status`** runs planned → drafted → written → locked, and is the user's to
move.

## The couplings

- **A beat's scene should contain the beat's character.** The beat says where
  the character's arc turns; the scene says who is in it. Nothing compares
  them. → `character-arc.md`

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

**A scene's shift against its beats and its objective.** The shift is what the
gap and the choice add up to. A `Value Turn` that no `Conflict` produces is a
turn the scene has not earned, and reading the two sections together is the
cheapest way to find it.