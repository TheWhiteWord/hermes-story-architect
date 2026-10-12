# Phase 6: Skill Update

**Goal:** Update the skill with the value pass guidance — how to record value turns, how to read them back, and how to handle continuity.

**Plan reference:** §5

## Code verification findings

- The skill is a SKILL.md file packaged with the plugin
- It guides the LLM on how to use the story tools
- The value pass is a separate step, never part of creating the scene
- The skill needs to teach: before recording, opening states, after inserting/moving/deleting scenes, the positive side, planning, roll-up and irony

## Tasks

### 6.1 — Add the value pass section to the skill
- [x] A separate step, never part of creating the scene
- [x] Before writing: brainstorm from the plot's schemas and lines, recording nothing
- [x] During writing: advice only
- [x] After the scene exists: record the turns

### 6.2 — Add "Before recording" guidance
- [x] Retrieve the plots the scene serves in one call: `story_retrieve` with `entity_type` plot, the plot ids, and `fields` set to `value_schemas` (add `value_lines` to see where each value stands)
- [x] For each value in the scene, use an existing value if it genuinely fits and say why
- [x] A near match is not a reason to define a new one
- [x] If none fits, define it by adding `schema` (the four words) to the first turn that uses it
- [x] The write registers it on the plot

### 6.3 — Add "Opening states" guidance
- [x] Default to the last recorded state of that value
- [x] Open elsewhere only when the scene itself shows a different state: a flashback or nonlinear telling, a time skip, a different counterpart or place, or a scene that reveals an earlier change
- [x] Say which in `effect`
- [x] An unexplained difference is a break to fix

### 6.4 — Add "After inserting, moving or deleting scenes" guidance
- [x] Compare the neighbouring turns' `from` and `to` in `value_lines`
- [x] Read the scenes that may need a rewrite
- [x] Note them as `continuity_warnings`

### 6.5 — Add "The positive side" guidance
- [x] The ladder grades antagonism, so P has nothing above it
- [x] Earned or naive: a P reached after visiting C, CD or NN is earned, and its depth is the deepest rung visited. Read it from `value_lines`.
- [x] Beyond P: the value usually changes (justice becomes mercy). Define a successor value on the plot.
- [x] Deepening: before recording `from` equal to `to`, check whether the change is in how it lands on the character (the conflict level and `effect`) and not in the value.

### 6.6 — Add "Planning" guidance
- [x] Discuss the values at play when creating plots, acts, sequences and scenes
- [x] Record the plan in the entity's sections

### 6.7 — Add "Roll-up and irony" guidance
- [x] Sequence, act and story summaries are read from `value_lines` by reasoning
- [x] Irony needs B3 (what the character believes versus what is true)

### 6.8 — Verify the skill loads correctly
- [x] The plugin registers the skill via `ctx.register_skill()` in `register()` — verified: `__init__.py:236 _register_skills` → `ctx.register_skill("hermes-story-architect", <repo>/skills/hermes-story-architect/SKILL.md, ...)`, called from `register()` at line 164
- [x] The skill has `provides_skills:` in `plugin.yaml` — verified: line 18-19
- [x] Restart Hermes after syncing — an operator step, required before the new file is live
- [x] Verify the skill is discoverable — pending the restart + copy into `skills/hermes-story-architect/`; see the Placement section of the standalone file

## Checklist

- [x] Value pass section added
- [x] Before recording guidance added
- [x] Opening states guidance added
- [x] After inserting/moving/deleting scenes guidance added
- [x] The positive side guidance added
- [x] Planning guidance added
- [x] Roll-up and irony guidance added
- [x] Skill verified loading in Hermes — registration path verified in code; live discovery pending the copy + restart

---

## Final Brief

**Deliverable:** `tasks/task_30/VALUE_PASS_SKILL_SECTION.md` — the §5 guidance
as a standalone agent-facing draft, written in the skill's house style (short
imperative rules, no field shapes, `story_describe` left as the authority), plus
a "What the store checks" block so the pass knows what a write will refuse, and
a Placement section recording where it lands.

**Written as a new file, not an edit,** per the brief: nothing in the repo's
skill tree was touched. The registration path was verified by reading the code,
not assumed — `provides_skills` in `plugin.yaml` and
`ctx.register_skill(...skills/hermes-story-architect/SKILL.md...)` in
`_register_skills` (`__init__.py:236`), called from `register()`.

**Verified against code before writing, and my first pass was partly wrong.**
Checking each flagged file against the live `ENTITY_SCHEMAS` (not keyword
matches) showed only **three** are actually stale; the other three describe the
B3 character/arc_beat track, which phase 5 kept on purpose:

- **Genuinely stale (3):** `model/value-system.md` (story-track field table +
  `view="story_value"`), `craft/scene-design.md` (scene
  `value_at_open/close/shift/y`), `mechanics/reading-the-project.md` (the
  `story_value` view + the story-track `value_at_close` line).
- **False positives — kept for B3, leave alone:** `theory/values.md` (only the
  verb "shift" in prose), `craft/character.md` (the character's arc charges,
  which still exist), `craft/character-arc.md` (all `arc_beat` fields, all
  still in the schema). My earlier "six stale files" claim was over-broad; the
  Placement section of the draft is corrected to match the code.

I did **not** edit them: this phase was scoped to add the new section, and
rewriting those files is a separate decision. The draft's Placement section now
records exactly which files it supersedes.

**Open items for you:**
1. Copy `VALUE_PASS_SKILL_SECTION.md` → `skills/hermes-story-architect/
   references/craft/value-pass.md`, add the SKILL.md craft-table row, restart
   Hermes, confirm it's discoverable — that's the only way 6.8's last two boxes
   close. Outside this phase's file scope, so it needs your go-ahead.
2. The stale six-file pass above.
