/* Story Architect chat: controller. Builds the right rail/panel, owns state, wires API <-> render.
   Drop-in: creates its own DOM inside #app (after the other panels) once a project is loaded. */
(function () {
  const SA = (window.SAChat = window.SAChat || {});
  const api = () => SA.api;
  const esc = SA.esc, icon = SA.icon;
  const LS = { open: 'sa.chat.open', conv: (slug) => 'sa.chat.conv.' + slug };
  const WRITE_TOOLS = ['draft', 'import', 'admin', 'memory', 'backup'];
  const STATE = {
    ready:          { cls: 'ok',   label: 'Agent ready' },
    starting:       { cls: 'warn', label: 'Starting agent…' },
    unknown:        { cls: 'warn', label: 'Checking agent…' },
    gateway_stopped:{ cls: 'bad',  label: 'Agent stopped (click to start)' },
    api_unreachable:{ cls: 'bad',  label: 'Agent not responding (click to start)' },
    not_configured: { cls: 'bad',  label: 'Agent not set up' },
  };

  const S = { slug: null, name: '', open: false, view: 'chat', agent: 'unknown', convId: null, msgs: [], streaming: false, abort: null,
              attach: [], stick: true, current: null };
  let R = {}; // dom refs
  const $ = (sel, root) => (root || R.root).querySelector(sel);
  const slugFromHash = () => { const m = (location.hash || '').match(/^#\/p\/([^/?]+)/); return m ? decodeURIComponent(m[1]) : null; };
  const store = { get: (k) => { try { return localStorage.getItem(k); } catch (e) { return null; } }, set: (k, v) => { try { v == null ? localStorage.removeItem(k) : localStorage.setItem(k, v); } catch (e) { /* ignore */ } } };

  function relTime(iso) {
    const t = Date.parse(iso); if (!t) return '';
    const m = Math.round((Date.now() - t) / 60000);
    if (m < 1) return 'just now'; if (m < 60) return m + ' min ago';
    const h = Math.round(m / 60); if (h < 24) return h + ' h ago';
    const d = Math.round(h / 24); return d === 1 ? 'yesterday' : d + ' days ago';
  }

  // ───────────────────────── DOM ─────────────────────────
  function build() {
    const aside = document.createElement('aside');
    aside.id = 'sa-chat';
    aside.setAttribute('aria-label', 'Chat');
    aside.innerHTML =
      '<div class="sa-head">' +
        '<button class="sa-rail-btn" id="sa-toggle" title="Chat" aria-expanded="false">' + icon('chat', 18) + '<span class="sa-badge" hidden></span><span class="sa-dot warn"></span></button>' +
        '<div class="sa-head-main"><button class="sa-icon-btn sa-back" title="Back to chat" hidden>' + icon('back', 16) + '</button>' +
          '<div class="sa-title"><span class="sa-title-text">Chat</span><span class="sa-sub"></span></div></div>' +
        '<button class="sa-agent" title="">' + icon('agent', 17) + '<span class="sa-dot warn"></span></button>' +
      '</div>' +
      '<div class="sa-body">' +
        '<section class="sa-view" data-view="chat">' +
          '<div class="sa-scroll"><div class="sa-messages"></div>' +
            '<div class="sa-float"><button class="sa-pillbtn sa-retry" hidden>' + icon('retry', 12) + 'Retry</button></div>' +
            '<button class="sa-pillbtn sa-jump" hidden>' + icon('down', 12) + 'Latest</button></div>' +
          '<div class="sa-notice" hidden><span></span><button class="sa-btn" data-act="start">Start agent</button></div>' +
          '<div class="sa-composer"><div class="sa-chips"></div>' +
            '<textarea class="sa-input" rows="1" placeholder="Message Story Architect…" aria-label="Message"></textarea>' +
            '<div class="sa-bar"><div class="sa-bar-l">' +
              '<button class="sa-icon-btn" data-act="attach" title="Attach what\'s open">' + icon('plus', 16) + '</button>' +
              '<button class="sa-icon-btn" data-act="new" title="New chat">' + icon('newchat', 16) + '</button>' +
              '<button class="sa-icon-btn" data-act="history" title="Recent chats">' + icon('history', 16) + '</button>' +
              '<button class="sa-icon-btn" data-act="settings" title="Settings">' + icon('settings', 16) + '</button>' +
            '</div><button class="sa-send" title="Send" aria-label="Send">' + icon('send', 15) + '</button></div></div>' +
        '</section>' +
        '<section class="sa-view" data-view="history" hidden><div class="sa-pane"></div></section>' +
        '<section class="sa-view" data-view="settings" hidden><div class="sa-pane"></div></section>' +
      '</div>';
    return aside;
  }

  function refs(root) {
    R = { root, toggle: $('#sa-toggle', root), badge: $('.sa-badge', root), agentBtn: $('.sa-agent', root), title: $('.sa-title-text', root), sub: $('.sa-sub', root),
      back: $('.sa-back', root), msgs: $('.sa-messages', root), retry: $('.sa-retry', root), jump: $('.sa-jump', root), notice: $('.sa-notice', root),
      chips: $('.sa-chips', root), input: $('.sa-input', root), send: $('.sa-send', root), composer: $('.sa-composer', root), views: {} };
    root.querySelectorAll('.sa-view').forEach((v) => { R.views[v.dataset.view] = v; });
  }

  // ───────────────────────── panel + views ─────────────────────────
  function setOpen(open) {
    S.open = open;
    R.root.classList.toggle('open', open);
    document.body.classList.toggle('sa-chat-open', open);
    R.toggle.setAttribute('aria-expanded', String(open));
    R.toggle.title = open ? 'Collapse chat' : 'Open chat';
    store.set(LS.open, open ? '1' : '0');
    if (open) { R.badge.hidden = true; if (!S.loaded) init(); setTimeout(() => S.view === 'chat' && R.input.focus(), 220); }
    window.dispatchEvent(new Event('resize')); // let graphs/canvases re-fit after the push
  }

  function setView(v) {
    S.view = v;
    Object.keys(R.views).forEach((k) => { R.views[k].hidden = k !== v; });
    R.back.hidden = v === 'chat';
    R.title.textContent = v === 'history' ? 'Recent chats' : v === 'settings' ? 'Settings' : 'Chat';
    R.sub.textContent = v === 'chat' ? (S.name || S.slug || '') : (S.name || S.slug || '');
    if (v === 'history') renderHistory();
    if (v === 'settings') renderSettings();
    if (v === 'chat') R.input.focus();
  }

  // ───────────────────────── agent status ─────────────────────────
  function setAgent(state, detail) {
    S.agent = STATE[state] ? state : 'unknown';
    const st = STATE[S.agent];
    R.root.querySelectorAll('.sa-dot').forEach((d) => { d.className = 'sa-dot ' + st.cls; });
    R.agentBtn.title = st.label + (detail ? ' — ' + detail : '');
    R.toggle.dataset.state = S.agent;
    const down = S.agent !== 'ready' && S.agent !== 'unknown' && S.agent !== 'starting';
    R.notice.hidden = !(down && S.view === 'chat');
    if (down) {
      $('span', R.notice).textContent = S.agent === 'not_configured' ? 'The agent isn\'t set up yet.' : 'The agent isn\'t running.';
      R.notice.querySelector('button').textContent = S.agent === 'not_configured' ? 'How to set up' : 'Start agent';
      R.notice.classList.add('bad');
    }
    updateSend();
  }
  async function pollAgent() {
    try { const r = await api().agentState(); if (S.agent !== 'starting' || r.state === 'ready') setAgent(r.state, r.detail); }
    catch (e) { if (S.agent !== 'starting') setAgent('api_unreachable', 'app server unreachable'); }
  }
  async function toggleAgent() {
    if (S.agent === 'not_configured') { setView('settings'); return; }
    if (S.agent === 'starting') return;
    const stopping = S.agent === 'ready';
    if (stopping && !confirm('Stop the agent? Chats won\'t get replies until it is started again.')) return;
    if (!stopping) setAgent('starting');
    try { const r = stopping ? await api().agentStop() : await api().agentStart(); setAgent(r.state || (stopping ? 'gateway_stopped' : 'ready'), r.message); if (S.view === 'settings') renderSettings(); }
    catch (e) { setAgent('api_unreachable', e.message); flashNotice(e.message); }
    pollAgent();
  }
  function flashNotice(msg) { R.notice.hidden = false; $('span', R.notice).textContent = msg; R.notice.classList.add('bad'); }

  // ───────────────────────── conversations ─────────────────────────
  async function init() {
    S.loaded = true;
    pollAgent();
    try {
      const p = await api().projects(); const hit = (p.projects || []).find((x) => x.slug === S.slug);
      if (hit && hit.name) { S.name = hit.name; R.sub.textContent = S.name; }
    } catch (e) { /* name is cosmetic */ }
    try {
      const list = (await api().conversations(S.slug)).conversations || [];
      const want = store.get(LS.conv(S.slug));
      const pick = list.find((c) => c.id === want) || list[0];
      if (pick) await openConversation(pick.id); else showEmpty();
    } catch (e) { showEmpty(); }
  }

  function showEmpty() {
    S.convId = null; S.msgs = []; R.msgs.innerHTML = '';
    const d = document.createElement('div'); d.className = 'sa-empty';
    d.innerHTML = icon('chat', 30) + '<b>' + esc(S.name || S.slug || 'This project') + '</b>Ask about your story, or have the agent propose changes. Use <b style="display:inline;font-weight:500">+</b> to share what you have open.';
    R.msgs.appendChild(d); updateRetry();
  }

  async function openConversation(id) {
    const c = await api().getConversation(S.slug, id);
    S.convId = c.id || id; S.msgs = [];
    store.set(LS.conv(S.slug), S.convId);
    R.msgs.innerHTML = '';
    const messages = (c.messages || []).filter((m) => !m.hidden);
    if (!messages.length) showEmpty(); else messages.forEach((m) => addMessage(m));
    scrollEnd(true); updateRetry();
  }

  async function ensureConversation() {
    if (S.convId) return S.convId;
    const r = await api().createConversation(S.slug);
    S.convId = r.id; store.set(LS.conv(S.slug), S.convId); return S.convId;
  }

  function newChat() {
    if (S.streaming) return;
    store.set(LS.conv(S.slug), null);
    showEmpty(); setView('chat'); R.input.focus();
  }

  const hooks = {
    approve: async (d) => { const r = await api().approveDraft(S.slug, d.id, S.convId); return r.draft || { status: r.status }; },
    reject: async (d) => { const r = await api().rejectDraft(S.slug, d.id, S.convId); return r.draft || { status: r.status }; },
    fix: (d) => send('The draft "' + (d.summary || d.id) + '" failed to apply (' + (d.error || 'unknown error') + '). Please fix it and re-stage.'),
  };

  function addMessage(m) {
    const empty = R.msgs.querySelector('.sa-empty'); if (empty) empty.remove();
    const v = SA.render.createMessage(m, hooks);
    R.msgs.appendChild(v.root); S.msgs.push(v); return v;
  }

  // ───────────────────────── scrolling ─────────────────────────
  const nearEnd = () => R.msgs.scrollHeight - R.msgs.scrollTop - R.msgs.clientHeight < 60;
  function scrollEnd(force) { if (force || S.stick) R.msgs.scrollTop = R.msgs.scrollHeight; R.jump.hidden = S.stick || !S.streaming; }

  // ───────────────────────── sending ─────────────────────────
  function updateSend() {
    const busy = S.streaming;
    R.send.classList.toggle('stop', busy);
    R.send.innerHTML = icon(busy ? 'stop' : 'send', 15);
    R.send.title = busy ? 'Stop' : 'Send';
    R.send.setAttribute('aria-label', R.send.title);
    R.send.disabled = !busy && !R.input.value.trim();
  }
  function updateRetry() {
    const last = S.msgs[S.msgs.length - 1];
    R.retry.hidden = S.streaming || !last || last.role !== 'assistant';
  }

  async function runStream(makeGen) {
    S.streaming = true; S.stick = true; updateSend(); updateRetry();
    const view = addMessage({ role: 'assistant', text: '', status: 'complete' });
    view.setStreaming(true); S.current = view;
    const ac = new AbortController(); S.abort = ac;
    let finished = false;
    try {
      for await (const ev of makeGen(ac.signal)) {
        if (ev.type === 'text') view.setText(view.text + (ev.text || ''));
        else if (ev.type === 'tool') view.upsertTool(ev);
        else if (ev.type === 'draft' && ev.draft) { view.upsertDraft(ev.draft); if (!S.open) R.badge.hidden = false; }
        else if (ev.type === 'error') { view.setStatus('error', ev.message); finished = true; if (ev.code === 'agent_not_configured' || ev.code === 'agent_unavailable') pollAgent(); }
        else if (ev.type === 'cancelled') { view.setStatus('cancelled'); finished = true; }
        else if (ev.type === 'done') { finished = true; }
        scrollEnd();
      }
      if (!finished && ac.signal.aborted) view.setStatus('cancelled');
      else if (!finished && !view.text && !view.tools.length) view.setStatus('error', 'No reply was received.');
    } catch (e) {
      if (e.name === 'AbortError') view.setStatus('cancelled'); else view.setStatus('error', e.message || 'The connection was lost.');
    } finally {
      view.flush(); view.setStreaming(false); view.setWaiting(false);
      S.streaming = false; S.abort = null; S.current = null;
      if (!S.open) R.badge.hidden = false;
      updateSend(); updateRetry(); scrollEnd();
    }
  }

  async function send(text) {
    text = (text == null ? R.input.value : text).trim();
    if (!text || S.streaming) return;
    if (S.agent !== 'ready' && S.agent !== 'unknown') { setAgent(S.agent); flashNotice('The agent isn\'t running. Start it, then send again.'); return; }
    let id;
    try { id = await ensureConversation(); } catch (e) { flashNotice(e.message); return; }
    const attachments = S.attach.slice();
    addMessage({ role: 'user', text, attachments });
    R.input.value = ''; autosize(); S.attach = []; renderChips(); closePop();
    await runStream((signal) => api().send(S.slug, id, { text, context: { project: S.slug, attachments } }, signal));
  }

  async function stop() {
    if (S.abort) S.abort.abort();
    try { await api().cancel(S.slug, S.convId); } catch (e) { /* the abort already stopped the UI side */ }
  }

  async function retry() {
    if (S.streaming || !S.convId) return;
    const last = S.msgs[S.msgs.length - 1];
    if (!last || last.role !== 'assistant') return;
    const risky = last.drafts.length || last.tools.some((t) => WRITE_TOOLS.indexOf(t.name) >= 0);
    if (risky && !confirm('This reply used tools that can change your project. Retrying runs it again and may repeat those changes. Retry anyway?')) return;
    last.root.remove(); S.msgs.pop();
    await runStream((signal) => api().retry(S.slug, S.convId, signal));
  }

  // ───────────────────────── context chips ─────────────────────────
  function collectContext() {
    const items = [];
    const nav = document.querySelector('.nav-btn.active[data-view]');
    if (nav) { const l = (nav.querySelector('.nav-label') || nav).textContent.trim(); items.push({ kind: 'view', id: nav.dataset.view, label: l + ' view' }); }
    const dp = document.getElementById('detail-panel');
    if (dp && dp.classList.contains('open')) {
      const type = (document.getElementById('panel-type') || {}).textContent || '', name = (document.getElementById('panel-name') || {}).textContent || '';
      const pc = (window.DASH && DASH.panelContext) || {};
      if (name.trim() && name.trim() !== '—') items.push({ kind: 'entity', id: pc.id || '', type: pc.type || type.trim().toLowerCase(), label: (type.trim() ? type.trim() + ': ' : '') + name.trim() });
    }
    const sp = document.getElementById('stats-panel');
    if (sp && sp.classList.contains('open')) {
      const t = sp.querySelector('.stats-tab.active'); const g = t ? t.textContent.trim() : 'Overview';
      items.push({ kind: 'stats', id: (t && t.dataset.group) || g.toLowerCase(), label: 'Statistics: ' + g });
    }
    return items;
  }
  const keyOf = (a) => a.kind + '|' + (a.id || '') + '|' + a.label;
  function renderChips() {
    R.chips.innerHTML = '';
    S.attach.forEach((a) => {
      const c = document.createElement('span'); c.className = 'sa-chip';
      c.innerHTML = '<span>' + esc(a.label) + '</span><button title="Remove" aria-label="Remove">' + icon('x', 10) + '</button>';
      c.querySelector('button').onclick = () => { S.attach = S.attach.filter((x) => keyOf(x) !== keyOf(a)); renderChips(); };
      R.chips.appendChild(c);
    });
  }
  function closePop() { const p = R.composer.querySelector('.sa-pop'); if (p) p.remove(); }
  function togglePop() {
    if (R.composer.querySelector('.sa-pop')) { closePop(); return; }
    const items = collectContext(), pop = document.createElement('div');
    pop.className = 'sa-pop';
    pop.innerHTML = '<div class="sa-pop-h">Share with the next message</div>' + (items.length ? '' : '<div class="sa-pop-empty">Nothing else is open.</div>');
    items.forEach((it) => {
      const on = S.attach.some((a) => keyOf(a) === keyOf(it));
      const b = document.createElement('button');
      b.innerHTML = '<span class="sa-tick">' + (on ? icon('check', 13) : '') + '</span><span>' + esc(it.label) + '</span>';
      b.onclick = () => { S.attach = on ? S.attach.filter((a) => keyOf(a) !== keyOf(it)) : S.attach.concat(it); renderChips(); closePop(); togglePop(); };
      pop.appendChild(b);
    });
    R.composer.appendChild(pop);
  }

  // ───────────────────────── history + settings ─────────────────────────
  async function renderHistory() {
    const pane = $('.sa-pane', R.views.history);
    pane.innerHTML = '<button class="sa-btn sa-newrow" data-act="new">' + icon('newchat', 13) + 'New chat</button><div class="sa-list"><div class="sa-help">Loading…</div></div>';
    pane.querySelector('[data-act=new]').onclick = newChat;
    let list = [];
    try { list = (await api().conversations(S.slug)).conversations || []; } catch (e) { pane.querySelector('.sa-list').innerHTML = '<div class="sa-help">Couldn\'t load chats: ' + esc(e.message) + '</div>'; return; }
    const box = pane.querySelector('.sa-list');
    if (!list.length) { box.innerHTML = '<div class="sa-help">No chats yet for this project.</div>'; return; }
    box.innerHTML = '';
    list.forEach((c) => {
      const row = document.createElement('div'); row.className = 'sa-conv' + (c.id === S.convId ? ' cur' : '');
      row.innerHTML = '<div class="sa-conv-main"><div class="sa-conv-title">' + esc(c.title || 'Untitled chat') + '</div><div class="sa-conv-time">' + relTime(c.updated_at || c.created_at) + '</div></div>' +
        '<button class="sa-icon-btn" title="Delete chat" aria-label="Delete chat">' + icon('trash', 14) + '</button>';
      row.onclick = async (e) => {
        if (e.target.closest('button')) return;
        if (S.streaming) return;
        try { await openConversation(c.id); setView('chat'); } catch (err) { flashNotice(err.message); }
      };
      row.querySelector('button').onclick = async () => {
        if (!confirm('Delete this chat?')) return;
        try { await api().deleteConversation(S.slug, c.id); if (c.id === S.convId) showEmpty(); renderHistory(); } catch (err) { flashNotice(err.message); }
      };
      box.appendChild(row);
    });
  }

  async function renderSettings() {
    const pane = $('.sa-pane', R.views.settings);
    pane.innerHTML = '<div class="sa-help">Loading…</div>';
    let s;
    try { s = await api().agentSettings(); } catch (e) { pane.innerHTML = '<div class="sa-help">Couldn\'t load settings: ' + esc(e.message) + '</div>'; return; }
    setAgent(s.state, s.detail);
    const st = STATE[S.agent] || STATE.unknown, canStop = s.can_stop !== false;
    const model = s.model || {};
    pane.innerHTML =
      '<div class="sa-sect">Agent</div>' +
      '<div class="sa-row"><span class="k">Status</span><span class="v sa-status"><span class="sa-dot ' + st.cls + '"></span>' + esc(st.label.replace(/ \(.*\)/, '')) + '</span></div>' +
      '<div class="sa-row"><span class="k">Gateway</span><span class="v"><button class="sa-btn" data-act="toggle"' + (S.agent === 'ready' && !canStop ? ' disabled title="This gateway is shared with other profiles; stop it from Hermes."' : '') + '>' +
        (S.agent === 'ready' ? 'Stop' : S.agent === 'starting' ? 'Starting…' : 'Start') + '</button></span></div>' +
      '<div class="sa-row"><label for="sa-auto">Start automatically with the app</label><button id="sa-auto" class="sa-switch" role="switch" aria-checked="' + !!s.autostart + '"></button></div>' +
      '<div class="sa-row"><span class="k">Profile</span><span class="v">' + esc(s.profile || '—') + '</span></div>' +
      '<div class="sa-row"><span class="k">Port</span><span class="v">' + esc(s.port || '—') + '</span></div>' +
      '<div class="sa-sect">Model</div>' +
      (model.options && model.options.length
        ? '<div class="sa-row"><label for="sa-model">Model</label><select id="sa-model" class="sa-select">' + model.options.map((o) => '<option' + (o === model.current ? ' selected' : '') + '>' + esc(o) + '</option>').join('') + '</select></div>'
        : '<div class="sa-row"><span class="k">Model</span><span class="v">' + esc(model.current || 'not available') + '</span></div>') +
      '<div class="sa-help" id="sa-msg"></div>' +
      (S.agent === 'not_configured' ? '<div class="sa-help">Set it up once from a terminal:<br><code>story-architect hermes setup</code></div>' : '');
    const msg = (t) => { const m = pane.querySelector('#sa-msg'); if (m) m.textContent = t; };
    pane.querySelector('[data-act=toggle]').onclick = async () => { await toggleAgent(); };
    pane.querySelector('#sa-auto').onclick = async (e) => {
      const next = e.currentTarget.getAttribute('aria-checked') !== 'true';
      e.currentTarget.setAttribute('aria-checked', String(next));
      try { await api().saveSettings({ autostart: next }); msg('Saved.'); } catch (err) { e.currentTarget.setAttribute('aria-checked', String(!next)); msg(err.message); }
    };
    const sel = pane.querySelector('#sa-model');
    if (sel) sel.onchange = async () => { msg('Saving…'); try { await api().saveSettings({ model: sel.value }); msg('Saved. New replies use ' + sel.value + '.'); } catch (err) { msg(err.message); } };
  }

  // ───────────────────────── input ─────────────────────────
  function autosize() { R.input.style.height = 'auto'; R.input.style.height = Math.min(R.input.scrollHeight, 160) + 'px'; }

  function wire() {
    R.toggle.onclick = () => setOpen(!S.open);
    R.agentBtn.onclick = toggleAgent;
    R.back.onclick = () => setView('chat');
    R.send.onclick = () => (S.streaming ? stop() : send());
    R.retry.onclick = retry;
    R.jump.onclick = () => { S.stick = true; scrollEnd(true); };
    R.notice.querySelector('button').onclick = toggleAgent;
    R.msgs.addEventListener('scroll', () => { S.stick = nearEnd(); R.jump.hidden = S.stick || !S.streaming; });
    R.input.addEventListener('input', () => { autosize(); updateSend(); });
    R.input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) { e.preventDefault(); if (!S.streaming) send(); }
      else if (e.key === 'Escape' && S.streaming) stop();
    });
    R.root.querySelector('.sa-bar-l').addEventListener('click', (e) => {
      const b = e.target.closest('[data-act]'); if (!b) return;
      ({ attach: togglePop, new: newChat, history: () => setView('history'), settings: () => setView('settings') })[b.dataset.act]();
    });
    document.addEventListener('click', (e) => { if (!e.target.closest('.sa-pop') && !e.target.closest('[data-act=attach]')) closePop(); });
    setInterval(() => { if (!document.hidden) pollAgent(); }, 8000);
  }

  // ───────────────────────── mount ─────────────────────────
  function mount() {
    if (document.getElementById('sa-chat')) return;
    const app = document.getElementById('app'), slug = slugFromHash();
    if (!app || !slug) return;
    S.slug = slug; S.loaded = false;
    const root = build(); app.appendChild(root); refs(root); wire();
    setAgent('unknown'); setView('chat'); updateSend(); updateRetry(); pollAgent();
    setOpen(store.get(LS.open) === '1');
  }

  window.addEventListener('hashchange', () => { const el = document.getElementById('sa-chat'); if (el && slugFromHash() !== S.slug) location.reload(); });

  window.DASH = window.DASH || {};
  const origInit = DASH.initStory;
  if (typeof origInit === 'function') DASH.initStory = function () { const r = origInit.apply(this, arguments); try { mount(); } catch (e) { console.error('[chat]', e); } return r; };
  else document.addEventListener('DOMContentLoaded', () => { try { mount(); } catch (e) { console.error('[chat]', e); } });

  // dashboard buttons ("Analyse this scene", …) send straight into the chat
  DASH.askAgent = function (text) {
    if (!R.root) { try { navigator.clipboard.writeText(text); } catch (e) { /* ignore */ } return; }
    if (!S.open) setOpen(true);
    setView('chat');
    send(text);
  };
  SA.state = S;
})();
