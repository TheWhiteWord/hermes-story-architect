# Arc Visualization — UI Specialist Brief

> **Deliverable**: Character arc graph panel in the Story dashboard.
> **Location**: Extend existing Characters view (`src/dashboard/story-dashboard.html`).
> **Reference**: `docs/research/arc-visualization-example.html` (working mockup).

---

## 1. What We're Doing

We're adding a **character arc visualization** to the Story dashboard. It renders each character's value journey as a line graph across the narrative timeline, showing how their internal value changes through the story.

**Key concepts**:
- **Arc**: A character's value journey (e.g., Trust → Betrayal)
- **Beat**: A point on the arc where the value shifts (encodes Action/Gap/Choice/Shift)
- **Value charge**: Numeric -1.0 to +1.0 derived from the linguistic shift
- **Beats are stored individually**: `arcs/{character}/{beat_id}.md` — one file per beat

---

## 2. Data Available (from `window.__STORY_DATA__`)

### In `index.yaml` → `characters[]`

Each character entry gains:

```yaml
characters:
  - id: mara
    name: "Mara Voss"
    story_role: Protagonist
    # NEW FIELDS:
    arc_type: negative          # positive | negative | flat | ironic | absent
    arc_value: "Trust"          # the value that changes
    arc_value_at_open: positive # starting charge
    arc_value_at_close: ironic  # ending charge
    arc_complete: true          # has the arc been designed?
    arc_beat_count: 5           # number of beats
    arc_beats_list:             # lightweight — NO prose
      - id: "1"
        label: "Naïve Trust"
        scene: central-room-day
        y: 0.8
        order: 1
      - id: "2"
        label: "First Doubt"
        scene: the-garden
        y: 0.3
        order: 2
      - id: "3"
        label: "Betrayal"
        scene: central-room-night
        y: -0.4
        order: 3
      # ...
```

### In `index.yaml` → `scenes[]`

Each scene gains:

```yaml
scenes:
  - id: the-garden
    # ... existing fields ...
    arc_beats:
      - char: mara
        beat_id: "2"
```

### Beat file content (loaded on demand)

When a beat is clicked, load via `story_retrieve arcs/{character}/{beat_id}`:

```yaml
---
id: "2"
character: mara
scene: the-garden
label: "First Doubt"
action: "Mara asks Oak directly about the files"
gap: "Oak lies smoothly — she realizes he's been lying for months"
choice: "She nods, says nothing, files the report herself"
shift: "positive → mixed"
y: 0.3
order: 2
is_crisis: false
is_climax: false
---

## Action
Why this action was chosen — what the character tries and why this move in the argument.

## Gap
Why this unexpected reaction — the collision between expectation and reality that forces change.

## Choice
Why the character makes this choice under pressure — what it reveals about their true nature.

## Shift
Why this value shift follows — how the value charge changes as a result (e.g., positive → contrary).

## Development Log
- v1: Initial beat
- v2: Refined gap description
```

**Important**: Each body section (`## Action`, `## Gap`, `## Choice`, `## Shift`) targets the reasoning behind its corresponding frontmatter field. The specialist may integrate these into the visualization in ways not explicitly described here — for example, showing the gap description on hover, or using the choice text as a beat tooltip, or rendering the shift as a color gradient along the line.

---

## 3. What the Visualization Should Do

### Arc Graph Panel

Render inside the **Characters view** (not a new sidebar tab). Place it as an extended panel — either below the character network graph or as a toggleable section.

**Required elements**:

| Element | Description |
|---------|-------------|
| **Multi-line graph** | Each character with `arc_type ≠ absent` gets a colored line |
| **X-axis** | Narrative progression (0.0 → 1.0). Map each beat's scene order to position. |
| **Y-axis** | Value charge (-1.0 → +1.0). Use `beat.y` directly. |
| **Beat points** | Dots at each `(x, y)` position. Color matches character's role color. |
| **Crisis beats** | Yellow dot (`#ffd93d`), larger radius |
| **Climax beats** | White circle with colored border, larger radius |
| **Act boundaries** | Vertical dashed lines at act divisions |
| **Hover/click beat** | Show label + value tooltip; click loads beat detail in side panel |
| **Legend** | Character name + color pip + arc_type indicator |

