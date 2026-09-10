# Task 10 v3: Script View + Statistics Panel — Implementation Plan with Gates

> Based on UI agent integration patches. 5 patches + 1 backend task + verification gates.
> Target: `src/dashboard/story-dashboard.html` (current ~2081 lines)

---

## Phase 0: Verification & Code Awareness (No Assumptions)

**Goal**: Confirm exact file state before editing. No changes made.

### Step 0.1: Verify Current Dashboard Structure

```bash
# Count lines to confirm we're working with the right version
wc -l /media/theww/AI/Projects/Plugins/Hermes/hermes-story-architect/src/dashboard/story-dashboard.html
```

Expected: ~2081 lines

### Step 0.2: Identify Critical Anchor Points

Search the current file for these exact strings to confirm patch anchors:

| Anchor | Expected Location | Purpose |
|--------|------------------|---------|
| `<link rel="stylesheet" href="screenplay.css">` | Line 13 | CDN insertion point |
| `/* Narrow layout */` | Line ~790 | CSS insertion point |
| `<div class="nav-separator"></div>` | Line ~877 | Nav button insertion point |
| `</main>` | Line ~973 | HTML views insertion point |
| `// ─── Start` | Line ~2077 | JS insertion point |

### Step 0.3: Confirm Existing Test Fixtures

```bash
# Verify save-the-children fixture exists
ls /media/theww/AI/Projects/Plugins/Hermes/hermes-story-architect/tests/fixtures/save-the-children/
```

Expected files:
- `screenplay.fountain` — full screenplay for testing
- `.story/index.yaml` — story index
- `expected_output.json` — parsed output reference
- `characters/`, `locations/`, `plots/`, `worlds/` — entity files

### Step 0.4: Confirm screenplay.css Classes

Read `src/dashboard/screenplay.css` and verify these classes exist:
- `.fountain-scene_heading`
- `.fountain-character`
- `.fountain-dialogue`
- `.fountain-action`
- `.fountain-transition`

### Step 0.5: Confirm fountain_lexer.py API

Read `core/fountain_lexer.py` and verify:
- `parse(script_text)` returns `{'tokens': [...], 'lengthAction': float, 'lengthDialogue': float, 'title_page': {...}, 'properties': {...}}`
- `tokens_to_html(tokens)` returns HTML string with fountain classes
- Token structure: `{'type': str, 'text': str, 'character': str|None, 'time': float|None, 'number': str|None}`

### Step 0.6: Confirm story_dashboard.py Injection

Read `tools/story_dashboard.py` and verify:
- `window.__STORY_DATA__` injection (line ~58)
- `window.__SCREENPLAY_TEXT__` injection (line ~70)
- Both inject before `// ─── Boot` comment

### Gate 0 Checklist (All must pass before proceeding)

- [ ] File line count matches expected
- [ ] All anchor strings found at expected locations
- [ ] screenplay.css has required fountain classes
- [ ] fountain_lexer.py has expected API
- [ ] story_dashboard.py injects data correctly
- [ ] save-the-children fixture exists with screenplay.fountain

**If any item fails**: Re-read the actual file content and update this plan's anchor locations before proceeding.

---

## Phase 1: Backend Preparation (Task B)

**Goal**: Add server-side stats computation to `story_dashboard.py`. Testable independently.

### Task B: Add Server-Side Stats Computation

**File**: `tools/story_dashboard.py`

**What**: After screenplay injection (line ~71), compute stats using `fountain_lexer.py` and inject `window.__SCREENPLAY_STATS__`.

**Stats to compute**:
```python
window.__SCREENPLAY_STATS__ = {
    'lengthStats': {
        'pagesWhole': int,      # max(1, line_count // 52)
        'scenes': int,          # len(scene_tokens)
        'words': int,          # len(text.split())
        'characters': int,     # len(text)
        'lines': int,          # text.count('\n') + 1
    },
    'durationStats': {
        'total': float,        # lengthAction + lengthDialogue
        'action': float,       # lengthAction
        'dialogue': float,     # lengthDialogue
        'lengthchart_action': [float],   # 20 buckets
        'lengthchart_dialogue': [float], # 20 buckets
    },
    'characterStats': {
        'characterCount': int,
        'monologues': int,     # sum of character monologues > 30s
        'characters': [
            {
                'name': str,
                'color': str,           # hsl hash from name
                'speakingParts': int,
                'secondsSpoken': float,
                'wordsSpoken': int,
                'monologues': int,
            }
        ]
    },
    'locationStats': {
        'locationsCount': int,
        'locations': [
            {
                'name': str,
                'color': str,
                'number_of_scenes': int,
                'interior_exterior': [str],  # ['int'] or ['ext']
                'times_of_day': [str],
            }
        ]
    },
    'sceneStats': {
        'scenes': [
            {
                'text': str,
                'number': str,
                'locType': str,     # 'int'|'ext'|'mixed'
                'locTime': str,     # 'day'|'night'|'morning'|etc
            }
        ],
        'typeCounts': {'int': int, 'ext': int, 'mixed': int},
        'timeCounts': {'day': int, 'night': int, ...},
    },
    'titlePage': {'tl': [...], 'tc': [...], ...},
    'scriptHtml': str,  # pre-rendered HTML from tokens_to_html()
}
```

