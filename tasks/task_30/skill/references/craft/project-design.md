# Project design

*The story before it has characters: what it is about, the shape it takes, and
the contract it makes with its audience.*

→ `references/theory/structure-and-plot.md`

## Requisites

None. A project is created on its own, and it is the one creative write with no
preview — `create_project` is a direct call. → `../mechanics/project-lifecycle.md`

## Deciding it

**The name and the logline.** `logline` is the one-sentence summary, and it is
the index label — the line the user recognises the project by.

**`spine`** — the protagonist's desire, story-long. Every scene's objective is a
piece of it. It is the promise the story makes, and it is not the same as the
premise.

**`controlling_idea`** — how and why life changes; the argument the story makes.
The climax resolves the debate the story runs, and the resolution *is* the
controlling idea. → `references/theory/values.md`

**`structure_type`** — Classical, Miniplot, or Antiplot. This is a claim about
the shape of the change, not a genre label, and it decides what the ending owes
the audience. → `references/theory/structure-and-plot.md`

**`genre`** — the contract with the audience: what this world owes them.

**`setting`** and **`period`** — the primary setting of the main story. They
describe the main story, and a project may hold worlds that are not its main
one. → `references/craft/world.md`

**`act_count`** — the number of acts. It adjusts upward on its own when more act
files exist, so it does not need maintaining.

**The sections** — `Premise`, `Spine`, `Controlling Idea`, `Value Arc`,
`Structure`, `Genre`, `Notes`. The story before it has characters, in prose. →
`../model/entity-sections.md`

## The couplings

- **`value_focus` is computed, not written.** Which values are major and which
  are minor is derived from the plots — the project's major is the main plot's,
  the minor the subplots'. Reading it is the way to see what the story is
  actually about; writing it is refused.
- **A world may be the main story's world or not.** `setting` and `period` are a
  statement about the main story, not a constraint every world must satisfy. →
  `references/craft/world.md`

## Consistency

**Against the plot that is the main one.** The main plot is the one with
`plot_scope = main`, and the story's milestones are whatever scenes hold those
roles in it. A `value_focus` that names a value no plot tracks is a value the
story has stopped using. → `references/craft/plot-and-structure.md`

**Against the world it is set in.** `genre` and the world's rules are two
records about the same reality, and nothing compares them. A world of magic
under a genre of sci-fi is one of the two being out of date, and which one is
the user's to say. → `references/craft/world.md`
