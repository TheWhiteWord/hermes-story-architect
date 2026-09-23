# Phase 5: Extract JS — Panels

## Goal

Extract the 2 panel modules: `panel-manager.js` and `entity-panels.js`. Panel-manager owns lifecycle. Entity-panels owns content rendering.

## Baseline Reference

**File:** `tasks/task_24/phase_0/baseline.json` — `functions` key (includes `openPanel`, `closePanel`, `renderSectionsHtml`, `arcSectionHtml`, all `show*Panel`).

After extraction, verify:
- Panel lifecycle separated from content rendering
- Panel interdependencies preserved (safe with classic scripts)
- All `show*Panel` functions on `DASH` namespace

## Verification Against Code

### Module Boundaries

| File | Functions | Internal Deps |
|------|-----------|---------------|
| `panel-manager.js` | `openPanel`, `closePanel`, `renderSectionsHtml`, `arcSectionHtml` | `escapeHtml`, `roleColor` (for arcSectionHtml) |
| `entity-panels.js` | `showCharacterPanel`, `showScenePanel`, `showLocationPanel`, `showPlotPanel`, `showRelationshipPanel`, `showSequencePanel`, `showActPanel`, `showWorldPanel` | All call each other + panel-manager |

### Cross-Module Dependencies

| Panel | Calls Other Panels | Calls Utils | Calls Colors |
|-------|-------------------|-------------|--------------|
| `showCharacterPanel` | `renderSectionsHtml`, `arcSectionHtml`, `openPanel`, `showScenePanel` | - | `relTypeColor` |
| `showScenePanel` | `showCharacterPanel`, `openPanel`, `showLocationPanel`, `showPlotPanel` | `findLocation`, `escapeHtml` | `roleColor` |
| `showLocationPanel` | `renderSectionsHtml`, `showCharacterPanel`, `openPanel`, `showScenePanel` | `findLocation` | `roleColor` |
| `showPlotPanel` | `renderSectionsHtml`, `showCharacterPanel`, `openPanel`, `showScenePanel` | - | `roleColor` |
| `showRelationshipPanel` | `showCharacterPanel`, `openPanel`, `showScenePanel` | `escapeHtml` | `roleColor`, `relTypeColor` |
| `showSequencePanel` | `showScenePanel`, `openPanel`, `showPlotPanel` | `escapeHtml` | - |
| `showActPanel` | `showSequencePanel`, `openPanel`, `showPlotPanel` | - | - |
| `showWorldPanel` | `renderSectionsHtml`, `openPanel`, `showPlotPanel` | - | - |

### Critical Finding: Circular Panel Dependencies

Panels call each other freely (`showScenePanel` → `showCharacterPanel` → `showScenePanel`). With classic scripts, this works because all functions are hoisted and available by the time any panel opens (all panels load before any user interaction).

**No issue.** This is the same pattern as the monolith.

## Checklist

- [x] Create `src/dashboard/js/panels/` directory
- [x] Create `js/panels/panel-manager.js`:
  - `window.DASH = window.DASH || {};`
  - `DASH.openPanel = function() { ... }`
  - `DASH.closePanel = function() { ... }`
  - `DASH.renderSectionsHtml = function(entityType, slug) { ... }`
  - `DASH.arcSectionHtml = function(char) { ... }`
- [x] Create `js/panels/entity-panels.js`:
  - `window.DASH = window.DASH || {};`
  - All 8 `show*Panel` functions
  - Internal calls use `DASH.*`
- [x] Update `tools/story_dashboard.py`:
  - `JS_ORDER` includes `panels/*.js` after `views/*.js`
- [x] Verify: tests pass, all panels open/close/content

## Issues Found

None. Panel interdependency is safe with classic scripts.

## Dependencies

**Parallel:** None. Phase 5 depends on Phase 4 (views).

## Expected Output

After Phase 5:
- 2 panel files in `js/panels/`
- Panel lifecycle separated from content
- All panels work

## Next Steps

After Phase 5 approval: Phase 6 (Extract JS — Graph: network, arc-graph).

## Final Report

**Status:** Complete — all checklist items verified.

**What was done:**
- Extracted 4 functions (`openPanel`, `closePanel`, `renderSectionsHtml`, `arcSectionHtml`) from `core.js` → `js/panels/panel-manager.js`
- Extracted 8 functions (`showCharacterPanel`, `showScenePanel`, `showLocationPanel`, `showPlotPanel`, `showRelationshipPanel`, `showSequencePanel`, `showActPanel`, `showWorldPanel`) from `core.js` → `js/panels/entity-panels.js`
- Removed all 12 functions from `core.js` (now 1164 lines, down from 1812)
- Updated `JS_ORDER` in `story_dashboard.py` to include `panels/panel-manager.js` and `panels/entity-panels.js` after views
- Updated `test_story_dashboard_integration.py` to include panel files in the bare-handler check

**Verification:**
- 25/25 integration tests pass
- 284/285 total tests pass (1 pre-existing failure in `test_field_coverage.py` — unrelated, fails on pristine branch too)
- All 12 functions confirmed removed from `core.js`
- All 12 functions confirmed present in their new files

**Notes:**
- No issues found. Panel interdependency (panels calling each other) is safe with classic scripts — all functions are hoisted and available before any user interaction.
- `arcSectionHtml` uses `DASH.roleColor` (from colors.js) — dependency preserved via load order.
- `renderSectionsHtml` uses `DASH.escapeHtml` (from utils.js) — dependency preserved.
- Entity panels use `DASH.escapeHtml`, `DASH.findLocation`, `DASH.roleColor`, `DASH.relTypeColor` — all loaded before panels in JS_ORDER.
