# Character

*A person in the story: who they are, what they want, what they know, and
what they do not show.* → `theory/character-and-arc.md`

Two subjects share this entity and have their own files, read when the task is
that one:

- **the arc** — a character's own value, its beats, its shape → `character-arc.md`
- **relationships** — the bonds to other characters → `character-relationships.md`

## Requisites

None. A character is created on its own. Its relationships, and the scenes it
appears in, come after.

## Deciding it

**The name, the role, and the one-sentence summary.** The summary is the index
label — the one line the user recognises the character by in a list.

- **`story_role`** is a claim about function in this story, not importance:
  Protagonist, Antagonist, Supporting, Minor, Cameo. One character holds one
  role. Two protagonists is a decision the user makes, not one to resolve.

- **What they want — `goals_short` and `goals_long`.** Short and long are not
  a scale of importance: the long goal is the one that survives the story. A
  character may also hold a want that contradicts the conscious one beneath
  the surface — that is the shape to offer, not a second ambition to invent.

- **What they know — `knowledge`.** Knowledge is what the character holds, and
  it is not the same as what is true. A character who is wrong about something
  is a working dramatic situation, and that stays. What the world makes
  possible for them to know at all is in `world-and-place.md`.

- **Who they are beneath — the sections.** `Identity`, `Background`,
  `Contradictions`, `Psychology`, `Voice`. A character is a contradiction:
  surface and core pull against each other, and a contradiction that dissolves
  whenever convenient is a plot device. `Voice` is not a description of how
  they talk, it is them talking.

- **The arc fields** — `arc_type`, `character_value`, the two charges,
  `arc_complete` — are the arc's decision, not this one's. Do not set them
  while creating a character. → `character-arc.md`

## The couplings

- **`relationships` and `arc_beats_list` are computed**, read-only, derived
  from the `relationship` and `arc_beat` entities. A write naming them is
  refused. They are where to *read* the bonds and beats from; the entities are
  where a bond or a beat is decided.

- **A relationship is one bond held by two characters.** It lives in a single
  `relationship` entity and each character sees it as `relationships`. Record
  it on one side only and the two characters disagree about their own
  relationship. → `character-relationships.md`

- **The charges and the beats are separate records.** A character's
  `*_value_at_open` and `*_value_at_close` are the arc's two ends; the beats
  between them carry their own charges. Ends with no beats is an arc with no
  shape; beats with no ends is a sequence of turns with nothing to turn
  between. → `character-arc.md`

## Consistency

Two records can disagree, both be right on their own terms, and leave a story
that does not add up. No write refuses it. Read the other side before changing
either.

**Against the plots they are in.** What a character wants is the same fact
as what a plot does to them, seen from either end. A `goals_long` that
contradicts the shape of a plot they are in — pursuing and then abandoning
exactly what the plot's arc requires — is two records in conflict, not two
records that are both fine. Which one is true is the user's to say. Read
the plot's `value_arc` and its beats before changing a goal, and read the
goals before deciding what a plot does to them.

**Against the world they act in.** What a character knows, wants, and can
do is bounded by the world's rules. Knowledge the world makes impossible, or
a goal the world has no room for, is a contradiction the character file
cannot see. → `world-and-place.md`

**Against the other characters.** What one character knows about another,
and what the bond between them is, lives on the relationship, not here.
Changing a character's `knowledge` or `Psychology` may contradict a bond
already recorded. → `character-relationships.md`
