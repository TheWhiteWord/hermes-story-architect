# The value pass

*How the values of a scene are recorded after the scene exists, and read back.*
→ `theory/values.md`

**A separate step, never part of creating the scene.** Field shapes, types and
defaults are not here — `story_describe` is the authority on those.

---

1. **Before writing — read and think, record nothing.** Retrieve the plots the
   scene serves (`value_schemas`, plus `value_lines` if you want to see where each
   value stands), and brainstorm with the user what turns in the scene. Nothing is
   written at this stage.
2. **During writing — advice only.** While the scene's prose and sections are
   being written, the value question is guidance in the conversation, not a field
   to fill.
3. **After the scene exists — record the turns.** Propose an edit adding
   `value_turns` to the scene, the same way any other change is proposed.

The scene's `Content` and sections are the writing; `value_turns` are the record
of what the writing did to the values. They are written at different times on
purpose.

---

## Before recording

- **Retrieve the plots the scene serves in one call:** `story_retrieve` with
  `entity_type` plot, the plot ids, and `fields` set to `value_schemas` — add
  `value_lines` to see where each value currently stands.
- **Reuse a value if it genuinely fits, and say why** in the proposal. The
  reason is part of the record: it is what makes the choice reviewable.
- **A near match is not a reason to define a new value.** A plot's vocabulary is
  meant to be small enough to hold in mind. A second word for the same thing is a
  second line through the same story.
- **If none fits, define the value by adding `schema` (the four words, and an
  optional `note`) to the first turn that uses it.** The write registers it on
  the plot. Later turns just name the value.
- **A schema for a value the plot already has is refused**, identical words or
  not. The refusal shows the existing schema; use its words, or fix the existing
  one deliberately in a separate proposal.

## Opening states

- **`from` defaults to the last recorded state of that value** — the closing
  `to` of its most recent turn in `value_lines`.
- **Open elsewhere only when the scene itself shows a different state**: a
  flashback or a nonlinear telling, a time skip, a different counterpart or
  place, or a scene that reveals a change that happened earlier.
- **Say which one it is in `effect`.** The reason for the jump belongs in the
  record, not in the agent's head.
- **An unexplained difference is a break to fix**, not a value to preserve:
  either the opening state is wrong, or the neighbouring turn is wrong.

## After inserting, moving or deleting scenes

- **Compare the neighbouring turns' `from` and `to` in `value_lines`.** The line
  is read in story order, so a scene moved in the sequence changes what its
  neighbours continue from.
- **Read the scenes that may need a rewrite** — the ones whose opening state no
  longer follows.
- **Note them as `continuity_warnings`** via `story_memory`, so the rewrite is
  not lost between sessions.

## The positive side

The ladder grades antagonism, so P has nothing above it. Three cases:

- **Earned or naive.** A P reached after visiting C, CD or NN is earned, and its
  depth is the deepest rung visited — read that from `value_lines`, where the
  turns are in order. A P that arrives without the descent is naive, and that is
  a thing to notice rather than to record differently.
- **Beyond P.** Past the positive, the value usually *changes* rather than
  continues: justice becomes mercy. Define a successor value on the plot and
  turn on that.
- **Deepening.** Before recording `from` equal to `to`, check whether the change
  is in how it lands on the character — the conflict level and the `effect`
  sentence — and not in the value. A value that holds while its cost changes is a
  real turn, recorded as a turn.

## Planning

- **Discuss the values at play when creating plots, acts, sequences and scenes** —
  which value each is written around, and what the positive is for it.
- **Record the plan in the entity's sections**, in prose. Sections are where
  intent lives; `value_turns` are where execution is recorded.

## Roll-up and irony

- **Sequence, act and story summaries are read from `value_lines` by reasoning.**
  Nothing above the scene is stored or derived: read the plot's line and
  summarise it in the entity's sections.
- **Irony is out of scope here.** It needs B3 — what the character believes
  versus what is true — which does not exist yet. Do not express irony in
  `value_turns`; note it in the sections and leave it for B3.

---

## What the store checks

So the pass is not guessing what will be refused: on write, the plot exists; the
value has a schema on that plot (existing or supplied inline); `from` and `to`
are words of that schema; `effects` is not empty; each effect's character is one
of the plot's protagonists and appears once; each effect has at least one level;
each `conflict_level` is valid and appears once per character; each `effect`
sentence is present. `value_lines` is computed and every write path refuses it.

