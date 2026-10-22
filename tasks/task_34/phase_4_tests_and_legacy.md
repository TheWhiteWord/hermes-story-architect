# Phase 4 — Tests and legacy

**Goal.** The test suite describes the system as it now is, and nothing old
survives past its usefulness.

**State on entry.** Phases 1–3 are done. The tabs are landed, named, and sized.

## Tasks

### 4.1 — Inventory what the new surface needs tested

Write the list before writing the tests, so the tests are chosen rather than
accumulated.

- [x] Enumerate every behaviour the tabs have that nothing currently asserts:
      the payload reader, both empty states, the lane/stacked switch, the gap and
      self-directed arrow, the act focus, the hover card, the milestone label.
- [x] For each, say whether it belongs in a node-level check or a headless-Chrome
      check. The rule already in this repo: **node for pure functions, Chrome for
      anything that only a browser can see.**

Checked against the landed files (`src/dashboard/js/…`), not the plan. Two of the
brief's items are already covered and are not re-invented: the payload reader
(`sceneBeatsOf`, three paths) and both Beats empty-state branches have node checks
in the scratch harness; the strip, the pane, and the ribbon/timeline shells have
Chrome checks in `TestActuallyRenders`.

#### Node — pure functions, or strings a browser would only echo

| behaviour | where it lives | state |
|---|---|---|
| `sceneBeatsOf` by `scene` / by `parent_id` alone / `null` | `track-data.js:29` | harness ✓ |
| `entityRef` for character, location, world, relationship, unknown; location/world colour from `ENTITY_KIND_COLORS` | `track-data.js:36` | **nothing** |
| `characterTrack` rows, coverage, protagonist, turns | `track-data.js:73` | harness ✓ |
| `deepestRung` is an index 0..3 or null, never the rung's word | `track-data.js:125` | harness ✓ |
| `milestoneLabel` for all six milestones + the `plot_` prefix | `value-graph.js:34` | harness ✓ |
| Beats: driver chip, objective, turning point, beat rows, gap rows, activity rows, crack, `is-self`, circumstance lane, changes, true character, notes, empty states | `scene-beats-tab.js` | harness ✓ |
| Beats: lane vs stacked switch at a given width | `scene-beats-tab.js:110` | harness ✓ (one width only) |
| Journey: stats, value chip, conflict levels, ribbon svg, depth rungs, milestone label, timeline, wants, nothing-to-trace | `character-journey-tab.js` | harness ✓ |
| Journey: act focus (`jr-focus`, `jr-chip.on`, act narrowing) | `character-journey-tab.js:150` | **nothing** |
| Journey: ribbon slot rule `max(MIN_SLOT, (W − LABEL_W − PAD_R) / n)` and the fill share at 1–48 scenes | `character-journey-tab.js:229` | **nothing** (Phase 3 probe) |
| Journey: axis is the value graph's own, labelled `plot` — `>plot</text>`, no string replacement | `character-journey-tab.js:132` | **nothing** (Phase 2 fix) |
| CSS contracts: every emitted class has a rule; no cross-tab class read; the two accent tokens | tab CSS | harness ✓ (two tokens only) |

#### Chrome — only a browser can see it

