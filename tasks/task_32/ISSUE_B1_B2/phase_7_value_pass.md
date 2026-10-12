# Phase 7: Value Pass Over Fixture and Test Project

**Goal:** Run the value pass over the fixture and the test project. Note anything the model cannot express.

**Plan reference:** §6 Step 7

## Tasks

### 7.1 — Run the value pass over the fixture
- [x] Open the fixture project
- [x] For each scene, identify the values at play
- [x] Record value turns using the new system
- [x] Define value schemas on plots where needed
- [x] Verify the turns read back correctly through `story_retrieve` with `fields=['value_lines']`

### 7.2 — Run the value pass over the test project (if one exists)
- [x] Same as 7.1 but for the live test project
- [x] If no test project exists, skip this task

**Live project: `browser-verification-test`.** It could not be imported at
all — the importer hard-refuses the retired keys, so every live edit through
the tool chain was blocked. Migrated by `tests/live_value_pass.py`: 11 notes
changed, DB rebuilt, verified through `story_retrieve`, `story_load`,
`get_dashboard_data` and an export→import round-trip. Idempotent (second run:
0 changes). See the Live project brief below.
### 7.3 — Note anything the model cannot express
- [x] Are there value shifts that don't fit the four-rung ladder?
- [x] Are there effects that don't fit the three conflict levels?
- [x] Are there values that need more than four words?
- [x] Is the `from`/`to` vocabulary too coarse or too fine?
- [x] Note any friction in the recording process

### 7.4 — Final verification
- [x] Full test suite passes
- [x] Fixture data is consistent (no orphaned value_turns, all schemas registered)
- [x] `story_retrieve` with `fields=['value_lines']` returns sensible data for the fixture
- [x] The dashboard still loads with the updated fixture
- [x] Export/import round-trip works with value data

## Checklist

- [x] Value pass run over fixture
- [x] Value pass run over test project (if applicable)
- [x] Model limitations noted
- [x] Full test suite passes
- [x] Fixture data consistent
- [x] Dashboard loads with fixture
- [x] Round-trip works

---

## Final Brief

**The pass.** `tests/value_pass_b1_b2.py` is the reproducible record (kept, per
your call). Markdown is the fixture's source of truth — `conftest.py` builds the
DB from it — so the pass writes the notes, then a COPY is imported to exercise
the real write path (validation + inline-schema registration) and read the
results back.

Two values declared on the main plot `the-resistance` (protagonists `kael`,
`mira`), each with its four-rung schema:
- **freedom**: p free, c dependent, cd imprisoned, nn gilded cage
- **trust**: p open, c wary, cd deceived, nn exploited

Three scenes carry two turns each (one per value). `value_lines` reads back in
story order, export→import round-trips every nested `effects`/`levels` entry,
and `get_dashboard_data` builds the dashboard payload with the value data
present. Schemas are declared on the plot note, so no scene needs an inline
`schema` — the clean form.

**No test project exists** (confirmed in Phase 0.3), so 7.2 is skipped.

**7.3 — what the model cannot express.** Running the pass surfaced one real
friction, not a vocabulary gap:

- **`from == to` is the model's honest case, and the fixture is full of it.**
  The last two scenes of every value hold the state (`free → free`,
  `open → open`). The ladder grades the *value's* opposition, so once a value
  reaches P there is nothing above it — the meaningful change moves into the
  conflict level and `effect`, exactly as §5 "Deepening" says. The model
  expresses this fine (the `effect` sentence carries the shift), but it means
  a "value arc" read from `from`/`to` alone is flat for the back half of a
  story. The depth is in `levels[].effect`, not the rung. Worth knowing before
  anyone builds a roll-up on the rung alone (design §5 "Roll-up").
- **Four words per value was enough** for this fixture; no value needed more.
  The `from`/`to` vocabulary is neither too coarse nor too fine at this scale.
- **Three conflict levels were enough**; every effect landed cleanly on inner /
  personal / extra-personal.
- **One schema word can only belong to one rung per plot**, which is correct,
  but a story that wants the *same word* to mean P in one scene and C in
  another (irony) has no way to say it — that is what B3's "what the character
  believes versus what is true" is for, and it is out of scope here.

