# Phase 7: Extract JS — Statistics

## Goal

Extract the 2 statistics modules: `statistics.js` (panel lifecycle + stat population) and `charts.js` (D3 chart implementations).

## Baseline Reference

**File:** `tasks/task_24/phase_0/baseline.json` — `functions` key (includes `openStatsPanel`, `closeStatsPanel`, `populateStats`, `populateStructuralStats`, `sortTable`, `renderDurationChart`, `renderCharacterChart`, `renderBarcodeChart`), `global_state` key (includes `_statsPopulated`).

After extraction, verify:
- Stats panel lifecycle separated from chart rendering
- Statistics-charts cross-calls preserved
- State variables (`_statsPopulated`, `_currentBarcodeMode`, `_chartObservers`) on `DASH` namespace

## Verification Against Code

### Module Boundaries

| File | Functions | Internal Deps |
|------|-----------|---------------|
| `statistics.js` | `openStatsPanel`, `closeStatsPanel`, `switchStatsGroup`, `_renderChartsForGroup`, `populateStats`, `populateStructuralStats`, `sortTable` | `fmtDuration`, `fmtDurationShort`, `setEl`, `setBar`, `escapeHtml`, `roleColor` |
| `charts.js` | `_ensureChartRendered`, `renderDurationChart`, `_renderDurationChart`, `renderCharacterChart`, `renderBarcodeChart` | `fmtDurationShort` |

### Cross-Module Dependencies

| Stat/Chart | Calls Utils | Calls Colors | Calls Panels |
|------------|-------------|--------------|--------------|
| `populateStats` | `fmtDuration`, `fmtDurationShort`, `setEl`, `setBar`, `escapeHtml` | - | - |
| `populateStructuralStats` | `escapeHtml`, `setEl` | `roleColor` | - |
| `_renderDurationChart` | `fmtDurationShort` | - | - |
| `renderCharacterChart` | `fmtDurationShort` | - | - |

**No panel calls from statistics.** Clean separation.

### State Variables

| Variable | File |
|----------|------|
| `DASH._scriptBuilt` | `script-view.js` (referenced by `openStatsPanel`) |
| `DASH._statsPopulated` | `statistics.js` |
| `DASH._structuralStatsPopulated` | `statistics.js` |
| `DASH._currentBarcodeMode` | `charts.js` |
| `DASH._chartObservers` | `charts.js` |

## Checklist

- [ ] Create `src/dashboard/js/statistics/` directory
- [ ] Create `js/statistics/statistics.js`:
  - `window.DASH = window.DASH || {};`
  - `DASH._statsPopulated = false;`
  - `DASH._structuralStatsPopulated = false;`
  - `DASH.openStatsPanel = function() { ... }`
  - `DASH.closeStatsPanel = function() { ... }`
  - `DASH.switchStatsGroup = function(group, btn) { ... }`
  - `DASH._renderChartsForGroup = function(group) { ... }`
  - `DASH.populateStats = function(stats) { ... }`
  - `DASH.populateStructuralStats = function() { ... }`
  - `DASH.sortTable = function(tableId, colIdx) { ... }`
  - Internal calls use `DASH.*`
  - `openStatsPanel` checks `DASH._scriptBuilt` and calls `DASH.buildScriptView()` if needed
- [ ] Create `js/statistics/charts.js`:
  - `window.DASH = window.DASH || {};`
  - `DASH._currentBarcodeMode = 'type';`
  - `DASH._chartObservers = {};`
  - `DASH._ensureChartRendered = function(containerId, renderFn) { ... }`
  - `DASH.renderDurationChart = function(stats) { ... }`
  - `DASH._renderDurationChart = function(stats) { ... }`
  - `DASH.renderCharacterChart = function(stats) { ... }`
  - `DASH.renderBarcodeChart = function(mode) { ... }`
  - Internal calls use `DASH.*`
- [ ] Update `tools/story_dashboard.py`:
  - `JS_ORDER` includes `statistics/*.js` after `graph/*.js`
- [ ] Update tests:
  - `test_open_stats_panel_function` → reads `js/statistics/statistics.js`
  - `test_d3_charts_functions` → reads `js/statistics/charts.js`
  - `test_sort_table_function` → reads `js/statistics/statistics.js`
- [ ] Verify: tests pass, stats panel works, charts draw

## Issues Found

None. Statistics-charts separation is clean.

## Dependencies

**Parallel:** None. Phase 7 depends on Phase 6 (graph).

## Expected Output

After Phase 7:
- 2 statistics files in `js/statistics/`
- Stats panel lifecycle separated from chart rendering
- Stats and charts work identically

## Next Steps

After Phase 7 approval: Phase 8 (Extract Script View).
