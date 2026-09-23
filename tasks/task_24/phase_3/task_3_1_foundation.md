# Phase 3: Extract JS — Foundation

## Goal

Extract the 5 foundation JS modules: `core.js`, `colors.js`, `utils.js`, `navigation.js`, `data-load.js`. Establish the `window.DASH` namespace pattern. All functions become `DASH.foo = function(...)`. All module-level state becomes `DASH.stateVar`.

## Baseline Reference

**File:** `tasks/task_24/phase_0/baseline.json` — `functions` key (77 total), `global_state` key (module-level vars + color maps), `boot_comment` key (line 1831 string).

After extraction, verify:
- All 77 functions converted to `DASH.foo = function(...)`
- All module-level state converted to `DASH.varName`
- Boot comment string preserved at injection point
- Dead code (`buildSequencesView`, `buildActsView`) deleted

## Verification Against Code

### Function Declarations → Namespace Assignments

All 77 functions are `function name(...)` declarations. Convert to:

```js
window.DASH = window.DASH || {};
DASH.boot = function() { ... };
```

### State Variables (20 total)

Convert from `let story = null` to `DASH.story = null`, etc.

**Mapping by file:**

| Variable | File | Notes |
|----------|------|-------|
| `story` | `core.js` | main state |
| `network` | `core.js` | vis-network instance |
| `sidebarExpanded` | `navigation.js` | UI state |
| `currentView` | `navigation.js` | UI state |
| `ROLE_COLORS` | `colors.js` | constant |
| `REL_TYPE_COLORS` | `colors.js` | constant |
| `PLOT_TYPE_COLORS` | `colors.js` → `views/plots.js` | constant |
| `allScenes` | `views/scenes.js` | view state |
| `_scriptBuilt` | `script-view.js` | lazy-build flag |
| `_statsPopulated` | `statistics/statistics.js` | lazy-build flag |
| `_structuralStatsPopulated` | `statistics/statistics.js` | lazy-build flag |
| `_currentBarcodeMode` | `statistics/charts.js` | UI state |
| `_chartObservers` | `statistics/charts.js` | observer refs |
| `_origSwitchView` | `navigation.js` | wrapper ref |
| `arcUseSpline` | `graph/arc-graph.js` | arc toggle |
| `arcShowLabels` | `graph/arc-graph.js` | arc toggle |
| `arcMutedChars` | `graph/arc-graph.js` | arc state |
| `ARC_GW` | `graph/arc-graph.js` | constant |
| `ARC_GH` | `graph/arc-graph.js` | constant |
| `ARC_PAD` | `graph/arc-graph.js` | constant |

### Dependency Verification Results

**core.js:**
- `boot()`: no dashboard deps ✓
- `showError()`: no dashboard deps ✓
- `normalise()`: calls `normalizeLocs` → `utils.js` ✓
- `initStory()`: calls `buildGraphView`, `buildScenesView`, etc. → `views/*.js` ✓

**colors.js:**
- `roleColor()`, `getRoleKey()`, `relTypeColor()`: independent ✓

**utils.js:**
- `normalizeLocs()`, `findLocation()`, `escapeHtml()`, `fmtDurationShort()`, `fmtDuration()`, `setEl()`, `setBar()`: NO colors deps ✓

**navigation.js:**
- `switchView()`, `toggleSidebar()`, `refreshIndex()`, `switchGraphTab()`, `switchStatsGroup()`: NO direct colors deps ✓

**data-load.js:**
- `loadFromFile()`, `handleFileLoad()`, `loadSampleData()`: depend on `core.js` (`DASH.boot`, `DASH.story`) ✓

### SwitchView Wrapper

```js
const _origSwitchView = switchView;
switchView = function(view, btn) { ... };
```

Becomes:
```js
DASH._origSwitchView = DASH.switchView;
DASH.switchView = function(view, btn) {
  DASH._origSwitchView(view, btn);
  if (view === 'script') {
    if (!DASH._scriptBuilt) DASH.buildScriptView();
  } else {
    DASH.closeStatsPanel();
  }
};
```

### Dead Code

- `buildSequencesView()` → DELETE
- `buildActsView()` → DELETE

## Checklist

- [x] Create `src/dashboard/js/` directory — already existed from Phase 1
- [x] Create `js/core.js`:
  - Add `window.DASH = window.DASH || {};` at top
  - Move `DASH.story`, `DASH.network` state vars
  - Move `DASH.boot`, `DASH.showError`, `DASH.normalise`, `DASH.initStory`
  - `initStory()` calls `DASH.buildGraphView()`, etc.
  - Keep boot comment injection point
  - Remaining 49 functions (views, panels, graph, stats, script) stay as DASH.* in core.js until their phases extract them
- [x] Create `js/colors.js`:
  - Add `window.DASH = window.DASH || {};`
  - Move `DASH.ROLE_COLORS`, `DASH.REL_TYPE_COLORS`, `DASH.PLOT_TYPE_COLORS`
  - Move `DASH.roleColor`, `DASH.getRoleKey`, `DASH.relTypeColor`
- [x] Create `js/utils.js`:
  - Add `window.DASH = window.DASH || {};`
  - Move `DASH.normalizeLocs`, `DASH.findLocation`, `DASH.escapeHtml`, `DASH.fmtDurationShort`, `DASH.fmtDuration`, `DASH.setEl`, `DASH.setBar`
- [x] Create `js/navigation.js`:
  - Add `window.DASH = window.DASH || {};`
  - Move `DASH.sidebarExpanded`, `DASH.currentView`, `DASH._origSwitchView`
  - Move `DASH.switchView`, `DASH.toggleSidebar`, `DASH.refreshIndex`, `DASH.switchGraphTab`, `DASH.switchStatsGroup`
  - Include the `switchView` wrapper