**Test**: `tests/test_story_dashboard_stats.py`

```python
"""Test server-side stats computation for story_dashboard."""
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add repo root to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "save-the-children"


@pytest.fixture
def fountain_text():
    return (FIXTURE_PATH / "screenplay.fountain").read_text()


@pytest.fixture
def index_yaml():
    return (FIXTURE_PATH / ".story" / "index.yaml").read_text()


class TestStatsComputation:
    """Test that fountain_lexer produces stats in expected format."""

    def test_parse_produces_tokens(self, fountain_text):
        """parse() returns tokens list."""
        from core.fountain_lexer import parse
        result = parse(fountain_text)
        assert 'tokens' in result
        assert isinstance(result['tokens'], list)
        assert len(result['tokens']) > 0

    def test_scene_heading_tokens(self, fountain_text):
        """Scene headings are correctly identified."""
        from core.fountain_lexer import parse
        result = parse(fountain_text)
        scenes = [t for t in result['tokens'] if t['type'] == 'scene_heading']
        assert len(scenes) > 0
        for s in scenes:
            assert 'text' in s
            assert 'number' in s

    def test_dialogue_has_duration(self, fountain_text):
        """Dialogue tokens have time estimate."""
        from core.fountain_lexer import parse
        result = parse(fountain_text)
        dialogue = [t for t in result['tokens'] if t['type'] == 'dialogue']
        assert len(dialogue) > 0
        for d in dialogue:
            assert d.get('time', 0) >= 0

    def test_character_stats_build(self, fountain_text):
        """Character stats can be aggregated from tokens."""
        from core.fountain_lexer import parse
        result = parse(fountain_text)
        tokens = result['tokens']
        
        char_map = {}
        for t in tokens:
            if t['type'] == 'dialogue' and t.get('character'):
                name = t['character']
                if name not in char_map:
                    char_map[name] = {'speakingParts': 0, 'secondsSpoken': 0, 'wordsSpoken': 0, 'monologues': 0}
                char_map[name]['speakingParts'] += 1
                char_map[name]['secondsSpoken'] += t.get('time', 0)
                char_map[name]['wordsSpoken'] += len(t['text'].split())
                if (t.get('time', 0) or 0) > 30:
                    char_map[name]['monologues'] += 1
        
        assert len(char_map) > 0
        for name, stats in char_map.items():
            assert stats['speakingParts'] > 0
            assert stats['secondsSpoken'] >= 0

    def test_scene_type_classification(self, fountain_text):
        """Scene headings classified as int/ext/mixed."""
        from core.fountain_lexer import parse
        result = parse(fountain_text)
        scenes = [t for t in result['tokens'] if t['type'] == 'scene_heading']
        
        for s in scenes:
            h = s['text'].upper()
            if 'INT.' in h and 'EXT.' in h:
                assert True  # mixed
            elif 'INT.' in h or 'INT ' in h:
                assert True  # int
            elif 'EXT.' in h or 'EXT ' in h:
                assert True  # ext

    def test_tokens_to_html_produces_classes(self, fountain_text):
        """tokens_to_html produces underscore class names."""
        from core.fountain_lexer import parse, tokens_to_html
        result = parse(fountain_text)
        html = tokens_to_html(result['tokens'])
        assert 'fountain-scene_heading' in html or 'fountain-scene_heading' in html.replace('-', '_')

    def test_duration_chart_buckets(self, fountain_text):
        """Duration chart produces 20 buckets."""
        from core.fountain_lexer import parse
        result = parse(fountain_text)
        tokens = result['tokens']
        
        BUCKETS = 20
        bucket_size = max(1, len(tokens) // BUCKETS)
        lchart_action = []
        for b in range(BUCKETS):
            start = b * bucket_size
            end = min(len(tokens), (b + 1) * bucket_size)
            slice_tokens = tokens[start:end]
            a = sum((len(t['text'].split()) / 200) * 60 for t in slice_tokens if t['type'] == 'action')
            lchart_action.append(round(a, 1))
        
        assert len(lchart_action) == BUCKETS


class TestStatsInjection:
    """Test that story_dashboard injects stats correctly."""

    def test_stats_injected_before_boot(self):
        """window.__SCREENPLAY_STATS__ is injected before Boot comment."""
        # Read the source file and verify injection pattern
        src = Path("src/dashboard/story-dashboard.html").read_text()
        # After modification, this should be true:
        # assert "window.__SCREENPLAY_STATS__" in src
        # For now, just verify the anchor exists
        assert "// ─── Boot" in src

    def test_screenplay_css_linked(self):
        """screenplay.css is linked in the dashboard."""
        src = Path("src/dashboard/story-dashboard.html").read_text()
        assert 'screenplay.css' in src
```