### Sanity Check Warnings

Display warnings when:
- All `|Δy| < 0.2` → "Arc is flat — nothing happens"
- Any `|Δy| > 0.8` → "Single beat is melodramatic — consider splitting"
- Two arcs never diverge → "Characters may be redundant"

### Empty State

When no characters have arcs designed:
```
No character arcs designed yet.
[Design arc with Hermes] → sends prompt to Hermes
```

### Scene Beat Indicators

In the **Scenes view**, each scene card gains small colored dots in its meta row for each `arc_beats` entry. Color follows character role color.

---

## 4. Existing Patterns to Follow

### Panel Pattern (like `#detail-panel`)

The arc detail panel should slide in from the right, matching the existing `#detail-panel`:

```html
<aside id="arc-panel" class="detail-panel">
  <div class="panel-header">...</div>
  <div class="panel-body">
    <!-- Beat sections render here -->
  </div>
</aside>
```

### Graph Rendering Pattern (like `#stats-panel`)

Use SVG for the arc graph (not canvas). The existing code uses D3 for charts and vis-network for the character web. For arcs, use **SVG with straight lines between points** (spline interpolation optional if time permits).

### Color Tokens (from existing CSS)

```css
--foreground: #e8e8e8;
--muted-foreground: #8a8a8a;
--accent: #7b9cf0;
--border: rgba(255,255,255,0.1);
--card: rgba(255,255,255,0.04);
--panel-bg: #181818;

/* Role colors — reuse for arc lines */
--role-protagonist: #7b9cf0;
--role-antagonist: #e07070;
--role-mentor: #b07be0;
--role-rival: #e0a86b;
--role-supporting: #6bbfb0;
```

### Font Sizes

```css
--font-size-xs: 10px;
--font-size-sm: 11px;
--font-size-base: 13px;
--font-size-lg: 15px;
```

### CSS Classes to Reuse

| Class | Use |
|-------|-----|
| `.view-header` | Panel header |
| `.view-title` | Panel title |
| `.panel-section-label` | Section labels |
| `.panel-text` | Body text |
| `.panel-muted` | Secondary text |
| `.tag` / `.tag-char` | Scene beat indicators |
| `.empty-state` | Empty state |
| `.btn` / `.btn-hermes` | Action buttons |
| `.legend-item` / `.legend-dot` | Graph legend |

### JS Pattern

Follow existing patterns in `story-dashboard.js`:
- `buildXxxView()` — render a view
- `showXxxPanel(entity)` — populate and open detail panel
- `escapeHtml(str)` — safe rendering
- Data comes from `window.__STORY_DATA__` (already normalized)

---

## 5. Implementation Guidance

### File to modify

`src/dashboard/story-dashboard.html` — single file contains all CSS + JS.

### CSS continuity

**Before writing new styles**, read the existing CSS in `story-dashboard.html` to understand:
- How panels slide in (transition patterns)
- How tags/chips are styled
- How the detail panel responds to screen width
- How the stats panel tabs work

Then add your arc-specific styles in a new section at the end of `<style>`:
```css
/* ─── Arc Panel ────────────────────────────────────────────── */
```

### CSS additions

Add a new section in `<style>`:
```css
/* ─── Arc Panel ────────────────────────────────────────────── */
.arc-panel { ... }
.arc-graph { ... }
.arc-line { ... }
.arc-beat-dot { ... }
.arc-beat-dot.crisis { ... }
.arc-beat-dot.climax { ... }
.arc-axis-label { ... }
.arc-act-line { ... }
.arc-legend { ... }
.arc-warning { ... }
.arc-scene-indicator { ... }
```

### JS additions

