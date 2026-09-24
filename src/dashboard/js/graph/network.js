window.DASH = window.DASH || {};

DASH.buildGraphView = function() {
  const chars = DASH.story.characters || [];
  document.getElementById('graph-subtitle').textContent = chars.length + ' characters';

  const fgColor = getComputedStyle(document.documentElement).getPropertyValue('--foreground').trim() || '#e8e8e8';
  const mutedColor = getComputedStyle(document.documentElement).getPropertyValue('--muted-foreground').trim() || '#8a8a8a';

  const nodes = new vis.DataSet(chars.map(c => {
    const role = c.role || c.story_role || '';
    const col = DASH.roleColor(role);
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
  const rels = DASH.story.relationships || [];

  // Average all strength values per character pair (both directions, all rels)
  const pairStrength = {};
  rels.forEach(rel => {
    if (!rel.characters || rel.characters.length < 2) return;
    const [a, b] = rel.characters;
    const key = [a, b].sort().join('::');
    const pa = (rel.perspectives || {})[a] || {};
    const pb = (rel.perspectives || {})[b] || {};
    pairStrength[key] = pairStrength[key] || [];
    if (pa.strength !== undefined) pairStrength[key].push(pa.strength);
    if (pb.strength !== undefined) pairStrength[key].push(pb.strength);
  });
  const avgStrength = {};
  for (const key in pairStrength) {
    const vals = pairStrength[key];
    avgStrength[key] = vals.length ? vals.reduce((a, b) => a + b, 0) / vals.length : 0;
  }

  rels.forEach(rel => {
    if (!rel.characters || rel.characters.length < 2) return;
    const [a, b] = rel.characters;
    const pa = (rel.perspectives || {})[a] || {};
    const pb = (rel.perspectives || {})[b] || {};
    const fontCfg = { color: mutedColor, size: 9, align: 'middle', strokeWidth: 2, strokeColor: '#1a1a1a' };
    const key = [a, b].sort().join('::');
    const TYPE_PROXIMITY = { family: 0, romantic: 10, ally: 40, neutral: 50, professional: 60, mentor: 70, rival: 80, enemy: 100, custom: 50 };
    const typeOffset = Math.max(
      TYPE_PROXIMITY[pa.type] ?? 40,
      TYPE_PROXIMITY[pb.type] ?? 40
    );
    const spring = 80 + typeOffset * 1.5 + (1 - (avgStrength[key] || 0)) * 40;

    edges.push({
      from: a, to: b,
      label: pa.label || '',
      color: { color: DASH.relTypeColor(pa.type) + 'aa', highlight: DASH.relTypeColor(pa.type) },
      font: fontCfg,
      width: 1.5,
      dashes: pa.secret || false,
      length: spring,
      smooth: { enabled: false },
      relId: rel.id
    });

    edges.push({
      from: b, to: a,
      label: pb.label || '',
      color: { color: DASH.relTypeColor(pb.type) + 'aa', highlight: DASH.relTypeColor(pb.type) },
      font: fontCfg,
      width: 1.5,
      dashes: pb.secret || false,
      length: spring,
      relId: rel.id
    });
  });

  // Unlinked entities: add virtual neutral edges to protagonist(s) only
  const linkedIds = new Set();
  edges.forEach(e => { linkedIds.add(e.from); linkedIds.add(e.to); });
  const protagonists = chars.filter(c => (c.role || c.story_role || '').toLowerCase().includes('protagonist'));
  chars.forEach(c => {
    if (linkedIds.has(c.id)) return;
    protagonists.forEach(p => {
      if (p.id === c.id) return;
      edges.push({
        from: c.id, to: p.id,
        label: '',
        color: { color: '#7a8a9a11', highlight: '#7a8a9a' },
        font: { color: mutedColor, size: 9, align: 'middle', strokeWidth: 2, strokeColor: '#1a1a1a' },
        width: 0.5,
        dashes: true,
        length: 80 + 50 * 1.5,
        smooth: { enabled: false },
        relId: '_virtual_'
      });
    });
  });

  const edgeDataSet = new vis.DataSet(edges);
  const container = document.getElementById('network-canvas');

  const options = {
    nodes: { borderWidthSelected: 2 },
    edges: { arrows: { to: { enabled: true, scaleFactor: 0.5 } } },
    physics: {
      enabled: true,
      solver: 'barnesHut',
      barnesHut: { gravitationalConstant: -500, centralGravity: 0.01, springConstant: 0.15, springLength: 150, damping: 0.4 }
    },
    interaction: { hover: true, tooltipDelay: 200, hideEdgesOnDrag: false },
    layout: { randomSeed: 42 }
  };

  DASH.network = new vis.Network(container, { nodes, edges: edgeDataSet }, options);

  // Fit after initial stabilization
  DASH.network.once('stabilizationIterationsDone', () => {
    DASH.network.fit({ animation: { duration: 400, easingFunction: 'easeInOutQuad' } });
  });

  DASH.network.on('hoverNode', params => {
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
    DASH.positionArcTooltip({ clientX: params.event.clientX, clientY: params.event.clientY });
  });
  DASH.network.on('blurNode', () => DASH.hideArcTooltip());

  DASH.network.on('click', params => {
    if (params.nodes.length > 0) {
      const charId = params.nodes[0];
      const char = chars.find(c => c.id === charId);
      if (char) DASH.showCharacterPanel(char);
    } else if (params.edges.length > 0) {
      const edgeId = params.edges[0];
      const edge = edgeDataSet.get(edgeId);
      if (edge && edge.relId) {
        const rel = rels.find(r => r.id === edge.relId);
        if (rel) DASH.showRelationshipPanel(rel);
      }
    }
  });

  const legend = document.getElementById('graph-legend');
  const seenRoles = new Set();
  chars.forEach(c => seenRoles.add(DASH.getRoleKey(c.role)));
  const roleLegend = [...seenRoles].map(role => {
    const charsInRole = chars.filter(c => DASH.getRoleKey(c.role) === role);
    const arcChars = charsInRole.filter(c => c.arc_type && c.arc_type !== 'absent');
    const arcBadge = arcChars.length > 0 ? ` <span style="color:var(--muted-foreground);font-size:9px">(${arcChars.length} arc)</span>` : '';
    return `
      <div class="legend-item">
        <div class="legend-dot" style="background:${DASH.ROLE_COLORS[role] || '#8a8a8a'}"></div>
        <span>${role.charAt(0).toUpperCase() + role.slice(1)}</span>${arcBadge}
      </div>`;
  }).join('');

  const usedRelTypes = new Set();
  rels.forEach(r => { Object.values(r.perspectives || {}).forEach(p => { if (p.type) usedRelTypes.add(p.type); }); });
  const relLegend = [...usedRelTypes].map(t => `
    <div class="legend-item">
      <div class="legend-dot" style="background:${DASH.relTypeColor(t)};width:16px;height:3px;border-radius:0;margin-left:3px"></div>
      <span>${t}</span>
    </div>`).join('');

  legend.innerHTML = roleLegend + (relLegend ? '<div style="height:4px"></div>' + relLegend : '');
}

DASH.resetGraphLayout = function() {
  if (DASH.network) {
    DASH.network.setOptions({ physics: { enabled: true } });
    setTimeout(() => {
      DASH.network.setOptions({ physics: { enabled: false } });
      DASH.network.fit({ animation: { duration: 400, easingFunction: 'easeInOutQuad' } });
    }, 3000);
  }
}
