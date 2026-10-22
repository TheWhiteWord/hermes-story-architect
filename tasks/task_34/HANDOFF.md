# Phase 1 → Phase 2/3/4 handoff

**Update — Phase 4 is done. The work is closed.** Read the "Phase 4 — done"
section first; everything below is history and is kept because later phases
edited the files it describes.

Written at the end of Phase 1. Everything below was verified against the code and
the running page, not assumed. Where a line number is given it is the **landed**
file (`src/dashboard/...`), which is what later phases edit — the delivered copies
in `tasks/task_34/` are reference artefacts and are now identical to them.

## Phase 4 — done

``` 
1191 passed
tests/dashboard_tabs_harness.js   63 node checks
tests/test_dashboard_tabs.py      3 tests
tests/test_dashboard.py           15 Chrome checks in TestActuallyRenders
```

**The harnesses are permanent and read the LANDED files.**
`tests/dashboard_tabs_harness.js` + `tests/test_dashboard_tabs.py` (node, 63
checks) take their payload from `core.db.get_dashboard_data` on the repo's own
fixture — no synthetic story, except where the fixture cannot reach (the act
focus, and the fill rule at 1–48 scenes). `tests/test_dashboard.py` gained
`_probe()`, which reads the **live DOM** into `document.title`, synchronously.

**`--dump-dom` produces no frames.** A `ResizeObserver` callback is never
delivered and `requestAnimationFrame` never fires, so a probe that waits for a
resize-driven re-render is a flake — the first fold check passed 5 runs and
failed the 6th with the pane correctly narrow. Anything that needs a different
width must arrange it *before* the tab renders: the fold check narrows the panel
first, then activates the tab.

**`--dump-dom` makes substring assertions meaningless.** The dumped page includes
the whole minified bundle and the injected payload, so `"sb-gap" in dom`,
`"jr-row" in dom` and `"Kael" in dom` are all true whether or not the tab
rendered. The two Phase 1 Chrome tab tests asserted exactly those, and would have
passed against an empty pane. Anything asserting on rendered content must go
through `_probe`.

**Two cross-reader defects were found and fixed at the source:**

1. `hasBeats` counted a placeholder record as a beat list, so the Journey tab
   said "beat lists exist for 3" while the Beats tab said "Beat list missing" for
   two of those scenes. `track-data.js` now requires `beats.length`; the dot and
   footer in `scene-beats-tab.js` use the same notion.
2. The Beats empty state was keyed on the whole pane, so a placeholder scene with
   value turns showed its header and said nothing while the strip's dot warned.
   `renderSceneBeats` now puts `emptyHtml(scene)` exactly where the beat spine
   would have gone.

**`test_no_bare_inline_handlers_in_index_html` carried a hand-kept copy of
`JS_ORDER`** and had already dropped the four tab/value files. It reads `JS_ORDER`
now.

**Changed: placeholders are not content.** `DASH.isPlaceholderSection` (in
`panel-manager.js`) is the one predicate; `renderSectionsHtml` and the scene
Content reader in `entity-panels.js` both use it, and the Beats tab's `notesHtml`
delegates to the renderer instead of keeping its own copy. Four Chrome checks pin
it, and `_probe` now terminates `open_js` itself — a caller without a trailing
`;` used to produce `showScenePanel('x')(function () {...})()` and a title that
never got set.

**Scratch deleted:** `t34_harness.js`, `ribbon_geom.js`, `ribbon_chrome_check.py`,
`t34_story.json`. The remaining probes were never carried over.

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

## What Phase 3 needed to know (now historical)

`character-journey-tab.js` changed in Phase 2, so its Phase 1 line numbers were
stale. Phase 3 edited it for the ribbon width and the things it met:

- `deepestRung`, not `deepest`.
- The axis call is `D.valueAxisSvg(view, geo, null, 'plot')` — the third
  argument is `plotId` (null = story-level milestones) and the fourth is the row
  label. It must not reintroduce a string replacement here.
- `MAX_SLOT` and the geometry were untouched by Phase 2 — the 204px fill finding
  stood exactly as measured.

## Phase 3 — done, and the premise it was written from is discharged

The finding was real and measured, not guessed. On the assembled page at the wide
panel (680px), with the Journey tab open:

```
jrPaneW=647          jrScroll clientW=647 scrollW=647
ribbonW=204          ribbonH=367
```

The ribbon was **204px of a 647px pane — 32%** — and `jr-scroll` did not overflow
(clientW == scrollW), so it simply left 443px empty. Cause:
`character-journey-tab.js:24,224` — `MAX_SLOT = 46` capped the per-scene column,
and for a 3-scene story the uncapped slot was already 204px.

