# Plot position — proposal, not implemented

*The state of a data change decided during the skill session. Nothing here is
implemented; the skill files are written against the CURRENT schema. Revisit
when there is time to do it properly.*

## The defect

`plot.setups` / `crisis` / `climax` / `payoffs` are written **on the plot**, so
deciding which scenes a plot runs through happens on the plot — in advance,
before those scenes exist. A scene is where a story element is actually
decided, so the direction is backwards. It also forces an agent to invent the
plot's scene list before it has written the scenes.

## The two vocabularies are the same axis

`scene.dramatic_role` and a plot's beats are one vocabulary at different
levels, not two parallel ones. A plot does not exist apart from the story: it
is a way of describing and planning what happens. So the scene's role is
primitive and the plot is the derived claim about which roles belong together.

Shared values kept as they are: `setup`, `complication`, `crisis`, `climax`,
`resolution`.

`dramatic_role` keeps two more — `transition` and `non-event`. These are
scenes that matter to the story but are not a position in any plot's
progression. That is what those two values are *for*, and it answers the
question of whether a scene in a plot with no position needs recording: it
does not, and a scene that has one is expressed as `transition` or
`non-event`.

## The shape

- **`dramatic_role` on the scene stays as it is**, all seven values. It is
  what the scene is in the story, needs no plot, and stays queryable.
- **A scene may be in more than one plot, and in a different position in each.**
  A scene can be a `setup` for one plot and a `climax` for another — so the
  role cannot live only on the scene.
- **Therefore the plot membership is a triple: (scene, plot, role).** Same
  pattern as `relationship.perspectives` and the current `plot.setups`, but
  the third element is the position in *that* plot.
- **The plot's five fields become computed**, derived from that relation, like
  `character.relationships` and `arc_beats_list`. Read-only.
  **Consequence worth keeping:** a plot with a climax and no setup now *reports*
  as incomplete, instead of looking finished — which is the half-finished
  state the current fields cannot show.
- **Writing the triple happens on the scene side**, so a plot is never opened
  again when a scene is added to it.

## Explicitly NOT being done

`is_inciting_incident`, `is_sequence_climax`, `is_act_climax`,
`is_story_climax` are **not** connected to plots. A scene's climax at the
sequence/act/story level is the plot's climax at whatever level that plot
runs, so the flag is sufficient — a separate link would be a second copy of
one fact.

## Where it touches

- `core/constants.py` — the five plot fields become computed; possibly a
  description change on `dramatic_role`
- `core/entity.py` — `_RELATION_FIELDS` gains a plot-position kind carrying a
  role. **Open problem:** the other two relation kinds carry no attribute, so
  either `note` is promoted or a column is added.
- `core/db.py` — computed read path for five fields; note the existing
  comment at ~597 that a `dramatic_elements` view exists precisely because
  those beats are not on the plot
- plot write path loses its beat fields
- `tools/story_import.py`, `tools/story_export.py` — round-trip
- fixture, and any test asserting a plot's beats are writable
- `db.py` unread-field surfaces: a plot's beats would now be reported unfilled
  when a position has no scene, which changes what `unfilled` means for plots

## Open question carried forward

Does a scene ever belong to a plot at **no** position? The answer given was no
— that case is what `transition` and `non-event` are for — but the triple has
no value meaning "belongs to this plot, no position", so confirm that is
intended rather than an oversight.

## Also untouched in that session

Nothing about the skill changes because of this. The craft files describe what
the schema is; when the schema moves, the plot file changes with it.