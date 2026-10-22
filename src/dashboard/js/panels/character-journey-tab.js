// Character "Journey" tab: one character across the story, in story order.
//
//   stats      how much is on record (the picture must not look more complete than it is)
//   ribbon     one SVG on the value graph's own axis (acts, sequences, milestones):
//                markers   in scene / drives / a choice / a change was recorded
//                circles   the conflict levels a scene reaches for them (protagonists only);
//                          a chord joins the levels hit in one scene, so complexity is visible
//                depth     per value, the rung they are carried through (P, C, CD, NN)
//   timeline   the same, in words, by act and sequence
//
// Nothing here scores intensity: the theory gives no scale. Position is the circle (inner,
// personal, extra-personal) or the rung of a value, both of which are the data itself.
// Data: DASH.characterTrack (track-data.js).
window.DASH = window.DASH || {};

(function (D) {
  'use strict';

  const h = s => D.escapeHtml(s == null ? '' : String(s));
  const LEVELS = ['extra-personal', 'personal', 'inner'];            // top to bottom: the world, then closer in
  const LEVEL_SHORT = { inner: 'inner', personal: 'personal', 'extra-personal': 'extra-pers.' };
  const RUNG = ['P', 'C', 'CD', 'NN'];
  const PINK = '#e06b9b';                                               // a true-character moment (--c-choice)
  const LABEL_W = 58, PAD_R = 8, MIN_SLOT = 12;

  const plotColor = p => (D.plotColor ? D.plotColor(p) : '#8a8a8a');
  const cutText = (s, n) => { s = String(s || ''); return s.length > n ? s.slice(0, Math.max(1, n - 1)) + '\u2026' : s; };

  // ---- the ribbon -----------------------------------------------------------------------
  function ribbonSvg(track, view, a0, geo, color) {
    const X = i => geo.labelW + (i + 0.5) * geo.slot;
    const inView = track.rows.filter(r => r.i >= a0 && r.i < a0 + view.n).map(r => Object.assign({}, r, { ri: r.i - a0 }));
    const parts = [];
    let y = 62;                                                           // the shared axis occupies the first 62px
    const label = (txt, yy) => parts.push(`<text class="vg-code" x="${geo.labelW - 8}" y="${yy}" text-anchor="end">${txt}</text>`);
    const bandRect = (yy, hh, k) => parts.push(`<rect class="vg-band ${k % 2 ? 'odd' : 'even'}" x="${geo.labelW}" y="${yy}" width="${geo.W - geo.labelW - PAD_R}" height="${hh}"/>`);

    // markers
    y += 8;
    const M = [['in scene', r => r.inCast || r.hasBeats || r.turns.length || r.change], ['in beats', r => r.acted + r.answered], ['drives', r => r.drives], ['choice', r => r.choices.length], ['change', r => !!r.change]];
    M.forEach(([name, test], k) => {
      const cy = y + k * 15 + 7;
      bandRect(y + k * 15, 15, k);
      label(name, cy + 3);
      inView.forEach(r => {
        if (!test(r)) return;
        const x = X(r.ri);
        if (name === 'in scene') {
          parts.push(r.inCast
            ? `<circle cx="${x}" cy="${cy}" r="2.4" fill="var(--muted-foreground)" opacity=".7"/>`
            : `<circle cx="${x}" cy="${cy}" r="2.6" fill="none" stroke="var(--muted-foreground)" stroke-dasharray="1.5 1.5" opacity=".8"><title>affected without being present</title></circle>`);
        } else if (name === 'in beats') {
          // how much of the scene's exchange is theirs: solid = beats they act in, pale = beats they answer
          const a = Math.min(r.acted, 5) * 2, b = Math.min(r.answered, 5) * 2, base = y + k * 15 + 14;
          if (b) parts.push(`<rect x="${x - 2.5}" y="${base - a - b}" width="5" height="${b}" rx="1" fill="${color}" opacity=".35"/>`);
          if (a) parts.push(`<rect x="${x - 2.5}" y="${base - a}" width="5" height="${a}" rx="1" fill="${color}"/>`);
        } else if (name === 'drives') {
          parts.push(`<circle cx="${x}" cy="${cy}" r="4.3" fill="none" stroke="${color}" stroke-width="2"/>`);
        } else if (name === 'choice') {
          parts.push(`<path d="M${x} ${cy - 5.5} L${x + 5} ${cy} L${x} ${cy + 5.5} L${x - 5} ${cy} Z" fill="${PINK}"/>`);
        } else {
          parts.push(`<rect x="${x - 3.2}" y="${cy - 3.2}" width="6.4" height="6.4" rx="1.2" fill="var(--foreground)" opacity=".78"/>`);
        }
      });
    });
    y += M.length * 15 + 10;

    // circles
    if (track.protagonist && track.coverage.effects) {
      const laneH = 24, top = y;
      LEVELS.forEach((lv, k) => {
        bandRect(top + k * laneH, laneH, k);
        label(LEVEL_SHORT[lv], top + k * laneH + laneH / 2 + 3);
      });
      const laneY = lv => top + LEVELS.indexOf(lv) * laneH + laneH / 2;
      inView.forEach(r => {
        const hit = {};
        r.turns.forEach(t => Object.keys(t.levels).forEach(lv => { (hit[lv] = hit[lv] || []).push(t); }));
        const used = LEVELS.filter(lv => hit[lv]);
        if (!used.length) return;
        const x = X(r.ri);
        if (used.length > 1) {
          parts.push(`<line x1="${x}" y1="${laneY(used[0])}" x2="${x}" y2="${laneY(used[used.length - 1])}" stroke="var(--foreground)" stroke-opacity=".28" stroke-width="3" stroke-linecap="round"/>`);
        }
        used.forEach(lv => {
          const ts = hit[lv], n = ts.length, c = plotColor(ts[0].plot);
          parts.push(`<circle cx="${x}" cy="${laneY(lv)}" r="${n > 1 ? 6 : 4.8}" fill="${c}" stroke="var(--background)" stroke-width="1.5"/>`);
          if (n > 1) parts.push(`<text x="${x}" y="${laneY(lv) + 3}" text-anchor="middle" font-size="8" font-weight="700" fill="var(--background)">${n}</text>`);
        });
      });
      y = top + LEVELS.length * laneH + 12;
    }

    // depth: per value, the rung they are carried through
    if (track.protagonist) {
      track.paths.forEach(p => {
        const steps = p.steps.filter(s => s.i >= a0 && s.i < a0 + view.n);
        if (!steps.length) return;
        const rowH = 10, top = y + 13;
        const col = plotColor(p.plot);
        const deep = p.deepestRung == null ? '' : ` &middot; deepest ${RUNG[p.deepestRung]}`;
        parts.push(`<text class="vg-label" x="${geo.labelW}" y="${y + 8}" font-size="9.5" fill="${col}">${h(p.value)}<tspan class="vg-code" dx="8" fill="var(--muted-foreground)" font-size="8.5">${h(p.first)} &rarr; ${h(p.last)}${deep}</tspan></text>`);
        for (let r = 0; r < 4; r++) {
          const ly = top + r * rowH + rowH / 2;
          label(RUNG[r], ly + 3);
          parts.push(`<line class="vg-lane-line" x1="${geo.labelW}" y1="${ly}" x2="${geo.W - PAD_R}" y2="${ly}"/>`);
        }
        const Y = r => top + r * rowH + rowH / 2;
        let prev = null;
        steps.forEach(s => {
          const x = X(s.i - a0);
          if (s.fromRung == null || s.toRung == null) return;
          if (prev) {
            const same = prev.rung === s.fromRung;
            parts.push(`<line class="${same ? 'vg-carry' : 'vg-jump'}" x1="${prev.x}" y1="${Y(prev.rung)}" x2="${x}" y2="${Y(s.fromRung)}" stroke="${col}"/>`);
          }
          parts.push(`<line x1="${x}" y1="${Y(s.fromRung)}" x2="${x}" y2="${Y(s.toRung)}" stroke="${col}" stroke-width="2" stroke-linecap="round"/>`);
          parts.push(`<circle cx="${x}" cy="${Y(s.fromRung)}" r="2" fill="var(--background)" stroke="${col}" stroke-width="1.4"/>`);
          parts.push(`<circle cx="${x}" cy="${Y(s.toRung)}" r="3.3" fill="${col}"/>`);
          prev = { x, rung: s.toRung };
        });
        y = top + 4 * rowH + 10;
      });
    }

    const H = y + 2;
    // hit columns last, so hover and click land on them
    for (let i = 0; i < view.n; i++) {
      const has = inView.some(r => r.ri === i);
      parts.push(`<rect class="jr-hit${has ? ' has' : ''}" data-i="${i + a0}" x="${geo.labelW + i * geo.slot}" y="0" width="${geo.slot}" height="${H}"/>`);
    }
    const axis = D.valueAxisSvg(view, geo, null, 'plot').replace(/^<svg[^>]*>/, '').replace(/<\/svg>\s*$/, '');
    return `<svg class="vg-svg jr-svg" width="${geo.W}" height="${H}" viewBox="0 0 ${geo.W} ${H}">${axis}${parts.join('')}</svg>`;
  }

  // ---- the parts around it --------------------------------------------------------------
  function statsHtml(track) {
    const c = track.coverage;
    const stat = (n, t) => `<div class="jr-stat"><b>${n}</b><span>${t}</span></div>`;
    const plotName = p => h(((D.story.plots || []).find(x => x.id === p) || {}).name || p);
    const role = track.protagonist
      ? `Protagonist of ${track.plots.length ? track.plots.map(plotName).join(', ') : 'a value turn'}`
      : 'Not a plot protagonist: no conflict levels or value path';
    return `<div class="jr-head">
      <div class="jr-stats">${stat(c.appears, c.appears === 1 ? 'scene' : 'scenes')}${stat(c.drives, 'drives')}${stat(c.choices, c.choices === 1 ? 'choice' : 'choices')}${stat(c.changes, c.changes === 1 ? 'change' : 'changes')}</div>
      <div class="jr-cover">${role}.<br>A change is on record in ${c.changes} of ${c.appears} scenes; beat lists exist for ${c.withBeats}.</div>
    </div>`;
  }

  function focusHtml(model, act) {
    if (model.acts.length < 2) return '';
    const chip = (key, txt) => `<button type="button" class="jr-chip${String(act) === String(key) ? ' on' : ''}" data-act="${key}">${h(txt)}</button>`;
    return `<div class="jr-focus">${chip('all', 'All')}${model.acts.map((a, k) => chip(k, a.name)).join('')}</div>`;
  }

  function legendHtml(track) {
    const g = (cls, txt) => `<span class="jr-key"><i class="${cls}"></i>${txt}</span>`;
    return `<div class="jr-legend">${g('k-in', 'in scene')}${g('k-beats', 'acts / answers in beats')}${g('k-drive', 'drives')}${g('k-choice', 'choice under pressure')}${g('k-change', 'change recorded')}${track.protagonist ? '<span class="jr-key"><i class="k-lane"></i>circles reached, rungs of each value</span>' : ''}</div>`;
  }

  function rowHtml(r, color) {
    const badges = (r.drives ? `<i class="jr-b drive" style="--c:${color}" title="drives the scene"></i>` : '')
      + (r.choices.length ? '<i class="jr-b choice" title="a choice under pressure"></i>' : '')
      + r.milestone.map(m => `<span class="tag tag-struct">${h(D.milestoneLabel ? D.milestoneLabel(m) : String(m).replace(/_/g, ' '))}</span>`).join('');
    const lines = [];
    if (r.drives && r.objective) lines.push(`<div class="jr-line"><span class="jr-k">wants</span>${h(r.objective)}</div>`);
    if (r.change) lines.push(`<div class="jr-line"><span class="jr-k">now</span>${h(r.change)}</div>`);
    if (r.acted || r.answered) {
      const bits = [];
      if (r.acted) bits.push('acts in ' + r.acted + ' beat' + (r.acted === 1 ? '' : 's'));
      if (r.answered) bits.push('answers in ' + r.answered);
      lines.push(`<div class="jr-line jr-beatsline"><span class="jr-k">beats</span>${bits.join(' &middot; ')}</div>`);
    }
    r.choices.forEach(c => lines.push(`<div class="jr-choice"><span class="jr-diamond"></span><div>
      ${c.dilemma ? `<div class="jr-cl"><span class="jr-k">dilemma</span>${h(c.dilemma)}</div>` : ''}
      ${c.choice_reveals ? `<div class="jr-cl"><span class="jr-k">reveals</span>${h(c.choice_reveals)}</div>` : ''}</div></div>`));
    r.turns.forEach(t => {
      const lv = LEVELS.filter(l => t.levels[l] != null);
      lines.push(`<div class="jr-fx"><div class="jr-fxv"><span class="tag" style="${D.valueChipStyle([t.plot])}">${h(t.value)}</span><span class="jr-ft">${h(t.from)} &rarr; ${h(t.to)}</span></div>
        ${lv.map(l => `<div class="jr-fxl"><span class="jr-lv">${LEVEL_SHORT[l]}</span>${h(t.levels[l])}</div>`).join('')}</div>`);
    });
    return `<div class="jr-row" id="jr-s${r.i}" data-i="${r.i}">
      <div class="jr-row-head"><span class="jr-num">${r.number}</span><button type="button" class="jr-scene" data-ent="scene:${h(r.id)}">${h(r.title)}</button>${badges}</div>
      ${lines.join('')}</div>`;
  }

  function timelineHtml(track, model, color, lo, hi) {
    const rows = track.rows.filter(r => r.i >= lo && r.i <= hi);
    if (!rows.length) return '';
    const recorded = r => r.drives || r.change || r.choices.length || r.turns.length || r.acted || r.answered;
    let out = '', lastAct = null, lastSeq = null, silent = [];
    const flush = () => {
      if (silent.length) out += `<div class="jr-silent">Present, nothing recorded: ${silent.map(r => `<button type="button" class="jr-scene" data-ent="scene:${h(r.id)}">${h(r.title)}</button>`).join(', ')}</div>`;
      silent = [];
    };
    rows.forEach(r => {
      const place = D.trackPlace(track.model, r.i);
      if (place.act && place.act !== lastAct) { flush(); out += `<div class="jr-act">${h(place.act.name)}</div>`; lastAct = place.act; lastSeq = null; }
      if (place.seq && place.seq !== lastSeq) { flush(); out += `<div class="jr-seq">${h(place.seq.name)}</div>`; lastSeq = place.seq; }
      if (recorded(r)) out += rowHtml(r, color); else silent.push(r);
    });
    flush();
    return `<div><div class="panel-section-title">In words</div><div class="jr-timeline">${out}</div></div>`;
  }

  // ---- the tab --------------------------------------------------------------------------
  // opts: { width, act }  (act: index into the story's acts, or 'all')
  D.renderCharacterJourney = function (charId, story, opts) {
    opts = opts || {};
    const st = story || D.story || {};
    const track = D.characterTrack(charId, st);
    if (!track) return '<div class="jr"><div class="panel-empty"><div class="panel-empty-lead">Journey unavailable</div></div></div>';
    const ref = D.entityRef(charId, st);
    if (!track.rows.length) {
      return `<div class="jr"><div class="panel-empty"><div class="panel-empty-lead">Nothing to trace yet</div>
        <div class="panel-muted">${h(ref.name)} is not in any scene, and no value turn or beat list names them.</div></div></div>`;
    }
    const model = track.model;
    const act = opts.act != null && opts.act !== 'all' && model.acts[opts.act] ? Number(opts.act) : 'all';
    const band = act === 'all' ? null : model.acts[act];
    const lo = band ? band.start : 0, hi = band ? band.end : model.n - 1;
    const view = band ? D.valueSlice(model, lo, hi) : model;
    const W = Math.floor(opts.width || 640);
    // The ribbon fills the pane: the slot is whatever the pane can give each scene.
    // Floored at MIN_SLOT because below that the per-scene marks (a 10.6px drives
    // ring, a 10px choice diamond) touch their neighbours — the excess then scrolls,
    // which is what `.jr-scroll`'s overflow-x is for. There is no upper cap: a wide
    // pane should be used, and the act-focus chips are the zoom for a short story.
    const slot = Math.max(MIN_SLOT, (W - LABEL_W - PAD_R) / Math.max(view.n, 1));
    const geo = { slot, labelW: LABEL_W, W: Math.ceil(LABEL_W + slot * view.n + PAD_R) };
    return `<div class="jr" data-char="${h(charId)}">
      ${statsHtml(track)}
      ${focusHtml(model, act)}
      <div class="jr-scroll">${ribbonSvg(track, view, lo, geo, ref.color)}</div>
      ${legendHtml(track)}
      ${timelineHtml(track, model, ref.color, lo, hi)}
    </div>`;
  };

  // hover card, in the value graph's tooltip style
  let tipEl = null;
  const tip = () => {
    if (!tipEl) { tipEl = document.createElement('div'); tipEl.className = 'vg-tip jr-tip'; document.body.appendChild(tipEl); }
    return tipEl;
  };
  function tipHtml(track, i) {
    const r = track.rows.find(x => x.i === i);
    const s = track.model.scenes[i];
    const head = `<div class="vg-tip-head"><b>${i + 1}</b> ${h((s && (s.title || s.name)) || '')}</div>`;
    if (!r) return head + '<div class="vg-tip-none">not in this scene</div>';
    const bits = [];
    if (r.drives && r.objective) bits.push(`<div class="vg-tip-row"><b class="vg-tip-val">wants</b> ${h(r.objective)}</div>`);
    if (r.change) bits.push(`<div class="vg-tip-row"><b class="vg-tip-val">now</b> ${h(cutText(r.change, 110))}</div>`);
    r.choices.forEach(c => bits.push(`<div class="vg-tip-row"><b class="vg-tip-val" style="color:${PINK}">choice</b> ${h(cutText(c.choice_reveals || c.dilemma, 110))}</div>`));
    r.turns.forEach(t => bits.push(`<div class="vg-tip-row"><i style="background:${plotColor(t.plot)}"></i><span class="vg-tip-val">${h(t.value)}</span> ${h(t.from)} \u2192 ${h(t.to)}${
      LEVELS.filter(l => t.levels[l] != null).map(l => `<div class="vg-tip-fx">${LEVEL_SHORT[l]}: ${h(cutText(t.levels[l], 90))}</div>`).join('')}</div>`));
    return head + (bits.length ? bits.join('') : '<div class="vg-tip-none">present, nothing recorded</div>');
  }

  // one set of listeners per pane; redraw() rebuilds the markup (resize, act focus)
  function wire(pane, charId) {
    const state = { act: 'all' };
    const redraw = () => { pane.innerHTML = D.renderCharacterJourney(charId, null, { width: pane.clientWidth, act: state.act }); };
    pane.addEventListener('click', ev => {
      const chip = ev.target.closest && ev.target.closest('[data-act]');
      if (chip) { state.act = chip.dataset.act; redraw(); return; }
      const hit = ev.target.closest && ev.target.closest('.jr-hit');
      if (hit) {
        const row = pane.querySelector('#jr-s' + hit.dataset.i);
        if (!row) return;
        row.scrollIntoView({ behavior: 'smooth', block: 'center' });
        row.classList.remove('flash'); void row.offsetWidth; row.classList.add('flash');
      }
    });
    pane.addEventListener('mousemove', ev => {
      const hit = ev.target.closest && ev.target.closest('.jr-hit');
      const el = tip();
      if (!hit) { el.style.display = 'none'; return; }
      el.innerHTML = tipHtml(D.characterTrack(charId), Number(hit.dataset.i));
      el.style.display = 'block';
      const x = Math.min(ev.clientX + 14, window.innerWidth - el.offsetWidth - 8);
      el.style.left = Math.max(8, x) + 'px';
      el.style.top = Math.min(ev.clientY + 14, window.innerHeight - el.offsetHeight - 8) + 'px';
    });
    pane.addEventListener('mouseleave', () => { tip().style.display = 'none'; });
    return redraw;
  }

  if (D.panelTabs) {
    D.panelTabs.register('character', id => {
      const ch = (D.story.characters || []).find(c => String(c.id) === String(id));
      if (!ch) return null;
      const name = ch.name || id;
      return [{
        id: 'journey', label: 'Journey', wide: true, redraw: true,
        render(pane) {
          if (!pane._redraw) pane._redraw = wire(pane, id);
          pane._redraw();
        },
        footer() {
          return `<button class="btn btn-hermes" data-hermes-send="Trace ${h(name)}'s journey through the story: where is the pressure rising, and where is it thin?">Trace this journey</button>`;
        },
      }];
    });
    D.panelTabs.decorate('showCharacterPanel', 'character', args => args[0] && args[0].id);
  }
})(window.DASH);
