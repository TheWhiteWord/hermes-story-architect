window.DASH = window.DASH || {};

DASH.arcUseSpline = false;
DASH.arcShowLabels = true;
DASH.arcMutedChars = new Set();
DASH.arcStoryMuted = false;

DASH.ARC_GW = 760;
DASH.ARC_GH = 320;
DASH.ARC_PAD = { top: 28, right: 40, bottom: 36, left: 42 };

DASH.arcXScale = function(t) {
  return DASH.ARC_PAD.left + t * (DASH.ARC_GW - DASH.ARC_PAD.left - DASH.ARC_PAD.right);
}

DASH.arcYScale = function(v) {
  return DASH.ARC_PAD.top + (1 - (v + 1) / 2) * (DASH.ARC_GH - DASH.ARC_PAD.top - DASH.ARC_PAD.bottom);
}

// The story's own line, in a colour that is not a role colour: the character
// arcs are coloured by role, the story value is the spine they all sit on.
DASH.STORY_COLOR = '#f0f0f0';

// scene id → { actIdx, idxInAct, countInAct }
DASH.scenePositions = function() {
  const acts = DASH.story.acts || [];
  const scenes = DASH.story.scenes || [];
  const actById = {};
  acts.forEach((a, i) => { actById[a.id] = i; });
  const inAct = {};
  scenes.forEach(s => {
    if (s.act_id != null) (inAct[s.act_id] = inAct[s.act_id] || []).push(s);
  });
  Object.values(inAct).forEach(list => list.sort((a, b) => a.order - b.order));
  const pos = {};
  scenes.forEach(s => {
    const list = inAct[s.act_id];
    if (s.act_id == null || !list) return;
    pos[s.id] = {
      actIdx: actById[s.act_id] != null ? actById[s.act_id] : -1,
      idxInAct: list.findIndex(x => x.id === s.id),
      countInAct: list.length,
    };
  });
  return pos;
}

// Position along the x-axis (0..1) for a scene id, or null if it has no act mapping.
// Scenes sit at the centre of their slot within the act band, so a band owns
// [actIdx, actIdx+1) exclusively and no two scenes ever share an x. Spanning
// edge-to-edge instead would put an act's last scene and the next act's first
// on the same pixel.
DASH.sceneT = function(pos, sceneId) {
  const info = pos[sceneId];
  if (!info || info.actIdx === -1) return null;
  return (info.actIdx + (info.idxInAct + 0.5) / info.countInAct)
    / (DASH.story.project.act_count || 3);
}

// One point per scene that records an ending charge, in story order. Same
// polyline as a character arc, different source: the story value turns in its
// own scenes, so the curve is drawn through them.
DASH.storySeries = function(pos) {
  return (DASH.story.scenes || [])
    .map(s => ({ scene: s, t: DASH.sceneT(pos, s.id), y: s.y }))
    .filter(p => p.t != null && typeof p.y === 'number')
    .sort((a, b) => a.t - b.t);
}

