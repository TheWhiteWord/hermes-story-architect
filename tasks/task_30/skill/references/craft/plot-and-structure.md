# Plot and structure

*The shape of the story: acts, the sequences inside them, the scenes inside
those, and the plots running through them. Where a climax belongs at each level,
and the difference between the links the system checks and the ones it does not.*

→ `references/theory/structure-and-plot.md`

The enum values are in `story_describe`.

## Requisites

- **An act must exist before a sequence is staged in it**, and a sequence before
  a scene. Containment is refused by name when the parent is missing — a scene
  whose sequence does not exist, or whose `act_id` disagrees with its sequence's
  act, is refused too.
- **A plot must exist before a sequence names it** as `primary_plot`. Nothing
  checks it, so a plot that has been renamed or deleted leaves the sequence
  pointing at nothing. → `../mechanics/ids-and-links.md`

## Deciding it

**Where a scene sits.** `order` is a fraction, not an integer, so a scene can be
inserted between two others without renumbering anything. → `references/craft/scene-design.md`

**The levels, and what each carries.** Four levels, and they are not equally
enforced:

    project → act → sequence → scene

- **A scene** turns the value-charged condition of a character's life.
- **A sequence** is a series of scenes culminating in one with greater impact
  than any preceding scene.
- **An act** is a series of sequences peaking in a climactic scene, causing a
  major reversal of values.
- **A story** is a series of acts culminating in absolute and irreversible change.
  → `references/theory/structure-and-plot.md`

**A climax at every level, and it is not stored.** A climax is the culmination
of a level, defined by being greater than everything inside that level — so
which scene it is follows from the container, and **which level a scene is the
climax of is decided by the container, not written on the scene**. A scene's
structural role is written on the scene itself, as `plot_roles`; the container's
pointer at it is a relation, and nothing reconciles the two. → `references/craft/scene-design.md`

- **A climax is not the biggest scene.** It is the scene where the value
  reverses hardest *at that level*. An act's climax and the story's climax are
  usually different scenes, and the story's is the one that cannot be undone.

**Escalation is read across the promoted scenes, and stored nowhere.** A plot's
chain of promoted scenes is the escalation: each milestone scene's
`scene_objective` states what is wanted, and its `turning_point` states where
the gap opens. Read it with `view="dramatic_elements"`, `plot` set to the plot,
and `milestones_only` — the rows come back as `id`, `milestone`, `role`,
`scene_objective`, `turning_point`. Successive turning points are the pattern;
each is larger than the last, and the reader judges that. A subplot's chain is
its own, read the same way, with the role under `role` since `milestone` is the
main plot's. → `../mechanics/reading-the-project.md`

**Plots.** The other thing running through the structure.

- A plot declares what kind it is: `plot_scope` is main or sub, and `plot_type`
  is one of four — Contradictory, Resonant, Complicating, Setup. **The kind is a
  claim about what the plot does to the main one**, not a label.
- **A plot states its value arc as a named shape** — Maturation, Redemption,
  Education, Punitive, Disillusionment, Testing. That is a different vocabulary
  from the charge words, and it belongs to plots alone: a plot says *what kind
  of change*, a scene says *how far the charge moved*.
- **The six role fields are a set, not six independent fields.** `setups`,
  `inciting_incident`, `complications`, `crisis`, `climax`, `resolutions` are the
  six places a plot is established, incited, obstructed, tested, resolved and
  paid back. **A plot with a climax and no setup is the common half-finished
  state** — and it is invisible, because each field is independently optional
  and nothing reports the set as incomplete. They are read-only: they are set
  by writing the role on the scene, as `plot_roles`, and read back from there.
- **A scene can be in several plots at once.** That is how a subplot earns its
  place — by touching scenes the main plot also uses.

**The sections** — `Summary`, `Purpose`, `Value Arc`, `Progression`,
`Sequence Climax`, `Plots`, `Notes`, on a sequence; `Summary`, `Objective`,
`Value Arc`, `Reversal`, `Notes`, on an act. The reasoning belongs here. →
`../model/entity-sections.md`

## The couplings

- **A sequence's `primary_plot` and the plot it names are two records, and
  nothing compares them.** A sequence that names a plot the story has dropped is
  a pointer into nothing, and no write refuses it.
- **A scene's `plot_roles` and the plot's role fields are two stores for one
  fact.** The scene is where the role is written; the plot's six fields are
  computed from the scenes and read-only. Set the role on the scene, and the
  plot's field follows.

## Consistency

**Against the structure it sits in.** A scene's `order` is a position inside its
sequence, and the sequence's act comes from the act — so a scene moved into
another sequence changes what its neighbours continue from, and nothing
reports it. Read the sequence's `value_focus` and the plots' turns before moving
one. → `references/craft/value-pass.md`

**Against the value the plot tracks.** A plot's `value_arc` is a named shape, and
the scenes that carry its roles are where that shape is enacted. A plot whose
climax scene does not reverse its value is a shape the story has not performed,
and the scenes are the only place to check it. → `references/theory/structure-and-plot.md`
