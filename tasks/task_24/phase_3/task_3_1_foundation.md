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

- [ ] Create `src/dashboard/js/` directory
- [ ] Create `js/core.js`:
  - Add `window.DASH = window.DASH || {};` at top
  - Move `DASH.story`, `DASH.network` state vars
  - Move `DASH.boot`, `DASH.showError`, `DASH.normalise`, `DASH.initStory`
  - `initStory()` calls `DASH.buildGraphView()`, etc.
  - Keep boot comment injection point
- [ ] Create `js/colors.js`:
  - Add `window.DASH = window.DASH || {};`
  - Move `DASH.ROLE_COLORS`, `DASH.REL_TYPE_COLORS`, `DASH.PLOT_TYPE_COLORS`
  - Move `DASH.roleColor`, `DASH.getRoleKey`, `DASH.relTypeColor`
- [ ] Create `js/utils.js`:
  - Add `window.DASH = window.DASH || {};`
  - Move `DASH.normalizeLocs`, `DASH.findLocation`, `DASH.escapeHtml`, `DASH.fmtDurationShort`, `DASH.fmtDuration`, `DASH.setEl`, `DASH.setBar`
- [ ] Create `js/navigation.js`:
  - Add `window.DASH = window.DASH || {};`
  - Move `DASH.sidebarExpanded`, `DASH.currentView`, `DASH._origSwitchView`
  - Move `DASH.switchView`, `DASH.toggleSidebar`, `DASH.refreshIndex`, `DASH.switchGraphTab`, `DASH.switchStatsGroup`
  - Include the `switchView` wrapper
- [ ] Create `js/data-load.js`:
  - Add `window.DASH = window.DASH || {};`
  - Move `DASH.loadFromFile`, `DASH.handleFileLoad`, `DASH.loadSampleData`
- [ ] Update `tools/story_dashboard.py`:
  - Read JS files in `JS_ORDER`
  - Concatenate into one `<script>` block
  - Replace `<!-- JS_PLACEHOLDER -->` with inline `<script>`
- [ ] Update tests:
  - `test_switch_view_wrapper` → reads `js/navigation.js`
  - `test_build_script_view_function` → reads `js/script-view.js` (not yet extracted, skip for now)
- [ ] Verify: tests pass, dashboard renders, navigation works

## Issues Found

None. Dependency verification confirms the planned boundaries are clean.

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
