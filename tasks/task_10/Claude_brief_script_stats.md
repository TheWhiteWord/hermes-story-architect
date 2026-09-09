# Task 10: Full Script Preview & Screenplay Statistics

> Brief for the UI agent — design a new Script view (main tab) and a Statistics panel (detail panel) for the Story Architect dashboard.

---

## Goal

Add **two new UI elements** to the Story Architect dashboard (`src/dashboard/story-dashboard.html`):

1. **"Script" tab** — A main sidebar tab that renders the entire screenplay in a formatted, scrollable preview (like Better Fountain's "Live Preview").
2. **"Statistics" panel** — A detail panel (slides in from the right, like the entity panels) that shows comprehensive screenplay analytics. **Opened from the Script tab**, not from the sidebar.

---

## Architecture Overview

### Current Dashboard Structure

```
┌─────────────────────────────────────────────────────────┐
│ Sidebar    │  Main Content                              │
│            │                                             │
│ ● Story    │  ┌─────────────────────────────────────┐   │
│ ● Graph    │  │  .view (active)                     │   │
│ ● Scenes   │  │    .view-header                     │   │
│ ● Locations│  │    .view-body                       │   │
│ ● Plots    │  │                                     │   │
│ ● Worlds   │  └─────────────────────────────────────┘   │
│ ─ ─ ─ ─ ─ │                                             │
│ ↻ Refresh  │                          ┌─────────────┐   │
│ ⇄ Toggle   │                          │ Detail Panel│   │
│            │                          │ (slides in) │   │
└─────────────────────────────────────────────────────────┘
```

### What We're Adding

```
┌─────────────────────────────────────────────────────────┐
│ Sidebar    │  Script View          │  Statistics Panel  │
│            │                       │  (detail panel)    │
│ ● Story    │  ┌──────────────────┐ │  ┌──────────────┐  │
│ ● Graph    │  │  .view-header    │ │  │ Overview     │  │
│ ● Scenes   │  │  [Stats button]──┼─┼──│ Characters   │  │
│ ● Locations│  │  .view-body      │ │  │ Scenes       │  │
│ ● Plots    │  │  (formatted      │ │  │              │  │
│ ● Worlds   │  │   screenplay)    │ │  └──────────────┘  │
│ ● Script ← NEW                                         │
│ ─ ─ ─ ─ ─ │                       │                    │
│ ↻ Refresh  │                       │                    │
└─────────────────────────────────────────────────────────┘
```

---

## Reference: How Better Fountain Does It

We ported Better Fountain's parser (`core/fountain_lexer.py` is a faithful port of `afterwriting-parser.js`). BF has two webviews that are our reference:

### Live Preview (`webviews/src/preview.html`)
- Renders the full screenplay as **formatted pages** (Courier Prime font, US Letter/A4, proper margins)
- Scene headings bold, dialogue indented, dual dialogue side-by-side, transitions right-aligned
- Title page rendered as a grid (top-left, top-center, top-right, center, bottom-left, bottom-right)
- Page breaks create new pages; page numbers in footer

### Statistics Panel (`webviews/src/stats.html` + `stats.js`)
A **sidebar-navigated** panel with 3 groups:

| Group | What it shows |
|-------|---------------|
| **Overview** | Length (pages, scenes, words, characters, lines), Duration (total/action/dialogue), Duration line chart (action vs dialogue over screenplay length) |
| **Characters** | Character count, monologues, complexity (readability median), Per-character duration line chart, Sortable table (name, duration, lines, words, complexity, monologues) |
| **Scenes** | Scene count, location count, INT/EXT/MIXED breakdown, time-of-day breakdown, Scene barcode chart (colored bars by type/time), Location table (name, scenes, time, INT/EXT) |

**Charts use D3.js** (line charts, barcode charts). Tables use DataTables (jQuery plugin).

---

## Current Dashboard State (What Already Exists)

The dashboard already has screenplay support — don't duplicate it:

### Already Present in `story-dashboard.html`

| Feature | Location | Status |
|---------|----------|--------|
| Screenplay CSS classes | Lines 657-747 (in `<style>`) | ✅ Complete |
| `formatFountainScene()` | JS function | ✅ Classifies lines into fountain types |
| `extractFountainScene()` | JS function | ✅ Extracts scene by heading |
| `window.__SCREENPLAY_TEXT__` | Injected by `story_dashboard.py` | ✅ Full screenplay text available |
| Detail panel (`#detail-panel`) | Lines 395-522 | ✅ Slides in from right |
| Entity panel functions | `showCharacterPanel()`, `showScenePanel()`, etc. | ✅ Pattern to follow |

### What the Dashboard Already Loads

```javascript
// Injected by story_dashboard.py (lines 58-71):
window.__STORY_DATA__ = { /* index.yaml as JSON */ };
window.__SCREENPLAY_TEXT__ = "/* full screenplay.fountain text */";
```

---

## What Data We Already Have

Our parser (`core/fountain_lexer.py`) already produces all the raw data needed. Here's the mapping:

### From `parse()` result:

| Field | Type | What it is |
|-------|------|------------|
| `tokens` | `list[dict]` | All tokens with `type`, `text`, `line`, `time`, `character`, `number`, `dual`, `level` |
| `lengthAction` | `float` | Total action duration (seconds) |
| `lengthDialogue` | `float` | Total dialogue duration (seconds) |
| `properties.scenes` | `list[dict]` | `{scene, text, line, actionLength, dialogueLength}` |
| `properties.sceneLines` | `list[int]` | Line numbers where scenes start |
| `properties.sceneNames` | `list[str]` | Scene heading texts |
| `properties.characters` | `dict[str, list[int]]` | Character name → [scene_numbers] |
| `properties.locations` | `dict[str, list[dict]]` | Location slug → [{scene_number, line, name, interior, exterior, time_of_day}] |
| `properties.structure` | `list[dict]` | Hierarchical structure (sections with children, scenes) |
| `title_page` | `dict` | {tl, tc, tr, cc, bl, br, hidden} — title page tokens |

### From `calculate_dialogue_duration(text)`:
Already ported. Returns seconds (float).

### From `tokens_to_html(tokens)`:
Already ported. Returns HTML string with `fountain-{type}` CSS classes.

---

## What We DON'T HAVE Yet (Gaps to Compute)

These are **not** in the parser yet, but are trivial to compute from the raw text + tokens:

| Stat | How to compute | BF reference |
|------|---------------|--------------|
| **Word count** | `len(text.split())` on raw screenplay | `getWordCount()` |
| **Character count** | `len(text)` | `getCharacterCount()` |
| **Character count (no whitespace)** | `len(re.sub(r'\s', '', text))` | `getCharacterCountWithoutWhitespace()` |
| **Line count** | `text.count('\n')` | `getLineCount()` |
| **Line count (no whitespace)** | Count lines matching `/\S/` | `getLineCountWithoutWhitespace()` |
| **Page count** | Estimate: `max(1, line_count / 52)` (52 lines/page is standard) or use PDF | `pdf.pagecount` |
| **Pages (real)** | Same estimate, or count page breaks + 1 | `pdf.pagecountReal` |
| **Is monologue** | `seconds > 30` | `isMonologue()` |
| **Per-character stats** | Iterate tokens, group by `character`, count speaking parts, sum `time`, count words | `createCharacterStatistics()` |
| **Scene type (INT/EXT/MIXED)** | Parse scene heading regex group 1 | `locationtype()` |
| **Scene time-of-day** | Parse scene heading after dash | `locationtime()` |
| **Duration by scene property** | Sum `actionLength + dialogueLength` per scene, bucket by type/time | `getLengthChart()` |
| **Character color** | Hash-based HSL from name | `wordToColor()` |
| **Location color** | Hash-based HSL from slug | `wordToColor()` |
| **Readability / complexity** | Optional — requires `readability-scores` Python port. Can be omitted in v1. | `readabilityScores()` |
| **PDF page map** | Optional — requires PDF generation. Can be omitted in v1. | `pdfstats.linemap` |

---

## Design Requirements

### Script Tab (Main View)

**Purpose**: Show the full screenplay formatted like a real screenplay.

**Integration**:
- Add a new sidebar button **"Script"** (after Worlds, before the separator)
- Create a new `#script-view` div (like `#story-view`, `#scenes-view`, etc.)
- When active, it shows the formatted screenplay in `.view-body`

**Rendering approach**:
- Use `formatFountainScene()` output (already exists) or equivalent
- Style with screenplay conventions: Courier-style font, scene headings bold, dialogue indented, dual dialogue side-by-side
- The dashboard already has fountain CSS classes (lines 657-747) — reuse them
- **Page-based layout** (like BF) is nice-to-have; a single scrollable document is acceptable for v1
- Title page rendered separately at top (if present)

**Header actions**:
- A **"Statistics" button** in `.view-header-actions` that opens the Statistics panel (see below)

**Data source**: `window.__SCREENPLAY_TEXT__` (already loaded by dashboard).

### Statistics Panel (Detail Panel)

**Purpose**: Show comprehensive screenplay analytics.

**Integration**:
- **NOT a sidebar tab** — opens as a detail panel (like entity panels)
- Opened from the Script view's header button
- Reuses `#detail-panel` structure (or creates a new panel div with same styling)
- **3 sub-groups**: Overview, Characters, Scenes (sidebar-navigated, like BF)

**Data to display** (grouped):

#### Overview Group
| Stat | Element ID | Source |
|------|-----------|--------|
| Pages (whole) | `lengthStats-pagesWhole` | `max(1, line_count / 52)` |
| Pages (fractional) | `lengthStats-pagesFractional` | Eighths remainder |
| Pages (printed) | `lengthStats-pagesReal` | Same as whole for v1 |
| Scenes | `lengthStats-scenes` | `len(properties.scenes)` |
| Words | `lengthStats-words` | `len(text.split())` |
| Characters | `lengthStats-characters` | `len(text)` |
| Characters (no spaces) | `lengthStats-characterswithoutwhitespace` | `len(re.sub(r'\s', '', text))` |
| Lines | `lengthStats-lines` | `text.count('\n')` |
| Lines (no spaces) | `lengthStats-lineswithoutwhitespace` | Count non-empty lines |
| Duration (total) | `durationStats-total` | `lengthAction + lengthDialogue` |
| Duration (action) | `durationStats-action` | `lengthAction` |
| Duration (dialogue) | `durationStats-dialogue` | `lengthDialogue` |
| Duration chart | `durationStats-lengthchart` | Line chart: action vs dialogue over lines |

**Duration summary text** (like BF): Generate a human-readable summary:
> "The screenplay is the length of a feature film. It is action-heavy (65% of the runtime)."

#### Characters Group
| Stat | Element ID | Source |
|------|-----------|--------|
| Character count | `characterStats-count` | `len(properties.characters)` |
| Monologues | `characterStats-monologues` | Count dialogues > 30s |
| Complexity | `characterStats-complexity` | Median readability (optional, omit in v1) |
| Character duration chart | `characterStats-lengthchart` | Per-character line chart |
| Character table | `characterStats-table` | Sortable table |

**Character table columns**: Name, Duration (seconds → HH:MM:SS), Lines (speaking parts), Words, Complexity (optional), Monologues

**Per-character data** (computed from tokens):
- `name`: character name
- `color`: hash-based HSL from name
- `speakingParts`: count of dialogue blocks
- `secondsSpoken`: sum of `time` for all dialogue tokens
- `wordsSpoken`: word count of all dialogue
- `monologues`: count of dialogues > 30s
- `averageComplexity`: optional

#### Scenes Group
| Stat | Element ID | Source |
|------|-----------|--------|
| Scene count | `sceneStats-count` | `len(properties.scenes)` |
| Location count | `locationStats-count` | `len(properties.locations)` |
| INT duration | `sceneprop-type_int` | Sum scene durations |
| EXT duration | `sceneprop-type_ext` | Sum scene durations |
| MIXED duration | `sceneprop-type_mixed` | Sum scene durations |
| DAWN duration | `sceneprop-time_dawn` | Sum scene durations |
| MORNING duration | `sceneprop-time_morning` | Sum scene durations |
| DAY duration | `sceneprop-time_day` | Sum scene durations |
| EVENING duration | `sceneprop-time_evening` | Sum scene durations |
| DUSK duration | `sceneprop-time_dusk` | Sum scene durations |
| NIGHT duration | `sceneprop-time_night` | Sum scene durations |
| Scene summary | `durationStats-scenesummary` | Human-readable text |
| Scene barcode chart | `sceneStats-timechart` | Colored bars by type/time |
| Location table | `locationStats-table` | Sortable table |

**Location table columns**: Name, Number of Scenes, Time of Day, INT/EXT

**Scene barcode chart**: Each scene is a colored bar. Color by INT/EXT/MIXED or by time-of-day. X-axis = line number, Y-axis = scene type/time.

---

## Naming Conventions

Match Better Fountain's stat field names exactly (they're already the de facto standard):

