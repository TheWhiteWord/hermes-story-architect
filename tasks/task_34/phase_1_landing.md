# Phase 1 — Land the files

**Goal.** Put the seven delivered files where the dashboard loads them, in the
order they depend on, and prove the order is pinned.

**State on entry.** Phase 1 (verification) is done. The files are correct and
executed for real: 44 node checks, 23 headless-Chrome checks, a geometry probe,
and the full suite at 1172 passed. Nothing is wired yet — `CSS_ORDER`/`JS_ORDER`
do not mention any of them, so the dashboard does not load a single one.

**Where they go.** Mirrors the repo's existing separation (`value-graph.js` +
`value-graph.css` is the precedent): data derivation beside the value model,
tab components beside the panels, one stylesheet per tab.

| delivered (`tasks/task_34/`) | lands at |
|---|---|
| `track-data.js` | `src/dashboard/js/graph/track-data.js` |
| `panel-tabs.js` | `src/dashboard/js/panels/panel-tabs.js` |
| `scene-beats-tab.js` | `src/dashboard/js/panels/scene-beats-tab.js` |
| `character-journey-tab.js` | `src/dashboard/js/panels/character-journey-tab.js` |
| `panel-tabs.css` | `src/dashboard/css/panel-tabs.css` |
| `scene-beats.css` | `src/dashboard/css/scene-beats.css` |
| `character-journey.css` | `src/dashboard/css/character-journey.css` |

## Tasks

### 1.1 — Copy the seven files to their destinations

`cp`, do not retype. The delivered files are the verified artefacts; a retyped
copy is a second thing to drift.

- [x] `track-data.js` → `src/dashboard/js/graph/`
- [x] `panel-tabs.js`, `scene-beats-tab.js`, `character-journey-tab.js` → `src/dashboard/js/panels/`
- [x] `panel-tabs.css`, `scene-beats.css`, `character-journey.css` → `src/dashboard/css/`

Copied byte-for-byte and confirmed with `md5sum` against the delivered copies.

### 1.2 — Wire `CSS_ORDER` (`tools/story_dashboard.py:8`)

Append the three after `value-graph.css`, so the tab styles land last and can
override nothing they should not:

```python
CSS_ORDER = ["base.css", "components.css", "views.css", "statistics.css",
             "graph.css", "value-graph.css",
             "panel-tabs.css", "scene-beats.css", "character-journey.css"]
```

- [x] Edit `CSS_ORDER` as above.

### 1.3 — Wire `JS_ORDER` (`tools/story_dashboard.py:10`)

The order is load-bearing, not cosmetic. Each dependency is a real failure if
reversed:

- `panels/panel-tabs.js` must come **after** `panels/panel-manager.js` (it wraps
  `openPanel`/`closePanel` at load time) and **after** `panels/entity-panels.js`
  (it wraps `show*Panel`).
- `graph/track-data.js` must come **after** `graph/value-graph.js` (it reads
  `D.valueModel`).
- `panels/scene-beats-tab.js` and `panels/character-journey-tab.js` must come
  **after** `panels/panel-tabs.js` (they call `D.panelTabs.register` at load
  time) and after `graph/track-data.js`.

```python
JS_ORDER = [
    "core.js", "colors.js", "utils.js", "navigation.js", "data-load.js",
    "views/scenes.js", "views/locations.js", "views/plots.js",
    "views/relationships.js", "views/worlds.js", "views/story.js",
    "panels/panel-manager.js", "panels/entity-panels.js", "panels/memory-dialog.js",
    "panels/panel-tabs.js",
    "graph/network.js",
    "graph/value-graph.js",
    "graph/track-data.js",
    "panels/scene-beats-tab.js", "panels/character-journey-tab.js",
    "statistics/statistics.js", "statistics/charts.js",
    "script-view.js",
]
```

- [x] Edit `JS_ORDER` as above.

The four pairs are stated in a comment above the list, beside the list that must
satisfy them, because the failure is silent: an unwired wrap renders the panel
exactly as it did before.

### 1.4 — Pin the order so it cannot silently regress

The failure mode is quiet: a reorder leaves the wrap unwired, the tab registers
into nothing, and the panel renders exactly as it did before — no error. A test
that asserts the relative order is the cheapest guard that catches it.

Add to `tests/test_dashboard.py`:

- [x] `test_js_order_satisfies_the_tab_dependencies` — assert the four
      required pairs hold in `JS_ORDER`: `panel-manager.js` before
      `panel-tabs.js`, `entity-panels.js` before `panel-tabs.js`,
      `value-graph.js` before `track-data.js`, `panel-tabs.js` before each tab.
