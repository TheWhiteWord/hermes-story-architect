// Value graphs: a story-level and a plot-level lane chart.
//
// Reads what the dashboard payload already carries:
//   DASH.story.scenes[].value_turns   [{plot, value, from, to, effects:[{character, levels:[{conflict_level, effect}]}]}]
//   DASH.story.acts / sequences       for story order and the bands
//   DASH.story.plots[].value_focus    major / minor values of a plot
//   DASH.story.project.value_focus    major / minor values of the story
//   DASH.story.values                 [{name, p, c, cd, nn, note}]  (NEW: the schemas, to place a word on a lane)
//
// Draws SVG strings. No libraries, no stored data.
window.DASH = window.DASH || {};

(function (D) {
  'use strict';

  const LANES = ['p', 'c', 'cd', 'nn'];                       // rung 0..3, top to bottom: distance from the ideal
  const LEVELS = ['inner', 'personal', 'extra-personal'];
  const LEVEL_SHORT = { inner: 'inner', personal: 'personal', 'extra-personal': 'extra-pers.' };
  const GEO = { labelW: 118, minSlot: 14, padR: 14 };

  const MILESTONES = {
    setup:              { label: 'Setup',            color: '#6bbfb0', shape: 'dot' },
    inciting_incident:  { label: 'Inciting Incident', color: '#7b9cf0', shape: 'diamond' },
    complication:        { label: 'Complication',      color: '#e0a86b', shape: 'dot' },
    crisis:             { label: 'Crisis',           color: '#e0707d', shape: 'dot' },
    climax:             { label: 'Climax',           color: '#ffd93d', shape: 'star' },
    resolution:         { label: 'Resolution',       color: '#b07be0', shape: 'dot' },
  };

  const starPath = (cx, cy, outerR, innerR) => {
    const pts = [];
    for (let i = 0; i < 10; i++) {
      const r = i % 2 === 0 ? outerR : innerR;
      const a = (i * Math.PI / 5) - Math.PI / 2;
      pts.push(`${i === 0 ? 'M' : 'L'}${(cx + r * Math.cos(a)).toFixed(1)},${(cy + r * Math.sin(a)).toFixed(1)}`);
    }
    return pts.join(' ') + ' Z';
  };

  const state = { tab: 'story', plot: null };
  D.valueGraphState = state;
  let vgUid = 0;

  // ---------- helpers
  const norm = s => String(s == null ? '' : s).trim().toLowerCase();
  const cut = (s, n) => { s = String(s == null ? '' : s); return s.length > n ? s.slice(0, Math.max(1, n - 1)) + '\u2026' : s; };
  const cmpKey = (a, b) => { for (let i = 0; i < a.length; i++) { if (a[i] < b[i]) return -1; if (a[i] > b[i]) return 1; } return 0; };
  const plotColor = pid => (D.plotColor ? D.plotColor(pid) : '#888');

  // ---------- model: story order, bands, lines
  // Scenes in story order (act, sequence, scene): the payload lists scenes by id, and a scene's
  // own `order` restarts in every sequence, so the order is rebuilt from the three levels.
  D.valueModel = function (story) {
    story = story || D.story || {};
    const acts = (story.acts || []).slice().sort((a, b) => (a.order || 0) - (b.order || 0));
    const actIdx = new Map(acts.map((a, i) => [a.id, i]));
    const seqById = new Map((story.sequences || []).map(q => [q.id, q]));
    const keyOf = s => {
      const q = seqById.get(s.sequence_id || s.parent_id);
      const aid = (q && q.parent_id) || s.act_id;
      return [actIdx.has(aid) ? actIdx.get(aid) : 1e6, q ? (q.order || 0) : 1e6, s.order || 0, String(s.id)];
    };
    const scenes = (story.scenes || []).slice().sort((a, b) => cmpKey(keyOf(a), keyOf(b)));
    const idxOf = new Map(scenes.map((s, i) => [s.id, i]));

    const bandOf = (items, groupOf, nameOf) => {
      const out = new Map();
      scenes.forEach((s, i) => {
        const id = groupOf(s);
        if (id == null || id === '') return;
        const r = out.get(id);
        if (r) r.end = i; else out.set(id, { id, name: nameOf(id), start: i, end: i });
      });
      return [...out.values()];
    };
    const actName = id => { const a = acts.find(x => x.id === id); return a ? (a.name || a.id) : id; };
    const seqName = id => { const q = seqById.get(id); return q ? (q.name || q.id) : id; };
    const actBands = bandOf(acts, s => { const q = seqById.get(s.sequence_id || s.parent_id); return (q && q.parent_id) || s.act_id; }, actName);
    const seqBands = bandOf([], s => s.sequence_id || s.parent_id, seqName);
    // per-act sequence numbering: S1, S2, S3 within each act
    const seqNums = new Map();
    const seqsByAct = new Map();
    (story.sequences || []).forEach(q => {
      const aid = q.parent_id;
      if (!seqsByAct.has(aid)) seqsByAct.set(aid, []);
      seqsByAct.get(aid).push(q);
    });
    seqsByAct.forEach(list => list.sort((a, b) => (a.order || 0) - (b.order || 0)));
    seqsByAct.forEach(list => list.forEach((q, i) => seqNums.set(q.id, `S${i + 1}`)));

    const schemas = new Map();
    (story.values || []).forEach(v => schemas.set(norm(v.name), v));
    const rungOf = (value, word) => {
      const sc = schemas.get(norm(value)), w = norm(word);
      if (!sc || !w) return null;
      for (let r = 0; r < 4; r++) if (norm(sc[LANES[r]]) === w) return r;
      return norm(sc.name) === w ? 0 : null;           // the value's own name is its positive word
    };
    const charName = new Map((story.characters || []).map(c => [c.id, c.name || c.id]));
    const plotName = new Map((story.plots || []).map(p => [p.id, p.name || p.id]));

    const lines = new Map();  // Map<plot, Map<normValue, line>>
    scenes.forEach((s, i) => (s.value_turns || []).forEach(t => {
      const plotKey = t.plot;
      const valKey = norm(t.value);
      if (!lines.has(plotKey)) lines.set(plotKey, new Map());
      const byValue = lines.get(plotKey);
      let line = byValue.get(valKey);
      if (!line) {
        line = { key: plotKey + ':' + valKey, plot: t.plot, value: (schemas.get(valKey) || {}).name || t.value, turns: [] };
        byValue.set(valKey, line);
      }
      const levels = new Set(), effects = [];
      (t.effects || []).forEach(e => (e.levels || []).forEach(l => {
        levels.add(l.conflict_level);
        effects.push({ character: charName.get(e.character) || e.character, level: l.conflict_level, effect: l.effect || '' });
      }));
      line.turns.push({
        i, sceneId: s.id, title: s.title || s.name || s.id,
        from: t.from, to: t.to,
        fromRung: rungOf(t.value, t.from), toRung: rungOf(t.value, t.to),
        levels, effects,
      });
    }));

    const allLines = [];
    lines.forEach(byValue => byValue.forEach(line => allLines.push(line)));

    return {
      n: scenes.length, scenes, idxOf, acts: actBands, seqs: seqBands,
      seqNums, lines: allLines, schemas, plotName,
    };
  };

  // ---------- geometry
  D.valueGeometry = function (model, width) {
    const n = Math.max(model.n, 1);
    const avail = Math.max((width || 900) - GEO.labelW - GEO.padR, n * GEO.minSlot);
    const slot = Math.max(GEO.minSlot, avail / n);
    return { slot, labelW: GEO.labelW, W: GEO.labelW + n * slot + GEO.padR };
  };

  // ---------- axis: 3 sections — acts, sequences, milestones
  D.valueAxisSvg = function (model, geo) {
    const H = 62, X = i => geo.labelW + (i + 0.5) * geo.slot, p = [];
    // Section 1: acts (y 0-18)
    model.acts.forEach((a, k) => {
      const x = geo.labelW + a.start * geo.slot, w = (a.end - a.start + 1) * geo.slot;
      p.push(`<rect class="vg-band ${k % 2 ? 'odd' : 'even'}" x="${x}" y="0" width="${w}" height="18"/>`);
      p.push(`<text class="vg-act-label" x="${x + 5}" y="12">${DASH.escapeHtml(cut(a.name, Math.max(3, Math.floor(w / 6))))}</text>`);
    });
    // Section 2: sequences with per-act S numbering (y 22-40)
    model.seqs.forEach(q => {
      const x = geo.labelW + q.start * geo.slot, w = (q.end - q.start + 1) * geo.slot;
      if (q.start > 0) p.push(`<line class="vg-seq-line" x1="${x}" y1="22" x2="${x}" y2="40"/>`);
      const label = model.seqNums.get(q.id) || q.name;
      p.push(`<text class="vg-seq-label" x="${x + 4}" y="33">${DASH.escapeHtml(label)}</text>`);
    });
    // Section 3: milestones (y 44-62)
    model.scenes.forEach((s, i) => {
      (s.milestone || []).forEach(m => {
        const cfg = MILESTONES[m];
        if (!cfg) return;
        const x = X(i), y = 50;
        if (cfg.shape === 'star') {
          p.push(`<path d="${starPath(x, y, 5, 2.2)}" fill="${cfg.color}"/>`);
        } else if (cfg.shape === 'diamond') {
          p.push(`<rect x="${x - 3.5}" y="${y - 3.5}" width="7" height="7" transform="rotate(45 ${x} ${y})" fill="${cfg.color}"/>`);
        } else {
          p.push(`<circle cx="${x}" cy="${y}" r="3" fill="${cfg.color}"/>`);
        }
      });
    });
    return `<svg class="vg-svg vg-axis" viewBox="0 0 ${geo.W} ${H}">${p.join('')}</svg>`;
  };

  // ---------- one value: four lanes, shifts as spans, optional level strip
  // o: { value, lines, compact, strip (bool), uid }
  D.valueChartSvg = function (model, geo, o) {
    const compact = !!o.compact;
    const laneH = compact ? 11 : 26, top = 6, laneBlock = laneH * 4;
    const useStrip = !compact && !!o.strip;
    const rowH = 12, stripTop = top + laneBlock + 12;
    const H = top + laneBlock + 6 + (useStrip ? 12 + 3 * rowH : 0) + 4;
    const Y = r => top + (r + 0.5) * laneH;
    const X = i => geo.labelW + (i + 0.5) * geo.slot;
    const uid = o.uid || 'vg';
    const schema = model.schemas.get(norm(o.value)) || {};
    const p = [];

    p.push(`<defs><pattern id="${uid}-h" width="5" height="5" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="5" class="vg-hatch"/></pattern></defs>`);
    model.acts.forEach((a, k) => p.push(
      `<rect class="vg-band ${k % 2 ? 'odd' : 'even'}" x="${geo.labelW + a.start * geo.slot}" y="0" width="${(a.end - a.start + 1) * geo.slot}" height="${H}"/>`));
    // the negation-of-negation lane is hatched: a corrupted positive, not just "more negative"
    p.push(`<rect x="${geo.labelW}" y="${top + 3 * laneH}" width="${model.n * geo.slot}" height="${laneH}" fill="url(#${uid}-h)"/>`);
    const labelCls = compact ? 'vg-label vg-label-compact' : 'vg-label';
    for (let r = 0; r < 4; r++) {
      p.push(`<line class="vg-lane-line" x1="${geo.labelW}" y1="${Y(r)}" x2="${geo.W - GEO.padR + 6}" y2="${Y(r)}"/>`);
      p.push(`<text class="${labelCls}" x="${geo.labelW - 8}" y="${Y(r) + 3}" text-anchor="end">${DASH.escapeHtml(cut(schema[LANES[r]] || (r === 0 ? o.value : ''), 17))}</text>`);
    }
    model.seqs.forEach(q => { if (q.start > 0) p.push(`<line class="vg-seq-line" x1="${geo.labelW + q.start * geo.slot}" y1="0" x2="${geo.labelW + q.start * geo.slot}" y2="${H}"/>`); });

    if (useStrip) {
      LEVELS.forEach((lv, k) => p.push(
        `<text class="vg-label vg-label-strip" x="${geo.labelW - 8}" y="${stripTop + k * rowH + 7}" text-anchor="end">${LEVEL_SHORT[lv]}</text>` +
        `<line class="vg-lane-line" x1="${geo.labelW}" y1="${stripTop + k * rowH + 5}" x2="${geo.W - GEO.padR + 6}" y2="${stripTop + k * rowH + 5}"/>`));
    }

    // hover columns: one per scene that has a shift of this value, with a title listing them
    const byScene = new Map();
    o.lines.forEach(line => line.turns.forEach(t => {
      if (!byScene.has(t.i)) byScene.set(t.i, []);
      byScene.get(t.i).push({ line, t });
    }));
    byScene.forEach((items, i) => {
      const first = items[0].t;
      const text = [`Scene ${i + 1}: ${first.title}`].concat(items.map(({ line, t }) => {
        const head = `${model.plotName.get(line.plot) || line.plot}: ${t.from || '?'} \u2192 ${t.to || '?'}`;
        return [head].concat(t.effects.map(e => `  ${e.character} (${e.level}): ${e.effect}`)).join('\n');
      })).join('\n');
      p.push(`<rect class="vg-col" data-scene="${DASH.escapeHtml(first.sceneId)}" x="${geo.labelW + i * geo.slot}" y="0" width="${geo.slot}" height="${H}"><title>${DASH.escapeHtml(text)}</title></rect>`);
    });

    const k = compact ? 0.7 : 1;
    // several shifts in one scene (two plots, or two characters) sit side by side, not on top of each other
    const totals = new Map(); o.lines.forEach(l => l.turns.forEach(t => totals.set(t.i, (totals.get(t.i) || 0) + 1)));
    const seen = new Map();
    o.lines.forEach(line => {
      const col = plotColor(line.plot);
      let prev = null;
      line.turns.forEach(t => {
        const n = seen.get(t.i) || 0; seen.set(t.i, n + 1);
        const x = X(t.i) + (n - (totals.get(t.i) - 1) / 2) * 5;
        const yF = t.fromRung == null ? null : Y(t.fromRung);
        const yT = t.toRung == null ? null : Y(t.toRung);
        // carried: from where the line ended to where this scene opens
        if (prev && prev.y != null && yF != null) {
          // flat: the line carried on. Slanted: this scene opens somewhere else (a flashback, a time skip, a break)
          const jump = prev.rung !== t.fromRung;
          p.push(`<line class="${jump ? 'vg-jump' : 'vg-carry'}" x1="${prev.x}" y1="${prev.y}" x2="${x}" y2="${yF}" stroke="${col}"/>`);
        }
        if (yF != null && yT != null && t.fromRung === t.toRung) {
          // same state: a dashed pill, a real state and not "nothing happened"
          p.push(`<rect class="vg-hold" x="${x - 6 * k}" y="${yT - 3 * k}" width="${12 * k}" height="${6 * k}" rx="${3 * k}" stroke="${col}"/>`);
        } else if (yF != null && yT != null) {
          p.push(`<line class="vg-span" x1="${x}" y1="${yF}" x2="${x}" y2="${yT}" stroke="${col}" stroke-width="${5 * k}"/>`);
          p.push(dot(x, yF, 2.7 * k, col, t.fromRung === 3, true));
          p.push(dot(x, yT, 4.4 * k, col, t.toRung === 3, false));
        } else if (yT != null) {
          p.push(dot(x, yT, 4.4 * k, col, t.toRung === 3, false));
        } else if (yF != null) {
          p.push(dot(x, yF, 2.7 * k, col, t.fromRung === 3, true));
        } else {
          p.push(`<text class="vg-unknown" x="${x}" y="${top + 2 * laneH + 4}" text-anchor="middle"><title>The word is not in this value's schema</title>?</text>`);
        }
        if (useStrip) {
          LEVELS.forEach((lv, m) => {
            if (!t.levels.has(lv)) return;
            const txt = t.effects.filter(e => e.level === lv).map(e => `${e.character}: ${e.effect}`).join('\n');
            p.push(`<rect class="vg-lvl" x="${x - Math.min(geo.slot * 0.34, 7)}" y="${stripTop + m * rowH + 1}" width="${Math.min(geo.slot * 0.68, 14)}" height="8" rx="2.5" fill="${col}"><title>${DASH.escapeHtml(`${LEVEL_SHORT[lv]}\n${txt}`)}</title></rect>`);
          });
        }
        prev = { x, y: yT, rung: t.toRung };
      });
    });

    return `<svg class="vg-svg" viewBox="0 0 ${geo.W} ${H}">${p.join('')}</svg>`;
  };

  // end marker of a shift: a dot, or a hollow ring in the negation-of-negation lane
  function dot(x, y, r, col, ring, small) {
    if (ring) return `<circle class="vg-ring" cx="${x}" cy="${y}" r="${r}" stroke="${col}"/>`;
    return small
      ? `<circle class="vg-from" cx="${x}" cy="${y}" r="${r}" stroke="${col}"/>`
      : `<circle cx="${x}" cy="${y}" r="${r}" fill="${col}"/>`;
  }

  // ---------- html around the charts
  const legendHtml = () => `<div class="vg-legend">
    <span class="vg-legend-item"><svg width="16" height="26"><line class="vg-span" x1="8" y1="5" x2="8" y2="20" stroke="var(--accent)" stroke-width="5"/><circle class="vg-from" cx="8" cy="5" r="2.7" stroke="var(--accent)"/><circle cx="8" cy="20" r="4.4" fill="var(--accent)"/></svg>shift in a scene (small ring = from, dot = to)</span>
    <span class="vg-legend-item"><svg width="18" height="26"><rect class="vg-hold" x="3" y="10" width="12" height="6" rx="3" stroke="var(--accent)"/></svg>stayed in the same state</span>
    <span class="vg-legend-item"><svg width="22" height="26"><line class="vg-carry" x1="2" y1="13" x2="20" y2="13" stroke="var(--accent)"/></svg>carried on between scenes</span>
    <span class="vg-legend-item"><svg width="22" height="26"><line class="vg-jump" x1="2" y1="5" x2="20" y2="21" stroke="var(--accent)"/></svg>the next scene opens elsewhere</span>
    <span class="vg-legend-item"><svg width="18" height="26"><circle class="vg-ring" cx="9" cy="13" r="4.4" stroke="var(--accent)"/></svg>negation of the negation (hatched lane)</span>
  </div>`;

  const milestoneLegendHtml = () => `<div class="vg-legend vg-legend-milestones">
    <span class="vg-legend-note">Milestones:</span>
    ${Object.entries(MILESTONES).map(([key, m]) => {
      const icon = m.shape === 'star'
        ? `<svg width="12" height="12"><path d="${starPath(6, 6, 5, 2)}" fill="${m.color}"/></svg>`
        : m.shape === 'diamond'
        ? `<svg width="10" height="10"><rect x="1.5" y="1.5" width="7" height="7" transform="rotate(45 5 5)" fill="${m.color}"/></svg>`
        : `<svg width="10" height="10"><circle cx="5" cy="5" r="3" fill="${m.color}"/></svg>`;
      return `<span class="vg-legend-item">${icon}${m.label}</span>`;
    }).join('')}
  </div>`;

  const plotDots = (model, lines) => {
    const ids = [...new Set(lines.map(l => l.plot))];
    return ids.map(id => `<span class="vg-plot"><i style="background:${plotColor(id)}"></i>${DASH.escapeHtml(model.plotName.get(id) || id)}</span>`).join('');
  };

  const sceneCount = lines => new Set([].concat(...lines.map(l => l.turns.map(t => t.i)))).size;

  function panel(model, geo, name, lines, o) {
    const head = `<span class="vg-title">${DASH.escapeHtml(name)}</span><span class="vg-meta">${sceneCount(lines)} scene${sceneCount(lines) === 1 ? '' : 's'}</span>${plotDots(model, lines)}`;
    const uid = 'vg' + (++vgUid);
    return `<div class="vg-panel${o.compact ? ' compact' : ''}"><div class="vg-panel-head">${head}</div>${D.valueChartSvg(model, geo, Object.assign({ value: name, lines, uid }, o))}</div>`;
  }

  const empty = () => `<div class="arc-empty"><div class="arc-empty-icon">\u25E6</div><div class="arc-empty-title">No value shifts recorded yet</div><div class="arc-empty-text">Value shifts appear here once the value pass has recorded them on scenes.</div></div>`;

  // value names to draw, in order: the focus lists first, then anything else that has turns
  function orderedValues(model, focus, onlyPlot) {
    const lines = model.lines.filter(l => !onlyPlot || l.plot === onlyPlot);
    const present = new Map();
    lines.forEach(l => { const k = norm(l.value); present.set(k, (present.get(k) || 0) + l.turns.length); });
    const pick = list => (list || []).map(x => x.value).filter(v => present.has(norm(v)));
    const major = pick(focus && focus.major), minor = pick(focus && focus.minor);
    const used = new Set([...major, ...minor].map(norm));
    const rest = [...present.keys()].filter(k => !used.has(k)).sort((a, b) => present.get(b) - present.get(a));
    const nameOf = k => (lines.find(l => norm(l.value) === k) || {}).value;
    return { major, minor: minor.concat(rest.map(nameOf)), lines };
  }

  // ---------- story-level graph: every major value, then every minor one, all plots
  D.renderValueStory = function (el) {
    const S = D.story || {}, model = D.valueModel(S);
    if (!model.lines.length) { el.innerHTML = empty(); return; }
    const geo = D.valueGeometry(model, el.clientWidth);
    const v = orderedValues(model, (S.project || {}).value_focus, null);
    const pnl = (names, o) => names.map(n => panel(model, geo, n, v.lines.filter(l => norm(l.value) === norm(n)), o)).join('');
    el.innerHTML = `<div class="vg-stack">${legendHtml()}${milestoneLegendHtml()}
      <div class="vg-axis-wrap">${D.valueAxisSvg(model, geo)}</div>
      ${v.major.length ? `<div class="vg-section">Major values</div>${pnl(v.major, {})}` : ''}
      ${v.minor.length ? `<div class="vg-section">Minor values</div>${pnl(v.minor, { compact: true })}` : ''}
    </div>`;
  };

  // ---------- plot-level graph: the values of one plot, with the conflict levels of each shift
  D.renderValuePlot = function (el, plotId) {
    const S = D.story || {}, model = D.valueModel(S);
    const plot = (S.plots || []).find(p => p.id === plotId);
    if (!plot) { el.innerHTML = empty(); return; }
    const v = orderedValues(model, plot.value_focus, plotId);
    if (!v.lines.length) { el.innerHTML = empty(); return; }
    const geo = D.valueGeometry(model, el.clientWidth);
    const o = { strip: true };
    const pnl = names => names.map(n => panel(model, geo, n, v.lines.filter(l => norm(l.value) === norm(n)), o)).join('');
    el.innerHTML = `<div class="vg-stack">${legendHtml()}
      <div class="vg-axis-wrap">${D.valueAxisSvg(model, geo)}</div>
      ${v.major.length ? `<div class="vg-section">Major values</div>${pnl(v.major)}` : ''}
      ${v.minor.length ? `<div class="vg-section">Minor values</div>${pnl(v.minor)}` : ''}
    </div>`;
  };

  // ---------- the view: tabs, plot picker, level style, click-through to the scene panel
  D.renderValues = function () {
    const el = document.getElementById('vg-content');
    if (!el) return;
    if (state.tab === 'plot') D.renderValuePlot(el, state.plot); else D.renderValueStory(el);
  };

  D.switchValuesTab = function (tab) {
    state.tab = tab;
    document.querySelectorAll('#values-view .vg-tab').forEach(b => b.classList.toggle('active', b.dataset.tab === tab));
    document.querySelectorAll('#values-view .vg-plot-only').forEach(n => { n.style.display = tab === 'plot' ? '' : 'none'; });
    D.renderValues();
  };

  D.buildValuesView = function () {
    const body = document.getElementById('values-body');
    if (!body) return;
    const S = D.story || {};
    const plots = (S.plots || []).slice().sort((a, b) => (a.plot_scope === 'main' ? 0 : 1) - (b.plot_scope === 'main' ? 0 : 1));
    if (!state.plot || !plots.some(p => p.id === state.plot)) state.plot = plots.length ? plots[0].id : null;
    const sub = document.getElementById('values-subtitle');
    if (sub) sub.textContent = `${(S.scenes || []).filter(s => (s.value_turns || []).length).length} scenes with value shifts`;
    body.innerHTML = `<div class="vg-toolbar">
        <div class="vg-seg"><button class="vg-tab" data-tab="story">Story</button><button class="vg-tab" data-tab="plot">Plot</button></div>
        <select class="vg-select vg-plot-only" id="vg-plot-select">${plots.map(p => `<option value="${DASH.escapeHtml(p.id)}">${DASH.escapeHtml(p.name || p.id)}</option>`).join('')}</select>
      </div><div id="vg-content" class="vg-content"></div>`;
    body.querySelectorAll('.vg-tab').forEach(b => b.addEventListener('click', () => D.switchValuesTab(b.dataset.tab)));
    const sel = body.querySelector('#vg-plot-select');
    sel.value = state.plot || '';
    sel.addEventListener('change', () => { state.plot = sel.value; D.renderValues(); });
    body.querySelector('#vg-content').addEventListener('click', e => {
      const t = e.target.closest ? e.target.closest('[data-scene]') : null;
      if (t && D.showScenePanel) D.showScenePanel(t.getAttribute('data-scene'));
    });
    const content = body.querySelector('#vg-content');
    if (typeof ResizeObserver !== 'undefined') {
      new ResizeObserver(() => D.renderValues()).observe(content);
    }
    D.switchValuesTab(state.tab);
  };

  // the container has no width while hidden, so draw when the view is opened
  D.onViewOpened(function (view) {
    if (view === 'values') D.renderValues();
  });
})(window.DASH);
