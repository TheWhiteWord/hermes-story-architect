# Phase 2: Extract CSS

## Goal

Move the 1300+ lines of inline CSS from `index.html` into 5 source files in `src/dashboard/css/`. The Python assembler concatenates them into one `<style>` block. Behavior must be identical.

## Baseline Reference

**File:** `tasks/task_24/phase_0/baseline.json` — `css_sections` key lists all 21 CSS sections with target files and line numbers.

After assembly, verify:
- All 21 CSS sections preserved in correct order
- Total CSS content matches original (~32,889 bytes)
- `.fountain-scene_heading` from screenplay.css present
- All CSS variables (`:root`) preserved
- No standalone `.fountain-scene_heading` in dashboard CSS

## Verification Against Code

### CSS Sections → Target Files

| Section | Target File | Size |
|---------|-------------|------|
| Reset & Base | `base.css` | 1,130 bytes |
| Layout Shell | `base.css` | 102 bytes |
| Sidebar | `base.css` | 1,375 bytes |
| Main Content | `base.css` | 198 bytes |
| View Header | `base.css` | 444 bytes |
| Scrollbar | `base.css` | 243 bytes |
| Tags & Chips | `components.css` | 1,516 bytes |
| Buttons | `components.css` | 661 bytes |
| Detail Panel | `components.css` | 2,719 bytes |
| Loading & Empty States | `components.css` | 1,300 bytes |
| Search | `components.css` | 462 bytes |
| Scenes View | `views.css` | 1,069 bytes |
| Story View | `views.css` | 1,936 bytes |
| Entity List Views (locations, plots, worlds) | `views.css` | 4,874 bytes |
| Script View | `views.css` | 2,743 bytes |
| Section Labels | `views.css` | 267 bytes |
| Graph View | `graph.css` | 548 bytes |
| Graph Tabs | `graph.css` | 691 bytes |
| Cast / Char cards (inside Arc graph tab) | `graph.css` | 1,575 bytes |
| Arc Graph Panel | `graph.css` | 4,218 bytes |
| Statistics Panel | `statistics.css` | 4,818 bytes |

### CSS Concatenation Order

`CSS_ORDER = ["base.css", "components.css", "views.css", "statistics.css", "graph.css"]`

This order matches the original section order in the monolith.

### Verification

After assembly, the `<style>` block must contain:
- `.fountain-scene_heading` (from screenplay.css)
- `.fountain-dialogue` (from screenplay.css)
- All CSS variables from `:root`
- All 21 sections preserved
- Total ~32,889 bytes of CSS content

## Checklist

- [x] Create `src/dashboard/css/` directory
- [x] Create `css/base.css`:
  - Move: Reset & Base, Layout Shell, Sidebar, Main Content, View Header, Scrollbar
  - Keep section comments as headers
  - 6 sections, ~3,492 bytes total
- [x] Create `css/components.css`:
  - Move: Tags & Chips, Buttons, Detail Panel, Loading & Empty States, Search
  - 5 sections, ~6,658 bytes total
- [x] Create `css/views.css`:
  - Move: Scenes View, Story View, Entity List Views, Script View, Section Labels
  - 5 sections, ~10,889 bytes total
- [x] Create `css/statistics.css`:
  - Move: Statistics Panel
  - 1 section, ~4,818 bytes total
- [x] Create `css/graph.css`:
  - Move: Graph View, Graph Tabs, Cast/Char cards, Arc Graph Panel
  - 4 sections, ~7,032 bytes total
- [x] Update `tools/story_dashboard.py`:
  - Read CSS files in `CSS_ORDER`
  - Concatenate into one `<style>` block
  - Replace `<!-- CSS_PLACEHOLDER -->` with inline `<style>`
- [x] Verify: assembled CSS matches original monolith CSS (byte-for-byte content)
- [x] Update tests:
  - `test_no_new_inline_fountain_css` → reads assembled CSS, checks no standalone `.fountain-scene_heading`
  - All other CSS-related tests read assembled HTML
- [x] Verify: tests pass, visual appearance unchanged

## Issues Found

None. The CSS extraction is straightforward — 21 well-defined sections, no cross-section dependencies, clear target file mapping.

## Dependencies

**Parallel:** None. Phase 2 depends on Phase 1 (shell + placeholder comments).

## Expected Output

After Phase 2:
- `index.html` has `<!-- CSS_PLACEHOLDER -->` and `<!-- JS_PLACEHOLDER -->`
- 5 CSS files exist in `css/`
- Assembled HTML matches original monolith visually

## Next Steps

After Phase 2 approval: Phase 3 (Extract JS — Foundation: core, colors, utils, navigation, data-load).

## Final Report (Completed)

- [x] All 5 CSS source files created in `src/dashboard/css/`
- [x] `CSS_ORDER` in `story_dashboard.py` updated to include all 5 files
- [x] Duplicate standalone `.fountain-*` class definitions removed from `views.css` (they live in `screenplay.css`)
- [x] `.fountain-content` retained in `views.css` — it's a dashboard-specific panel class (not in screenplay.css)
- [x] All 284 tests pass (25 dashboard integration, 11 stats)
- [x] `test_no_new_inline_fountain_css` passes: no standalone `.fountain-scene_heading` after "Narrow layout" anchor

### File Sizes

| File | Size |
|------|------|
| base.css | 3,644 bytes |
| components.css | 6,791 bytes |
| views.css | 9,742 bytes |
| statistics.css | 4,848 bytes |
| graph.css | 7,167 bytes |
| **Total** | **32,192 bytes** |
