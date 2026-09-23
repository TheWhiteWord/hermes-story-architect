// ─── Boot ─────────────────────────────────────────────────────────────────────
window.DASH = window.DASH || {};

let story = null;

let network = null;


let _scriptBuilt = false;

let _statsPopulated = false;

let _structuralStatsPopulated = false;

let _currentBarcodeMode = 'type';

let _chartObservers = {};

let arcUseSpline = false;

let arcShowLabels = true;

let arcMutedChars = new Set();

const ARC_GW = 760;

const ARC_GH = 320;

const ARC_PAD = { top: 28, right: 40, bottom: 36, left: 42 };

DASH.boot = async function() {
  try {
    // Injected data takes precedence (avoids fetch('file://') which Electron blocks)
    if (window.__STORY_DATA__) {
      DASH.initStory(window.__STORY_DATA__);
      return;
    }

    // Check for project path in URL query param first
    const params = new URLSearchParams(window.location.search);
    const projectPath = params.get('project');
    let indexPath;

    if (projectPath) {
      indexPath = projectPath.replace(/\/$/, '') + '/.DASH.story/index.yaml';
    } else {
      indexPath = '.DASH.story/index.yaml';
    }

    const res = await fetch('file://' + indexPath);
    if (!res.ok) throw new Error('not found');
    const text = await res.text();
    const data = jsyaml.load(text);
    DASH.initStory(data);
  } catch (e) {
    DASH.showError();
  }
}

DASH.showError = function() {
  document.getElementById('loading-screen').style.display = 'none';
  document.getElementById('error-screen').style.display = 'flex';
}

DASH.normalise = function(data) {
  const d = JSON.parse(JSON.stringify(data)); // deep clone

  // Characters
  (d.characters || []).forEach(c => {
    // story_role → role
    if (c.story_role && !c.role) c.role = c.story_role;
    // goals object → flat
    if (c.goals && typeof c.goals === 'object') {
      if (!c.goals_short) c.goals_short = c.goals.short;
      if (!c.goals_long)  c.goals_long  = c.goals.long;
    }
    // knowledge: string[] → join for display (keep array for panel)
    if (Array.isArray(c.knowledge)) {
      c._knowledge_arr = c.knowledge;
      c.knowledge = c.knowledge.join(' · ');
    }
    // scenes: [{id, heading}] → map to scene IDs (prefer id match)
    if (Array.isArray(c.scenes) && c.scenes.length && typeof c.scenes[0] === 'object') {
      c._scene_objs = c.scenes;
      c.scenes = c.scenes.map(s => {
        const found = (d.scenes || []).find(sc =>
          String(sc.id) === String(s.id) ||  // match by slug id (preferred)
          sc.heading === s.heading ||          // fallback: heading match
          (sc.heading || '').includes(s.heading || '__NOMATCH__')  // fallback: fuzzy
        );
        return found ? String(found.id) : (s.heading || String(s.id));
      });
    } else {
      // ensure they're strings for consistent lookup
      c.scenes = (c.scenes || []).map(s => String(s));
    }
  });

  // Scenes: ensure id is string, title exists, normalise character/location arrays
  (d.scenes || []).forEach(s => {
    s.id = String(s.id);
    s.title = s.title || s.id;  // ensure title exists
    s.characters = (s.characters || []).map(String);
    // locations: normalize from location (string) or locations (array)
    s.locations = DASH.normalizeLocs(s.locations || s.location);
    s.plots = (s.plots || []);
  });

  // Plots: setups/payoffs already normalized by backend to [{heading, number, description}]
  (d.plots || []).forEach(pl => {
    pl.characters = (pl.characters || []).map(String);
  });

  // Locations: scenes may be heading strings — keep for cross-reference
  (d.locations || []).forEach(loc => {
    if (!loc._scene_headings && Array.isArray(loc.scenes)) {
      loc._scene_headings = loc.scenes.filter(s => typeof s === 'string');
    }
  });

  d.worlds = d.worlds || [];
  d.story_memory = d.story_memory || {};

  return d;
}

DASH.initStory = function(data) {
  DASH.story = DASH.normalise(data);
  DASH.story.characters = DASH.story.characters || [];
  DASH.story.locations  = DASH.story.locations  || [];
  DASH.story.plots      = DASH.story.plots      || [];
  DASH.story.scenes     = DASH.story.scenes     || [];
  DASH.story.worlds     = DASH.story.worlds     || [];
  DASH.story.story_memory = DASH.story.story_memory || {};
  DASH.story.relationships = DASH.story.relationships || [];

  document.getElementById('loading-screen').style.display = 'none';

  DASH.buildGraphView();
  DASH.buildScenesView();
  DASH.buildLocationsView();
  DASH.buildPlotsView();
  DASH.buildRelationshipsView();
  DASH.buildWorldsView();
  DASH.buildStoryView();
}

DASH._ensureChartRendered = function(containerId, renderFn) {
  const container = document.getElementById(containerId);
  if (!container) return;
  // Clean up previous observer for this container
  if (DASH._chartObservers[containerId]) {
    DASH._chartObservers[containerId].disconnect();
    delete DASH._chartObservers[containerId];
  }
  // Render immediately
  renderFn();
  // Observe resize — re-render when container reaches final size (after CSS transition)
  const ro = new ResizeObserver(entries => {
    for (const entry of entries) {
      if (entry.contentRect.width > 0) {
        renderFn();
      }
    }
  });
  ro.observe(container);
  DASH._chartObservers[containerId] = ro;
}

DASH._renderChartsForGroup = function(group) {
  const stats = window.__SCREENPLAY_STATS__;
  if (!stats) return;
  // requestAnimationFrame ensures layout has settled before reading dimensions
  requestAnimationFrame(() => {
    if (group === 'overview')    DASH.renderDurationChart(stats);
    if (group === 'characters')  DASH.renderCharacterChart(stats);
    if (group === 'scenes')      DASH.renderBarcodeChart(DASH._currentBarcodeMode);
    // No D3 charts for 'structure' — static HTML rendered in populateStructuralStats()
  });
}

DASH._renderDurationChart = function(stats) {
  const container = document.getElementById('durationStats-lengthchart');
  if (!container || !window.d3) return;
  container.innerHTML = '';

  const ds = stats.durationStats || {};
  const actionData = ds.lengthchart_action   || [];
  const dialogueData = ds.lengthchart_dialogue || [];
  if (!actionData.length && !dialogueData.length) return;

  // Pad to same length
  const len = Math.max(actionData.length, dialogueData.length);
  const aData = actionData.concat(Array(len - actionData.length).fill(0));
  const dData = dialogueData.concat(Array(len - dialogueData.length).fill(0));

  const W = container.clientWidth  || 320;
  const H = container.clientHeight || 72;
  const mg = { top: 6, right: 8, bottom: 16, left: 26 };
  const w = W - mg.left - mg.right;
  const h = H - mg.top  - mg.bottom;

  const svg = d3.select(container).append('svg').attr('width', W).attr('height', H);
  const g = svg.append('g').attr('transform', `translate(${mg.left},${mg.top})`);

  const x = d3.scaleLinear().domain([0, len - 1]).range([0, w]);
  const maxY = d3.max([...aData, ...dData]) || 1;
  const y = d3.scaleLinear().domain([0, maxY]).range([h, 0]);

  const area = (data, fill) => d3.area()
    .x((d, i) => x(i)).y0(h).y1(d => y(d))
    .curve(d3.curveCatmullRom)(data);
  const line = (data) => d3.line()
    .x((d, i) => x(i)).y(d => y(d))
    .curve(d3.curveCatmullRom)(data);

  g.append('path').attr('d', area(aData)).attr('fill', 'rgba(123,156,240,0.12)');
  g.append('path').attr('d', area(dData)).attr('fill', 'rgba(107,191,176,0.12)');
  g.append('path').attr('d', line(aData)).attr('fill','none').attr('stroke','#7b9cf0').attr('stroke-width',1.5);
  g.append('path').attr('d', line(dData)).attr('fill','none').attr('stroke','#6bbfb0').attr('stroke-width',1.5);

  g.append('g').attr('transform',`translate(0,${h})`)
    .call(d3.axisBottom(x).ticks(4).tickFormat(i => Math.round((i/(len-1||1))*100)+'%'))
    .selectAll('text').style('font-size','9px').attr('fill','var(--muted-foreground)');
  g.append('g')
    .call(d3.axisLeft(y).ticks(3).tickFormat(d => DASH.fmtDurationShort(d)))
    .selectAll('text').style('font-size','9px').attr('fill','var(--muted-foreground)');
  g.selectAll('.domain,.tick line').attr('stroke','rgba(255,255,255,0.12)');

  // Legend
  const leg = svg.append('g').attr('transform', `translate(${mg.left + w - 86},${mg.top + 2})`);
  leg.append('circle').attr('r',4).attr('cx',5).attr('cy',5).attr('fill','#7b9cf0');
  leg.append('text').attr('x',12).attr('y',9).text('Action').style('font-size','8px').attr('fill','var(--muted-foreground)');
  leg.append('circle').attr('r',4).attr('cx',5).attr('cy',17).attr('fill','#6bbfb0');
  leg.append('text').attr('x',12).attr('y',21).text('Dialogue').style('font-size','8px').attr('fill','var(--muted-foreground)');
}

