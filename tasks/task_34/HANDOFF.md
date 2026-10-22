# Phase 1 → Phase 2/3/4 handoff

**Update — Phase 2 is done.** Everything below still holds; the changes Phase 2
made are listed at the end, so Phase 3 reads that section first.

Written at the end of Phase 1. Everything below was verified against the code and
the running page, not assumed. Where a line number is given it is the **landed**
file (`src/dashboard/...`), which is what later phases edit — the delivered copies
in `tasks/task_34/` are reference artefacts and are now identical to them.

## Where things stand

Phase 1 is complete. The seven delivered files are landed and loaded, the order is
pinned by tests, and the shipping path (`story_dashboard.handler` →
`assemble_dashboard` → the dashboard's own JS) renders both tabs.

```
1179 passed
```

Three defects were found while verifying and fixed at their source (details in
`phase_1_landing.md`): the dashboard payload never carried `scene_objective` on
the scene, the fixture's beat list was an unfilled placeholder, and
`test_milestones_only_trims_the_rows` asserted a three-key contract the code had
outgrown to five.

## The file map

| delivered (`tasks/task_34/`) | landed | role |
|---|---|---|
| `track-data.js` | `src/dashboard/js/graph/track-data.js` | pure data: `sceneBeatsOf`, `entityRef`, `characterTrack`, `trackPlace` |
| `panel-tabs.js` | `src/dashboard/js/panels/panel-tabs.js` | wraps `openPanel`/`closePanel`/`show*Panel`; owns the tab strip |
| `scene-beats-tab.js` | `src/dashboard/js/panels/scene-beats-tab.js` | the scene Beats tab |
| `character-journey-tab.js` | `src/dashboard/js/panels/character-journey-tab.js` | the character Journey tab |
| `panel-tabs.css` | `src/dashboard/css/panel-tabs.css` | `.ptab-*` strip and panes |
| `scene-beats.css` | `src/dashboard/css/scene-beats.css` | `.sb-*` |
| `character-journey.css` | `src/dashboard/css/character-journey.css` | `.jr-*` |

Load order is in `tools/story_dashboard.py` (`CSS_ORDER`, `JS_ORDER`) and is
load-bearing. `tests/test_dashboard.py::TestAssembledOrder` pins the four
dependency pairs plus file existence and no-duplicates.

## Contracts the tabs depend on

**Payload** (`__STORY_DATA__` → `DASH.story`, normalised by `core.js`):
`scene_beats[]` (whole records: `{id, parent_id, scene, driver, scene_objective,
turning_point, beats[], changes[], true_character[]}`), `scenes[]` with
`value_turns[]` and `scene_objective`, `plots[].characters`, `values[]` with
`{name, p, c, cd, nn}`. `D.sceneBeatsOf` resolves a record by `scene` **or**
`parent_id` — the two are allowed to disagree.

**DASH globals the tabs read**, all pre-existing: `valueModel`, `valueSlice`,
`valueAxisSvg`, `valueChipStyle`, `roleColor`, `relTypeColor`, `plotColor`,
`milestoneLabel`, `escapeHtml`, `renderSectionsHtml`. `D.milestoneLabel` was
exported from `value-graph.js` in the commit before this phase; it did not exist
when the tabs were written.

**Registration protocol** (`panel-tabs.js`): a module calls
`D.panelTabs.register(kind, id => [tabs])` and
`D.panelTabs.decorate('showXPanel', kind, args => id)`. A tab is
`{id, label, wide, dot, render(pane, id), redraw, footer(id)}`. Remove both calls
and the panel is exactly what it was.

## Phase 2 targets — all four fixed

All four were still unfixed in the landed files when Phase 2 began. Line numbers
below are the **pre-Phase-2** landed files; the files have since moved, so read
the phase file (`phase_2_naming.md`) for the landed state.

**2.1 `deepest` means two things — fixed.**
`track-data.js` now builds `deepestRung` (an index, `0..3`, or `null`) and
`character-journey-tab.js` reads it. `core/track.py` is untouched and still
emits the word. The scratch harness asserts the type for every path.

**2.2 `is-self` is emitted and unstyled — fixed.** `scene-beats.css` now gives
`.sb-link.is-self` the actor's lane colour and a solid stroke. The arrowhead's
`left` was also wrong for a self-directed arrow (it was drawn at a coordinate the
path never reaches); it is now placed at the turn.

**2.3 the journey ribbon edits the value graph's SVG output — fixed.**
`D.valueAxisSvg(model, geo, plotId, beatLabel)`; the ribbon passes `'plot'`. The
`.replace('>beats</text>', '>plot</text>')` chain is gone. The graph's own two
callers still get `'beats'`.

**2.4 hard-coded entity colours — fixed, differently than briefed.**
`D.entityRef` no longer carries hex literals. **It does not use
`--role-supporting`/`--role-rival`**: those tokens name *roles*, and
`roleColor('supporting')` is the same teal as a location, so using them would
have made a place indistinguishable from a supporting character (and an ally
relationship chip the same teal again). Instead `colors.js` gained
`DASH.ENTITY_KIND_COLORS = { location, world }`, read by `entityRef` **and** by
the hard-coded pips in `views/locations.js` / `views/worlds.js` — which is what
the brief's "confirm the chips match the cards" was really about. Phase 4.4,
which sweeps for legacy, should treat `ENTITY_KIND_COLORS` as the single source
for these two colours.

## What Phase 3 must know

`character-journey-tab.js` changed, so its line numbers from Phase 1 are stale.
Phase 3 edits it for the ribbon width. The things it will meet:

- `deepestRung`, not `deepest`.
- The axis call is now `D.valueAxisSvg(view, geo, null, 'plot')` — the third
  argument is `plotId` (null = story-level milestones) and the fourth is the row
  label. Phase 3 must not reintroduce a string replacement here.
- `MAX_SLOT` and the geometry are **untouched** — the 204px fill finding stands
  exactly as measured.

## What Phase 4 must know

- **The node harness is still a scratch file.** Phase 2 added its assertion
  there, and it is 41 checks now (Phase 1 counted 44 including 3 source-level
  checks run separately). Phase 4.2 gives it a permanent home; the new
  `deepestRung` type assertion and the `>plot</text>` axis assertions are the ones
  to carry over.
- **`ENTITY_KIND_COLORS`** is new and read in three places (`colors.js`,
  `track-data.js`, `views/locations.js`, `views/worlds.js`) — that is the sweep
  item 4.4 is asking about.
- **`--role-supporting` is not a location colour.** Do not "fix" `entityRef` back
  to it.

## Phase 3 — measurement already done

The finding is real and measured, not guessed. On the assembled page at the wide
panel (680px), with the Journey tab open:

```
jrPaneW=647          jrScroll clientW=647 scrollW=647
ribbonW=204          ribbonH=367
```

The ribbon is **204px of a 647px pane — 32%** — and `jr-scroll` does not overflow
(clientW == scrollW), so it simply leaves 443px empty. Cause:
`character-journey-tab.js:24,224` — `MAX_SLOT = 46` caps the per-scene column, and
for a 3-scene story the uncapped slot is already 204px. `value-graph.js:146` has
no such cap (`valueGeometry` lets the slot grow with the width), which is why the
two charts disagree.

Phase 3 task 3.1 wants the rule chosen from a 30+ scene story, not this fixture.
The probe used is described below; reuse it.

## Verification — what actually works

```bash
.venv/bin/python -m pytest -q                       # full suite, ~60s
.venv/bin/python -m pytest tests/test_dashboard.py -q
```

The Chrome checks live in `tests/test_dashboard.py::TestActuallyRenders`, driven by
its `_dom(html, tmp_path, name, drive_js)` helper: it serves the assembled page,
appends `<script>drive_js</script>` before `</body>`, and `--dump-dom`s it. Both
tab checks call the dashboard's own JS (`DASH.showScenePanel(...)`,
`DASH.panelTabs.activate('beats')`) and assert on the **pane content**, not just
the strip.

