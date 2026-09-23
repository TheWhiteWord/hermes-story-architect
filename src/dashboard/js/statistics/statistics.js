window.DASH = window.DASH || {};

DASH._statsPopulated = false;
DASH._structuralStatsPopulated = false;


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

DASH.switchStatsGroup = function(group, btn) {
  document.querySelectorAll('.stats-group').forEach(g => g.classList.remove('active'));
  document.querySelectorAll('.stats-tab').forEach(b => b.classList.remove('active'));
  document.getElementById('stats-group-' + group).classList.add('active');
  btn.classList.add('active');
  // Charts must be drawn into a visible container
  requestAnimationFrame(() => DASH._renderChartsForGroup(group));
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
