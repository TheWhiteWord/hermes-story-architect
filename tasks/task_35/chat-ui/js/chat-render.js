/* Story Architect chat: rendering of icons, messages, tool cards and draft cards.
   Pure DOM builders; no network, no app state. */
(function () {
  const SA = (window.SAChat = window.SAChat || {});
  const esc = SA.esc;

  const PATHS = {
    chat: '<path d="M2.5 3.5h11v7h-6l-3 2.5v-2.5h-2z"/>',
    send: '<path d="M8 13V3M4 7l4-4 4 4"/>',
    stop: '<rect x="4.5" y="4.5" width="7" height="7" rx="1.5" fill="currentColor" stroke="none"/>',
    retry: '<path d="M3 8a5 5 0 1 0 1.6-3.7M3 2.5v3h3"/>',
    plus: '<path d="M8 3v10M3 8h10"/>',
    newchat: '<path d="M9 3H3.5v9.5H13V7"/><path d="M11.5 2.5l2 2L8 10H6V8z"/>',
    history: '<circle cx="8" cy="8" r="5.5"/><path d="M8 5v3l2 1.5"/>',
    settings: '<path d="M3 5h6M12 5h1M3 11h1M7 11h6"/><circle cx="10.5" cy="5" r="1.5"/><circle cx="5.5" cy="11" r="1.5"/>',
    back: '<path d="M10 3L5 8l5 5"/>',
    chev: '<path d="M6 3.5l4.5 4.5L6 12.5"/>',
    copy: '<rect x="5.5" y="5.5" width="7" height="8" rx="1.2"/><path d="M3.5 10.5v-7h6"/>',
    check: '<path d="M3 8.5l3.2 3L13 4.5"/>',
    x: '<path d="M4 4l8 8M12 4l-8 8"/>',
    down: '<path d="M4 6.5l4 4 4-4"/>',
    agent: '<circle cx="8" cy="3.8" r="1.8"/><circle cx="3.5" cy="12" r="1.8"/><circle cx="12.5" cy="12" r="1.8"/><path d="M8 5.6v2.4M8 8l-3.5 2.4M8 8l3.5 2.4"/>',
    draft: '<path d="M4 2.5h5.5l3 3v8H4z"/><path d="M9.5 2.5v3h3M6 8.5h4.5M6 11h4.5"/>',
    trash: '<path d="M3.5 4.5h9M6.5 4.5v-2h3v2M5 4.5l.5 9h5l.5-9"/>',
  };
  function icon(name, size) {
    const s = size || 14;
    return '<svg class="sa-i" viewBox="0 0 16 16" width="' + s + '" height="' + s + '" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + (PATHS[name] || '') + '</svg>';
  }

  function div(cls, html) { const d = document.createElement('div'); if (cls) d.className = cls; if (html != null) d.innerHTML = html; return d; }
  const clip = (s, n) => { s = String(s); return s.length > n ? s.slice(0, n - 1) + '…' : s; };
  const pretty = (v) => { if (v == null) return ''; if (typeof v === 'string') return v; try { return JSON.stringify(v, null, 2); } catch (e) { return String(v); } };

  function chipHtml(a) { return '<span class="sa-chip static"><span>' + esc(a.label || a.id || a.kind) + '</span></span>'; }

  // ───────── tool cards ─────────
  const HINT_KEYS = ['query', 'id', 'entity_id', 'name', 'action', 'type', 'project', 'slug'];
  function toolHint(args) {
    if (!args || typeof args !== 'object') return '';
    const bits = [];
    for (const k of HINT_KEYS) if (typeof args[k] === 'string' && args[k]) bits.push(args[k]);
    return clip(bits.slice(0, 2).join(' · '), 60);
  }
  function stateIcon(status) {
    if (status === 'finished') return icon('check', 12);
    if (status === 'failed') return icon('x', 12);
    return '<span class="sa-spin"></span>';
  }
  function paintTool(d, t) {
    d.className = 'sa-tool ' + (t.status || 'started');
    d.querySelector('summary').innerHTML =
      '<span class="sa-tstate">' + stateIcon(t.status) + '</span><span class="sa-tname">' + esc(t.name || 'tool') + '</span>' +
      '<span class="sa-thint">' + esc(toolHint(t.args) || clip(t.label || '', 70)) + '</span>' +
      (t.duration_ms != null ? '<span class="sa-tdur">' + (t.duration_ms < 1000 ? Math.round(t.duration_ms) + ' ms' : (t.duration_ms / 1000).toFixed(1) + ' s') + '</span>' : '') +
      '<span class="sa-chev">' + icon('chev', 12) + '</span>';
    const body = d.querySelector('.sa-tool-body');
    const a = pretty(t.args) || (t.label ? String(t.label) : ''), r = pretty(t.result_preview);
    body.innerHTML = (a ? '<div class="sa-tlabel">Arguments</div><pre>' + esc(clip(a, 4000)) + '</pre>' : '') +
      (r ? '<div class="sa-tlabel">Result</div><pre>' + esc(clip(r, 4000)) + '</pre>' : '') +
      (!a && !r ? '<div class="sa-tlabel">No details available</div>' : '');
  }
  function createTool(t) {
    const d = document.createElement('details');
    d.dataset.id = t.id;
    d.innerHTML = '<summary></summary><div class="sa-tool-body"></div>';
    paintTool(d, t);
    return d;
  }

  // ───────── draft cards ─────────
  // A change is: {kind, entity_type, entity_id?, label?, summary?, detail?,
  //   fields?:[{field,before,after}], sections?:[{name,before,after}], unfilled?:[name],
  //   order?:[{id,label,from,to}], count?, reversible?}. Everything is optional except kind;
  // whatever the backend provides is shown, nothing is assumed per entity type.
  const KIND = { create: 'CREATE', edit: 'EDIT', delete: 'DELETE', reorder: 'REORDER' };
  const STATUS = { open: 'Awaiting approval', committed: 'Approved', discarded: 'Rejected', failed: 'Failed' };
  const blank = (v) => v == null || v === '' || (Array.isArray(v) && !v.length);
  const plural = (n, w) => n + ' ' + w + (n === 1 ? '' : 's');
  // ── structured values (lists / objects / keyed objects), rendered recursively ──
  // `node` is an optional schema hint: {type, keyed, sub_fields:{key: node}} (the entity schema's sub_fields).
  // It only influences key order; without it the data's own order is used.
  const isPlain = (o) => o && typeof o === 'object' && !Array.isArray(o);
  const prettyKey = (k) => String(k).replace(/_/g, ' ');
  const SHORT = 28;
  function meter(v) { return '<span class="sa-meter' + (v < 0 ? ' neg' : '') + '"><i style="width:' + Math.round(Math.abs(v) * 100) + '%"></i></span> ' + esc(String(v)); }
  function scalarHtml(v, key) {
    if (v == null || v === '') return '<em>not set</em>';
    if (typeof v === 'boolean') return v ? 'yes' : 'no';
    if (typeof v === 'number') return key === 'strength' && v >= -1 && v <= 1 ? meter(v) : esc(String(v));
    return esc(v);
  }
  function orderKeys(obj, sub) {
    const keys = Object.keys(obj);
    if (!sub) return keys;
    const first = Object.keys(sub).filter((k) => k in obj);
    return first.concat(keys.filter((k) => first.indexOf(k) < 0));
  }
  function renderVal(v, depth, key, node) {
    depth = depth || 0;
    if (v == null || v === '' || (Array.isArray(v) && !v.length) || (isPlain(v) && !Object.keys(v).length)) return '<em>not set</em>';
    if (depth > 5) return '<code>' + esc(JSON.stringify(v)) + '</code>';
    const sub = node && node.sub_fields;
    if (Array.isArray(v)) {
      if (v.every((x) => typeof x === 'string' && x.length <= SHORT && x.indexOf('\n') < 0)) return '<div class="sa-tags">' + v.map((x) => '<span>' + esc(x) + '</span>').join('') + '</div>';
      if (v.every((x) => x == null || typeof x !== 'object')) return '<ul class="sa-vlist">' + v.map((x) => '<li>' + scalarHtml(x, key) + '</li>').join('') + '</ul>';
      const item = sub ? { sub_fields: sub } : null;
      return '<div class="sa-vitems">' + v.map((x) => '<div class="sa-vitem">' + renderVal(x, depth + 1, key, item) + '</div>').join('') + '</div>';
    }
    if (isPlain(v)) {
      const keyed = node && node.keyed;
      const keys = keyed ? Object.keys(v) : orderKeys(v, sub);
      const flat = keys.every((k) => v[k] == null || typeof v[k] !== 'object');
      if (!keyed && flat && keys.length <= 3 && keys.every((k) => String(v[k] == null ? '' : v[k]).length <= 30)) {
        return '<span class="sa-pairs">' + keys.map((k) => '<span class="sa-pair"><span class="k">' + esc(prettyKey(k)) + '</span> ' + scalarHtml(v[k], k) + '</span>').join('') + '</span>';
      }
      return '<dl class="sa-kv">' + keys.map((k) => {
        const val = v[k], nested = val && typeof val === 'object';
        const child = keyed ? (sub ? { sub_fields: sub } : null) : (sub ? sub[k] : null);
        return '<div class="sa-kvrow' + (nested ? ' nested' : '') + '"><dt>' + esc(prettyKey(k)) + '</dt><dd>' + renderVal(val, depth + 1, k, child) + '</dd></div>';
      }).join('') + '</dl>';
    }
    return scalarHtml(v, key);
  }
  const structured = (v) => v != null && typeof v === 'object';
  function valueHtml(v) { return renderVal(v, 0); }
  function fieldRow(f, hints) {
    const node = hints && hints[f.field];
    if (structured(f.after) || structured(f.before)) {
      return '<div class="sa-frow block"><div class="sa-fk">' + esc(f.field) + '</div><div class="sa-val">' + renderVal(f.after, 0, f.field, node) +
        (blank(f.before) ? '' : '<details class="sa-was"><summary>Previous value</summary>' + renderVal(f.before, 0, f.field, node) + '</details>') + '</div></div>';
    }
    const val = blank(f.before)
      ? '<div class="sa-val">' + valueHtml(f.after) + '</div>'
      : '<div class="sa-val"><div class="sa-old">' + valueHtml(f.before) + '</div><div class="sa-new">' + valueHtml(f.after) + '</div></div>';
    return '<div class="sa-frow"><div class="sa-fk">' + esc(f.field) + '</div>' + val + '</div>';
  }
  function sectionHtml(sec, kind) {
    const edit = kind === 'edit', fresh = blank(sec.before);
    return '<div class="sa-sec"><div class="sa-sec-h">' + esc(sec.name) +
      (edit ? '<span class="sa-tag">' + (fresh ? 'new' : 'changed') + '</span>' : '') + '</div>' +
      '<div class="sa-sec-b">' + (blank(sec.after) ? '<em>empty</em>' : esc(sec.after)) + '</div>' +
      (edit && !fresh ? '<details class="sa-was"><summary>Previous text</summary><div class="sa-sec-b">' + esc(sec.before) + '</div></details>' : '') + '</div>';
  }
  function orderHtml(c) {
    const o = c.order || [];
    if (!o.length) return c.count ? '<div class="sa-csum" style="padding-left:0">' + plural(c.count, 'item') + ' in the new order</div>' : '';
    return '<ol class="sa-order">' + o.map((it) => {
      const d = it.from != null && it.to != null ? it.from - it.to : 0;
      return '<li class="' + (d ? 'moved' : '') + '"><span class="sa-pos">' + esc(it.to != null ? it.to : '') + '</span><span class="sa-olabel">' + esc(it.label || it.id) + '</span>' +
        (d > 0 ? '<span class="sa-mv up">↑' + d + '</span>' : d < 0 ? '<span class="sa-mv dn">↓' + -d + '</span>' : '') + '</li>';
    }).join('') + '</ol>';
  }
  function changeHtml(c, open) {
    const kind = c.kind || 'edit';
    const name = c.label || c.entity_id || '';
    const nF = (c.fields || []).length, nS = (c.sections || []).length;
    const counts = kind === 'reorder' ? (c.count ? plural(c.count, 'item') : '') : [nF ? plural(nF, 'field') : '', nS ? plural(nS, 'section') : ''].filter(Boolean).join(' · ');
    let body;
    if (kind === 'delete') {
      body = '<div class="sa-del">Will be removed: <b>' + esc(name || c.entity_type) + '</b>' + (c.detail ? ' — ' + esc(c.detail) : '') +
        '<div class="sa-csum" style="padding-left:0">' + (c.reversible === false ? 'This cannot be undone.' : 'Soft delete — it can be restored later.') + '</div></div>';
    } else if (kind === 'reorder') {
      body = orderHtml(c);
    } else {
      body = (c.fields || []).map((f) => fieldRow(f, c.schema)).join('') + (c.sections || []).map((x) => sectionHtml(x, kind)).join('') +
        ((c.unfilled || []).length ? '<div class="sa-unfilled">Not set yet: ' + c.unfilled.map(esc).join(', ') + '</div>' : '');
      if (!body) body = '<div class="sa-csum" style="padding-left:0">No field details provided.</div>';
    }
    return '<details class="sa-change"' + (open ? ' open' : '') + '><summary><div class="sa-change-top">' +
      '<span class="sa-chev">' + icon('chev', 11) + '</span><span class="sa-kind k-' + esc(kind) + '">' + (KIND[kind] || esc(kind).toUpperCase()) + '</span>' +
      (c.entity_type ? '<span class="sa-etype">' + esc(c.entity_type) + '</span>' : '') +
      (name ? '<span class="sa-target">' + esc(name) + '</span>' : '') +
      (c.label && c.entity_id && c.label !== c.entity_id ? '<span class="sa-tid">' + esc(c.entity_id) + '</span>' : '') +
      (counts ? '<span class="sa-ccount">' + esc(counts) + '</span>' : '') + '</div>' +
      (c.summary ? '<div class="sa-csum">' + esc(c.summary) + '</div>' : '') + '</summary><div class="sa-cbody">' + body + '</div></details>';
  }
  function changesHtml(list) {
    if (!list.length) return '<div class="sa-cbody sa-csum">No changes listed.</div>';
    const items = list.reduce((n, c) => n + (c.fields || []).length + (c.sections || []).length + (c.order ? 1 : 0), 0);
    const all = list.length === 1 || items <= 12;
    return list.map((c, i) => changeHtml(c, all || i === 0)).join('');
  }

  // hooks: { approve(draft)->Promise<draft>, reject(draft)->Promise<draft>, fix(draft) }
  function createDraft(d, hooks) {
    const root = document.createElement('div');
    const api = { root, data: d, busy: false };
    function foot(x) {
      const n = (x.changes || []).length;
      if (x.status === 'committed') return '<div class="sa-draft-foot ok">' + icon('check', 13) + '<span>Approved · ' + n + ' change' + (n === 1 ? '' : 's') + ' applied</span></div>';
      if (x.status === 'discarded') return '<div class="sa-draft-foot mute">' + icon('x', 13) + '<span>Rejected · nothing was changed</span></div>';
      if (x.status === 'failed') return '<div class="sa-draft-foot bad"><span>' + esc(x.error || 'Applying this draft failed.') + '</span><span class="sp"></span><button class="sa-btn" data-act="fix">Ask agent to fix</button></div>';
      return (x.error ? '<div class="sa-draft-warn" style="color:var(--sa-bad)">' + esc(x.error) + '</div>' : '') +
        '<div class="sa-draft-foot"><button class="sa-btn primary" data-act="approve"' + (api.busy ? ' disabled' : '') + '>' + icon('check', 13) + 'Approve</button>' +
        '<button class="sa-btn" data-act="reject"' + (api.busy ? ' disabled' : '') + '>Reject</button></div>';
    }
    function paint() {
      const x = api.data, st = x.status || 'open';
      root.className = 'sa-draft st-' + st;
      root.dataset.id = x.id;
      root.innerHTML = '<div class="sa-draft-head">' + icon('draft', 15) + '<div class="sa-draft-title"><div class="sa-draft-kicker">Proposed changes</div><div class="sa-draft-sum">' + esc(x.summary || x.id) +
        '</div></div><span class="sa-pill ' + st + '">' + (STATUS[st] || esc(st)) + '</span></div>' +
        '<div class="sa-draft-changes">' + changesHtml(x.changes || []) + '</div>' +
        ((x.warnings || []).length ? '<div class="sa-draft-warn">' + x.warnings.map(esc).join('<br>') + '</div>' : '') + foot(x);
    }
    root.addEventListener('click', async (e) => {
      const b = e.target.closest('button[data-act]');
      if (!b || api.busy) return;
      const act = b.dataset.act;
      if (act === 'fix') { hooks.fix && hooks.fix(api.data); return; }
      api.busy = true; paint();
      try { const nd = await (act === 'approve' ? hooks.approve(api.data) : hooks.reject(api.data)); api.data = Object.assign({}, api.data, nd, { error: nd.error || null }); }
      catch (err) { api.data = Object.assign({}, api.data, { error: err.message || 'Request failed.' }); }
      api.busy = false; paint();
    });
    api.update = (nd) => { api.data = nd; paint(); };
    paint();
    return api;
  }

  // ───────── messages ─────────
  function createMessage(msg, hooks) {
    hooks = hooks || {};
    const root = document.createElement('div');
    root.dataset.id = msg.id || '';
    if (msg.role === 'user') {
      root.className = 'sa-msg sa-user';
      root.innerHTML = '<div class="sa-bubble">' + esc(msg.text || '').replace(/\n/g, '<br>') + '</div>' +
        ((msg.attachments || []).length ? '<div class="sa-attached">' + msg.attachments.map(chipHtml).join('') + '</div>' : '');
      return { root, role: 'user', data: msg };
    }
    root.className = 'sa-msg sa-assistant';
    root.innerHTML = '<div class="sa-avatar" aria-hidden="true">SA</div><div class="sa-mbody"><div class="sa-who">Story Architect</div>' +
      '<div class="sa-tools"></div><div class="sa-typing"><i></i><i></i><i></i></div><div class="sa-text sa-md"></div><div class="sa-drafts"></div><div class="sa-note" hidden></div>' +
      '<div class="sa-actions"><button class="sa-icon-btn" data-act="copy" title="Copy reply">' + icon('copy', 13) + '</button></div></div>';
    const q = (s) => root.querySelector(s);
    const textEl = q('.sa-text'), toolsEl = q('.sa-tools'), draftsEl = q('.sa-drafts'), noteEl = q('.sa-note');
    const api = { root, role: 'assistant', text: msg.text || '', tools: [], drafts: [], status: msg.status || 'complete' };
    const toolEls = {}, draftViews = {};
    let raf = 0;
    const paint = () => { raf = 0; textEl.innerHTML = SA.md(api.text); };
    api.setText = (t) => { api.text = t; api.setWaiting(false); if (!raf) raf = requestAnimationFrame(paint); };
    api.flush = () => { if (raf) cancelAnimationFrame(raf); paint(); };
    api.setWaiting = (b) => root.classList.toggle('sa-wait', !!b && !api.text && !api.tools.length);
    api.upsertTool = (t) => {
      if (/^mcp_+story_+/.test(t.name || '')) return; // Hermes' echo of a story tool; the app's own event carries the details
      api.setWaiting(false);
      const i = api.tools.findIndex((x) => x.id === t.id);
      if (i >= 0) { const m = Object.assign({}, api.tools[i]); for (const k in t) if (t[k] !== null && t[k] !== undefined) m[k] = t[k]; api.tools[i] = m; } else api.tools.push(t);
      const cur = api.tools.find((x) => x.id === t.id);
      if (toolEls[t.id]) paintTool(toolEls[t.id], cur); else { toolEls[t.id] = createTool(cur); toolsEl.appendChild(toolEls[t.id]); }
    };
    api.upsertDraft = (d) => {
      api.setWaiting(false);
      const i = api.drafts.findIndex((x) => x.id === d.id);
      if (i >= 0) api.drafts[i] = d; else api.drafts.push(d);
      if (draftViews[d.id]) draftViews[d.id].update(d); else { draftViews[d.id] = createDraft(d, hooks); draftsEl.appendChild(draftViews[d.id].root); }
    };
    api.setStreaming = (b) => { root.classList.toggle('sa-streaming', !!b); api.setWaiting(b); };
    api.setStatus = (status, message) => {
      api.status = status;
      const map = { cancelled: 'Stopped before finishing.', partial: 'This reply was interrupted.', error: message || 'Something went wrong.' };
      noteEl.hidden = !map[status];
      noteEl.className = 'sa-note' + (status === 'error' ? ' error' : '');
      noteEl.textContent = map[status] || '';
    };
    root.addEventListener('click', (e) => {
      const b = e.target.closest('[data-act=copy]');
      if (b) { try { navigator.clipboard.writeText(api.text); } catch (err) { /* ignore */ } }
    });
    (msg.tools || []).forEach((t, i) => api.upsertTool(typeof t === 'string' ? { id: 'legacy-' + i, name: t, status: 'finished' } : t));
    (msg.drafts || []).forEach(api.upsertDraft);
    paint();
    api.setStatus(api.status, msg.error);
    return api;
  }

  SA.icon = icon;
  SA.render = { createMessage, chipHtml, div };
})();
