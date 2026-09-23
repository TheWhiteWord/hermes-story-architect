# Phase 1: Establish Shell

## Goal

Extract the HTML shell from the monolith into `src/dashboard/index.html` with CSS and JS placeholder comments. The Python assembler replaces placeholders with file contents. Behavior must be identical.

## Baseline Reference

**File:** `tasks/task_24/phase_0/baseline.json`

After assembly, verify the assembled HTML matches baseline:
- All 103 static DOM IDs present
- All 3 CDNs present
- Boot comment string intact
- screenplay.css styles present
- No unresolved placeholders

## Verification Against Code

### Inline Handler Strategy (RESOLVED)

**Decision: Option A — prefix all HTML-facing handlers with `DASH.`**

Not every function becomes `DASH.foo`. Only functions at the **HTML ↔ JS boundary** (called from inline event handlers) get the prefix. Internal JS→JS calls stay local within their module.

### Step 1: Enumerate all inline handlers

Found 66 total inline handlers using 28 unique functions (verified against actual monolith):

| Function | Handler Types | Count |
|----------|---------------|-------|
| switchView | onclick | 8 |
| showScenePanel | onclick | 5 |
| showCharacterPanel | onclick | 5 |
| sortTable | onclick | 8 |
| showLocationPanel | onclick | 3 |
| showPlotPanel | onclick | 6 |
| closeStatsPanel | onclick | 1 |
| switchStatsGroup | onclick | 4 |
| toggleArcCharMute | onclick | 1 |
| showRelationshipPanel | onclick | 1 |
| showActPanel | onclick | 1 |
| showSequencePanel | onclick | 2 |
| showWorldPanel | onclick | 2 |
| loadFromFile | onclick | 1 |
| loadSampleData | onclick | 1 |
| refreshIndex | onclick | 1 |
| toggleSidebar | onclick | 1 |
| resetGraphLayout | onclick | 1 |
| switchGraphTab | onclick | 2 |
| toggleArcSpline | onclick | 1 |
| toggleArcLabels | onclick | 1 |
| openStatsPanel | onclick | 1 |
| closePanel | onclick | 1 |
| handleFileLoad | onchange | 1 |
| renderBarcodeChart | onchange | 2 |
| filterScenes | oninput | 1 |
| showArcTooltip | onmouseenter | 1 |
| hideArcTooltip | onmouseleave | 1 |

All 28 correspond to real `function name(...)` definitions in the monolith. These are the **HTML-facing API surface**.

### Step 2: Update HTML handlers only

Replace `foo(` → `DASH.foo(` for the 28 functions above **only in inline handler attributes** (`onclick=`, `onchange=`, `oninput=`, `onmouseenter=`, `onmouseleave=`).

**Do NOT replace:**
- JS-to-JS calls within `<script>` block (e.g., `switchView(...)` inside another function)
- Function definitions themselves (those get `DASH.switchView = function(...)` in Phase 3)

### Step 3: Post-replacement verification

After all replacements, search the entire `index.html` for any remaining bare handler references inside HTML attributes:
```bash
grep -nP 'on\w+="[^"]*\b(switchView|showScenePanel|...)\b[^."]' index.html
```
Should return zero hits. Any hit means a handler was missed.

### Step 4: Add regression test

Add to `test_story_dashboard_integration.py`:

```python
def test_no_bare_inline_handlers_in_index_html():
    """All inline event handlers must use DASH.* prefix (not bare globals)."""
    index_html = Path("src/dashboard/index.html").read_text()
    handler_fns = [
        "switchView", "showScenePanel", "showCharacterPanel", "showLocationPanel",
        "showPlotPanel", "showRelationshipPanel", "showSequencePanel", "showActPanel",
        "showWorldPanel", "openStatsPanel", "closeStatsPanel", "switchStatsGroup",
        "sortTable", "switchGraphTab", "resetGraphLayout", "toggleArcSpline",
        "toggleArcLabels", "toggleArcCharMute", "refreshIndex", "toggleSidebar",
        "loadFromFile", "loadSampleData", "closePanel", "handleFileLoad",
        "renderBarcodeChart", "filterScenes", "showArcTooltip", "hideArcTooltip",
    ]
    for fn in handler_fns:
        # Must NOT appear as bare function in handler attribute
        assert not re.search(rf'on\w+="{fn}\(', index_html), f"Bare {fn}() in handler — must be DASH.{fn}()"
        # Must appear with DASH prefix if it's an HTML-facing function
        assert f'DASH.{fn}(' in index_html, f"DASH.{fn}() missing from index.html"
```

