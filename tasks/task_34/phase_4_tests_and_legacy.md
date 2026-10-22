# Phase 4 — Tests and legacy

**Goal.** The test suite describes the system as it now is, and nothing old
survives past its usefulness.

**State on entry.** Phases 1–3 are done. The tabs are landed, named, and sized.

## Tasks

### 4.1 — Inventory what the new surface needs tested

Write the list before writing the tests, so the tests are chosen rather than
accumulated.

- [ ] Enumerate every behaviour the tabs have that nothing currently asserts:
      the payload reader, both empty states, the lane/stacked switch, the gap and
      self-directed arrow, the act focus, the hover card, the milestone label.
- [ ] For each, say whether it belongs in a node-level check or a headless-Chrome
      check. The rule already in this repo: **node for pure functions, Chrome for
      anything that only a browser can see.**

### 4.2 — Put the checks where the repo keeps them

- [ ] The node harness used in Phase 1 (44 checks) becomes a permanent fixture,
      not a scratch file. Give it a home and a name that says what it checks.
- [ ] The headless-Chrome checks join `tests/test_dashboard.py`, beside the
      existing `_dom` helper and `TestActuallyRenders` — that class already
      drives the dashboard's own JS and asserts on the built DOM, which is
      exactly the shape these need.
- [ ] Delete the scratch copies from `~/.hermes/cache/scratch/` once the
      permanent versions are green.

### 4.3 — Refactor the tests that the tabs disturbed

Not addition on top — the suite should read as one thing.

- [ ] `test_every_class_the_panels_use_exists_in_the_css` (extended in Phase 1)
      now covers the tab files. Confirm it has no allowlist and no skipped
      groups; if a group had to be skipped, say why in a comment or drop it.
- [ ] Look for tests that assert the *old* panel shape and now pass only by
      accident. A test that still passes while asserting something the code no
      longer does is worse than no test.

### 4.4 — Sweep for legacy and old code

The tabs read `story.scene_beats[]`, `valueModel`, `valueSlice`, `valueAxisSvg`,
`valueChipStyle`, `roleColor`, `relTypeColor`, `plotColor`, `milestoneLabel`,
`renderSectionsHtml`. Check each is still the only path to that fact.

- [ ] `core/db.py` still emits `scene.scene_beats` as the **pointer** for the base
      map, and `scene_beats[]` whole for the dashboard. Confirm both readers still
      exist and neither was left half-migrated.
- [ ] `core/track.py` `deepest` (the word) — still read by the LLM-facing
      `story_load` view after Phase 2 renamed the JS field. Confirm no reader was
      missed.
- [ ] `tools/story_load.py:208-215` builds its own `scene_beats` map for the
      `dramatic_elements` view. That is a separate reader of the same rows —
      confirm it still agrees with what the dashboard now emits, and say so.
- [ ] Any panel code the tabs make redundant. Do not delete on suspicion:
      remove only what nothing reads, and name the reader that was checked.

### 4.5 — Naming verification

The standing rule for this work: after a refactor, names are checked against the
state, not left because they were fine before.

- [ ] Every class a tab emits has a rule, and no tab reads another tab's class —
      the Phase 1 guard covers the first; add the second (the journey tab reading
      `.sb-*` out of the beat tab's stylesheet was a real defect found this way).
- [ ] Every `data-*` attribute a tab reads is one it emits, or one documented as
      a protocol (`data-ent`, `data-hermes-send`).
- [ ] No `var()` reference resolves to an undeclared token. The Phase 1 harness
      checks the two accents; extend it to every custom property the tab CSS uses.

### 4.6 — Verify

- [ ] Full suite green.
- [ ] The node and Chrome harnesses green from their permanent homes.
- [ ] Record in this file what was removed, and what was checked before removing
      it.

## Parallel work

None. This phase closes the work.

## Checklist

- [ ] Behaviour inventory written, each item assigned to node or Chrome
- [ ] Node harness and Chrome checks given permanent homes; scratch copies deleted
- [ ] Test suite refactored, not extended — no accidental passers
- [ ] Legacy sweep done; removals named with the reader that was checked
- [ ] Naming verification done: classes, `data-*`, custom properties
- [ ] Full suite green
- [ ] Removals recorded here
