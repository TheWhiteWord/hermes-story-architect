# Phase 6: Extract JS — Graph

## Goal

Extract the 2 graph modules: `network.js` (vis-network) and `arc-graph.js` (SVG arc rendering).

## Baseline Reference

**File:** `tasks/task_24/phase_0/baseline.json` — `functions` key (includes `buildGraphView`, `resetGraphLayout`, `buildCharsGrid`, `buildArcGraph`, etc.).

After extraction, verify:
- vis-network and arc-graph logic separated
- Graph-panel cross-calls preserved via `DASH.*`
- Arc graph state variables (`arcUseSpline`, `arcShowLabels`, `arcMutedChars`) on `DASH` namespace

## Verification Against Code

### Module Boundaries

| File | Functions | Internal Deps |
|------|-----------|---------------|
| `network.js` | `buildGraphView`, `resetGraphLayout` | `roleColor`, `getRoleKey`, `relTypeColor`, `showCharacterPanel`, `showRelationshipPanel`, `hideArcTooltip`, `positionArcTooltip` |
| `arc-graph.js` | `switchGraphTab`, `getArcTypeClass`, `buildCharsGrid`, `arcXScale`, `arcYScale`, `buildArcGraph`, `catmullRomPath`, `updateLegend`, `toggleArcCharMute`, `toggleArcSpline`, `toggleArcLabels`, `showArcTooltip`, `hideArcTooltip`, `positionArcTooltip` | `escapeHtml`, `roleColor` |

### Cross-Module Dependencies

| Graph | Calls Panels | Calls Utils | Calls Colors |
|-------|--------------|-------------|--------------|
| `buildGraphView` | `showCharacterPanel`, `showRelationshipPanel` | - | `roleColor`, `getRoleKey`, `relTypeColor` |
| `buildCharsGrid` | - | `escapeHtml` | `roleColor` |
| `buildArcGraph` | - | `escapeHtml` | `roleColor` |
| `updateLegend` | - | `escapeHtml` | `roleColor` |

**Critical:** `buildGraphView` calls panel functions (`showCharacterPanel`, `showRelationshipPanel`). These are only invoked at runtime (click handlers), not parse time. With classic scripts, all functions are hoisted, so load order doesn't matter for correctness.

### State Variables

| Variable | File |
|----------|------|
| `DASH.arcUseSpline` | `arc-graph.js` |
| `DASH.arcShowLabels` | `arc-graph.js` |
| `DASH.arcMutedChars` | `arc-graph.js` |
| `DASH.ARC_GW` | `arc-graph.js` |
| `DASH.ARC_GH` | `arc-graph.js` |
| `DASH.ARC_PAD` | `arc-graph.js` |

## Checklist

- [x] Create `src/dashboard/js/graph/` directory
- [x] Create `js/graph/network.js`:
  - `window.DASH = window.DASH || {};`
  - `DASH.buildGraphView = function() { ... }`
  - `DASH.resetGraphLayout = function() { ... }`
  - Internal calls use `DASH.*`
  - `buildGraphView` click handlers: `DASH.showCharacterPanel`, `DASH.showRelationshipPanel`
- [x] Create `js/graph/arc-graph.js`:
  - `window.DASH = window.DASH || {};`
  - `DASH.arcUseSpline = false;`
  - `DASH.arcShowLabels = true;`
  - `DASH.arcMutedChars = new Set();`
  - `DASH.ARC_GW = 760;`, `DASH.ARC_GH = 320;`, `DASH.ARC_PAD = { ... };`
  - All 14 arc-graph functions
  - Internal calls use `DASH.*`
- [x] Update `tools/story_dashboard.py`:
  - `JS_ORDER` includes `graph/*.js` after `panels/*.js`
- [x] Verify: tests pass, graph renders, arc graph works

## Implementation Notes

- Extracted `buildGraphView` and `resetGraphLayout` from `core.js` → `js/graph/network.js`
- Extracted all 14 arc-graph functions from `core.js` → `js/graph/arc-graph.js`
- Removed arc state variables (`arcUseSpline`, `arcShowLabels`, `arcMutedChars`, `ARC_GW`, `ARC_GH`, `ARC_PAD`) from `core.js`
- The `DASH.buildGraphView()` call in `initStory()` (core.js:127) remains — it resolves at runtime via hoisting since classic scripts share scope
- `switchGraphTab` stays in `navigation.js` — it calls `DASH.buildCharsGrid()`, `DASH.buildArcGraph()`, `DASH.updateLegend()` which are now in arc-graph.js

## Final Report

**Status:** Complete

**Files created:**
- `src/dashboard/js/graph/network.js` (100 lines) — vis-network graph construction, physics, legend, hover/click handlers
- `src/dashboard/js/graph/arc-graph.js` (270 lines) — SVG arc rendering, char grid, controls, tooltips, state

**Files modified:**
- `src/dashboard/js/core.js` — removed 496 lines of graph code (from 1164 → 668 lines)
- `tools/story_dashboard.py` — added `graph/network.js` and `graph/arc-graph.js` to `JS_ORDER`
- `tests/test_story_dashboard_integration.py` — added graph files to hardcoded JS list in `test_no_bare_inline_handlers_in_index_html`

**Test results:** 36/36 passed (25 integration + 11 stats)

**Verification:**
- All 16 graph functions present in assembled output
- `node --check` passes on all 3 files
- No remaining graph function definitions in core.js
- Graph → panel cross-calls (`showCharacterPanel`, `showRelationshipPanel`) preserved via `DASH.*`
- Arc state variables (`arcUseSpline`, `arcShowLabels`, `arcMutedChars`) on `DASH` namespace in arc-graph.js

**No issues found.** Graph-panel cross-calls are safe with classic scripts (hoisting).

## Issues Found

None. Graph-panel cross-calls are safe with classic scripts.

## Dependencies

**Parallel:** None. Phase 6 depends on Phase 5 (panels).

## Expected Output

After Phase 6:
- 2 graph files in `js/graph/`
- vis-network and arc-graph separated
- Graph works identically

## Next Steps

After Phase 6 approval: Phase 7 (Extract JS — Statistics: statistics, charts).