### SwitchView Wrapper

```js
const _origSwitchView = switchView;
switchView = function(view, btn) { ... };
```

**Issue:** This wrapper reassigns `switchView` at runtime. After refactor, `DASH.switchView` is defined in `navigation.js`. The wrapper lives at the end of the script. **Resolution:** The wrapper stays at the end of the last JS file (or in `core.js`). Since `DASH.switchView` is a function expression (`DASH.switchView = function(...)`), it CAN be reassigned: `const _orig = DASH.switchView; DASH.switchView = function(view, btn) { _orig(view, btn); ... }`. This works.

### Module-Level State

```js
let story = null;           // core.js → DASH.story
let network = null;         // core.js → DASH.network
let sidebarExpanded = false; // navigation.js → DASH.sidebarExpanded
let currentView = 'graph';  // navigation.js → DASH.currentView
let allScenes = [];        // views/scenes.js → DASH.allScenes
let _scriptBuilt = false;  // script-view.js → DASH._scriptBuilt
let _statsPopulated = false; // statistics/statistics.js → DASH._statsPopulated
let _currentBarcodeMode = 'type'; // statistics/charts.js → DASH._currentBarcodeMode
let _chartObservers = {};  // statistics/charts.js → DASH._chartObservers
let arcUseSpline = false;  // graph/arc-graph.js → DASH.arcUseSpline
let arcShowLabels = true;  // graph/arc-graph.js → DASH.arcShowLabels
let arcMutedChars = new Set(); // graph/arc-graph.js → DASH.arcMutedChars
```

**Resolution:** Convert to `DASH.story = null`, etc. at top of respective files.

### Dead Code

- `buildSequencesView()` — empty stub, DELETE
- `buildActsView()` — empty stub, DELETE

## Checklist

- [ ] Create `src/dashboard/css/` and `src/dashboard/js/` directories
- [ ] Create `src/dashboard/index.html`:
  - Extract HTML shell from monolith (lines 1–1823 of original)
  - Remove `<style>...</style>` block → replace with `<!-- CSS_PLACEHOLDER -->`
  - Remove `<script>...</script>` block → replace with `<!-- JS_PLACEHOLDER -->`
  - Remove `<link rel="stylesheet" href="screenplay.css">` → replace with `<!-- SCREENPLAY_CSS_PLACEHOLDER -->`
  - **Update 66 inline handlers** (28 unique functions): `foo(` → `DASH.foo(` only in HTML attributes
  - Keep CDNs in place (vis-network, js-yaml, D3)
  - Add regression test for bare handler detection
- [ ] Verify no bare handlers remain (post-replacement grep check)
- [ ] Update `tools/story_dashboard.py`:
  - Add `CSS_ORDER`, `JS_ORDER` lists
  - Add `assemble_dashboard()` function reading from files
  - Replace string-replace logic with placeholder replacement
  - Boot comment injection point preserved
- [ ] Verify: tests pass, dashboard renders, no behavioral change
- [ ] Capture assembled artifact as baseline for Phase 2+

## Expected Output

After Phase 1, the assembled HTML should be **structurally identical** to the original monolith:
- Same DOM IDs
- Same CDNs
- Same inline handlers (with `DASH.` prefix)
- Same Boot comment
- Same screenplay styles
- Same script content

## Issues Flagged

None remaining from Phase 0 (Issue 1 resolved by `DASH.*` prefix decision, Issues 2-3 auto-resolved).

## Next Steps

After Phase 1 approval: Phase 2 (Extract CSS).
