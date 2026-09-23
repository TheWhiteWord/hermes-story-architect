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

- [ ] Create `js/script-view.js`:
  - `window.DASH = window.DASH || {};`
  - `DASH._scriptBuilt = false;`
  - `DASH.buildScriptView = function() { ... }`
  - Internal calls use `DASH.*`
  - Scene heading click handler: `DASH.showScenePanel(matched.id)`
- [ ] Update `tools/story_dashboard.py`:
  - `JS_ORDER` includes `script-view.js` after `statistics/*.js`
- [ ] Update tests:
  - `test_build_script_view_function` → reads `js/script-view.js`
  - `test_scene_click_matching` → reads `js/script-view.js`
- [ ] Verify: tests pass, script view renders, scene clicks work

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
