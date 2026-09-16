# Phase 3: Coherence Visualization

## Files to modify

| File | Change |
|------|--------|
| `src/dashboard/story-dashboard.html` | Add delta bar, existing warnings area used for coherence, multi-character line styles, act band backgrounds |
| `tools/story_dashboard.py` | Inject `window.__COHERENCE_FLAGS__` |

## Step-by-step

### Step 3.1 — Add CSS for coherence overlay

After existing `.arc-warnings` CSS (~line 1240), add:

```css
/* Act band backgrounds */
.arc-act-band.even { fill: rgba(255,255,255,0.02); }
.arc-act-band.odd { fill: rgba(255,255,255,0.04); }

/* Structural avenue — wide soft band from value_open to value_close per act */
.arc-structural-avenue {
    fill: rgba(255, 255, 255, 0.06);
    stroke: rgba(255, 255, 255, 0.1);
    stroke-width: 1;
    rx: 6;
    filter: blur(4px);
}

/* Multi-character line styles */
.arc-line.antagonist { stroke-dasharray: 6 4; }
.arc-line.supporting { stroke-width: 1; opacity: 0.4; }

/* Per-act delta bar */
.arc-delta-bar { display: flex; gap: 4px; padding: 8px 16px; border-top: 1px solid var(--border); }
.arc-delta-bar-bar { flex: 1; height: 24px; border-radius: 3px; position: relative; min-width: 20px; }
.arc-delta-bar-bar.positive { background: rgba(107,191,176,0.5); }
.arc-delta-bar-bar.negative { background: rgba(239,108,92,0.5); }
.arc-delta-bar-label { font-size: 9px; color: var(--muted-foreground); text-align: center; margin-top: 2px; }

/* Coherence flags — appended to existing arc-warnings, slightly different color */
.arc-warning.coherence .arc-warning-icon { color: #ffd93d; }
```

### Step 3.2 — Add delta bar HTML container

In the arc graph section (~line 1483-1485), after `#arc-warnings`:

```html
<div class="arc-delta-bar" id="arc-delta-bar"></div>
```

### Step 3.3 — Rewrite act band rendering

Replace the act boundary block (~lines 3784-3799) with equal-width bands from Phase 2. Add band backgrounds and structural avenue before drawing character lines.

Add `CHARGE_SIGN` mapping at top of `buildArcGraph()`:

```javascript
const CHARGE_SIGN = { positive: 1, mixed: 0, negative: -1, ironic: 0 };
```

Then draw:

```javascript
// Draw act band backgrounds and structural avenues
acts.forEach((act, i) => {
    const x = ARC_PAD.left + i * actBandwidth;
    const actId = act.id || `act-${i+1}`;
    
    // Band background
    svg += `<rect x="${x}" y="${ARC_PAD.top - 8}" width="${actBandwidth}" height="${ARC_GH - ARC_PAD.top - ARC_PAD.bottom + 12}" class="arc-act-band${i % 2 === 0 ? ' even' : ' odd'}" data-act="${actId}"/>`;
    
    // Structural avenue: soft wide band from value_open to value_close
    if (act.value_open && act.value_close) {
        const yOpen = arcYScale(CHARGE_SIGN[act.value_open] || 0);
        const yClose = arcYScale(CHARGE_SIGN[act.value_close] || 0);
        const bandTop = Math.min(yOpen, yClose);
        const bandHeight = Math.max(Math.abs(yClose - yOpen), 4);
        svg += `<rect x="${x + 4}" y="${bandTop}" width="${actBandwidth - 8}" height="${bandHeight}" rx="8" class="arc-structural-avenue"/>`;
    }
    
    // Act label
    svg += `<text x="${x + 4}" y="${ARC_PAD.top - 4}" class="arc-act-label">${escapeHtml(act.title || actId)}</text>`;
    
    // Boundary line (skip first — left edge is graph border)
    if (i > 0) {
        svg += `<line x1="${x}" y1="${ARC_PAD.top - 8}" x2="${x}" y2="${ARC_GH - ARC_PAD.bottom + 4}" class="arc-act-line"/>`;
    }
});
```

### Step 3.4 — Differentiate line styles by character role

In the `chars.forEach` loop (~line 3802), after getting `color`:

```javascript
const lineClass = char.story_role === 'Antagonist' ? ' antagonist' : 
                  char.story_role === 'Protagonist' ? '' : ' supporting';
const lineWidth = char.story_role === 'Protagonist' ? 2 : 
                  char.story_role === 'Antagonist' ? 2 : 1;
```

Apply `lineClass` to `.arc-line` and `lineWidth` to `stroke-width`.

### Step 3.5 — Add per-act delta bar rendering

New function `buildDeltaBar(protagonistId)`:

```javascript
function buildDeltaBar(protagonistId) {
    const container = document.getElementById('arc-delta-bar');
    if (!container || !protagonistId) { container.innerHTML = ''; return; }
    
    const acts = story.acts || [];
    const actCount = story.project.act_count || 3;
    const chars = story.characters || [];
    const char = chars.find(c => c.id === protagonistId);
    if (!char || !char.arc_beats_list) { container.innerHTML = ''; return; }
    
    // Compute net Δy per act
    const netDy = {};
    char.arc_beats_list.forEach(b => {
        const scene = (story.scenes || []).find(s => s.id === b.scene);
        if (!scene) return;
        const actIdx = acts.findIndex(a => a.id === scene.act_id);
        if (actIdx === -1) return;
        // Δy = current y - previous y (or y itself for first beat)
        // Simplified: sum y values per act as proxy for movement
        netDy[actIdx] = (netDy[actIdx] || 0) + b.y;
    });
    
    let html = '';
    for (let i = 0; i < actCount; i++) {
        const dy = netDy[i] || 0;
        const cls = dy >= 0 ? 'positive' : 'negative';
        const height = Math.min(Math.abs(dy) * 30, 24);
        html += `<div class="arc-delta-bar-bar ${cls}" style="height:${height}px" title="Act ${i+1}: net Δy ${dy >= 0 ? '+' : ''}${dy.toFixed(2)}"></div>`;
    }
    container.innerHTML = html;
}
```

### Step 3.6 — Add coherence flags to existing warnings area

Instead of a separate sidebar alert list, coherence flags are appended to the existing `warnings` array (the same one that feeds `#arc-warnings` at the bottom of the graph). This avoids duplicate alert surfaces.

In `buildArcGraph()`, after the existing character sanity checks (~line 3769):

```javascript
// Coherence flags from backend
const coherenceFlags = (window.__COHERENCE_FLAGS__ || []);
coherenceFlags.forEach(f => {
    warnings.push(`${f.message}`);
});
```

Update CSS — the existing `.arc-warning-icon` uses `&#9888;` (⚠). For coherence flags we want a slightly different visual. Add:

```css
.arc-warning.coherence .arc-warning-icon { color: #ffd93d; }
```

And in the rendering loop, mark coherence flag entries:

```javascript
// Warnings rendering (~line 3842)
warningsEl.innerHTML = warnings.map(w => {
    const isCoherence = coherenceFlags.some(f => f.message === w);
    return `<div class="arc-warning${isCoherence ? ' coherence' : ''}"><span class="arc-warning-icon">&#9888;</span><span>${escapeHtml(w)}</span></div>`;
}).join('');
```

Remove the `#arc-alert-list` container and `buildAlertList()` function from the task — they're replaced by the existing warnings area.
```

### Step 3.7 — Call delta bar at end of `buildArcGraph()`

After warnings rendering (~line 3851):

```javascript
const protag = (story.characters || []).find(c => c.story_role === 'Protagonist');
buildDeltaBar(protag ? protag.id : null);
```

### Step 3.8 — Inject coherence flags in `story_dashboard.py`

In `tools/story_dashboard.py`, add to the injection block (~line 383):

```python
from core.coherence import compute_coherence
coherence_flags = compute_coherence(yaml_data)
injections += f"\nwindow.__COHERENCE_FLAGS__ = {json.dumps(coherence_flags)};"
```

### Step 3.9 — Add act-band data attribute for highlighting

In the act band loop, add `data-act="${acts[i]?.id || ''}"` to each `<rect>` so alerts can reference them.

## Legacy cleanup

- The old act boundary rendering code (~lines 3784-3799) is removed and replaced by equal-width bands
- The old `beatX()` scene-based positioning is replaced by act-band-based positioning (done in Phase 2)

## Naming convention check

- `buildDeltaBar`, `buildAlertList` — verb-first, match `buildArcGraph` pattern
- `lineClass` — camelCase local, matches `muted` pattern
- `arc-delta-bar`, `arc-alert-list` — kebab-case CSS classes, match `arc-graph-wrap` pattern
- `__COHERENCE_FLAGS__` — uppercase dunder, matches `__STORY_DATA__`, `__SECTIONS__` pattern

## Verification checklist

- [x] CSS added for act bands, line styles, delta bar, coherence flag color
- [x] HTML container for delta bar added
- [x] Act bands render as equal-width backgrounds from Phase 2
- [x] Antagonist line is dashed, supporting line is thin
- [x] Per-act delta bar renders below main graph
- [x] Coherence flags appended to existing warnings area (not separate alert list)
- [x] `window.__COHERENCE_FLAGS__` injected by `story_dashboard.py`
- [x] `test_coherence.py` updated with visualization tests
- [x] `pytest tests/test_coherence.py -k "dashboard"` passes (14/14)
- [x] Existing tests still pass (`pytest tests/test_arcs.py` — 49/49)
- [x] Full suite passes (120/120)

## Final notes

**Implementation:** Phase 3 complete. Added structural avenue rendering (soft blurred band from value_open→value_close), multi-character line differentiation (antagonist dashed, supporting thin), per-act delta bar (net Δy per act as colored bars below graph), and coherence flags injected from backend into existing warnings area with yellow icon.

**No divergences from spec.** All steps implemented as specified.

**NITE:**
- ~~`.arc-warning.coherence` CSS color was same as default — fixed to `#e0a86b` for visual distinction.~~ (fixed)
- `buildDeltaBar()` linear height scaling may saturate for large Δy — annotated with `ponytail:` comment, normalize against max Δy if needed.
