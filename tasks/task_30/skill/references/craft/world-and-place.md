# World and place

*Schematic draft — headings and notes only.*

The world the story happens in, and the places in it. What each is for, how a
place relates to a world, and what the system checks about the links between
them — which is close to nothing.

The field names are in `story_describe`. The theory behind them is not here.

---

## Nothing here is checked

*The frame for this file, and the reason it has to be read carefully.*

- **Every reference on a world or a location is silent.** Verified by pointing
  each one at a slug that does not exist and committing:
  - a location's `world`;
  - a location's `variant_of`; a world's `variant_of`;
  - a scene's `location`; a scene's `characters`;
  - a sequence's `act_id`; its `primary_plot`;
  - a relationship's `characters`; an act's `climax_scene_id`.
- **None of them warns. All of them commit.** A world can belong to nothing, a
  variant can point at itself, and nothing anywhere reports any of it.
- For contrast, exactly **four** references in the whole system are enforced: a
  scene's `sequence`, a scene's `act`, a plot's `characters`, and an arc beat's
  `character`. Those four are the ones that keep the **hierarchy** standing.
- **So the rule the code actually follows: the tree is defended, the web is
  not.** A scene will never be orphaned from its parent, and it will happily
  be in a room that does not exist, in a world that has never been written.
- This is the same gap as the structural one in
  `plot-and-structure.md`, seen from a different direction. → that file, and
  `deferred-code-work.md`.

## World and location are different jobs

*The distinction the two entity types are making.*

- **A world is the set of rules that generates pressure.** Its fields are the
  friction: the rules that hold, what the world holds sacred, and who holds
  power and how. A world whose rules and power are empty is a backdrop; a world
  with them is something a character can run into.
- **A location is a place that does something.** Its job is not to be described
  but to *work*: the mood it establishes, and the reason it exists in the story
  at all. A location with a description and no dramatic function is scenery.
- So a location **belongs to a world**, and the two answer different questions:
  what is true here, and what does being here do to someone.
- **The link between them is unchecked.** A location can name a world that does
  not exist, and it will be stored and displayed. The field is a claim, and the
  user maintains it.

## A scene's location is free text on purpose

*Not an oversight — the opposite.*

- A scene's `location` accepts **a slug or free text.** A scene set in "a
  rooftop nobody has named" is a legitimate thing to write, and it stores as
  written. Verified: no warning, and the reverse relation is created carrying
  that text.
- So **not every place in a story needs to be a location entity.** A named place
  that recurs, that has a mood, or that the story returns to, deserves a
  record. A place mentioned once does not.
- The cost of that choice: the system cannot tell a typo from a deliberate
  description. "Offcie" and "a rooftop nobody has named" are the same kind of
  value, and neither is flagged.
- So when a location is a real place in the story, use its slug, and **create
  the location first** — otherwise the scene and the location are two records
  that do not know about each other.

## `variant_of`: the same place, differently

*What the one genuinely structural field here is for.*

- Both a world and a location can declare that they are **a version of
  another** — the same place as it is in a different time, or the same
  organisation before and after it changed.
- It is the only field on either type that is not a fact about the thing but a
  fact about **its relationship to another version of the same thing.**
- **It is entirely unchecked**, and the shapes that break are all accepted:
  - a location that is a variant of **itself**;
  - a variant pointing at something that does not exist;
  - **a cycle** — A is a variant of B and B is a variant of A. Verified,
    committed, no warning.
- A cycle matters more than the other two: anything that walks the chain to
  find the base version will not terminate. Keep the base record's field empty
  and point variants at it, one level deep, unless there is a reason not to.
- *A base record has an empty `variant_of`.* That is the whole convention.

## What to write, and when

- [ ] **The world**, when the story's rules start to matter. Rules and power
      before values: a world with rules and no power has nothing to push
      against.
- [ ] **A location**, when a place recurs or does specific work. Its
      `dramatic_function` is the field that earns the record; the description
      alone does not.
- [ ] **A variant**, only when the same place at a different time is genuinely
      a separate thing with its own meaning. Two records of one room in two acts
      is not a variant; it is one room.
- [ ] **Scene locations as slugs** where a location record exists, free text
      where it does not — and both are accepted, so the choice is one of record
      hygiene rather than one the system will make for you.
- The prose for all of it lives in the sections. → `entity-sections.md`

---

## Open questions

- [ ] `variant_of` accepts a self-reference and a cycle. A cycle is the one with
      teeth — anything walking to the base version will not terminate. Should
      that be a hard check even though the other reference gaps are not?
- [ ] A scene's location being free text means typos and descriptions are
      indistinguishable. Worth saying in the file, or is it the kind of
      observation that will read as criticism of a deliberate choice?
