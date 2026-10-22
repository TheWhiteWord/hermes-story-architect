# The value pass — skill section (standalone draft)

**Status:** this draft is **superseded by the skill reference**
`tasks/task_30/skill/references/craft/value-pass.md` (the same file in the
skill tree). Read that file — it carries the value-pass section in full, in
the form it would ship, and it is kept in sync with this section's intent.
This draft is retained only as the review copy of that reference.

**Audience:** the agent, not a reader of documentation. Every rule is stated as
the action to take. Field shapes, types and defaults are not here —
`story_describe` is the authority on those.

---

## The value pass

A **separate step, never part of creating the scene.** A scene is created with
no `value_turns` at all; the pass fills them in afterwards by editing the
scene. `story_load view='values' scene=<id>` before writing;
`story_retrieve(fields=['value_focus'])` before writing into a sequence or
act; create the `value` entity first — read `theory/values.md` to set its
four rungs as a design choice, not a form — then record the shift. The full
rules — the values-view calls, the create-then-record workflow, and what the
store checks — are in `references/craft/value-pass.md`.

---

## Placement

- **Target:** a new reference file, `references/craft/value-pass.md`, listed in
  SKILL.md's craft table (read when: recording a value turn, or checking what
  a scene did to a value; theory: `references/theory/values.md`).
- **Supersedes:** `references/model/value-system.md` (its whole story-track
  field table and `view="story_value"` — project/act/sequence/scene no longer
  carry a value word, charge, shift or `y`; the character/arc_beat B3 track
  below is unaffected and stays) and the scene value passages in
  `references/craft/scene-design.md` (the `value_at_open/close/shift/y` block)
  and `references/mechanics/reading-the-project.md` (the `story_value` view).
- **Not superseded — still correct:** `references/theory/values.md`,
  `references/craft/character.md`, `references/craft/character-arc.md` describe
  the character/arc_beat track, which B1/B2 intentionally kept for B3. Only
  the scene and story-container value fields were removed.
- **Registration (task 6.8):** the skill is registered in code, not by file
  position — `provides_skills: hermes-story-architect` in `plugin.yaml`, and
  `ctx.register_skill("hermes-story-architect", <repo>/skills/
  hermes-story-architect/SKILL.md, ...)` in `__init__.py` (`_register_skills`).
  Both verified present in the repo. Landing this file requires it to be
  copied into `skills/hermes-story-architect/references/craft/` and Hermes
  restarted; that is an operator step outside this draft.
