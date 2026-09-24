# Story Dashboard Refactor — Plan

## Runtime Constraint (Binding)

`tools/story_dashboard.py` → reads single HTML → string-replaces `screenplay.css` link with inline `<style>` → injects `window.__*__` data before `// ─── Boot` → writes temp `.html` → loads via `file://` in preview pane.

**Implication:** The final artifact is always one HTML file with all CSS and JS inline. Modularity lives in *source*, not runtime.

---

## Architecture: One Coherent Model

### Source Tree

```
src/dashboard/
├── index.html                ← HTML shell only: app structure, nav, view containers, panel skeletons
├── css/
│   ├── base.css              ← reset, tokens, layout shell, sidebar, main, loading/error, scrollbar
│   ├── components.css        ← tags, badges, buttons, detail panels, search bar, entity cards, empty states
│   ├── views.css             ← scenes view, story view, script view, entity-list views, fountain tokens
│   ├── statistics.css        ← stats panel, stat blocks, duration bars, D3 charts, tables, barcode controls
│   └── graph.css             ← graph tabs, arc graph panel, char cards, arc SVG elements, tooltip
└── js/
    ├── core.js               ← state, boot(), normalise(), initStory(), showError()
    ├── colors.js             ← ROLE_COLORS, REL_TYPE_COLORS, PLOT_TYPE_COLORS, roleColor(), relTypeColor(), getRoleKey()
    ├── utils.js              ← escapeHtml(), normalizeLocs(), findLocation(), setEl(), setBar(), fmtDurationShort(), fmtDuration()
    ├── navigation.js         ← switchView(), toggleSidebar(), refreshIndex(), switchGraphTab(), switchStatsGroup()
    ├── data-load.js          ← loadFromFile(), handleFileLoad(), loadSampleData()
    ├── views/
    │   ├── scenes.js         ← buildScenesView(), renderSceneList(), renderSceneItem(), filterScenes()
    │   ├── locations.js      ← buildLocationsView()
    │   ├── plots.js          ← buildPlotsView(), plotScopeBadge()
    │   ├── relationships.js  ← buildRelationshipsView()
    │   ├── worlds.js         ← buildWorldsView()
    │   └── story.js          ← buildStoryView()
    ├── panels/
    │   ├── panel-manager.js  ← openPanel(), closePanel(), renderSectionsHtml(), arcSectionHtml()
    │   └── entity-panels.js  ← showCharacterPanel(), showScenePanel(), showLocationPanel(), showPlotPanel(),
    │                           showRelationshipPanel(), showSequencePanel(), showActPanel(), showWorldPanel()
    ├── graph/
    │   ├── network.js        ← buildGraphView(), resetGraphLayout()
    │   └── arc-graph.js      ← buildCharsGrid(), buildArcGraph(), catmullRomPath(), updateLegend(),
    │                           toggleArcCharMute(), toggleArcSpline(), toggleArcLabels(), arc tooltip handlers
    ├── statistics/
    │   ├── statistics.js     ← openStatsPanel(), closeStatsPanel(), _renderChartsForGroup(), populateStats(),
    │                           populateStructuralStats(), sortTable()
    │   └── charts.js         ← D3 chart fns (_ensureChartRendered, renderDurationChart, renderCharacterChart, renderBarcodeChart)
    └── script-view.js        ← buildScriptView(), _scriptBuilt flag
```

Each module owns a coherent responsibility. **These are starting boundaries** — split a module further when it contains multiple independently changing subsystems or grows substantially beyond its intended responsibility. Do not split merely to hit a line-count target. Line count is a diagnostic signal, not a design constraint.

### Why These Boundaries

| Module | Owns | Why it changes |
|--------|------|----------------|
| `core.js` | Bootstrap, state, data normalization | Data schema changes, boot flow changes |
| `colors.js` | All color maps and lookups | New role types, new rel types, new plot types |
| `utils.js` | Pure helpers (escape, format, DOM lookup) | New formatting needs, edge cases in display |
| `navigation.js` | View switching, sidebar toggle, tab switching | New views, navigation behavior changes |
| `data-load.js` | File load, sample data | Data loading behavior, sample data updates |
| `views/*.js` | List rendering per entity type | Entity display changes |
| `panels/panel-manager.js` | Panel lifecycle, shared rendering | Panel lifecycle changes |
| `panels/entity-panels.js` | Entity-specific panel content | Panel content changes, new entity fields |
| `graph/network.js` | vis-network construction, physics, legend | Graph behavior changes |
| `graph/arc-graph.js` | SVG arc rendering, controls, tooltip | Arc math, visual changes |
| `statistics/statistics.js` | Stats panel lifecycle, stat population, sorting | New stats, structural stats changes |
| `statistics/charts.js` | D3 chart implementations | Chart visual changes |
| `script-view.js` | Screenplay rendering, page breaks, scene click matching | Script view behavior |

