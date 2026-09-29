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

## The empty-section problem

*Why deciding what to leave blank is the work.*

- A new entity returns every section as `""` — nine empty strings for a
  character. **Nothing reports a section as unfilled.** `unfilled_fields` counts
  fields only, so an empty section is indistinguishable from one holding a space.
- So a blank section is invisible: nobody is told, and nothing flags it. Which
  sections are worth writing *now* is a judgement about what the user is
  currently deciding, and most entities are mid-thought most of the time.
- A section that does not exist at all is different: requesting a name off the
  list returns `null` and `sections_not_found`. Blank is not the same as absent,
  and the agent can tell them apart.
- *Known gap:* a tool that reported blank sections the way `unfilled_fields`
  reports blank fields would settle this. It does not exist — recorded in
  `deferred-code-work.md`, with a note that this file has to be revisited if it
  is built. Designed around the absence for now.

## `Notes` — the same on all ten types

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
- **Value Arc** — the value at stake and its sweep. Pairs with the value fields;
  does not set them. → `value-system.md`
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
- **Arc** — where they end up different. The prose; the shape is → `arc-beats.md`
- **Relationships** — prose about bonds. The structured version is its own
  entity → `relationships.md`
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
  payoffs; does not set them. → `plot-and-structure.md`
- **Value** — the value at stake across this plot, and its journey.
- **Characters** — who is in it, and their stake.
- **Notes**

## Act

*Five sections. The largest unit below the story.*

- **Summary** — what this act accomplishes.
- **Objective** — the protagonist's immediate goal for it. Pairs with
  `act_objective`.
- **Value Arc** — the charge entering and leaving.
- **Reversal** — the climax scene and why it is irreversible.
- **Notes**

## Sequence

*Seven sections. The hinge between act and scene.*

- **Summary** — what it accomplishes.
- **Purpose** — why it exists, what it builds toward.
- **Value Arc** — entering and leaving charge.
- **Progression** — how the scenes escalate.
- **Sequence Climax** — the scene that recontextualises everything before it.
- **Plots** — which plot(s) it serves.
- **Notes**

## Scene

*Eight sections. The one with a special first section.*

- **Content** — **the scene itself, in Fountain.** Not prose about the scene; the
  screenplay. → `screenplay-format.md`
- **Objective** — what the character wants here, against the story-long want.
- **Conflict** — the antagonism: inner, personal, extra-personal.
- **Beats** — the action/reaction exchanges.
- **Value Turn** — opening charge, closing charge, the turn between.
- **Dramatic Function** — its role in the larger structure, and the flags.
- **Production** — location, time, heading. Screenplay-facing.
- **Notes**

## Arc beat

*Five sections. The clearest case of a field and a section working side by side.*

- **Action** — what the character does. The field holds the short version; this
  section holds the thinking behind it. → `arc-beats.md`
- **The Gap** — the disconfirming reaction. Also a field, named `gap`.
- **Choice** — what they do next. Also a field.
- **Value Shift** — the resulting change. Also a field, named `shift`.
- **Notes** — see below.
- *No ruling needed here, and that is the point:* four of the five shadow a
  field, and that is not a duplication to be resolved. The field is the fact
  every other reader uses; the section is why the character did it. A beat can
  be written either way round, and often only one of them is worth writing yet.

## Relationship

*Six sections. The entity that lives between two people.*

- **Nature** — what defines the bond at its core.
- **Perspectives** — each character's view. Pairs with the `perspectives` dict;
  does not set it. → `relationships.md`
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
  them. They work together naturally. On `arc_beat`, where four of five section
  names shadow a field, that is the arrangement working, not a duplication to
  resolve.
- **The "which section informs which field" mapping.** Useful as a prompt, and
  deliberately **not** a rule. If a section has been written and its field is
  empty, that is a natural moment to notice — not an error and not a
  requirement.
- **`Notes`.** The section set is fixed and not customisable, so `Notes` is
  where content that belongs to the entity but fits nowhere else goes, instead
  of being lost or forced into a section about something else. Not a scratchpad
  and not a home for facts that have fields.
- **Reporting blank sections.** Deferred to `deferred-code-work.md`. This file
  is designed around the absence and must be revisited if the tool change is
  built.