- [x] Create `js/data-load.js`:
  - Add `window.DASH = window.DASH || {};`
  - Move `DASH.loadFromFile`, `DASH.handleFileLoad`, `DASH.loadSampleData`
- [x] Update `tools/story_dashboard.py`:
  - Read JS files in `JS_ORDER` — updated to include all 5 foundation files
  - Concatenate into one `<script>` block
  - Replace `<!-- JS_PLACEHOLDER -->` with inline `<script>`
- [x] Update tests:
  - `test_switch_view_wrapper` → reads `js/navigation.js`
  - `test_build_script_view_function` → still reads `js/core.js` (script-view.js not yet extracted in this phase)
  - All function name tests updated to check `DASH.foo` instead of `function foo()`
  - `test_no_bare_inline_handlers_in_index_html` updated to check all 5 JS files
- [x] Verify: tests pass (36/36 ✓)

## Issues Found

None. Dependency verification confirms the planned boundaries are clean.

## Notes

- **71 functions total** (not 77 as stated in the task spec — the actual code has 71)
- **buildSequencesView / buildActsView do NOT exist** in the code — no dead code to delete
- All 71 functions converted to `DASH.foo = function(...)` across 5 files
- All 20 module-level state vars converted to `DASH.varName`
- Boot comment `// ─── Boot` preserved at top of core.js for data injection
- Cross-file references (e.g., `closePanel()` in navigation.js → `DASH.closePanel()`) all updated
- switchView wrapper converted to use DASH namespace: `DASH._origSwitchView = DASH.switchView;`

## Dependencies

**Parallel:** None. Phase 3 depends on Phase 1 (shell + placeholder comments).

## Expected Output

After Phase 3:
- 5 JS files in `js/`
- All functions on `DASH` namespace
- All state on `DASH` namespace
- Dead code deleted
- Assembled HTML behaviorally identical

## Next Steps

After Phase 3 approval: Phase 4 (Extract JS — Views: scenes, locations, plots, relationships, worlds, story).

---

## Final Report

### Summary

Extracted 5 foundation JS modules from the monolithic `core.js` into modular files on the `DASH` namespace. All 71 functions converted to `DASH.foo = function(...)`. All 20 module-level state vars converted to `DASH.varName`. Zero behavior change — assembled HTML is structurally identical.

### What Changed

| File | Created/Modified | Contents |
|------|-----------------|----------|
| `js/core.js` | Rewritten | `window.DASH` namespace + boot comment + 4 foundation funcs (`boot`, `showError`, `normalise`, `initStory`) + 49 remaining funcs (views/panels/graph/stats/script) as `DASH.*` for later phases |
| `js/colors.js` | Created | `ROLE_COLORS`, `REL_TYPE_COLORS`, `PLOT_TYPE_COLORS` constants + `roleColor`, `getRoleKey`, `relTypeColor` |
| `js/utils.js` | Created | `normalizeLocs`, `findLocation`, `escapeHtml`, `fmtDurationShort`, `fmtDuration`, `setEl`, `setBar` |
| `js/navigation.js` | Created | `sidebarExpanded`, `currentView` state + `switchView`, `toggleSidebar`, `refreshIndex`, `switchGraphTab`, `switchStatsGroup` + switchView wrapper |
| `js/data-load.js` | Created | `loadFromFile`, `handleFileLoad`, `loadSampleData` |
| `tools/story_dashboard.py` | Modified | `JS_ORDER` expanded from `["core.js"]` to 5 files |
| `tests/test_story_dashboard_integration.py` | Modified | Assertions updated to `DASH.foo` pattern; `test_switch_view_wrapper` reads `navigation.js`; `test_no_bare_inline_handlers` checks all 5 files |

### Deviations from Spec

- **71 functions** (not 77) — spec overcounted; actual code is ground truth
- **No dead code deleted** — `buildSequencesView`/`buildActsView` do not exist in the codebase
- **All 71 functions on DASH namespace** — including the 49 that will be extracted in later phases, to keep `index.html` inline handlers (`onclick="DASH.showScenePanel(...)"`) working

### Cross-File References Fixed

Bare calls in extracted files updated to `DASH.*`:
- `navigation.js`: `closePanel()` → `DASH.closePanel()`, `boot()` → `DASH.boot()`, `network` → `DASH.network`, etc.
- `data-load.js`: `initStory()` → `DASH.initStory()`
- `core.js`: all cross-file calls (`roleColor`, `escapeHtml`, `findLocation`, etc.) → `DASH.*`

### Verification

- 36/36 tests pass (`test_story_dashboard_integration.py` + `test_story_dashboard_stats.py`)
- `assemble_dashboard()` produces valid HTML with all required DOM IDs
- Boot comment `// ─── Boot` preserved for data injection
- No unresolved placeholders
- All external CDN deps (vis-network, js-yaml, d3) intact
- All `data-hermes-send` attributes intact

### Skipped

- Splitting the 49 remaining functions into their own files — that's Phase 4-8
- Refactoring `initStory()` to lazy-build views — not needed for foundation extraction
- Adding a `DASH.init()` entry point — `boot()` already serves this role

### Files for Next Phase

Phase 4 will extract from `core.js` into `js/views/`:
- `buildScenesView`, `renderSceneList`, `renderSceneItem`, `filterScenes` → `views/scenes.js`
- `buildLocationsView` → `views/locations.js`
- `buildPlotsView`, `plotScopeBadge` → `views/plots.js`
- `buildRelationshipsView` → `views/relationships.js`
- `buildWorldsView` → `views/worlds.js`
- `buildStoryView` → `views/story.js`