**3.1 asked for a 30+ scene measurement before touching the constant, and it
settled the question.** The cap binds only while the uncapped slot still exceeds
46px — `n ≤ 12` at 680px, `n ≤ 7` at 320px. From 20 scenes up the uncapped slot
is already *below* the cap, so `MAX_SLOT` is inert there. It was never a
readability guard; it only ever bit short stories, exactly where the fill was
worst. The widest mark the ribbon draws per scene is the drives ring at 10.6px
across (r 4.3 + a 2px stroke), so a wide column cannot make a marker unreadable
— it only makes it small relative to its column.

**Landed:** `MAX_SLOT` is gone, and the `Math.max(280, …)` floor on `W` with it
(a second arbitrary constant that never bound — the pane is 647px wide and 287px
narrowed). The slot is now `max(MIN_SLOT, (W - LABEL_W - PAD_R) / n)`. The ribbon
fills the pane; when `MIN_SLOT` binds it exceeds the pane and `.jr-scroll`
scrolls it, which is what that container is for. The act-focus chips remain the
zoom for a short story.

Before/after on the assembled page:

```
                    BEFORE                    AFTER
default   pane 647  ribbon 204  32%           ribbon 647  100%
narrow    pane 287  ribbon 204  71%           ribbon 287  100%
                    slot 46 (capped)          slot 193.8 / 86.0
```

**3.3's answer:** the ribbon and the value graph now share the axis and the
*form* of the slot rule (fill, floor, scroll) — the one real disagreement, one
capped and one not, is gone. They differ in the floor values (1.5px vs 12px, and
a 360px `W` floor the ribbon does not have) because the containers differ: a
360px floor would make a 3-scene story at the *default* panel 360px wide and
overflow it. That is the clipping 3.2 exists to prevent, so the difference is
deliberate.

**Corrected:** the phase cited `value-graph.js:142` for the slot rule. It is
`value-graph.js:149` (`valueGeometry`); line 142 is inside `valueLabelWidth`.
The finding itself was right and reproduced.

**Verification was DOM assertions, not screenshots** — the vision tool was down.
The probe drives the dashboard's own JS and reads the width the panel actually
rendered; the overlap check is computed from the built DOM. Both probes are
still scratch files at `~/.hermes/cache/scratch/ribbon_geom.js` and
`ribbon_chrome_check.py`; Phase 4.2 gives them permanent homes.

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
- **The ribbon's geometry is now `max(MIN_SLOT, (W - LABEL_W - PAD_R) / n)`.**
  `MAX_SLOT` and the `280` floor are deleted, so 4.4 should not "restore" them:
  the fill rule is the deliberate outcome of Phase 3, measured at 1–48 scenes.
  The constants that survive are `LABEL_W = 58` (= `GEO.minLabelW` in
  `value-graph.js`), `PAD_R = 8`, `MIN_SLOT = 12`.
- **Two new scratch probes** worth giving permanent homes in 4.2:
  `~/.hermes/cache/scratch/ribbon_geom.js` (node; reports the fill share for any
  scene count) and `~/.hermes/cache/scratch/ribbon_chrome_check.py` (Chrome; the
  four journey DOM invariants).

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

## Phase 3's probe, and its pitfalls

Phase 3 measured with two probes, both still scratch:
`~/.hermes/cache/scratch/ribbon_geom.js` (node, reads the landed modules, reports
the width the panel itself rendered for any scene count) and
`~/.hermes/cache/scratch/ribbon_chrome_check.py` (Chrome, drives the assembled
page and asserts on the built DOM). Phase 4.2 gives them homes.

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

**A probe's own bug reads like a code failure.** Phase 3 hit two: the probe
constant was defined but never concatenated into the drive string, and the
node harness recomputed the old formula instead of reading the rendered
`width` attribute — so it reported the *pre-fix* numbers after the fix landed.
Read the width the panel rendered, never a copy of the rule.

**The panel's default state is WIDE.** `panel-tabs.js` initialises
`memory = { tab: {}, wide: true }`, and a tab marked `wide: true` calls
`setWide(true)` on open — so the Journey tab opens at 680px and the widen button
*narrows* it. A probe that assumes "click widen → wider" measures the opposite.

**A `.ptab-pane` is `display:none` until active.** Querying it before
`DASH.panelTabs.activate(...)` gives `clientWidth = 0` and no children, which
looks like a rendering failure.

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

- **Nothing.** Phase 4 closed the work: the harnesses have permanent homes, the
  scratch copies are deleted, and the two defects the sweep found are fixed. The
  one open item is a decision, not work — see "Found, not changed" above.
- **The delivered copies in `tasks/task_34/`** are synced to the landed files
  again (byte-identical, re-verified after the Phase 3 edit). They remain
  reference artefacts, not the code that ships — `JS_ORDER` is what loads the
  landed copies.
