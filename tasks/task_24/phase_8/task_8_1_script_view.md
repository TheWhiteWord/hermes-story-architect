# Phase 8: Extract Script View

## Goal

Extract `script-view.js` — the screenplay rendering module.

## Baseline Reference

**File:** `tasks/task_24/phase_0/baseline.json` — `functions` key (includes `buildScriptView`), `global_state` key (includes `_scriptBuilt`).

After extraction, verify:
- Script view logic separated from views
- Scene heading click calls `DASH.showScenePanel()`
- `_scriptBuilt` flag on `DASH` namespace

## Verification Against Code

### Module Boundaries

| File | Functions | Internal Deps |
|------|-----------|---------------|
| `script-view.js` | `buildScriptView` | `escapeHtml`, `setEl`, `showScenePanel` |

### Cross-Module Dependencies

| Function | Calls Utils | Calls Panels |
|----------|-------------|--------------|
| `buildScriptView` | `escapeHtml`, `setEl` | `showScenePanel` |

**Note:** `buildScriptView` calls `DASH.showScenePanel()` when a scene heading is clicked. Safe with classic scripts (all functions hoisted).

### Who Calls `buildScriptView`

Only `openStatsPanel` in `statistics/statistics.js`. The call is guarded: `if (!DASH._scriptBuilt) DASH.buildScriptView();`

### State Variables

| Variable | File |
|----------|------|
| `DASH._scriptBuilt` | `script-view.js` |

## Checklist

- [x] Create `js/script-view.js`:
  - `window.DASH = window.DASH || {};`
  - `DASH._scriptBuilt = false;`
  - `DASH.buildScriptView = function() { ... }`
  - Internal calls use `DASH.*`
  - Scene heading click handler: `DASH.showScenePanel(matched.id)`
- [x] Update `tools/story_dashboard.py`:
  - `JS_ORDER` includes `script-view.js` after `statistics/*.js`
- [x] Update tests:
  - `test_build_script_view_function` → reads `js/script-view.js`
  - `test_scene_click_matching` → reads `js/script-view.js`
- [x] Verify: tests pass, script view renders, scene clicks work

## Issues Found

None. `script-view.js` is self-contained.

## Dependencies

**Parallel:** None. Phase 8 depends on Phase 7 (statistics).

## Expected Output

After Phase 8:
- `js/script-view.js` exists
- Script view renders correctly
- Scene heading clicks work

## Next Steps

After Phase 8 approval: Phase 9 (Cleanup & Validation).

## ✅ Phase 8 Complete

### Changes Made

1. **`src/dashboard/js/script-view.js`** (NEW)
   - Extracted `buildScriptView` from `core.js` (lines 128-221)
   - `_scriptBuilt` moved from module-local `let` to `DASH._scriptBuilt`
   - All internal calls use `DASH.*` namespace

2. **`src/dashboard/js/core.js`** (MODIFIED)
   - Removed `let _scriptBuilt = false;` (line 8)
   - Removed `DASH.buildScriptView` function body (lines 128-221)
   - Removed `DASH.buildScriptView()` call from `initStory()`
   - Now 124 lines (was 221)

3. **`tools/story_dashboard.py`** (MODIFIED)
   - Added `"script-view.js"` to `JS_ORDER` after statistics files

4. **`tests/test_story_dashboard_integration.py`** (MODIFIED)
   - `test_build_script_view_function` → reads `src/dashboard/js/script-view.js`
   - `test_scene_click_matching` → reads `src/dashboard/js/script-view.js`
   - `test_no_bare_inline_handlers_in_index_html` → added `script-view.js` to file list

### Test Results

- `test_story_dashboard_integration.py`: 25 passed ✓
- `test_story_dashboard_stats.py`: 11 passed ✓
- Manual assembly check: `DASH._scriptBuilt`, `DASH.buildScriptView`, `DASH.showScenePanel(matched.id)` all present ✓

### Notes

- `openStatsPanel` in `statistics/statistics.js` already checks `DASH._scriptBuilt` — this was correctly preserved since `_scriptBuilt` is now on `DASH.*` namespace, not module-local.
- Phase 8 is the final JS extraction phase. No further modules to extract.
