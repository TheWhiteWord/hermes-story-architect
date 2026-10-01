# Project design

*Schematic draft — headings and notes only.*

Shaping the story before it has characters or scenes. What the `project` entity
is for, which of its fields belong to which stage of thinking, and the two
places where the same fact has to be written twice.

The twenty field names are in `story_describe` and are not repeated here.

---

## Only one thing is required

*Verified: of twenty fields, only `name` is required. Everything else defaults.*

- A project can be created nearly empty and filled in as the thinking happens.
  That is deliberate, and it is the right instinct: **a user who has a premise
  and nothing else should be able to start.**
- So the useful question is not "what does a project need" but **"what is worth
  settling now, and what can wait until it is actually decided."** A field left
  empty is a field still being thought about.
- Nothing on a project is computed. Every field is a judgement the user makes —
  there is no part of it the agent can fill in on their behalf.

## Four clusters, four different moments

*The twenty fields are not one list. They belong to four jobs, and mixing them
is the easiest way to fill a project with noise.*

| Cluster | What it is | When it settles |
|---|---|---|
| identity | name, logline, genre, setting | at the start, and the logline keeps moving |
| story design | spine, controlling idea, the value fields, structure, act count | over the life of the project, in the order below |
| scene pointers | which scene is the inciting incident, which is the climax | **after those scenes exist** |
| title page | the script's title, credit, author, contact, draft date, draft label | at the end, when there is a script to put them on |

- **The title-page cluster is a different job.** Those fields describe the
  *screenplay artifact* — the dashboard renders them as a script title page —
  not the story. Do not offer them while someone is still finding the premise.
  They are also the only fields with sensible defaults, and the only ones that
  are purely presentational.

## The order the thinking comes in

*Not a procedure. A dependency — each one is easier to answer once the last is.*

- **Premise** — the "what if". → the `Premise` section.
- **Spine** — the protagonist's story-long want. A premise is not yet a spine;
  a spine is a character who wants something, which is why this cannot be
  answered before there is someone to want it.
- **Controlling idea** — how and why life changes. This is the *argument* the
  story makes, and it is usually the last thing the user can state, because it
  is a reading of everything above rather than a decision about it.
- **Value** — what is at stake, and where it starts and ends. Stated once, here,
  and inherited by everything below. → `value-system.md`
- **Structure** — the design type and the act count, once the value and the spine
  are known. Choosing a structure before either is choosing a shape for nothing.
- `act_count` defaults to 3 and **adjusts upward on its own** if more acts exist,
  so it does not need maintaining by hand.
- *Note:* the sections carry the prose for all of this; the fields carry what
  the system reads. Neither requires the other — see `entity-sections.md`.

## The inciting incident and the climax: written twice

*One fact, two fields, two live consumers, and nothing checks they agree.*

- **The project points at the scene** — the inciting incident and the story
  climax, by slug. **The scene also carries its own boolean.** Both are read:
  the project pointer is what the dashboard's story view uses to find the scene,
  and the scene's flag is what the structural views and the scene badges use.
- **Setting one does not set the other.** Verified: the project can point at one
  scene while a different one carries the flag, and nothing reports a conflict.
- So when either is marked, **the other is a separate decision.** Either set both
  deliberately, or know which reader you are satisfying and which you are not.
- **The pointer may be written before the scene exists** — verified: a slug with
  no matching scene is accepted without complaint, and is simply inert until the
  scene is created. So the field can be reserved early, but it buys nothing
  until then.
- *Practical order:* create the scene, flag it, then point the project at it —
  unless the user has already decided which scene it will be, in which case
  writing the pointer early is a reasonable way to record the intention.

## The one step with no review loop

- **A project cannot be drafted.** `story_draft` refuses the op outright,
  because a project that does not exist has no database to hold a draft. So
  creation goes through `story_admin` directly: no `preview_md`, no
  confirmation, no chance to change your mind in the gap.
- Everything after it is protected — the project edits through the ordinary draft
  loop like any other entity. **The exposure is one call, at the very start.**
- That makes this the moment to be most careful and least automatic: ask what
  the project is before creating it, and do not invent a logline or a genre to
  fill a field. An empty field is recoverable; a wrong one is a decision the
  user did not make.
- *Not in this file:* the parameters. → `mechanics/project-lifecycle.md`

---

## Open questions

- [ ] The scene pointer and the scene boolean are one fact stored twice with no
      agreement check. Is "set both" the right guidance, or should the file say
      which reader each one serves and let the user choose?
- [ ] The order above is a dependency, not a procedure. Worth stating as
      "these constrain each other", or is that too soft to be useful?
