# Dashboard inventory
Every claim here is either a command's real output or a `path:line` reference . Where a fact is **not** established it is written `UNVERIFIED`, never as an assumption.

Nothing in this document changes behaviour. 

## INDEX

This is a index of all the files containing the fact sheet : what the dashboard is today, file by file, plus a golden baseline the parity tests compare against.
For each file you are provided here with:
- `###` Title
- FILE LINK
- SHORT DESCRIPTION
- SECTIONS BREAKDOWN

Note: All files include a Final brief from the session they were created in (with few exceptions), with subsections `### Verification performed`, `### What the section records` , `### Findings that change later phases` (not added here to the index).

### "Views and tabs"
FILE: `tasks/task_35/docs/0.4.1 — Views and tabs.md`
SHORT DESCRIPTION:
Nine top-level views (container id, nav label, data-view) plus three sub-view switching systems (graph tabs, values toolbar, statistics groups) and the detail panel as a tab strip and the Memory dialog as a modal. Ends with a switching-summary table .

SECTIONS:

```
## 0.4.1 — Views and tabs
### Top-level views — nine
### Sub-views — three switching systems besides the top level
### The detail panel — a tab strip, not a view
### The Memory dialog — a modal, not a view
### Views with no JS of their own
### Dead state in `navigation.js` (recorded, not fixed here)
```
---

### "Each JS file's responsibility"
FILE: `tasks/task_35/docs/0.4.2 — Each JS file's responsibility.md`
SHORT DESCRIPTION:
All 23 JS files in load order with a one-line responsibility, a per-file table of the DASH.* members each defines / DOM ids it queries / pure-or-not, and seven mechanical invariants a port must reproduce (no imports, JS_ORDER, boot re-entrancy, nine views, two pure modules, payload doors).

SECTIONS:

```
## 0.4.2 — Each JS file's responsibility
### Module surface (what each file defines and what it reaches for)
```
---

### "Global state"
FILE: `tasks/task_35/docs/0.4.3 — Global state.md`
SHORT DESCRIPTION:
Three tiers of state the dashboard keeps between calls: the DASH.* surface other modules reach (who writes and reads each member, the dead ones, the five cross-module shared members), module-scoped values that are file-private, and the four injected payloads. Also covers the four one-shot guards and the no-client-persistence finding.

SECTIONS:

```
## 0.4.3 — Global state
### Tier 1 — the `DASH.*` surface
### Tier 2 — module-scoped (not on `DASH`, unreachable from a port's other view)
### Tier 3 — injected payloads
```

---

### "Exact JSON shapes"
FILE: `tasks/task_35/docs/0.4.4 — Exact JSON shapes.md`
SHORT DESCRIPTION:
The four payloads __STORY_DATA__, __SECTIONS__, __SCREENPLAY_STATS__, __STRUCTURAL_STATS__ with key-by-key shape, per-type key sets, nested shapes, the two truthiness gates, and the defect that plot beat-field names are not pluralised names. Includes the reproduction command and the three keys that are never injected.

SECTIONS:

```
## 0.4.4 — Exact JSON shapes
### 0.4.4.0 — The six keys of `get_dashboard_data`
### 0.4.4.1 — `__STORY_DATA__` = `data['story_data']`
### 0.4.4.2 — `__SECTIONS__` = `data['sections']`
### 0.4.4.3 — `__SCREENPLAY_STATS__`
### 0.4.4.4 — `__STRUCTURAL_STATS__` = `data['structural_stats']`
### 0.4.4.4a — Defect: the plot's beat fields are keyed by *both* names, and the JS's plural rule is wrong for three of the six
### 0.4.4.5 — Injection order, and the two truthiness gates
### 0.4.4.6 — Reproduction note
```

---

### "DOM structure per view"
FILE: `tasks/task_35/docs/0.4.5 — DOM structure per view.md`
SHORT DESCRIPTION:
For each of the nine views: container id and class, the DOM ids the JS fills and how (textContent vs innerHTML), the markup , the CSS classes expected, and the empty state. Every element is cited to its emitting JS file.

