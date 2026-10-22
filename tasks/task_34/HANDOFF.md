# Phase 1 → Phase 2/3/4 handoff

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

## Phase 2 targets — verified present, with locations

All four are still unfixed in the landed files. Line numbers are the landed files.

**2.1 `deepest` means two things.**
`src/dashboard/js/graph/track-data.js:121` builds it as a **rung index** (`0..3`);
`src/dashboard/js/panels/character-journey-tab.js:101` renders it as `RUNG[p.deepest]`.
`core/track.py:204-227` builds the LLM-facing `deepest` as the **word** and must be
left alone. Rename the JS field to `deepestRung` in both files.

**2.2 `is-self` is emitted and unstyled.**
`src/dashboard/js/panels/scene-beats-tab.js:91`. No `.sb-link.is-self` rule exists
in `scene-beats.css`. Give it a rule or delete the class and the `same` ternary —
do not leave it dangling.

**2.3 the journey ribbon edits the value graph's SVG output.**
`src/dashboard/js/panels/character-journey-tab.js:132` string-replaces
`'>beats</text>'` with `'>plot</text>'`. `src/dashboard/js/graph/value-graph.js:168`
is `D.valueAxisSvg(model, geo, plotId)`; the label is written at `:171`
(`rowLabel('beats', 50)`). Add a `beatLabel` parameter defaulting to `'beats'`,
pass `'plot'` from the journey tab, delete the `.replace()` chain. The value
graph's own two callers (`:499`, `:518`) pass nothing.

**2.4 hard-coded entity colours.**
`src/dashboard/js/graph/track-data.js:43,45` hard-code `#6bbfb0` (location) and
`#e0a86b` (world). The character branch already goes through `D.roleColor`. Note
these are the same values as `--role-supporting` / `--role-rival` and as
`PLOT_TYPE_COLORS.Setup` / `.Complicating` — pick the token, don't add a new one.

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

- **The ribbon fill** (Phase 3). Measured, recorded above, untouched.
- **Scratch probes** at `~/.hermes/cache/scratch/geo_probe.py` and
  `click_probe.py`. They auto-prune in 24h. Phase 4 task 4.2 is what gives the
  harnesses permanent homes; these were measurement probes, not harnesses.
- **Phases 2, 3, 4** — untouched. Their briefs are `phase_2_naming.md`,
  `phase_3_ribbon_fill.md`, `phase_4_tests_and_legacy.md`.
