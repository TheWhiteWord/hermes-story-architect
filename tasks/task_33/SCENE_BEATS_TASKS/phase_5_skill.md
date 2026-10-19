# Phase 5 — The skill

Prose only. It names the fields and sections of every earlier phase, so it
lands after them.

Verified against code on `feature/issue-redesign`.

---

## Tasks

- [ ] **T5.1** Add a `scene_beats` section to the skill's model file
      (`references/model/entity-sections.md`).

  The three sections and what goes in each:
  - **Conflict:** what resists the objective, and from which circle.
  - **Findings:** the evaluation of the scene (missing conflict, repetition,
    misplaced turning point, on-the-nose dialogue).
  - **Notes:** free-form.

  Also: the rule that `scene_beats` is exempt from unfilled checks (depth
  is elastic — it can be absent, minimal, or full).

- [ ] **T5.2** Update `references/craft/scene-design.md`.

  - The scene's `Beats` and `Conflict` sections move to `scene_beats`.
  - The scene keeps `Objective`.
  - The two directions are stated:
    - **Structure-first:** Scene created with intent (`scene_objective`,
      `value_turns`). `scene_beats` designs the beats and decides the
      turning point before the script is written. Script written.
      `scene_beats` revised. Scene fields reconciled.
    - **Content-first:** Script written. `scene_beats` read from the text.
      Scene fields derived.
  - Skill guidance: after writing or reworking `scene_beats`, check whether
    the scene's `scene_objective` and `effects` still hold. Fill gap, risk
    and `changes` where something moves, and leave the rest empty.

  **Verify:** no reference to a scene `Beats` section remains.

- [ ] **T5.3** Retire the `arc_beat` references in the skill.

  Files: `character-arc.md`, `value-system.md`, `value-pass.md`,
  `ids-and-links.md`, `entity-sections.md`.

  **Verify:** `git grep arc_beat tasks/task_30/skill/` returns nothing.

- [ ] **T5.4** Fix the `SKILL.md` file table to match the tree it lists.

  The file table does not match the tree (pre-existing). Every path in the
  table must exist.

  **Verify:** every path in the table exists.

---

## Findings

**F5.1 — the skill file table is wrong today.** It is pre-existing, not caused
by this design. Resolved by T5.4 as part of this phase, because a skill
that cannot be navigated is worse than a skill that is out of date.

## Dependencies

Phases 1–4 must be complete (all fields and sections exist).
