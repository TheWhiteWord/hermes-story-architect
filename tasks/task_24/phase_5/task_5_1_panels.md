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

- [ ] Create `src/dashboard/js/panels/` directory
- [ ] Create `js/panels/panel-manager.js`:
  - `window.DASH = window.DASH || {};`
  - `DASH.openPanel = function() { ... }`
  - `DASH.closePanel = function() { ... }`
  - `DASH.renderSectionsHtml = function(entityType, slug) { ... }`
  - `DASH.arcSectionHtml = function(char) { ... }`
- [ ] Create `js/panels/entity-panels.js`:
  - `window.DASH = window.DASH || {};`
  - All 8 `show*Panel` functions
  - Internal calls use `DASH.*`
- [ ] Update `tools/story_dashboard.py`:
  - `JS_ORDER` includes `panels/*.js` after `views/*.js`
- [ ] Verify: tests pass, all panels open/close/content

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
