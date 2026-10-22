// Scene "Beats" tab: how one scene works.
//
//   header       who drives, what they want, the turning point, the values that turn
//   rhythm       one cell per beat: who acted (top), who answered (bottom), whether a gap opened
//   exchange     lanes by participant; each beat a zig-zag from the lane that acts to the lane
//                that answers, a crack on the arrow where a gap opened, the gap sentence below
//   changes      what is different at the end of the scene, per entity
//   true char.   a choice under pressure: the dilemma and what it reveals
//
// Renders the scene's `scene_beats` record (DASH.story.scene_beats, see track-data.js).
// Lanes need room: given the pane width and the number of participants, the exchange either
// draws lanes or folds into one column (chat style). The tab redraws when the panel is resized.
window.DASH = window.DASH || {};

(function (D) {
  'use strict';

  const h = s => D.escapeHtml(s == null ? '' : String(s));
  const arr = x => (Array.isArray(x) ? x : []);
  const WORLD = { key: '_world', name: 'Circumstance', color: '#8a8a8a', type: 'world' };

  // ---- participants ---------------------------------------------------------------------
  // A beat's `by` is a character, location or world; left out, it is circumstance (an object,
  // time, an institution). Lanes run in order of appearance, the driver first.
  function lanesOf(sb) {
    const order = [];
    const add = by => { const k = by ? String(by) : WORLD.key; if (!order.includes(k)) order.push(k); };
    if (sb.driver) add(sb.driver);
    arr(sb.beats).forEach(b => { add(b && b.action && b.action.by); add(b && b.reaction && b.reaction.by); });
    const named = order.filter(k => k !== WORLD.key).map(k => {
      const r = D.entityRef(k);
      return { key: k, name: r.name, color: r.color, type: r.type };
    });
    return order.includes(WORLD.key) ? named.concat([WORLD]) : named;      // circumstance always last
  }

  const chip = (ref, extra) =>
    `<button type="button" class="sb-chip" data-ent="${h(ref.type)}:${h(ref.id)}" style="--c:${ref.color}"><i></i>${h(ref.name)}</button>${extra || ''}`;

  // ---- pieces ---------------------------------------------------------------------------
  function headHtml(sb, scene) {
    const drv = sb.driver ? D.entityRef(sb.driver) : null;
    const turns = arr(scene && scene.value_turns);
    const vals = turns.map(t =>
      `<span class="tag sb-val" style="${D.valueChipStyle([t.plot])}">${h(t.value)}: ${h(t.from)} &rarr; ${h(t.to)}</span>`).join('');
    const objective = sb.scene_objective
      ? `<div class="sb-objective">${h(sb.scene_objective)}</div>` : '';
    const turn = sb.turning_point
      ? `<div class="sb-turn"><div class="sb-k">turning point</div><div class="sb-turn-text">${h(sb.turning_point)}</div>${vals ? '<div class="sb-vals">' + vals + '</div>' : ''}</div>`
      : (vals ? `<div class="sb-vals">${vals}</div>` : '');
    if (!drv && !objective && !turn) return '';
    return `<div class="sb-head">
      ${drv ? `<div class="sb-drive"><span class="sb-k">drives</span>${chip(drv)}</div>` : ''}
      ${objective}${turn}
    </div>`;
  }

  // one cell per beat. The cell is split: top the lane that acts, bottom the lane that answers.
  // Amber underline = a gap opened; a dimmed cell is mere activity.
  function rhythmHtml(sb, lanes) {
    const beats = arr(sb.beats);
    if (!beats.length) return '';
    const colorOf = by => (lanes.find(l => l.key === (by ? String(by) : WORLD.key)) || WORLD).color;
    const cells = beats.map((b, i) => {
      const a = colorOf(b.action && b.action.by), r = colorOf(b.reaction && b.reaction.by);
      const gap = !!(b.gap && String(b.gap).trim());
      return `<button type="button" class="sb-cell-r${gap ? ' gap' : ''}" data-go="sb-b${i}" style="--a:${a};--r:${r}" title="Beat ${i + 1}${gap ? ': a gap opens' : ': mere activity'}">${i + 1}</button>`;
    }).join('');
    const gaps = beats.filter(b => b.gap && String(b.gap).trim()).length;
    const acts = {};
    beats.forEach(b => { const k = (b.action && b.action.by) ? String(b.action.by) : WORLD.key; acts[k] = (acts[k] || 0) + 1; });
    const who = Object.keys(acts).sort((x, y) => acts[y] - acts[x]).map(k => {
      const lane = lanes.find(l => l.key === k) || WORLD;
      return `<span style="color:${lane.color}">${h(lane.name)}</span> ${acts[k]}&times;`;
    }).join(' &middot; ');
    return `<div class="sb-rhythm">
      <div class="sb-cells">${cells}</div>
      <div class="sb-rsum">${beats.length} beat${beats.length === 1 ? '' : 's'} &middot; ${gaps} open${gaps === 1 ? 's' : ''} a gap${beats.length - gaps ? ' &middot; ' + (beats.length - gaps) + ' mere activity' : ''}<br>acts: ${who}</div>
    </div>`;
  }

  // the arrow from the acting lane to the answering lane, drawn in the columns it spans
  function linkHtml(ai, ri, gap) {
    const lo = Math.min(ai, ri), span = Math.abs(ai - ri) + 1;
    const x = i => ((i - lo + 0.5) / span) * 100;
    const xa = x(ai), xb = x(ri), same = ai === ri;
    const path = same
      ? `M ${xa} 0 C ${xa + 44} 1 ${xa + 44} 21 ${xa} 22`         // inner conflict: the arrow turns back on itself
      : `M ${xa} 0 C ${xa} 13 ${xb} 9 ${xb} 22`;
    const mid = same ? xa + 33 : (xa + xb) / 2;
    return `<div class="sb-link${gap ? ' has-gap' : ''}${same ? ' is-self' : ''}" style="grid-column:${lo + 2} / span ${span}">
      <svg viewBox="0 0 100 22" preserveAspectRatio="none" aria-hidden="true"><path d="${path}" vector-effect="non-scaling-stroke"/></svg>
      <i class="sb-tip" style="left:${xb}%"></i>
      ${gap ? `<span class="sb-crack" style="left:${mid}%"><svg viewBox="0 0 12 14"><polyline points="7,0 3,6.5 8.5,7.5 4.5,14"/></svg></span>` : ''}
    </div>`;
  }

  function bubble(side, side_i, lane, text) {
    const surface = text && text.surface ? `<div class="sb-surface">${h(text.surface)}</div>` : '';
    const sub = text && text.subtext ? `<div class="sb-sub">${h(text.subtext)}</div>` : '';
    return `<div class="sb-cell sb-${side}" style="grid-column:${side_i + 2};--lane:${lane.color}">
      <div class="sb-bubble"><div class="sb-who">${h(lane.name)}</div>${surface}${sub}</div>
    </div>`;
  }

  const LANE_MIN = 150;            // px a lane needs before its bubbles stop being a column of words
  const stackedFor = (lanes, width) => !!width && (width < 480 || width / lanes.length < LANE_MIN);

  function exchangeHtml(sb, lanes, width) {
    const beats = arr(sb.beats);
    if (!beats.length) return '';
    const idx = by => Math.max(0, lanes.findIndex(l => l.key === (by ? String(by) : WORLD.key)));
    const head = lanes.map((l, i) =>
      `<div class="sb-lane" style="grid-column:${i + 2};--lane:${l.color}"><i></i><span>${h(l.name)}</span></div>`).join('');
    const rows = beats.map((b, i) => {
      const a = b.action || {}, r = b.reaction || {};
      const ai = idx(a.by), ri = idx(r.by);
      const gap = !!(b.gap && String(b.gap).trim());
      return `<div class="sb-beat${gap ? ' has-gap' : ' is-activity'}" id="sb-b${i}">
        <span class="sb-num">${i + 1}</span>
        ${bubble('a', ai, lanes[ai], a)}
        ${linkHtml(ai, ri, gap)}
        ${bubble('r', ri, lanes[ri], r)}
        ${gap ? `<div class="sb-gap"><span class="sb-k">gap</span>${h(b.gap)}</div>` : ''}
      </div>`;
    }).join('');
    return `<div class="sb-exchange${stackedFor(lanes, width) ? ' is-stacked' : ''}" style="--n:${lanes.length}">
      <div class="sb-lanes">${head}</div>${rows}
    </div>`;
  }

  // what is different at the end: characters first, then relationships, places, worlds
  function changesHtml(sb) {
    const order = { character: 0, relationship: 1, location: 2, world: 3, unknown: 4 };
    const list = arr(sb.changes).filter(c => c && c.entity)
      .map(c => ({ ref: D.entityRef(c.entity), text: c.change }))
      .sort((x, y) => order[x.ref.type] - order[y.ref.type]);
    if (!list.length) return '';
    return `<div><div class="panel-section-title">What changed</div>
      <div class="sb-changes">${list.map(c =>
        `<div class="sb-change" style="--c:${c.ref.color}">${chip(c.ref)}<div class="sb-change-text">${h(c.text)}</div></div>`).join('')}</div></div>`;
  }

  function choicesHtml(sb) {
    const list = arr(sb.true_character).filter(t => t && t.character);
    if (!list.length) return '';
    return `<div><div class="panel-section-title">True character</div>
      ${list.map(t => `<div class="sb-choice">
        <div class="sb-choice-head"><span class="sb-diamond"></span>${chip(D.entityRef(t.character))}<span class="sb-k">choice under pressure</span></div>
        ${t.dilemma ? `<div class="sb-choice-row"><span class="sb-k">dilemma</span>${h(t.dilemma)}</div>` : ''}
        ${t.choice_reveals ? `<div class="sb-choice-row"><span class="sb-k">reveals</span>${h(t.choice_reveals)}</div>` : ''}
      </div>`).join('')}</div>`;
  }

  // Conflict / Findings / Notes. Placeholder text from stubs is not shown as content.
  function notesHtml(sb) {
    const data = (window.__SECTIONS__ && window.__SECTIONS__.scene_beats && window.__SECTIONS__.scene_beats[sb.id]) || {};
    const parts = Object.entries(data).filter(([, v]) => v && !/^\s*\[placeholder/i.test(v));
    if (!parts.length) return '';
    return `<details class="sb-notes"><summary>Analysis notes</summary>${parts.map(([name, v]) =>
      `<div class="panel-section-title">${h(name)}</div><div class="panel-text">${h(v).replace(/\n/g, '<br>')}</div>`).join('')}</details>`;
  }

  // ---- the empty state: say what is expected, not just that nothing is there ----------------
  function emptyHtml(scene) {
    const role = (scene && scene.dramatic_role) || '';
    const planned = (scene && scene.status) === 'planned';
    let tone = 'panel-empty', lead, text;
    if (role === 'transition' || role === 'non-event') {
      lead = 'No beat list';
      text = 'Not expected for a ' + role + ' scene. It serves no plot, so nothing has to turn.';
    } else if (planned) {
      lead = 'Not started';
      text = 'This scene is still planned. A beat list can be built before the script, or read from it afterwards.';
    } else {
      tone += ' is-missing';
      lead = 'Beat list missing';
      text = 'This scene has a script but no beat list. Developing one shows who drives it, where a gap opens, and what has changed by the end.';
    }
    return `<div class="${tone}"><div class="panel-empty-lead">${lead}</div><div class="panel-muted">${text}</div></div>`;
  }

  // ---- the tab --------------------------------------------------------------------------
  D.renderSceneBeats = function (sceneId, story, width) {
    const st = story || D.story || {};
    const scene = (st.scenes || []).find(s => String(s.id) === String(sceneId));
    const sb = D.sceneBeatsOf(sceneId, st);
    if (!sb) return `<div class="sb">${emptyHtml(scene)}</div>`;
    const lanes = lanesOf(sb);
    const body = headHtml(sb, scene) + rhythmHtml(sb, lanes) + exchangeHtml(sb, lanes, width) + changesHtml(sb) + choicesHtml(sb) + notesHtml(sb);
    return `<div class="sb">${body || emptyHtml(scene)}</div>`;
  };

  function after(pane) {
    pane.addEventListener('click', ev => {
      const go = ev.target.closest && ev.target.closest('[data-go]');
      if (!go) return;
      const el = pane.querySelector('#' + go.dataset.go);
      if (!el) return;
      el.scrollIntoView({ behavior: 'smooth', block: 'center' });
      el.classList.remove('flash'); void el.offsetWidth; el.classList.add('flash');
    });
  }

  if (D.panelTabs) {
    D.panelTabs.register('scene', id => {
      const scene = (D.story.scenes || []).find(s => String(s.id) === String(id));
      if (!scene) return null;
      const has = !!D.sceneBeatsOf(id);
      const name = scene.title || scene.name || id;
      return [{
        id: 'beats', label: 'Beats', wide: true,
        dot: !has && scene.status && scene.status !== 'planned' && !/^(transition|non-event)$/.test(scene.dramatic_role || '') ? 'No beat list yet' : '',
        render(pane) { pane.innerHTML = D.renderSceneBeats(id, null, pane.clientWidth); after(pane); },
        redraw: true,
        footer() {
          const send = has ? 'Analyse the dynamics of the scene "' + name + '": where do the gaps open, and does it turn?'
                           : 'Develop the beat list for the scene "' + name + '".';
          return `<button class="btn btn-hermes" data-hermes-send="${h(send)}">${has ? 'Analyse this scene' : 'Develop the beats'}</button>`;
        },
      }];
    });
    D.panelTabs.decorate('showScenePanel', 'scene', args => args[0]);
  }
})(window.DASH);
