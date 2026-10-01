# Character arc

*The change in one character's inner nature, and the moments it turns at.*

**An arc beat is not a beat.** In the theory, a beat is an exchange of
behavior — that is the sense a scene's `Beats` section uses. An `arc_beat` is
one moment in a single character's arc. → `theory/character-and-arc.md`,
`scene-design.md`

**The value is the character's, and it sits inside the story's.** The story
value is the main thematic investigation. `character_value` is a position
inside it, never unrelated to it and never a copy of it. For the protagonist
it is often the same value, because the story's value is defined by them and
by the screen they occupy. For anyone else it is usually a different facet of
the same theme — its contradiction, its resonance, its complication, the
distorted form the theme takes in another life. → `values.md`

## Requisites

An `arc_beat` cannot be created without two existing records, and the write
refuses by name if either is missing:

- **the character** — `character` is required
- **the scene** — `scene` is required, and a beat without a scene has nowhere
  it happens

The character's arc fields need nothing. They are set on the character.

## Deciding it

### The arc's shape, on the character

- **`character_value`** — which value this arc moves. The story value is the
  main investigation; a character's value is a position inside it, not a copy
  of it. For the protagonist it is often the same value, because the story's
  value is defined by them and by the screen they occupy. For anyone else it
  is usually a different facet of the same theme — the contradiction, the
  resonance, the complication, the distorted form the theme takes in someone
  else's life. A value unrelated to the story's is not a facet, it is a second
  story's theme attached to a person. → `values.md`
- **`character_value_at_open` and `character_value_at_close`** — the charge
  where the arc begins and where it ends. The arc is the sweep between them.
- **`arc_type`** — positive, negative, flat, ironic, or absent. `absent` and
  `flat` are real answers for a character who is not there to change.
- **`arc_complete`** — the user's, and the only field here that is purely a
  statement to them. Nothing derives it from the beats and nothing recomputes
  it.

### A beat, on the arc

A beat is a moment the value turns at. These are the decisions that make one,
and one way they usually arrive at each other — but the writing does not
always come from the same direction. A story can need a particular action, or
a particular choice, or a particular shift, before the rest of the beat can be
found. Start from whichever of these the user has already decided, and let the
others follow. What is not negotiable is that they agree: the gap, the choice,
the action and the shift have to be the same moment, or the beat is two
things.

**Where a turn comes from, in the usual case.** First what kind of moment this
is, then what the character does, then what it cost them, and the shift is
what all of that adds up to:

1. **`is_crisis` / `is_climax`** — what kind of moment this is. A crisis is
   where the pressure is highest and the choice costs most; a climax is where
   the value reverses hardest. This is the structural claim, and it decides
   what the moment has to accomplish.
2. **`action`** — what the character does. A beat is not a mood; it is
   something a person does.
3. **`gap`** — what they expected, against what came. An action that went as
   planned is not a turn.
4. **`choice`** — what they chose, once the alternatives were real. This is
   where a character is revealed.
5. **`shift`** — how the value turns here, in the story's own words. Stated
   after the gap and the choice because it is what they add up to: the gap is
   what happened to them, the choice is what they did about it, and the shift
   is the result. When the shift is set first — because the arc needs to land
   there, or a later beat depends on it — the rest of the beat is found by
   working backwards from it, and a shift that no choice can produce is a
   shift the story has not earned yet.
6. **`label`** — then name it. The name comes from what happened, and it is
   how the user finds this beat in a list.
7. **`y`** — that same `shift` as a number, derived from it, and read only to
   draw the arc's curve. The shift is the fact; `y` is its measurement. It is
   the one field here the agent can compute rather than ask for.
8. **The two charges** — `character_value_at_open` and
   `character_value_at_close` on the beat, the charge entering and leaving
   this moment. They are this beat's own, not the arc's ends. A beat's close
   is usually the next beat's open, but the arc moves on the character, not
   only on camera: they can be changed by something that happens while they
   are not in the room. Read the beats in order and set each open charge from
   the one before it, unless the story has moved them in between.

**A beat is added when the arc turns here, and not otherwise.** A turn is not
only a swing from one charge to its opposite: `mixed` and `ironic` are turns
too, and a scene that lands a character somewhere unresolved is a beat, not a
scene that moved nothing. Equally, a character can be in a scene that does
not move their arc at all — that is a correct scene, not a missing beat. A
story progresses on more than one front and not everything progresses at the
same pace. → `scene-design.md`

**The sections** — `Action`, `The Gap`, `Choice`, `Value Shift`, `Notes` — are
the same beat in prose, one per field. Write the reason here, not the field
restated.

## The couplings

- **A beat belongs to its character.** `character` is its parent, and the
  character's `arc_beats_list` is computed from those beats and read-only. The
  beats are not on the character, and editing the character's arc shape does
  not touch them.

- **A beat belongs to a scene, and that scene's `characters` should include
  this character.** The beat says where the arc turns; the scene says who is
  in it. Both records, and nothing compares them — a beat at a scene its
  character is absent from is a beat in a room they were not in. →
  `scene-design.md`

- **The arc's charges and the beats' charges are separate records.** The
  character's `*_value_at_open` and `*_value_at_close` are the arc's two ends.
  Set every beat's open charge to the character's open charge and the arc has
  no shape: every moment starts from the same place.

## Consistency

**Against the plots this character is in.** A character in a plot has beats
that happen inside it, and where a beat and a plot's own beat land on the same
scene, they are two accounts of one moment and have to agree — what the plot
says happens there, and what the character says happens to them. Nothing in
the store compares them. When they disagree, it is usually one of the two that
was written from a later draft of the story, and which is current is the
user's to say. → `plot-and-structure.md`

**A beat does not have to belong to a plot.** A character's value moves on
their own life as well as on the plot's pressure, and beats can sit entirely
outside any plot — a private turn, a loss no subplot is tracking. A character
in a plot is not a character whose every beat is that plot's. Check the beats
that land on a plot's scenes; leave the rest alone.