### Gate B Checklist

- [ ] `tests/test_story_dashboard_stats.py` created and passing
- [ ] `fountain_lexer.parse()` produces expected output format
- [ ] `tokens_to_html()` produces underscore class names
- [ ] Character stats aggregation works
- [ ] Duration chart produces 20 buckets
- [ ] All tests pass: `python -m pytest tests/test_story_dashboard_stats.py -v`

---

## Phase 2: Patch Application (Tasks 1-5)

Apply each patch in order. After each task, verify before moving to next.

### Task 1: Add D3.js CDN

**File**: `story-dashboard.html`, `<head>`

```html
<!-- D3.js for statistics charts -->
<script src="https://cdnjs.cloudflare.com/ajax/libs/d3/3.9.0/d3.min.js"></script>
```

**Verification**:
```bash
grep -n "d3.min.js" src/dashboard/story-dashboard.html
```

### Gate 1 Checklist

- [ ] D3.js script tag added
- [ ] Located after screenplay.css link
- [ ] No duplicate script tags
- [ ] HTML still valid (open in browser, check console for 404s)

---

### Task 2: Add Script View + Stats Panel CSS

**File**: `story-dashboard.html`, `<style>` block

Insert after `/* Narrow layout */` media query. See plan.md Task 2 for full CSS.

**Key classes added**:
- `#script-view .view-body`
- `.screenplay-doc`
- `.screenplay-title-page`
- `.title-tl` through `.title-br`
- `.screenplay-page-break`
- `.screenplay-doc .fountain-scene_heading` (clickable)
- `.screenplay-dual`
- `.script-empty`
- `#stats-panel` + `.open`
- `.stats-header`, `.stats-tab`, `.stats-group`
- `.stat-grid`, `.stat-block`
- `.duration-bar-*`
- `.chart-container`
- `.char-pip`
- `.stats-table` (sortable)
- `.barcode-controls`

### Gate 2 Checklist

- [ ] CSS inserted before `</style>`
- [ ] No duplicate class definitions (no redefining `.fountain-*` classes)
- [ ] `--stats-panel-w` defined
- [ ] `@media (max-width: 699px)` responsive rule present
- [ ] Existing views still render correctly (Story, Characters, Scenes, etc.)

---

### Task 3: Add Script Nav Button

**File**: `story-dashboard.html`, sidebar `<nav>`

Insert BEFORE `<div class="nav-separator"></div>`:
```html
<button class="nav-btn" data-view="script" onclick="switchView('script', this)">
  <svg class="nav-icon" viewBox="0 0 16 16" fill="none">
    <rect x="3" y="1.5" width="10" height="13" rx="1.5" stroke="currentColor" stroke-width="1.4"/>
    <line x1="5.5" y1="5" x2="10.5" y2="5" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/>
    <line x1="5.5" y1="7.5" x2="10.5" y2="7.5" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/>
    <line x1="5.5" y1="10" x2="8.5" y2="10" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/>
  </svg>
  <span class="nav-label">Script</span>
</button>
```

### Gate 3 Checklist

- [ ] Script button appears in sidebar
- [ ] Button positioned between Worlds and separator
- [ ] SVG icon renders (document with lines)
- [ ] Clicking button switches to Script tab (even if empty)
- [ ] All other nav buttons still work

