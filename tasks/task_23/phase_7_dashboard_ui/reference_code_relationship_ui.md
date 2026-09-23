# Dashboard Integration Reference — Relationship UI Patch

This file is self-contained. You can send it to the specialist without the 4034-line dashboard. Every section has the exact code, the exact location to patch, and the exact string to find/replace.

---

## 1. CSS Tokens You'll Reference (verified, lines 25-55)

```css
  --foreground: #e8e8e8;
  --muted-foreground: #8a8a8a;
  --accent: #7b9cf0;
  --border: rgba(255,255,255,0.1);
  --card: rgba(255,255,255,0.04);
  --panel-bg: #181818;
  --radius: 6px;
  --gap: 12px;
  --font-size-xs: 10px;
  --font-size-sm: 11px;
  --font-size-base: 13px;
  --font-size-lg: 15px;
```

---

## 2. CSS to Add (after `.relationship-row` styles, line ~772)

```css
/* Perspective panels in relationship panel */
.panel-perspective {
  padding: 10px;
  background: var(--card);
  border-radius: var(--radius);
  border: 1px solid var(--border);
}
```

---

## 3. Helper Function (add after `getRoleKey()`, line ~2061)

```javascript
const REL_TYPE_COLORS = {
  'ally':         '#6bbfb0',
  'enemy':        '#e07070',
  'family':       '#7b9cf0',
  'romantic':     '#e06b9b',
  'professional': '#e0a86b',
  'mentor':       '#b07be0',
  'rival':        '#e0a86b',
  'custom':       '#8a8a8a',
};

function relTypeColor(type) {
  if (!type) return '#8a8a8a';
  return REL_TYPE_COLORS[type.toLowerCase()] || '#8a8a8a';
}
```

---

## 4. Replacement: `loadSampleData()` (lines 1858-1914)

**Find**: The `relationships:` entries on sample characters (lines 1867, 1875-1877).

**Replace** with new format:
```javascript
// In detective-oak character:
relationships: [{ with: "mara", label: "Partner", type: "ally", strength: 0.5 }]

// In mara character:
relationships: [
  { with: "detective-oak", label: "Partner", type: "ally", strength: 0.4 },
  { with: "victor-hale", label: "Boss", type: "enemy", strength: -0.6 }
]
```

Also **add** a top-level `relationships` array to the `sample` object (after `story_memory`, line 1909):
```javascript
relationships: [
  {
    id: "mara-oak",
    name: "Mara & Oak",
    characters: ["mara", "detective-oak"],
    perspectives: {
      mara: { label: "Partner", feeling: "Wary respect — he's useful but unpredictable", type: "ally", strength: 0.4, secret: false },
      "detective-oak": { label: "Partner", feeling: "Brilliant but reckless", type: "ally", strength: 0.5, secret: false }
    },
    scenes: [],
    status: "active",
    history: ""
  },
  {
    id: "mara-victor",
    name: "Mara & Victor",
    characters: ["mara", "victor-hale"],
    perspectives: {
      mara: { label: "Boss", feeling: "Fear — he knows what she's found", type: "enemy", strength: -0.6, secret: true },
      "victor-hale": { label: "Employee", feeling: "Useful asset, potential threat", type: "professional", strength: -0.2, secret: false }
    },
    scenes: [],
    status: "active",
    history: ""
  }
]
```

---

## 5. Replacement: `normalise()` (lines 1925-1989)

**Find** (line 1932-1935):
```javascript
if (c.relationships && !c.related) {
  c.related = c.relationships.map(r => ({ id: r.id, label: r.label, feeling: r.feeling }));
}
```

**Replace** with:
```javascript
if (c.relationships && !c.related) {
  c.related = c.relationships.map(r => ({
    id: r.with || r.id,
    label: r.label,
    feeling: '',  // feeling moved to perspectives in full entity
  }));
}
```

---

## 6. Replacement: `initStory()` (lines 1992-2010)

