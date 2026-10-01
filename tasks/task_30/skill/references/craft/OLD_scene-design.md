# Scene design

*Schematic draft — headings and notes only.*

What a scene needs before it is worth staging. The scene is the smallest unit
the system records, and it is the one where "a lot of content" and "a scene" are
most easily confused.

The field names are in `story_describe`. Fountain syntax is not here.

---

## A scene turns, or it is an event

*The whole test, and the reason this file exists.*

- A scene is **continuous time and place in which something changes.** If the
  value entering is the same as the value leaving, nothing happened dramatically
  no matter how much was written.
- That is the difference between a scene and a sequence of things happening. A
  character enters a room, learns a thing, and leaves having lost something they
  wanted — the charge moved, and the scene turned.
- **So the test before staging: can you say what the value is on the way out, and
  how it differs from the way in?** If not, the scene is not ready, and adding
  prose will not make it ready.
- *A scene that does not turn is not always wrong* — a deliberate flat beat, a
  rest, a non-event. But it should be a decision, not an accident, and the
  `dramatic_role` field is where that decision gets recorded.

## Where the turn is recorded

*Four fields, one fact. They answer different questions and none of them is
optional in principle.*

- **The charge pair** — what the value is entering and leaving. This is the
  measurement of the turn.
- **`shift`** — how it turns, in the story's language. This is the finding, and
  the one a writer actually uses.
- **`y`** — where the turn lands on the scale, so the curve can be drawn.
- → `value-system.md` for how to read the charge words, derive `y` from `shift`,
  and what a missing `y` means.
- **The scene sections carry the same turn in prose**: `Objective` (what is
  wanted), `Conflict` (what resists it), `Beats` (the exchanges), `Value Turn`
  (the measurement in words). The fields and the sections are the same decision
  in two forms; neither requires the other. → `entity-sections.md`
- **Conflict levels** — inner, personal, extra-personal. More than one is
  normal, and a scene with only one is worth a second look.

## Placement: sequence, act, and order

*The structural side, and one rule the write path enforces.*

- A scene lives in a **sequence**, which lives in an act. Both are required.
- **Both are checked, and both can refuse the write.** Verified: a sequence that
  does not exist is refused by name, and a scene whose `act_id` disagrees with
  its sequence's act is refused too. So neither is free-form — derive the act
  from the sequence rather than choosing it, and do not stage a scene before its
  sequence exists. **[checked]**
- `order` is a **fraction**, not an integer, so a scene can be inserted between
  two others without renumbering anything. Reordering is a separate operation
  that renumbers a whole list.
- → `plot-and-structure.md` for where a scene sits in the larger shape.
- → `mechanics/dashboard.md` for why order is not bookkeeping: scene order *is*
  the screenplay.

## Role and milestones: two different questions

*The scene has a role word and four booleans. They are not the same fact.*

- **`dramatic_role`** is what this scene *does* structurally: setup,
  complication, crisis, climax, resolution, transition, non-event. Exactly one.
- **The four booleans** mark *milestone* scenes specifically: this is the
  inciting incident, this is the sequence's climax, this is the act's climax,
  this is the story's climax. Each is a separate claim at a different level of
  the hierarchy.
- **A scene with the role `climax` is not the story climax.** It is a climax
  *of something* — of a beat, of a sequence, of a subplot. Setting the role does
  not set a milestone, and setting a milestone does not set the role.
- Setting a milestone also has a counterpart on the project — see
  `project-design.md`, which states which reader each side serves.
- The milestones are what the structural views report, so an unmarked climax is
  a scene the views cannot see.

## Cast

- `characters` is a list of slugs present in the scene.
- **`no_cast` is a decision, not a workaround.** Set it when a scene
  deliberately has no characters — an empty room, a landscape, a device — so the
  absence is recorded as chosen rather than left looking like an oversight.
- **It works on one surface, not two.** Verified: `story_load(view="unfilled")`
  honours the flag and reports the scene as complete on that field, while
  `story_retrieve`'s per-entity `unfilled_fields` does not know about it and
  still lists `characters` as unfilled. The flag is substituted further down, in
  the view, not in the field check.
- So **an agent reading the per-entity surface will see a deliberate empty cast
  reported as a gap.** That is not a bug to work around — it is the flag doing
  its job on the surface that shows the user. Trust the unfilled view for "is
  this scene missing its cast", and do not re-add a character to satisfy the
  other one.
- An empty cast with no flag is an oversight. An empty cast with the flag is a
  decision. Nothing else distinguishes them.

## Two headings, and they are not interchangeable

*Both concern the script, and only one of them is what the script reads.*

- The **`heading` field** is screenplay metadata — a slug-friendly heading for
  the scene. It is optional and defaults to empty.
- **The `Content` section's first line** is what the renderer actually reads, and
  it must be a Fountain scene heading. A scene whose Content does not open with
  one is silently absent from the script.
- They can disagree and nothing checks. The field is for the user's own
  organisation; the section is the script.
- → `screenplay-format.md` for the format, and the two failure modes that render
  as a working dashboard.

## Content is the scene, not about the scene

- The `Content` section holds **the screenplay itself** — Fountain, not prose
  describing what happens. Every other section is about the scene; this one is
  the scene.
- That is worth stating plainly because the section is named the same as every
  other one and reads like it: `Objective` and `Content` are not the same kind of
  thing.
- *The sections, in order:* `Content`, `Objective`, `Conflict`, `Beats`,
  `Value Turn`, `Dramatic Function`, `Production`, `Notes`.

## What a scene needs before it is worth staging

*The practical version of the top of this file.*

- [ ] A turn: the charge entering differs from the charge leaving.
- [ ] The shift stated in the story's language, not as a pair of charge words.
- [ ] A sequence, and an act that matches it.
- [ ] A role — or a decision that it has none.
- [ ] Cast, or `no_cast`.
- [ ] Content, if the scene is being written rather than only planned.
- `status` runs planned → drafted → written → locked, and is the user's to move.

---

## Open questions

- [ ] `heading` and the Content's first line are two headings with no
      relationship. Is the field worth keeping in the file at all, or is it
      mentioned once and left alone?
- [ ] "A scene that does not turn is not always wrong" — is that permission
      worth giving explicitly, or does it weaken the test at the top?