```javascript
// ─── Arc Graph ────────────────────────────────────────────────
function buildArcGraph() {
  // 1. Find characters with arc_type !== "absent" and arc_beats_list.length > 0
  // 2. Render SVG with axes, grid lines, act boundaries
  // 3. Plot each character's arc as polyline through beat points
  // 4. Plot crisis/climax beats with special markers
  // 5. Add legend
  // 6. Add empty state if no arcs
}

function showArcBeatPanel(characterId, beatId) {
  // 1. Load beat note via fetch (or use pre-loaded __SECTIONS__ if available)
  // 2. Populate panel with Action/Gap/Choice/Shift sections
  // 3. Open panel
}

function renderArcSceneIndicators() {
  // 1. For each scene, add colored dots for arc_beats[]
  // 2. Place in scene-meta row alongside existing tags
}
```

### SVG Structure

```svg
<svg viewBox="0 0 800 400" class="arc-graph">
  <!-- Grid lines -->
  <line class="grid-line" ... />
  <!-- Act boundaries -->
  <line class="act-line" ... />
  <!-- Arc lines (one per character) -->
  <polyline class="arc-line" style="stroke:#7b9cf0" points="..." />
  <!-- Beat dots -->
  <circle class="arc-beat-dot" cx="..." cy="..." r="5" />
  <!-- Labels -->
  <text class="beat-label">First Doubt</text>
  <!-- Y-axis labels -->
  <text class="axis-label">+1.0</text>
</svg>
```

---

## 6. Constraints

- **Single file**: All CSS and JS in `story-dashboard.html` — no external dependencies beyond what's already loaded (vis-network, D3, js-yaml)
- **No build step**: Pure HTML/CSS/JS that runs in the Hermes preview pane (Electron)
- **Reusable**: The arc graph should be a reusable component (function that takes a container and renders)
- **Responsive**: Graph should scale to container width (use `viewBox` + `width: 100%`)
- **Performance**: 40 characters × 20 beats = 800 points max. SVG handles this fine.

---

## 7. Deliverables

1. **Arc graph** in Characters view (with role-colored lines, beat points, act boundaries, legend)
2. **Beat detail panel** (slide-in from right, shows Action/Gap/Choice/Shift/Development Log)
3. **Scene beat indicators** (small colored dots in Scenes view meta row)
4. **Sanity check warnings** (flat arc, melodramatic beat)
5. **Empty state** with "Design arc with Hermes" prompt
6. **Act boundary lines** derived from `story.acts[]` and `story.sequences[]`

---

## 8. Reference Files

| File | What to read |
|------|-------------|
| `src/dashboard/story-dashboard.html` | Existing patterns, CSS tokens, JS structure |
| `src/dashboard/screenplay.css` | Fountain styling (for reference) |
| `docs/research/arc-visualization-example.html` | Working SVG mockup |
| `skills/story-theory/references/values.md` | Theory grounding |
| `tools/story_dashboard.py` | Backend injection logic (no changes needed) |

---

## 9. Open for Your Decision

These are creative/UX decisions we leave to you:

- **Graph placement**: Below network graph or toggleable tab?
- **Line style**: Straight lines or smooth spline?
- **Beat point sizing**: Fixed or scaled by conflict level?
- **Panel width**: Match `#detail-panel` (320px) or wider?
- **Color for "mixed" charge**: Gradient along line or solid?
- **Animation**: Animate line drawing on load?

Make it look good. The mockup in `arc-visualization-example.html` is a starting point, not a constraint.

## 9. Open for Your Decision

These are creative/UX decisions we leave to you:

- **Graph placement**: Below network graph or toggleable tab?
- **Line style**: Straight lines or smooth spline?
- **Beat point sizing**: Fixed or scaled by conflict level?
- **Panel width**: Match `#detail-panel` (320px) or wider?
- **Color for "mixed" charge**: Gradient along line or solid?
- **Animation**: Animate line drawing on load?

Make it look good. The mockup in `arc-visualization-example.html` is a starting point, not a constraint.
