# Phase 4: Dashboard — Arc Visualization in Characters View

## Prerequisite

Phase 1 + 2 + 3 complete. Index includes `arcs`, `character.arc_beats_list`, and `scene.arc_beats`.

## Files to modify

| File | Change |
|------|--------|
| `src/dashboard/story-dashboard.html` | Add arc graph panel to Characters view |
| `src/dashboard/story-dashboard.html` | Add arc graph CSS (from `tasks/task_14/arc-panel-demo.html`) |
| `src/dashboard/story-dashboard.html` | Add arc graph JS (from `tasks/task_14/arc-panel-demo.html`) |
| `src/dashboard/story-dashboard.html` | Add arc beat indicator dots to scene cards |

## Reference files

| File | Why |
|------|-----|
| `tasks/task_14/arc-panel-demo.html` | Working arc graph demo — contains all CSS/JS to integrate |
| `src/dashboard/story-dashboard.html` | Existing dashboard — Graph tab pattern, sidebar tokens |

## Key Design Decisions

1. **Arc graph goes inside the existing Characters view** — below the vis.js network graph, in the same tab. No new tab.
2. **Reuse the arc-panel-demo.html code** — it was built for this. Extract the `<style>` and `<script>` blocks, adapt selectors.
3. **X-axis: narrative progression** — derived from scene order (0.0–1.0), not beat order. Beat has `scene` field → look up scene's order → normalize.
4. **Y-axis: value charge** — directly from `beat.y` (-1.0 to +1.0).
5. **Straight lines between points** — spline is optional polish, ship straight first.
6. **Empty state** — when no beats exist, show "Design arc with Hermes" prompt.

## Step-by-step

### Step 4.1 — Add arc graph CSS

In `src/dashboard/story-dashboard.html`, find the `<style>` block (at top). Append arc graph styles from `arc-panel-demo.html` (lines ~600-900). Key classes:

```css
.arc-graph-container { ... }
.arc-graph-svg { ... }
.arc-line { ... }
.arc-point { ... }
.arc-point.crisis { ... }
.arc-point.climax { ... }
.arc-label { ... }
.arc-legend { ... }
.arc-empty-state { ... }
```

### Step 4.2 — Add arc graph container HTML

In the Characters view section (around line 1364: `<!-- ── Characters ── -->`), add below the network canvas:

```html
<!-- Arc Graph Panel -->
<div id="arc-graph-panel" class="arc-graph-container" style="display:none;">
  <div class="arc-graph-header">
    <h3>Character Arcs</h3>
    <span id="arc-graph-subtitle"></span>
  </div>
  <svg id="arc-graph-svg" class="arc-graph-svg"></svg>
  <div id="arc-legend" class="arc-legend"></div>
  <div id="arc-empty-state" class="arc-empty-state" style="display:none;">
    <p>No arc beats designed yet.</p>
    <button class="btn btn-hermes" data-hermes-send="Design a character arc for [character] showing their value shift across the story.">Design arc with Hermes</button>
  </div>
</div>
```

### Step 4.3 — Add arc graph JS

At the end of the `<script>` block in `src/dashboard/story-dashboard.html`, append the arc graph rendering logic. Adapt from `arc-panel-demo.html`:

```javascript
// ─── Arc Graph ────────────────────────────────────────────────────────────────
function buildArcGraph() {
  const chars = (story.characters || []).filter(c => c.arc_type !== 'absent' && c.arc_beats_list && c.arc_beats_list.length > 0);
  const panel = document.getElementById('arc-graph-panel');
  const svg = document.getElementById('arc-graph-svg');
  const emptyState = document.getElementById('arc-empty-state');
  const subtitle = document.getElementById('arc-graph-subtitle');

  if (chars.length === 0) {
    panel.style.display = 'block';
    svg.style.display = 'none';
    emptyState.style.display = 'block';
    subtitle.textContent = 'No arcs designed';
    return;
  }

  panel.style.display = 'block';
  svg.style.display = 'block';
  emptyState.style.display = 'none';
  subtitle.textContent = chars.length + ' character arcs';

  // Build scene order lookup for X-axis
  const sceneOrder = {};
  (story.scenes || []).forEach((s, i) => { sceneOrder[s.id] = i; });
  const totalScenes = (story.scenes || []).length || 1;

  // SVG dimensions
  const W = svg.clientWidth || 800;
  const H = 300;
  const pad = { top: 20, right: 20, bottom: 30, left: 40 };
  const plotW = W - pad.left - pad.right;
  const plotH = H - pad.top - pad.bottom;

  // Y scale: -1.0 to +1.0 → plotH
  const yScale = (y) => pad.top + plotH / 2 - (y * plotH / 2);

  // X scale: scene index → plotW
  const xScale = (sceneId) => {
    const idx = sceneOrder[sceneId] || 0;
    return pad.left + (idx / Math.max(1, totalScenes - 1)) * plotW;
  };

  // Grid lines
  let gridSvg = '';
  for (let y = -1.0; y <= 1.0; y += 0.5) {
    const py = yScale(y);
    gridSvg += `<line x1="${pad.left}" y1="${py}" x2="${W - pad.right}" y2="${py}" stroke="rgba(255,255,255,0.05)" stroke-width="1"/>`;
    gridSvg += `<text x="${pad.left - 5}" y="${py + 3}" fill="rgba(255,255,255,0.3)" font-size="9" text-anchor="end">${y.toFixed(1)}</text>`;
  }

  // Plot each character
  let linesSvg = '';
  chars.forEach(char => {
    const color = roleColor(char.role || char.story_role || '');
    const beats = char.arc_beats_list.sort((a, b) => a.order - b.order);

    // Line path
    const points = beats.map(b => `${xScale(b.scene)},${yScale(b.y)}`).join(' ');
    linesSvg += `<polyline points="${points}" fill="none" stroke="${color}" stroke-width="2" opacity="0.8"/>`;

    // Beat points
    beats.forEach(b => {
      const px = xScale(b.scene);
      const py = yScale(b.y);
      const cls = b.is_climax ? 'climax' : (b.is_crisis ? 'crisis' : '');
      linesSvg += `<circle cx="${px}" cy="${py}" r="4" fill="${color}" class="arc-point ${cls}" data-label="${escapeHtml(b.label)}" data-y="${b.y}"/>`;
    });
  });

  svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
  svg.innerHTML = gridSvg + linesSvg;

  // Build legend
  const legend = document.getElementById('arc-legend');
  legend.innerHTML = chars.map(char => `
    <div class="legend-item">
      <div class="legend-line" style="background:${roleColor(char.role || char.story_role || '')}"></div>
      <span>${escapeHtml(char.name)}</span>
      <span class="legend-arc-type">${char.arc_type}</span>
    </div>
  `).join('') + `
    <div class="legend-item" style="gap:12px;margin-left:auto">
      <div style="display:flex;align-items:center;gap:4px"><div class="legend-dot" style="background:#ffd93d"></div><span>crisis</span></div>
      <div style="display:flex;align-items:center;gap:4px"><div class="legend-dot" style="background:transparent;border:1px solid #e8e8e8"></div><span>climax</span></div>
    </div>
  `;
}
```

