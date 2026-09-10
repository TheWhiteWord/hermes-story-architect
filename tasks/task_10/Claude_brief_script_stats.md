# Task 10 v2: Script View + Statistics Panel — Refined Brief

> Brief for UI agent. Replace previous version. Based on lessons learned from first attempt.

---

## Goal

Add two new UI elements to the **current** Story Architect dashboard:

1. **"Script" tab** — Sidebar tab that renders the full screenplay as a formatted, scrollable document
2. **"Statistics" panel** — Detail panel (slides in from right) showing screenplay analytics, opened from the Script tab header

---

## The File You're Working From

**Target file**: `src/dashboard/story-dashboard.html` (current, ~2081 lines)

Read this file before producing output. The previous attempt was based on an older version and diverged from our current code. The current file has:
- Sidebar order: Story → Characters → Scenes → Locations → Plots → Worlds → Script (NEW)
- External `screenplay.css` link for fountain formatting
- `window.__STORY_DATA__` injection for index data
- `window.__SCREENPLAY_TEXT__` injection for screenplay text
- Existing `#detail-panel` for entity panels (characters, scenes, locations, plots, worlds)
- `showScenePanel()`, `showCharacterPanel()`, `showLocationPanel()`, `showPlotPanel()`, `showWorldPanel()` functions
- `formatFountainScene()` and `extractFountainScene()` for scene detail panel content

---

## What Already Exists (Do NOT Duplicate)

### screenplay.css (External Stylesheet)
Our `screenplay.css` already provides all fountain formatting with **underscore** class names:

```css
.fountain-scene_heading    /* bold, 1.5em top margin */
.fountain-action           /* full width, no indent */
.fountain-character        /* 3.5in left margin, top margin */
.fountain-parenthetical    /* 3.0in left margin */
.fountain-dialogue         /* 2.5in left, 1.0in right margin */
.fountain-transition       /* right-aligned, bold */
.fountain-centered         /* 92.5% width, centered */
.fountain-section          /* 0.2 opacity, -30px left, bold */
.fountain-synopsis         /* 0.4 opacity, italic, -20px left */
.fountain-note             /* 0.5 opacity, italic */
.fountain-page-break       /* centered, top border, 2em margin */
.fountain-boneyard         /* 0.5 opacity, italic */
.fountain-lyric            /* italic */
```

**Do NOT create new CSS for these classes.** Use screenplay.css as-is. If you need additional classes for Script view structure (document container, title page grid, page break indicators), name them with `.screenplay-` prefix to avoid conflicts.

### fountain_lexer.py (Python Parser)
Our tokenizer runs **server-side** in `story_dashboard.py`. It produces tokens with:
- `type`: scene_heading, character, dialogue, parenthetical, action, transition, centered, section, synopsis, page_break, separator, dual_dialogue_begin/end, dialogue_begin/end
- `text`: the line content
- `character`: character name (for dialogue tokens)
- `time`: duration in seconds (for dialogue/action tokens)
- `number`: scene number (for scene_heading tokens)
- `dual`: "left"/"right" (for dual dialogue tokens)
- `level`: section depth (for section tokens)

Stats are pre-computed server-side and injected as `window.__SCREENPLAY_STATS__`. Do NOT write a JS tokenizer.

### Data Injection Pipeline
```javascript
// Injected by story_dashboard.py:
window.__STORY_DATA__ = { /* index.yaml as JSON */ };
window.__SCREENPLAY_TEXT__ = "/* full screenplay.fountain text */";
window.__SCREENPLAY_STATS__ = { /* pre-computed stats from fountain_lexer.parse() */ };
```

