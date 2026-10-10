# NOTES — to write into SKILL.md

*Reminders collected while drafting. Not part of the skill. Delete when
SKILL.md is written.*

- **The boundary of judgement, in one sentence.** The user is the author: put
  every value to them, structure what they decide, never fill a blank to look
  finished. Stated once here, nowhere else — craft files do not repeat it.
- **Half-sentence to test:** read the entity's reference before writing it. Not
  its content — the fact that it has one. This is what stops the apparatus
  being skipped.
- **The narrowed words.** Theory speaks generally; the app fixes the meaning.
  Goes here as a standing table, not per entity:
  - **beat** — a scene's `Beats` section is the theory's exchange of
    behavior; an `arc_beat` is one moment in one character's arc. Two
    different things, one word.
  - **the value** — two tracks. Story value is the main investigation; a
    character's value is a position inside it. Same value for the protagonist,
    a facet of it for anyone else, never unrelated.
  - **turn → shift → y** — a chain. The turn produces the shift; the shift is
    stated in the story's words; `y` is that shift as a number, derived, for
    the curve. The shift is the fact, `y` is its measurement.
  - **crisis / climax** — not one field, and what it means depends on the
    entity: a dramatic function, a container's pointer, the scene it points
    at.
  - **milestone** — not a field at all. The agent never holds it. Omit.
  - where one field covers several theory concepts, the file says which.
- **Read the validation before asking the user to confirm, and fix a finding
  rather than reporting past it.** True of every draft of every entity, so it
  belongs here and not in a craft file.
- **A suggestion is not a value.** Offering options the user picks from is not
  supplying a decision. The agent proposes; the user chooses; nothing is
  stored until they do.
- **What advice is based on** — the story's own vocabulary, what the project
  already decided, and the system's own frame. Never the agent's taste.
- **The tools** — the table, one line each. Parameters are in the schemas.
- **How a session runs** — orient with a load, then narrow, then write as a
  proposal.
- **The hard rules** — the four from the first draft, re-checked: never commit
  unapproved, never invent an id, a blank is a question not a defect, the
  database is the source of truth.
- **Reference map** — the four folders and one line on when to read each.

## Open

- `location.mood` and `location.dramatic_function` have no theory in
  `Good_Writing.md`. Written in `craft/location.md` from what the app says
  they are. If a source exists, replace those lines.
- `craft/SAMPLE.md` is a working document, not part of the skill. Delete when
  the craft files are done.

---

## Issue A — Skill update notes (task 5)

### Theory guidance (design §4.2–4.3)

These are the standing rules the skill teaches. They live in the skill, not in
the schema.

1. **Plan, execution and verification are separate.** The plan is what the
   user or assistant intends. Execution is what the written scenes actually
   do. Verification is the user's and assistant's reasoning about plan
   versus execution against the theory. No program judges whether the story
   obeys the theory.
2. **Each fact is stored once.** Duplicated facts drift. The fixture
   `save-the-children` proved it: `is_inciting_incident: False` on a scene
   that both the project pointer and its own text claimed was the inciting
   incident.
3. **Only record what the theory does not already determine.** A sequence
   culminates in its climax and an act peaks in its climax — position follows
   from the theory. Recording it adds no information.
4. **The full set of story elements is tracked at story and plot level.**
   The source file defines them at story level. Applying them inside
   sequences and acts is an inference, and resolution cannot exist inside a
   unit that ends at its climax.
5. **Setup is not the inciting incident.** Setup is the opening state before
   the balance is upset. The inciting incident is the first major turn that
   upsets it, and the protagonist must react to it.
6. **Story-level milestones are the main plot's roles.** The main plot is the
   plot with `plot_scope = main`. The story's inciting incident, crisis and
   climax are whatever scenes hold those roles in the main plot. Nothing
   separate is stored at project level.
7. **Act and sequence climaxes are not stored.** Position follows from the
   theory.

### Planning instruction

Record any planning discussion for an element in that element's sections
when creating it. A plan can be written before any scene exists, and it
evolves with the writing. It never names a scene, because where an element
happens is only known once the scene is written. No new schema fields are
added for planning.

### Verification layer

The `story-theory` skill states the expectations (escalation, position of
climaxes, plan versus execution), and the findings go in the existing memory
categories: `decisions`, `open_questions`, `continuity_warnings`.

### What changed in scene-design.md

Removed stale descriptions of deleted fields:

- The "What the scene is for" bullet no longer lists `dramatic_role` values
  as structural roles (setup, complication, etc.). It now says
  `dramatic_role` only distinguishes whether a scene serves a plot
  (`plot_role`, `transition`, `non-event`), and `plot_roles` carries the
  six structural roles.
- The `is_inciting_incident`, `is_sequence_climax`, `is_act_climax`,
  `is_story_climax` flag names are gone from the bullet.
- The "Climaxes nest" bullet no longer says "several flags being true is not
  a conflict." It says which level a climax belongs to is decided by the
  container, not stored on the scene.
- The "A climax is as large as its level" bullet dropped the sentence about
  a sequence climax outrunning its act's climax landing flat (the theory
  point stands without it).
- "The couplings" section dropped the two bullets about `climax_scene_id`
  pointers and the incident flag/pointer pattern — both removed in Issue A.

### Verification

- Skill files are not tested by the suite. The check is that no test imports
  or parses them. Suite stays green without changes for this task.
- `core/constants.py` confirms `PLOT_ROLES` has six roles including
  `inciting_incident`, and `SCENE_DRAMATIC_ROLES` is `["plot_role",
  "transition", "non-event"]` — the scene-design.md description now matches.
- `core/entity.py` `validate_scene_dramatic_role` confirms `dramatic_role`
  carries no structural role, only the plot-serving distinction.