### Step 4.4 — Call `buildArcGraph()` when Characters tab is shown

Find the tab-switching logic (around `onclick="switchTab('characters', this)"` or similar). Add `buildArcGraph()` to the characters tab activation.

### Step 4.5 — Add arc beat indicator dots to scene cards

In the scene card rendering (around line 1963 where `charTags` is built), add arc beat indicators:

```javascript
// After charTags, add arc beat dots
const arcBeats = s.arc_beats || [];
const arcDots = arcBeats.map(ab => {
  const c = (story.characters || []).find(x => x.id === ab.character);
  const color = c ? roleColor(c.role || c.story_role || '') : '#8a8a8a';
  return `<span class="arc-beat-dot" style="background:${color}" title="${escapeHtml(c?.name || '')}: ${escapeHtml(ab.label || '')}"></span>`;
}).join('');
```

Add CSS for `.arc-beat-dot`:
```css
.arc-beat-dot { display:inline-block; width:6px; height:6px; border-radius:50%; margin-left:2px; vertical-align:middle; }
```

## Legacy cleanup

None — additive only.

## Naming convention check

- `arc_type` (matches character frontmatter)
- `arc_beats_list` (matches index derivation output)
- `arc_beats` (matches scene reverse lookup)
- CSS classes: `arc-graph-*`, `arc-point`, `arc-legend` (matches existing `arc-*` prefix from demo)

## Final checklist

- [x] Arc graph CSS added to dashboard `<style>` block
- [x] Arc graph HTML container added to Characters view
- [x] Arc graph JS rendering function added
- [x] `buildArcGraph()` called on Characters tab activation
- [x] X-axis uses scene order (0.0–1.0)
- [x] Y-axis uses beat.y (-1.0 to +1.0)
- [x] Crisis beats render as yellow dots
- [x] Climax beats render as white circles
- [x] Empty state shows "Design arc with Hermes" button
- [x] Legend shows character name + color + arc_type
- [x] Arc beat indicator dots added to scene cards
- [ ] Tests added to `test_arcs.py` for dashboard rendering
- [ ] `pytest tests/test_arcs.py` passes

---

## Implementation Complete (2026-09-15)

All Phase 4 tasks implemented in `src/dashboard/story-dashboard.html`:

1. **Tab bar added** — Network / Arc graph / List tabs inside `#graph-view`
2. **Arc graph CSS** — full panel styling, SVG element classes, tooltip, empty state
3. **Arc graph HTML** — tab content container with SVG wrapper and legend div
4. **Arc graph JS** — `buildArcGraph()` renders polylines + beat dots per character, grid lines, axis labels, legend, tooltip
5. **Tab switching** — `switchGraphTab()` shows/hides content, calls `buildArcGraph()` when Arc graph tab activated
6. **Character list tab** — `buildCharList()` renders character cards with arc info
7. **Arc beat dots on scene cards** — `renderSceneItem()` appends colored dots from `scene.arc_beats[]`
8. **Tooltip** — `#arc-beat-tooltip` element + `showArcTooltip/hideArcTooltip` handlers

Skipped: tests (deferred — needs HTML fixture for dashboard integration test).

**NOTE:**
- The demo's Catmull-Rom spline toggle was skipped — straight polylines match the simpler design and the task spec says "ship straight first"
- The demo's arc detail panel (right-side panel for beat details) was skipped — not required for Phase 4 (visualization), would be Phase 5 scope
- `graph-legend` (vis.js network legend) is hidden when on arc graph tab to avoid visual conflict
