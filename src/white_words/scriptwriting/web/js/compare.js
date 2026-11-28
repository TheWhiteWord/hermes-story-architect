window.DASH = window.DASH || {};

// Two drafts side by side: every entity that differs, field by field and section by
// section, and the screenplay scene by scene. `html` is pure; `show` loads and wires it.
(function (D) {
  const C = D.draftsCommon;
  const esc = C.esc;
  const plural = (n, w) => n + ' ' + w + (n === 1 ? '' : 's');

  const nameOf = (m, id) => (m.names[id] ? m.names[id].name : id);

  const SHOWN = 24;

  function diffRow(o) {
    if (o.op === 'gap') return '<div class="ln gap">⋯ ' + plural(o.skipped, 'unchanged line') + '</div>';
    const g = o.op === 'add' ? '+' : o.op === 'del' ? '−' : ' ';
    return '<div class="ln ' + o.op + '"><span class="g" aria-hidden="true">' + g + '</span>' + (esc(o.text) || ' ') + '</div>';
  }

  // A scene that is new in one draft is all additions; past a screenful the rest folds.
  function diffBlock(a, b) {
    const ops = D.textDiff.collapse(D.textDiff.lines(a, b), 2);
    const rest = ops.slice(SHOWN);
    return '<div class="cp-diff">' + ops.slice(0, SHOWN).map(diffRow).join('')
      + (rest.length ? '<details class="cp-more"><summary>Show ' + plural(rest.length, 'more line') + '</summary>' + rest.map(diffRow).join('') + '</details>' : '') + '</div>';
  }

  // A scene's Content is its script text, and the Script tab shows it in full; here it is
  // only counted, so the entities tab stays about what else changed.
  function scriptNote(id, v) {
    const ops = D.textDiff.lines(v.a, v.b);
    const n = (op) => ops.filter((o) => o.op === op).length;
    return '<div class="cp-scriptnote">Script text changed · <span class="plus">+' + n('add') + '</span> <span class="minus">−' + n('del') + '</span> '
      + (n('add') === 1 && n('del') === 0 ? 'line' : 'lines') + ' <button class="cp-link" data-cp="goto" data-scene="' + esc(id) + '">See it in the Script tab</button></div>';
  }

  function fieldRow(key, v, m) {
    const name = (id) => (m.names[id] ? m.names[id].name : undefined);
    return '<div class="cp-field"><div class="cp-key">' + esc(C.keyLabel(key)) + '</div><div class="cp-vals">'
      + '<div class="cp-val a">' + C.fmtValue(v.a, name) + '</div><div class="cp-val b">' + C.fmtValue(v.b, name) + '</div></div></div>';
  }

  function entityRow(e, m, i) {
    const name = esc(nameOf(m, e.id));
    const head = '<span class="cp-chip st-' + e.status + '">' + e.status + '</span><span class="cp-type">' + esc(C.typeWord(e.type)) + '</span><span class="cp-name">' + name + '</span>';
    if (e.status !== 'changed') {
      const where = e.status === 'added' ? m.labels.b : m.labels.a;
      return '<div class="cp-ent flat"><div class="cp-sum">' + head + '<span class="cp-note">only in ' + esc(where) + '</span></div></div>';
    }
    const fields = Object.keys(e.fields || {});
    const secs = Object.keys(e.sections || {});
    const body = (h) => (e.type === 'scene' && h === 'Content' ? scriptNote(e.id, e.sections[h]) : diffBlock(e.sections[h].a, e.sections[h].b));
    return '<details class="cp-ent"' + (i < 3 ? ' open' : '') + '><summary class="cp-sum">' + head + '<span class="cp-note">' + plural(fields.length + secs.length, 'difference') + '</span></summary><div class="cp-body">'
      + fields.map((k) => fieldRow(k, e.fields[k], m)).join('')
      + secs.map((h) => '<div class="cp-sec"><div class="cp-key">' + esc(h) + '</div>' + body(h) + '</div>').join('')
      + '</div></details>';
  }

  function orderRow(key, v, m) {
    const i = key.indexOf(':');
    const type = key.slice(0, i);
    const parent = key.slice(i + 1);
    const inA = new Set(v.a || []);
    const inB = new Set(v.b || []);
    const list = (ids, other, cls) => '<ol class="cp-order">' + (ids || []).map((id) => '<li class="' + (other.has(id) ? '' : cls) + '">' + esc(nameOf(m, id)) + '</li>').join('') + '</ol>';
    return '<div class="cp-field"><div class="cp-key">Order of ' + esc(C.typeLabel(type).toLowerCase()) + ' in ' + esc(nameOf(m, parent)) + '</div><div class="cp-vals">'
      + '<div class="cp-val a">' + list(v.a, inB, 'del') + '</div><div class="cp-val b">' + list(v.b, inA, 'add') + '</div></div></div>';
  }

  function summary(m) {
    const ents = Object.keys(m.diff.entities).map((k) => m.diff.entities[k]);
    const n = (st) => ents.filter((e) => e.status === st).length;
    const total = n('changed') + n('added') + n('removed');
    const kinds = [n('changed') && n('changed') + ' changed', n('added') && n('added') + ' added', n('removed') && n('removed') + ' removed'].filter(Boolean);
    const scenes = (m.diff.script || []).filter((r) => r.status !== 'unchanged').length;
    const orders = Object.keys(m.diff.order || {}).length;
    const bits = [];
    if (total) bits.push((total === 1 ? '1 entity differs' : total + ' entities differ') + ' (' + kinds.join(', ') + ')');
    if (orders) bits.push(plural(orders, 'order change'));
    if (scenes) bits.push((scenes === 1 ? '1 scene differs' : scenes + ' scenes differ') + ' in the script');
    return { text: bits.join(' · '), identical: !bits.length };
  }

  function entitiesBody(m) {
    const ents = Object.keys(m.diff.entities).map((k) => m.diff.entities[k]).filter((e) => e.status !== 'unchanged')
      .sort((a, b) => C.typeRank(a.type) - C.typeRank(b.type));
    const order = Object.keys(m.diff.order || {});
    if (!ents.length && !order.length) return '<p class="pj-empty">No entity differs.</p>';
    return '<div class="cp-cols"><span>A · ' + esc(m.labels.a) + '</span><span>B · ' + esc(m.labels.b) + '</span></div>'
      + ents.map((e, i) => entityRow(e, m, i)).join('')
      + (order.length ? '<h3 class="pj-sub">Order</h3>' + order.map((k) => orderRow(k, m.diff.order[k], m)).join('') : '');
  }

  const ELEMENT = {
    heading: ['h3', 'fountain-scene_heading'], action: ['p', 'fountain-action'], character: ['h4', 'fountain-character'],
    parenthetical: ['p', 'fountain-parenthetical'], dialogue: ['p', 'fountain-dialogue'], transition: ['h2', 'fountain-transition'],
    note: ['p', 'fountain-note'], raw: ['p', 'fountain-action'],
  };

  // One screenplay block, set the way the Script view sets it. A heading carries the
  // scene's number in the script it belongs to (the one it has on that side).
  function blockEl(block, number) {
    const [tag, cls] = ELEMENT[block.type] || ELEMENT.raw;
    const num = block.type === 'heading' && number != null ? ' data-scenenumber="' + esc(number) + '"' : '';
    return '<' + tag + ' class="' + cls + '"' + num + '>' + esc(block.text) + '</' + tag + '>';
  }

  function blockRow(o, r) {
    if (o.op === 'gap') return '<div class="cs-row gap">⋯ ' + plural(o.skipped, 'unchanged block') + '</div>';
    const g = o.op === 'add' ? '+' : o.op === 'del' ? '−' : ' ';
    const number = o.op === 'del' ? r.number.a : (r.number.b != null ? r.number.b : r.number.a);
    return '<div class="cs-row ' + o.op + '"><span class="g" aria-hidden="true">' + g + '</span><div class="cs-block">' + blockEl(o.block, number) + '</div></div>';
  }

  function screenplayDiff(r) {
    const ops = D.textDiff.collapse(D.textDiff.blocks(r.blocks && r.blocks.a, r.blocks && r.blocks.b), 2, true);
    const rest = ops.slice(SHOWN);
    return '<div class="screenplay-doc screenplay-content cs">' + ops.slice(0, SHOWN).map((o) => blockRow(o, r)).join('')
      + (rest.length ? '<details class="cp-more"><summary>Show ' + plural(rest.length, 'more block') + '</summary>' + rest.map((o) => blockRow(o, r)).join('') + '</details>' : '') + '</div>';
  }

  // "Scene 7", or how the number moved, in the script the scene is part of.
  function numberText(r) {
    const a = r.number && r.number.a;
    const b = r.number && r.number.b;
    if (a == null && b == null) return 'no script text';
    if (a == null) return 'scene ' + b + ' (new)';
    if (b == null) return 'was scene ' + a;
    return a === b ? 'scene ' + b : 'scene ' + a + ' → ' + b;
  }

  function where(p, m) {
    return p ? [nameOf(m, p.act), nameOf(m, p.sequence)].join(' · ') : '';
  }

  function scriptBody(m) {
    const rows = m.diff.script || [];
    const same = rows.filter((r) => r.status === 'unchanged');
    const shown = rows.filter((r) => m.showSame || r.status !== 'unchanged');
    const toggle = same.length ? '<label class="cp-same"><input type="checkbox" data-cp="same"' + (m.showSame ? ' checked' : '') + '> Show ' + plural(same.length, 'unchanged scene') + '</label>' : '';
    if (!shown.length) return toggle + '<p class="pj-empty">No scene differs.</p>';
    return toggle + shown.map((r) => {
      const a = r.placement && r.placement.a;
      const b = r.placement && r.placement.b;
      const moved = a && b && where(a, m) !== where(b, m);
      const place = moved ? 'was ' + where(a, m) + ' → now ' + where(b, m) : where(b || a, m);
      const body = r.status === 'moved' && (r.text || {}).a === (r.text || {}).b ? '' : screenplayDiff(r);
      return '<section class="cp-scene" data-scene="' + esc(r.id) + '"><header class="cp-sum"><span class="cp-chip st-' + r.status + '">' + r.status + '</span><span class="cp-name">' + esc(nameOf(m, r.id)) + '</span>'
        + '<span class="cp-note">' + esc(numberText(r) + (place ? ' · ' + place : '')) + '</span></header>' + body + '</section>';
    }).join('');
  }

  function picker(side, value, hist) {
    const groups = C.refOptions(hist).filter((g) => g.items.length);
    const known = groups.some((g) => g.items.some((i) => i.ref === value));
    return '<select class="cp-pick" data-cp="pick" data-side="' + side + '" aria-label="Draft ' + side.toUpperCase() + '">'
      + (known ? '' : '<option value="' + esc(value) + '" selected>' + esc(value) + '</option>')
      + groups.map((g) => '<optgroup label="' + esc(g.group) + '">' + g.items.map((i) => '<option value="' + esc(i.ref) + '"' + (i.ref === value ? ' selected' : '') + '>' + esc(i.label) + '</option>').join('') + '</optgroup>').join('') + '</select>';
  }

  // A merge goes into a branch's open draft, so A has to be one; B is where it comes from.
  function mergeBar(m) {
    if (m.a === m.b) return '';
    if (m.a.indexOf('branch:') !== 0) return '<p class="cp-hint">To bring changes from B into a branch, choose that branch\'s open draft as A.</p>';
    const target = (m.hist.branches || []).find((b) => 'branch:' + b.id === m.a);
    return '<div class="cp-mergebar"><button class="btn btn-primary" data-cp="merge">Merge B into ' + esc(target ? target.name : 'this branch') + '…</button>'
      + '<span class="cp-hint">Choose which changes to bring, then settle what clashes. Nothing is applied until you say so.</span></div>';
  }

  function html(m) {
    const s = summary(m);
    const tab = (id, label) => '<button class="dr-tab' + (m.tab === id ? ' on' : '') + '" role="tab" aria-selected="' + (m.tab === id) + '" data-cp="tab" data-tab="' + id + '">' + label + '</button>';
    const body = s.identical ? '<p class="pj-empty">These two drafts are identical.</p>' : (m.tab === 'script' ? scriptBody(m) : entitiesBody(m));
    return '<div class="pj-inner dr"><header class="dr-head"><a class="btn" href="#/">← Projects</a><h1>Compare</h1><span class="pj-chip">' + esc(m.projectName) + '</span></header>'
      + '<div class="cp-picks"><label>A ' + picker('a', m.a, m.hist) + '</label><button class="btn" data-cp="swap" title="Swap A and B" aria-label="Swap A and B">⇄</button><label>B ' + picker('b', m.b, m.hist) + '</label></div>'
      + mergeBar(m)
      + '<p class="cp-summary">' + esc(s.text) + '</p>'
      + (s.identical ? '' : '<div class="dr-tabs" role="tablist">' + tab('entities', 'Entities') + tab('script', 'Script') + '</div>') + body + '</div>';
  }

  D.compare = { html, summary, parts: { fieldRow, diffBlock, orderRow, screenplayDiff, numberText, where, scriptNote, nameOf } };

  if (typeof document === 'undefined') return;

  const S = { tab: 'entities', showSame: false };

  async function show(el, route, ctx) {
    const { slug, a, b } = route;
    el.onclick = null;
    el.onchange = null;
    el.innerHTML = '<div class="pj-inner"><p class="pj-empty">Comparing…</p></div>';
    let m;
    try {
      const [hist, diff, ia, ib] = await Promise.all([
        D.historyApi(slug, 'GET', '/'),
        D.historyApi(slug, 'GET', '/diff?a=' + encodeURIComponent(a) + '&b=' + encodeURIComponent(b)),
        D.historyApi(slug, 'GET', '/read/' + encodeURIComponent(a) + '/entities'),
        D.historyApi(slug, 'GET', '/read/' + encodeURIComponent(b) + '/entities'),
      ]);
      const names = {};
      ia.entities.concat(ib.entities).forEach((e) => { names[e.id] = { name: e.name, type: e.type }; });
      ib.entities.forEach((e) => { names[e.id] = { name: e.name, type: e.type }; });
      m = { projectName: ctx.projectName(slug), a, b, hist, diff, names, labels: { a: C.refLabel(a, hist), b: C.refLabel(b, hist) }, tab: S.tab, showSame: S.showSame };
    } catch (e) {
      el.innerHTML = '<div class="pj-inner"><a class="btn" href="#/">← Projects</a><p class="pj-empty bad">' + esc(e.message) + '</p></div>';
      return;
    }
    const draw = () => { const top = el.scrollTop; el.innerHTML = html(m); el.scrollTop = top; };
    const go = (na, nb) => { location.hash = C.href({ kind: 'compare', slug, a: na, b: nb }); };

    el.onclick = (e) => {
      const t = e.target.closest('[data-cp]');
      if (!t) return;
      if (t.dataset.cp === 'tab') { m.tab = S.tab = t.dataset.tab; draw(); }
      else if (t.dataset.cp === 'swap') go(m.b, m.a);
      else if (t.dataset.cp === 'merge') {
        D.historyApi(slug, 'POST', '/merges', { target: m.a.slice('branch:'.length), source: m.b })
          .then((started) => { location.hash = C.href({ kind: 'merge', slug, session: started.id }); })
          .catch((err) => D.efToast && D.efToast(err.message, 'bad'));
      }
      else if (t.dataset.cp === 'goto') {
        m.tab = S.tab = 'script';
        draw();
        const sc = Array.prototype.find.call(el.querySelectorAll('[data-scene]'), (x) => x.dataset.scene === t.dataset.scene);
        if (sc) sc.scrollIntoView({ block: 'start' });
      }
    };
    el.onchange = (e) => {
      const t = e.target.closest('[data-cp]');
      if (!t) return;
      if (t.dataset.cp === 'pick') go(t.dataset.side === 'a' ? t.value : m.a, t.dataset.side === 'b' ? t.value : m.b);
      else if (t.dataset.cp === 'same') { m.showSame = S.showSame = t.checked; draw(); }
    };
    draw();
  }

  D.compare.show = show;
})(window.DASH);
