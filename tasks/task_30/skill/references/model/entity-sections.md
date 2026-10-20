# Entity sections

*Schematic draft — headings and notes only.*

Every entity is created with all of its standard sections present and **empty**.
This file is what goes in them, and what to do about the ones that stay empty.

The section *names* are not here. `story_describe` reports them per type, and
they are a closed set — a name that is not on that list is rejected by the write
path, so there is nothing to look up and nothing to guess.

---

## What a section is for

*The frame the whole file sits in.*

- A section is where **thinking, decisions and extended detail are kept.** It is
  the roomier half of an entity: the field holds the fact, the section holds
  everything around the fact that the author does not want to lose.
- **Neither half requires the other.** You do not have to write the `Desires`
  section to set `goals_short`, and setting the field does not oblige you to
  write the section. Nothing in the code couples them and nothing here should
  make them a pair of obligations.
- They work together **naturally**, the way a person works: you think in prose
  and the decision that survives is the one worth putting in a field. Which of
  the two you reach for first is not a rule, and the order is not the point.
- The practical consequence: a fact worth querying belongs in a field, and prose
  that makes the fact meaningful belongs in a section. Writing a good `Desires`
  section does not fill `goals_short` — and that is fine, because they are
  answering different questions.
- *Why the field is the one to reach for first when it comes to a choice:*
  every reader that is not a person uses fields — the dashboard, the graphs,
  `story_load`'s views. A section has exactly one reader, and is looking at it.
- The old sections design doc has a "which section informs which field" table.
  **It is a prompt, not a rule.** If a section has been written and the
  corresponding field is empty, that is a natural moment to notice — not an
  error, not a requirement, and not something to state as automatic.

## Seeing which sections are blank

*How to look. There is nothing to switch on.*

- `story_retrieve` with `sections: ["all"]` returns every section the entity
  holds, keyed by name, and **a blank one comes back as `""`**. An empty string
  in that payload *is* the report — it says the section exists and nothing has
  been written into it yet.
- `sections: ["all"]` also returns the headings the note actually uses, not
  only the standard names. Where an author has written under a name of their
  own, that heading is in the payload with its prose in it, and there is nothing
  to reconcile. Read what is there before concluding a section is unfilled.
- Asking for one name by hand is different: a name with no section behind it
  comes back `null`, with `sections_not_found` and `available_sections`
  alongside. Absent and blank are told apart by `null` versus `""`.
- Blank is a normal state, not a finding. A new entity has every section blank,
  and most entities are mid-thought most of the time. Which blanks are worth
  writing *now* is a judgement about what the user is currently deciding — the
  payload shows the state, it does not make the call.

## Notes — the same on all eleven types

*Stated once here rather than repeated in every block above.*

The section set is **fixed and not customisable**: a section name off the list
is rejected by the write path, and there is no way to add one of your own. So
when something genuinely belongs to this entity but fits none of the sections
above, `Notes` is where it goes rather than being lost or forced into a section
that is about something else.

That is its whole job. It is not a scratchpad, not a to-do list, and not a place
to put a fact that has a field — a fact with a field belongs in the field. It is
the overflow for content the author wants to keep and that the fixed set has no
home for.

---

## How to read a type block

- Each block is one entity type, in the order a story gets built.
- One line per section: what it is for, and when leaving it blank is right.
- Nothing here restates the field list — `story_describe` has it.

---

## Project

*Seven sections. The story before it has characters.*

- **Premise** — the "what if" that started it.
- **Spine** — the protagonist's story-long want. Every scene relates to it.
- **Controlling Idea** — how and why life changes; the argument the story makes.
- **Value Arc** — the value at stake and its sweep. The stored read-back is each
  plot's `value_focus`; the recording pass is `references/craft/value-pass.md`.
- **Structure** — design type, act count, where the turning points sit.
- **Genre** — the contract with the audience: what this world owes them.
- **Notes** — everything that does not fit above.

## Character

*Nine sections — the most of any type.*

- **Identity** — who they are; surface against core.
- **Desires** — conscious want and the one underneath it. The most common place
  to write well and set no field.
- **Background** — what happened to them. Feeds `knowledge` if anything is a
  fact someone else could act on.
- **Contradictions** — what does not add up in them. Depth.
- **Psychology** — the inner life: fears, secrets, the mental landscape.
- **Arc** — where they end up different. The prose; the shape is → `references/craft/character-arc.md`
- **Relationships** — prose about bonds. The structured version is its own
  entity → `references/craft/character-relationships.md`
- **Voice** — how they speak. No field for it at all; this section is the only
  place it can live.
- **Notes**

## World

*Eight sections.*

- **Description** — the world as experienced.
- **History** — how it came to be.
- **Livelihood** — how its people earn and eat. Texture.
- **Power** — who holds authority and how. Friction for arcs.
- **Rituals** — the customs that make it not-anywhere.
- **Values** — what it holds sacred. What its characters are arguing about.
- **Conflict** — where its friction comes from, given the rules above.
- **Notes**