DASH.buildArcGraph = function() {
  const wrap = document.getElementById('arc-graph-wrap');
  if (!wrap) return;

  const chars = (DASH.story.characters || []).filter(c =>
    c.arc_type && c.arc_type !== 'absent' && c.arc_beats_list && c.arc_beats_list.length > 0
  );

  const actCount = DASH.story.project.act_count || 3;
  const acts = DASH.story.acts || [];
  const scenes = DASH.story.scenes || [];
  const sceneActIdx = DASH.scenePositions();
  const storyPts = DASH.storySeries(sceneActIdx);

  // Either track alone is worth drawing: a story curve with no character arcs
  // is a real state (a project mid-write), not an empty graph.
  if (chars.length === 0 && storyPts.length === 0) {
    wrap.innerHTML = `
      <div class="arc-empty">
        <div class="arc-empty-icon">&#9670;</div>
        <div class="arc-empty-title">No value trajectories yet</div>
        <div class="arc-empty-text">Record a scene's ending charge (y) or design a character arc to see value trajectories plotted here.</div>
        <button class="btn btn-hermes" data-hermes-send="Design a character arc for the protagonist showing their value shift across the DASH.story.">Design arc with Hermes</button>
      </div>`;
    return;
  }

  function beatX(char, beat) {
    const t = DASH.sceneT(sceneActIdx, beat.scene);
    if (t == null) {
      // Fallback: use beat order within character arc
      return (beat.order - 1) / (char.arc_beat_count || 1);
    }
    return t;
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

  // The story value's own curve, drawn under the character arcs: same engine,
  // one point per scene that records an ending charge. No heuristics are run
  // on it — "flat" and "jump too far" are judgements about a character, and
  // the story is allowed to hold steady across an act.
  if (storyPts.length > 0 && !DASH.arcStoryMuted) {
    const pts = storyPts.map(p => [DASH.arcXScale(p.t), DASH.arcYScale(p.y)]);
    if (DASH.arcUseSpline && pts.length > 2) {
      svg += `<path class="arc-line story-line" d="${DASH.catmullRomPath(pts)}" stroke="${DASH.STORY_COLOR}" stroke-opacity="0.9"/>`;
    } else {
      svg += `<polyline class="arc-line story-line" points="${pts.map(p => p.join(',')).join(' ')}" stroke="${DASH.STORY_COLOR}" stroke-opacity="0.9"/>`;
    }
    storyPts.forEach(p => {
      const px = DASH.arcXScale(p.t);
      const py = DASH.arcYScale(p.y);
      const yDisp = p.y >= 0 ? `+${p.y.toFixed(2)}` : p.y.toFixed(2);
      svg += `<circle class="story-point" cx="${px}" cy="${py}" r="5" fill="${DASH.STORY_COLOR}" data-label="${DASH.escapeHtml(p.scene.title || p.scene.id || '')}" data-char="${DASH.escapeHtml(DASH.story.project.story_value || 'the story value')}" data-shift="${DASH.escapeHtml(p.scene.shift || '')}" data-y="${yDisp}" onmouseenter="DASH.showArcTooltip(event, this)" onmouseleave="DASH.hideArcTooltip()"/>`;
    });
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

  // X-axis (scene names at bottom, positioned within their act band). A scene
  // is labelled when something is plotted on it — a beat or a story point.
  const storySceneIds = new Set(storyPts.map(p => p.scene.id));
  scenes.forEach(scene => {
    const t = DASH.sceneT(sceneActIdx, scene.id);
    if (t == null) return; // skip scenes with no act mapping
    const hasBeats = scene.arc_beats && scene.arc_beats.length > 0;
    if (!hasBeats && !storySceneIds.has(scene.id)) return;
    const x = DASH.arcXScale(t);
    const y = DASH.ARC_GH - DASH.ARC_PAD.bottom + 14;
    svg += `<text x="${x}" y="${y}" class="arc-axis-label" text-anchor="middle">${DASH.escapeHtml((scene.title || scene.id || '').split('—')[0].trim())}</text>`;
    svg += `<line x1="${x}" y1="${DASH.ARC_GH - DASH.ARC_PAD.bottom}" x2="${x}" y2="${DASH.ARC_GH - DASH.ARC_PAD.bottom + 4}" class="arc-grid-line"/>`;
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
        ${char.character_value ? `<span style="font-size:10px;color:var(--muted-foreground)">${DASH.escapeHtml(char.character_value)}</span>` : ''}
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

DASH.positionArcTooltip = function(e) {
  const tt = document.getElementById('arc-beat-tooltip');
  if (!tt) return;
  tt.style.left = Math.min(e.clientX + 14, window.innerWidth - 220) + 'px';
  tt.style.top = Math.max(e.clientY - 40, 8) + 'px';
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

DASH.toggleArcCharMute = function(charId) {
  if (DASH.arcMutedChars.has(charId)) DASH.arcMutedChars.delete(charId);
  else DASH.arcMutedChars.add(charId);
  document.querySelectorAll('.char-card').forEach(c => c.classList.remove('selected'));
  DASH.buildArcGraph();
  DASH.updateLegend();
}

DASH.toggleArcStory = function() {
  DASH.arcStoryMuted = !DASH.arcStoryMuted;
  document.getElementById('btn-story')?.classList.toggle('btn-primary', !DASH.arcStoryMuted);
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
  const storyWord = DASH.story.project.story_value;
  const storyItem = DASH.storySeries(DASH.scenePositions()).length > 0 ? `
    <div class="legend-item${DASH.arcStoryMuted ? ' muted' : ''}" onclick="DASH.toggleArcStory()">
      <div class="legend-line" style="background:${DASH.STORY_COLOR}"></div>
      <span>${DASH.escapeHtml(storyWord || 'Story value')}</span>
    </div>` : '';
  legend.innerHTML = storyItem + chars.map(char => {
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