```javascript
// Top-level structure
{
  lengthStats: { words, characters, characterswithoutwhitespace, lines, lineswithoutwhitespace, pages, pagesreal, scenes },
  durationStats: { total, action, dialogue, durationBySceneProp, lengthchart_action, lengthchart_dialogue, characters, scenes, characternames, monologues },
  characterStats: { characters: [{name, color, speakingParts, secondsSpoken, averageComplexity, monologues, wordsSpoken}], complexity, characterCount, monologues },
  locationStats: { locationsCount, locations: [{name, color, scene_numbers, scene_lines, number_of_scenes, times_of_day, interior_exterior}] },
  structure: [...],
  pdfmap: "{...}"  // JSON string, optional
}
```

**Element IDs** (for the HTML):
- `lengthStats-words`, `lengthStats-characters`, `lengthStats-lines`, `lengthStats-scenes`, `lengthStats-pagesWhole`, `lengthStats-pagesFractional`, `lengthStats-pagesReal`, `lengthStats-characterswithoutwhitespace`, `lengthStats-lineswithoutwhitespace`
- `durationStats-total`, `durationStats-action`, `durationStats-dialogue`, `durationStats-summary`, `durationStats-lengthchart`, `durationStats-scenesummary`
- `characterStats-count`, `characterStats-monologues`, `characterStats-complexity`, `characterStats-lengthchart`, `characterStats-table`
- `sceneStats-count`, `locationStats-count`, `sceneStats-timechart`, `locationStats-table`
- `sceneprop-type_int`, `sceneprop-type_ext`, `sceneprop-type_mixed`
- `sceneprop-time_dawn`, `sceneprop-time_morning`, `sceneprop-time_day`, `sceneprop-time_evening`, `sceneprop-time_dusk`, `sceneprop-time_night`

