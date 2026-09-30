# Location

*A place in the story, and what it is there to do.* → `theory/world-and-place.md`

A location is not a set description. It is a specific place in a specific
world, and it earns its record by what it does for the story — what it
enables, what it forces, what it recalls.

## Requisites

None required. A location is created on its own, before any scene uses it.

- **`world`** names the world it belongs to. It is optional and nothing
  checks it, so confirm the world exists before naming it — and if the place
  could exist in more than one world, that is a decision to put to the user
  rather than one to make.
- **A scene that names this place needs this place to exist.** A scene's
  `location` may be left empty while the story is still being shaped — that is
  a field not yet set, and it is reported as unfilled. But a value that is set
  has to resolve to a location record, and if there is none, create it. A
  place that is only ever named in scenes and never recorded has no mood, no
  image system and no history, and the scenes cannot reach anything it holds.
  → `scene-design.md`

## Deciding it

**The name and the one-sentence summary.** The summary is the index label.

- **`mood`** — the emotional register of the place, generalized: not "it is
  dark" but what the dark is doing, an atmosphere as a single word or short
  phrase that the whole place carries. The same mood holds across a location
  however the scenes in it vary.
- **`dramatic_function`** — why this place exists in the story. This is the
  field that decides whether a location is worth having at all, and it is a
  claim about the story rather than a description of the room: a place that is
  where the past catches up, or where a choice cannot be deferred any longer,
  is doing work. A place with no function is a backdrop, and the user decides
  whether they want one.
- **`world`** — the world it belongs to. → `world.md`
- **`variant_of`** — a variant is this same place with a change the story
  cares about, and the base stays a location in its own right. →
  `variant.md`
- **The sections** — `Description`, `Atmosphere`, `Image System`, `History`,
  `Dramatic Function`, `Notes`. The place in prose.
  - `Atmosphere` is the `mood` in words; `Description` is what is there.
  - **`Image System`** is the motifs this place carries. An image system is a
    repetition in sight and sound that works below the level of statement, and
    a place is where it is planted: the same image can be set up in one
    location and returned to in another, much later, and the audience feels
    the connection without being told. A motif stated once is a symbol
    announced.
  - `History` is what happened here, not what the world is like — a place's
    history is what it holds over the people in it.

## The couplings

- **A location is read by the scenes that use it, and nothing connects them.**
  A scene's `location` is a slug or free text, and a location's own record is
  not required to be set on the scene. A location can exist with no scene in
  it, which is a place the story has not used yet or does not need — the user
  decides which. → `scene-design.md`

- **A place is bounded by its world.** Its rules, its power structure and its
  period constrain what can happen in it, and a location that assumes a
  different world is a contradiction the location file cannot see. → `world.md`

## Consistency

**A variant and its base must not disagree about which world they are in.** A
variant inherits its base's world, and states its own only when the change
altered the world itself — a room that burned does not need a new world, a
city that burned does, and the difference is the world's condition rather
than the location's. So a variant naming a different world, or none, while its
base names one is two records in conflict, and only the user can say which the
story means. → `variant.md`