The stats object structure:
```javascript
window.__SCREENPLAY_STATS__ = {
  lengthStats: { pagesWhole, scenes, words, characters, lines },
  durationStats: { total, action, dialogue, lengthchart_action: [...], lengthchart_dialogue: [...] },
  characterStats: { characterCount, monologues, characters: [{ name, color, speakingParts, secondsSpoken, wordsSpoken, monologues }] },
  locationStats: { locationsCount, locations: [{ name, color, number_of_scenes, times_of_day, interior_exterior }] },
  sceneStats: { scenes: [{ text, number, locType, locTime }], typeCounts: { int, ext, mixed }, timeCounts: { day, night, ... } },
  titlePage: { tl: [], tc: [], tr: [], cc: [], bl: [], br: [] },
  scriptHtml: "<h3 class=\"fountain-scene_heading\">...</h3>..." // pre-rendered screenplay HTML from tokens_to_html()
};
```

---

## Architecture Decisions (Locked — Do Not Change)

| Decision | What It Means |
|----------|---------------|
| Server-side stats | Stats are pre-computed in Python, injected as JSON. Do NOT compute stats in JS. |
| screenplay.css | Use our existing CSS for fountain formatting. Do NOT redefine fountain classes. |
| Separate stats panel | `#stats-panel` is a separate `<aside>` from `#detail-panel`. Entity panels remain functional while stats panel is open. |
| Server-side tokenization | Script view rendering uses `window.__SCREENPLAY_STATS__.scriptHtml` (pre-rendered). No client-side tokenizer. |
| Lazy build | Script view is built on first tab visit, not at boot. |
| Scene heading click | Clicking a scene heading in the Script view calls `showScenePanel(sceneId)` with the matched scene ID. |
| 52 lines/page | Soft page breaks inserted every ~52 lines at scene heading boundaries. |
| D3.js for charts | Action-vs-dialogue line chart, character speaking time bar chart, scene barcode. |
| Stats panel width | `--stats-panel-w: 360px` (wider than `#detail-panel` at 320px). |

---

## What to Produce

### HTML to Add

1. **Script sidebar button** — Insert between Worlds button and separator. SVG icon: document with lines.

2. **`#script-view` div** — New `.view` with:
   - `.view-header` containing title "Script", subtitle (page/scene count), and "Statistics" button
   - `.view-body` containing `#screenplay-container` (empty state + rendered screenplay)

3. **`#stats-panel` aside** — After `</main>`, before `#detail-panel`. Structure:
   - Header with title + close button
   - 3-tab subnav: Overview / Characters / Scenes
   - `.stats-body` with 3 `.stats-group` divs (`.active` on first)

### CSS to Add

Add to the `<style>` block in story-dashboard.html. **Do NOT redefine existing fountain classes.**

**New classes needed** (use `.screenplay-` prefix for structural elements):
- `.screenplay-doc` — max-width 680px, centered, Courier font, padding
- `.screenplay-title-page` — CSS grid for title page (tl/tc/tr/cc/bl/br areas)
- `.title-tl`, `.title-tc`, `.title-tr`, `.title-cc`, `.title-bl`, `.title-br` — grid areas
- `.screenplay-page-break` — dashed border + page number pseudo-element
- `.scene-num` — muted scene number prefix
- `.fountain-dual-dialogue` — grid for dual dialogue side-by-side
- `.script-empty` — centered empty state

**Stats panel classes** (from your previous output, keep these):
- `#stats-panel` — sliding panel, 360px when open, responsive overlay on narrow screens
- `.stats-header`, `.stats-title`, `.stats-close`, `.stats-subnav`, `.stats-tab`, `.stats-group`
- `.stat-grid`, `.stat-block`, `.stat-block-value`, `.stat-block-label`
- `.duration-bar-group`, `.duration-bar-row`, `.duration-bar-label`, `.duration-bar-track`, `.duration-bar-fill`, `.duration-bar-value`
- `.chart-container` — background, border, padding for D3 charts
- `.stats-section-label` — uppercase muted labels

**DataTables** — If you need sortable/filterable tables, you can use DataTables standalone CDN. But investigate whether plain HTML tables with click-sort would suffice for ~5-20 rows.

### JS to Add