---

## Technical Constraints

1. **Single HTML file** — Add to `src/dashboard/story-dashboard.html` (no build step)
2. **CDN libraries** — Can load D3.js and DataTables from CDN (like vis-network already is)
3. **Hermes conventions** — Use CSS variables, `data-hermes-send`, transparent background, app font
4. **Data loading** — The dashboard already loads `screenplay.md` via `window.__SCREENPLAY_TEXT__`. Parse it client-side (the parser is in Python, but the statistics can be computed from the raw text + a client-side tokenization, OR we can pre-compute stats server-side and embed them)
5. **No Python in the browser** — The statistics computation must happen either:
   - **Client-side**: Tokenize the Fountain text in JS (we can port the minimal tokenization needed)
   - **Server-side**: Pre-compute stats when loading the project, embed as JSON in the HTML
   - **Hybrid**: Load `screenplay.md`, compute stats in JS, render

**Recommended approach**: Client-side computation. The dashboard already loads `screenplay.md`. Add a JS function that:
1. Reads the Fountain text
2. Computes all statistics (word count, line count, duration, per-character, per-scene)
3. Renders the Script tab (formatted HTML) and Statistics tab (charts + tables)

This keeps the architecture simple — no server round-trip needed.

---

## What to Hand the UI Agent

This document provides:
1. **Reference** — How Better Fountain does it (what to emulate)
2. **Data mapping** — What our parser already provides vs. what needs computing
3. **Naming conventions** — Exact field names and element IDs to use
4. **Layout structure** — Script tab (main view) + Statistics panel (detail panel with 3 sub-groups)
5. **Technical constraints** — Single HTML, CDN libs, Hermes conventions, client-side computation
6. **Gaps identified** — What stats need new computation logic
7. **Existing patterns** — The dashboard already has screenplay formatting, detail panel, and entity panels to follow

