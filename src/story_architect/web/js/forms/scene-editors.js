// Scene editors — value turns and the beat sheet.
//
// Two purpose-built widgets for the scene form, registered as kinds in DASH.efKinds. Each is one tab
// of the scene overlay and is saved with the scene (the beat sheet is a separate record behind the
// scenes; the writer never has to know).
//
// Value turns are built around the thing they are about: a value has four words (a "ladder"), a
// turn is a move from one word to another, so you PICK the two words on the ladder instead of
// typing them; and the protagonists to affect come from the chosen plot, so you tick which levels
// the shift reaches instead of free-typing a name. What can't be wrong isn't offered.
//
// The server's validation is the authority (see core/manual_entities.py); this file only makes the
// right thing the easy thing, and shows the server's messages where they belong.
window.DASH = window.DASH || {};
(function (D) {
  'use strict';

  const K = D.efKinds = D.efKinds || {};
  const h = (s) => String(s == null ? '' : s).replace(/[&<>"']/g,
    (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const eqCI = (a, b) => String(a || '').trim().toLowerCase() === String(b || '').trim().toLowerCase();
  const list = (k) => (D.story || {})[k] || [];
  const nameOf = (e) => e.name || e.title || e.id;
  const byId = (k, id) => list(k).find((e) => e.id === id);
  const nameIn = (k, id) => { const e = byId(k, id); return e ? nameOf(e) : id; };
  const anyName = (id) => { for (const k of ['characters', 'relationships', 'locations', 'worlds']) { const e = byId(k, id); if (e) return nameOf(e); } return id; };
  const setIn = (root, parts, val) => { let o = root; for (let i = 0; i < parts.length - 1; i++) o = o[parts[i]]; o[parts[parts.length - 1]] = val; };
  const idFor = (prefix, path) => `${prefix}-${path.replace(/\./g, '-')}`;
  const sorted = (xs) => xs.slice().sort((a, b) => String(nameOf(a)).localeCompare(String(nameOf(b))));

  const RUNGS = [
    { key: 'p', code: 'P', help: 'Positive — the ideal' },
    { key: 'c', code: 'C', help: 'Contrary — the opposite, not the absolute negation' },
    { key: 'cd', code: 'CD', help: 'Contradictory — the direct negation' },
    { key: 'nn', code: 'NN', help: 'Negation of the negation — a false version of the positive' },
  ];
  const act = (k, op, extra) => `data-act="ext" data-k="${k}" data-op="${op}"${extra || ''}`;
  const msg = (path) => `<div class="ef-msg" data-msg="${h(path)}"></div>`;

  // ═══ Value turns ═══════════════════════════════════════════════════════════
  const valueOf = (name) => list('values').find((v) => eqCI(v.name, name));
  const wordsOf = (v) => (v ? RUNGS.map((r) => ({ ...r, word: v[r.key] })).filter((w) => w.word) : []);

  function normTurns(v) {
    const s = (x) => String(x == null ? '' : x).trim();
    const out = [];
    (v || []).forEach((t) => {
      const effects = (t.effects || []).map((e) => ({
        character: s(e.character),
        levels: (e.levels || []).map((l) => ({ conflict_level: s(l.conflict_level), effect: s(l.effect) })).filter((l) => l.conflict_level || l.effect),
      })).filter((e) => e.character || e.levels.length);
      const turn = { plot: s(t.plot), value: s(t.value), from: s(t.from), to: s(t.to), effects };
      if (turn.plot || turn.value || turn.from || turn.to || effects.length) out.push(turn);
    });
    return out;
  }

  const select = (attrs, id, options, current, blank, stray) =>
    `<select class="ef-input" ${attrs} id="${id}"><option value="">${blank}</option>
      ${current && !options.some((o) => o[0] === current) ? `<option value="${h(current)}" selected>${h(stray || current)} (missing)</option>` : ''}
      ${options.map(([v, l]) => `<option value="${h(v)}"${v === current ? ' selected' : ''}>${h(l)}</option>`).join('')}</select>`;

  function ladder(t, i, pos, label) {
    const v = valueOf(t.value), words = wordsOf(v), path = `value_turns.${i}.${pos}`;
    const chips = words.map((w) => {
      const on = eqCI(t[pos], w.word);
      return `<button type="button" class="ve-chip${on ? ' on' : ''}" ${act('valueturns', 'pick', ` data-i="${i}" data-pos="${pos}" data-word="${h(w.word)}"`)} aria-pressed="${on}" title="${h(w.help)}"><i>${w.code}</i><span>${h(w.word)}</span></button>`;
    }).join('');
    const stray = t[pos] && v && !words.some((w) => eqCI(w.word, t[pos]))
      ? `<button type="button" class="ve-chip on stray" ${act('valueturns', 'pick', ` data-i="${i}" data-pos="${pos}" data-word="${h(t[pos])}"`)} title="Not a word of this value">${h(t[pos])}</button>` : '';
    return `<div class="ef-field"><div class="ef-label">${label}</div>
      ${v ? `<div class="ve-ladder" role="group" aria-label="${h(label)}">${chips}${stray}</div>` : '<div class="ve-ladder none">Choose a value to see its four words.</div>'}
      ${msg(path)}</div>`;
  }

  function effects(f, t, i) {
    if (!t.plot) return '<div class="ef-note">Choose a plot to see its protagonists.</div>';
    const plot = byId('plots', t.plot), prot = (plot && plot.characters) || [];
    let html = prot.length ? '' : '<div class="ef-note ve-warn">This plot has no protagonists yet. Add them in the plot’s form (Plots → Edit), then come back.</div>';
    html += prot.map((cid) => {
      const ei = t.effects.findIndex((e) => e.character === cid), e = ei >= 0 ? t.effects[ei] : null, who = nameIn('characters', cid);
      const toggles = f.levels.map((l) => {
        const on = !!e && e.levels.some((x) => x.conflict_level === l.key);
        return `<button type="button" class="ve-lv${on ? ' on' : ''}" ${act('valueturns', 'level', ` data-i="${i}" data-c="${h(cid)}" data-l="${l.key}"`)} aria-pressed="${on}" title="${h(l.help)}">${h(l.label)}</button>`;
      }).join('');
      const inputs = e ? e.levels.map((lv, li) => {
        const lab = (f.levels.find((l) => l.key === lv.conflict_level) || {}).label || lv.conflict_level, vp = `${i}.effects.${ei}.levels.${li}.effect`;
        return `<div class="ef-field"><label class="ef-label ve-small" for="${idFor('ve', vp)}">${h(lab)}</label>
          <input class="ef-input" data-k="valueturns" data-vp="${vp}" data-path="value_turns.${vp}" id="${idFor('ve', vp)}" value="${h(lv.effect)}" autocomplete="off"
            placeholder="One sentence: what this does to ${h(who)} at the ${h(lab.toLowerCase())} level">${msg('value_turns.' + vp)}</div>`;
      }).join('') : '';
      return `<div class="ve-eff"><div class="ve-who">${h(who)}</div><div class="ve-levels">${toggles}</div>${inputs}
        ${e ? msg(`value_turns.${i}.effects.${ei}.character`) + msg(`value_turns.${i}.effects.${ei}.levels`) : ''}</div>`;
    }).join('');
    // Effects already written for someone who is not (or is no longer) a protagonist of this plot:
    // shown, never silently dropped, and removable.
    t.effects.forEach((e, ei) => {
      if (prot.includes(e.character)) return;
      html += `<div class="ve-eff stale"><div class="ve-who">${h(nameIn('characters', e.character) || 'Someone')} <span class="ve-note">— not a protagonist of this plot</span>
        <button type="button" class="ef-rm" ${act('valueturns', 'eff-del', ` data-i="${i}" data-e="${ei}"`)} aria-label="Remove" title="Remove">×</button></div>
        ${e.levels.map((l) => `<div class="ve-sub">${h(l.conflict_level)}: ${h(l.effect)}</div>`).join('')}${msg(`value_turns.${i}.effects.${ei}.character`)}</div>`;
    });
    return html;
  }

  function turnHtml(f, t, i) {
    const plots = sorted(list('plots')).map((p) => [p.id, nameOf(p)]), values = sorted(list('values')).map((v) => [v.name, v.name]);
    const sum = t.value && (t.from || t.to) ? `${h(t.value)}: ${h(t.from || '?')} → ${h(t.to || '?')}` : '';
    const at = (leaf) => `data-k="valueturns" data-vp="${i}.${leaf}" data-path="value_turns.${i}.${leaf}"`;
    return `<div class="ef-sub-card ve-turn">
      <div class="ef-sub-card-h">Value turn ${i + 1}<span class="ve-sum">${sum}</span>
        <button type="button" class="ef-rm ef-rm-card" ${act('valueturns', 'turn-del', ` data-i="${i}"`)} aria-label="Remove" title="Remove">×</button></div>
      <div class="ef-grid">
        <div class="ef-field"><label class="ef-label" for="${idFor('ve', i + '.plot')}">Plot</label>${select(at('plot'), idFor('ve', i + '.plot'), plots, t.plot, '— choose —')}${msg(`value_turns.${i}.plot`)}</div>
        <div class="ef-field"><label class="ef-label" for="${idFor('ve', i + '.value')}">Value</label>${select(at('value'), idFor('ve', i + '.value'), values, valueOf(t.value) ? valueOf(t.value).name : t.value, '— choose —')}${msg(`value_turns.${i}.value`)}</div>
      </div>
      ${ladder(t, i, 'from', 'When the scene opens')}${ladder(t, i, 'to', 'When it closes')}
      <div class="ef-field"><div class="ef-label">How it lands on the protagonists</div>${effects(f, t, i)}${msg(`value_turns.${i}.effects`)}</div></div>`;
  }

  K.valueturns = {
    count: (f, v) => normTurns(v).length,
    norm: (f, v) => normTurns(v),
    html(f, c) {
      const turns = c.S.values[f.key] || [];
      return `<div class="ve-intro">A value turn records how a value shifts in this scene — and how that lands on each protagonist of the plot.</div>
        ${turns.map((t, i) => turnHtml(f, t, i)).join('')}
        <button type="button" class="ef-add" ${act('valueturns', 'turn-add')}>+ Add value turn</button>
        ${!list('values').length ? '<div class="ef-note ve-warn">There are no values yet — create one from the Values view first.</div>' : ''}
        ${!list('plots').length ? '<div class="ef-note ve-warn">There are no plots yet — create one from the Plots view first.</div>' : ''}`;
    },
    onInput(el, f, c) {
      const turns = c.S.values[f.key], parts = el.dataset.vp.split('.');
      setIn(turns, parts, el.value); c.touch(el.dataset.path);
      const leaf = parts[parts.length - 1];
      if (parts.length === 2 && (leaf === 'plot' || leaf === 'value')) {
        const t = turns[+parts[0]];
        if (leaf === 'value') {                                   // a different value has different words
          const words = wordsOf(valueOf(t.value));
          ['from', 'to'].forEach((p) => { if (!words.some((w) => eqCI(w.word, t[p]))) t[p] = ''; });
        }
        c.rerender(el.id);
      }
    },
    onAct(op, el, f, c) {
      const turns = c.S.values[f.key] = c.S.values[f.key] || [], i = +el.dataset.i;
      if (op === 'turn-add') {
        const roles = (c.S.values.plot_roles || []).map((r) => r.plot).filter(Boolean);   // this scene's own plot, if it has one
        const plots = list('plots'), plot = roles[0] || (plots.length === 1 ? plots[0].id : '');
        turns.push({ plot, value: '', from: '', to: '', effects: [] });
        c.rerender(idFor('ve', `${turns.length - 1}.${plot ? 'value' : 'plot'}`));
      } else if (op === 'turn-del') { turns.splice(i, 1); c.rerender(); }
      else if (op === 'pick') {
        const t = turns[i], word = el.dataset.word, pos = el.dataset.pos;
        t[pos] = eqCI(t[pos], word) ? '' : word; c.touch(`value_turns.${i}.${pos}`); c.rerender();
      } else if (op === 'eff-del') { turns[i].effects.splice(+el.dataset.e, 1); c.rerender(); }
      else if (op === 'level') {
        const t = turns[i], cid = el.dataset.c, lk = el.dataset.l, order = f.levels.map((l) => l.key);
        let e = t.effects.find((x) => x.character === cid);
        if (!e) { e = { character: cid, levels: [] }; t.effects.push(e); }
        const at = e.levels.findIndex((l) => l.conflict_level === lk);
        if (at >= 0) e.levels.splice(at, 1);
        else { e.levels.push({ conflict_level: lk, effect: '' }); e.levels.sort((a, b) => order.indexOf(a.conflict_level) - order.indexOf(b.conflict_level)); }
        if (!e.levels.length) t.effects.splice(t.effects.indexOf(e), 1);
        const ei = t.effects.indexOf(e), li = e.levels.findIndex((l) => l.conflict_level === lk);
        c.rerender(at < 0 && ei >= 0 ? idFor('ve', `${i}.effects.${ei}.levels.${li}.effect`) : null);
      }
    },
    diff(f, a, b, c) {
      const line = (t) => {
        const eff = t.effects.map((e) => `${h(nameIn('characters', e.character))} — ${e.levels.map((l) => `${h(l.conflict_level)}: ${h(l.effect)}`).join('; ')}`);
        return `<b>${h(nameIn('plots', t.plot) || '?')}</b> · ${h(t.value || '?')}: ${h(t.from || '?')} → ${h(t.to || '?')}${eff.map((x) => `<div class="ve-sub">${x}</div>`).join('')}`;
      };
      const items = (v) => normTurns(v).map((t) => ({ key: JSON.stringify(t), html: line(t) }));
      return c.listDiff(items(a), items(b));
    },
  };

  // ═══ Beat sheet ════════════════════════════════════════════════════════════
  const BLANK_SIDE = () => ({ by: '', surface: '', subtext: '' });
  const blankBeat = (by) => ({ action: { ...BLANK_SIDE(), by: by || '' }, reaction: BLANK_SIDE(), gap: '' });

  function normSheet(v) {
    const s = (x) => String(x == null ? '' : x).trim(), v_ = v || {};
    const side = (o) => ({ by: s((o || {}).by), surface: s((o || {}).surface), subtext: s((o || {}).subtext) });
    return {
      driver: s(v_.driver), turning_point: s(v_.turning_point),
      true_character: (v_.true_character || []).map((t) => ({ character: s(t.character), dilemma: s(t.dilemma), choice_reveals: s(t.choice_reveals) })).filter((t) => Object.values(t).some(Boolean)),
      changes: (v_.changes || []).map((c) => ({ entity: s(c.entity), change: s(c.change) })).filter((c) => c.entity || c.change),
      beats: (v_.beats || []).map((b) => ({ action: side(b.action), reaction: side(b.reaction), gap: s(b.gap) }))
        .filter((b) => Object.values(b.action).some(Boolean) || Object.values(b.reaction).some(Boolean) || b.gap),
    };
  }

  const groups = (types, current) => {
    let known = false;
    const html = types.map(([k, title]) => {
      const opts = sorted(list(k)).map((e) => { if (e.id === current) known = true; return `<option value="${h(e.id)}"${e.id === current ? ' selected' : ''}>${h(nameOf(e))}</option>`; }).join('');
      return opts ? `<optgroup label="${title}">${opts}</optgroup>` : '';
    }).join('');
    return (current && !known ? `<option value="${h(current)}" selected>${h(current)} (missing)</option>` : '') + html;
  };
  const BY = [['characters', 'Characters'], ['locations', 'Locations'], ['worlds', 'Worlds']];
  const CHANGED = [['characters', 'Characters'], ['relationships', 'Relationships'], ['locations', 'Locations'], ['worlds', 'Worlds']];

  const bp = (path) => `data-k="beatsheet" data-bp="${path}" data-path="beat_sheet.${path}" id="${idFor('bs', path)}"`;
  const field = (label, path, control, help, wide) => `<div class="ef-field${wide ? ' ef-wide' : ''}"><label class="ef-label" for="${idFor('bs', path)}">${label}</label>${control}${help ? `<div class="ef-help">${help}</div>` : ''}${msg('beat_sheet.' + path)}</div>`;
  const text = (path, v, ph) => `<input class="ef-input" ${bp(path)} value="${h(v)}" autocomplete="off"${ph ? ` placeholder="${h(ph)}"` : ''}>`;
  const area = (path, v, ph) => `<textarea class="ef-input" ${bp(path)} rows="2"${ph ? ` placeholder="${h(ph)}"` : ''}>${h(v)}</textarea>`;
  const pick = (path, v, types, blank) => `<select class="ef-input" ${bp(path)}><option value="">${blank}</option>${groups(types, v)}</select>`;
  const head = (title, help) => `<div class="ve-section"><div class="ve-section-h">${title}</div>${help ? `<div class="ef-help">${help}</div>` : ''}</div>`;
  const ctl = (op, i, label, glyph, off) => `<button type="button" class="ro-btn" ${act('beatsheet', op, ` data-i="${i}"`)} aria-label="${label}" title="${label}"${off ? ' disabled' : ''}>${glyph}</button>`;

  function beatCard(b, i, n) {
    const side = (kind, title) => `<div class="ve-side"><div class="ve-side-h">${title}</div>
      ${field('By', `beats.${i}.${kind}.by`, pick(`beats.${i}.${kind}.by`, b[kind].by, BY, '— nobody —'))}
      ${field('Surface', `beats.${i}.${kind}.surface`, area(`beats.${i}.${kind}.surface`, b[kind].surface), 'What is shown or said.')}
      ${field('Subtext', `beats.${i}.${kind}.subtext`, text(`beats.${i}.${kind}.subtext`, b[kind].subtext), 'The underlying action, as a gerund phrase — “testing the rules”.')}</div>`;
    return `<div class="ef-sub-card"><div class="ef-sub-card-h">Beat ${i + 1}<span class="ve-ctl">${ctl('beat-up', i, 'Move up', '↑', i === 0)}${ctl('beat-down', i, 'Move down', '↓', i === n - 1)}
        <button type="button" class="ef-rm" ${act('beatsheet', 'beat-del', ` data-i="${i}"`)} aria-label="Remove" title="Remove">×</button></span></div>
      <div class="ef-grid">${side('action', 'Action')}${side('reaction', 'Reaction')}
        ${field('Gap', `beats.${i}.gap`, area(`beats.${i}.gap`, b.gap), 'The break between what was expected and what came back. Leave empty if this beat is only activity.', true)}</div>
      ${msg(`beat_sheet.beats.${i}`)}</div>`;
  }

  K.beatsheet = {
    count: (f, v) => normSheet(v).beats.length,
    norm: (f, v) => normSheet(v),
    html(f, c) {
      const s = c.S.values[f.key] = Object.assign({ driver: '', turning_point: '', true_character: [], changes: [], beats: [] }, c.S.values[f.key]);
      const tc = s.true_character.map((t, i) => `<div class="ef-sub-card"><div class="ef-sub-card-h">Moment ${i + 1}
          <button type="button" class="ef-rm ef-rm-card" ${act('beatsheet', 'tc-del', ` data-i="${i}"`)} aria-label="Remove" title="Remove">×</button></div>
        <div class="ef-grid">${field('Character', `true_character.${i}.character`, pick(`true_character.${i}.character`, t.character, [['characters', 'Characters']], '— choose —'))}
          ${field('What the choice reveals', `true_character.${i}.choice_reveals`, text(`true_character.${i}.choice_reveals`, t.choice_reveals))}
          ${field('The dilemma', `true_character.${i}.dilemma`, area(`true_character.${i}.dilemma`, t.dilemma), 'The alternatives, and what choosing costs.', true)}</div></div>`).join('');
      const ch = s.changes.map((x, i) => `<div class="ef-sub-card"><div class="ef-sub-card-h">Change ${i + 1}
          <button type="button" class="ef-rm ef-rm-card" ${act('beatsheet', 'ch-del', ` data-i="${i}"`)} aria-label="Remove" title="Remove">×</button></div>
        <div class="ef-grid">${field('Who or what', `changes.${i}.entity`, pick(`changes.${i}.entity`, x.entity, CHANGED, '— choose —'))}
          ${field('What is different now', `changes.${i}.change`, area(`changes.${i}.change`, x.change), 'The new state, not the event.')}</div></div>`).join('');
      return `<div class="ve-intro">The scene’s beat sheet: who drives it, where it turns, and the beats of action and reaction. The scene’s objective is on the Fields tab.</div>
        <div class="ef-grid">${field('Driver', 'driver', pick('driver', s.driver, [['characters', 'Characters']], '— none —'), 'The character who drives the scene.')}
          ${field('Turning point', 'turning_point', area('turning_point', s.turning_point), 'The moment the biggest gap opens and the value turns. It starts the closing state — it doesn’t resolve it.')}</div>
        ${head('True-character moments', 'Choices that reveal who a character really is. None, one or several.')}${tc}
        <button type="button" class="ef-add" ${act('beatsheet', 'tc-add')}>+ Add moment</button>
        ${head('What changed by the end', 'Only where something changed. No entry means unchanged.')}${ch}
        <button type="button" class="ef-add" ${act('beatsheet', 'ch-add')}>+ Add change</button>
        ${head('Beats', 'In order. A beat with no gap is activity, not action.')}${s.beats.map((b, i) => beatCard(b, i, s.beats.length)).join('')}
        <button type="button" class="ef-add" ${act('beatsheet', 'beat-add')}>+ Add beat</button>`;
    },
    onInput(el, f, c) {
      setIn(c.S.values[f.key], el.dataset.bp.split('.'), el.value); c.touch(el.dataset.path);
    },
    onAct(op, el, f, c) {
      const s = c.S.values[f.key], i = +el.dataset.i;
      if (op === 'tc-add') { s.true_character.push({ character: '', dilemma: '', choice_reveals: '' }); c.rerender(idFor('bs', `true_character.${s.true_character.length - 1}.character`)); }
      else if (op === 'tc-del') { s.true_character.splice(i, 1); c.rerender(); }
      else if (op === 'ch-add') { s.changes.push({ entity: '', change: '' }); c.rerender(idFor('bs', `changes.${s.changes.length - 1}.entity`)); }
      else if (op === 'ch-del') { s.changes.splice(i, 1); c.rerender(); }
      else if (op === 'beat-add') { s.beats.push(blankBeat(s.driver)); c.rerender(idFor('bs', `beats.${s.beats.length - 1}.action.${s.driver ? 'surface' : 'by'}`)); }
      else if (op === 'beat-del') { s.beats.splice(i, 1); c.rerender(); }
      else if (op === 'beat-up' && i > 0) { [s.beats[i - 1], s.beats[i]] = [s.beats[i], s.beats[i - 1]]; c.rerender(); }
      else if (op === 'beat-down' && i < s.beats.length - 1) { [s.beats[i + 1], s.beats[i]] = [s.beats[i], s.beats[i + 1]]; c.rerender(); }
    },
    diff(f, a, b, c) {
      const items = (v) => {
        const s = normSheet(v), out = [];
        const clip = (x) => (x.length > 90 ? x.slice(0, 90) + '…' : x);
        if (s.driver) out.push({ key: 'd:' + s.driver, html: `Driver: ${h(nameIn('characters', s.driver))}` });
        if (s.turning_point) out.push({ key: 't:' + s.turning_point, html: `Turning point: ${h(clip(s.turning_point))}` });
        s.true_character.forEach((t) => out.push({ key: 'tc:' + JSON.stringify(t), html: `True-character: ${h(nameIn('characters', t.character))}${t.dilemma ? ' — ' + h(clip(t.dilemma)) : ''}${t.choice_reveals ? ' → ' + h(clip(t.choice_reveals)) : ''}` }));
        s.changes.forEach((x) => out.push({ key: 'c:' + JSON.stringify(x), html: `Changed: ${h(anyName(x.entity))} — ${h(clip(x.change))}` }));
        s.beats.forEach((x) => {
          const side = (o) => `${o.by ? h(anyName(o.by)) + ': ' : ''}${h(clip(o.surface || o.subtext || '…'))}`;
          out.push({ key: 'b:' + JSON.stringify(x), html: `Beat: ${side(x.action)} ⇄ ${side(x.reaction)}${x.gap ? ' — gap: ' + h(clip(x.gap)) : ''}` });
        });
        return out;
      };
      const was = items(a), now = items(b), r = c.listDiff(was, now);
      // Same beats, different order: the list diff sees nothing, so say it.
      if (JSON.stringify(normSheet(a).beats) !== JSON.stringify(normSheet(b).beats)
          && JSON.stringify(was.map((x) => x.key).sort()) === JSON.stringify(now.map((x) => x.key).sort())) r[1] += '<br><span class="add">Beats reordered</span>';
      return r;
    },
  };
})(window.DASH);
