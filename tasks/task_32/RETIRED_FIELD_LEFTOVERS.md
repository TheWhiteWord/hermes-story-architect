# Retired-field leftovers — audit for the dashboard rework

Recorded 2026-10-12, after Phase 7 of task_32 (B1/B2). **Nothing here has been
changed.** It is the list to clean up during the dashboard rework, not a to-do
list for now.

## The refusal is structural, not a compatibility shim

There is no retired-key list anywhere in the code. The refusal is emergent:
`tools/story_import._extra_for` builds

    valid = skip | ENTITY_SCHEMAS[entity_type] | {id, type}

and rejects anything outside it; `create_entity` and `edit_entity` do the same
against `ENTITY_SCHEMAS`. Phase 5 deleted the story-track fields from
`ENTITY_SCHEMAS`, so the keys are simply not valid vocabulary any more. A note
carrying them fails to import — which is what blocked the live
`browser-verification-test` project until Phase 7 migrated it.

Consequence: nothing needs a special case for old data, because no project
exists that carries it. Only `character_value_at_open` / `_at_close` and
`arc_beat.shift` / `.y` remain, and both are kept on purpose for B3.

## Dead JS — reads fields nothing can populate

Verified: `core/db.py` produces `y` and `shift` for **arc_beat only**
(`get_character_arcs`, `_build_arc_beat`, `get_dashboard_data`). No producer
exists for a scene. `DASH.storySeries` reads `s.y`, so it returns `[]` for every
real payload — the story curve is empty by design (design §7).

| File:line | Reads | Status |
|---|---|---|
| `src/dashboard/js/views/story.js:40-42` | `p.story_value`, `p.story_value_at_open`, `p.story_value_at_close` (whole `valueArc` block) | dead |
| `src/dashboard/js/graph/arc-graph.js:158` | `p.scene.shift` on story points (`data-shift`) | dead |
| `src/dashboard/js/graph/arc-graph.js:340` | `DASH.story.project.story_value` | dead — falls back to the literal `'Story value'` it already has |
| `src/dashboard/js/panels/entity-panels.js:455-456` | `scene.value_at_open`, `scene.value_at_close`, `scene.conflict_levels` | dead |

`arc-graph.js:182` reads `beat.shift` on arc **beats** — that one is alive, do
not remove it. `showArcTooltip` (`:301`) defaults `data-shift` to `''` and
`tt-shift` is still used by beats, so dropping it from story points is safe.

## Dead tests

`tests/test_arc_graph_story_series.py` — 8 tests, all passing, all testing a
feature that no longer exists. They build a synthetic `DASH.story` with scene
`y` and `shift` and assert the story curve plots, sorts and warns. No payload
the app produces can contain a scene `y`, so they pass only on hand-injected
data. Design §7 accepts the empty curve; §9 "The new value graph (UI)" is where
this gets rebuilt on `plot.value_lines` instead.

Kept for now as reference for that rework, per the owner's call.

## What the rework should use instead

`plot.value_lines` is the read-back for exactly this: per value, its schema and
its turns in story order (scene id, from, to, and each affected character with
their conflict levels). It is already computed in `core/db.py:286`, exposed
through plot retrieve/describe/load, and present in the dashboard payload. The
story curve and the value-arc tags should be rebuilt from it rather than
restored.
