# Phase 4: Extract JS — Views

## Goal

Extract the 6 view modules: `scenes.js`, `locations.js`, `plots.js`, `relationships.js`, `worlds.js`, `story.js`. Each owns list rendering for one entity type.

## Baseline Reference

**File:** `tasks/task_24/phase_0/baseline.json` — `functions` key (77 total, including view builders).

After extraction, verify:
- All 6 view files created with correct functions
- Views reference shared utils/panels via `DASH.*`
- Dead code (`buildSequencesView`, `buildActsView`) deleted if not already removed in Phase 3

## Verification Against Code

### Module Boundaries

| File | Functions | Internal Deps |
|------|-----------|---------------|
| `scenes.js` | `buildScenesView`, `renderSceneList`, `renderSceneItem`, `filterScenes` | `escapeHtml`, `renderSceneList`, `renderSceneItem`, `showActPanel`, `showScenePanel`, `showSequencePanel` |
| `locations.js` | `buildLocationsView` | `findLocation`, `showLocationPanel` |
| `plots.js` | `buildPlotsView`, `plotScopeBadge` | `plotScopeBadge`, `showPlotPanel` |
| `relationships.js` | `buildRelationshipsView` | `relTypeColor`, `showRelationshipPanel` |
| `worlds.js` | `buildWorldsView` | `showWorldPanel` |
| `story.js` | `buildStoryView` | `showPlotPanel`, `showScenePanel` |

### Cross-Module Dependencies

| View | Calls Panels | Notes |
|------|--------------|-------|
| `scenes.js` | `showActPanel`, `showScenePanel`, `showSequencePanel` | Via `renderSceneList` |
| `locations.js` | `showLocationPanel` | Direct call |
| `plots.js` | `showPlotPanel` | Direct call |
| `relationships.js` | `showRelationshipPanel` | Direct call |
| `worlds.js` | `showWorldPanel` | Direct call |
| `story.js` | `showScenePanel`, `showPlotPanel` | Direct call |

**Critical:** Views call panels. With classic scripts and ordered load, views can call panel functions defined in later files. Since panels load AFTER views in the load order, this works fine (forward references allowed with classic scripts).

### State Variables

- `DASH.allScenes` → `scenes.js`

### Dead Code

- `buildSequencesView()` → DELETE
- `buildActsView()` → DELETE

## Checklist

- [x] Create `src/dashboard/js/views/` directory
- [x] Create `js/views/scenes.js`:
  - `window.DASH = window.DASH || {};`
  - `DASH.allScenes = [];`
  - `DASH.buildScenesView = function() { ... }`
  - `DASH.renderSceneList = function(scenes) { ... }`
  - `DASH.renderSceneItem = function(s) { ... }`
  - `DASH.filterScenes = function(query) { ... }`
  - Internal calls use `DASH.*`
- [x] Create `js/views/locations.js`:
  - `DASH.buildLocationsView = function() { ... }`
- [x] Create `js/views/plots.js`:
  - `DASH.PLOT_TYPE_COLORS` (already in colors.js — referenced, not redefined)
  - `DASH.plotScopeBadge = function(pl) { ... }`
  - `DASH.buildPlotsView = function() { ... }`
- [x] Create `js/views/relationships.js`:
  - `DASH.buildRelationshipsView = function() { ... }`
- [x] Create `js/views/worlds.js`:
  - `DASH.buildWorldsView = function() { ... }`
- [x] Create `js/views/story.js`:
  - `DASH.buildStoryView = function() { ... }`
- [x] Delete `buildSequencesView` and `buildActsView` from `core.js` — already absent (dead code only in old unused monolith)
- [x] Update `tools/story_dashboard.py`:
  - `JS_ORDER` includes `views/*.js` after `data-load.js`
- [x] Verify: tests pass (25 integration + 11 stats = 36 total), all views render

## Final Brief

**Status:** COMPLETE

**What was done:**
- Extracted 6 view modules from `core.js` (392 lines removed, 1812 remaining)
- Each view file attaches to `window.DASH = window.DASH || {};`
- `DASH.allScenes` state moved to `scenes.js`
- `DASH.PLOT_TYPE_COLORS` referenced from `colors.js` (not redefined in `plots.js`)
- `JS_ORDER` updated: views load after `data-load.js`, before panels
- Test `test_no_bare_inline_handlers_in_index_html` updated to scan view files

**Files changed:**
- `src/dashboard/js/core.js` — view function definitions removed
- `src/dashboard/js/views/scenes.js` — created
- `src/dashboard/js/views/locations.js` — created
- `src/dashboard/js/views/plots.js` — created
- `src/dashboard/js/views/relationships.js` — created
- `src/dashboard/js/views/worlds.js` — created
- `src/dashboard/js/views/story.js` — created
- `tools/story_dashboard.py` — `JS_ORDER` updated
- `tests/test_story_dashboard_integration.py` — scan list updated

**Verification:**
- `assemble_dashboard()` produces valid output, no unresolved placeholders
- All 36 tests pass (25 integration + 11 stats)
- Boot injection point, CDNs, Hermes attributes all preserved
- `initStory()` calls to view builders remain in `core.js` (dispatch to extracted modules via `DASH.*`)

**Notes:**
- Dead code (`buildSequencesView`, `buildActsView`) was already absent from `core.js` — only existed in the old `story-dashboard.html` monolith which is not part of the assembly pipeline

## Issues Found

None. Cross-module panel calls work with ordered classic scripts.

## Dependencies

**Parallel:** None. Phase 4 depends on Phase 3 (foundation).

## Expected Output

After Phase 4:
- 6 view files in `js/views/`
- Views reference panels via `DASH.*`
- Dead code deleted
- All views render correctly

## Next Steps

After Phase 4 approval: Phase 5 (Extract JS — Panels: panel-manager, entity-panels).