### Dependency Direction

```
core.js ──────────┬── data-load.js
colors.js ────────┤
utils.js ─────────┼── navigation.js
                  │    ↓
                  ├── views/*.js
                  ├── panels/*.js
                  ├── graph/*.js
                  ├── statistics/*.js
                  └── script-view.js
```

**Rules:**
- `utils.js` is **dependency-light** — pure functions with no imports from other dashboard modules.
- `colors.js` is independent — pure lookups.
- `core.js` does NOT become a dumping ground. It owns bootstrap + state + normalization. Data loading lives in `data-load.js`. View building lives in `views/*.js`. If core.js grows beyond ~200 lines, stop and split by responsibility.
- `plotScopeBadge()` is a **view/UI helper**, not a generic utility. It lives in `views/plots.js`.

### Global Namespace Model

Each JS file attaches to a single global object to avoid polluting `window`:

```js
// At top of each file
window.DASH = window.DASH || {};
```

Then:
- `DASH.boot()`, `DASH.story`, `DASH.normalise()` in core.js
- `DASH.roleColor()`, `DASH.relTypeColor()` in colors.js
- `DASH.escapeHtml()`, `DASH.findLocation()` in utils.js
- `DASH.switchView()` in navigation.js
- etc.

Functions call each other via `DASH.*`. Inline `onclick` handlers in HTML still work because `DASH` is global.

**Load order** (deterministic, no hoisting surprises):
1. `core.js` (defines `DASH.story`, `DASH.boot`, `DASH.normalise`)
2. `colors.js` (defines color lookups — no dependencies)
3. `utils.js` (defines helpers — pure, no dashboard deps)
4. `navigation.js` (defines view switching — depends on utils.js)
5. `data-load.js` (defines file/sample loading — depends on core.js)
6. `views/scenes.js`, `views/locations.js`, `views/plots.js`, `views/relationships.js`, `views/worlds.js`, `views/story.js`
7. `panels/panel-manager.js` (defines panel lifecycle — depends on utils.js)
8. `panels/entity-panels.js` (defines entity panels — depends on panel-manager, colors, utils)
9. `graph/network.js` (defines vis-network — depends on utils.js, colors.js, panels.js)
10. `graph/arc-graph.js` (defines arc graph — depends on utils.js, colors.js)
11. `statistics/statistics.js` (defines stats panel — depends on utils.js)
12. `statistics/charts.js` (defines D3 charts — depends on utils.js)
13. `script-view.js` (defines script view — depends on utils.js)

### Assembly Function (replaces string-replace in story_dashboard.py)

```python
CSS_ORDER = ["base.css", "components.css", "views.css", "statistics.css", "graph.css"]
JS_ORDER = [
    "core.js", "colors.js", "utils.js", "navigation.js", "data-load.js",
    "views/scenes.js", "views/locations.js", "views/plots.js",
    "views/relationships.js", "views/worlds.js", "views/story.js",
    "panels/panel-manager.js", "panels/entity-panels.js",
    "graph/network.js", "graph/arc-graph.js",
    "statistics/statistics.js", "statistics/charts.js",
    "script-view.js",
]

def assemble_dashboard(dashboard_dir: Path) -> str:
    """Assemble modular dashboard source into final HTML string."""
    html = (dashboard_dir / "index.html").read_text(encoding="utf-8")

    # Inline CSS
    css = "\n".join(
        (dashboard_dir / "css" / f).read_text(encoding="utf-8") for f in CSS_ORDER
    )
    html = html.replace("<!-- CSS_PLACEHOLDER -->", f"<style>\n{css}\n</style>")

    # Inline JS
    js = "\n".join(
        (dashboard_dir / "js" / f).read_text(encoding="utf-8") for f in JS_ORDER
    )
    html = html.replace("<!-- JS_PLACEHOLDER -->", f"<script>\n{js}\n</script>")

    # Inline screenplay.css
    screenplay_css = (dashboard_dir / "screenplay.css").read_text(encoding="utf-8")
    html = html.replace("<!-- SCREENPLAY_CSS_PLACEHOLDER -->", f"<style>\n{screenplay_css}\n</style>")

    return html
```