- [x] `test_every_css_file_in_css_order_exists` — a typo'd entry in either order
      raises only when the dashboard is assembled, which is the wrong time to
      find it. Read both lists and check each file is on disk.

Both were added, plus two more from the same finding: `test_every_js_file_in_the_order_exists`
(the script list is the one that actually drifts) and `test_no_file_is_loaded_twice`
(a duplicated entry runs a module twice, which for the wrapping modules is not
idempotent). New class `TestAssembledOrder`.

### 1.5 — Extend the class guard to the new files

`tests/test_dashboard.py:390` `test_every_class_the_panels_use_exists_in_the_css`
reads only `panels/entity-panels.js`, `colors.js`, `statistics/statistics.js`.
It is the guard that catches a renamed class silently un-styling a panel, and it
currently does not see any of the new files.

- [x] Add `panels/panel-tabs.js`, `panels/scene-beats-tab.js`,
      `panels/character-journey-tab.js` to the file list it reads.
- [x] It must pass **without** an allowlist. If a class is genuinely shared
      (`vg-*` from `value-graph.css`, `tag-struct`/`panel-*` from
      `components.css`), the guard already finds them in the assembled CSS. Do
      not add an escape hatch — if it fails, the class is missing.

Passes with no allowlist: 108 class names extracted from the six files, none
missing. `track-data.js` is pure functions and emits no markup, so it is
correctly not in the list.

### 1.6 — Verify end to end on the real assembled page

The node harness and the Chrome harness both read the delivered files directly.
This task proves the *shipping* path — `story_dashboard.handler` →
`assemble_dashboard` → a page that renders both tabs.

- [x] Headless Chrome on the assembled dashboard for a fixture project: assert
      the `.ptab-strip` is present on the scene panel and the character panel,
      and that the Beats and Journey panes render their content.
- [x] Re-run the full suite.

Two checks added to `TestActuallyRenders`, both driving the dashboard's own JS
through the existing `_dom` helper. They assert the pane's **content**, not just
its shell — a strip that opens over an empty pane is exactly the silent failure
this phase exists to catch. Full suite: 1179 passed.

## Defects found while verifying, and fixed where they live

**1. `get_dashboard_data` never emitted `scene_objective` on the scene.** The
Beats tab's header reads `sb.scene_objective`, and the character track reads it
off the scene object; the payload carried the records but not the scene-level
field, so the "drives" header was empty for every scene that had one — silently,
because the record itself was correct. `core/db.py` now emits it on the scene,
from the record, with the same scene-first/record-fallback rule the base
`story_load` map already uses. Pinned by
`test_a_scene_carries_its_records_objective`.

**2. The fixture's beat list was an unfilled placeholder.** All three
`scene_beats/*.md` notes carried only `[placeholder — scene/Notes]`, so the
assembled page could not exercise the exchange at all — the tab rendered its
empty state on the real shipping path. `Central Room - Day.md` now holds a real
record (driver, objective, turning point, a true-character moment, two changes,
two beats with a gap), which is the shape the tab was verified against. The
other two scenes keep their placeholders deliberately: they are the empty state
the tab must still render.

**3. `test_milestones_only_trims_the_rows` asserted a contract the code had
already outgrown.** It required `milestones_only` rows to carry exactly
`{id, milestone, role}`, while `story_load` has emitted `scene_objective` and
`turning_point` there since those fields were added to the view — and its own
schema description says so. It passed only because every fixture scene left both
facts empty. Fixed to the documented five-key contract, and it now asserts both
facts are present, which the three-key version could not do.

## Not done here

**The ribbon fills 32% of the pane** (204px in a 647px pane at the wide panel;
`jr-scroll` clientW == scrollW == 647, so nothing overflows). Measured, not
guessed. That is Phase 3's finding and Phase 3's decision — it needs a 30+ scene
story to choose the rule from, and it edits the same file. Left untouched.

## Parallel work

None. This phase is the trunk every later phase branches from.

## Checklist

- [x] All seven files copied to `src/dashboard/`
- [x] `CSS_ORDER` carries the three stylesheets, last
- [x] `JS_ORDER` carries the four scripts in dependency order
- [x] Order-pinning test added and green
- [x] Class guard extended to the new files and green with no allowlist
- [x] Headless Chrome renders both tabs from the assembled page
- [x] Full suite green — 1179 passed
