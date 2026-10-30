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
  const KIND = { create: 'CREATE', edit: 'EDIT', delete: 'DELETE', reorder: 'REORDER' };
  const STATUS = { open: 'Awaiting approval', committed: 'Approved', discarded: 'Rejected', failed: 'Failed' };
  function fmtVal(v) {
    if (v == null || v === '') return '<em>not set</em>';
    if (Array.isArray(v)) return esc(v.map((x) => (typeof x === 'object' ? JSON.stringify(x) : x)).join(', '));
    if (typeof v === 'object') return esc(JSON.stringify(v));
    return esc(v);
  }
  function fieldHtml(f) {
    const long = (v) => typeof v === 'string' && (v.length > 90 || v.indexOf('\n') >= 0);
    if (long(f.before) || long(f.after)) {
      return '<div class="sa-field"><details><summary><span class="sa-fname">' + esc(f.field) + '</span> (show change)</summary><div class="sa-diff"><div class="b">' + fmtVal(f.before) + '</div><div>' + fmtVal(f.after) + '</div></div></details></div>';
    }
    return '<div class="sa-field"><span class="sa-fname">' + esc(f.field) + '</span>' +
      (f.before == null || f.before === '' ? '' : '<del>' + fmtVal(f.before) + '</del> → ') + '<ins>' + fmtVal(f.after) + '</ins></div>';
  }
  function changeHtml(c) {
    const kind = c.kind || 'edit';
    const target = c.label || [c.entity_type, c.entity_id].filter(Boolean).join(' / ');
    return '<div class="sa-change"><div class="sa-change-top"><span class="sa-kind k-' + esc(kind) + '">' + (KIND[kind] || esc(kind).toUpperCase()) + '</span>' +
      '<span class="sa-target">' + esc(target) + '</span></div>' +
      (c.summary ? '<div class="sa-csum">' + esc(c.summary) + '</div>' : '') +
      (kind === 'reorder' && c.count ? '<div class="sa-csum">' + c.count + ' items</div>' : '') +
      (c.fields || []).map(fieldHtml).join('') + '</div>';
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
        '<div class="sa-draft-changes">' + ((x.changes || []).map(changeHtml).join('') || '<div class="sa-change sa-csum">No changes listed.</div>') + '</div>' +
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
      api.setWaiting(false);
      const i = api.tools.findIndex((x) => x.id === t.id);
      if (i >= 0) api.tools[i] = Object.assign({}, api.tools[i], t); else api.tools.push(t);
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
    (msg.tools || []).forEach(api.upsertTool);
    (msg.drafts || []).forEach(api.upsertDraft);
    paint();
    api.setStatus(api.status, msg.error);
    return api;
  }

  SA.icon = icon;
  SA.render = { createMessage, chipHtml, div };
})();