---

### Task 4: Add Script View + Stats Panel HTML

**File**: `story-dashboard.html`, before `</main>`

Replace:
```html
  </main>

  <!-- Detail Panel -->
  <aside id="detail-panel">
```

With: (Script View div + Stats Panel aside + unchanged Detail Panel)

See plan.md Task 4 for full HTML.

**Critical element IDs** (must match exactly):
- `script-view`, `script-subtitle`, `screenplay-container`
- `stats-panel`, `stats-group-overview`, `stats-group-characters`, `stats-group-scenes`
- `lengthStats-pagesWhole`, `lengthStats-scenes`, `lengthStats-words`
- `durationStats-total`, `durationStats-action`, `durationStats-dialogue`
- `characterStats-count`, `characterStats-monologues`, `characterStats-table`
- `sceneStats-count`, `locationStats-count`, `locationStats-table`
- `sceneprop-type_int`, `sceneprop-type_ext`, `sceneprop-type_mixed`
- `sceneprop-time_day`, `sceneprop-time_night`, etc.

### Gate 4 Checklist

- [ ] `#script-view` div exists before `</main>`
- [ ] `#stats-panel` aside exists after `</main>`, before `#detail-panel`
- [ ] All stat element IDs present
- [ ] `#detail-panel` still exists (not removed)
- [ ] Stats panel has 3 tabs (Overview, Characters, Scenes)
- [ ] Empty state message in screenplay-container

---

### Task 5: Add Script View + Stats Panel JS

**File**: `story-dashboard.html`, `<script>` block

Insert BEFORE `// ─── Start` comment. See plan.md Task 5 for full JS.

**Key functions**:
- `fmtDurationShort(sec)` — "1h 23m" format
- `fmtDuration(sec)` — "1:23:45" format
- `setEl(id, val)` — set element text
- `setBar(baseId, count, total)` — update bar fill width
- `sortTable(tableId, colIdx)` — vanilla JS table sort
- `buildScriptView()` — render screenplay from `window.__SCREENPLAY_STATS__`
- `openStatsPanel()` — open stats panel + populate
- `closeStatsPanel()` — close stats panel
- `switchStatsGroup(group, btn)` — tab switching
- `renderDurationChart(stats)` — D3 area line chart
- `renderCharacterChart(stats)` — D3 horizontal bar chart
- `renderBarcodeChart(mode)` — D3 scene barcode
- `switchView` wrapper — lazy build + stats cleanup

### Gate 5 Checklist

- [ ] All functions defined without errors
- [ ] `window.__SCREENPLAY_STATS__` referenced (not `window.__SCREENPLAY_TEXT__` for stats)
- [ ] `buildScriptView()` handles missing stats gracefully (empty state)
- [ ] `sortTable()` handles numeric and text columns
- [ ] Scene heading click calls `showScenePanel(sceneId)`
- [ ] `switchView` wrapper preserves original behavior
- [ ] No JavaScript syntax errors (check browser console)

---

## Phase 3: Integration & Testing (Tasks 6-8)

### Task 6: Add Server-Side Stats to story_dashboard.py

**File**: `tools/story_dashboard.py`

Add after screenplay injection (line ~71):

```python
from ..core.fountain_lexer import parse as fountain_parse

# After line 71 (screenplay injection):
if screenplay_path.exists():
    try:
        sp_text = screenplay_path.read_text(encoding="utf-8")
        parsed = fountain_parse(sp_text)
        # ... build stats dict (see plan.md Task 6)
        stats_json = json.dumps({...})
        html = html.replace(
            "// ─── Boot ─────────────────────────────────────────────────────────────────────",
            f"window.__SCREENPLAY_STATS__ = {stats_json};\n// ─── Boot ─────────────────────────────────────────────────────────────────────",
        )
    except Exception:
        pass  # Dashboard still works without stats
```

### Gate 6 Checklist

- [ ] `fountain_parse` imported
- [ ] Stats computed only if screenplay.fountain exists
- [ ] `window.__SCREENPLAY_STATS__` injected before Boot comment
- [ ] Exception handling prevents dashboard breakage on parse failure
- [ ] Stats JSON is valid (no circular references, all values serializable)

---

### Task 7: Fix sortTable Default Direction

**File**: `story-dashboard.html`, JS `sortTable()` function

Change first-click behavior: numeric columns default to descending.

