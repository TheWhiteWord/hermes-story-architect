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
  const GEO = { minLabelW: 58, maxLabelW: 118, padR: 10 };

  const MILESTONES = {
    setup:              { label: 'Setup',            color: '#6bbfb0', shape: 'dot' },
    inciting_incident:  { label: 'Inciting Incident', color: '#e0c96b', shape: 'square' },
    complication:        { label: 'Complication',      color: '#e0a86b', shape: 'dot' },
    crisis:             { label: 'Crisis',           color: '#e0707d', shape: 'dot' },
    climax:             { label: 'Climax',           color: '#ffd93d', shape: 'ring' },
    resolution:         { label: 'Resolution',       color: '#b07be0', shape: 'dot' },
  };

  // The label of a milestone, for a reader that lists a scene's milestones
  // without drawing them (the character journey's timeline). The map stays
  // private; the label is the part another view needs, and it is the same
  // label the axis legend already shows, so the two cannot drift.
  D.milestoneLabel = m => (MILESTONES[String(m).replace(/^plot_/, '')] || {}).label
    || String(m).replace(/_/g, ' ');

  const state = { tab: 'story', plot: null, base: null, act: null, seq: null, animate: false };
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
    const sceneTurns = new Map();  // scene index -> every shift in it, for the hover card
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
      if (!sceneTurns.has(i)) sceneTurns.set(i, []);
      sceneTurns.get(i).push({ plot: t.plot, value: line.value, from: t.from, to: t.to, effects });
    }));

    const allLines = [];
    lines.forEach(byValue => byValue.forEach(line => allLines.push(line)));

    return {
      n: scenes.length, scenes, idxOf, acts: actBands, seqs: seqBands,
      seqNums, lines: allLines, schemas, plotName, sceneTurns, offset: 0,
    };
  };

  // ---------- geometry: real pixels, so text keeps its size however many scenes there are.
  // Only the marks adapt: below ~12px per scene they shrink, below ~10px a "same state" pill becomes a tick.
  const lodOf = geo => Math.min(1, Math.max(0.35, geo.slot / 12));
  const h = s => D.escapeHtml(s);

  D.valueLabelWidth = function (model) {
    let chars = 11;                                            // 'extra-pers.' in the level strip
    model.schemas.forEach(sc => LANES.forEach(k => { chars = Math.max(chars, Math.min(17, String(sc[k] || '').length)); }));
    return Math.min(GEO.maxLabelW, Math.max(GEO.minLabelW, Math.ceil(chars * 5.4) + 14));
  };

  D.valueGeometry = function (model, width) {
    const labelW = D.valueLabelWidth(model);
    const W = Math.max(360, Math.floor(width || 900));
    return { slot: Math.max(1.5, (W - labelW - GEO.padR) / Math.max(model.n, 1)), labelW, W };
  };

  // one act of the story as its own model: scenes a..b, bands clipped and re-based, lines without turns dropped
  D.valueSlice = function (model, a, b) {
    const clip = list => list.filter(x => x.end >= a && x.start <= b)
      .map(x => Object.assign({}, x, { start: Math.max(x.start, a) - a, end: Math.min(x.end, b) - a }));
    const lines = model.lines.map(l => Object.assign({}, l, {
      turns: l.turns.filter(t => t.i >= a && t.i <= b).map(t => Object.assign({}, t, { i: t.i - a })),
    })).filter(l => l.turns.length);
    const sceneTurns = new Map();
    model.sceneTurns.forEach((rows, i) => { if (i >= a && i <= b) sceneTurns.set(i - a, rows); });
    return Object.assign({}, model, {
      n: b - a + 1, offset: (model.offset || 0) + a, scenes: model.scenes.slice(a, b + 1),
      acts: clip(model.acts), seqs: clip(model.seqs), lines, sceneTurns,
    });
  };

  // ---------- axis: acts, sequences, milestones
  D.valueAxisSvg = function (model, geo, plotId) {
    const H = 62, X = i => geo.labelW + (i + 0.5) * geo.slot, d = Math.max(0.65, lodOf(geo)), p = [];
    const rowLabel = (txt, y) => p.push(`<text class="vg-code" x="${geo.labelW - 8}" y="${y}" text-anchor="end">${txt}</text>`);
    rowLabel('act', 12); rowLabel('seq', 33); rowLabel('beats', 50);
    model.acts.forEach((a, k) => {
      const x = geo.labelW + a.start * geo.slot, w = (a.end - a.start + 1) * geo.slot;
      p.push(`<rect class="vg-band ${k % 2 ? 'odd' : 'even'}" x="${x}" y="0" width="${w}" height="18"/>`);
      p.push(`<text class="vg-act-label" x="${x + 5}" y="12">${h(cut(a.name, Math.max(3, Math.floor(w / 6))))}</text>`);
    });
    model.seqs.forEach(q => {
      const x = geo.labelW + q.start * geo.slot, w = (q.end - q.start + 1) * geo.slot;
      if (q.start > 0) p.push(`<line class="vg-seq-line" x1="${x}" y1="22" x2="${x}" y2="40"/>`);
      if (w >= 18) p.push(`<text class="vg-seq-label" x="${x + 4}" y="33">${h(model.seqNums.get(q.id) || q.name)}</text>`);
    });
    model.scenes.forEach((s, i) => {
      const milestones = plotId
        ? (s.plots || []).filter(e => e.id === plotId).map(e => e.role)
        : (s.milestone || []);
      milestones.forEach((m, j) => {
        const cfg = MILESTONES[String(m).replace(/^plot_/, '')];
        if (!cfg) return;
        const x = X(i), y = 46 + j * 10;
        if (cfg.shape === 'ring') {
          p.push(`<circle class="vg-ring" cx="${x}" cy="${y}" r="${3.5 * d}" stroke="${cfg.color}"/>`);
        } else if (cfg.shape === 'square') {
          p.push(`<rect x="${x - 3 * d}" y="${y - 3 * d}" width="${6 * d}" height="${6 * d}" fill="none" stroke="${cfg.color}" stroke-width="1.5"/>`);
        } else {
          p.push(`<circle cx="${x}" cy="${y}" r="${2.5 * d}" fill="${cfg.color}"/>`);
        }
      });
    });
    return `<svg class="vg-svg vg-axis" width="${geo.W}" height="${H}" viewBox="0 0 ${geo.W} ${H}">${p.join('')}</svg>`;
  };

  // ---------- one value: four lanes, shifts as spans, optional level strip
  // o: { value, lines, compact, strip (bool), uid }
  D.valueChartSvg = function (model, geo, o) {
    const compact = !!o.compact, d = lodOf(geo);
    const laneH = compact ? 12 : 26, top = 6, laneBlock = laneH * 4;
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
      p.push(`<text class="${labelCls}" x="${geo.labelW - 8}" y="${Y(r) + 3}" text-anchor="end">${h(cut(schema[LANES[r]] || (r === 0 ? o.value : ''), 17))}</text>`);
    }
    model.seqs.forEach(q => { if (q.start > 0) p.push(`<line class="vg-seq-line" x1="${geo.labelW + q.start * geo.slot}" y1="0" x2="${geo.labelW + q.start * geo.slot}" y2="${H}"/>`); });

    if (useStrip) {
      LEVELS.forEach((lv, k) => p.push(
        `<text class="vg-label vg-label-strip" x="${geo.labelW - 8}" y="${stripTop + k * rowH + 7}" text-anchor="end">${LEVEL_SHORT[lv]}</text>` +
        `<line class="vg-lane-line" x1="${geo.labelW}" y1="${stripTop + k * rowH + 5}" x2="${geo.W - GEO.padR + 6}" y2="${stripTop + k * rowH + 5}"/>`));
    }

    const k = (compact ? 0.7 : 1) * Math.max(0.5, d);
    const step = Math.max(2, 5 * d);
    // several shifts in one scene (two plots, or two characters) sit side by side, not on top of each other
    const totals = new Map(); o.lines.forEach(l => l.turns.forEach(t => totals.set(t.i, (totals.get(t.i) || 0) + 1)));
    const seen = new Map();
    o.lines.forEach(line => {
      const col = plotColor(line.plot);
      let prev = null;
      line.turns.forEach(t => {
        const n = seen.get(t.i) || 0; seen.set(t.i, n + 1);
        const x = X(t.i) + (n - (totals.get(t.i) - 1) / 2) * step;
        const yF = t.fromRung == null ? null : Y(t.fromRung);
        const yT = t.toRung == null ? null : Y(t.toRung);
        // carried: from where the line ended to where this scene opens
        if (prev && prev.y != null && yF != null) {
          // flat: the line carried on. Slanted: this scene opens somewhere else (a flashback, a time skip, a break)
          const jump = prev.rung !== t.fromRung;
          if (jump || geo.slot >= 4) p.push(`<line class="${jump ? 'vg-jump' : 'vg-carry'}" x1="${prev.x}" y1="${prev.y}" x2="${x}" y2="${yF}" stroke="${col}"/>`);
        }
        if (yF != null && yT != null && t.fromRung === t.toRung) {
          // same state: a dashed pill (a tick when scenes are narrow), a real state and not "nothing happened"
          if (geo.slot < 10) {
            p.push(`<line class="vg-hold-tick" x1="${x - 2.5}" y1="${yT}" x2="${x + 2.5}" y2="${yT}" stroke="${col}"/>`);
          } else {
            const w = Math.min(12 * k, geo.slot * 0.9);
            p.push(`<rect class="vg-hold" x="${x - w / 2}" y="${yT - 3 * k}" width="${w}" height="${6 * k}" rx="${3 * k}" stroke="${col}"/>`);
          }
        } else if (yF != null && yT != null) {
          p.push(`<line class="vg-span" x1="${x}" y1="${yF}" x2="${x}" y2="${yT}" stroke="${col}" stroke-width="${Math.max(1.6, 5 * k)}"/>`);
          p.push(dot(x, yF, 2.7 * k, col, t.fromRung === 3, true));
          p.push(dot(x, yT, 4.4 * k, col, t.toRung === 3, false));
        } else if (yT != null) {
          p.push(dot(x, yT, 4.4 * k, col, t.toRung === 3, false));
        } else if (yF != null) {
          p.push(dot(x, yF, 2.7 * k, col, t.fromRung === 3, true));
        } else {
          p.push(`<text class="vg-unknown" x="${x}" y="${top + 2 * laneH + 4}" text-anchor="middle">?</text>`);
        }
        if (useStrip) {
          const w = Math.max(2, Math.min(geo.slot * 0.68, 14));
          LEVELS.forEach((lv, m) => {
            if (t.levels.has(lv)) p.push(`<rect class="vg-lvl" x="${x - w / 2}" y="${stripTop + m * rowH + 1}" width="${w}" height="8" rx="${Math.min(2.5, w / 2)}" fill="${col}"/>`);
          });
        }
        prev = { x, y: yT, rung: t.toRung };
      });
    });

    return `<svg class="vg-svg" width="${geo.W}" height="${H}" viewBox="0 0 ${geo.W} ${H}">${p.join('')}</svg>`;
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
    <span class="vg-legend-item"><svg width="16" height="26"><line class="vg-span" x1="8" y1="5" x2="8" y2="20" stroke="var(--accent)" stroke-width="5"/><circle class="vg-from" cx="8" cy="5" r="2.7" stroke="var(--accent)"/><circle cx="8" cy="20" r="4.4" fill="var(--accent)"/></svg>shift in a scene</span>
    <span class="vg-legend-item"><svg width="18" height="26"><rect class="vg-hold" x="3" y="10" width="12" height="6" rx="3" stroke="var(--accent)"/></svg>stayed in the same state</span>
    <span class="vg-legend-item"><svg width="18" height="26"><circle class="vg-ring" cx="9" cy="13" r="4.4" stroke="var(--accent)"/></svg>negation of the negation</span>
  </div>`;

  const milestoneLegendHtml = () => `<div class="vg-legend vg-legend-milestones">
    ${Object.entries(MILESTONES).map(([key, m]) =>
      m.shape === 'ring'
        ? `<span class="vg-legend-item"><svg width="10" height="10"><circle class="vg-ring" cx="5" cy="5" r="3.5" stroke="${m.color}"/></svg>${m.label}</span>`
        : m.shape === 'square'
        ? `<span class="vg-legend-item"><svg width="10" height="10"><rect x="1.5" y="1.5" width="7" height="7" fill="none" stroke="${m.color}" stroke-width="1.5"/></svg>${m.label}</span>`
        : `<span class="vg-legend-item"><svg width="10" height="10"><circle cx="5" cy="5" r="2.5" fill="${m.color}"/></svg>${m.label}</span>`
    ).join('')}
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

  // ---------- what is on screen: the whole story, one act, or one sequence
  function currentModel(S) {
    const full = D.valueModel(S);
    state.total = full.n;
    const actBand = state.act ? full.acts.find(x => x.id === state.act) : null;
    if (state.act && !actBand) { state.act = null; state.seq = null; }
    const seqBand = state.seq ? full.seqs.find(x => x.id === state.seq) : null;
    if (state.seq && !seqBand) state.seq = null;
    const num = seqBand ? full.seqNums.get(seqBand.id) : '';
    state.names = { act: actBand ? actBand.name : '', seq: seqBand ? (num ? num + ' ' : '') + (seqBand.name || '') : '' };
    const band = seqBand || actBand;
    return band ? D.valueSlice(full, band.start, band.end) : full;
  }

  // ---------- zoom: wheel in goes All -> act -> sequence under the pointer, wheel out goes back, never above the chosen level
  const ZOOM = { plainWheelOnAxis: true, plainWheelOnCharts: false, step: 60, lockMs: 320 };
  let viewCtx = null, wheelAcc = 0, wheelLock = 0;

  function zoomIn(idx) {                                      // idx: scene index in the model on screen
    if (!viewCtx) return false;
    const full = D.valueModel(D.story || {});
    const g = idx + (viewCtx.model.offset || 0);              // index in the whole story
    const at = list => list.find(x => g >= x.start && g <= x.end);
    if (!state.act) { const x = at(full.acts); if (!x) return false; state.act = x.id; state.seq = null; return true; }
    if (!state.seq) { const x = at(full.seqs); if (!x) return false; state.seq = x.id; return true; }
    return false;
  }

  function zoomOut() {
    if (state.seq) { state.seq = null; return true; }
    if (state.act && state.act !== state.base) { state.act = null; return true; }   // the chosen act is the ceiling
    return false;
  }

  function onWheel(e) {
    const overAxis = e.target.closest && e.target.closest('.vg-axis-wrap');
    const wants = e.ctrlKey || e.metaKey || (overAxis && ZOOM.plainWheelOnAxis) || ZOOM.plainWheelOnCharts;
    if (!wants || !viewCtx) return;
    e.preventDefault();                                       // not the page scroll, not the browser zoom
    const now = Date.now();
    if (now < wheelLock) return;
    wheelAcc += e.deltaY * (e.deltaMode === 1 ? 16 : 1);
    if (Math.abs(wheelAcc) < ZOOM.step) return;
    const zoomingIn = wheelAcc < 0;                           // wheel forward, like a map
    wheelAcc = 0;
    let changed = false;
    if (zoomingIn) {
      const axis = e.currentTarget.querySelector('svg.vg-axis');
      if (axis) {
        const r = axis.getBoundingClientRect(), g = viewCtx.geo;
        const raw = Math.floor(((e.clientX - r.left) * (g.W / r.width) - g.labelW) / g.slot);
        changed = zoomIn(Math.max(0, Math.min(viewCtx.model.n - 1, raw)));
      }
    } else {
      changed = zoomOut();
    }
    if (changed) { wheelLock = now + ZOOM.lockMs; state.animate = true; D.renderValues(); }
  }

  // where you are: All > Act II > S3, each step clickable down to the chosen level
  function renderCrumbs() {
    const box = document.getElementById('vg-crumbs');
    if (!box) return;
    const n = state.names || {}, parts = [];
    if (!state.base) parts.push({ label: 'All', go: () => { state.act = null; state.seq = null; } });
    if (state.act) parts.push({ label: n.act, go: () => { state.seq = null; } });
    if (state.seq) parts.push({ label: n.seq, go: null });
    if (parts.length < 2) { box.innerHTML = ''; return; }
    box.innerHTML = parts.map((x, k) => {
      const last = k === parts.length - 1;
      return `<span class="vg-crumb${last ? ' current' : ''}" data-k="${k}">${h(x.label)}</span>`;
    }).join('<span class="vg-sep">\u203A</span>');
    box.querySelectorAll('.vg-crumb:not(.current)').forEach(el => {
      el.onclick = () => { parts[+el.dataset.k].go(); state.animate = true; D.renderValues(); };
    });
  }

  // the drawing width: the container's width without its padding
  function innerWidth(el) {
    const cs = getComputedStyle(el);
    return el.clientWidth - (parseFloat(cs.paddingLeft) || 0) - (parseFloat(cs.paddingRight) || 0);
  }

  function setHint(geo) {
    const el = document.getElementById('vg-hint');
    const top = !state.act && !state.seq;
    if (el) el.textContent = !top ? '' : (geo.slot < 7 ? `${state.total} scenes: Ctrl/\u2318 + scroll to zoom in` : 'Ctrl/\u2318 + scroll to zoom');
    if (el) el.title = 'Scroll in to zoom from the whole story to the act, then the sequence under the pointer. Scroll out to go back. On the axis a plain scroll works too.';
  }

  // ---------- hover guide, one card for the whole scene, click-through to the scene panel
  let tipEl = null;
  function tip() {
    if (!tipEl) { tipEl = document.createElement('div'); tipEl.className = 'vg-tip'; document.body.appendChild(tipEl); }
    return tipEl;
  }

  function tipHtml(model, i, onlyPlot) {
    const s = model.scenes[i];
    const rows = (model.sceneTurns.get(i) || []).filter(r => !onlyPlot || r.plot === onlyPlot);
    const roles = (onlyPlot ? (s.plots || []).filter(e => e.id === onlyPlot).map(e => e.role) : (s.milestone || []))
      .map(m => (MILESTONES[String(m).replace(/^plot_/, '')] || {}).label).filter(Boolean);
    const head = `<div class="vg-tip-head"><b>${(model.offset || 0) + i + 1}</b> ${h(s.title || s.name || s.id)}${roles.length ? `<span class="vg-tip-role">${h(roles.join(', '))}</span>` : ''}</div>`;
    if (!rows.length) return head + '<div class="vg-tip-none">no value shifts</div>';
    return head + rows.map(r => `<div class="vg-tip-row"><i style="background:${plotColor(r.plot)}"></i><span class="vg-tip-val">${h(r.value)}</span> ${h(r.from || '?')} \u2192 ${h(r.to || '?')}` +
      r.effects.map(e => `<div class="vg-tip-fx">${h(e.character)} (${h(e.level)}): ${h(e.effect)}</div>`).join('') + '</div>').join('');
  }

  function attachHover(el, model, geo, onlyPlot) {
    const stack = el.querySelector('.vg-stack');
    if (!stack) return;
    const axis = stack.querySelector('.vg-axis-wrap');
    const guide = document.createElement('div');
    guide.className = 'vg-guide';
    guide.style.top = (axis ? axis.offsetTop : 0) + 'px';
    stack.appendChild(guide);
    const card = tip();
    let last = -2;
    const hide = () => { guide.style.display = 'none'; card.style.display = 'none'; last = -2; };
    const sceneAt = e => {
      const svg = e.target.closest ? e.target.closest('svg.vg-svg') : null;
      if (!svg) return null;
      const r = svg.getBoundingClientRect();
      const i = Math.floor(((e.clientX - r.left) * (geo.W / r.width) - geo.labelW) / geo.slot);
      return i >= 0 && i < model.n ? { i, r } : null;
    };
    stack.addEventListener('mousemove', e => {
      const hit = sceneAt(e);
      if (!hit) { hide(); return; }
      if (hit.i !== last) {
        last = hit.i;
        const sr = stack.getBoundingClientRect();
        guide.style.left = (hit.r.left - sr.left + (geo.labelW + (hit.i + 0.5) * geo.slot) * (hit.r.width / geo.W)) + 'px';
        guide.style.display = 'block';
        card.innerHTML = tipHtml(model, hit.i, onlyPlot);
      }
      card.style.display = 'block';
      const w = card.offsetWidth, ht = card.offsetHeight;
      let x = e.clientX + 16, y = e.clientY + 16;
      if (x + w > window.innerWidth - 8) x = e.clientX - w - 16;
      if (y + ht > window.innerHeight - 8) y = Math.max(8, window.innerHeight - ht - 8);
      card.style.left = x + 'px'; card.style.top = y + 'px';
    });
    stack.addEventListener('mouseleave', hide);
    stack.addEventListener('click', e => {
      const hit = sceneAt(e);
      if (hit && D.showScenePanel) D.showScenePanel(model.scenes[hit.i].id);
    });
  }

  const legendsHtml = () => `<div class="vg-legends">${legendHtml()}${milestoneLegendHtml()}</div>`;

  // ---------- story-level graph: every major value, then every minor one, all plots
  D.renderValueStory = function (el) {
    const S = D.story || {}, model = currentModel(S);
    if (!model.lines.length) { el.innerHTML = empty(); return; }
    const geo = D.valueGeometry(model, innerWidth(el));
    setHint(geo); viewCtx = { model, geo };
    const v = orderedValues(model, (S.project || {}).value_focus, null);
    const pnl = (names, o) => names.map(n => panel(model, geo, n, v.lines.filter(l => norm(l.value) === norm(n)), o)).join('');
    el.innerHTML = `<div class="vg-stack${state.animate ? ' vg-enter' : ''}">${legendsHtml()}
      <div class="vg-axis-wrap">${D.valueAxisSvg(model, geo)}</div>
      ${v.major.length ? `<div class="vg-section">Major values</div>${pnl(v.major, {})}` : ''}
      ${v.minor.length ? `<div class="vg-section">Minor values</div>${pnl(v.minor, { compact: true })}` : ''}
    </div>`;
    attachHover(el, model, geo, null);
  };

  // ---------- plot-level graph: the values of one plot, with the conflict levels of each shift
  D.renderValuePlot = function (el, plotId) {
    const S = D.story || {}, model = currentModel(S);
    const plot = (S.plots || []).find(p => p.id === plotId);
    if (!plot) { el.innerHTML = empty(); return; }
    const v = orderedValues(model, plot.value_focus, plotId);
    if (!v.lines.length) { el.innerHTML = empty(); return; }
    const geo = D.valueGeometry(model, innerWidth(el));
    setHint(geo); viewCtx = { model, geo };
    const o = { strip: true };
    const pnl = names => names.map(n => panel(model, geo, n, v.lines.filter(l => norm(l.value) === norm(n)), o)).join('');
    el.innerHTML = `<div class="vg-stack${state.animate ? ' vg-enter' : ''}">${legendsHtml()}
      <div class="vg-axis-wrap">${D.valueAxisSvg(model, geo, plotId)}</div>
      ${v.major.length ? `<div class="vg-section">Major values</div>${pnl(v.major)}` : ''}
      ${v.minor.length ? `<div class="vg-section">Minor values</div>${pnl(v.minor)}` : ''}
    </div>`;
    attachHover(el, model, geo, plotId);
  };

  // ---------- the view: tabs, plot picker, act focus
  let lastW = 0;
  function renderActs() {
    const box = document.getElementById('vg-acts');
    if (!box) return;
    const acts = ((D.story || {}).acts || []).slice().sort((a, b) => (a.order || 0) - (b.order || 0));
    if (acts.length < 2) { box.style.display = 'none'; return; }
    box.style.display = '';
    box.innerHTML = `<button data-act="">All</button>` + acts.map(a => `<button data-act="${h(a.id)}" title="${h(a.name || a.id)}">${h(cut(a.name || a.id, 14))}</button>`).join('');
    box.querySelectorAll('button').forEach(b => {
      b.classList.toggle('active', (b.dataset.act || null) === state.base);
      b.onclick = () => { state.base = b.dataset.act || null; state.act = state.base; state.seq = null; state.animate = true; D.renderValues(); };
    });
  }

  D.renderValues = function () {
    const el = document.getElementById('vg-content');
    if (!el || !el.clientWidth) return;                       // hidden: nothing to measure
    document.querySelectorAll('#values-view .vg-tab').forEach(b => b.classList.toggle('active', b.dataset.tab === state.tab));
    document.querySelectorAll('#values-view .vg-plot-only').forEach(n => { n.style.display = state.tab === 'plot' ? '' : 'none'; });
    const sel = document.querySelector('#vg-plot-select');
    if (sel) sel.value = state.plot || '';
    renderActs();
    if (state.tab === 'plot') D.renderValuePlot(el, state.plot); else D.renderValueStory(el);
    renderCrumbs();
    state.animate = false;
    lastW = Math.round(el.clientWidth);
  };

  D.switchValuesTab = function (tab) {
    state.tab = tab;
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
        <select class="vg-select vg-plot-only" id="vg-plot-select">${plots.map(p => `<option value="${h(p.id)}">${h(p.name || p.id)}</option>`).join('')}</select>
        <div class="vg-seg vg-acts" id="vg-acts"></div>
        <span class="vg-crumbs" id="vg-crumbs"></span>
        <span class="vg-hint" id="vg-hint"></span>
      </div><div id="vg-content" class="vg-content"></div>`;
    body.querySelectorAll('.vg-tab').forEach(b => b.addEventListener('click', () => D.switchValuesTab(b.dataset.tab)));
    const sel = body.querySelector('#vg-plot-select');
    sel.value = state.plot || '';
    sel.addEventListener('change', () => { state.plot = sel.value; D.renderValues(); });
    const content = body.querySelector('#vg-content');
    content.addEventListener('wheel', onWheel, { passive: false });
    if (typeof ResizeObserver !== 'undefined') {
      // redraw only when the width really changed, and once per frame: a redraw can add or remove a scrollbar
      let raf = 0;
      new ResizeObserver(() => {
        const w = Math.round(content.clientWidth);
        if (!w || Math.abs(w - lastW) < 2) return;
        cancelAnimationFrame(raf);
        raf = requestAnimationFrame(() => D.renderValues());
      }).observe(content);
    }
    D.switchValuesTab(state.tab);
  };

  // the container has no width while hidden, so draw when the view is opened
  D.onViewOpened(function (view) {
    if (view === 'values') D.renderValues();
  });
})(window.DASH);
