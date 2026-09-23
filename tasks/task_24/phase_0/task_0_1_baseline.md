# Phase 0: Baseline Capture

## Goal

Capture the complete structural baseline of the existing monolith before any extraction. This becomes the reference for verifying behavioral equivalence after each stage.

## Checklist

- [x] Create `tasks/task_24/phase_0/baseline.json` with:
  - All DOM IDs (112 total — verified: 103 static + 9 dynamic template)
  - All function definitions (77 total, including nested — verified)
  - All inline onclick handlers (62 total — verified)
  - External CDN URLs — verified
  - All `data-hermes-send` attributes — verified (13 occurrences, 12 unique)
  - Boot comment string — verified
  - screenplay.css link string — verified
  - Total line count — verified (4,329)
- [x] Verify all 21 CSS sections are accounted for in the 5 target CSS files
- [x] Document all global state variables (module-level `let`/`const`)
- [x] Document all inline `onclick` handler function calls
- [x] Capture the exact Boot comment injection point
- [x] Record any issues or plan inconsistencies found

---

## Verification Data (captured)

### DOM IDs
112 total (103 static + 9 dynamic template). Key groups:
- App shell: `app`, `loading-screen`, `error-screen`, `sidebar`, `main`
- Views: `story-view`, `graph-view`, `scenes-view`, `locations-view`, `plots-view`, `relationships-view`, `worlds-view`, `script-view`
- Stats: `stats-panel`, `stats-group-{overview,characters,scenes,structure}`, all stat element IDs
- Panels: `detail-panel`, `panel-type`, `panel-name`, `panel-body`, `panel-footer`
- Graph: `network-canvas`, `graph-legend`, `chars-grid`, `arc-graph-wrap`, `arc-legend`, `arc-warnings`
- Script: `screenplay-container`, `script-subtitle`

### Functions (77 total)
All defined as `function name(...)` at top level. 5 nested: `renderBeats` (inside buildArcGraph), `perspectiveHtml` (inside renderSectionsHtml), `arcXScale`/`arcYScale`/`beatX` (module-level, arc-only).

### Inline Handlers (62 total)
All use bare function names (e.g., `onclick="switchView('story', this)"`).

### External CDNs
- `https://cdnjs.cloudflare.com/ajax/libs/vis-network/9.1.9/standalone/umd/vis-network.min.js`
- `https://cdnjs.cloudflare.com/ajax/libs/js-yaml/4.1.0/js-yaml.min.js`
- `https://cdnjs.cloudflare.com/ajax/libs/d3/7.9.0/d3.min.js`

### Hermes Integration
13 `data-hermes-send` attributes across panels and views (12 unique prompts).

---

## Issues Found

### Issue 1 (CRITICAL): Inline Handler Naming

**Problem:** All 62 inline `onclick` handlers use bare function names (`switchView(...)`, `showScenePanel(...)`). After refactor, functions attach to `window.DASH` namespace (`DASH.switchView = function(...)`). Bare names will break because `switchView` is no longer a global.

**Impact:** Medium. Requires updating all 62 inline handlers in `index.html` from bare names to `DASH.*` prefix, OR keeping dual assignment (`window.switchView = DASH.switchView`).

**Resolution needed:** Ask user.

### Issue 2 (MINOR): Module-Level State Variables

**Problem:** `let _scriptBuilt = false;` and `let _statsPopulated = false;` are module-level state. After extraction, they live in separate files but need shared access.

**Impact:** Low. Can be resolved by storing on `DASH` namespace: `DASH._scriptBuilt = false`.

**Resolution:** Auto-resolve during implementation.

### Issue 3 (MINOR): Dead Code Functions

**Problem:** `buildSequencesView()` and `buildActsView()` are empty stubs (just comments).

**Impact:** Low. Should be deleted during extraction.

**Resolution:** Auto-resolve during implementation.

### Issue 4 (NOTE): CSS Divider Count

**Observation:** Plan says 21 CSS sections. Actual count: 21 dividers inside `<style>` block. 6 additional dividers are in JavaScript comments — NOT CSS. All 21 style sections accounted for.

### Issue 5 (NOTE): `data-hermes-send` Count

**Observation:** Task brief says 12 `data-hermes-send` attributes. Actual count: 13 occurrences. One prompt ("Give me an overview of ${p.name}.") appears twice.

---

## Next Steps

After Phase 0 approval:
1. Resolve Issue 1 with user
2. Proceed to Phase 1: Establish Shell

---

## Phase 0 Completion Report

**Captured baseline to:** `tasks/task_24/phase_0/baseline.json` (10.8 KB, validated JSON)

**Verified counts:**
| Metric | Plan Says | Actual | Status |
|--------|-----------|--------|--------|
| Total lines | ~4,300 | 4,329 | ✓ |
| DOM IDs | 112 | 112 (103 static + 9 dynamic) | ✓ |
| Functions | 77 | 77 | ✓ |
| Inline onclick | 62 | 62 | ✓ |
| CSS sections | 21 | 21 (in <style>) + 6 JS comment dividers | ✓ |
| data-hermes-send | 12 | 13 (12 unique prompts) | ✓+1 |
| CDNs | 3 | 3 | ✓ |

**No issues found with plan structure.** The monolith is well-organized: CSS at top (lines 18-1332), HTML body (1333-1823), JavaScript (1824-4327). Boot sequence: `boot()` → data loading → view builders → panels → graph → statistics → script view. State vars declared near end of file (line 4022) but used throughout via hoisting (since `let`/`const` are hoisted to temporal dead zone — this works because functions are called, not invoked at parse time).

**One plan note:** `_statsPopulated` flag was not mentioned in the original Issue 2 list but is confirmed to exist. Both `_scriptBuilt` and `_statsPopulated` should be resolved the same way (DASH namespace or core.js state).
