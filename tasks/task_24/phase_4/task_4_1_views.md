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

- [ ] Create `src/dashboard/js/views/` directory
- [ ] Create `js/views/scenes.js`:
  - `window.DASH = window.DASH || {};`
  - `DASH.allScenes = [];`
  - `DASH.buildScenesView = function() { ... }`
  - `DASH.renderSceneList = function(scenes) { ... }`
  - `DASH.renderSceneItem = function(s) { ... }`
  - `DASH.filterScenes = function(query) { ... }`
  - Internal calls use `DASH.*`
- [ ] Create `js/views/locations.js`:
  - `DASH.buildLocationsView = function() { ... }`
- [ ] Create `js/views/plots.js`:
  - `DASH.PLOT_TYPE_COLORS = { ... }`
  - `DASH.plotScopeBadge = function(pl) { ... }`
  - `DASH.buildPlotsView = function() { ... }`
- [ ] Create `js/views/relationships.js`:
  - `DASH.buildRelationshipsView = function() { ... }`
- [ ] Create `js/views/worlds.js`:
  - `DASH.buildWorldsView = function() { ... }`
- [ ] Create `js/views/story.js`:
  - `DASH.buildStoryView = function() { ... }`
- [ ] Delete `buildSequencesView` and `buildActsView` from `core.js`
- [ ] Update `tools/story_dashboard.py`:
  - `JS_ORDER` includes `views/*.js` after `data-load.js`
- [ ] Verify: tests pass, all views render

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