| behaviour | why Chrome | state |
|---|---|---|
| Both tabs render on the assembled page, strip + pane + content | the shipping path | `TestActuallyRenders` ✓ |
| Beats empty state on the real page (the fixture's placeholder scenes) | the payload, not a synthetic one | **nothing** |
| Lane/stacked switch at real panel widths | layout is the thing | **nothing** |
| Self-directed arrow drawn, with its head at the turn | SVG geometry | **nothing** |
| Act focus chips narrow the ribbon and the timeline | the render is pure; the click is a 3-line delegation to it | **node** — the fixture has one act, so there is no chip to click on the real page. `DASH.loadSampleData()` has no acts either, so a Chrome check would need a fixture that does not exist |
| Hover card on a hit column | `mousemove` | **nothing** |
| Milestone label on a timeline row | DOM text | **nothing** |
| Ribbon geometry: no overflow, hits inside the scroll box, no label past the right edge, no two labels sharing space | layout | **nothing** (Phase 3 probe) |
| A `data-ent` chip opens that entity's own panel | click routing | **nothing** |

The four ribbon invariants and the hover/self-arrow checks are what 4.2 gives
permanent homes in Chrome; `entityRef`, the act-focus render, the slot rule, the
`plot` axis label and the naming contracts are what the node harness gains.


### 4.2 — Put the checks where the repo keeps them

- [x] The node harness used in Phase 1 (44 checks) becomes a permanent fixture,
      not a scratch file. Give it a home and a name that says what it checks.
- [x] The headless-Chrome checks join `tests/test_dashboard.py`, beside the
      existing `_dom` helper and `TestActuallyRenders` — that class already
      drives the dashboard's own JS and asserts on the built DOM, which is
      exactly the shape these need.
- [x] Delete the scratch copies from `~/.hermes/cache/scratch/` once the
      permanent versions are green.

**`tests/dashboard_tabs_harness.js`** — the node harness, named for what it
checks. It loads the **landed** modules (`colors.js`, `utils.js`,
`navigation.js`, `value-graph.js`, `track-data.js`, `panel-tabs.js`, both tabs)
in `JS_ORDER`'s dependency order and runs **63 checks**. Its payload is not a
fixture written for the test: `tests/test_dashboard_tabs.py` builds the repo's
own fixture project and hands it `core.db.get_dashboard_data` output, so a
reader that expects a key the backend stopped emitting fails there rather than
in a browser. The synthetic story survives only where the fixture cannot reach:
the act focus (the fixture has one act) and the fill rule at 1–48 scenes.

**Chrome** — `_probe()` added beside `_dom()`, and the tab checks moved onto it.
`--dump-dom` returns the whole bundle, so a substring assertion over it can be
satisfied by a string literal in the minified JS: `sb-gap` and `jr-row` are
both literals in the tab files, and the fixture's text is in the injected
payload. `_probe` runs the dashboard's own JS, then reads the **live DOM** into
`document.title`. Eight checks added; the two weak tab tests rewritten onto it
(see 4.3).

**Pitfall, measured: `--dump-dom` produces no frames.** A `ResizeObserver`
callback is a rendering-step task, so it is *never* delivered, and
`requestAnimationFrame` never fires either. A probe that waits for the
resize-driven re-render is a flake — the first version of the fold check passed
5 times and failed the 6th, with the pane correctly at 287px and the exchange
still unfolded. The fix is not a longer wait: `test_the_beats_exchange_folds_
into_one_column_when_narrow` narrows the panel **before** activating the tab, so
the tab's first render is the narrow one and no re-render is involved. Verified
6/6 and then 3/3 full runs.

**Deleted** — `~/.hermes/cache/scratch/t34_harness.js`, `ribbon_geom.js`,
`ribbon_chrome_check.py`, `t34_story.json`. Each was checked for a reader
first: nothing in `tests/`, `tools/`, `core/` or `src/` names any of them, and
each has a permanent replacement that is green. The remaining probes
(`ribbon_probe.py`, `ribbon_label.js`, `ribbon_aspect.js`, `ribbon_axis.js`,
`t34_probe.js`, `t34_render.py`) were never carried over and auto-prune in 24h.

### 4.3 — Refactor the tests that the tabs disturbed

Not addition on top — the suite should read as one thing.

- [x] `test_every_class_the_panels_use_exists_in_the_css` (extended in Phase 1)
      now covers the tab files. Confirm it has no allowlist and no skipped
      groups; if a group had to be skipped, say why in a comment or drop it.
- [x] Look for tests that assert the *old* panel shape and now pass only by
      accident. A test that still passes while asserting something the code no
      longer does is worse than no test.

**The class guard has no allowlist and no skipped groups.** It reads the six
files and the assembled CSS, and skips only an attribute group containing `${`
or `(` — a template hole it cannot resolve — which its comment states. No
class is excused.

**Two tests were passing by accident, and were rewritten rather than kept.**
Both `test_the_scene_panel_opens_with_its_beats_tab` and
`test_the_character_panel_opens_with_its_journey_tab` asserted `"sb-exchange" in
dom`, `"sb-gap" in dom`, `"jr-svg" in dom`, `"jr-row" in dom`, `"Kael" in dom`.
Every one of those strings is present in the dumped page whether or not the tab
rendered: they are string literals in the tab files, and `Kael` is in the
injected payload. A tab that rendered nothing would have passed. They are now
split by what they actually prove — the wrap (strip, tab, pane) stays on
`_dom`; the content moved to `_probe`, which counts the built DOM.

**`test_no_bare_inline_handlers_in_index_html` carried a hand-kept copy of
`JS_ORDER`** and had already dropped `panels/panel-tabs.js`,
`panels/scene-beats-tab.js`, `panels/character-journey-tab.js`,
`graph/value-graph.js`, `graph/track-data.js`, `panels/memory-dialog.js` and
`statistics/charts.js` — so the guard could not see a bare handler in any of
them. It now reads `JS_ORDER`, so it covers every file the dashboard loads and
cannot drift again.

### 4.4 — Sweep for legacy and old code

The tabs read `story.scene_beats[]`, `valueModel`, `valueSlice`, `valueAxisSvg`,
`valueChipStyle`, `roleColor`, `relTypeColor`, `plotColor`, `milestoneLabel`,
`renderSectionsHtml`. Check each is still the only path to that fact.

- [x] `core/db.py` still emits `scene.scene_beats` as the **pointer** for the base
      map, and `scene_beats[]` whole for the dashboard. Confirm both readers still
      exist and neither was left half-migrated.
- [x] `core/track.py` `deepest` (the word) — still read by the LLM-facing
      `story_load` view after Phase 2 renamed the JS field. Confirm no reader was
      missed.
- [x] `tools/story_load.py:208-215` builds its own `scene_beats` map for the
      `dramatic_elements` view. That is a separate reader of the same rows —
      confirm it still agrees with what the dashboard now emits, and say so.
- [x] Any panel code the tabs make redundant. Do not delete on suspicion:
      remove only what nothing reads, and name the reader that was checked.

**Nothing was removed.** Each item checked, with the reader named:

| item | readers | verdict |
|---|---|---|
| `scene.scene_beats` pointer | `tools/story_load.py` base map (`acts[].sequences[].scenes[].scene_beats`) | **3 of 3** pointers name a record present in the dashboard payload. Neither reader half-migrated. |
| `scene_beats[]` whole | `core/db.py:983` → `story_data["scene_beats"]`; read only by `track-data.js` `sceneBeatsOf` and the two tabs | whole, with `parent_id` beside `scene`. No second reader of the beats in the JS. |
| `deepest` (the word) | `core/track.py:235`, read by `view="track"` | still the word (`"imprisoned"`, `"deceived"`). The only JS field is `deepestRung`, renamed in Phase 2 and read by `character-journey-tab.js:101`. No reader missed. |
| `dramatic_elements` `scene_beats` map | `tools/story_load.py:211-215` → emitted as the pointer plus `scene_objective` / `turning_point` | agrees with the dashboard on all three fixtures: same pointer, same objective (scene-first, record-fallback in both), same turning point. Pinned by `test_the_llm_view_and_the_dashboard_agree`. |
| `renderSectionsHtml` | `panel-manager.js:11`; called from `entity-panels.js` for every entity's Overview | still the only renderer for entity sections. The Beats tab's `notesHtml` is **not** a duplicate: it filters `[placeholder …]` and wraps in `<details>`, which `renderSectionsHtml` does not. Left alone. |
| panel code the tabs make redundant | `entity-panels.js` has **no** reference to `scene_beats` or beats at all; the scene Overview renders the scene's own sections, the tab renders the record | nothing redundant. No reader to delete. |

**Two inconsistencies were found and fixed at their source**, both cases of two
readers disagreeing about the same rows:

1. **`hasBeats` counted a placeholder record as a beat list.** Two of the
   fixture's three records are empty. The Journey tab's coverage said "beat
   lists exist for 3" while the Beats tab's own empty state said "Beat list
   missing" for two of those scenes. `track-data.js:106` is now
   `!!sb && beats.length > 0`, and `scene-beats-tab.js`'s dot and footer use the
   same notion, so the strip and the pane agree.
2. **The empty state was keyed on the whole pane, not on the beat spine.** A
   scene with value turns but no beats showed its header and said nothing, while
   the strip's dot warned "No beat list yet". `renderSceneBeats` now puts
   `emptyHtml(scene)` exactly where `rhythmHtml + exchangeHtml` would have gone,
   so the header still renders and the missing list is still said.

Both are pinned in the harness.

### 4.5 — Naming verification

The standing rule for this work: after a refactor, names are checked against the
state, not left because they were fine before.

- [x] Every class a tab emits has a rule, and no tab reads another tab's class —
      the Phase 1 guard covers the first; add the second (the journey tab reading
      `.sb-*` out of the beat tab's stylesheet was a real defect found this way).
- [x] Every `data-*` attribute a tab reads is one it emits, or one documented as
      a protocol (`data-ent`, `data-hermes-send`).
- [x] No `var()` reference resolves to an undeclared token. The Phase 1 harness
      checks the two accents; extend it to every custom property the tab CSS uses.

All three are harness checks now. The class check resolves each emitted class
against the dashboard's own CSS **or the tab's own stylesheet** — never another
tab's, which is the defect class Phase 1 found. The `data-*` check reads
`dataset.*`, `closest('[data-…]')` and `querySelector('[data-…]')` and allows
only `ent` and `hermes-send` as protocol keys. The token check resolves every
`var(--x)` in the tab CSS against the assembled CSS, allowing the five the tab
JS sets inline (`--c`, `--lane`, `--n`, `--a`, `--r`) and the two the tab CSS
declares itself (`--ink`, `--ink-s`); **21 tokens used, none undeclared**.

### 4.6 — Verify

- [x] Full suite green.
- [x] The node and Chrome harnesses green from their permanent homes.
- [x] Record in this file what was removed, and what was checked before removing
      it.

```
1191 passed            (was 1179)
tests/dashboard_tabs_harness.js   63 checks, all green
tests/test_dashboard_tabs.py      3 tests
tests/test_dashboard.py           15 Chrome checks in TestActuallyRenders
```

## Phase brief

The tabs now have a permanent test surface, and the sweep found two real
disagreements between readers — both fixed at the concept's source, both pinned.

**Landed:** `tests/dashboard_tabs_harness.js` + `tests/test_dashboard_tabs.py`
(node, 63 checks, real fixture payload) and eight Chrome checks on a new
`_probe` helper that reads the live DOM into `document.title` (the bundle makes
substring assertions meaningless). Two tests that were passing by accident were
rewritten, and `test_no_bare_inline_handlers_in_index_html` stopped carrying a
stale copy of `JS_ORDER`.

**Fixed:** `hasBeats` counted a placeholder record as a beat list, and the Beats
empty state was keyed on the whole pane so a placeholder scene's pane stayed
silent while its strip warned.

**Changed — the decision came back as "we don't want placeholders".** The
Overview rendered an unfilled section's placeholder as content:
`renderSectionsHtml` typeset `[placeholder — scene/Objective]` under a
`panel-section-title` as if the author had written it. Three readers of section
bodies could do it, and two of them each carried their own copy of the filter:

- `renderSectionsHtml` (`panel-manager.js`) — the shared renderer, **no filter at
  all**. This was the defect: all seven Overview callers inherited it.
- `scene-beats-tab.js` `notesHtml` — had its own inline filter, which it has now
  dropped in favour of the shared renderer.
- `entity-panels.js` — reads `__SECTIONS__.scene[slug].Content` directly, so it
  needed the guard too.

`DASH.isPlaceholderSection` is the one predicate, in the sections module
(`panel-manager.js`), so every reader agrees. `renderSectionsHtml` filters on it,
and `entity-panels.js` uses it for the scene Content. Pinned by four Chrome
checks (no placeholder in the scene, plot or sequence Overview; the real sections
survive) and four harness checks.

Two further things fell out of it:

- **`_probe` had a silent ASI trap.** It joined `open_js` and the probe with a
  newline, so a caller whose `open_js` did not end in `;` produced
  `showScenePanel('x')\n(function () {...})()` — one call, on the return value of
  `showScenePanel`. That throws, leaves `document.title` unset, and looks exactly
  like "the probe never ran". The `;` is now added by the helper, so no caller can
  hit it.
- **`notesHtml` no longer duplicates the renderer.** It is a `<details>` wrapper
  around `renderSectionsHtml('scene_beats', sb.id)` — one renderer, one filter.

## Parallel work

None. This phase closes the work.

## Checklist

- [x] Behaviour inventory written, each item assigned to node or Chrome
- [x] Node harness and Chrome checks given permanent homes; scratch copies deleted
- [x] Test suite refactored, not extended — no accidental passers
- [x] Legacy sweep done; removals named with the reader that was checked
- [x] Naming verification done: classes, `data-*`, custom properties
- [x] Full suite green
- [x] Removals recorded here

