# The value pass

*How the values of a scene are recorded after the scene exists, and read back.*
→ `theory/values.md`

**A separate step, never part of creating the scene.** Field shapes, types and
defaults are not here — `story_describe` is the authority on those.

---

1. **Before writing — read and think, record nothing.** Run
   `story_load view='values' scene=<id>`: it returns the sequence's and act's
   major/minor values, and for each plot the scene serves, where every value
   was last left (scene, closing word) and where it turns next (scene, opening
   word). Brainstorm with the user what turns in the scene. Nothing is written
   at this stage.
2. **During writing — advice only.** While the scene's prose and sections are
   being written, the value question is guidance in the conversation, not a
   field to fill.
3. **After the scene exists — record the turns.** Propose an edit adding
   `value_turns` to the scene, the same way any other change is proposed.

The scene's `Content` and sections are the writing; `value_turns` are the
record of what the writing did to the values. They are written at different
times on purpose.

---

## Before recording

- **See what values exist:** `story_load view='values'` with no arguments
  lists every value entity with its four rung words. A value is an entity, one
  per value, shared by every plot that uses it — a value has one schema
  wherever it is used.
- **Reuse a value if it genuinely fits, and say why** in the proposal. The
  reason is part of the record: it is what makes the choice reviewable.
- **A near match is not a reason to create a new value.** The vocabulary is
  meant to be small enough to hold in mind. A second word for the same thing
  is a second line through the same story.
- **If none fits, create the value, then record the shift.** Read
  `theory/values.md` first — the four rungs are a design choice (what the
  positive is for this value, what its contrary/contradictory/negation-of-negation
  mean in this story), not a form to fill. Then use `story_draft` to create a
  `value` entity (the `name` plus four distinct words, and an optional
  `note`). The create can go in the same draft as the scene edit — a draft
  applies creates before edits. Then name the value in the turn. Nothing is
  defined inline on the scene.
- **A turn naming a value that does not exist is refused.** The message lists
  the defined values and their words and says to create the value first.

## Opening states

- **`from` defaults to the last recorded state of that value** — read it from
  the scene view as `last_left`, the closing word of the value's most recent
  turn before this scene.
- **Open elsewhere only when the scene itself shows a different state**: a
  flashback or a nonlinear telling, a time skip, a different counterpart or
  place, or a scene that reveals a change that happened earlier.
- **Say which one it is in `effect`.** The reason for the jump belongs in the
  record, not in the agent's head.
- **An unexplained difference is a break to fix**, not a value to preserve:
  either the opening state is wrong, or the neighbouring turn is wrong.

## After inserting, moving or deleting scenes

- **Re-read the plot's turns through the values view**:
  `story_load view='values' plot=<id>` returns each value's turns in story
  order (scene, plot, from, to). The line is read in story order, so a scene
  moved in the sequence changes what its neighbours continue from.
- **Read the scenes that may need a rewrite** — the ones whose opening state no
  longer follows.
- **Note them as `continuity_warnings`** via `story_memory`, so the rewrite is
  not lost between sessions.

## The positive side

The ladder grades antagonism, so P has nothing above it. Three cases:

- **Earned or naive.** A P reached after visiting C, CD or NN is earned, and
  its depth is the deepest rung visited — read the plot's turns in order from
  the values view (`story_load view='values' plot=<id>`). A P that arrives
  without the descent is naive, and that is a thing to notice rather than to
  record differently.
- **Beyond P.** Past the positive, the value usually *changes* rather than
  continues: justice becomes mercy. Create a successor value and turn on that.
- **Deepening.** Before recording `from` equal to `to`, check whether the
  change is in how it lands on the character — the conflict level and the
  `effect` sentence — and not in the value. A value that holds while its cost
  changes is a real turn, recorded as a turn.

## Planning

- **Discuss the values at play when creating plots, acts, sequences and
  scenes** — which value each is written around, and what the positive is for
  it.
- **Before writing into a sequence or act, read `value_focus`**
  (`story_retrieve` on the sequence, act or project with
  `fields=['value_focus']`) to see which values are major and minor there, and
  weigh the scene's shifts against them.
- **Record the plan in the entity's sections**, in prose. Sections are where
  intent lives; `value_turns` are where execution is recorded.

## Roll-up and irony

- **Sequence, act and story: read the computed `value_focus`** for which
  values are major and minor (`story_retrieve` on the entity with
  `fields=['value_focus']`; the project's major is the main plot's, minor the
  subplots'). The reasoning is now only for the prose summary — write it in
  the entity's **sections**.
- **Irony is out of scope here.** It needs B3 — what the character believes
  versus what is true — which does not exist yet. Do not express irony in
  `value_turns`; note it in the sections and leave it for B3.

---

## What the store checks

So the pass is not guessing what will be refused: on write, the plot exists;
the turn's value names an existing `value` entity (else the write is refused,
and the message lists the defined values and their words and says to create
the value first); `from` and `to` are words of that value entity's four rungs
(p/c/cd/nn); `effects` is not empty; each effect names one protagonist of the
plot, once; each effect has at least one level, one per conflict circle; each
`conflict_level` is valid and appears once per character; each `effect`
sentence is present.