**Find** (lines 2003-2009):
```javascript
  buildGraphView();
  buildScenesView();
  buildLocationsView();
  buildPlotsView();
  buildWorldsView();
  buildStoryView();
```

**Replace** with (add `buildRelationshipsView()` after `buildPlotsView()`):
```javascript
  buildGraphView();
  buildScenesView();
  buildLocationsView();
  buildPlotsView();
  buildRelationshipsView();
  buildWorldsView();
  buildStoryView();
```

---

## 7. Replacement: `buildGraphView()` (full function, lines 2064-2177)

**Replace the entire function** with:

```javascript
function buildGraphView() {
  const chars = story.characters || [];
  document.getElementById('graph-subtitle').textContent = chars.length + ' characters';

  const fgColor = getComputedStyle(document.documentElement).getPropertyValue('--foreground').trim() || '#e8e8e8';
  const mutedColor = getComputedStyle(document.documentElement).getPropertyValue('--muted-foreground').trim() || '#8a8a8a';

  const nodes = new vis.DataSet(chars.map(c => {
    const role = c.role || c.story_role || '';
    const col = roleColor(role);
    return {
      id: c.id,
      label: c.name,
      color: {
        background: col + '22',
        border: col,
        highlight: { background: col + '44', border: col },
        hover: { background: col + '33', border: col }
      },
      font: { color: fgColor, size: 12, face: 'inherit' },
      borderWidth: 1.5,
      borderWidthSelected: 2,
      size: 22,
      shape: 'dot'
    };
  }));

  const edges = [];
  const rels = story.relationships || [];

  rels.forEach(rel => {
    if (!rel.characters || rel.characters.length < 2) return;
    const [a, b] = rel.characters;
    const pa = rel.perspectives[a] || {};
    const pb = rel.perspectives[b] || {};

    edges.push({
      from: a, to: b,
      label: pa.label || '',
      color: { color: relTypeColor(pa.type) + 'aa', highlight: relTypeColor(pa.type) },
      font: { color: mutedColor, size: 9, align: 'middle', strokeWidth: 0 },
      width: 1 + ((pa.strength || 0) + 1) * 2,
      dashes: pa.secret || false,
      smooth: { type: 'curvedCW', roundness: 0.2 },
      relId: rel.id
    });

    edges.push({
      from: b, to: a,
      label: pb.label || '',
      color: { color: relTypeColor(pb.type) + 'aa', highlight: relTypeColor(pb.type) },
      font: { color: mutedColor, size: 9, align: 'middle', strokeWidth: 0 },
      width: 1 + ((pb.strength || 0) + 1) * 2,
      dashes: pb.secret || false,
      smooth: { type: 'curvedCCW', roundness: 0.2 },
      relId: rel.id
    });
  });

  const edgeDataSet = new vis.DataSet(edges);
  const container = document.getElementById('network-canvas');

  const options = {
    nodes: { borderWidthSelected: 2 },
    edges: { arrows: { to: { enabled: true, scaleFactor: 0.5 } } },
    physics: {
      enabled: true,
      solver: 'forceAtlas2Based',
      forceAtlas2Based: { gravitationalConstant: -40, centralGravity: 0.01, springLength: 120, springConstant: 0.08, damping: 0.4 }
    },
    interaction: { hover: true, tooltipDelay: 200, hideEdgesOnDrag: false },
    layout: { randomSeed: 42 }
  };

  network = new vis.Network(container, { nodes, edges: edgeDataSet }, options);

  // Fix: center graph after physics stabilization (was missing — caused spawn-off-center bug)
  network.once('stabilizationIterationsDone', () => {
    network.setOptions({ physics: { enabled: false } });
    setTimeout(() => network.fit({
      animation: { duration: 400, easingFunction: 'easeInOutQuad' }
    }), 100);
  });
  setTimeout(() => {
    if (network) {
      network.setOptions({ physics: { enabled: false } });
      network.fit({ animation: { duration: 400, easingFunction: 'easeInOutQuad' } });
    }
  }, 3000);

  network.on('hoverNode', params => {
    const nodeId = params.node;
    const char = chars.find(c => c.id === nodeId);
    if (!char) return;
    const role = char.role || char.story_role || '';
    const arcType = char.arc_type || 'absent';
    const arcValue = char.arc_value || '';
    const arcBeatCount = char.arc_beats_list ? char.arc_beats_list.length : 0;
    const tt = document.getElementById('arc-beat-tooltip');
    if (!tt) return;
    document.getElementById('tt-label').textContent = char.name;
    document.getElementById('tt-char').textContent = role;
    let shiftText = '';
    if (arcBeatCount > 0) {
      shiftText = arcType + (arcValue ? ' · ' + arcValue : '') + ' · ' + arcBeatCount + ' beats';
    } else {
      shiftText = arcType;
    }
    document.getElementById('tt-shift').textContent = shiftText;
    document.getElementById('tt-value').innerHTML = '';
    tt.classList.add('visible');
    positionArcTooltip({ clientX: params.event.clientX, clientY: params.event.clientY });
  });
  network.on('blurNode', () => hideArcTooltip());

  network.on('click', params => {
    if (params.nodes.length > 0) {
      const charId = params.nodes[0];
      const char = chars.find(c => c.id === charId);
      if (char) showCharacterPanel(char);
    } else if (params.edges.length > 0) {
      const edgeId = params.edges[0];
      const edge = edgeDataSet.get(edgeId);
      if (edge && edge.relId) {
        const rel = rels.find(r => r.id === edge.relId);
        if (rel) showRelationshipPanel(rel);
      }
    }
  });

  const legend = document.getElementById('graph-legend');
  const seen_roles = new Set();
  chars.forEach(c => seen_roles.add(getRoleKey(c.role)));
  const roleLegend = [...seen_roles].map(role => {
    const charsInRole = chars.filter(c => getRoleKey(c.role) === role);
    const arcChars = charsInRole.filter(c => c.arc_type && c.arc_type !== 'absent');
    const arcBadge = arcChars.length > 0 ? ` <span style="color:var(--muted-foreground);font-size:9px">(${arcChars.length} arc)</span>` : '';
    return `
      <div class="legend-item">
        <div class="legend-dot" style="background:${ROLE_COLORS[role] || '#8a8a8a'}"></div>
        <span>${role.charAt(0).toUpperCase() + role.slice(1)}</span>${arcBadge}
      </div>`;
  }).join('');

  const usedRelTypes = new Set();
  rels.forEach(r => { Object.values(r.perspectives || {}).forEach(p => { if (p.type) usedRelTypes.add(p.type); }); });
  const relLegend = [...usedRelTypes].map(t => `
    <div class="legend-item">
      <div class="legend-dot" style="background:${relTypeColor(t)};width:16px;height:3px;border-radius:0;margin-left:3px"></div>
      <span>${t}</span>
    </div>`).join('');

  legend.innerHTML = roleLegend + (relLegend ? '<div style="height:4px"></div>' + relLegend : '');
}
```