DASH.arcSectionHtml = function(char) {
  const arcBeats = char.arc_beats_list || [];
  const arcType = char.arc_type || 'absent';
  const arcValue = char.arc_value || '';
  if (arcBeats.length > 0) {
    return `
      <div class="panel-muted" style="font-size:var(--font-size-sm);margin-bottom:8px">
        ${arcBeats.length} beats designed (${arcType}${arcValue ? ' · ' + arcValue : ''})
      </div>
      <div class="arc-beat-list">
        ${arcBeats.map(b => `
          <div class="arc-beat-item" style="display:flex;align-items:center;gap:6px;margin-bottom:4px">
            <span class="arc-beat-dot" style="background:${DASH.roleColor(char.role || char.story_role || '')}"></span>
            <span style="font-size:var(--font-size-sm)">${DASH.escapeHtml(b.label || b.id)}</span>
            <span class="panel-muted" style="margin-left:auto;font-size:var(--font-size-xs)">${DASH.escapeHtml(b.shift || '')}</span>
          </div>
        `).join('')}
      </div>`;
  }
  return `
    <div class="panel-muted" style="font-size:var(--font-size-sm)">No beats designed</div>
    <button class="btn btn-hermes" data-hermes-send="Design a character arc for ${char.name} showing their value shift across the DASH.story.">Design arc with Hermes</button>`;
}

DASH.arcXScale = function(t) {
  return DASH.ARC_PAD.left + t * (DASH.ARC_GW - DASH.ARC_PAD.left - DASH.ARC_PAD.right);
}

DASH.arcYScale = function(v) {
  return DASH.ARC_PAD.top + (1 - (v + 1) / 2) * (DASH.ARC_GH - DASH.ARC_PAD.top - DASH.ARC_PAD.bottom);
}

DASH.buildArcGraph = function() {
  const wrap = document.getElementById('arc-graph-wrap');
  if (!wrap) return;

  const chars = (DASH.story.characters || []).filter(c =>
    c.arc_type && c.arc_type !== 'absent' && c.arc_beats_list && c.arc_beats_list.length > 0
  );

  if (chars.length === 0) {
    wrap.innerHTML = `
      <div class="arc-empty">
        <div class="arc-empty-icon">&#9670;</div>
        <div class="arc-empty-title">No arc trajectories yet</div>
        <div class="arc-empty-text">Design a character arc to see value trajectories plotted here.</div>
        <button class="btn btn-hermes" data-hermes-send="Design a character arc for the protagonist showing their value shift across the DASH.story.">Design arc with Hermes</button>
      </div>`;
    return;
  }

  const actCount = DASH.story.project.act_count || 3;
  const acts = DASH.story.acts || [];
  const scenes = DASH.story.scenes || [];

  // Map scene → act index and scene order within that act
  const actById = {};
  acts.forEach((a, i) => { actById[a.id] = i; });
  const scenesInActMap = {};
  scenes.forEach(s => {
    if (s.act_id != null) {
      (scenesInActMap[s.act_id] = scenesInActMap[s.act_id] || []).push(s);
    }
  });
  Object.values(scenesInActMap).forEach(list => list.sort((a, b) => a.order - b.order));
  const sceneActIdx = {};  // scene id → { actIdx, idxInAct, countInAct }
  scenes.forEach(s => {
    if (s.act_id != null && scenesInActMap[s.act_id]) {
      const list = scenesInActMap[s.act_id];
      sceneActIdx[s.id] = {
        actIdx: actById[s.act_id] != null ? actById[s.act_id] : -1,
        idxInAct: list.findIndex(x => x.id === s.id),
        countInAct: list.length,
      };
    }
  });

  function beatX(char, beat) {
    const info = sceneActIdx[beat.scene];
    if (!info || info.actIdx === -1) {
      // Fallback: use beat order within character arc
      return (beat.order - 1) / (char.arc_beat_count || 1);
    }
    const innerPos = info.countInAct > 1 ? info.idxInAct / (info.countInAct - 1) : 0.5;
    return (info.actIdx + innerPos) / actCount;
  }

  // Sanity warnings
  const warnings = [];
  chars.forEach(char => {
    const ys = char.arc_beats_list.map(b => b.y);
    const maxDelta = Math.max(...ys.map((y, i) => i > 0 ? Math.abs(y - ys[i-1]) : 0));
    const range = Math.max(...ys) - Math.min(...ys);
    if (range < 0.2) warnings.push(`"${char.name}" arc is flat — nothing dramatic happens`);
    if (maxDelta > 0.8) warnings.push(`"${char.name}" has a single beat jump > 0.8 — consider splitting`);
  });

  let svg = `<svg viewBox="0 0 ${DASH.ARC_GW} ${DASH.ARC_GH}" class="arc-graph" id="arc-svg">`;

  // Grid lines
  for (let v = -1; v <= 1; v += 0.5) {
    const y = DASH.arcYScale(v);
    const cls = v === 0 ? 'arc-zero-line' : 'arc-grid-line';
    svg += `<line x1="${DASH.ARC_PAD.left}" y1="${y}" x2="${DASH.ARC_GW - DASH.ARC_PAD.right}" y2="${y}" class="${cls}"/>`;
    svg += `<text x="${DASH.ARC_PAD.left - 5}" y="${y}" class="arc-axis-label" text-anchor="end" dominant-baseline="central">${v > 0 ? '+' : ''}${v.toFixed(1)}</text>`;
  }

  // Y-axis label
  svg += `<text x="9" y="${DASH.ARC_GH/2}" class="arc-axis-label" text-anchor="middle" transform="rotate(-90,9,${DASH.ARC_GH/2})">value charge</text>`;

  // Equal-width act bands from act_count (renders even with no act files)
  const actBandwidth = (DASH.ARC_GW - DASH.ARC_PAD.left - DASH.ARC_PAD.right) / actCount;
  for (let i = 0; i < actCount; i++) {
    const x = DASH.ARC_PAD.left + i * actBandwidth;
    const act = acts[i];
    const label = act ? (act.title || act.id || `Act ${i+1}`) : `Act ${i+1}`;
    const cls = i % 2 === 0 ? 'even' : 'odd';
    svg += `<rect x="${x}" y="${DASH.ARC_PAD.top - 8}" width="${actBandwidth}" height="${DASH.ARC_GH - DASH.ARC_PAD.top - DASH.ARC_PAD.bottom + 12}" class="arc-act-band ${cls}"/>`;
    if (i > 0) {
      svg += `<line x1="${x}" y1="${DASH.ARC_PAD.top - 8}" x2="${x}" y2="${DASH.ARC_GH - DASH.ARC_PAD.bottom + 4}" class="arc-act-line"/>`;
    }
    svg += `<text x="${x + 4}" y="${DASH.ARC_PAD.top - 4}" class="arc-act-label">${DASH.escapeHtml(label)}</text>`;
  }

  // Arc lines + beat dots
  chars.forEach(char => {
    const color = DASH.roleColor(char.role || char.story_role || '');
    const muted = DASH.arcMutedChars.has(char.id) ? ' muted' : '';
    const beats = [...(char.arc_beats_list || [])].sort((a, b) => a.order - b.order);
    const pts = beats.map(b => [DASH.arcXScale(beatX(char, b)), DASH.arcYScale(b.y)]);

    if (DASH.arcUseSpline && pts.length > 2) {
      svg += `<path class="arc-line${muted}" d="${DASH.catmullRomPath(pts)}" stroke="${color}" stroke-opacity="${muted ? '0.15' : '0.8'}"/>`;
    } else {
      svg += `<polyline class="arc-line${muted}" points="${pts.map(p => p.join(',')).join(' ')}" stroke="${color}" stroke-opacity="${muted ? '0.15' : '0.8'}"/>`;
    }

    beats.forEach(beat => {
      const bx = DASH.arcXScale(beatX(char, beat));
      const by = DASH.arcYScale(beat.y);
      let r = 5, extraClass = '', fill = color, stroke = 'none', strokeW = 0;
      if (beat.is_crisis) { r = 7; fill = '#ffd93d'; extraClass = ' crisis'; }
      else if (beat.is_climax) { r = 7; fill = 'transparent'; stroke = color; strokeW = 2; extraClass = ' climax'; }
      const yDisp = beat.y >= 0 ? `+${beat.y.toFixed(2)}` : beat.y.toFixed(2);
      svg += `<circle class="arc-beat-dot${extraClass}${muted}" cx="${bx}" cy="${by}" r="${r}" fill="${fill}" stroke="${stroke}" stroke-width="${strokeW}" data-label="${DASH.escapeHtml(beat.label)}" data-char="${DASH.escapeHtml(char.name)}" data-shift="${DASH.escapeHtml(beat.shift || '')}" data-y="${yDisp}" onmouseenter="DASH.showArcTooltip(event, this)" onmouseleave="DASH.hideArcTooltip()"/>`;
      if (DASH.arcShowLabels && !DASH.arcMutedChars.has(char.id)) {
        svg += `<text class="beat-label" x="${bx}" y="${by - (beat.is_crisis || beat.is_climax ? 12 : 10)}" text-anchor="middle">${DASH.escapeHtml(beat.label)}</text>`;
      }
    });
  });

  // X-axis (scene names at bottom, positioned within their act band)
  (DASH.story.scenes || []).forEach(scene => {
    const info = sceneActIdx[scene.id];
    let x;
    if (info && info.actIdx !== -1) {
      const innerPos = info.countInAct > 1 ? info.idxInAct / (info.countInAct - 1) : 0.5;
      x = DASH.ARC_PAD.left + (info.actIdx + innerPos) * actBandwidth;
    } else {
      return; // skip scenes with no act mapping
    }
    const y = DASH.ARC_GH - DASH.ARC_PAD.bottom + 14;
    const hasBeats = scene.arc_beats && scene.arc_beats.length > 0;
    if (hasBeats) {
      svg += `<text x="${x}" y="${y}" class="arc-axis-label" text-anchor="middle">${DASH.escapeHtml((scene.title || scene.id || '').split('—')[0].trim())}</text>`;
      svg += `<line x1="${x}" y1="${DASH.ARC_GH - DASH.ARC_PAD.bottom}" x2="${x}" y2="${DASH.ARC_GH - DASH.ARC_PAD.bottom + 4}" class="arc-grid-line"/>`;
    }
  });

  svg += '</svg>';
  wrap.innerHTML = svg;

  // Warnings
  const warningsEl = document.getElementById('arc-warnings');
  if (warningsEl) {
    warningsEl.innerHTML = warnings.map(w => `
      <div class="arc-warning">
        <span class="arc-warning-icon">&#9888;</span>
        <span>${DASH.escapeHtml(w)}</span>
      </div>
    `).join('');
  }
}