**The bug the pass exposed (C, fixed properly per your call).** `edit_entity`
did not run the shape validator that `create_entity`, the importer and the
draft stager all run, so a wrong-typed value landed verbatim in `extra`.
`value_schemas: "PROBE"` on a plot stored a string, and the next scene edit
crashed with `AttributeError` reading it as a list of dicts. Fix: `edit_entity`
now validates the shape of any structured field in `data` before writing and
refuses with the same findings the other paths report (`core/writes.py`, the
"Shape of a structured field" block). `plot_roles` is excluded — its bespoke
validator owns it with its own pinned messages.

Two tests changed contract as a consequence, both correctly:
- `test_edit_silent_success` sweep now probes each field with a **type-correct**
  value and rebuilds the project per probe (a plot-schema probe otherwise
  orphans the scenes' turns). It asserts acceptance of a *valid* value, not
  tolerance of a wrong one — which is the real invariant now that edit refuses
  bad shapes.
- `test_soft_delete::test_story_load_omits_it` now asserts the deleted
  character is absent as an **entity node**, not absent from all text: a value
  turn legitimately names a character in its `effects` prose, so "no trace"
  was never the right invariant once turns reference characters by name.
- `test_story_describe` vocabulary test collects `sub_fields` **recursively**
  and registers the computed `value_lines` read-back keys (`turns`, `scene_id`,
  `from`, `to`, `schema`), matching the now-nested schema.

**Suite: 1094 passed** (was 1094 before the pass, 3 broken by the value data,
now green with the fix).

---

## Live project brief — `browser-verification-test`

**It was broken, not merely stale.** `story_import` hard-refuses the retired
keys, so the project could not be imported at all and every live edit through
the tool chain was blocked. `story_import --dry_run` confirmed nothing would be
destroyed (all 37 DB entities have notes behind them), a copy was migrated and
verified, and only then were the live notes touched. The import made its own
timestamped DB backup; I also left `browser-verification-test.bak-20261012-193643`
next to it.

**The turns carry the facts the retired fields held.** The old scene `shift`
string was the value vocabulary and the old `conflict_levels` said which circle
each shift reached, so the new turns are read off that data rather than
invented. One value, `trust`, on `the-resistance`, with the four rungs
p self-trust / c doubt / cd suspicion / nn self-deception — the words taken
from the project's own shift strings. Six scenes, one turn each, and the
opening state of each turn continues the previous scene's closing state, which
is what the old `value_at_open`/`value_at_close` pairs encoded. `garden-dream`
is the one deliberate break: it is a dream, so it opens on the state the scene
itself shows and the `effect` says why.

**The pass found a pre-existing structural error, and it was fixed with your
go-ahead.** `the-core-day` — the resolution ("the children emerge into the real
world for the first time", "We're free") — was filed in Act I / The Discovery
with `order: 3`, while `the-door-closes`, whose own note calls it "the last
scene of the script", sat in Act II. Story order is what `value_lines` reads,
so the trust line put the resolution third and read the back half out of
sequence. Moved to `seq-confrontation` / `act-2` / `order: 5`; the line now
runs continuously:

```
central-room-day     self-trust -> suspicion
central-room-night   suspicion -> self-trust
garden-day           self-trust -> self-trust   (holds, quality changes)
garden-dream         self-trust -> doubt        (dream — deliberate break)
the-door-closes      doubt    -> self-trust
the-core-day         self-trust -> self-trust   (earned, shared)
```

**Verified on the live project:** import succeeds, no retired keys remain
(`arc_beat.shift`/`y` correctly kept for B3), `story_load` shows the corrected
structure, `value_lines` reads in story order, the dashboard builds with
`value_turns` in its payload, and export→import round-trips every turn and the
schema. Suite still 1094 passed.

**Open for you:** `the-door-closes` carries `order: 4` but is the script's last
scene — after the reorder it still sorts before `the-core-day`. Its prose says
the choice is permanent and the door cannot be reopened, so whether the final
image is the leaving or the arriving is a story decision, not a data one. Left
alone deliberately.