The existing `_render_dashboard()` then:
```python
def _render_dashboard(data, project_path, project):
    dashboard_dir = Path(__file__).parent.parent / "src" / "dashboard"
    html = assemble_dashboard(dashboard_dir)

    # ... project frontmatter, injections ...
    # Existing data injection logic unchanged
    # Temp file write unchanged
```

### Integration Tests Update

Tests currently do `Path("src/dashboard/story-dashboard.html").read_text()`. After refactor:

- **`test_story_dashboard_integration.py`**: Update fixture to read from `index.html` (checks element IDs). Update function-name tests to read from JS source files. Add test that `assemble_dashboard()` produces valid output with all expected IDs.
- **`test_story_dashboard_stats.py`**: Keep stats computation tests (those test `story_dashboard.py` logic, not the HTML). Update `test_stats_injected_before_boot` to check the assembler output.

New helper fixture:
```python
@pytest.fixture
def dashboard_html():
    from tools.story_dashboard import assemble_dashboard
    from pathlib import Path
    dashboard_dir = Path("src/dashboard")
    return assemble_dashboard(dashboard_dir)
```

### Behavioral Equivalence Verification (per stage)

After each extraction stage, compare the new assembled artifact against the old monolith for:
- All required DOM IDs present
- All external resources loaded (vis-network, js-yaml, D3 CDNs)
- Data injection point preserved (`// ─── Boot` comment present)
- Script order preserved (functions defined before use)
- CSS presence (no missing style blocks)
- Hermes attributes intact (`data-hermes-send` attributes preserved)
- Boot sequence intact (`boot()` called at end of script)
- No unresolved placeholders (`<!-- CSS_PLACEHOLDER -->`, `<!-- JS_PLACEHOLDER -->`, `<!-- SCREENPLAY_CSS_PLACEHOLDER -->`)

Not byte-for-byte identical (whitespace/comments will change) but structurally equivalent.

### Assembly Integrity Tests (new)

```python
def test_assembled_dashboard_contains_no_placeholders(dashboard_html):
    """No unresolved placeholders survive assembly."""
    assert "<!-- CSS_PLACEHOLDER -->" not in dashboard_html
    assert "<!-- JS_PLACEHOLDER -->" not in dashboard_html
    assert "<!-- SCREENPLAY_CSS_PLACEHOLDER -->" not in dashboard_html

def test_assembled_dashboard_contains_required_dom_ids(dashboard_html):
    """All required element IDs present in assembled output."""
    required_ids = [...]  # same list as existing test
    for eid in required_ids:
        assert f'id="{eid}"' in dashboard_html

def test_assembled_dashboard_preserves_external_deps(dashboard_html):
    """vis-network, js-yaml, D3 CDNs loaded."""
    assert "vis-network.min.js" in dashboard_html
    assert "js-yaml.min.js" in dashboard_html
    assert "d3.min.js" in dashboard_html

def test_assembled_dashboard_preserves_data_injection_point(dashboard_html):
    """Boot comment preserved for injection."""
    assert "// ─── Boot" in dashboard_html

def test_assembled_dashboard_preserves_hermes_attributes(dashboard_html):
    """data-hermes-send attributes preserved."""
    assert "data-hermes-send" in dashboard_html

def test_assembled_dashboard_preserves_screenplay_css(dashboard_html):
    """Better Fountain screenplay styles present."""
    assert ".fountain-scene_heading" in dashboard_html
    assert ".fountain-dialogue" in dashboard_html
```

