# Phase 5: Integration with Existing Views — Arc Badges & Indicators

## Prerequisite

Phase 4 complete. Arc graph exists in Characters view.

## Files to modify

| File | Change |
|------|--------|
| `src/dashboard/story-dashboard.html` | Add arc_type badge to character nodes in Graph view |
| `src/dashboard/story-dashboard.html` | Add arc beat count to character panel |
| `src/dashboard/story-dashboard.html` | Add arc summary to Structure stats view |

## Key Findings

1. **Character nodes** use vis.js — `buildGraphView()` at line 1796. Nodes have `label` and `title` (tooltip). Add arc_type to tooltip.
2. **Character panel** — `showCharacterPanel()` at line 2255. Add arc summary section.
3. **Structure view** — static HTML in `populateStructuralStats()`. No act timeline exists to overlay beats on. Instead, add arc design summary (characters with arcs, total beats).
4. **Scene cards** — arc beat dots already added in Phase 4 Step 4.5. This phase adds the badge integration.

## Step-by-step

### Step 5.1 — Add arc_type badge to character nodes

In `buildGraphView()` (line 1796), modify the node creation to include arc_type in the tooltip:

```javascript
const nodes = new vis.DataSet(chars.map(c => {
  const role = c.role || c.story_role || '';
  const col = roleColor(role);
  const arcType = c.arc_type || 'absent';
  const arcBeatCount = c.arc_beats_list ? c.arc_beats_list.length : 0;
  const arcSummary = arcBeatCount > 0 ? ` | ${arcBeatCount} beats` : '';
  return {
    id: c.id,
    label: c.name,
    title: `${role}\nArc: ${arcType}${arcSummary}`,  // Enhanced tooltip
    // ... rest unchanged
  };
}));
```

### Step 5.2 — Add arc summary to character panel

In `showCharacterPanel()` (line 2255), after the existing stats/structure/plots rendering, add arc info:

```javascript
// Arc summary
const arcBeats = char.arc_beats_list || [];
const arcType = char.arc_type || 'absent';
const arcSection = arcBeats.length > 0 ? `
  <div class="panel-section">
    <div class="panel-section-title">Arc (${arcType})</div>
    <div class="panel-muted" style="font-size:var(--font-size-sm);margin-bottom:8px">
      ${arcBeats.length} beats designed
    </div>
    <div class="arc-beat-list">
      ${arcBeats.map(b => `
        <div class="arc-beat-item" style="display:flex;align-items:center;gap:6px;margin-bottom:4px">
          <span class="arc-beat-dot" style="background:${roleColor(char.role || char.story_role || '')}"></span>
          <span style="font-size:var(--font-size-sm)">${escapeHtml(b.label || b.id)}</span>
          <span class="panel-muted" style="margin-left:auto;font-size:var(--font-size-xs)">y=${b.y}</span>
        </div>
      `).join('')}
    </div>
  </div>
` : `
  <div class="panel-section">
    <div class="panel-section-title">Arc</div>
    <div class="panel-muted" style="font-size:var(--font-size-sm)">No beats designed</div>
    <button class="btn btn-hermes" data-hermes-send="Design a character arc for ${char.name} showing their value shift across the story.">Design arc with Hermes</button>
  </div>
`;

// Insert arcSection into the panel body (after structureHtml or before hermesHtml)
```

### Step 5.3 — Add arc summary to Structure stats view

In `populateStructuralStats()` (around line 2157 where `structure` array is built), add arc design summary:

```javascript
// Arc design summary
const charsWithArcs = (story.characters || []).filter(c => c.arc_type && c.arc_type !== 'absent');
const totalArcBeats = (story.arcs || []).length;
if (charsWithArcs.length > 0) {
  structure.push(`<div style="margin-bottom:6px"><span style="color:var(--muted-foreground);font-size:var(--font-size-xs);text-transform:uppercase;letter-spacing:0.06em">Character Arcs</span><div style="font-size:var(--font-size-sm);color:var(--foreground);margin-top:2px">${charsWithArcs.length} characters · ${totalArcBeats} beats designed</div></div>`);
}
```

### Step 5.4 — Add arc beat count to character legend in Graph view

In `buildGraphView()` where legend is built (around line 1871), add arc_type indicator:

```javascript
legend.innerHTML = [...seen_roles].map(role => {
  const charsInRole = chars.filter(c => getRoleKey(c.role) === role);
  const arcChars = charsInRole.filter(c => c.arc_type && c.arc_type !== 'absent');
  const arcBadge = arcChars.length > 0 ? ` <span style="color:var(--muted-foreground);font-size:9px">(${arcChars.length} arc)</span>` : '';
  return `
    <div class="legend-item">
      <div class="legend-dot" style="background:${ROLE_COLORS[role] || '#8a8a8a'}"></div>
      <span>${role.charAt(0).toUpperCase() + role.slice(1)}</span>${arcBadge}
    </div>
  `;
}).join('');
```

## Legacy cleanup

None — additive only.

## Naming convention check

- `arc_type` (matches character frontmatter)
- `arc_beats_list` (matches index derivation output)
- `arc_beat_count` (matches character field)
- CSS: `.arc-beat-item`, `.arc-beat-dot`, `.arc-beat-list` (matches existing `arc-*` prefix)

## Final checklist (unmarked)

- [ ] Character nodes show arc_type in tooltip
- [ ] Character nodes show arc beat count in tooltip
- [ ] Character panel shows arc summary section
- [ ] Character panel shows arc beats list (label + y value)
- [ ] Character panel shows "Design arc" button when no beats
- [ ] Structure view shows arc design summary (characters with arcs, total beats)
- [ ] Graph legend shows arc count per role
- [ ] Scene cards show arc beat dots (from Phase 4)
- [ ] Tests added to `test_arcs.py` for dashboard integration
- [ ] `pytest tests/test_arcs.py` passes