### Pitfalls that cost real time here

**`--dump-dom` does not run `setTimeout`.** A probe that measures inside
`setTimeout(..., 800)` never fires under `--virtual-time-budget`; the title comes
back empty and it looks like a code failure. Measure **synchronously**.

**The panel width animates.** `#detail-panel` has `transition: width 0.2s`, so a
synchronous read mid-transition returns **0**. Inject
`<style>*{transition:none !important;}</style>` before measuring.

**`mount()` replaces the whole panel body.** Opening a second panel destroys the
first panel's panes, so `.ptab-pane[data-pane="beats"]` is `null` after a
character panel opens. Measure each tab in its own probe, or re-open the first
panel before measuring it.

**`--dump-dom` dumps the whole bundle.** A `grep` over its output matches the
minified vis-network CSS embedded in the page. Write probe output to
`document.title` and extract with a narrow regex, or write the probe to a file and
run it as a script rather than a heredoc.

## Fixture state — read before writing tests

`tests/fixtures/save-the-children/` is the only fixture the dashboard tests use,
and its DB is **built** by `conftest.py`, never committed.

- `scene_beats/Central Room - Day.md` — **real record**: driver, objective,
  turning point, one true-character moment, two changes, two beats (one with a gap).
  This is what makes the Beats tab render content on the assembled page.
- `scene_beats/Central Room - Night.md` and `The Core - Day.md` — **placeholders**
  (`[placeholder — scene/Notes]`). Deliberate: they are the empty state the tab
  must still render. Do not fill them without saying why.
- `tests/test_dashboard.py` has a class guard that reads the three tab JS files and
  asserts every class they emit has a rule in the assembled CSS, with **no
  allowlist**. A rename in `scene-beats.css` or `character-journey.css` that
  misses a class fails there.

## Not done, deliberately

- **The ribbon fill** (Phase 3). Measured, recorded above, untouched — Phase 2
  did not change the geometry or `MAX_SLOT`.
- **Scratch probes** at `~/.hermes/cache/scratch/geo_probe.py` and
  `click_probe.py`. They auto-prune in 24h. Phase 4 task 4.2 is what gives the
  harnesses permanent homes; these were measurement probes, not harnesses.
- **Phases 3 and 4** — untouched. Their briefs are `phase_3_ribbon_fill.md` and
  `phase_4_tests_and_legacy.md`. Phase 2 is complete: `phase_2_naming.md` carries
  what was landed and the two places it deliberately departed from its brief.
- **The delivered copies in `tasks/task_34/`** are synced to the landed files
  again (they were byte-identical at the start of Phase 2 and are again now).
  They remain reference artefacts, not the code that ships — `JS_ORDER` is what
  loads the landed copies.
