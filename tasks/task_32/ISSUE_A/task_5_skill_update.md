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

- [ ] Theory guidance added to skill
- [ ] Planning instruction added
- [ ] Verification layer guidance added
- [ ] Skill file saved
- [ ] Full suite green (skill is not tested, but verify nothing breaks)