DASH.buildCharsGrid = function() {
  const grid = document.getElementById('chars-grid');
  if (!grid) return;
  grid.innerHTML = '';
  (DASH.story.characters || []).forEach(char => {
    const color = DASH.roleColor(char.role || char.story_role || '');
    const div = document.createElement('div');
    div.className = 'char-card';
    div.innerHTML = `
      <div class="char-name" style="color:${color}">${DASH.escapeHtml(char.name)}</div>
      <div class="char-role">
        <span class="char-role-dot" style="background:${color}"></span>
        ${DASH.escapeHtml(char.role || char.story_role || '')}
      </div>
      <div class="char-arc-type">
        <span class="arc-type-badge ${DASH.getArcTypeClass(char.arc_type)}">${char.arc_type || 'absent'}</span>
        ${char.arc_value ? `<span style="font-size:10px;color:var(--muted-foreground)">${DASH.escapeHtml(char.arc_value)}</span>` : ''}
      </div>
      ${char.arc_beat_count > 0
        ? `<div class="char-beat-count">${char.arc_beat_count} beat${char.arc_beat_count !== 1 ? 's' : ''}</div>`
        : `<div class="char-beat-count" style="color:#555">No arc designed</div>`}
    `;
    div.addEventListener('click', () => {
      const wasSelected = div.classList.contains('selected');
      document.querySelectorAll('.char-card').forEach(c => c.classList.remove('selected'));
      if (!wasSelected) {
        div.classList.add('selected');
        DASH.arcMutedChars = new Set((DASH.story.characters || []).filter(c => c.id !== char.id).map(c => c.id));
      } else {
        DASH.arcMutedChars = new Set();
      }
      DASH.buildArcGraph();
      DASH.updateLegend();
    });
    grid.appendChild(div);
  });
}

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
  const container = document.getElementById('DASH.network-canvas');

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
  const seen_roles = new Set();
  chars.forEach(c => seen_roles.add(DASH.getRoleKey(c.role)));
  const roleLegend = [...seen_roles].map(role => {
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


DASH.buildScriptView = function() {
  const stats = window.__SCREENPLAY_STATS__;
  const container = document.getElementById('screenplay-container');
  if (!container) return;

  // No stats or no scriptHtml → empty state
  if (!stats || !stats.scriptHtml) {
    container.innerHTML = '<div class="script-empty"><div class="empty-state-title">No scenes with content yet</div><div class="empty-state-sub">Add content to your scenes to see the script view.</div></div>';
    DASH._scriptBuilt = true;
    return;
  }

  const doc = document.createElement('div');
  doc.className = 'screenplay-doc screenplay-content';

  // ── Title page ──
  if (stats.titlePage) {
    const tp = stats.titlePage;
    const hasContent = Object.values(tp).some(arr => Array.isArray(arr) ? arr.length > 0 : !!arr);
    if (hasContent) {
      const titleTokens = (tp.cc || []);
      const titleText = titleTokens.map(t => t.text || t).join('\n');
      const tl = (tp.tl || []).map(t => t.text || t).join('<br>');
      const tr = (tp.tr || []).map(t => t.text || t).join('<br>');
      const bl = (tp.bl || []).map(t => t.text || t).join('<br>');
      const br = (tp.br || []).map(t => t.text || t).join('<br>');

      // Split title page tokens into title + credit lines
      const titleLines = titleText.split('\n');
      const titleName = titleLines[0] || '';
      const creditLines = titleLines.slice(1).join('<br>');

      const tpEl = document.createElement('div');
      tpEl.className = 'screenplay-title-page';
      tpEl.innerHTML = `
        <div class="title-tl">${tl}</div>
        <div class="title-tc"></div>
        <div class="title-tr">${tr}</div>
        <div class="title-cc">
          <span class="tp-title">${DASH.escapeHtml(titleName)}</span>
          ${creditLines ? `<span class="tp-credit">${creditLines}</span>` : ''}
        </div>
        <div class="title-bl">${bl}</div>
        <div class="title-br">${br}</div>
      `;
      doc.appendChild(tpEl);
    }
  }

  // ── Screenplay body (server-rendered HTML) ──
  const body = document.createElement('div');
  body.innerHTML = stats.scriptHtml;

  // Insert soft page breaks every ~8 scene headings
  let headingCount = 0;
  let pageNum = 1;
  body.querySelectorAll('.fountain-scene_heading').forEach(el => {
    headingCount++;
    if (headingCount > 1 && headingCount % 8 === 1) {
      pageNum++;
      const br = document.createElement('hr');
      br.className = 'screenplay-page-break';
      br.setAttribute('data-page', 'p. ' + pageNum);
      el.parentNode.insertBefore(br, el);
    }
  });

  doc.appendChild(body);

  // ── Wire scene heading clicks ──
  doc.querySelectorAll('.fountain-scene_heading').forEach(el => {
    const rawHeading = el.textContent.replace(/^\d+\.\s*/, '').toUpperCase().trim()
                                     .replace(/\s*\(.*\)\s*$/, '');
    const matched = (DASH.story && DASH.story.scenes || []).find(s => {
      const h = (s.heading || '').toUpperCase().trim().replace(/\s*\(.*\)\s*$/, '');
      return h === rawHeading;
    });
    if (matched) {
      el.style.cursor = 'pointer';
      el.addEventListener('click', () => {
        DASH.showScenePanel(matched.id);
      });
    }
  });

  // Subtitle
  const sceneCount = (DASH.story.scenes || []).length;
  const pages = stats.lengthStats && stats.lengthStats.pagesWhole || '?';
  DASH.setEl('script-subtitle', pages + ' p · ' + sceneCount + ' scenes');

  container.innerHTML = '';
  container.appendChild(doc);
  DASH._scriptBuilt = true;
}


DASH.catmullRomPath = function(pts, alpha = 0.5) {
  if (pts.length < 2) return '';
  const d = [`M ${pts[0][0]} ${pts[0][1]}`];
  for (let i = 0; i < pts.length - 1; i++) {
    const p0 = pts[Math.max(i - 1, 0)];
    const p1 = pts[i];
    const p2 = pts[i + 1];
    const p3 = pts[Math.min(i + 2, pts.length - 1)];
    const cp1x = p1[0] + (p2[0] - p0[0]) / 6;
    const cp1y = p1[1] + (p2[1] - p0[1]) / 6;
    const cp2x = p2[0] - (p3[0] - p1[0]) / 6;
    const cp2y = p2[1] - (p3[1] - p1[1]) / 6;
    d.push(`C ${cp1x} ${cp1y}, ${cp2x} ${cp2y}, ${p2[0]} ${p2[1]}`);
  }
  return d.join(' ');
}

DASH.closePanel = function() { document.getElementById('detail-panel').classList.remove('open'); }

DASH.closeStatsPanel = function() {
  document.getElementById('stats-panel').classList.remove('open');
}


DASH.getArcTypeClass = function(type) {
  const map = {
    negative: 'arc-type-negative',
    positive: 'arc-type-positive',
    flat:     'arc-type-flat',
    ironic:   'arc-type-ironic',
    absent:   'arc-type-absent',
  };
  return map[type] || 'arc-type-flat';
}

DASH.hideArcTooltip = function() {
  const tt = document.getElementById('arc-beat-tooltip');
  if (tt) tt.classList.remove('visible');
}

DASH.openPanel = function() { document.getElementById('detail-panel').classList.add('open'); }

DASH.openStatsPanel = function() {
  if (!DASH._scriptBuilt) DASH.buildScriptView();

  const stats = window.__SCREENPLAY_STATS__;
  if (!stats) {
    // No stats available — show panel with empty state message
    document.getElementById('stats-panel').classList.add('open');
    DASH.closePanel(); // close entity panel if open
    return;
  }

  if (!DASH._statsPopulated) {
    DASH.populateStats(stats);
    DASH._statsPopulated = true;
  }

  document.getElementById('stats-panel').classList.add('open');
  DASH.closePanel();

  // Re-render the active chart in case it was first rendered while hidden
  requestAnimationFrame(() => {
    const activeGroup = document.querySelector('.stats-group.active');
    if (activeGroup) {
      const id = activeGroup.id.replace('stats-group-', '');
      DASH._renderChartsForGroup(id);
    }
  });
}


DASH.populateStats = function(stats) {
  const ls = stats.lengthStats    || {};
  const ds = stats.durationStats  || {};
  const cs = stats.characterStats || {};
  const lo = stats.locationStats  || {};
  const ss = stats.sceneStats     || {};

  // ── Overview: Length ──
  DASH.setEl('lengthStats-pagesWhole', ls.pagesWhole  || '—');
  DASH.setEl('lengthStats-scenes',     ls.scenes      || '—');
  DASH.setEl('lengthStats-words',      (ls.words      || 0).toLocaleString());
  DASH.setEl('lengthStats-lines',      (ls.lines      || 0).toLocaleString());
  DASH.setEl('lengthStats-characters', (ls.characters || 0).toLocaleString());

  // ── Overview: Duration ──
  DASH.setEl('durationStats-total',    DASH.fmtDurationShort(ds.total));
  DASH.setEl('durationStats-action',   DASH.fmtDurationShort(ds.action));
  DASH.setEl('durationStats-dialogue', DASH.fmtDurationShort(ds.dialogue));

  const totalMin = Math.round((ds.total || 0) / 60);
  const actionPct = ds.total > 0 ? Math.round(((ds.action || 0) / ds.total) * 100) : 0;
  const lengthLabel = totalMin < 60 ? 'a short film' :
                      totalMin < 90 ? 'an hour-long film' :
                      totalMin < 120 ? 'a feature film' : 'an epic feature';
  const balanceLabel = actionPct > 65 ? 'action-heavy' :
                       actionPct < 35 ? 'dialogue-heavy' : 'balanced';
  DASH.setEl('durationStats-summary',
    `The screenplay is the length of ${lengthLabel}. It is ${balanceLabel} (${actionPct}% action).`);

  // ── Characters ──
  DASH.setEl('characterStats-count',      cs.characterCount || (cs.characters || []).length);
  DASH.setEl('characterStats-monologues', cs.monologues || 0);

  // Character table
  const chars = cs.characters || [];
  const cTbody = document.querySelector('#characterStats-table tbody');
  if (cTbody) {
    cTbody.innerHTML = chars.map(c => {
      const secs = c.secondsSpoken || 0;
      return `<tr>
        <td><span class="char-pip" style="background:${c.color || '#888'}"></span>${DASH.escapeHtml(c.name)}</td>
        <td data-sort="${secs}">${DASH.fmtDuration(secs)}</td>
        <td>${c.speakingParts || 0}</td>
        <td>${c.wordsSpoken || 0}</td>
        <td>${c.monologues || 0}</td>
      </tr>`;
    }).join('');
    // Default sort: duration desc
    DASH.sortTable('characterStats-table', 1);
  }

  // ── Scenes: counts ──
  const scenes = ss.scenes || [];
  DASH.setEl('sceneStats-count',    scenes.length || ls.scenes || 0);
  DASH.setEl('locationStats-count', lo.locationsCount || (lo.locations || []).length);

  // INT/EXT bars
  const tc = ss.typeCounts || {};
  const totalType = (tc.int || 0) + (tc.ext || 0) + (tc.mixed || 0);
  DASH.setBar('sceneprop-type_int',   tc.int   || 0, totalType);
  DASH.setBar('sceneprop-type_ext',   tc.ext   || 0, totalType);
  DASH.setBar('sceneprop-type_mixed', tc.mixed || 0, totalType);

  // Time-of-day bars
  const timec = ss.timeCounts || {};
  const totalTime = Object.values(timec).reduce((a, b) => a + b, 0);
  DASH.setBar('sceneprop-time_day',     timec.day     || 0, totalTime);
  DASH.setBar('sceneprop-time_night',   timec.night   || 0, totalTime);
  DASH.setBar('sceneprop-time_morning', timec.morning || 0, totalTime);
  DASH.setBar('sceneprop-time_evening', timec.evening || 0, totalTime);
  DASH.setBar('sceneprop-time_dawn',    timec.dawn    || 0, totalTime);
  DASH.setBar('sceneprop-time_dusk',    timec.dusk    || 0, totalTime);

  // Location table
  const locs = lo.locations || [];
  const lTbody = document.querySelector('#locationStats-table tbody');
  if (lTbody) {
    lTbody.innerHTML = locs.map(l => {
      const type = (l.interior_exterior || []).join('/').toUpperCase() || '—';
      return `<tr>
        <td><span class="char-pip" style="background:${l.color || '#888'}"></span>${DASH.escapeHtml(l.name)}</td>
        <td>${l.number_of_scenes || 0}</td>
        <td>${type}</td>
      </tr>`;
    }).join('');
    DASH.sortTable('locationStats-table', 1);
  }

  // ── Structural stats (from window.__STRUCTURAL_STATS__) ──
  if (!DASH._structuralStatsPopulated) {
    DASH.populateStructuralStats();
    DASH._structuralStatsPopulated = true;
  }
}

DASH.populateStructuralStats = function() {
  const ss = window.__STRUCTURAL_STATS__;
  if (!ss) return;

  DASH.setEl('structStats-scenes', ss.sceneCount || '—');
  DASH.setEl('structStats-sequences', ss.sequenceCount || '—');
  DASH.setEl('structStats-acts', ss.actCount || '—');

  // Scene status bars
  const statusContainer = document.getElementById('structStats-status-bars');
  if (statusContainer) {
    const statusColors = { planned: '#888', drafted: '#e0c96b', written: '#6bbfb0', locked: '#7b9cf0' };
    const status = ss.sceneStatus || {};
    const total = Object.values(status).reduce((a, b) => a + b, 0);
    statusContainer.innerHTML = Object.entries(status).map(([key, count]) => {
      const pct = total > 0 ? Math.round((count / total) * 100) : 0;
      return `<div class="duration-bar-row">
        <span class="duration-bar-label">${DASH.escapeHtml(key)}</span>
        <div class="duration-bar-track"><div class="duration-bar-fill" style="background:${statusColors[key] || '#888'};width:${pct}%"></div></div>
        <span class="duration-bar-value">${count}</span>
      </div>`;
    }).join('') || '<div class="panel-muted" style="font-size:var(--font-size-xs);">No scenes.</div>';
  }

  // Dramatic role bars
  const roleContainer = document.getElementById('structStats-role-bars');
  if (roleContainer) {
    const roleColors = { setup: '#7b9cf0', complication: '#e0c96b', crisis: '#e07070', climax: '#b07be0', resolution: '#6bbfb0', transition: '#888', unset: '#444' };
    const roles = ss.sceneRoles || {};
    const total = Object.values(roles).reduce((a, b) => a + b, 0);
    roleContainer.innerHTML = Object.entries(roles).map(([key, count]) => {
      const pct = total > 0 ? Math.round((count / total) * 100) : 0;
      return `<div class="duration-bar-row">
        <span class="duration-bar-label">${DASH.escapeHtml(key)}</span>
        <div class="duration-bar-track"><div class="duration-bar-fill" style="background:${roleColors[key] || '#888'};width:${pct}%"></div></div>
        <span class="duration-bar-value">${count}</span>
      </div>`;
    }).join('') || '<div class="panel-muted" style="font-size:var(--font-size-xs);">No roles assigned.</div>';
  }

  // Plot coverage bars
  const plotContainer = document.getElementById('structStats-plot-coverage');
  if (plotContainer) {
    const plotColors = { main: '#b07be0', Contradictory: '#e07070', Resonant: '#7b9cf0', Complicating: '#e0a86b', Setup: '#6bbfb0' };
    const coverage = ss.plotCoverage || [];
    if (coverage.length) {
      const maxCount = Math.max(...coverage.map(p => p.sceneCount));
      plotContainer.innerHTML = coverage.map(p => {
        const col = plotColors[p.plot_scope] || (plotColors[p.plot_type] || '#888');
        const pct = maxCount > 0 ? Math.round((p.sceneCount / maxCount) * 100) : 0;
        const label = p.plot_scope === 'main' ? `${p.name} (MAIN)` : p.name;
        return `<div class="duration-bar-row">
          <span class="duration-bar-label" style="color:${col}">${DASH.escapeHtml(label)}</span>
          <div class="duration-bar-track"><div class="duration-bar-fill" style="background:${col};width:${pct}%"></div></div>
          <span class="duration-bar-value">${p.sceneCount} (${p.coveragePct}%)</span>
        </div>`;
      }).join('');
    } else {
      plotContainer.innerHTML = '<div class="panel-muted" style="font-size:var(--font-size-xs);">No plot coverage data.</div>';
    }
  }

  // Act list
  const actContainer = document.getElementById('structStats-act-list');
  if (actContainer) {
    const acts = ss.acts || [];
    actContainer.innerHTML = acts.map(a =>
      `<div class="beat-row">
        <span class="beat-scene">${DASH.escapeHtml(a.title || a.id)}</span>
        <span class="beat-desc">${a.sceneCount || 0} scenes · ${a.sequenceCount || 0} sequences</span>
      </div>`
    ).join('') || '<div class="panel-muted" style="font-size:var(--font-size-xs);">No acts.</div>';
  }

  // Arc design summary
  const arcContainer = document.getElementById('structStats-arc-summary');
  if (arcContainer) {
    const chars = DASH.story.characters || [];
    const charsWithArcs = chars.filter(c => c.arc_type && c.arc_type !== 'absent' && c.arc_beats_list && c.arc_beats_list.length > 0);
    const totalArcBeats = chars.reduce((sum, c) => sum + (c.arc_beats_list ? c.arc_beats_list.length : 0), 0);
    if (charsWithArcs.length > 0) {
      arcContainer.innerHTML = `<div style="margin-bottom:6px;font-size:var(--font-size-sm);color:var(--foreground);margin-top:2px">${charsWithArcs.length} characters · ${totalArcBeats} beats designed</div>` +
        charsWithArcs.map(c => {
          const col = DASH.roleColor(c.role || c.story_role || '');
          return `<div style="display:flex;align-items:center;gap:6px;margin-bottom:4px">
            <span class="legend-dot" style="background:${col}"></span>
            <span style="font-size:var(--font-size-sm)">${DASH.escapeHtml(c.name)}</span>
            <span class="panel-muted" style="margin-left:auto;font-size:var(--font-size-xs)">${c.arc_type} · ${c.arc_beats_list.length} beats</span>
          </div>`;
        }).join('');
    } else {
      arcContainer.innerHTML = '<div class="panel-muted" style="font-size:var(--font-size-xs);">No character arcs designed.</div>';
    }
  }
}

DASH.positionArcTooltip = function(e) {
  const tt = document.getElementById('arc-beat-tooltip');
  if (!tt) return;
  tt.style.left = Math.min(e.clientX + 14, window.innerWidth - 220) + 'px';
  tt.style.top = Math.max(e.clientY - 40, 8) + 'px';
}

DASH.renderBarcodeChart = function(mode) {
  DASH._currentBarcodeMode = mode;
  const container = document.getElementById('sceneStats-timechart');
  if (!container || !window.d3) return;
  container.innerHTML = '';

  const stats = window.__SCREENPLAY_STATS__;
  const scenes = stats && stats.sceneStats && stats.sceneStats.scenes || [];
  if (!scenes.length) return;

  const TYPE_COL = { int:'#7b9cf0', ext:'#6bbfb0', mixed:'#e0a86b', other:'#555' };
  const TIME_COL = {
    dawn:'#e06b9b', morning:'#e07070', day:'#e0c96b',
    afternoon:'#e0c96b', evening:'#b07be0', dusk:'#6bbfb0',
    night:'#7b9cf0', continuous:'#555', later:'#555', unspecified:'#333'
  };

  const W = container.clientWidth || 320;
  const H = container.clientHeight || 44;
  const pad = 3;
  const bw = Math.max(1.5, (W - pad * 2) / scenes.length);

  const svg = d3.select(container).append('svg').attr('width', W).attr('height', H);
  svg.selectAll('rect').data(scenes).enter().append('rect')
    .attr('x',      (d, i) => pad + i * bw)
    .attr('y',      0)
    .attr('width',  Math.max(1, bw - 0.5))
    .attr('height', H)
    .attr('fill',   d => mode === 'type'
      ? (TYPE_COL[d.locType] || TYPE_COL.other)
      : (TIME_COL[d.locTime] || TIME_COL.unspecified))
    .attr('rx', 1)
    .append('title').text(d => d.text || d.number);
}

DASH.renderCharacterChart = function(stats) {
  const container = document.getElementById('characterStats-lengthchart');
  if (!container || !window.d3) return;
  container.innerHTML = '';

  const chars = ((stats.characterStats || {}).characters || []).slice(0, 8);
  if (!chars.length) return;

  const W = container.clientWidth  || 320;
  const H = container.clientHeight || 110;
  const mg = { top: 6, right: 8, bottom: 18, left: 70 };
  const w = W - mg.left - mg.right;
  const h = H - mg.top  - mg.bottom;

  const svg = d3.select(container).append('svg').attr('width',W).attr('height',H);
  const g = svg.append('g').attr('transform',`translate(${mg.left},${mg.top})`);

  const maxSec = d3.max(chars, c => c.secondsSpoken || 0) || 1;
  const x = d3.scaleLinear().domain([0, maxSec]).range([0, w]);
  const y = d3.scaleBand().domain(chars.map(c => c.name)).range([0, h]).padding(0.25);

  g.selectAll('rect').data(chars).enter().append('rect')
    .attr('x', 0)
    .attr('y', d => y(d.name))
    .attr('height', y.bandwidth())
    .attr('width', d => x(d.secondsSpoken || 0))
    .attr('fill', d => d.color || '#7b9cf0')
    .attr('rx', 2);

  g.append('g').call(d3.axisLeft(y).tickSize(0))
    .selectAll('text').style('font-size','9px').attr('dx','-3').attr('fill','var(--muted-foreground)');
  g.append('g').attr('transform',`translate(0,${h})`)
    .call(d3.axisBottom(x).ticks(4).tickFormat(d => DASH.fmtDurationShort(d)))
    .selectAll('text').style('font-size','9px').attr('fill','var(--muted-foreground)');
  g.selectAll('.domain,.tick line').attr('stroke','rgba(255,255,255,0.12)');
}

DASH.renderDurationChart = function(stats) {
  DASH._ensureChartRendered('durationStats-lengthchart', () => {
    DASH._renderDurationChart(stats);
  });
}


DASH.renderSectionsHtml = function(entityType, slug) {
  const data = (window.__SECTIONS__ && window.__SECTIONS__[entityType] && window.__SECTIONS__[entityType][slug]);
  if (!data) return '';
  return Object.entries(data).map(([name, content]) => `
    <div>
      <div class="panel-section-title">${name}</div>
      <div class="panel-text">${DASH.escapeHtml(content).replace(/\n/g, '<br>')}</div>
    </div>
  `).join('');
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

DASH.showActPanel = function(actId) {
  const act = (DASH.story.acts || []).find(a => a.id === actId);
  if (!act) return;

  document.getElementById('panel-type').textContent = 'Act';
  document.getElementById('panel-name').textContent = act.title || act.id;

  const seqRows = (act.sequences_list || []).map(sid => {
    const seq = (DASH.story.sequences || []).find(s => s.id === sid);
    return seq ? `<div class="beat-row" onclick="DASH.showSequencePanel('${sid}')">
      <span class="beat-scene">${seq.title || sid}</span>
      <span class="beat-desc">${seq.scene_count || 0} scenes</span>
    </div>` : '';
  }).join('');

  // Plot threads in this act with scope/type
  const plotRows = (act.plots || []).map(p => {
    const pl = (DASH.story.plots || []).find(x => x.id === p.id);
    if (!pl) return '';
    const scope = pl.plot_scope === 'main' ? 'MAIN' : (pl.plot_type || '');
    const col = pl.plot_scope === 'main' ? '#b07be0' : (DASH.PLOT_TYPE_COLORS[pl.plot_type] || '#888');
    return `<div class="beat-row" onclick="DASH.showPlotPanel('${pl.id}')">
      <span class="beat-scene" style="color:${col}">${pl.name}</span>
      ${scope ? `<span class="beat-desc" style="color:${col}">${scope}</span>` : ''}
      ${p.has_setup ? '<span class="beat-desc">setup</span>' : ''}
      ${p.has_crisis ? '<span class="beat-desc">crisis</span>' : ''}
      ${p.has_climax ? '<span class="beat-desc">climax</span>' : ''}
      ${p.has_payoff ? '<span class="beat-desc">payoff</span>' : ''}
    </div>`;
  }).join('');

  document.getElementById('panel-body').innerHTML = `
    <div><span class="status-badge ${act.status || ''}">${act.status || 'planned'}</span></div>
    ${(() => {
      const projectSpine = (DASH.story.project || {}).spine;
      const actObj = act.act_objective;
      if (!projectSpine && !actObj) return '';
      return `<div style="margin-top:8px">
        ${projectSpine ? `<div style="font-size:var(--font-size-xs);color:var(--muted-foreground);margin-bottom:4px">Story spine: <span style="font-style:italic">${projectSpine}</span></div>` : ''}
        ${actObj ? `<div style="font-size:var(--font-size-xs);color:var(--muted-foreground)">Act objective: <span style="color:var(--foreground);font-weight:500">${actObj}</span></div>` : ''}
      </div>`;
    })()}
    ${plotRows ? `<div><div class="panel-section-title">Plot threads</div>${plotRows}</div>` : ''}
    ${seqRows ? `<div><div class="panel-section-title">Sequences (${act.sequence_count || 0})</div>${seqRows}</div>` : '<div class="panel-muted">No sequences in this act yet.</div>'}
  `;

  document.getElementById('panel-footer').innerHTML = `
    <button class="btn btn-hermes" data-hermes-send="What is the dramatic arc of '${act.title || act.id}'?">Ask Hermes about this act</button>
  `;

  DASH.openPanel();
}

DASH.showArcTooltip = function(e, el) {
  const tt = document.getElementById('arc-beat-tooltip');
  if (!tt) return;
  document.getElementById('tt-label').textContent = el.dataset.label;
  document.getElementById('tt-char').textContent = el.dataset.char;
  document.getElementById('tt-shift').textContent = el.dataset.shift || '';
  document.getElementById('tt-value').innerHTML = `Value charge: <strong>${el.dataset.y}</strong>`;
  tt.classList.add('visible');
  DASH.positionArcTooltip(e);
}

DASH.showCharacterPanel = function(char) {
  document.getElementById('panel-type').textContent = char.role || char.story_role || 'Character';
  document.getElementById('panel-name').textContent = char.name;

  // Scenes: char.scenes is normalised to an array of scene ids (strings)
  const scenes = (char.scenes || []).map(sid => {
    const s = (DASH.story.scenes || []).find(x => String(x.id) === String(sid));
    if (s) {
      const num = s.number != null ? String(s.number) : '';
      const label = num ? `${num}. ${s.title || s.id}` : (s.title || s.id);
      return `<span class="tag tag-scene" style="cursor:pointer" onclick="DASH.showScenePanel('${s.id}')">${label}</span>`;
    }
    return sid ? `<span class="tag tag-scene">${sid}</span>` : '';
  }).filter(Boolean).join('');

  // Relationships: use relationships[] (new schema) with type + strength
  const rels = (char.relationships || []).map(rel => {
    const c = (DASH.story.characters || []).find(x => x.id === rel.with);
    const nameEl = c
      ? `<button class="relationship-name entity-link" onclick="DASH.showCharacterPanel(DASH.story.characters.find(x=>x.id==='${c.id}'))">${c.name}</button>`
      : `<span class="relationship-name">${rel.with}</span>`;
    const secretIcon = rel.secret ? ' 🔒' : '';
    const typeTag = rel.type ? `<span class="tag" style="background:${DASH.relTypeColor(rel.type)}22;color:${DASH.relTypeColor(rel.type)}">${rel.type}</span>` : '';
    return `
      <div class="relationship-row">
        ${nameEl}${secretIcon}
        ${rel.label ? `<span class="relationship-label">${rel.label}</span>` : ''}
        ${typeTag}
        ${rel.strength !== undefined ? `<span class="relationship-feeling">strength: ${rel.strength > 0 ? '+' : ''}${rel.strength}</span>` : ''}
      </div>`;
  }).join('');

  // Knowledge: may be array (_knowledge_arr) or string
  const knowledgeArr = char._knowledge_arr || (char.knowledge ? [char.knowledge] : []);
  const knowledgeHtml = knowledgeArr.length
    ? knowledgeArr.map(k => `<div class="knowledge-item">${k}</div>`).join('')
    : '';

  document.getElementById('panel-body').innerHTML = `
    <div>
      <div class="panel-section-title">In one sentence</div>
      <div class="panel-text">${char.one_sentence || '—'}</div>
    </div>
    ${char.age ? `<div><div class="panel-section-title">Age</div><div class="panel-muted">${char.age}</div></div>` : ''}
    ${char.goals_short ? `<div>
      <div class="panel-section-title">Immediate goal</div>
      <div class="panel-text">${char.goals_short}</div>
    </div>` : ''}
    ${char.goals_long ? `<div>
      <div class="panel-section-title">Deeper goal</div>
      <div class="panel-muted">${char.goals_long}</div>
    </div>` : ''}
    ${knowledgeHtml ? `<div>
      <div class="panel-section-title">What they know</div>
      ${knowledgeHtml}
    </div>` : ''}
    ${scenes ? `<div>
      <div class="panel-section-title">Appears in</div>
      <div class="panel-tags">${scenes}</div>
    </div>` : ''}
    ${rels ? `<div>
      <div class="panel-section-title">Relationships</div>
      ${rels}
    </div>` : ''}
    <div>
      <div class="panel-section-title">Arc</div>
      ${DASH.arcSectionHtml(char)}
    </div>
    ${DASH.renderSectionsHtml('character', char.id)}
  `;

  document.getElementById('panel-footer').innerHTML = `
    <button class="btn btn-hermes" data-hermes-send="Tell me more about ${char.name}'s character development.">Ask Hermes about ${char.name}</button>
  `;

  DASH.openPanel();

  if (DASH.network) {
    DASH.network.selectNodes([char.id]);
    DASH.network.focus(char.id, { scale: 1.2, animation: { duration: 400, easingFunction: 'easeInOutQuad' } });
  }
}

DASH.showLocationPanel = function(locId) {
  // Deselect all entity cards, select the one clicked
  document.querySelectorAll('#location-list .entity-card').forEach(el => el.classList.remove('selected'));
  const card = document.querySelector(`#location-list .entity-card[data-id="${locId}"]`);
  if (card) card.classList.add('selected');

  const loc = (DASH.story.locations || []).find(l => l.id === locId);
  if (!loc) return;

  document.getElementById('panel-type').textContent = 'Location';
  document.getElementById('panel-name').textContent = loc.name;

  // Backend gives loc.scenes as heading strings; find scene objects by heading
  const sceneRefs = loc._scene_headings || loc.scenes || [];
  const scenes = sceneRefs.map(ref => {
    const s = (DASH.story.scenes || []).find(x =>
      x.heading === ref || String(x.id) === String(ref)
    );
    if (s) {
      const num = s.number != null ? String(s.number) : '';
      const label = num ? `${num}. ${s.heading || s.id}` : (s.heading || s.id);
      return `<span class="tag tag-scene" style="cursor:pointer" onclick="DASH.showScenePanel('${s.id}')">${label}</span>`;
    }
    return `<span class="tag tag-scene">${ref}</span>`;
  }).join('');

  // Find scenes that reference this location for "Appears in" section
  const appearScenes = (DASH.story.scenes || []).filter(s => s.location === loc.id);
  const appearsIn = appearScenes.map(s => {
    const num = s.number != null ? String(s.number) : '';
    const label = num ? `${num}. ${s.heading || s.id}` : (s.heading || s.id);
    return `<span class="tag tag-scene" style="cursor:pointer" onclick="DASH.showScenePanel('${s.id}')">${label}</span>`;
  }).join('');

  // Characters in this location (via their scenes)
  const charIds = new Set();
  sceneRefs.forEach(ref => {
    const s = (DASH.story.scenes || []).find(x => x.heading === ref || String(x.id) === String(ref));
    if (s) (s.characters || []).forEach(cid => charIds.add(cid));
  });
  const charLinks = [...charIds].map(cid => {
    const c = (DASH.story.characters || []).find(x => x.id === cid || String(x.id) === String(cid));
    return c ? `<button class="entity-link" onclick="DASH.showCharacterPanel(DASH.story.characters.find(x=>x.id==='${c.id}'))" style="border-left:2px solid ${DASH.roleColor(c.role)}">${c.name}</button>` : '';
  }).filter(Boolean).join('');

  document.getElementById('panel-body').innerHTML = `
    <div>
      <div class="panel-section-title">In one sentence</div>
      <div class="panel-text">${loc.one_sentence || '—'}</div>
    </div>
    ${loc.mood ? `<div>
      <div class="panel-section-title">Mood</div>
      <div class="panel-text" style="font-style:italic">${loc.mood}</div>
    </div>` : ''}
    ${loc.dramatic_function ? `<div>
      <div class="panel-section-title">Dramatic function</div>
      <div class="panel-text">${loc.dramatic_function}</div>
    </div>` : ''}
    ${loc.world ? `<div>
      <div class="panel-section-title">World</div>
      <div class="panel-text">${loc.world}</div>
    </div>` : ''}
    ${loc.variant_of ? `<div>
      <div class="panel-section-title">Variant of</div>
      ${(() => {
        const v = DASH.findLocation(loc.variant_of);
        return v ? `<button class="entity-link" onclick="DASH.showLocationPanel('${v.id}')">${v.name}</button>` : `<div class="panel-text" style="color:#e0a86b">${loc.variant_of}</div>`;
      })()}
    </div>` : ''}
    ${charLinks ? `<div>
      <div class="panel-section-title">Characters here</div>
      <div style="display:flex;flex-direction:column;gap:4px;">${charLinks}</div>
    </div>` : ''}
    ${appearsIn ? `<div>
      <div class="panel-section-title">Appears in</div>
      <div class="panel-tags">${appearsIn}</div>
    </div>` : ''}
    ${DASH.renderSectionsHtml('location', loc.id)}
  `;

  document.getElementById('panel-footer').innerHTML = `
    <button class="btn btn-hermes" data-hermes-send="Describe ${loc.name} and its role in the DASH.story.">Ask Hermes about this location</button>
  `;

  DASH.openPanel();
}

DASH.showPlotPanel = function(plotId) {
  document.querySelectorAll('#plot-list .entity-card').forEach(el => el.classList.remove('selected'));
  const card = document.querySelector(`#plot-list .entity-card[data-id="${plotId}"]`);
  if (card) card.classList.add('selected');

  const plot = (DASH.story.plots || []).find(p => p.id === plotId || String(p.id) === String(plotId));
  if (!plot) return;

  const scope = plot.plot_scope === 'main' ? 'MAIN' : (plot.plot_type || '');
  const col = plot.plot_scope === 'main' ? '#b07be0' : (DASH.PLOT_TYPE_COLORS[plot.plot_type] || '#888');
  const scopeHtml = scope ? `<span class="tag" style="background:${col}22;color:${col}">${scope}</span>` : '';
  const arcHtml = (plot.plot_scope === 'main' && plot.value_arc) ? `<div style="margin-top:4px"><span style="color:var(--muted-foreground);font-size:var(--font-size-xs);text-transform:uppercase;letter-spacing:0.06em">Value Arc</span><div style="font-size:var(--font-size-sm);color:var(--foreground)">${plot.value_arc}</div></div>` : '';

  document.getElementById('panel-type').textContent = plot.plot_scope === 'main' ? 'Main Plot' : 'Subplot';
  document.getElementById('panel-name').textContent = plot.name;

  const chars = (plot.characters || []).map(cid => {
    const c = (DASH.story.characters || []).find(x => x.id === cid || String(x.id) === String(cid));
    return c
      ? `<button class="entity-link" onclick="DASH.showCharacterPanel(DASH.story.characters.find(x=>x.id==='${c.id}'))" style="border-left:2px solid ${DASH.roleColor(c.role)}">${c.name}</button>`
      : '';
  }).filter(Boolean).join('');

  // Setups/payoffs: [{scene_id, description}] (backend-normalized)
  function renderBeats(arr) {
    if (!arr || !arr.length) return '';
    return arr.map(item => {
      if (typeof item === 'string') {
        return `<div class="beat-row">${item}</div>`;
      }
      // Backend normalizes to {scene_id, description}
      const sceneObj = (DASH.story.scenes || []).find(s => String(s.id) === String(item.scene_id));
      const displayNum = sceneObj && sceneObj.order != null ? String(sceneObj.order) : '';
      const sceneName = sceneObj ? (sceneObj.title || sceneObj.id) : (item.scene_id || '');
      if (!sceneName) return '';
      const sceneLink = sceneObj
        ? `<span class="beat-scene" onclick="DASH.showScenePanel('${sceneObj.id}')" style="cursor:pointer">${displayNum ? displayNum + '. ' : ''}${sceneName}</span>`
        : `<span class="beat-scene">${displayNum ? displayNum + '. ' : ''}${sceneName}</span>`;
      return `<div class="beat-row">${sceneLink}${item.description ? `<span class="beat-desc">${item.description}</span>` : ''}</div>`;
    }).join('');
  }

  const setupObjs = plot.setups || [];
  const crisisObjs = plot.crisis || [];
  const climaxObjs = plot.climax || [];
  const payoffObjs = plot.payoffs || [];
  const setupsHtml = renderBeats(setupObjs);
  const crisisHtml = renderBeats(crisisObjs);
  const climaxHtml = renderBeats(climaxObjs);
  const payoffsHtml = renderBeats(payoffObjs);

  document.getElementById('panel-body').innerHTML = `
    <div>
      <div class="panel-section-title">Thread</div>
      <div class="panel-text">${plot.one_sentence || '—'}</div>
    </div>
    <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap">
      ${scopeHtml}
      <span class="status-badge ${plot.status || ''}">${plot.status || 'active'}</span>
    </div>
    ${arcHtml}
    ${chars ? `<div>
      <div class="panel-section-title">Characters involved</div>
      <div style="display:flex;flex-direction:column;gap:4px;">${chars}</div>
    </div>` : ''}
    ${setupsHtml ? `<div>
      <div class="panel-section-title">Setups</div>
      ${setupsHtml}
    </div>` : ''}
    ${crisisHtml ? `<div>
      <div class="panel-section-title">Crisis</div>
      ${crisisHtml}
    </div>` : ''}
    ${climaxHtml ? `<div>
      <div class="panel-section-title">Climax</div>
      ${climaxHtml}
    </div>` : ''}
    ${payoffsHtml ? `<div>
      <div class="panel-section-title">Payoffs</div>
      ${payoffsHtml}
    </div>` : ''}
    ${DASH.renderSectionsHtml('plot', plot.id)}
  `;

  document.getElementById('panel-footer').innerHTML = '';
  DASH.openPanel();
}

DASH.showRelationshipPanel = function(rel) {
  const a = rel.characters[0];
  const b = rel.characters[1];
  const charA = (DASH.story.characters || []).find(c => c.id === a);
  const charB = (DASH.story.characters || []).find(c => c.id === b);
  const pa = (rel.perspectives || {})[a] || {};
  const pb = (rel.perspectives || {})[b] || {};

  const nameA = charA
    ? `<button class="entity-link" onclick="DASH.showCharacterPanel(DASH.story.characters.find(x=>x.id==='${a}'))" style="border-left:2px solid ${DASH.roleColor(charA.role)}">${charA.name}</button>`
    : `<span class="panel-muted">${a}</span>`;
  const nameB = charB
    ? `<button class="entity-link" onclick="DASH.showCharacterPanel(DASH.story.characters.find(x=>x.id==='${b}'))" style="border-left:2px solid ${DASH.roleColor(charB.role)}">${charB.name}</button>`
    : `<span class="panel-muted">${b}</span>`;

  function perspectiveHtml(charName, charRole, p) {
    if (!charName) return '';
    const col = DASH.relTypeColor(p.type);
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
    const s = (DASH.story.scenes || []).find(x => String(x.id) === String(sid));
    if (s) {
      const num = s.number != null ? String(s.number) : '';
      const label = num ? `${num}. ${s.title || s.id}` : (s.title || s.id);
      return `<span class="tag tag-scene" style="cursor:pointer" onclick="DASH.showScenePanel('${s.id}')">${label}</span>`;
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
      <div class="panel-text">${DASH.escapeHtml(rel.history).replace(/\n/g, '<br>')}</div>
    </div>` : ''}
  `;

  document.getElementById('panel-footer').innerHTML = `
    <button class="btn btn-hermes" data-hermes-send="Update the relationship between ${charA?.name || a} and ${charB?.name || b}. Current status: ${rel.status || 'active'}. Tell me what changed and why.">Edit with Hermes</button>
  `;

  DASH.openPanel();
}

DASH.showScenePanel = function(sceneId) {
  const scene = (DASH.story.scenes || []).find(s => String(s.id) === String(sceneId));
  if (!scene) return;

  document.querySelectorAll('.scene-item').forEach(el => el.classList.remove('selected'));
  const sceneEl = document.querySelector(`.scene-item[data-id="${sceneId}"]`);
  if (sceneEl) sceneEl.classList.add('selected');

  document.getElementById('panel-type').textContent = 'Scene';
  document.getElementById('panel-name').textContent = scene.title || scene.id;

  const chars = (scene.characters || []).map(cid => {
    const c = (DASH.story.characters || []).find(x => x.id === cid || String(x.id) === String(cid));
    return c
      ? `<button class="entity-link" onclick="DASH.showCharacterPanel(DASH.story.characters.find(x=>x.id==='${c.id}'))" style="border-left:2px solid ${DASH.roleColor(c.role)}">${c.name}</button>`
      : '';
  }).filter(Boolean).join('');

  const locs = (scene.locations || []).map(lref => {
    const l = DASH.findLocation(lref);
    return l ? `<button class="entity-link" onclick="DASH.showLocationPanel('${l.id}')">${l.name}</button>` : '';
  }).filter(Boolean).join('');

  // Plots: backend populates scene.plots from plot setups/payoffs
  const plotRefs = (scene.plots || []);
  const plots = plotRefs.map(pref => {
    const pid = (typeof pref === 'object' && pref !== null) ? pref.id : pref;
    const beat = (typeof pref === 'object' && pref !== null) ? (pref.beat || '') : '';
    const pl = (DASH.story.plots || []).find(x => x.id === pid || String(x.id) === String(pid));
    if (!pl) return '';
    const scope = pl.plot_scope === 'main' ? 'MAIN' : (pl.plot_type || '');
    const col = pl.plot_scope === 'main' ? '#b07be0' : (DASH.PLOT_TYPE_COLORS[pl.plot_type] || '#888');
    const beatLabel = beat ? ` · ${beat.toUpperCase()}` : '';
    const scopeLabel = scope ? ` · ${scope}` : '';
    return `<button class="entity-link" onclick="DASH.showPlotPanel('${pl.id}')" style="border-left:2px solid ${col}">${pl.name}<span style="color:${col};font-size:var(--font-size-xs);margin-left:4px">${scopeLabel}${beatLabel}</span></button>`;
  }).filter(Boolean).join('');

  // Content from __SECTIONS__.scenes[slug]["Content"]
  let contentHtml = '';
  const sections = window.__SECTIONS__;
  const sceneContent = sections?.scene?.[sceneId]?.Content;
  if (sceneContent) {
    contentHtml = `<div class="fountain-content">${DASH.escapeHtml(sceneContent)}</div>`;
  } else {
    contentHtml = '<div class="panel-muted">No content yet.</div>';
  }

  // Dramatic metadata — only show positive values
  const dramaTags = [];
  if (scene.dramatic_role) dramaTags.push({ l: 'role', v: scene.dramatic_role });
  if (scene.is_inciting_incident) dramaTags.push({ l: 'inciting', v: 'Inciting Incident' });
  if (scene.is_sequence_climax) dramaTags.push({ l: 'seq-climax', v: 'Sequence Climax' });
  if (scene.is_act_climax) dramaTags.push({ l: 'act-climax', v: 'Act Climax' });
  if (scene.is_story_climax) dramaTags.push({ l: 'DASH.story-climax', v: 'Story Climax' });

  const valueArc = [scene.value, scene.value_open, scene.value_close].filter(Boolean);
  const conflicts = (scene.conflict_levels || []).filter(Boolean);

  const dramaHtml = (dramaTags.length || valueArc.length || conflicts.length) ? `
    <div>
      <div style="display:flex;flex-wrap:wrap;gap:4px;margin-bottom:8px">
        ${dramaTags.map(t => `<span class="tag tag-struct">${t.v}</span>`).join('')}
        ${conflicts.map(c => `<span class="tag tag-char" style="font-size:var(--font-size-xs)">${c}</span>`).join('')}
      </div>
      ${valueArc.length ? `<div style="font-size:var(--font-size-xs);color:var(--muted-foreground);margin-bottom:8px">Value arc: ${valueArc.join(' → ')}</div>` : ''}
    </div>` : '';

  document.getElementById('panel-body').innerHTML = `
    ${dramaHtml}
    ${chars ? `<div>
      <div class="panel-section-title">Characters</div>
      <div style="display:flex;flex-direction:column;gap:4px;">${chars}</div>
    </div>` : ''}
    ${locs ? `<div>
      <div class="panel-section-title">Location</div>
      <div style="display:flex;flex-wrap:wrap;gap:4px;">${locs}</div>
    </div>` : ''}
    ${plots ? `<div>
      <div class="panel-section-title">Plot threads</div>
      <div style="display:flex;flex-direction:column;gap:4px;">${plots}</div>
    </div>` : ''}
    ${scene.heading ? `<div>
      <div class="panel-section-title">Screenplay heading</div>
      <div class="panel-muted">${DASH.escapeHtml(scene.heading)}</div>
    </div>` : ''}
    <div>
      <div class="panel-section-title">Content</div>
      ${contentHtml}
    </div>
  `;

  document.getElementById('panel-footer').innerHTML = `
    <button class="btn btn-hermes" data-hermes-send="What happens in ${scene.title || scene.id}?">Ask Hermes about this scene</button>
  `;

  DASH.openPanel();
}

DASH.showSequencePanel = function(seqId) {
  const seq = (DASH.story.sequences || []).find(s => s.id === seqId);
  if (!seq) return;

  document.getElementById('panel-type').textContent = 'Sequence';
  document.getElementById('panel-name').textContent = seq.title || seq.id;

  const sceneRows = (seq.scenes_list || []).map((sid, i) => {
    const scene = (DASH.story.scenes || []).find(s => s.id === sid);
    if (!scene) return '';
    return `<div class="beat-row" onclick="DASH.showScenePanel('${sid}')">
      <span class="beat-scene">${i + 1}. ${scene.title || sid}</span>
      ${scene.heading ? `<span class="beat-desc">${DASH.escapeHtml(scene.heading)}</span>` : ''}
    </div>`;
  }).join('');

  // Plot threads in this sequence with scope/type
  const plotRows = (seq.plots || []).map(p => {
    const pl = (DASH.story.plots || []).find(x => x.id === p.id);
    if (!pl) return '';
    const scope = pl.plot_scope === 'main' ? 'MAIN' : (pl.plot_type || '');
    const col = pl.plot_scope === 'main' ? '#b07be0' : (DASH.PLOT_TYPE_COLORS[pl.plot_type] || '#888');
    return `<div class="beat-row" onclick="DASH.showPlotPanel('${pl.id}')">
      <span class="beat-scene" style="color:${col}">${pl.name}</span>
      ${scope ? `<span class="beat-desc" style="color:${col}">${scope}</span>` : ''}
      ${p.has_setup ? '<span class="beat-desc">setup</span>' : ''}
      ${p.has_crisis ? '<span class="beat-desc">crisis</span>' : ''}
      ${p.has_climax ? '<span class="beat-desc">climax</span>' : ''}
      ${p.has_payoff ? '<span class="beat-desc">payoff</span>' : ''}
    </div>`;
  }).join('');

  document.getElementById('panel-body').innerHTML = `
    <div><span class="status-badge ${seq.status || ''}">${seq.status || 'planned'}</span></div>
    ${plotRows ? `<div><div class="panel-section-title">Plot threads</div>${plotRows}</div>` : ''}
    ${sceneRows ? `<div><div class="panel-section-title">Scenes (${seq.scene_count || 0})</div>${sceneRows}</div>` : '<div class="panel-muted">No scenes in this sequence yet.</div>'}
  `;

  document.getElementById('panel-footer').innerHTML = `
    <button class="btn btn-hermes" data-hermes-send="What is the dramatic function of the sequence '${seq.title || seq.id}'?">Ask Hermes about this sequence</button>
  `;

  DASH.openPanel();
}

DASH.showWorldPanel = function(worldId) {
  document.querySelectorAll('#world-list .entity-card').forEach(el => el.classList.remove('selected'));
  const card = document.querySelector(`#world-list .entity-card[data-id="${worldId}"]`);
  if (card) card.classList.add('selected');

  const world = (DASH.story.worlds || []).find(w => w.id === worldId);
  if (!world) return;

  document.getElementById('panel-type').textContent = 'World';
  document.getElementById('panel-name').textContent = world.name;

  const rules = (world.rules || []).map(r =>
    `<div class="world-rule">${r}</div>`
  ).join('');

  const sections = (world.sections || []).join(', ');

  // Plots in this world
  const worldPlots = (DASH.story.plots || []).filter(pl =>
    (pl.worlds || []).includes(worldId) ||
    (pl.world === worldId)
  );
  const plotLinks = worldPlots.map(pl =>
    `<button class="entity-link" onclick="DASH.showPlotPanel('${pl.id}')">${pl.name}</button>`
  ).join('');

  document.getElementById('panel-body').innerHTML = `
    <div>
      <div class="panel-section-title">In one sentence</div>
      <div class="panel-text">${world.one_sentence || '—'}</div>
    </div>
    ${world.period ? `<div>
      <div class="panel-section-title">Period</div>
      <div class="panel-text">${world.period}</div>
    </div>` : ''}
    ${(world.values && world.values.length) ? `<div>
      <div class="panel-section-title">Values</div>
      <div class="panel-text">${world.values.map(v => `<div class="world-rule">${v}</div>`).join('')}</div>
    </div>` : ''}
    ${(world.power && world.power.length) ? `<div>
      <div class="panel-section-title">Power</div>
      <div class="panel-text">${world.power.map(p => `<div class="world-rule">${p}</div>`).join('')}</div>
    </div>` : ''}
    ${rules ? `<div>
      <div class="panel-section-title">Rules</div>
      ${rules}
    </div>` : ''}
    ${world.variant_of ? `<div>
      <div class="panel-section-title">Variant of</div>
      ${(() => {
        const v = (DASH.story.worlds || []).find(w => w.id === world.variant_of);
        return v ? `<button class="entity-link" onclick="DASH.showWorldPanel('${v.id}')">${v.name}</button>` : `<div class="panel-text" style="color:#e0a86b">${world.variant_of}</div>`;
      })()}
    </div>` : ''}
    ${plotLinks ? `<div>
      <div class="panel-section-title">Plot threads</div>
      <div style="display:flex;flex-direction:column;gap:4px;">${plotLinks}</div>
    </div>` : ''}
    ${DASH.renderSectionsHtml('world', world.id)}
  `;

  document.getElementById('panel-footer').innerHTML = '';
  DASH.openPanel();
}

DASH.sortTable = function(tableId, colIdx) {
  const table = document.getElementById(tableId);
  if (!table) return;
  const th = table.querySelectorAll('thead th')[colIdx];
  const isNum = th.dataset.type === 'num';
  const wasAsc = th.classList.contains('sort-asc');
  const wasDesc = th.classList.contains('sort-desc');
  // Reset all headers
  table.querySelectorAll('thead th').forEach(h => h.classList.remove('sort-asc','sort-desc'));
  if (!wasAsc && !wasDesc) {
    th.classList.add(isNum ? 'sort-desc' : 'sort-asc');
  } else {
    th.classList.add(wasDesc ? 'sort-asc' : 'sort-desc');
  }
  const asc = th.classList.contains('sort-asc');

  const tbody = table.querySelector('tbody');
  const rows = [...tbody.querySelectorAll('tr')];
  rows.sort((a, b) => {
    const aText = a.cells[colIdx]?.textContent.trim() || '';
    const bText = b.cells[colIdx]?.textContent.trim() || '';
    if (isNum) {
      // extract leading number (handles "1:23" duration, plain integers, etc.)
      const aNum = parseFloat(a.cells[colIdx]?.dataset.sort || aText) || 0;
      const bNum = parseFloat(b.cells[colIdx]?.dataset.sort || bText) || 0;
      return asc ? aNum - bNum : bNum - aNum;
    }
    return asc ? aText.localeCompare(bText) : bText.localeCompare(aText);
  });
  rows.forEach(r => tbody.appendChild(r));
}

DASH.toggleArcCharMute = function(charId) {
  if (DASH.arcMutedChars.has(charId)) DASH.arcMutedChars.delete(charId);
  else DASH.arcMutedChars.add(charId);
  document.querySelectorAll('.char-card').forEach(c => c.classList.remove('selected'));
  DASH.buildArcGraph();
  DASH.updateLegend();
}

DASH.toggleArcLabels = function() {
  DASH.arcShowLabels = !DASH.arcShowLabels;
  document.getElementById('btn-labels')?.classList.toggle('btn-primary', DASH.arcShowLabels);
  DASH.buildArcGraph();
}

DASH.toggleArcSpline = function() {
  DASH.arcUseSpline = !DASH.arcUseSpline;
  document.getElementById('btn-spline')?.classList.toggle('btn-primary', DASH.arcUseSpline);
  DASH.buildArcGraph();
}

DASH.updateLegend = function() {
  const legend = document.getElementById('arc-legend');
  if (!legend) return;
  const chars = (DASH.story.characters || []).filter(c =>
    c.arc_type && c.arc_type !== 'absent' && c.arc_beats_list && c.arc_beats_list.length > 0
  );
  legend.innerHTML = chars.map(char => {
    const color = DASH.roleColor(char.role || char.story_role || '');
    const muted = DASH.arcMutedChars.has(char.id) ? ' muted' : '';
    return `<div class="legend-item${muted}" onclick="DASH.toggleArcCharMute('${char.id}')">
      <div class="legend-line" style="background:${color}"></div>
      <span>${DASH.escapeHtml(char.name)}</span>
      <span class="legend-arc-type">${char.arc_type}</span>
    </div>`;
  }).join('') + `
    <div class="legend-item" style="gap:12px;margin-left:auto">
      <div style="display:flex;align-items:center;gap:4px"><div class="legend-dot" style="background:#ffd93d"></div><span>crisis</span></div>
      <div style="display:flex;align-items:center;gap:4px"><div class="legend-dot" style="background:transparent;border:1px solid #e8e8e8"></div><span>climax</span></div>
    </div>`;
}

document.addEventListener('mousemove', e => {
  const tt = document.getElementById('arc-beat-tooltip');
  if (tt?.classList.contains('visible')) DASH.positionArcTooltip(e);
});