| Test | Change |
|------|--------|
| `test_script_view_exists` | Read from `index.html` — IDs unchanged ✓ |
| `test_stats_panel_exists` | Read from `index.html` — IDs unchanged ✓ |
| `test_stats_panel_width_defined` | Read assembled CSS — token unchanged ✓ |
| `test_script_nav_button_exists` | Read from `index.html` ✓ |
| `test_stats_element_ids_present` | Read from `index.html` — IDs unchanged ✓ |
| `test_build_script_view_function` | Read from `js/script-view.js` |
| `test_open_stats_panel_function` | Read from `js/statistics/statistics.js` |
| `test_d3_charts_functions` | Read from `js/statistics/charts.js` |
| `test_sort_table_function` | Read from `js/statistics/statistics.js` |
| `test_switch_view_wrapper` | Read from `js/navigation.js` |
| `test_scene_click_matching` | Read from `js/script-view.js` |
| `test_no_new_inline_fountain_css` | Read assembled CSS — check no standalone `.fountain-scene_heading` |
| `test_d3_cdn_loaded` | Read from `index.html` ✓ |
| `test_fountain_parse_imported` | Unchanged (tests `story_dashboard.py`) |
| `test_screenplay_stats_computation` | Unchanged |
| `test_stats_injected_before_boot` | Read assembled HTML, check injection before `// ─── Boot` |
| `test_hsl_from_name_deterministic` | Unchanged |

---

## Execution Stages

### Stage 0: Baseline Capture
- Record the existing assembled artifact (the monolith) as baseline
- Capture: all DOM IDs, script tags, CSS blocks, injection points, Hermes attributes
- Use this baseline for comparison in every subsequent stage

### Stage 1: Establish Shell (no behavior change)
- Create directory structure: `src/dashboard/css/`, `src/dashboard/js/`
- Split `index.html` from monolith (extract HTML shell, keep all CSS/JS inline as-is for now)
- Verify: assembled artifact matches baseline (structurally equivalent)

### Stage 2: Extract CSS
- Move CSS sections from inline `<style>` into `css/base.css`, `css/components.css`, `css/views.css`, `css/statistics.css`, `css/graph.css`
- Replace inline `<style>` with `<!-- CSS_PLACEHOLDER -->`
- Update `story_dashboard.py` to assemble CSS from files
- Update tests to read assembled CSS
- Verify: tests pass, visual appearance unchanged

### Stage 3: Extract JS — Foundation
- Move state/boot/normalize → `js/core.js`
- Move color maps → `js/colors.js`
- Move pure helpers → `js/utils.js`
- Move navigation → `js/navigation.js`
- Move data loading → `js/data-load.js`
- Attach each to `window.DASH = window.DASH || {}`
- Update HTML inline `<script>` → `<!-- JS_PLACEHOLDER -->`
- Update `story_dashboard.py` to assemble JS from files in order
- Verify: tests pass, dashboard renders, navigation works

### Stage 4: Extract JS — Views
- Move view builders into `js/views/scenes.js`, `js/views/locations.js`, `js/views/plots.js`, `js/views/relationships.js`, `js/views/worlds.js`, `js/views/story.js`
- Verify: all views render

### Stage 5: Extract JS — Panels
- Move panel lifecycle → `js/panels/panel-manager.js`
- Move entity panels → `js/panels/entity-panels.js`
- Verify: all panels open/close/content

### Stage 6: Extract JS — Graph
- Move vis-network → `js/graph/network.js`
- Move arc graph → `js/graph/arc-graph.js`
- Verify: graph renders, arc graph works

### Stage 7: Extract JS — Statistics
- Move stats panel + population → `js/statistics/statistics.js`
- Move D3 charts → `js/statistics/charts.js`
- Verify: stats panel works, charts draw, sorting works

### Stage 8: Extract Script View
- Move script view → `js/script-view.js`
- Verify: script view renders, scene clicks work

### Stage 9: Cleanup & Validation
- Run full test suite
- Verify no console errors, all views/panels/graphs work
- Final structural comparison against baseline

---

## Key Decisions

| Decision | Choice | Why |
|----------|--------|-----|
| Loading | Classic `<script>` tags, ordered | file:// compatible, no MIME/module issues |
| Namespace | `window.DASH` | Avoids globals pollution, explicit ownership |
| CSS | Source files, inlined at assembly | file:// compatible, source modularity |
| Backend | New `assemble_dashboard()` function | Minimal change to existing runtime model |
| Tests | Fixture calls assembler + reads source JS | Tests the actual artifact, not a phantom |

## What We Do NOT Do