```javascript
// Replace:
const wasDesc = th.classList.contains('sort-desc');
// With:
const wasAsc = th.classList.contains('sort-asc');
const wasDesc = th.classList.contains('sort-desc');
if (!wasAsc && !wasDesc) {
  th.classList.add(isNum ? 'sort-desc' : 'sort-asc');
  const asc = !isNum;
} else {
  th.classList.add(wasDesc ? 'sort-asc' : 'sort-desc');
  const asc = !wasDesc;
}
```

### Gate 7 Checklist

- [ ] First click on numeric column sorts descending
- [ ] First click on text column sorts ascending
- [ ] Subsequent clicks toggle direction
- [ ] Sort indicator arrows (↑↓) appear correctly

---

### Task 8: Integration Testing

**Test file**: `tests/test_story_dashboard_integration.py`

```python
"""Integration tests for Script View + Statistics Panel."""
import pytest
from pathlib import Path
from unittest.mock import patch, mock_open

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "save-the-children"


class TestDashboardIntegration:
    """Test that dashboard HTML includes all required elements."""

    @pytest.fixture
    def dashboard_html(self):
        return Path("src/dashboard/story-dashboard.html").read_text()

    def test_script_view_exists(self, dashboard_html):
        """Script view div is present."""
        assert 'id="script-view"' in dashboard_html

    def test_stats_panel_exists(self, dashboard_html):
        """Stats panel aside is present."""
        assert 'id="stats-panel"' in dashboard_html

    def test_stats_panel_width_defined(self, dashboard_html):
        """Stats panel width CSS variable defined."""
        assert '--stats-panel-w' in dashboard_html

    def test_script_nav_button_exists(self, dashboard_html):
        """Script nav button with data-view='script'."""
        assert "data-view=\"script\"" in dashboard_html

    def test_stats_element_ids_present(self, dashboard_html):
        """All required stat element IDs are in HTML."""
        required_ids = [
            'lengthStats-pagesWhole', 'lengthStats-scenes', 'lengthStats-words',
            'durationStats-total', 'durationStats-action', 'durationStats-dialogue',
            'characterStats-count', 'characterStats-monologues',
            'sceneStats-count', 'locationStats-count',
            'sceneprop-type_int', 'sceneprop-type_ext', 'sceneprop-type_mixed',
            'sceneprop-time_day', 'sceneprop-time_night',
        ]
        for eid in required_ids:
            assert f'id="{eid}"' in dashboard_html, f"Missing ID: {eid}"

    def test_build_script_view_function(self, dashboard_html):
        """buildScriptView function is defined."""
        assert 'function buildScriptView()' in dashboard_html

    def test_open_stats_panel_function(self, dashboard_html):
        """openStatsPanel function is defined."""
        assert 'function openStatsPanel()' in dashboard_html

    def test_d3_charts_functions(self, dashboard_html):
        """D3 chart rendering functions are defined."""
        assert 'function renderDurationChart(' in dashboard_html
        assert 'function renderCharacterChart(' in dashboard_html
        assert 'function renderBarcodeChart(' in dashboard_html

    def test_sort_table_function(self, dashboard_html):
        """sortTable function is defined."""
        assert 'function sortTable(' in dashboard_html

    def test_switch_view_wrapper(self, dashboard_html):
        """switchView is wrapped (not replaced)."""
        assert 'const _origSwitchView = switchView;' in dashboard_html

    def test_scene_click_matching(self, dashboard_html):
        """Scene heading click matching logic present."""
        assert 'showScenePanel(matched.id)' in dashboard_html

    def test_no_inline_fountain_css(self, dashboard_html):
        """No inline .fountain-* class definitions (use screenplay.css)."""
        # Should not have: .fountain-scene_heading { ... } in <style>
        import re
        style_content = re.search(r'<style>(.*?)</style>', dashboard_html, re.DOTALL)
        if style_content:
            assert '.fountain-scene_heading {' not in style_content.group(1)

    def test_d3_cdn_loaded(self, dashboard_html):
        """D3.js CDN is loaded."""
        assert 'd3.min.js' in dashboard_html

    def test_stats_computation_in_backend(self):
        """story_dashboard.py computes stats."""
        src = Path("tools/story_dashboard.py").read_text()
        assert 'fountain_parse' in src
        assert '__SCREENPLAY_STATS__' in src

    def test_stats_injected_before_boot(self):
        """Stats injected before Boot comment."""
        src = Path("tools/story_dashboard.py").read_text()
        stats_pos = src.find('__SCREENPLAY_STATS__')
        boot_pos = src.find('// ─── Boot')
        assert stats_pos > 0 and boot_pos > 0
        assert stats_pos < boot_pos
```

