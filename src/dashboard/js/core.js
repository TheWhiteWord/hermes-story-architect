// ─── Boot ─────────────────────────────────────────────────────────────────────
window.DASH = window.DASH || {};

let story = null;

let network = null;

let _scriptBuilt = false;

let _statsPopulated = false;

let _structuralStatsPopulated = false;

let _currentBarcodeMode = 'type';

let _chartObservers = {};


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


DASH.closeStatsPanel = function() {
  document.getElementById('stats-panel').classList.remove('open');
}



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