The UI agent should produce:
- Updated `src/dashboard/story-dashboard.html` with:
  - New "Script" sidebar button
  - New `#script-view` div (formatted screenplay)
  - New `#statistics-panel` detail panel (or reuse `#detail-panel`)
  - Embedded CSS (using Hermes variables, reusing existing fountain classes)
  - Embedded JS for:
    - Fountain tokenization (minimal, for statistics)
    - Statistics computation
    - Script rendering (formatted screenplay)
    - Charts (D3.js) and tables (DataTables)
- "Ask Hermes" buttons where appropriate (e.g., "Analyze character arc", "Check pacing")

---

## Out of Scope (For Later)

- PDF page map (requires PDF generation)
- Readability scores (requires `readability-scores` Python port)
- Live sync with editor (we don't have an editor)
- Export to PDF/HTML
- Scene content editing
- Collaborative features

---

## Success Criteria

- [ ] Script tab renders the full screenplay with proper formatting
- [ ] Statistics panel opens from Script tab header (not sidebar)
- [ ] Statistics panel shows Overview, Characters, Scenes sub-groups
- [ ] All stats match what Better Fountain computes (where data is available)
- [ ] Charts render correctly (line chart, barcode chart)
- [ ] Tables are sortable and filterable
- [ ] Responsive in narrow preview pane (~400-600px)
- [ ] Uses Hermes CSS variables for theming
- [ ] No build step — single HTML file with CDN libs
- [ ] Reuses existing fountain CSS classes (no duplication)
- [ ] Reuses existing detail panel pattern (slide-in from right)