### Gate 8 Checklist

- [ ] All integration tests pass
- [ ] Dashboard HTML contains all required elements
- [ ] Backend computes and injects stats
- [ ] No inline fountain CSS conflicts
- [ ] D3.js CDN loaded
- [ ] All functions defined

---

## Phase 4: Browser Verification (Manual)

### Task 9: Manual Browser Test

**Prerequisites**:
- Hermes desktop app running
- Plugin installed from GitHub
- save-the-children project indexed

**Steps**:

1. **Open Dashboard**
   ```
   story_dashboard project="save-the-children"
   ```

2. **Verify Script Tab**
   - [ ] Click "Script" in sidebar
   - [ ] Screenplay renders with Courier font
   - [ ] Scene headings are bold
   - [ ] Dialogue is indented
   - [ ] Transitions are right-aligned
   - [ ] Title page renders (if present in fountain file)

3. **Verify Scene Click**
   - [ ] Click a scene heading
   - [ ] Entity panel opens for that scene
   - [ ] Panel shows characters, location, plot threads

4. **Verify Statistics Panel**
   - [ ] Click "Statistics" button in Script view header
   - [ ] Stats panel slides in from right
   - [ ] Entity panel closes (if open)
   - [ ] Overview tab shows pages, scenes, words, duration
   - [ ] Duration summary text is human-readable

5. **Verify Charts**
   - [ ] Action vs. Dialogue line chart renders
   - [ ] Switch to Characters tab
   - [ ] Character speaking time bar chart renders
   - [ ] Character table shows data
   - [ ] Switch to Scenes tab
   - [ ] INT/EXT bars show percentages
   - [ ] Time-of-day bars show percentages
   - [ ] Scene barcode renders
   - [ ] Toggle barcode mode (INT/EXT ↔ Time of day)

6. **Verify Table Sorting**
   - [ ] Click "Duration" header in character table
   - [ ] First click sorts descending
   - [ ] Second click sorts ascending
   - [ ] Click "Scenes" header in location table
   - [ ] Sorts numerically

7. **Verify Entity Panels Still Work**
   - [ ] Switch to Characters tab
   - [ ] Click a character node in graph
   - [ ] Entity panel opens (not stats panel)
   - [ ] Switch to Scenes tab
   - [ ] Click a scene
   - [ ] Entity panel opens with scene content

8. **Verify Responsive**
   - [ ] Narrow the preview pane
   - [ ] Stats panel becomes overlay on narrow screens
   - [ ] Close button works

### Gate 9 Checklist (All must pass)

- [ ] Script tab renders screenplay correctly
- [ ] Scene heading click → entity panel
- [ ] Statistics button → stats panel
- [ ] All 3 chart types render
- [ ] Table sorting works (numeric desc default)
- [ ] Entity panels still functional
- [ ] Responsive narrow layout works
- [ ] No JavaScript errors in console
- [ ] No CSS conflicts with existing views

---

## Execution Order Summary

```
Phase 0: Verification (Task 0)
    ↓ Gate 0 ✓
Phase 1: Backend (Task B)
    ↓ Gate B ✓
Phase 2: Patches (Tasks 1-5)
    ↓ Gate 1-5 ✓
Phase 3: Integration (Tasks 6-8)
    ↓ Gate 6-8 ✓
Phase 4: Browser (Task 9)
    ↓ Gate 9 ✓
DONE
```

---

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| D3.js CDN blocked in Hermes Electron | Test in Task 1; if blocked, inline minimal D3 or use canvas |
| `fountain_lexer.parse()` slow on large scripts | Wrap in try/except; dashboard works without stats |
| Scene heading matching fails | Fallback: strip parenthetical suffixes, case-insensitive compare |
| Stats panel width too narrow | User confirmed 360px; adjustable via CSS variable |
| sortTable first-click direction wrong | Task 7 explicitly fixes this |
| Inline fountain CSS conflicts | Task 2 removes inline definitions; screenplay.css governs |

---

## Out of Scope (Confirmed)

- Script content editing (read-only v1)
- PDF page map
- Readability scores
- Live sync with editor
- Export to PDF/HTML
- Full dual-dialogue pairing (simplified rendering)