- Do not introduce a build tool, bundler, or npm
- Do not change the data contract (`window.__*__` globals)
- Do not rename CSS classes
- Do not change visual appearance
- Do not refactor algorithms (graph math, arc calculations, D3 charts)
- Do not remove error handling, empty states, or edge cases
- Do not allow core.js to become a dumping ground
- Do not combine unrelated code merely to hit a line-count target
| `test_build_script_view_function` | Read from `js/script-view.js` |
| `test_open_stats_panel_function` | Read from `js/statistics/statistics.js` |
| `test_d3_charts_functions` | Read from `js/statistics/charts.js` |
| `test_sort_table_function` | Read from `js/statistics/statistics.js` |
| `test_switch_view_wrapper` | Read from `js/navigation.js` |
| `test_scene_click_matching` | Read from `js/script-view.js` |
| `test_no_new_inline_fountain_css` | Read assembled CSS — check no standalone `.fountain-scene_heading` |
| `test_d3_cdn_loaded` | Read from `index.html` ✓ |
| `test_fountain_parse_imported` | Unchanged (tests `story_dashboard.py`) |
| `test_screenplay_stats_computation` | Unchanged |
| `test_stats_injected_before_boot` | Read assembled HTML, check injection before `// ─── Boot` |
| `test_hsl_from_name_deterministic` | Unchanged |

---

## Execution Stages

### Stage 0: Baseline Capture
- Record the existing assembled artifact (the monolith) as baseline
- Capture: all DOM IDs, script tags, CSS blocks, injection points, Hermes attributes
- Use this baseline for comparison in every subsequent stage

### Stage 1: Establish Shell (no behavior change)
- Create directory structure: `src/dashboard/css/`, `src/dashboard/js/`
- Split `index.html` from monolith (extract HTML shell, keep all CSS/JS inline as-is for now)
- Verify: assembled artifact matches baseline (structurally equivalent)

### Stage 2: Extract CSS
- Move CSS sections from inline `<style>` into `css/base.css`, `css/components.css`, `css/views.css`, `css/statistics.css`, `css/graph.css`
- Replace inline `<style>` with `<!-- CSS_PLACEHOLDER -->`
- Update `story_dashboard.py` to assemble CSS from files
- Update tests to read assembled CSS
- Verify: tests pass, visual appearance unchanged

### Stage 3: Extract JS — Foundation
- Move state/boot/normalize → `js/core.js`
- Move color maps → `js/colors.js`
- Move pure helpers → `js/utils.js`
- Move navigation → `js/navigation.js`
- Move data loading → `js/data-load.js`
- Attach each to `window.DASH = window.DASH || {}`
- Update HTML inline `<script>` → `<!-- JS_PLACEHOLDER -->`
- Update `story_dashboard.py` to assemble JS from files in order
- Verify: tests pass, dashboard renders, navigation works

### Stage 4: Extract JS — Views
- Move view builders into `js/views/scenes.js`, `js/views/locations.js`, `js/views/plots.js`, `js/views/relationships.js`, `js/views/worlds.js`, `js/views/story.js`
- Verify: all views render

### Stage 5: Extract JS — Panels
- Move panel lifecycle → `js/panels/panel-manager.js`
- Move entity panels → `js/panels/entity-panels.js`
- Verify: all panels open/close/content

### Stage 6: Extract JS — Graph
- Move vis-network → `js/graph/network.js`
- Move arc graph → `js/graph/arc-graph.js`
- Verify: graph renders, arc graph works

### Stage 7: Extract JS — Statistics
- Move stats panel + population → `js/statistics/statistics.js`
- Move D3 charts → `js/statistics/charts.js`
- Verify: stats panel works, charts draw, sorting works

### Stage 8: Extract Script View
- Move script view → `js/script-view.js`
- Verify: script view renders, scene clicks work

### Stage 9: Cleanup & Validation
- Run full test suite
- Verify no console errors, all views/panels/graphs work
- Final structural comparison against baseline

---

## Key Decisions

| Decision | Choice | Why |
|----------|--------|-----|
| Loading | Classic `<script>` tags, ordered | file:// compatible, no MIME/module issues |
| Namespace | `window.DASH` | Avoids globals pollution, explicit ownership |
| CSS | Source files, inlined at assembly | file:// compatible, source modularity |
| Backend | New `assemble_dashboard()` function | Minimal change to existing runtime model |
| Tests | Fixture calls assembler + reads source JS | Tests the actual artifact, not a phantom |

## What We Do NOT Do

- Do not introduce a build tool, bundler, or npm
- Do not change the data contract (`window.__*__` globals)
- Do not rename CSS classes
- Do not change visual appearance
- Do not refactor algorithms (graph math, arc calculations, D3 charts)
- Do not remove error handling, empty states, or edge cases
- Do not allow core.js to become a dumping ground
- Do not combine unrelated code merely to hit a line-count target