---

## 8. Replacement: `resetGraphLayout()` (lines 2179-2184)

**Replace** with:

```javascript
function resetGraphLayout() {
  if (network) {
    network.setOptions({ physics: { enabled: true } });
    setTimeout(() => {
      network.setOptions({ physics: { enabled: false } });
      network.fit({ animation: { duration: 400, easingFunction: 'easeInOutQuad' } });
    }, 3000);
  }
}
```

---

## 9. New: `showRelationshipPanel()` (add after `showPlotPanel`, line ~2954)

```javascript
function showRelationshipPanel(rel) {
  const a = rel.characters[0];
  const b = rel.characters[1];
  const charA = (story.characters || []).find(c => c.id === a);
  const charB = (story.characters || []).find(c => c.id === b);
  const pa = (rel.perspectives || {})[a] || {};
  const pb = (rel.perspectives || {})[b] || {};

  const nameA = charA
    ? `<button class="entity-link" onclick="showCharacterPanel(story.characters.find(x=>x.id==='${a}'))" style="border-left:2px solid ${roleColor(charA.role)}">${charA.name}</button>`
    : `<span class="panel-muted">${a}</span>`;
  const nameB = charB
    ? `<button class="entity-link" onclick="showCharacterPanel(story.characters.find(x=>x.id==='${b}'))" style="border-left:2px solid ${roleColor(charB.role)}">${charB.name}</button>`
    : `<span class="panel-muted">${b}</span>`;

  function perspectiveHtml(charName, charRole, p) {
    if (!charName) return '';
    const col = relTypeColor(p.type);
    const typeTag = p.type ? `<span class="tag" style="background:${col}22;color:${col}">${p.type}</span>` : '';
    const secretBadge = p.secret ? `<span class="tag" style="background:rgba(224,107,155,0.18);color:#e06b9b">secret 🔒</span>` : '';
    const strengthBar = p.strength !== undefined ? `
      <div style="display:flex;align-items:center;gap:6px;margin-top:4px">
        <div style="flex:1;height:3px;background:var(--border);border-radius:2px;overflow:hidden">
          <div style="width:${Math.abs(p.strength) * 50}%;height:100%;background:${p.strength >= 0 ? col : '#e07070'};margin-left:${p.strength >= 0 ? '50%' : (50 - Math.abs(p.strength) * 50) + '%'}"></div>
        </div>
        <span style="font-size:var(--font-size-xs);color:var(--muted-foreground)">${p.strength > 0 ? '+' : ''}${p.strength}</span>
      </div>` : '';
    return `
      <div class="panel-perspective" style="flex:1">
        <div style="font-size:var(--font-size-sm);font-weight:500;margin-bottom:4px">${charName}</div>
        ${charRole ? `<div style="font-size:var(--font-size-xs);color:var(--muted-foreground);margin-bottom:6px">${charRole}</div>` : ''}
        <div style="display:flex;flex-wrap:wrap;gap:4px;margin-bottom:4px">${typeTag}${secretBadge}</div>
        ${p.label ? `<div style="font-size:var(--font-size-sm);margin-bottom:2px">${p.label}</div>` : ''}
        ${p.feeling ? `<div style="font-size:var(--font-size-xs);color:var(--muted-foreground);font-style:italic">${p.feeling}</div>` : ''}
        ${strengthBar}
      </div>`;
  }

  const sceneTags = (rel.scenes || []).map(sid => {
    const s = (story.scenes || []).find(x => String(x.id) === String(sid));
    if (s) {
      const num = s.number != null ? String(s.number) : '';
      const label = num ? `${num}. ${s.title || s.id}` : (s.title || s.id);
      return `<span class="tag tag-scene" style="cursor:pointer" onclick="showScenePanel('${s.id}')">${label}</span>`;
    }
    return sid ? `<span class="tag tag-scene">${sid}</span>` : '';
  }).filter(Boolean).join('');

  document.getElementById('panel-type').textContent = 'Relationship';
  document.getElementById('panel-name').textContent = rel.name || `${a} & ${b}`;

  document.getElementById('panel-body').innerHTML = `
    <div>
      <div class="panel-section-title">Characters</div>
      <div style="display:flex;gap:8px;flex-wrap:wrap">${nameA}${nameB}</div>
    </div>
    <div>
      <div class="panel-section-title">Perspectives</div>
      <div style="display:flex;gap:16px">
        ${perspectiveHtml(charA?.name, charA?.role, pa)}
        ${perspectiveHtml(charB?.name, charB?.role, pb)}
      </div>
    </div>
    ${sceneTags ? `<div>
      <div class="panel-section-title">Scenes</div>
      <div class="panel-tags">${sceneTags}</div>
    </div>` : ''}
    ${rel.status ? `<div>
      <div class="panel-section-title">Status</div>
      <span class="status-badge ${rel.status}">${rel.status}</span>
    </div>` : ''}
    ${rel.history ? `<div>
      <div class="panel-section-title">History</div>
      <div class="panel-text">${escapeHtml(rel.history).replace(/\n/g, '<br>')}</div>
    </div>` : ''}
  `;

  document.getElementById('panel-footer').innerHTML = `
    <button class="btn btn-hermes" data-hermes-send="Update the relationship between ${charA?.name || a} and ${charB?.name || b}. Current status: ${rel.status || 'active'}. Tell me what changed and why.">Edit with Hermes</button>
  `;

  openPanel();
}
```

