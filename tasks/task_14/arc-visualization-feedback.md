# Arc Visualization — Feedback & Integration Notes

The demo is **excellent** — the graph rendering, beat detail panel, spline toggle, sanity checks, and scene indicators are all exactly what we need. Send this back to the specialist with the following integration notes.

---

## What to Change

### 1. Tab Rename + Network Tab

Your "Network" tab should be called **"Arc graph"** (it IS the arc graph). Add a new tab:

| Tab | Content |
|-----|---------|
| **Network** | Existing character web (vis-network force-directed graph). We'll provide you the JS for this. |
| **Arc graph** | Your current multi-line arc visualization. |

So:
- Rename `id="tab-web"` → `id="tab-network"`
- Rename `id="tab-arcs"` → `id="tab-arc-graph"`
- Update `switchTab()` to handle `'network'` (renders vis-network) and `'arc-graph'` (your SVG arc graph)

### 2. Data Source Alignment

Your demo uses hardcoded `STORY_DATA`. The real data comes from `window.__STORY_DATA__` (injected by `tools/story_dashboard.py`). The structure matches what's in the brief:

```javascript
// Replace STORY_DATA with:
const story = window.__STORY_DATA__;

// Replace BEAT_DETAILS with on-demand load:
// When beat panel opens, fetch beat note content via __SECTIONS__ if available,
// otherwise the panel shows "Load from Hermes" prompt
```

**Critical**: Derive act x-positions from scene order, not from `story.acts[].x_start/x_end`. Your `beatX()` function is correct — use `sceneOrder[beat.scene] / (sceneCount - 1)` as you already do.

### 3. Sidebar Integration

Remove your standalone sidebar. The arc view integrates into the existing dashboard sidebar:

```html
<!-- Add to existing sidebar nav -->
<button class="nav-btn" data-view="arcs" onclick="switchView('arcs', this)">
  <svg class="nav-icon" viewBox="0 0 16 16" fill="none">
    <path d="M2 12 L5 7 L8 9 L11 4 L14 6" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/>
    <circle cx="5" cy="7" r="1.2" fill="currentColor"/>
    <circle cx="11" cy="4" r="1.2" fill="currentColor"/>
  </svg>
  <span class="nav-label">Arcs</span>
</button>
```

### 4. Event Delegation Pattern

Your `onmouseenter`/`onmouseleave`/`onclick` inline attributes work but the existing dashboard uses `addEventListener`. For consistency, attach events after SVG render:

```javascript
// Instead of inline attributes:
wrap.addEventListener('mouseover', e => {
  if (e.target.classList.contains('arc-beat-dot')) showTooltip(e, e.target);
});
wrap.addEventListener('click', e => {
  if (e.target.classList.contains('arc-beat-dot')) openPanel(e.target.dataset.char, e.target.dataset.beat);
});
```

### 5. CSS Token Alignment

Your tokens are 95% aligned. A few small fixes:

```css
/* Your --border is slightly different — use existing value */
--border: rgba(255,255,255, 0.1);  /* ← change to 0.08 to match existing */

/* Your --card value is fine but existing uses rgba(255,255,255,0.04) — keep yours */
```

### 6. Beat Detail Loading

Your `BEAT_DETAILS` local object is fine for demo. For production:

```javascript
function openPanel(charId, beatId) {
  // 1. Check if __SECTIONS__ has beat content
  const beatSection = window.__SECTIONS__?.['arc']?.[`${charId}/${beatId}`];
  if (beatSection) {
    // Parse Action/Gap/Choice/Shift from sections
    const action = getSectionBody(beatSection, 'Action');
    const gap = getSectionBody(beatSection, 'Gap');
    // ...
  } else {
    // Show "Load from Hermes" prompt
  }
}
```

---

## What to Keep (It's All Good)

- SVG graph rendering with Catmull-Rom spline
- Beat detail panel with icon-coded sections (Action/Gap/Choice/Shift)
- Development log display
- Beat navigation (prev/next)
- Sanity warnings (flat arc, melodramatic beat, redundancy)
- Scene beat indicators (colored dots in scene cards)
- Empty state with Hermes prompt
- Legend with mute toggle
- Spline/labels toggles
- Tooltip on beat hover

---

## Handoff Checklist

When the specialist returns the updated version:

- [ ] "Arc graph" tab renders arc visualization
- [ ] "Network" tab renders vis-network character web (you provide the JS)
- [ ] Sidebar nav integrated into existing `#sidebar`
- [ ] Data sourced from `window.__STORY_DATA__`
- [ ] Events use `addEventListener` pattern
- [ ] Beat detail loads from `__SECTIONS__` when available
- [ ] CSS tokens aligned with existing dashboard
