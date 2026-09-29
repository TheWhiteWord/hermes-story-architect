# Entity sections

*Schematic draft — headings and notes only.*

Every entity is created with all of its standard sections present and **empty**.
This file is what goes in them, and what to do about the ones that stay empty.

The section *names* are not here. `story_describe` reports them per type, and
they are a closed set — a name that is not on that list is rejected by the write
path, so there is nothing to look up and nothing to guess.

---

## The empty-section problem

*Why this file exists at all.*

- A new entity returns every section as `""` — nine empty strings for a
  character. **Nothing reports a section as unfilled.** `unfilled_fields` counts
  fields only, and an empty section is indistinguishable from a section holding
  a space.
- So an empty section is invisible. Nobody is told it is blank, and no dashboard
  flags it. **Deciding which sections to leave empty is the work**, and it is
  invisible work.
- A section that does not exist at all is different: requesting a name off the
  list returns `null` and `sections_not_found`. Blank is not the same as absent,
  and the agent can tell them apart.
- *Note:* is there a case for a tool that reports blank sections, the way
  `unfilled_fields` reports blank fields? If so it is a tool fix, not a
  reference file. Flagged, not assumed.

## Sections and fields are separate things

*The rule that stops the same fact being written twice.*

- **Prose in a section never sets a field.** Nothing derives one from the other —
  there is no code path from a section body to frontmatter.
- So a fact that matters structurally has to be written *twice*: once as prose
  that reads well, once as a field the system can query. Writing a good `Desires`
  section does not fill `goals_short`.
- *Which is authoritative?* **The field.** Every reader that is not a human uses
  fields — the dashboard, the graphs, `story_load`'s views. A section has exactly
  one reader: the person looking at it.
- *Exception, and it needs a line of its own:* on `arc_beat` the section names
  and the field names collide — `action` and `choice` are both, and `gap` /
  `shift` are the same idea as `The Gap` / `Value Shift`. Same trap, different
  spelling.
- The old sections design doc has a "which section informs which field" table.
  That is a **design note about a human's workflow, not a mechanism.** Worth
  keeping as a prompt ("you wrote about desires — does `goals_short` say it?"),
  never worth stating as automatic.

## How to read a type block

- Each block is one entity type, in the order a story gets built.
- One line per section: what it is for, and when leaving it empty is right.
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

*Five sections — and the one place sections and fields collide.*

- **Action** — what the character does. **Also a field.** → `arc-beats.md`
- **The Gap** — the disconfirming reaction. Also a field, named `gap`.
- **Choice** — what they do next. **Also a field.**
- **Value Shift** — the resulting change. Also a field, named `shift`.
- **Notes**
- *Open question:* with four of five sections shadowing a field, is the prose
  redundant, or is the field the short version and the section the thinking?
  Needs a decision, and `arc-beats.md` is where it belongs.

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

## Open questions

- [ ] Should a tool report blank sections the way `unfilled_fields` reports blank
      fields? If yes, that is a tool fix and this file gets smaller.
- [ ] The `arc_beat` field/section collision needs a ruling: which is
      authoritative, and does the prose earn its place?
- [ ] Is "which section informs which field" worth keeping as a prompt, or is it
      the kind of thing that rots? A design note, not a mechanism.
- [ ] `Notes` exists on all ten types and nothing says what belongs in one.
      Worth a line, or is it self-evident?