1. **`openStatsPanel()`** — Build script if not yet built, then open `#stats-panel`
2. **`closeStatsPanel()`** — Close `#stats-panel`
3. **`switchStatsGroup(group, btn)`** — Switch tab + re-render D3 charts (charts need visible container)
4. **`buildScriptView()`** — Lazy-build on first Script tab visit. Uses `window.__SCREENPLAY_STATS__.scriptHtml` or falls back to empty state.
5. **`populateStats(stats)`** — Fill text content for all stat elements, initialize tables
6. **D3 chart functions** — `renderDurationChart()`, `renderCharacterChart()`, `renderBarcodeChart(mode)`
7. **Wrap `switchView`** — After original definition, add: if view === 'script' and !_scriptBuilt, call buildScriptView(); if view !== 'script', closeStatsPanel()

### Scene Heading Click Matching

In `buildScriptView()`, wire up click handlers on `.fountain-scene_heading` elements. Match screenplay headings to `story.scenes[]` by:

```javascript
const heading = element.textContent.toUpperCase().trim().replace(/\s*\(.*\)\s*$/, '');
const scene = story.scenes.find(s => s.heading.toUpperCase().trim().replace(/\s*\(.*\)\s*$/, '') === heading);
if (scene) showScenePanel(scene.id);
```

Handle parenthetical suffixes like "(400 YEARS EARLIER)" by stripping before comparison.

---

## Element IDs (Preserved from Brief)

All stat elements need these IDs for JS targeting:

- `lengthStats-pagesWhole`, `lengthStats-scenes`, `lengthStats-words`, `lengthStats-lines`, `lengthStats-characters`
- `durationStats-total`, `durationStats-action`, `durationStats-dialogue`, `durationStats-summary`, `durationStats-lengthchart`
- `characterStats-count`, `characterStats-monologues`, `characterStats-lengthchart`, `characterStats-table`
- `sceneStats-count`, `locationStats-count`, `sceneStats-timechart`, `locationStats-table`
- `sceneprop-type_int`, `sceneprop-type_ext`, `sceneprop-type_mixed`
- `sceneprop-time_day`, `sceneprop-time_night`, `sceneprop-time_morning`, `sceneprop-time_evening`, `sceneprop-time_dawn`, `sceneprop-time_dusk`

Each `_bar` suffixed ID corresponds to a `.duration-bar-fill` div for the colored bar.

---

## Technical Constraints

- Single HTML file (no build step)
- CDN libraries allowed (D3.js, DataTables standalone)
- Hermes CSS variables (`--foreground`, `--muted-foreground`, `--accent`, `--border`, `--card`, `--panel-bg`, `--radius`)
- Transparent background on body
- No jQuery (use vanilla JS or standalone CDN libs)
- Works in Hermes Electron preview pane (test CDN availability)

---

## Deliverables

1. **Updated `story-dashboard.html`** — Current file + your additions
2. **New CSS** — Add to `<style>` block (screenplay-structural + stats-panel classes only)
3. **New JS** — Add to `<script>` block (script view builder, stats panel controls, D3 charts, switchView wrapper)
4. **CDN links** — Add to `<head>` (D3.js, DataTables standalone if needed)

Do NOT include: inline fountain CSS (we have screenplay.css), tokenizer JS (server-side), sidebar order changes (Story-first stays), `switchView` replacement (wrap instead).

---

## Out of Scope

- PDF page map
- Readability scores
- Live sync with editor
- Export to PDF/HTML
- **Script content editing** — Read-only preview in v1. Do NOT add editable textareas, save buttons, or edit-related UI. Editing is a separate feature.
- Full dual-dialogue pairing (capture in tokens, simplified rendering acceptable)

---

## Success Criteria

- Script tab renders formatted screenplay using screenplay.css (Courier, bold headings, indented dialogue, right-aligned transitions)
- Clicking scene heading opens entity panel for that scene
- Statistics panel opens from Script tab header
- 3 sub-groups (Overview / Characters / Scenes) with tab navigation
- Charts render (line chart, bar chart, barcode)
- Tables are sortable (DataTable or hand-rolled)
- Responsive in narrow preview pane (~400px)
- Uses Hermes CSS variables
- No build step — single HTML file