## Location

*Six sections.*

- **Description** — the sensory surface.
- **Atmosphere** — the emotional register. Pairs with `mood`; does not set it.
- **Image System** — recurring motifs. Purely prose; nothing reads it.
- **History** — what happened here.
- **Dramatic Function** — why this place exists in the story.
- **Notes**

## Plot

*Six sections.*

- **Summary** — the through-line.
- **Role** — what kind of plot this is, main or sub. Pairs with `plot_type` /
  `plot_scope`.
- **Threads** — how it weaves through scenes. Pairs with setups/crisis/climax/
  payoffs; does not set them. → `references/craft/plot-and-structure.md`
- **Value** — the value at stake across this plot, and its journey.
- **Characters** — who is in it, and their stake.
- **Notes**

## Act

*Five sections. The largest unit below the story.*

- **Summary** — what this act accomplishes.
- **Objective** — the protagonist's immediate goal for it. Pairs with
  `act_objective`.
- **Value Arc** — the value entering and leaving this act, read from the scenes'
  value turns. → `../craft/value-pass.md`
- **Reversal** — the climax scene and why it is irreversible.
- **Notes**

## Sequence

*Seven sections. The hinge between act and scene.*

- **Summary** — what it accomplishes.
- **Purpose** — why it exists, what it builds toward.
- **Value Arc** — entering and leaving, read from the scenes' value turns. →
  `../craft/value-pass.md`
- **Progression** — how the scenes escalate.
- **Sequence Climax** — the scene that recontextualises everything before it.
- **Plots** — which plot(s) it serves.
- **Notes**

## Scene

*Six sections. The one with a special first section.*

- **Content** — **the scene itself, in Fountain.** Not prose about the scene; the
  screenplay. → `references/mechanics/screenplay-format.md`
- **Objective** — what the character wants here, against the story-long want.
  Pairs with the scene's own `scene_objective` field, which carries the same
  fact.
- **Value Turn** — what this scene does to each value it touches. The turn
  itself is recorded as `value_turns` after the scene exists; this section holds
  the reasoning. → `../craft/value-pass.md`
- **Dramatic Function** — its role in the larger structure.
- **Production** — location, time, heading. Screenplay-facing.
- **Notes**

*The scene's `Conflict` and `Beats` sections are gone.* Both moved to the
`scene_beats` record, which holds the beats and the evaluation of the scene.
The scene keeps its own `Objective`.

## Scene beats

*Three sections. The scene's beats, and the evaluation of the scene.*

- **Conflict** — what resists the objective, and from which circle: inner,
  personal, extra-personal. More than one at once is normal. The scene's own
  `Conflict` section is gone; this is where it went.
- **Findings** — the evaluation of the scene: missing conflict, repetition, a
  turning point in the wrong place, on-the-nose dialogue. These are the
  author's judgements, written here rather than computed, so the list is not a
  closed one.
- **Notes** — see below.

## Relationship

*Six sections. The entity that lives between two people.*

- **Nature** — what defines the bond at its core.
- **Perspectives** — each character's view. Pairs with the `perspectives` dict;
  does not set it. → `references/craft/character-relationships.md`
- **Tension** — the friction, and the dramatic potential.
- **History** — how it evolved. Pairs with `history`.
- **Scenes to Write** — what scenes this relationship *needs*, not where it
  happens. A to-do, not a record.
- **Notes**

---

## Rulings applied

Answers to the four open questions, kept so the reasoning is not re-derived.

- **Fields and sections.** A section is where thinking, decisions and extended
  detail are kept; the field holds the fact. Neither requires the other — no
  obligation to write one before the other, and nothing in the code couples
  them. They work together naturally. On an entity where most sections shadow a
  field, that is the arrangement working, not a duplication to resolve.
- **The "which section informs which field" mapping.** Useful as a prompt, and
  deliberately **not** a rule. If a section has been written and its field is
  empty, that is a natural moment to notice — not an error and not a
  requirement.
- **`Notes`.** The section set is fixed and not customisable, so `Notes` is
  where content that belongs to the entity but fits nowhere else goes, instead
  of being lost or forced into a section about something else. Not a scratchpad
  and not a home for facts that have fields.
- **Completeness is elastic, and one type is exempt.** `scene_beats` carries no
  completeness bar: the beats can be absent, minimal, or full, and an empty
  list is a valid state rather than a gap to close. The scene's computed
  `scene_beats` field is a pointer — the record's slug — and is what is
  reported as missing when the record does not exist at all: the record, not
  its contents. Read the record itself with `story_retrieve` on `scene_beats`
  and that id.
- **Reporting blank sections.** Not a separate report. `story_retrieve` with
  `sections: ["all"]` returns each section's body, and a blank one is `""` —
  read it there. It also returns the headings the note uses under names of its
  own, so what is written is visible next to what is not. Deciding which blank
  sections matter is left to the reader, because most entities are mid-thought
  most of the time and a permanent gap report would be noise on every entity.

