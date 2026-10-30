/* Story Architect chat: API layer (real backend + ?mock=1 stand-in).
   Everything the UI needs from the server goes through window.SAChat.api. */
(function () {
  const SA = (window.SAChat = window.SAChat || {});
  const HDR = { 'X-Story-Architect': '1' };
  SA.MOCK = /[?&]mock=1\b/.test(location.search);

  async function json(method, url, body) {
    const res = await fetch(url, {
      method,
      headers: body === undefined ? HDR : Object.assign({ 'Content-Type': 'application/json' }, HDR),
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    let data = null;
    try { data = await res.json(); } catch (e) { /* empty body */ }
    if (!res.ok) {
      const err = new Error((data && data.error && data.error.message) || 'HTTP ' + res.status);
      err.status = res.status;
      err.code = data && data.error && data.error.code;
      throw err;
    }
    return data;
  }

  // Parse a text/event-stream body into normalized events.
  // Also accepts the legacy Phase 3 shapes (tool_started / tool_finished).
  async function* sse(res) {
    const reader = res.body.getReader();
    const dec = new TextDecoder();
    const open = {}; // legacy tool name -> id
    let n = 0, buf = '';
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      buf += dec.decode(value, { stream: true });
      let i;
      while ((i = buf.indexOf('\n\n')) >= 0) {
        const block = buf.slice(0, i);
        buf = buf.slice(i + 2);
        let ev = '', data = '';
        for (const line of block.split('\n')) {
          if (line.startsWith('event:')) ev = line.slice(6).trim();
          else if (line.startsWith('data:')) data += line.slice(5).trim();
        }
        let p = {};
        if (data) { try { p = JSON.parse(data); } catch (e) { continue; } }
        let type = p.type || ev.toLowerCase();
        if (type === 'textdelta') type = 'text';
        if (type === 'tool_started') { const id = 'L' + (++n); open[p.name] = id; yield { type: 'tool', id, name: p.name, status: 'started' }; continue; }
        if (type === 'tool_finished') { yield { type: 'tool', id: open[p.name] || 'L' + (++n), name: p.name, status: 'finished' }; continue; }
        if (type === 'toolstarted' || type === 'toolfinished') continue;
        yield Object.assign({}, p, { type });
      }
    }
  }

  async function* stream(url, body, signal) {
    let res;
    try {
      res = await fetch(url, { method: 'POST', signal, headers: Object.assign({ 'Content-Type': 'application/json' }, HDR), body: JSON.stringify(body || {}) });
    } catch (e) {
      if (e.name === 'AbortError') throw e;
      yield { type: 'error', message: 'Could not reach the app server.', retryable: true };
      return;
    }
    if (!res.ok) {
      let m = 'HTTP ' + res.status, code;
      try { const d = await res.json(); m = (d.error && d.error.message) || m; code = d.error && d.error.code; } catch (e) { /* keep */ }
      yield { type: 'error', message: m, code, retryable: res.status >= 500 };
      return;
    }
    yield* sse(res);
  }

  const P = (slug) => '/api/projects/' + encodeURIComponent(slug);
  const real = {
    agentState: () => json('GET', '/api/agent/state'),
    agentSettings: () => json('GET', '/api/agent/settings'),
    saveSettings: (patch) => json('PATCH', '/api/agent/settings', patch),
    agentStart: () => json('POST', '/api/agent/start', {}),
    agentStop: () => json('POST', '/api/agent/stop', {}),
    projects: () => json('GET', '/api/projects'),
    conversations: (slug) => json('GET', P(slug) + '/conversations'),
    createConversation: (slug) => json('POST', P(slug) + '/conversations', {}),
    getConversation: (slug, id) => json('GET', P(slug) + '/conversations/' + encodeURIComponent(id)),
    deleteConversation: (slug, id) => json('DELETE', P(slug) + '/conversations/' + encodeURIComponent(id)),
    send: (slug, id, body, signal) => stream(P(slug) + '/conversations/' + encodeURIComponent(id) + '/messages', body, signal),
    retry: (slug, id, signal) => stream(P(slug) + '/conversations/' + encodeURIComponent(id) + '/retry', {}, signal),
    cancel: (slug, id) => json('POST', P(slug) + '/conversations/' + encodeURIComponent(id) + '/cancel', {}),
    approveDraft: (slug, draftId, conversationId) => json('POST', P(slug) + '/drafts/' + encodeURIComponent(draftId) + '/approve', { conversation_id: conversationId }),
    rejectDraft: (slug, draftId, conversationId) => json('POST', P(slug) + '/drafts/' + encodeURIComponent(draftId) + '/reject', { conversation_id: conversationId }),
  };

  // ───────────────────────── mock backend (?mock=1) ─────────────────────────
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  const iso = (minAgo) => new Date(Date.now() - minAgo * 60000).toISOString();

  const mock = (function () {
    let state = 'ready', autostart = false, model = 'nous/hermes-4-70b', seq = 0;
    const convs = {};
    const drafts = {};
    function add(title, minAgo, messages) {
      const id = 'c' + ++seq;
      convs[id] = { id, title, created_at: iso(minAgo), updated_at: iso(minAgo), messages: messages || [] };
      return convs[id];
    }
    function draftSnap(id) {
      return {
        id, status: 'open', summary: 'Tighten the Act 2 midpoint and add a mentor scene', created_at: iso(0),
        changes: [
          { kind: 'edit', entity_type: 'scene', entity_id: 'central-room-night', summary: 'Sharpen the stakes of the argument',
            fields: [{ field: 'scene_objective', before: 'Decide whether to wake the children', after: 'Force Voss to choose between the mission and the children' },
                     { field: 'turning_point', before: null, after: 'Marcus reveals the reactor is failing' }] },
          { kind: 'create', entity_type: 'scene', entity_id: 'mentor-hallway-night', label: 'Mentor Hallway - Night', summary: 'New quiet scene where the Outsider advises Kael' },
          { kind: 'reorder', entity_type: 'scene', count: 6, summary: 'Move the hallway scene before the Core confrontation' },
        ],
        warnings: ['Scene "mentor-hallway-night" has no characters assigned yet.'],
      };
    }
    add('Act two pacing', 90, [
      { id: 'm1', role: 'user', text: 'Is the midpoint strong enough?', status: 'complete', created_at: iso(91) },
      { id: 'm2', role: 'assistant', status: 'complete', created_at: iso(90),
        tools: [{ id: 't1', name: 'retrieve', status: 'finished', args: { type: 'scene', id: 'central-room-night' }, result_preview: '{"success": true, "scene": "Central Room - Night"}', duration_ms: 240 }],
        text: 'The midpoint lands, but the **stakes are implied rather than shown**.\n\n- Voss argues, but nothing is lost if she loses\n- Marcus never tests her answer\n\nWant me to draft a stronger version?' },
    ]);
    add('Character voice: Kael', 60 * 26, []);
    add('Untitled chat', 60 * 24 * 4, []);

    async function* reply(conv, text, signal) {
      const msg = { id: 'm' + Date.now(), role: 'assistant', status: 'complete', created_at: iso(0), text: '', tools: [], drafts: [] };
      const stop = () => signal && signal.aborted;
      const end = () => { conv.messages.push(msg); conv.updated_at = iso(0); };
      try {
        await wait(500); if (stop()) throw new DOMException('aborted', 'AbortError');
        const t = { id: 'tool' + Date.now(), name: 'retrieve', args: { type: 'project', slug: 'demo' } };
        yield Object.assign({ type: 'tool', status: 'started' }, t);
        await wait(700);
        const fin = Object.assign({ status: 'finished', result_preview: '{"success": true, "scenes": 6, "characters": 6}', duration_ms: 690 }, t);
        msg.tools.push(fin); yield Object.assign({ type: 'tool' }, fin);
        const wantsDraft = /draft|change|rename|add|rewrite|fix/i.test(text);
        const body = wantsDraft
          ? 'Here is a proposal. I staged it as a draft so you can **approve or reject** it:\n\n1. Sharpen the midpoint argument\n2. Add a short mentor scene\n3. Reorder so the hallway scene comes first\n\nNothing changes until you approve.'
          : 'This project has **6 scenes** and **6 characters** across 3 acts.\n\n> The strongest thread is *The Resistance*; the Scientists\' arc is still thin.\n\nTry asking for a `draft` and I will stage some changes.';
        for (const w of body.split(/(\s+)/)) {
          if (stop()) throw new DOMException('aborted', 'AbortError');
          msg.text += w; yield { type: 'text', text: w }; await wait(18);
        }
        if (wantsDraft) {
          const id = 'd-' + Date.now(); drafts[id] = draftSnap(id); msg.drafts.push(drafts[id]);
          yield { type: 'draft', draft: drafts[id] };
        }
        yield { type: 'done', message_id: msg.id };
      } catch (e) {
        if (e.name === 'AbortError') msg.status = 'cancelled'; else throw e;
      } finally { end(); }
    }

    return {
      agentState: async () => { await wait(80); return { state, detail: '' }; },
      agentSettings: async () => { await wait(80); return { state, detail: '', profile: 'story-architect', port: 8643, autostart, can_stop: true,
        model: { current: model, options: ['nous/hermes-4-70b', 'nous/hermes-4-405b', 'meituan/longcat-2.5-preview:free'] } }; },
      saveSettings: async (p) => { if ('autostart' in p) autostart = !!p.autostart; if (p.model) model = p.model; return mock.agentSettings(); },
      agentStart: async () => { state = 'starting'; await wait(1400); state = 'ready'; return { state, message: 'Agent ready.' }; },
      agentStop: async () => { await wait(500); state = 'gateway_stopped'; return { state, message: 'Agent stopped.' }; },
      projects: async () => ({ projects: [{ slug: 'demo', name: 'Save the Children' }] }),
      conversations: async () => ({ conversations: Object.values(convs).sort((a, b) => b.updated_at.localeCompare(a.updated_at))
        .map((c) => ({ id: c.id, title: c.title, updated_at: c.updated_at })) }),
      createConversation: async () => ({ id: add('', 0).id }),
      getConversation: async (s, id) => JSON.parse(JSON.stringify(convs[id])),
      deleteConversation: async (s, id) => { delete convs[id]; return { deleted: true }; },
      send: (s, id, body, signal) => { const c = convs[id]; c.messages.push({ id: 'u' + Date.now(), role: 'user', text: body.text, status: 'complete', created_at: iso(0), attachments: (body.context || {}).attachments });
        if (!c.title) c.title = body.text.slice(0, 48); return reply(c, body.text, signal); },
      retry: (s, id, signal) => { const c = convs[id]; const last = c.messages.filter((m) => m.role === 'user').pop(); while (c.messages.length && c.messages[c.messages.length - 1].role !== 'user') c.messages.pop();
        return reply(c, last ? last.text : '', signal); },
      cancel: async () => ({ cancelled: true }),
      approveDraft: async (s, id) => { await wait(500); drafts[id].status = 'committed'; return { status: 'committed', draft: drafts[id] }; },
      rejectDraft: async (s, id) => { await wait(250); drafts[id].status = 'discarded'; return { status: 'discarded', draft: drafts[id] }; },
    };
  })();

  SA.api = SA.MOCK ? mock : real;
})();