---

## 10. New: `buildRelationshipsView()` (add after `buildPlotsView`, line ~2411)

```javascript
function buildRelationshipsView() {
  const rels = story.relationships || [];
  document.getElementById('relationships-subtitle').textContent = rels.length + ' relationships';
  const list = document.getElementById('relationship-list');

  if (!rels.length) {
    list.innerHTML = '<div class="empty-state"><div class="empty-state-title">No relationships</div></div>';
    return;
  }

  list.innerHTML = rels.map(rel => {
    const charA = (story.characters || []).find(c => c.id === rel.characters[0]);
    const charB = (story.characters || []).find(c => c.id === rel.characters[1]);
    const pa = (rel.perspectives || {})[rel.characters[0]] || {};
    const pb = (rel.perspectives || {})[rel.characters[1]] || {};

    const charTags = rel.characters.map(cid => {
      const c = (story.characters || []).find(x => x.id === cid);
      return c ? `<span class="tag tag-char">${c.name}</span>` : '';
    }).join('');

    const types = new Set();
    if (pa.type) types.add(pa.type);
    if (pb.type) types.add(pb.type);
    const typeTags = [...types].map(t =>
      `<span class="tag" style="background:${relTypeColor(t)}22;color:${relTypeColor(t)}">${t}</span>`
    ).join('');

    const strengths = [pa.strength, pb.strength].filter(s => s !== undefined);
    const avgStrength = strengths.length ? strengths.reduce((a, b) => a + b, 0) / strengths.length : null;
    const strengthHtml = avgStrength !== null ? `
      <div style="display:flex;align-items:center;gap:4px;margin-top:4px">
        <div style="flex:1;height:3px;background:var(--border);border-radius:2px;overflow:hidden">
          <div style="width:${Math.abs(avgStrength) * 50}%;height:100%;background:${avgStrength >= 0 ? '#6bbfb0' : '#e07070'};margin-left:${avgStrength >= 0 ? '50%' : (50 - Math.abs(avgStrength) * 50) + '%'}"></div>
        </div>
        <span style="font-size:var(--font-size-xs);color:var(--muted-foreground)">${avgStrength > 0 ? '+' : ''}${avgStrength.toFixed(1)}</span>
      </div>` : '';

    const pipColor = types.size ? relTypeColor(types.values().next().value) : '#8a8a8a';

    return `
      <div class="entity-card" data-id="${rel.id}" onclick="showRelationshipPanel(story.relationships.find(r=>r.id==='${rel.id}'))">
        <div class="entity-card-pip" style="background:${pipColor}"></div>
        <div class="entity-card-body">
          <div class="entity-card-name" style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
            ${rel.name || `${rel.characters[0]} & ${rel.characters[1]}`}
            <span class="status-badge ${rel.status || ''}">${rel.status || 'active'}</span>
          </div>
          <div class="entity-card-sub">${charTags}</div>
          ${typeTags ? `<div class="entity-card-meta">${typeTags}</div>` : ''}
          ${strengthHtml ? `<div class="entity-card-meta">${strengthHtml}</div>` : ''}
        </div>
      </div>`;
  }).join('');
}
```

