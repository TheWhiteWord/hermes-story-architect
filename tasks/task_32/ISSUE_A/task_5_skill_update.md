# Task 5: Update the `story-theory` skill

## Goal

Update the `story-theory` skill with the theory guidance from the design
document (section 4.3) and the instruction to record planning in entity
sections when creating elements.

## Work

### 5.1 Locate the skill

The skill is at `skills/story-theory/SKILL.md` (or similar path — verify).

### 5.2 Add theory guidance

Add the following to the skill:

1. **Plan, execution and verification are separate.** The plan is what the
   user or assistant intends. Execution is what the written scenes actually
   do. Verification is the user's and assistant's reasoning about plan versus
   execution against the theory. No program judges whether the story obeys
   the theory.

2. **Each fact is stored once.** Duplicated facts drift.

3. **Only record what the theory does not already determine.** A sequence
   culminates in its climax and an act peaks in its climax — position follows
   from the theory.

4. **The full set of story elements is tracked at story and plot level.**
   The source file defines them at story level. Applying them inside
   sequences and acts is an inference.

5. **Setup is not the inciting incident.** Setup is the opening state before
   the balance is upset. The inciting incident is the first major turn that
   upsets it.

6. **Story-level milestones are the main plot's roles.** The main plot is the
   plot with `plot_scope = main`. The story's inciting incident, crisis and
   climax are whatever scenes hold those roles in the main plot.

7. **Act and sequence climaxes are not stored.** Position follows from the
   theory.

### 5.3 Add planning instruction

Add the instruction: "Record any planning discussion for an element in that
element's sections when creating it. A plan can be written before any scene
exists, and it evolves with the writing. It never names a scene, because
where an element happens is only known once the scene is written."

### 5.4 Add verification layer guidance

Add: "The `story-theory` skill states the expectations (escalation, position
of climaxes, plan versus execution), and the findings go in the existing
memory categories: `decisions`, `open_questions`, `continuity_warnings`."

## Checklist

- [x] Theory guidance added to skill
- [x] Planning instruction added
- [x] Verification layer guidance added
- [x] Skill file saved
- [x] Full suite green (skill is not tested, but verify nothing breaks)

## Final brief

Updated two files to remove stale descriptions of fields deleted in the
Issue A refactor, and added the theory guidance from design §4.2–4.3.

**scene-design.md** — two sections had drifted from the code:

1. "What the scene is for" bullet: `dramatic_role` no longer carries
   structural roles (setup, complication, crisis, climax, resolution).
   It now only says whether a scene serves a plot (`plot_role`,
   `transition`, `non-event`). The structural roles live in `plot_roles`,
   one entry per plot, with six roles including `inciting_incident`.
   Removed all references to the deleted `is_inciting_incident`,
   `is_sequence_climax`, `is_act_climax`, `is_story_climax` flags.

2. "The couplings" section: dropped the two bullets about
   `climax_scene_id` pointers and the incident flag/pointer pattern —
   both removed in the refactor. Remaining couplings (beat/cast,
   heading/Fountain first line) are unchanged.

**NOTES_SKILL.md** — appended the Issue A skill update notes:

- Theory guidance (7 rules from design §4.2–4.3)
- Planning instruction (record plans in entity sections, never name a scene)
- Verification layer guidance (findings go in `decisions`,
  `open_questions`, `continuity_warnings`)
- Change log for scene-design.md with verification against `core/constants.py`
  and `core/entity.py`

Skill files are not tested; the suite stays green without changes.
