# Character arc

*The change in one character's inner nature, and the shape it takes.*

**An arc is not a series of beats.** In the theory, a beat is an exchange of
behavior — that is the sense a scene's beats use. A character's arc is their
change over the story, and it is read off the scenes, not built from moments of
its own. → `references/theory/character-and-arc.md`, `references/craft/scene-design.md`

**The value is the character's, and it sits inside the story's.** The story
value is the main thematic investigation. `character_value` is a position
inside it, never unrelated to it and never a copy of it. For the protagonist
it is often the same value, because the story's value is defined by them and
by the screen they occupy. For anyone else it is usually a different facet of
the same theme — its contradiction, its resonance, its complication, the
distorted form the theme takes in another life. → `references/theory/values.md`

## Requisites

None. The arc's fields are set on the character, and the character is created
without them.

## Deciding it

### The arc's shape, on the character

- **`character_value`** — which value this arc moves. The story value is the
  main investigation; a character's value is a position inside it, not a copy
  of it. For the protagonist it is often the same value, because the story's
  value is defined by them and by the screen they occupy. For anyone else it
  is usually a different facet of the same theme — the contradiction, the
  resonance, the complication, the distorted form the theme takes in someone
  else's life. A value unrelated to the story's is not a facet, it is a second
  story's theme attached to a person. → `references/theory/values.md`
- **`character_value_at_open` and `character_value_at_close`** — the charge
  where the arc begins and where it ends. The arc is the sweep between them.
- **`arc_type`** — positive, negative, flat, ironic, or absent. `absent` and
  `flat` are real answers for a character who is not there to change.
- **`arc_complete`** — the user's, and the only field here that is purely a
  statement to them. Nothing derives it and nothing recomputes it.

### The shape, read off the story

**The arc is a sweep, and the sweep is what the scenes do.** The charge enters
with the story and leaves with it, and the change has to be absolute and
irreversible. So the arc is not drawn separately from the scenes — it is read
off them, and a character's `arc_type` is a claim about what the scenes did,
not a decision made beside them. → `references/theory/character-and-arc.md`

**Where the turns land is a structural question, not a per-character one.** A
crisis is where the pressure is highest and the choice costs most; a climax is
where the value reverses hardest. Both belong to a level of the structure —
the story, an act, a sequence — and which one a scene is, is decided by the
container. → `../theory/structure-and-plot.md`

**A character can be in a scene that does not move their arc.** A turn is not
only a swing from one charge to its opposite: `mixed` and `ironic` are turns
too, and a scene that lands a character somewhere unresolved is a turn, not a
scene that moved nothing. Equally, a story progresses on more than one front
and not everything progresses at the same pace, so a scene that leaves a
character's arc where it was is a correct scene, not a missing one. →
`references/craft/scene-design.md`

## The couplings

- **The arc's ends and the scenes that produce them are separate records.** The
  character's `*_value_at_open` and `*_value_at_close` are the arc's two ends;
  the turns between them are recorded on the scenes as `value_turns`. The ends
  with no turns between them is an arc with no shape, and turns with no ends is
  a sequence of shifts with nothing to sweep between.

- **A character's value is the story's value read from one life.** `character_value`
  and the story's value are two records about one theme, and a facet that has
  drifted into a second theme is two records disagreeing. Which one is true is
  the user's to say. → `references/theory/values.md`

## Consistency

**Against the plots this character is in.** What a character wants is the same
fact as what a plot does to them, seen from either end. A `goals_long` that
contradicts the shape of a plot they are in — pursuing and then abandoning
exactly what the plot's arc requires — is two records in conflict, not two
records that are both fine. Read the plot's `value_arc` and its scenes before
changing a goal, and read the goals before deciding what a plot does to them.
→ `../craft/plot-and-structure.md`

**Against the scenes that carry it.** The arc is the sweep, and the scenes are
where it happens. A `character_value_at_close` that no scene produced is a
number the story has not earned, and the scenes are the only place to check it.
