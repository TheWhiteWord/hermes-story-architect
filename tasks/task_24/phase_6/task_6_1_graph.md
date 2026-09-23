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

- [ ] Create `src/dashboard/js/graph/` directory
- [ ] Create `js/graph/network.js`:
  - `window.DASH = window.DASH || {};`
  - `DASH.buildGraphView = function() { ... }`
  - `DASH.resetGraphLayout = function() { ... }`
  - Internal calls use `DASH.*`
  - `buildGraphView` click handlers: `DASH.showCharacterPanel`, `DASH.showRelationshipPanel`
- [ ] Create `js/graph/arc-graph.js`:
  - `window.DASH = window.DASH || {};`
  - `DASH.arcUseSpline = false;`
  - `DASH.arcShowLabels = true;`
  - `DASH.arcMutedChars = new Set();`
  - `DASH.ARC_GW = 760;`, `DASH.ARC_GH = 320;`, `DASH.ARC_PAD = { ... };`
  - All 14 arc-graph functions
  - Internal calls use `DASH.*`
- [ ] Update `tools/story_dashboard.py`:
  - `JS_ORDER` includes `graph/*.js` after `panels/*.js`
- [ ] Verify: tests pass, graph renders, arc graph works

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