SECTIONS:

```
## 0.4.5 — DOM structure per view
### 1. Story view — `views/story.js` (`buildStoryView`, line 3)
### 2. Graph view — `graph/network.js` (`buildGraphView`, line 3)
### 3. Scenes view — `views/scenes.js` (`buildScenesView`, line 5)
### 4. Locations view — `views/locations.js` (`buildLocationsView`, line 3)
### 5. Plots view — `views/plots.js` (`buildPlotsView`, line 16)
### 6. Relationships view — `views/relationships.js` (`buildRelationshipsView`, line 3)
### 7. Worlds view — `views/worlds.js` (`buildWorldsView`, line 3)
### 8. Values view — `graph/value-graph.js` (`buildValuesView`, line 563)
### 9. Script view — `script-view.js` (`buildScriptView`, line 5; `DASH.boot()` at line 106)
```

---

### "External resources"
FILE: `tasks/task_35/docs/0.4.6 — External resources.md`
SHORT DESCRIPTION:
The three cdnjs scripts in index.html with the exact line and the consuming JS file each: vis-network, js-yaml, d3. States which are hard runtime dependencies, which exist only for the manual-YAML path.

SECTIONS:

```
## 0.4.6 — External resources
```

---

### "Global CSS selectors and viewport assumptions"
FILE: `tasks/task_35/docs/0.4.7 — Global CSS selectors and viewport assumptions.md`
SHORT DESCRIPTION:
Every global CSS selector (universal reset, :root with 29 custom properties, html/body, #app at 100vh, .view), the second :root block in statistics.css, viewport-height and viewport-width usage, innerWidth/innerHeight tooltip clamping only, and screenplay.css's absence of global selectors — plus what the scoper must preserve.

SECTIONS:

```
## 0.4.7 — Global CSS selectors and viewport assumptions
### Global selectors
### Viewport-height usage (`100vh`)
### Viewport-width usage (`100vw`)
### `window.innerWidth` / `window.innerHeight` — tooltip clamping only (not layout)
### `screenplay.css` — no global selectors
```

---

### "Inline handlers, `innerHTML`, HTML-string building"
FILE: `tasks/task_35/docs/0.4.8 — Inline handlers, innerHTML, HTML-string building.md`
SHORT DESCRIPTION:
Census of the 35 inline handlers in index.html (31 onclick, 1 oninput, 3 onchange) with the DASH function each calls; the 61 innerHTML/insertAdjacentHTML sites per file; the 4 property-assigned handlers; the escaping census (8 of 23 files escape; statistics.js escapes text but not attributes); and the 5 raw interpolations that reach the DOM unescaped.

 SECTIONS:

```
## 0.4.8 — Inline handlers, `innerHTML`, HTML-string building
### 0.4.8.1 — Inline handlers in `index.html` — 35
### 0.4.8.2 — `innerHTML` / `insertAdjacentHTML` census — 61
### 0.4.8.3 — Property-assigned handlers — 4
### 0.4.8.4 — Escaping census
### 0.4.8.5 — Raw interpolations that reach the DOM
```

---

### "All `data-hermes-send` sites"
FILE: `tasks/task_35/docs/0.4.9 — All data-hermes-send sites.md`
SHORT DESCRIPTION:
All 12 data-hermes-send sites with source line and verbatim prompt text. Records the two DASH.story template-literal artifacts, the DASH.story-section-title find/replace defect, and the data-ent protocol (7 sites) as a separate data protocol.

SECTIONS:

```
## 0.4.9 — All `data-hermes-send` sites
```

---

### "Dependency table"
FILE: `tasks/task_35/docs/0.4.10 — Dependency table.md`
SHORT DESCRIPTION:
One row per unit of Phase 3's 14-unit order (3.0) with per-unit dependencies: what each unit calls, what calls it, and whether anything from a later unit flows back. Includes answers to the required questions.

SECTIONS:

```
## 0.4.10 — Dependency table (the Phase 3 order is checked against this)
### Answers to questions
```

---