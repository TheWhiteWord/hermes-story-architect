# Plot and structure

*Schematic draft — headings and notes only.*

The shape of the story: acts, the sequences inside them, the scenes inside
those, and the plots running through them. Where a climax belongs at each level,
and the difference between the links the system checks and the ones it does not.

The enum values are in `story_describe`. The theory of structure is not here.

---

## The hierarchy, and which links hold

*Four levels, and they are not equally enforced.*

    project → act → sequence → scene

- **Containment is checked.** A scene's sequence must exist, and its act must
  match that sequence's act — both refused by name. A sequence's act must
  exist. **[checked]**
- **Everything a container *points at* is not checked.** Verified, all four of
  these stage, produce **no warning at all**, and commit:
  - an act's `climax_scene_id` naming a scene that does not exist;
  - a sequence's `climax_scene_id` naming a scene that does not exist;
  - a sequence's `primary_plot` naming a plot that does not exist;
  - an act's `climax_scene_id` pointing at one scene while a *different* scene
    carries the act-climax flag.
- **So: a broken link in the structure is invisible until a human notices it.**
  There is no dangling-reference report, and nothing will tell the user that the
  act points at a scene that was renamed. This is the single most useful thing
  to carry out of this file: when a scene or plot is renamed or deleted, the
  containers pointing at it are not updated and not flagged.
- The value fields on these same entities *are* checked — the charge words and
  the `y` range. So the shape of the story is enforced and its wiring is not.
  That asymmetry is worth knowing before assuming a good validation report means
  the structure is sound.

## A climax at every level, stored twice

*The recurring pattern of this file, and the thing to be careful about.*

- **Three levels have a climax** — the sequence, the act, and the story. Each is
  marked twice:
  - the **container points at the scene** — `climax_scene_id` on an act, on a
    sequence, and the story's own pointer on the project;
  - the **scene carries the flag** — `is_sequence_climax`, `is_act_climax`,
    `is_story_climax`.
- **The two are never reconciled.** Verified: an act can point at one scene while
  a different scene carries its climax flag, and it commits without a word.
- **They are not the same fact, though.** The container's pointer says *which
  scene the reversal lands in*; the scene's flag says *this scene is a climax of
  something*. Both are needed and both are read — by different consumers, the
  pointer by the dashboard's structure view and the flag by the structural views
  and the scene badges.
- **So the practical rule: when marking a climax, mark both, or know which one
  you are satisfying.** → `project-design.md` has the same decision for the
  inciting incident and the story climax.
- **A climax is not the biggest scene.** It is the scene where the value
  reverses hardest *at that level*. An act's climax and the story's climax are
  usually different scenes, and the story's is the one that cannot be undone.

## Plots

*The other thing running through the structure.*

- A plot is a thread of its own, and it declares what kind it is: main or sub,
  and one of four kinds — Contradictory, Resonant, Complicating, Setup. **The
  kind is a claim about what the plot does to the main one**, not a label.
- **A plot states its value arc as a named shape** — Maturation, Redemption,
  Education, Punitive, Disillusionment, Testing. That is a different vocabulary
  from the charge words, and it belongs to plots alone: a plot says *what kind
  of change*, a scene says *how far the charge moved*.
- **The four beat fields are a set, not four independent fields.** `setups`,
  `crisis`, `climax` and `payoffs` are the four places a plot is established,
  tested, resolved and paid back. **A plot with a climax and no setup is the
  common half-finished state** — and it is invisible, because each field is
  independently optional and nothing reports the set as incomplete.
- The beat fields hold a scene and a description of what happens there, so the
  description is not optional in spirit even though the shape allows a bare
  slug. The `Threads` section is where the reasoning lives. →
  `entity-sections.md`
- **A scene can be in several plots at once.** That is how a subplot earns its
  place — by touching scenes the main plot also uses.

## What the structure needs before it is worth staging

- [ ] Acts exist, in order. `act_count` on the project adjusts upward on its
      own, so it does not need maintaining.
- [ ] Sequences exist inside acts, and scenes inside sequences. **Containment
      is checked**, so this order is enforced.
- [ ] Each level's charge is recorded where the turn happens — the act's open
      and close, the sequence's, the scene's. Never inherited. → `value-system.md`
- [ ] Climaxes marked, at both halves of the pair, at the levels that have one.
- [ ] Plots declared with their kind and scope, and their four beats filled in
      as a set rather than one at a time.
- [ ] Any `primary_plot` on a sequence points at a plot that exists — **this one
      is entirely on the author**, and a dangling one is silent.

---

## Open questions

- [ ] Every structural reference is unchecked: a renamed or deleted scene leaves
      its containers pointing at nothing, silently. This is a genuine gap rather
      than a design choice, unlike the two-character warning on a relationship.
      Worth adding to `deferred-code-work.md` as a third entry?
- [ ] The climax pair — container pointer and scene flag — is stated in three
      files now (`project-design`, `scene-design`, this one). Worth one place
      that owns it, with the other two pointing at it?
