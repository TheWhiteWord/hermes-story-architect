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
- [ ] A separate step, never part of creating the scene
- [ ] Before writing: brainstorm from the plot's schemas and lines, recording nothing
- [ ] During writing: advice only
- [ ] After the scene exists: record the turns

### 6.2 — Add "Before recording" guidance
- [ ] Retrieve the plots the scene serves in one call: `story_retrieve` with `entity_type` plot, the plot ids, and `fields` set to `value_schemas` (add `value_lines` to see where each value stands)
- [ ] For each value in the scene, use an existing value if it genuinely fits and say why
- [ ] A near match is not a reason to define a new one
- [ ] If none fits, define it by adding `schema` (the four words) to the first turn that uses it
- [ ] The write registers it on the plot

### 6.3 — Add "Opening states" guidance
- [ ] Default to the last recorded state of that value
- [ ] Open elsewhere only when the scene itself shows a different state: a flashback or nonlinear telling, a time skip, a different counterpart or place, or a scene that reveals an earlier change
- [ ] Say which in `effect`
- [ ] An unexplained difference is a break to fix

### 6.4 — Add "After inserting, moving or deleting scenes" guidance
- [ ] Compare the neighbouring turns' `from` and `to` in `value_lines`
- [ ] Read the scenes that may need a rewrite
- [ ] Note them as `continuity_warnings`

### 6.5 — Add "The positive side" guidance
- [ ] The ladder grades antagonism, so P has nothing above it
- [ ] Earned or naive: a P reached after visiting C, CD or NN is earned, and its depth is the deepest rung visited. Read it from `value_lines`.
- [ ] Beyond P: the value usually changes (justice becomes mercy). Define a successor value on the plot.
- [ ] Deepening: before recording `from` equal to `to`, check whether the change is in how it lands on the character (the conflict level and `effect`) and not in the value.

### 6.6 — Add "Planning" guidance
- [ ] Discuss the values at play when creating plots, acts, sequences and scenes
- [ ] Record the plan in the entity's sections

### 6.7 — Add "Roll-up and irony" guidance
- [ ] Sequence, act and story summaries are read from `value_lines` by reasoning
- [ ] Irony needs B3 (what the character believes versus what is true)

### 6.8 — Verify the skill loads correctly
- [ ] The plugin registers the skill via `ctx.register_skill()` in `register()`
- [ ] The skill has `provides_skills:` in `plugin.yaml`
- [ ] Restart Hermes after syncing
- [ ] Verify the skill is discoverable

## Checklist

- [ ] Value pass section added
- [ ] Before recording guidance added
- [ ] Opening states guidance added
- [ ] After inserting/moving/deleting scenes guidance added
- [ ] The positive side guidance added
- [ ] Planning guidance added
- [ ] Roll-up and irony guidance added
- [ ] Skill verified loading in Hermes