---

## 11. Replacement: Character Panel Relationship Section (lines 2614-2626)

**Find**:
```javascript
const rels = (char.related || []).map(rel => {
    const c = (story.characters || []).find(x => x.id === rel.id || String(x.id) === String(rel.id));
    const nameEl = c
        ? `<button class="relationship-name entity-link" onclick="showCharacterPanel(story.characters.find(x=>x.id==='${c.id}'))">${c.name}</button>`
        : `<span class="relationship-name">${rel.id}</span>`;
    return `
      <div class="relationship-row">
        ${nameEl}
        ${rel.label ? `<span class="relationship-label">${rel.label}</span>` : ''}
        ${rel.feeling ? `<span class="relationship-feeling">— ${rel.feeling}</span>` : ''}
      </div>`;
}).join('');
```

**Replace** with:
```javascript
const rels = (char.relationships || []).map(rel => {
    const c = (story.characters || []).find(x => x.id === rel.with);
    const nameEl = c
        ? `<button class="relationship-name entity-link" onclick="showCharacterPanel(story.characters.find(x=>x.id==='${c.id}'))">${c.name}</button>`
        : `<span class="relationship-name">${rel.with}</span>`;
    const secretIcon = rel.secret ? ' 🔒' : '';
    const typeTag = rel.type ? `<span class="tag" style="background:${relTypeColor(rel.type)}22;color:${relTypeColor(rel.type)}">${rel.type}</span>` : '';
    return `
      <div class="relationship-row">
        ${nameEl}${secretIcon}
        ${rel.label ? `<span class="relationship-label">${rel.label}</span>` : ''}
        ${typeTag}
        ${rel.strength !== undefined ? `<span class="relationship-feeling">strength: ${rel.strength > 0 ? '+' : ''}${rel.strength}</span>` : ''}
      </div>`;
}).join('');
```

