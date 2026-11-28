window.DASH = window.DASH || {};

// The merge workspace: what a branch can take from another draft, what clashes, and the
// preview and apply. A merge is a session on the server; this page only reads its plan and
// sends choices back. `html` is pure; `show` loads and wires it.
(function (D) {
  const C = D.draftsCommon;
  const P = D.compare.parts;
  const esc = C.esc;
  const plural = (n, w) => n + ' ' + w + (n === 1 ? '' : /(ch|sh|s|x)$/.test(w) ? 'es' : 's');

  const STATE = { take: 'changed in B', conflict: 'changed on both sides', keep: 'only changed on your side', same: 'same on both sides' };
  const TITLE = {
    D1: 'The same id was added on both sides', D2: 'Changed on both sides', D3: 'Where it goes', D4: 'Role collision',
    D5: 'Something it needs is missing', D6: 'It is in your trash', D7: 'Order changed on both sides', D8: 'Clean up',
    D9: 'Deleted on one side, edited on the other',
  };
  const OPTIONAL = { D3: 1, D5: 1, D8: 1 };
  const LABEL = {
    mine: 'Keep mine', theirs: 'Take theirs', replace: 'Replace the old scene', 'keep-mine': 'Keep mine', 'take-theirs': 'Take theirs',
    'keep-both': 'Keep both', combine: 'Combine field by field', bring: 'Bring it along', drop: 'Leave it out', cancel: 'Skip this change',
    restore: 'Restore it', keep: 'Keep it', delete: 'Delete it',
  };
  const CUSTOM = { D2: 'Write my own', D4: 'Another role…', D7: 'Arrange it…' };
  // Delete against edit: which side deleted decides what each answer means.
  const D9_LABEL = {
    ours: { 'keep-mine': 'Keep it deleted', 'take-theirs': 'Restore it, with B’s changes' },
    theirs: { 'keep-mine': 'Keep it, with my changes', 'take-theirs': 'Delete it' },
  };
  const optLabel = (d, o) => {
    if (o === 'custom') return CUSTOM[d.code] || 'Write my own';
    if (d.code === 'D9' && D9_LABEL[d.deleted_on === 'theirs' ? 'theirs' : 'ours'][o]) return D9_LABEL[d.deleted_on === 'theirs' ? 'theirs' : 'ours'][o];
    return LABEL[o] || o;
  };

  const nameOf = (m, id) => P.nameOf(m, id);
  const selectable = (it) => it.state === 'take' || it.state === 'conflict';
  const text = (v) => (typeof v === 'string' ? v : v == null ? '' : JSON.stringify(v, null, 2));

  // "Scene “The farm” · status", whatever kind of key it is.
  function subject(key, m) {
    const p = String(key).split(':');
    if (p[0] === 'entity') return C.typeWord(p[1]) + ' “' + nameOf(m, p[2]) + '”';
    if (p[0] === 'field' || p[0] === 'section') return C.typeWord(p[1]) + ' “' + nameOf(m, p[2]) + '” · ' + C.keyLabel(p.slice(3).join(':'));
    if (p[0] === 'order') return 'Order of ' + C.typeLabel(p[1]).toLowerCase() + ' in ' + nameOf(m, p.slice(2).join(':'));
    return key;
  }

  // ─── decisions ───

  function editorHtml(d, m) {
    const key = esc(d.key);
    if (d.choice === 'custom' && d.code === 'D2') {
      return '<textarea class="ef-input ef-area mg-val" data-mg="val" data-key="' + key + '" rows="' + (String(text(d.value)).split('\n').length > 3 ? 8 : 3) + '" aria-label="Your value">' + esc(text(d.value)) + '</textarea>';
    }
    if (d.choice === 'custom' && d.code === 'D4') {
      return '<select class="cp-pick" data-mg="val" data-key="' + key + '" aria-label="Role">'
        + (d.roles || []).map((r) => '<option value="' + esc(r) + '"' + (d.value === r ? ' selected' : '') + '>' + esc(C.keyLabel(r)) + '</option>').join('') + '</select>';
    }
    if (d.choice === 'keep-both' && d.code === 'D1') {
      const v = d.value && typeof d.value === 'object' ? d.value : {};
      const nameKey = d.theirs && d.theirs.fields && 'title' in d.theirs.fields && !('name' in d.theirs.fields) ? 'title' : 'name';
      const shown = (v.fields && v.fields[nameKey]) || ((d.theirs && d.theirs.fields && d.theirs.fields[nameKey]) || '');
      return '<div class="mg-keepboth"><label class="ef-field"><span class="ef-label">New id for theirs</span><input class="ef-input" data-mg="val" data-part="id" data-key="' + key + '" value="' + esc(v.id || d.suggested_id || '') + '"></label>'
        + '<label class="ef-field"><span class="ef-label">' + esc(C.keyLabel(nameKey)) + ' for theirs</span><input class="ef-input" data-mg="val" data-part="field" data-field="' + esc(nameKey) + '" data-key="' + key + '" value="' + esc(shown) + '"></label></div>';
    }
    if (d.choice === 'custom' && d.code === 'D7') {
      const list = Array.isArray(d.value) ? d.value : [];
      return '<ol class="mg-order">' + list.map((id, i) => '<li><span>' + esc(nameOf(m, id)) + '</span>'
        + '<button class="btn" data-mg="move" data-key="' + key + '" data-i="' + i + '" data-dir="-1" aria-label="Move up"' + (i ? '' : ' disabled') + '>↑</button>'
        + '<button class="btn" data-mg="move" data-key="' + key + '" data-i="' + i + '" data-dir="1" aria-label="Move down"' + (i < list.length - 1 ? '' : ' disabled') + '>↓</button></li>').join('') + '</ol>';
    }
    return '';
  }

  function sidesHtml(d, m) {
    if (d.code === 'D2') return '<div class="cp-vals"><div class="cp-val a"><span class="mg-who">Mine</span>' + C.fmtValue(d.ours, (id) => (m.names[id] ? m.names[id].name : undefined)) + '</div><div class="cp-val b"><span class="mg-who">Theirs</span>' + C.fmtValue(d.theirs, (id) => (m.names[id] ? m.names[id].name : undefined)) + '</div></div>';
    if (d.code === 'D1') {
      const f = (e) => (e && e.fields && (e.fields.name || e.fields.title)) || (e && e.id) || '';
      return '<div class="cp-vals"><div class="cp-val a"><span class="mg-who">Mine</span>' + esc(f(d.ours)) + '</div><div class="cp-val b"><span class="mg-who">Theirs</span>' + esc(f(d.theirs)) + '</div></div>';
    }
    if (d.code === 'D4' && d.holder) return '<div class="cp-hint">Currently on “' + esc(d.holder.name) + '”.</div>';
    if (d.code === 'D7') return P.orderRow(String(d.item).slice('order:'.length), { a: d.ours, b: d.theirs }, m);
    if (d.code === 'D3') return '<div class="cp-hint">Placed after the scene that came before it in B when that scene is here, otherwise before the one that followed.</div>';
    if (d.code === 'D9') return '<div class="cp-hint">Deleted ' + (d.deleted_on === 'theirs' ? 'in B' : 'on your side') + ', changed ' + (d.deleted_on === 'theirs' ? 'on your side' : 'in B') + '.</div>';
    return '';
  }

  function decisionHtml(d, m) {
    const mine = d.set_by === 'user';
    const suggested = d.set_by === 'agent-suggested';
    const open = !mine && !OPTIONAL[d.code];
    const badge = d.error ? '<span class="pj-chip changed">needs your choice</span>'
      : suggested ? '<span class="pj-chip">suggested by Hermes</span>'
        : open ? '<span class="pj-chip changed">needs your choice</span>'
          : mine ? '<span class="pj-chip current">answered</span>' : '<span class="pj-chip">default applies</span>';
    const options = d.code === 'D3' ? '' : d.options.map((o) => {
      const on = (mine || suggested) && d.choice === o;
      return '<button class="mg-opt' + (on ? ' on' : '') + '" data-mg="choose" data-key="' + esc(d.key) + '" data-choice="' + esc(o) + '" aria-pressed="' + on + '">' + esc(optLabel(d, o)) + '</button>';
    }).join('');
    return '<section class="mg-decision' + (d.error || open ? ' open' : '') + '" data-decision="' + esc(d.key) + '"><header class="cp-sum"><span class="cp-name">' + esc(TITLE[d.code] || d.kind) + '</span><span class="cp-type">' + esc(subject(d.item, m)) + '</span>' + badge + '</header>'
      + '<div class="cp-body"><p class="mg-msg">' + esc(d.message || '') + '</p>' + sidesHtml(d, m)
      + (suggested ? '<div class="mg-suggest">Hermes suggests “' + esc(optLabel(d, d.choice)) + '”. <button class="btn btn-primary" data-mg="accept" data-key="' + esc(d.key) + '">Accept</button></div>' : '')
      + (options ? '<div class="mg-opts" role="group" aria-label="Your choice">' + options + '</div>' : '')
      + editorHtml(d, m)
      + (d.error ? '<p class="mg-error" role="alert">' + esc(d.error) + '</p>' : '')
      + '<button class="cp-link mg-ask" data-mg="ask" data-key="' + esc(d.key) + '">Ask Hermes about this</button></div></section>';
  }

  // ─── what can be brought ───

  function pairOf(it, m) {
    const e = (m.diff.entities || {})[it.id] || {};
    const from = it.kind === 'section' ? (e.sections || {})[it.name] : (e.fields || {})[it.name];
    if (it.kind === 'order') {
      const o = (m.diff.order || {})[it.key.slice('order:'.length)] || {};
      return { a: it.ours !== undefined ? it.ours : o.a, b: it.theirs !== undefined ? it.theirs : it.value !== undefined ? it.value : o.b };
    }
    return { a: it.ours !== undefined ? it.ours : from && from.a, b: it.theirs !== undefined ? it.theirs : it.value !== undefined ? it.value : from && from.b };
  }

  function valuesHtml(it, m) {
    if (it.kind === 'entity') {
      const clash = String(it.decision || '').split('#')[1];
      const what = it.deletes ? 'Deleted in B.' : clash === 'D9' ? 'You deleted it and B changed it: decide below.' : clash === 'D1' ? 'Both sides added it: decide below.' : it.in_trash ? 'It is in your trash.' : 'New in B; it comes with what it needs.';
      return '<div class="cp-hint">' + esc(what) + '</div>';
    }
    const v = pairOf(it, m);
    if (it.kind === 'order') return P.orderRow(it.key.slice('order:'.length), v, m);
    if (it.kind === 'section') return it.type === 'scene' && it.name === 'Content' ? P.scriptNote(it.id, v) : P.diffBlock(v.a, v.b);
    const name = (id) => (m.names[id] ? m.names[id].name : undefined);
    return '<div class="cp-vals"><div class="cp-val a">' + C.fmtValue(v.a, name) + '</div><div class="cp-val b">' + C.fmtValue(v.b, name) + '</div></div>';
  }

  function itemRow(it, m) {
    const on = m.selected.has(it.key);
    const can = selectable(it);
    const what = it.kind === 'entity' ? (it.deletes ? 'Delete' : 'Bring') + ' this ' + C.typeWord(it.type) : it.kind === 'order' ? 'Order' : C.keyLabel(it.name);
    const clash = String(it.decision || '').split('#')[1];
    const stateText = it.kind === 'entity'
      ? (it.deletes ? 'deleted in B' : clash === 'D9' ? 'deleted here, changed in B' : clash === 'D1' ? 'added on both sides' : it.in_trash ? 'in your trash' : 'new in B')
      : STATE[it.state] || it.state;
    return '<div class="mg-item ' + it.state + '" data-item="' + esc(it.key) + '"><label class="mg-tick"><input type="checkbox" data-mg="tick" data-key="' + esc(it.key) + '"' + (on ? ' checked' : '') + (can ? '' : ' disabled') + ' aria-label="Bring ' + esc(subject(it.key, m)) + '">'
      + '<span class="mg-what">' + esc(what) + '</span></label><span class="cp-chip st-' + (it.state === 'conflict' ? 'changed' : it.state === 'take' ? 'added' : 'removed') + '">' + esc(stateText) + '</span>'
      + (can || it.state === 'keep' ? '<div class="mg-vals">' + (it.state === 'keep' ? '<div class="cp-hint">Nothing to bring: only your side changed it.</div>' : valuesHtml(it, m)) + '</div>' : '') + '</div>';
  }

  function groups(m) {
    const by = {};
    m.plan.items.filter((it) => it.state !== 'same' && (m.showKept || it.state !== 'keep')).forEach((it) => {
      const g = it.kind === 'order' ? 'order' : it.type + ':' + it.id;
      (by[g] = by[g] || { key: g, type: it.kind === 'order' ? 'order' : it.type, id: it.id, items: [] }).items.push(it);
    });
    return Object.keys(by).map((k) => by[k]).sort((a, b) => (a.key === 'order') - (b.key === 'order') || C.typeRank(a.type) - C.typeRank(b.type));
  }

  function changesBody(m) {
    const gs = groups(m);
    if (!gs.length) return '<p class="pj-empty">There is nothing to bring from B: every difference is on your side only.</p>';
    return gs.map((g) => {
      const can = g.items.filter(selectable);
      const picked = can.filter((it) => m.selected.has(it.key)).length;
      const state = !can.length ? '' : picked === can.length ? ' checked' : picked ? ' data-partial="1"' : '';
      const head = g.key === 'order' ? 'Order' : esc(nameOf(m, g.id));
      return '<section class="cp-ent mg-group"><header class="cp-sum"><label class="mg-tick"><input type="checkbox" data-mg="group" data-group="' + esc(g.key) + '"' + state + (can.length ? '' : ' disabled') + ' aria-label="Everything for ' + head + '"><span class="cp-name">' + head + '</span></label>'
        + (g.key === 'order' ? '' : '<span class="cp-type">' + esc(C.typeWord(g.type)) + '</span>') + '</header><div class="cp-body">' + g.items.map((it) => itemRow(it, m)).join('') + '</div></section>';
    }).join('');
  }

  // ─── the script lens: a scene stands for all of its items ───

  function sceneKeys(row, m) {
    const known = {};
    m.plan.items.forEach((it) => { known[it.key] = it; });
    return (row.items || []).filter((k) => known[k] && selectable(known[k]));
  }

  function scriptBody(m) {
    const rows = (m.diff.script || []).filter((r) => r.status !== 'unchanged');
    if (!rows.length) return '<p class="pj-empty">No scene differs.</p>';
    return rows.map((r) => {
      const keys = sceneKeys(r, m);
      const picked = keys.filter((k) => m.selected.has(k)).length;
      const state = !keys.length ? '' : picked === keys.length ? ' checked' : picked ? ' data-partial="1"' : '';
      const body = r.status === 'moved' && (r.text || {}).a === (r.text || {}).b ? '' : P.screenplayDiff(r);
      return '<section class="cp-scene" data-scene="' + esc(r.id) + '"><header class="cp-sum"><label class="mg-tick"><input type="checkbox" data-mg="scene" data-id="' + esc(r.id) + '"' + state + (keys.length ? '' : ' disabled') + ' aria-label="Bring ' + esc(nameOf(m, r.id)) + '"><span class="cp-chip st-' + r.status + '">' + r.status + '</span><span class="cp-name">' + esc(nameOf(m, r.id)) + '</span></label>'
        + '<span class="cp-note">' + esc(P.numberText(r) + (keys.length ? '' : ' · only changed on your side')) + '</span></header>' + body + '</section>';
    }).join('');
  }

  // ─── the page ───

  function previewHtml(pv) {
    if (!pv) return '';
    if (pv.status === 'clean') return '<p class="mg-verdict ok" role="status">Preview is clean: ' + plural(pv.plan && pv.plan.ops ? pv.plan.ops.length : 0, 'operation') + ' would be applied.</p>';
    if (pv.status === 'blocked') return '<p class="mg-verdict bad" role="status">' + esc(pv.message || 'Some decisions are still unanswered.') + '</p>';
    const fails = (pv.failures || []).map((f) => '<li>' + esc(f.message || f.error || JSON.stringify(f)) + '</li>').join('');
    return '<div class="mg-verdict bad" role="alert"><p>' + esc(pv.message || 'The preview refused this merge.') + '</p>' + (fails ? '<ul>' + fails + '</ul>' : '') + '</div>';
  }

  function html(m) {
    const closed = m.session && m.session.status && m.session.status !== 'open' && !m.result;
    if (closed) {
      return '<div class="pj-inner dr"><header class="dr-head"><a class="btn" href="#/">← Projects</a><h1>This merge is closed</h1></header>'
        + '<p>It was ' + esc(m.session.status) + (m.session.status === 'applied' ? ' and its changes are in ' + esc(m.target.name) + '.' : ' without applying anything.') + ' Start a new merge from Compare to bring changes across.</p></div>';
    }
    if (m.result) {
      return '<div class="pj-inner dr"><header class="dr-head"><h1>Merge applied</h1><span class="pj-chip st-added">into ' + esc(m.target.name) + '</span></header>'
        + '<p>' + esc(plural(m.result.ops_applied != null ? m.result.ops_applied : (m.plan.ops || []).length, 'change')) + ' brought from ' + esc(m.sourceLabel) + (m.result.complete ? ', recorded as a complete merge.' : '.') + '</p>'
        + '<p class="cp-hint">' + (m.result.complete ? 'The next draft you save on ' + esc(m.target.name) + ' will record this merge in its history.' : 'What you left out is still offered next time.') + '</p>'
        + '<div class="mg-bar"><a class="btn btn-primary" href="#/" data-mg="done">Back to drafts</a></div></div>';
    }
    const plan = m.plan;
    const items = plan.items.filter((it) => it.state !== 'same');
    const take = items.filter(selectable).length;
    const kept = items.filter((it) => it.state === 'keep').length;
    const conflicts = items.filter((it) => it.state === 'conflict').length;
    const open = plan.open.length;
    const picked = m.selected.size;
    const tab = (id, label) => '<button class="dr-tab' + (m.tab === id ? ' on' : '') + '" role="tab" aria-selected="' + (m.tab === id) + '" data-mg="tab" data-tab="' + id + '">' + label + '</button>';
    const decisions = plan.decisions.length ? '<div class="mg-decisions"><h3 class="pj-sub">Decisions · ' + (open ? open + ' open' : 'all answered') + '</h3>' + plan.decisions.map((d) => decisionHtml(d, m)).join('') + '</div>' : '';
    const blocked = !picked ? 'Tick something to bring first.' : open ? plural(open, 'decision') + ' still open.' : '';
    return '<div class="pj-inner dr"><header class="dr-head"><a class="btn" href="#/">← Projects</a><h1>Merge into ' + esc(m.target.name) + '</h1><span class="pj-chip">from ' + esc(m.sourceLabel) + '</span></header>'
      + (m.stale ? '<div class="mg-banner" role="alert">The branch changed after this plan was made. <button class="cp-link" data-mg="replan">Refresh the plan</button></div>' : '')
      + (m.imprecise ? '<div class="mg-banner">These drafts share more than one common ancestor, so the merge may show more clashes than it needs to.</div>' : '')
      + '<p class="cp-summary">' + esc(plural(take, 'change') + ' can be brought' + (conflicts ? ', ' + conflicts + (conflicts === 1 ? ' of them clashes' : ' of them clash') + ' with yours' : '') + (kept ? ' · ' + kept + ' only on your side' : '')) + '</p>'
      + decisions
      + '<div class="dr-tabs" role="tablist">' + tab('changes', 'Changes') + tab('script', 'Script') + '</div>'
      + (m.tab === 'changes' ? (kept ? '<label class="cp-same"><input type="checkbox" data-mg="kept"' + (m.showKept ? ' checked' : '') + '> Show the ' + plural(kept, 'change') + ' that only exist on your side</label>' : '') + changesBody(m) : scriptBody(m))
      + '<div class="mg-footer"><span class="cp-hint">' + esc(picked ? plural(picked, 'item') + ' ticked' : '') + (blocked ? ' · ' + esc(blocked) : '') + '</span><span class="sp"></span>'
      + '<button class="btn" data-mg="discard">Discard</button><button class="btn" data-mg="preview"' + (picked ? '' : ' disabled') + '>Preview</button>'
      + '<button class="btn btn-primary" data-mg="apply"' + (picked && !open && !m.stale ? '' : ' disabled') + '>Apply merge…</button></div>'
      + previewHtml(m.preview) + '</div>';
  }

  D.merge = { html, decisionHtml, subject };

  if (typeof document === 'undefined') return;

  // Hermes plugs in here (the agent tools, T11): it is handed the decision and what the
  // page knows about it. Until then the button says so.
  D.askHermes = D.askHermes || function () {
    if (D.efToast) D.efToast('Hermes cannot see merges from this page yet.', 'bad');
  };

  async function show(el, route, ctx) {
    const { slug } = route;
    el.onclick = null;
    el.onchange = null;
    el.innerHTML = '<div class="pj-inner"><p class="pj-empty">Loading the merge…</p></div>';
    let m;
    const load = async () => {
      const s = await D.historyApi(slug, 'GET', '/merges/' + encodeURIComponent(route.session));
      const targetRef = 'branch:' + s.target_branch_id;
      const sourceRef = (s.source.kind === 'branch' ? 'branch:' : 'snapshot:') + s.source.id;
      return { s, targetRef, sourceRef };
    };
    try {
      const { s, targetRef, sourceRef } = await load();
      const [hist, diff, ia, ib] = await Promise.all([
        D.historyApi(slug, 'GET', '/'),
        D.historyApi(slug, 'GET', '/diff?a=' + encodeURIComponent(targetRef) + '&b=' + encodeURIComponent(sourceRef)),
        D.historyApi(slug, 'GET', '/read/' + encodeURIComponent(targetRef) + '/entities'),
        D.historyApi(slug, 'GET', '/read/' + encodeURIComponent(sourceRef) + '/entities'),
      ]);
      const names = {};
      ia.entities.concat(ib.entities).forEach((e) => { names[e.id] = { name: e.name, type: e.type }; });
      const branch = (hist.branches || []).find((b) => b.id === s.target_branch_id);
      m = {
        projectName: ctx.projectName(slug), sid: s.id, session: s, plan: s.plan, stale: s.stale, imprecise: s.imprecise_base, diff, names,
        target: { id: s.target_branch_id, name: branch ? branch.name : s.target_branch_id }, sourceLabel: C.refLabel(sourceRef, hist),
        labels: { a: C.refLabel(targetRef, hist), b: C.refLabel(sourceRef, hist) }, selected: new Set(s.selection), tab: 'changes', showKept: false, preview: null, result: null,
      };
    } catch (e) {
      el.innerHTML = '<div class="pj-inner"><a class="btn" href="#/">← Projects</a><p class="pj-empty bad">' + esc(e.message) + '</p></div>';
      return;
    }
    const base = '/merges/' + encodeURIComponent(m.sid);
    const draw = () => {
      const top = el.scrollTop;
      el.innerHTML = html(m);
      el.scrollTop = top;
      el.querySelectorAll('input[data-partial]').forEach((i) => { i.indeterminate = true; });
    };
    const fail = (e) => { if (D.efToast) D.efToast(e.message, 'bad'); };
    const refresh = async () => {
      const s = await D.historyApi(slug, 'GET', base);
      m.session = s; m.plan = s.plan; m.stale = s.stale; m.imprecise = s.imprecise_base; m.selected = new Set(s.selection); m.preview = null;
      draw();
    };
    const select = async (keys, on) => {
      keys.forEach((k) => (on ? m.selected.add(k) : m.selected.delete(k)));
      try { await D.historyApi(slug, 'PUT', base + '/selection', { selection: Array.from(m.selected) }); await refresh(); } catch (e) { fail(e); }
    };
    const decide = async (key, choice, value, setBy) => {
      try {
        await D.historyApi(slug, 'PUT', base + '/decisions/' + encodeURIComponent(key), Object.assign({ choice, set_by: setBy || 'user' }, value === undefined ? {} : { value }));
        await refresh();
      } catch (e) { fail(e); }
    };
    const decision = (key) => m.plan.decisions.find((d) => d.key === key);

    // What a custom answer starts as: something valid, so it can be answered at once.
    const starter = (d, choice) => {
      if (choice === 'custom' && d.code === 'D2') return d.theirs;
      if (choice === 'custom' && d.code === 'D4') return (d.roles || []).find((r) => r !== d.role) || d.roles[0];
      if (choice === 'custom' && d.code === 'D7') return (d.ours || []).concat((d.theirs || []).filter((id) => (d.ours || []).indexOf(id) < 0));
      if (choice === 'keep-both') return { id: d.suggested_id };
      return undefined;
    };

    const dialogApply = () => {
      const ops = m.plan.ops.map((o) => '<li>' + esc(o.summary || o.op) + '</li>').join('');
      D.efDialog({
        kicker: 'Apply merge', title: 'Apply this merge to “' + m.target.name + '”?', confirm: 'Apply merge',
        bodyHtml: '<ul class="mg-ops">' + ops + '</ul>'
          + '<label class="pj-check"><input type="checkbox" data-f="complete"> Complete merge: everything in ' + esc(m.sourceLabel) + ' is accounted for. What I did not tick stays as mine and is not offered again.</label>'
          + '<p class="cp-hint">A draft is saved first, so this can be undone.</p>',
        onConfirm: async (dlg) => {
          const complete = !!dlg.el.querySelector('[data-f="complete"]').checked;
          dlg.error('');
          dlg.busy(true);
          try {
            m.result = Object.assign({ complete }, await D.historyApi(slug, 'POST', base + '/apply', { confirm: true, complete }));
            dlg.close();
            draw();
          } catch (e) {
            dlg.error(esc(e.message));
            dlg.busy(false);
            if (e.code === 'stale_plan') { dlg.close(); await refresh(); }
          }
        },
      });
    };

    el.onclick = async (e) => {
      const t = e.target.closest('[data-mg]');
      if (!t) return;
      const a = t.dataset.mg;
      if (a === 'tab') { m.tab = t.dataset.tab; draw(); }
      else if (a === 'choose') {
        const d = decision(t.dataset.key);
        decide(d.key, t.dataset.choice, starter(d, t.dataset.choice));
      } else if (a === 'accept') { const d = decision(t.dataset.key); decide(d.key, d.choice, d.value === null ? undefined : d.value, 'user'); }
      else if (a === 'move') {
        const d = decision(t.dataset.key);
        const list = d.value.slice();
        const i = +t.dataset.i;
        const j = i + +t.dataset.dir;
        const x = list[i]; list[i] = list[j]; list[j] = x;
        decide(d.key, 'custom', list);
      } else if (a === 'ask') {
        const d = decision(t.dataset.key);
        D.askHermes({ slug, session: m.sid, decision: d, subject: subject(d.item, m), target: m.target, source: m.sourceLabel });
      } else if (a === 'preview') {
        try { m.preview = await D.historyApi(slug, 'POST', base + '/preview'); } catch (err) { m.preview = Object.assign({ status: 'refused', message: err.message }, err.detail || {}); }
        draw();
      } else if (a === 'apply') dialogApply();
      else if (a === 'replan') { try { await D.historyApi(slug, 'PUT', base + '/selection', { selection: Array.from(m.selected) }); await refresh(); } catch (err) { fail(err); } }
      else if (a === 'discard') {
        D.efDialog({
          kicker: 'Discard', title: 'Discard this merge?', confirm: 'Discard', bodyHtml: '<p class="pj-dlg">Nothing has been applied. Your ticks and answers are dropped.</p>',
          onConfirm: async (dlg) => {
            try { await D.historyApi(slug, 'DELETE', base); dlg.close(); location.hash = '#/'; } catch (err) { dlg.error(esc(err.message)); dlg.busy(false); }
          },
        });
      } else if (a === 'done') { try { sessionStorage.setItem('ww:expand', slug); } catch (err) { /* private mode */ } }
    };

    el.onchange = (e) => {
      const t = e.target.closest('[data-mg]');
      if (!t) return;
      const a = t.dataset.mg;
      if (a === 'tick') select([t.dataset.key], t.checked);
      else if (a === 'group') {
        const g = groups(m).find((x) => x.key === t.dataset.group);
        if (g) select(g.items.filter(selectable).map((it) => it.key), t.checked);
      } else if (a === 'scene') {
        const row = (m.diff.script || []).find((r) => r.id === t.dataset.id);
        if (row) select(sceneKeys(row, m), t.checked);
      } else if (a === 'kept') { m.showKept = t.checked; draw(); }
      else if (a === 'val') {
        const d = decision(t.dataset.key);
        if (d.code === 'D1') {
          const cur = d.value && typeof d.value === 'object' ? d.value : {};
          const next = { id: cur.id || d.suggested_id, fields: Object.assign({}, cur.fields) };
          if (t.dataset.part === 'id') next.id = t.value.trim(); else next.fields[t.dataset.field] = t.value;
          decide(d.key, 'keep-both', next);
        } else if (d.code === 'D2') {
          let v = t.value;
          if (typeof d.ours !== 'string' && typeof d.theirs !== 'string') {
            try { v = JSON.parse(t.value); } catch (err) { fail(new Error('That is not valid JSON.')); return; }
          }
          decide(d.key, 'custom', v);
        } else decide(d.key, 'custom', t.value);
      }
    };
    draw();
  }

  D.merge.show = show;
})(window.DASH);