---

## 12. Sidebar Button HTML (insert after "Characters" button, line ~1379)

Insert before the Scenes button:
```html
<button class="nav-btn" data-view="relationships" onclick="switchView('relationships', this)">
  <svg class="nav-icon" viewBox="0 0 16 16" fill="none">
    <circle cx="5" cy="5" r="2.2" stroke="currentColor" stroke-width="1.3"/>
    <circle cx="11" cy="11" r="2.2" stroke="currentColor" stroke-width="1.3"/>
    <path d="M6.8 6.8L9.2 9.2" stroke="currentColor" stroke-width="1.2"/>
    <path d="M9.2 6.8L6.8 9.2" stroke="currentColor" stroke-width="1.2" stroke-dasharray="2 1"/>
  </svg>
  <span class="nav-label">Relationships</span>
</button>
```

---

## 13. Relationships View Container HTML (insert after Plots view, line ~1536)

```html
<!-- Relationships View -->
<div class="view entity-list-view" id="relationships-view">
  <div class="view-header">
    <div class="view-title">Relationships</div>
    <div class="view-subtitle" id="relationships-subtitle">—</div>
  </div>
  <div class="view-body">
    <div class="entity-grid" id="relationship-list"></div>
  </div>
</div>
```

---

## Summary of Integration Points

| # | Where | Action |
|---|-------|--------|
| 2 | CSS after line 772 | Add `.panel-perspective` |
| 3 | JS after line 2061 | Add `relTypeColor()` helper |
| 4 | JS lines 1858-1914 | Replace sample data relationships |
| 5 | JS line 1932 | Replace normalise() mapping |
| 6 | JS lines 2003-2009 | Add `buildRelationshipsView()` call |
| 7 | JS lines 2064-2177 | Replace `buildGraphView()` entirely |
| 8 | JS lines 2179-2184 | Replace `resetGraphLayout()` |
| 9 | JS after line 2954 | Add `showRelationshipPanel()` |
| 10 | JS after line 2411 | Add `buildRelationshipsView()` |
| 11 | JS lines 2614-2626 | Replace character panel relationship section |
| 12 | HTML after line 1379 | Add sidebar button |
| 13 | HTML after line 1536 | Add relationships view container |

---

## Bugs Fixed from Original Brief

1. `r.perspectives.forEach(...)` → `Object.values(r.perspectives || {}).forEach(...)` (perspectives is an object, not array)
2. `relTypeColor([types.values().next().value])` → `relTypeColor(types.values().next().value)` (pass string, not array)
3. Centering bug: added `network.fit()` in `buildGraphView` stabilization handler and `resetGraphLayout` — graph now auto-centers on spawn and reset
