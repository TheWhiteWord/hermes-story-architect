// Script editor — the overlay a person writes a scene's script in.
//
// One source of truth: the scene's Fountain `Content`. The page is a list of
// typed blocks (see model.js), one <textarea> each. Everything the server knows
// — what a cue resolves to, which warnings apply, what the heading composes to —
// comes from GET/POST/PUT /api/projects/{slug}/scenes/{id}/script[/check]
// (core/manual_edits.py); nothing is re-derived here.
//
// It lives inside #main, so the sidebar, the detail panel and the chat stay
// beside it: a character chip opens that character in the detail panel, and the
// chat can still be asked about what is on the page.
window.DASH = window.DASH || {};

(function () {
  'use strict';

  const M = DASH.SEModel;
  const esc = (s) => DASH.escapeHtml(String(s == null ? '' : s));
  const EDIT_RE = /^#\/p\/([^/?]+)\/scene\/([^/?]+)\/edit/;
  const slugFromHash = () => { const m = (location.hash || '').match(/^#\/p\/([^/?]+)/); return m ? decodeURIComponent(m[1]) : null; };
  const editHash = (slug, id) => '#/p/' + encodeURIComponent(slug) + '/scene/' + encodeURIComponent(id) + '/edit';
  const store = {
    get: (k) => { try { return localStorage.getItem(k); } catch (e) { return null; } },
    set: (k, v) => { try { localStorage.setItem(k, v); } catch (e) { /* storage unavailable */ } },
  };

  const S = {
    open: false, root: null, paper: null,
    slug: null, sceneId: null,
    data: null,      // last GET/PUT response (what is stored)
    view: null,      // data, overlaid with the latest /check of the draft
    blocks: [], H: null, extraCast: new Set(),
    base: '', focus: -1, focusText: null,
    showWarn: store.get('se.warn') !== '0',
    ac: null, pop: null, banner: null, readonly: false, saving: false,
    pushed: false, ownWriteUntil: 0, checkTimer: null, checkSeq: 0, toastTimer: null,
  };

  // ─── API ───────────────────────────────────────────────────────────────────
  async function api(path, opts) {
    const o = Object.assign({ headers: { 'Content-Type': 'application/json', 'X-Story-Architect': '1' } }, opts || {});
    const res = await fetch('/api/projects/' + encodeURIComponent(S.slug) + path, o);
    const j = await res.json().catch(() => ({}));
    if (!res.ok) {
      const e = new Error((j.error && j.error.message) || res.statusText);
      e.status = res.status; e.body = j.error || {};
      throw e;
    }
    return j;
  }
  const scenePath = (suffix) => '/scenes/' + encodeURIComponent(S.sceneId) + '/script' + (suffix || '');

  // ─── State helpers ─────────────────────────────────────────────────────────
  const cur = () => ({ blocks: S.blocks, H: S.H, extraCast: S.extraCast });
  const isDirty = () => S.open && S.data && M.snapshot(cur()) !== S.base;
  const sceneTitle = () => (S.data && S.data.scene.title) || S.sceneId;
  const registry = () => (S.data && S.data.registry) || { characters: [], locations: [] };
  const locById = (id) => registry().locations.find(l => l.id === id) || null;
  const charById = (id) => registry().characters.find(c => c.id === id) || null;
  const V = () => S.view || S.data;

  function headingFrom(res) {
    const h = res.heading || {};
    return {
      mode: h.mode || 'structured', int_ext: h.int_ext || 'INT.',
      location: h.location || '', location_text: h.location_text || '',
      time_of_day: h.time_of_day || '', text: h.text || '',
    };
  }

  function applyServer(res, opts) {
    S.data = res; S.view = res;
    S.blocks = res.blocks.map(b => ({ type: b.type, text: b.text }));
    if (!S.blocks.length) S.blocks = [{ type: 'action', text: '' }];
    S.H = headingFrom(res);
    S.extraCast = new Set(res.cast.filter(c => !c.in_script).map(c => c.id));
    S.base = M.snapshot(cur());
    S.readonly = !!res.locked;
    S.banner = res.locked ? { kind: 'locked', reason: res.locked_reason } : null;
    renderAll(opts && opts.focus);
  }

  // ─── DOM skeleton ──────────────────────────────────────────────────────────
  function ensureRoot() {
    if (S.root) return S.root;
    const main = document.getElementById('main');
    const root = document.createElement('div');
    root.id = 'se'; root.className = 'se'; root.hidden = true;
    root.innerHTML = `
      <header class="se-head">
        <button class="se-back" id="se-back" type="button"></button>
        <div class="se-title">
          <div class="se-title-main"><strong id="se-name"></strong><span class="se-muted" id="se-status"></span></div>
          <div class="se-muted se-sub" id="se-sub"></div>
        </div>
        <div class="se-head-actions">
          <span class="se-dirty" id="se-dirty" hidden><i></i>Unsaved changes</span>
          <button class="btn" id="se-discard" type="button">Discard</button>
          <button class="btn se-primary" id="se-save" type="button">Save script</button>
        </div>
      </header>
      <div class="se-banner" id="se-banner" hidden></div>
      <div class="se-body">
        <aside class="se-rail" id="se-rail"></aside>
        <section class="se-stage">
          <div class="se-scroll" id="se-scroll"><div class="se-paper-wrap"><div class="se-paper" id="se-paper"></div></div></div>
          <div class="se-drawer" id="se-drawer" hidden></div>
          <footer class="se-status" id="se-statusbar"></footer>
        </section>
      </div>
      <div class="se-toast" id="se-toast" hidden></div>`;
    main.appendChild(root);
    S.root = root; S.paper = root.querySelector('#se-paper');
    wire(root);
    return root;
  }
  const $ = (sel) => S.root.querySelector(sel);

  // ─── Rendering ─────────────────────────────────────────────────────────────
  function renderAll(focus) {
    renderHead(); renderBanner(); renderRail(); renderPaper(focus); renderStatus(); syncChrome();
  }

  function backLabel() {
    const v = DASH.currentView;
    return '← ' + ({ script: 'Script', scenes: 'Scenes' }[v] || 'Back');
  }

  function renderHead() {
    $('#se-back').textContent = backLabel();
    $('#se-name').textContent = sceneTitle();
    const st = S.data && S.data.scene.status;
    $('#se-status').textContent = st ? 'Status: ' + st : '';
  }

  function locationName() {
    const l = locById(S.H.location);
    return l ? l.name : (S.H.location_text || '');
  }
  const headingText = () => M.composeHeading(S.H, locationName());

  function syncChrome() {
    if (!S.root || !S.data) return;
    const dirty = isDirty();
    const blocker = M.saveBlocker(cur());
    $('#se-dirty').hidden = !dirty;
    const save = $('#se-save');
    save.disabled = S.saving || S.readonly || !dirty || !!blocker;
    save.title = S.readonly ? 'This scene is read-only' : (blocker || (dirty ? 'Save (Ctrl/⌘ S)' : 'Nothing to save'));
    save.textContent = S.saving ? 'Saving…' : 'Save script';
    $('#se-discard').disabled = !dirty || S.saving;
    $('#se-sub').textContent = 'Script · ' + (headingText() || 'no heading yet');
    renderStatus();
  }

  function rowHtml(b, i) {
    const cue = b.type === 'character' ? cueOf(i) : null;
    const unreg = cue && !cue.id && b.text.trim();
    return `<div class="se-row se-r-${b.type}${unreg ? ' se-unreg' : ''}" data-i="${i}">
      <span class="se-gutter">${M.GUTTER[b.type] || b.type}</span>
      <textarea class="se-ta se-t-${b.type}" data-i="${i}" rows="1" ${b.type === 'character' ? 'spellcheck="false" autocomplete="off"' : ''} ${S.readonly ? 'readonly' : ''}></textarea>
      ${unreg ? '<span class="se-unreg-mark" title="Not a registered character">!</span>' : ''}
    </div>`;
  }

  function headingRowHtml() {
    const H = S.H, dis = S.readonly ? 'disabled' : '';
    if (H.mode === 'custom') {
      return `<div class="se-row se-heading" data-heading>
        <span class="se-gutter">Heading</span>
        <div class="se-hline"><input class="se-hinput" id="se-hinput" spellcheck="false" ${S.readonly ? 'readonly' : ''}>
        <button class="se-pill" data-h="fields" type="button" ${dis} title="Build the heading from INT/EXT, location and time">Use fields</button></div></div>`;
    }
    const name = locationName();
    const registered = !!locById(H.location);
    return `<div class="se-row se-heading" data-heading>
      <span class="se-gutter">Heading</span>
      <div class="se-hline">
        <button class="se-pill" data-h="ie" type="button" ${dis}>${esc(H.int_ext)}</button>
        <button class="se-pill se-loc${!name ? ' se-warn' : ''}${name && !registered ? ' se-dashed' : ''}" data-h="loc" type="button" ${dis}
          title="${registered ? 'Registered location' : (name ? 'Not a registered location' : 'Choose a location')}">${name ? esc(name.toUpperCase()) : 'LOCATION'}</button>
        <span class="se-dash">-</span>
        <button class="se-pill${!H.time_of_day ? ' se-warn' : ''}" data-h="tod" type="button" ${dis}>${esc(H.time_of_day || 'TIME')}</button>
        <button class="se-icon" data-h="custom" type="button" ${dis} title="Edit the heading as text">✎</button>
      </div></div>`;
  }

  function renderPaper(focus) {
    const html = headingRowHtml() + S.blocks.map(rowHtml).join('') + '<div class="se-end" data-end title="Click to continue writing"></div>';
    S.paper.innerHTML = html;
    S.paper.querySelectorAll('textarea[data-i]').forEach(ta => {
      ta.value = S.blocks[+ta.dataset.i].text;
      autosize(ta);
    });
    const hi = S.paper.querySelector('#se-hinput');
    if (hi) hi.value = S.H.text;
    S.ac = null;
    if (focus) focusBlock(focus.i, focus.pos);
  }

  const autosize = (ta) => { ta.style.height = 'auto'; ta.style.height = ta.scrollHeight + 'px'; };

  function focusBlock(i, pos) {
    const ta = S.paper.querySelector('textarea[data-i="' + i + '"]');
    if (!ta) return;
    ta.focus({ preventScroll: true });
    const p = pos == null || pos === 'end' ? ta.value.length : (pos === 'start' ? 0 : pos);
    ta.setSelectionRange(p, p);
    ta.scrollIntoView({ block: 'nearest' });
  }
  function focusHeading() {
    const b = S.paper.querySelector('[data-h="loc"]') || S.paper.querySelector('#se-hinput');
    if (b) { b.focus(); b.scrollIntoView({ block: 'nearest' }); }
  }

  function cueOf(i) {
    const v = V();
    return (v && v.cues || []).find(c => c.block === i) || null;
  }

  // ── Rail: element list, cast, settings ──
  function roleColor(role) { return DASH.roleColor ? DASH.roleColor(role) : '#8a8a8a'; }

  // Who is in the scene: everyone the script names (as of the last check) plus
  // whoever was added by hand. The hand-added are read from local state, so a
  // chip appears the moment "+" is used, not when the next check returns.
  function castEntries() {
    const v = V(), known = (v && v.cast) || [];
    const speaking = known.filter(c => c.in_script);
    const ids = speaking.map(c => c.id).concat(Array.from(S.extraCast).filter(id => !speaking.some(c => c.id === id)));
    return ids.map(id => {
      const hit = known.find(c => c.id === id), reg = charById(id);
      if (!reg) return null;
      return { id, name: reg.name, story_role: reg.story_role, in_script: !!(hit && hit.in_script), cues: hit ? hit.cues : 0 };
    }).filter(Boolean);
  }

  function renderRail() {
    if (!S.data) return;
    const v = V(), active = activeElement(), ro = S.readonly ? 'disabled' : '';
    const els = M.ELEMENTS.map((e, n) => `
      <button class="se-el${active === e.type ? ' on' : ''}" data-el="${e.type}" type="button" ${ro}>
        <span>${e.label}</span><kbd>^${n + 1}</kbd></button>`).join('');

    const chips = castEntries().map(c => {
      const col = roleColor(c.story_role);
      return `<button class="se-chip${c.in_script ? '' : ' se-silent'}" data-char="${esc(c.id)}" type="button" style="--c:${col}"
        title="${c.in_script ? 'Speaks in ' + c.cues + (c.cues === 1 ? ' cue' : ' cues') : 'In the scene, no dialogue'}">${esc(c.name.toUpperCase())}</button>`;
    }).join('');
    const adhoc = (v.adhoc || []).map(a => `<button class="se-chip se-adhoc" data-adhoc="${esc(a.cue)}" type="button"
        title="Not a registered character — only exists in this script">${esc(a.cue)}</button>`).join('');
    const none = !chips && !adhoc ? '<div class="se-muted se-small">No one yet</div>' : '';

    const loc = locById(S.H.location);   // the heading's own state: immediate
    const typed = S.H.location_text && !locById(S.H.location);
    const locChip = loc
      ? `<button class="se-chip se-loc-chip" data-loc="${esc(loc.id)}" type="button" style="--c:#6bbfb0">${esc(loc.name.toUpperCase())}</button>
         ${loc.world ? `<button class="se-chip se-world-chip" data-world="${esc(loc.world.id)}" type="button" style="--c:#e0a86b">${esc(loc.world.name.toUpperCase())}</button>`
                     : '<span class="se-chip se-bad" title="This location belongs to no world">NO WORLD</span>'}`
      : (typed ? `<span class="se-chip se-adhoc" title="Not a registered location">${esc(S.H.location_text.toUpperCase())}</span>`
               : '<div class="se-muted se-small">No location</div>');

    S.root.querySelector('#se-rail').innerHTML = `
      <div class="se-rail-sec"><div class="se-label">Element</div><div class="se-els">${els}</div></div>
      <div class="se-rail-sec">
        <div class="se-label">Scene cast<span class="se-pm">
          <button type="button" data-cast="add" ${ro} title="Add a character to the scene">+</button>
          <button type="button" data-cast="remove" ${ro} title="Remove a character from the scene">−</button></span></div>
        <div class="se-chips">${chips}${adhoc}${none}</div>
      </div>
      <div class="se-rail-sec">
        <div class="se-label">Settings<span class="se-pm">
          <button type="button" data-set="add" ${ro} title="Set the location">+</button>
          <button type="button" data-set="remove" ${ro} title="Clear the location">−</button></span></div>
        <div class="se-chips">${locChip}</div>
      </div>
      <div class="se-rail-foot">
        <button class="btn se-open-scene" id="se-open-scene" type="button">Open scene</button>
        <div class="se-hints" id="se-hints"></div>
      </div>`;
    syncHints();
  }

  function activeElement() {
    if (S.focus === 'heading') return 'heading';
    return S.focus >= 0 && S.blocks[S.focus] ? S.blocks[S.focus].type : null;
  }
  function syncRailActive() {
    const a = activeElement();
    S.root.querySelectorAll('.se-el').forEach(b => b.classList.toggle('on', b.dataset.el === a));
    syncHints();
  }
  function syncHints() {
    const el = S.root.querySelector('#se-hints');
    if (!el) return;
    const b = S.focus >= 0 ? S.blocks[S.focus] : null;
    const tab = b ? M.TAB_TYPE[b.type] : null;
    el.innerHTML = (tab ? `<div>Tab → ${M.GUTTER[tab]}</div>` : '') +
      '<div>Enter → new block</div><div>⌘/Ctrl S saves · Esc closes</div>';
  }

  // ── Banner ──
  function renderBanner() {
    const el = $('#se-banner'), b = S.banner;
    if (!b) { el.hidden = true; el.innerHTML = ''; return; }
    el.hidden = false; el.className = 'se-banner se-banner-' + b.kind;
    if (b.kind === 'conflict') {
      el.innerHTML = `<span>This scene was changed (by Hermes, or elsewhere) since you opened it.</span>
        <button class="btn" data-banner="reload" type="button">Load latest — discard mine</button>
        <button class="btn" data-banner="overwrite" type="button">Keep mine — overwrite</button>`;
    } else if (b.kind === 'locked') {
      el.innerHTML = b.reason === 'status'
        ? '<span>This scene is locked, so it opens read-only. Unlock it to edit.</span>'
        : `<span>This script uses Fountain the editor can’t edit without losing text, so it opens read-only.</span>
           <button class="btn btn-hermes" data-hermes-send="Reformat the script of the scene '${esc(sceneTitle())}' so it uses only standard Fountain." type="button">Ask Hermes to tidy it</button>`;
    } else {
      el.innerHTML = `<span>${esc(b.text || '')}</span>`;
    }
  }

  // ── Status bar + warnings drawer ──
  function findingsOf() {
    const f = (V() && V().findings) || [];
    return { crit: f.filter(x => x.level === 'critical'), other: f.filter(x => x.level !== 'critical') };
  }
  function renderStatus() {
    if (!S.root || !S.data) return;
    const { crit, other } = findingsOf(), v = V(), st = v.stats || {};
    const fmt = crit.length
      ? `<button class="se-fmt se-fmt-bad" data-fmt type="button">● ${crit.length} critical${other.length ? ' · ○ ' + other.length : ''}</button>`
      : `<button class="se-fmt se-fmt-ok" data-fmt type="button">✓ Formatting check${other.length ? ' · ○ ' + other.length : ''}</button>`;
    const sp = st.speaking_parts || 0;
    $('#se-statusbar').innerHTML = `${fmt}
      <label class="se-check"><input type="checkbox" id="se-showwarn" ${S.showWarn ? 'checked' : ''}> Show warnings</label>
      <span class="se-stats">${st.lines || 0} lines · ${sp} speaking ${sp === 1 ? 'part' : 'parts'}</span>
      <span class="se-muted se-fountain">Fountain</span>`;
    const dr = $('#se-drawer');
    dr.hidden = !S.showWarn || (!crit.length && !other.length);
    if (!dr.hidden) {
      const item = (f, i) => `<div class="se-find se-find-${f.level === 'critical' ? 'c' : 'o'}">
        <span class="se-find-msg">${esc(f.message)}</span>
        <span class="se-find-act">${findingButtons(f, i)}</span></div>`;
      const all = (V().findings || []);
      dr.innerHTML =
        (crit.length ? `<div class="se-drawer-h">Critical</div>${crit.map(f => item(f, all.indexOf(f))).join('')}` : '') +
        (other.length ? `<div class="se-drawer-h">Others</div>${other.map(f => item(f, all.indexOf(f))).join('')}` : '');
    }
  }

  function askPrompt(f) {
    const t = sceneTitle();
    if (f.field === 'order') return `Decide where the scene '${t}' belongs in its sequence and set its order.`;
    if (f.field === 'plot_roles') return `Which plot does the scene '${t}' serve, and in what role? Set its plot_roles, or mark it transition or non-event.`;
    if (f.code === 'character_unregistered') {
      const m = /Character '([^']+)'/.exec(f.message);
      return `Create a character called ${m ? m[1] : 'this speaker'} for the scene '${t}'. They speak in it and are not registered yet.`;
    }
    if (f.code === 'location_no_world') return `Which world does the location of the scene '${t}' belong to? Set it.`;
    if (f.field) return `Fill the missing field '${f.field}' for the scene '${t}'.`;
    return null;
  }
  function findingButtons(f, i) {
    const out = [];
    const local = f.block != null || ['heading', 'location', 'time_of_day'].includes(f.field);
    if (local && !(f.field === 'location' && f.code === 'location_no_world')) {
      out.push(`<button class="se-link" data-go="${i}" type="button">Go to</button>`);
    }
    if (askPrompt(f)) out.push(`<button class="se-link" data-hermes-send="${esc(askPrompt(f))}" type="button">Ask Hermes</button>`);
    return out.join('');
  }

  // ─── Live check (debounced) ────────────────────────────────────────────────
  function payload(withHash) {
    const p = {
      blocks: S.blocks.map(b => ({ type: b.type, text: b.type === 'parenthetical' ? M.wrapParenthetical(b.text) : b.text })),
      heading: { mode: S.H.mode, int_ext: S.H.int_ext, location: S.H.location, location_text: S.H.location_text,
                 time_of_day: S.H.time_of_day, text: S.H.text },
      extra_cast: Array.from(S.extraCast),
    };
    if (withHash) p.base_hash = withHash;
    return p;
  }
  function scheduleCheck(ms) {
    clearTimeout(S.checkTimer);
    S.checkTimer = setTimeout(runCheck, ms == null ? 450 : ms);
  }
  async function runCheck() {
    if (!S.open || !S.data) return;
    const seq = ++S.checkSeq;
    try {
      const res = await api(scenePath('/check'), { method: 'POST', body: JSON.stringify(payload()) });
      if (seq !== S.checkSeq || !S.open) return;
      S.view = Object.assign({}, S.data, res);
      applyCues();
      renderRail(); renderStatus();
    } catch (e) { /* the page stays usable; the last findings stay on screen */ }
  }
  // Re-mark the cue rows in place — a re-render would drop the caret.
  function applyCues() {
    S.paper.querySelectorAll('.se-r-character').forEach(row => {
      const i = +row.dataset.i, cue = cueOf(i), unreg = cue && !cue.id && S.blocks[i] && S.blocks[i].text.trim();
      row.classList.toggle('se-unreg', !!unreg);
      let mark = row.querySelector('.se-unreg-mark');
      if (unreg && !mark) { mark = document.createElement('span'); mark.className = 'se-unreg-mark'; mark.textContent = '!'; mark.title = 'Not a registered character'; row.appendChild(mark); }
      if (!unreg && mark) mark.remove();
    });
  }
  function structural() {            // blocks were inserted/removed: cue indices are stale
    if (S.view) S.view = Object.assign({}, S.view, { cues: [] });
    scheduleCheck(120);
  }
  function onChange() { syncChrome(); scheduleCheck(); }

  // ─── Pop-up menus (heading controls, cast and location pickers) ───────────
  function closePop() {
    if (!S.pop) return;
    S.pop.el.remove(); S.pop = null;
    document.removeEventListener('mousedown', popOutside, true);
  }
  function popOutside(e) { if (S.pop && !S.pop.el.contains(e.target)) closePop(); }

  // items: [{label, sub, color, value, disabled}]; opts: {search, placeholder, free(q) -> item|null, onPick}
  function openPop(anchor, items, opts) {
    closePop();
    const el = document.createElement('div');
    el.className = 'se-pop';
    el.innerHTML = (opts.search ? `<input class="se-pop-q" placeholder="${esc(opts.placeholder || 'Search…')}" spellcheck="false">` : '') + '<div class="se-pop-list"></div>';
    S.root.appendChild(el);
    const r = anchor.getBoundingClientRect(), rr = S.root.getBoundingClientRect();
    el.style.left = Math.max(8, Math.min(r.left - rr.left, rr.width - 280)) + 'px';
    el.style.top = (r.bottom - rr.top + 4) + 'px';
    S.pop = { el, items, opts, sel: 0, shown: [] };
    const draw = () => {
      const q = (el.querySelector('.se-pop-q') || {}).value || '';
      const Q = q.trim().toLowerCase();
      let shown = items.filter(i => !Q || (i.label + ' ' + (i.sub || '')).toLowerCase().includes(Q));
      const free = opts.free && Q ? opts.free(q.trim()) : null;
      if (free) shown = shown.concat([free]);
      S.pop.shown = shown; S.pop.sel = Math.min(S.pop.sel, Math.max(0, shown.length - 1));
      el.querySelector('.se-pop-list').innerHTML = shown.length ? shown.map((it, n) =>
        `<button type="button" class="se-pop-item${n === S.pop.sel ? ' on' : ''}${it.disabled ? ' dis' : ''}" data-n="${n}" ${it.disabled ? 'aria-disabled="true"' : ''}
          ${it.color ? `style="--c:${it.color}"` : ''}><span>${esc(it.label)}</span>${it.sub ? `<small>${esc(it.sub)}</small>` : ''}</button>`).join('')
        : '<div class="se-muted se-small se-pop-empty">Nothing to show</div>';
    };
    S.pop.draw = draw; draw();
    el.addEventListener('mousedown', (e) => {
      const b = e.target.closest('.se-pop-item');
      if (e.target.closest('.se-pop-q')) return;
      e.preventDefault();
      if (b) choosePop(+b.dataset.n);
    });
    const q = el.querySelector('.se-pop-q');
    if (q) { q.addEventListener('input', () => { S.pop.sel = 0; draw(); }); q.focus(); }
    el.addEventListener('keydown', popKey);
    if (!q) { el.tabIndex = -1; el.focus(); }
    setTimeout(() => document.addEventListener('mousedown', popOutside, true), 0);
  }
  function choosePop(n) {
    const p = S.pop; if (!p) return;
    const it = p.shown[n];
    if (!it || it.disabled) return;
    const pick = p.opts.onPick; closePop();
    pick(it.value);
    restoreFocus();
  }
  function popKey(e) {
    const p = S.pop; if (!p) return;
    if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); closePop(); restoreFocus(); }
    else if (e.key === 'ArrowDown') { e.preventDefault(); p.sel = Math.min(p.shown.length - 1, p.sel + 1); p.draw(); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); p.sel = Math.max(0, p.sel - 1); p.draw(); }
    else if (e.key === 'Enter') { e.preventDefault(); choosePop(p.sel); }
  }
  function restoreFocus() { if (S.focus >= 0 && S.blocks[S.focus]) focusBlock(S.focus); }

  // ── the specific menus ──
  function pickLocation(anchor) {
    const items = registry().locations.map(l => ({
      label: l.name, sub: l.world ? l.world.name : 'no world', color: '#6bbfb0', value: { id: l.id }, disabled: false }));
    openPop(anchor, items, {
      search: true, placeholder: 'Find a location, or type a new one',
      free: (q) => ({ label: 'Use “' + q + '”', sub: 'not registered', value: { text: q } }),
      onPick: (v) => {
        if (v.id) { S.H.location = v.id; S.H.location_text = ''; } else { S.H.location = ''; S.H.location_text = v.text; }
        if (S.H.mode === 'custom') S.H.mode = 'structured';
        afterHeadingChange();
      },
    });
  }
  function afterHeadingChange() { renderAll(); onChange(); }

  function castMenu(kind, anchor) {
    const inCast = new Set(castEntries().map(c => c.id));
    if (kind === 'add') {
      const items = registry().characters.filter(c => !inCast.has(c.id)).map(c => ({
        label: c.name, sub: c.story_role, color: roleColor(c.story_role), value: c.id }));
      openPop(anchor, items, { search: true, placeholder: 'Add a registered character',
        onPick: (id) => { S.extraCast.add(id); renderRail(); onChange(); } });
    } else {
      const items = castEntries().map(c => ({
        label: c.name, color: roleColor(c.story_role), value: c.id,
        disabled: c.in_script, sub: c.in_script ? 'speaks in ' + c.cues + (c.cues === 1 ? ' cue' : ' cues') : 'no dialogue' }));
      openPop(anchor, items, { search: false,
        onPick: (id) => { S.extraCast.delete(id); renderRail(); onChange(); } });
    }
  }

  // ─── Editing: blocks ───────────────────────────────────────────────────────
  function setBlocks(blocks, focus) {
    S.blocks = blocks;
    S.focus = focus ? focus.i : S.focus;
    renderPaper(focus); renderRail(); structural(); syncChrome();
  }

  function applyElement(type) {
    if (S.readonly) return;
    if (type === 'heading') { S.focus = 'heading'; focusHeading(); syncRailActive(); return; }
    const i = typeof S.focus === 'number' ? S.focus : -1;
    if (i < 0 || !S.blocks[i]) {
      const r = M.insertAfter(S.blocks, S.blocks.length - 1, type);
      return setBlocks(M.convert(r.blocks, r.index, type), { i: r.index });
    }
    if (!S.blocks[i].text.trim()) {
      const out = M.convert(S.blocks, i, type);
      return setBlocks(out, { i, pos: type === 'parenthetical' ? 1 : 'end' });
    }
    const r = M.insertAfter(S.blocks, i, type);
    setBlocks(M.convert(r.blocks, r.index, type), { i: r.index, pos: type === 'parenthetical' ? 1 : 'end' });
  }

  function convertCurrent(i, type) {
    const out = M.convert(S.blocks, i, type);
    setBlocks(out, { i, pos: type === 'parenthetical' && out[i].text === '()' ? 1 : 'end' });
  }

  function onKey(e) {
    const ta = e.target.closest('textarea[data-i]');
    if (!ta || S.readonly) return;
    const i = +ta.dataset.i, b = S.blocks[i];
    if (!b) return;

    // The cue list owns the arrows and Escape while it is open. Enter accepts a
    // suggestion only when the person chose one (arrowed to it) or is part-way
    // through a name; it never rewrites a name that already matches something, and
    // Tab never accepts — it converts the block, as everywhere else.
    if (S.ac && S.ac.i === i) {
      if (e.key === 'ArrowDown') { e.preventDefault(); S.ac.touched = true; S.ac.sel = Math.min(S.ac.items.length - 1, S.ac.sel + 1); drawAc(); return; }
      if (e.key === 'ArrowUp') { e.preventDefault(); S.ac.touched = true; S.ac.sel = Math.max(0, S.ac.sel - 1); drawAc(); return; }
      if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); closeAc(); return; }
      if (e.key === 'Enter' && S.ac.items.length) {
        const typed = b.text.trim(), exact = S.ac.items.some(it => it.kind !== 'new' && it.insert === typed);   // “Use ‘X’” always equals what is typed
        if (S.ac.touched || (typed && !exact)) { e.preventDefault(); pickAc(S.ac.sel); return; }
      }
      if (e.key === 'Tab') closeAc();
    }
    // ^1..^7 (Ctrl, or Alt where the browser keeps Ctrl+digit for tabs)
    if ((e.ctrlKey || e.altKey) && /^[1-7]$/.test(e.key)) {
      e.preventDefault(); applyElement(M.ELEMENTS[+e.key - 1].type); return;
    }
    if (e.key === 'Tab') {
      e.preventDefault();
      if (e.shiftKey) return;
      convertCurrent(i, M.TAB_TYPE[b.type] || 'action'); return;
    }
    if (e.key === 'Enter') {
      if (e.shiftKey && !M.SINGLE_LINE.has(b.type)) return;       // a newline inside the block
      e.preventDefault();
      const a = M.onEnter(S.blocks, i, ta.selectionStart);
      if (a.kind === 'none') return;
      if (a.kind === 'convert') return convertCurrent(i, a.type);
      if (a.kind === 'split') { const r = M.splitAt(S.blocks, i, a.pos); return setBlocks(r.blocks, { i: r.index, pos: 'start' }); }
      if (b.type === 'parenthetical') S.blocks[i].text = M.wrapParenthetical(b.text);
      const r = M.insertAfter(S.blocks, i, a.type);
      const blocks = M.convert(r.blocks, r.index, a.type);
      if (a.type === 'parenthetical') blocks[r.index].text = '()';
      return setBlocks(blocks, { i: r.index, pos: 'end' });
    }
    if (e.key === 'Backspace' && !b.text && S.blocks.length > 1) {
      e.preventDefault();
      const out = M.removeAt(S.blocks, i);
      return setBlocks(out, { i: Math.max(0, i - 1), pos: 'end' });
    }
    if (e.key === 'ArrowUp' || e.key === 'ArrowDown') {
      const ed = M.caretEdges(ta.value, ta.selectionStart, ta.selectionEnd);
      if (e.key === 'ArrowUp' && ed.onFirstLine && i > 0) { e.preventDefault(); focusBlock(i - 1, 'end'); }
      else if (e.key === 'ArrowDown' && ed.onLastLine && i < S.blocks.length - 1) { e.preventDefault(); focusBlock(i + 1, 'start'); }
    }
  }

  function onInput(e) {
    const hi = e.target.closest('#se-hinput');
    if (hi) { S.H.text = hi.value; return onChange(); }
    const ta = e.target.closest('textarea[data-i]');
    if (!ta) return;
    const i = +ta.dataset.i, b = S.blocks[i];
    const v = M.normalizeText(b.type, ta.value);
    if (v !== ta.value) { const p = ta.selectionStart; ta.value = v; ta.setSelectionRange(p, p); }
    b.text = v; autosize(ta);
    if (b.type === 'character') openAc(i); else closeAc();
    onChange();
  }

  function onBlur(e) {
    const ta = e.target.closest && e.target.closest('textarea[data-i]');
    if (!ta) return;
    const i = +ta.dataset.i, b = S.blocks[i];
    if (b && b.type === 'parenthetical') {
      const w = M.wrapParenthetical(b.text);
      if (w !== b.text) { b.text = w; ta.value = w; autosize(ta); onChange(); }
    }
    setTimeout(() => { if (S.ac && S.ac.i === i && document.activeElement !== ta) closeAc(); }, 0);
  }

  function onFocus(e) {
    if (e.target.closest && e.target.closest('textarea[data-i]')) {
      S.focus = +e.target.dataset.i; syncRailActive();
      // Only an empty cue opens the list on focus: moving into a finished one
      // must not put suggestions in the way of Enter.
      const b = S.blocks[S.focus];
      if (b && b.type === 'character' && !b.text.trim()) openAc(S.focus); else closeAc();
    } else if (e.target.closest && e.target.closest('[data-heading]')) {
      S.focus = 'heading'; syncRailActive();
    }
  }

  async function onPaste(e) {
    const ta = e.target.closest('textarea[data-i]');
    if (!ta || S.readonly) return;
    const text = (e.clipboardData || window.clipboardData).getData('text');
    if (!/\n/.test(text.trim())) return;                       // one line: let the browser paste it
    e.preventDefault();
    const i = +ta.dataset.i;
    try {
      const res = await api('/script/parse', { method: 'POST', body: JSON.stringify({ text }) });
      let incoming = res.blocks;
      if (res.heading) incoming = [{ type: 'action', text: res.heading }].concat(incoming);
      if (!incoming.length) return;
      const empty = !S.blocks[i].text.trim();
      const out = M.insertAfter(S.blocks, i, 'action').blocks.slice();
      out.splice(i + 1, 1, ...incoming.map(b => ({ type: b.type, text: b.text })));
      if (empty) out.splice(i, 1);
      const last = (empty ? i : i + 1) + incoming.length - 1;
      setBlocks(out, { i: last, pos: 'end' });
    } catch (err) { toast('Could not read the pasted text: ' + err.message, 'bad'); }
  }

  // ─── Character-cue autocomplete ────────────────────────────────────────────
  function openAc(i) {
    const b = S.blocks[i]; if (!b || b.type !== 'character' || S.readonly) return;
    const v = V(), castIds = castEntries().map(c => c.id);
    const items = M.acItems(b.text, registry().characters, castIds, v.adhoc || [], S.data.adhoc_elsewhere || []);
    S.ac = { i, items, sel: Math.min(S.ac && S.ac.i === i ? S.ac.sel : 0, Math.max(0, items.length - 1)) };
    drawAc();
  }
  function closeAc() {
    S.ac = null;
    S.paper && S.paper.querySelectorAll('.se-ac').forEach(n => n.remove());
  }
  function drawAc() {
    S.paper.querySelectorAll('.se-ac').forEach(n => n.remove());
    const a = S.ac; if (!a || !a.items.length) return;
    const row = S.paper.querySelector('.se-row[data-i="' + a.i + '"]'); if (!row) return;
    const el = document.createElement('div');
    el.className = 'se-ac';
    el.innerHTML = a.items.map((it, n) => `<button type="button" class="se-ac-item${n === a.sel ? ' on' : ''}" data-n="${n}"
      ${it.kind === 'registered' ? `style="--c:${roleColor(it.role)}"` : ''}><span>${esc(it.label)}</span><small>${esc(it.tag)}</small></button>`).join('');
    el.addEventListener('mousedown', (e) => {
      const b = e.target.closest('.se-ac-item'); e.preventDefault();
      if (b) pickAc(+b.dataset.n);
    });
    row.appendChild(el);
  }
  function pickAc(n) {
    const a = S.ac; if (!a) return;
    const it = a.items[n]; if (!it) return;
    const i = a.i;
    S.blocks[i].text = it.insert;
    closeAc();
    const next = S.blocks[i + 1];
    if (next && (next.type === 'dialogue' || next.type === 'parenthetical')) {
      renderPaper({ i: i + 1, pos: 'end' }); S.focus = i + 1; onChange(); renderRail();
    } else {
      const r = M.insertAfter(S.blocks, i, 'dialogue');
      setBlocks(r.blocks, { i: r.index, pos: 'end' });
    }
  }

  // ─── Save / discard / conflict ─────────────────────────────────────────────
  function toast(text, kind) {
    const t = $('#se-toast'); if (!t) return;
    t.textContent = text; t.className = 'se-toast se-toast-' + (kind || 'ok'); t.hidden = false;
    clearTimeout(S.toastTimer);
    S.toastTimer = setTimeout(() => { t.hidden = true; }, kind === 'bad' ? 6000 : 2200);
  }

  async function save(hashOverride) {
    if (S.saving || S.readonly || !S.data) return;
    const blocker = M.saveBlocker(cur());
    if (blocker) return toast(blocker, 'warn');
    if (!isDirty() && !hashOverride) return;
    S.blocks.forEach(b => { if (b.type === 'parenthetical') b.text = M.wrapParenthetical(b.text); });
    S.saving = true; syncChrome();
    const keep = typeof S.focus === 'number' ? { i: S.focus, pos: 'end' } : null;
    try {
      const res = await api(scenePath(), { method: 'PUT', body: JSON.stringify(payload(hashOverride || S.data.hash)) });
      S.ownWriteUntil = Date.now() + 6000; DASH._ownWriteUntil = S.ownWriteUntil;
      applyServer(res, keep);
      toast('Script saved', 'ok');
      if (DASH.reloadData) DASH.reloadData();
    } catch (e) {
      if (e.status === 409) { S.banner = { kind: 'conflict', hash: e.body.current_hash }; renderBanner(); }
      else toast(e.message, 'bad');
    } finally { S.saving = false; syncChrome(); }
  }

  function discard() {
    if (!isDirty()) return;
    if (!confirm('Discard your unsaved changes?')) return;
    applyServer(S.data);
  }

  async function reloadLatest() {
    const res = await api(scenePath());
    applyServer(res);
  }

  // Hermes (or anything else) wrote while the editor is open.
  async function onExternalUpdate() {
    if (!S.open || !S.data) return;
    try {
      const res = await api(scenePath());
      if (res.hash === S.data.hash) return;      // our own save, or nothing that matters
      if (!isDirty()) { applyServer(res); toast('Updated — this scene changed elsewhere', 'warn'); }
      else { S.banner = { kind: 'conflict', hash: res.hash }; renderBanner(); }
    } catch (e) { /* the next event retries */ }
  }

  // ─── Open / close / routing ────────────────────────────────────────────────
  async function openFromRoute(id) {
    ensureRoot();
    S.slug = slugFromHash(); S.sceneId = id; S.open = true;
    S.root.hidden = false; S.focus = -1; S.banner = null; S.data = null;
    S.paper.innerHTML = '<div class="se-loading">Opening script…</div>';
    $('#se-name').textContent = ''; $('#se-sub').textContent = '';
    try {
      const res = await api(scenePath());
      applyServer(res);
      const want = S.focusText && S.focusText.trim().slice(0, 40).toLowerCase();
      S.focusText = null;
      const i = want ? S.blocks.findIndex(b => b.text.trim().toLowerCase().startsWith(want) || want.startsWith(b.text.trim().toLowerCase().slice(0, 40)) && b.text.trim()) : -1;
      if (i >= 0) focusBlock(i, 'end');
      else if (!res.locked && S.blocks.length === 1 && !S.blocks[0].text) focusBlock(0);
    } catch (e) {
      toast(e.status === 404 ? 'That scene no longer exists.' : e.message, 'bad');
      doClose();
    }
  }

  function doClose() {
    clearTimeout(S.checkTimer); closePop(); closeAc();
    S.open = false; if (S.root) S.root.hidden = true;
    S.data = null; S.view = null;
    if (EDIT_RE.test(location.hash || '')) {
      if (S.pushed) { S.pushed = false; history.back(); }
      else location.hash = '#/p/' + encodeURIComponent(S.slug || slugFromHash() || '');
    }
  }
  function requestClose() {
    if (isDirty() && !confirm('Discard your unsaved changes?')) return;
    doClose();
  }

  DASH.openScriptEditor = function (sceneId, opts) {
    const slug = slugFromHash(); if (!slug) return;
    S.focusText = opts && opts.focusText || null;
    S.pushed = true;
    const target = editHash(slug, sceneId);
    if (location.hash === target) DASH.routeEditor(); else location.hash = target;
  };

  // Called after the project loads and on every hash change.
  DASH.routeEditor = function () {
    const m = (location.hash || '').match(EDIT_RE);
    if (m) {
      const id = decodeURIComponent(m[2]);
      if (S.open && S.sceneId === id) return;
      if (S.open && isDirty() && !confirm('Discard your unsaved changes?')) { location.hash = editHash(S.slug, S.sceneId); return; }
      if (!(DASH.story && (DASH.story.scenes || []).length)) return;
      openFromRoute(id);
    } else if (S.open) {
      if (isDirty() && !confirm('Discard your unsaved changes?')) { location.hash = editHash(S.slug, S.sceneId); return; }
      doClose();
    }
  };
  window.addEventListener('hashchange', () => DASH.routeEditor());
  window.addEventListener('beforeunload', (e) => { if (isDirty()) { e.preventDefault(); e.returnValue = ''; } });

  // ─── Event wiring ──────────────────────────────────────────────────────────
  function wire(root) {
    const paper = root.querySelector('#se-paper');
    paper.addEventListener('keydown', onKey);
    paper.addEventListener('input', onInput);
    paper.addEventListener('focusin', onFocus);
    paper.addEventListener('focusout', onBlur);
    paper.addEventListener('paste', onPaste);
    paper.addEventListener('click', (e) => {
      const h = e.target.closest('[data-h]');
      if (h && !S.readonly) {
        const k = h.dataset.h;
        if (k === 'ie') openPop(h, M.INT_EXT.map(v => ({ label: v, value: v })), { onPick: (v) => { S.H.int_ext = v; afterHeadingChange(); } });
        else if (k === 'tod') openPop(h, [{ label: '(no time)', value: '' }].concat(M.TIMES.map(v => ({ label: v, value: v }))), { onPick: (v) => { S.H.time_of_day = v; afterHeadingChange(); } });
        else if (k === 'loc') pickLocation(h);
        else if (k === 'custom') { S.H.text = headingText(); S.H.mode = 'custom'; afterHeadingChange(); setTimeout(() => { const i = $('#se-hinput'); if (i) i.focus(); }, 0); }
        else if (k === 'fields') { S.H.mode = 'structured'; afterHeadingChange(); }
        return;
      }
      if (e.target.closest('[data-end]') && !S.readonly) {
        const last = S.blocks.length - 1;
        if (S.blocks[last] && !S.blocks[last].text.trim()) return focusBlock(last);
        const r = M.insertAfter(S.blocks, last, 'action'); setBlocks(r.blocks, { i: r.index });
      }
    });
    // the rail keeps focus where the person was typing
    root.querySelector('#se-rail').addEventListener('mousedown', (e) => { if (e.target.closest('button')) e.preventDefault(); });
    root.querySelector('#se-rail').addEventListener('click', (e) => {
      const el = e.target.closest('[data-el]');
      if (el) return applyElement(el.dataset.el);
      const c = e.target.closest('[data-cast]');
      if (c) return castMenu(c.dataset.cast, c);
      const st = e.target.closest('[data-set]');
      if (st) {
        if (st.dataset.set === 'add') return pickLocation(st);
        S.H.location = ''; S.H.location_text = ''; return afterHeadingChange();
      }
      const ch = e.target.closest('[data-char]');
      if (ch) { const c2 = (DASH.story.characters || []).find(x => String(x.id) === ch.dataset.char); if (c2) DASH.showCharacterPanel(c2); return; }
      const lc = e.target.closest('[data-loc]'); if (lc) return DASH.showLocationPanel(lc.dataset.loc);
      const wc = e.target.closest('[data-world]'); if (wc) return DASH.showWorldPanel(wc.dataset.world);
      const ad = e.target.closest('[data-adhoc]');
      if (ad) {
        const name = ad.dataset.adhoc;
        return openPop(ad, [{ label: 'Ask Hermes to create “' + name + '”', value: 'create' }], {
          onPick: () => DASH.askAgent(`Create a character called ${name} for the scene '${sceneTitle()}'. They speak in it and are not registered yet.`) });
      }
      if (e.target.closest('#se-open-scene')) DASH.showScenePanel(S.sceneId);
    });
    root.querySelector('#se-back').addEventListener('click', requestClose);
    root.querySelector('#se-save').addEventListener('click', () => save());
    root.querySelector('#se-discard').addEventListener('click', discard);
    root.querySelector('#se-banner').addEventListener('click', async (e) => {
      const b = e.target.closest('[data-banner]'); if (!b) return;
      if (b.dataset.banner === 'reload') { try { await reloadLatest(); } catch (err) { toast(err.message, 'bad'); } }
      else if (b.dataset.banner === 'overwrite') { const h = S.banner && S.banner.hash; S.banner = null; renderBanner(); save(h); }
    });
    root.querySelector('#se-statusbar').addEventListener('click', (e) => {
      if (e.target.closest('[data-fmt]')) { S.showWarn = !S.showWarn; store.set('se.warn', S.showWarn ? '1' : '0'); renderStatus(); }
    });
    root.querySelector('#se-statusbar').addEventListener('change', (e) => {
      if (e.target.id === 'se-showwarn') { S.showWarn = e.target.checked; store.set('se.warn', S.showWarn ? '1' : '0'); renderStatus(); }
    });
    root.querySelector('#se-drawer').addEventListener('click', (e) => {
      const g = e.target.closest('[data-go]'); if (!g) return;
      const f = (V().findings || [])[+g.dataset.go]; if (!f) return;
      if (f.block != null) focusBlock(f.block, 'end');
      else if (f.field === 'heading') focusHeading();
      else if (f.field === 'location') { const a = S.paper.querySelector('[data-h="loc"]'); if (a) pickLocation(a); }
      else if (f.field === 'time_of_day') { const a = S.paper.querySelector('[data-h="tod"]'); if (a) a.click(); }
    });
    document.addEventListener('keydown', (e) => {
      if (!S.open) return;
      if ((e.ctrlKey || e.metaKey) && (e.key === 's' || e.key === 'S')) { e.preventDefault(); save(); }
      else if (e.key === 'Escape' && !S.pop && !S.ac) { e.preventDefault(); requestClose(); }
      else if ((e.ctrlKey || e.altKey) && /^[1-7]$/.test(e.key) && !e.target.closest('textarea')) { e.preventDefault(); applyElement(M.ELEMENTS[+e.key - 1].type); }
    });
  }

  // ─── Integration with the rest of the dashboard ────────────────────────────

  // Re-read the project after a save, without a page reload (a reload would
  // throw away anything else open). The stale parts are the script view, the
  // scene list, the graph — all rebuilt by initStory from the same payload boot uses.
  DASH.reloadData = async function () {
    const slug = slugFromHash(); if (!slug) return;
    try {
      const res = await fetch('/api/projects/' + encodeURIComponent(slug) + '/dashboard');
      if (!res.ok) return;
      const data = await res.json();
      window.__STORY_DATA__ = data.story_data;
      window.__SECTIONS__ = data.sections;
      window.__SCREENPLAY_STATS__ = data.screenplay_stats;
      window.__STRUCTURAL_STATS__ = data.structural_stats;
      if (DASH.network) { try { DASH.network.destroy(); } catch (e) { /* already gone */ } DASH.network = null; }
      DASH.initStory(data.story_data);
    } catch (e) { console.error('[script-editor] reload failed', e); }
  };

  // The global "Project updated — Refresh" banner reloads the page, which would
  // discard an open editor. While the editor is open it handles updates itself,
  // and a person's own save never raises the banner.
  const origIndicator = DASH.showUpdateIndicator;
  DASH.showUpdateIndicator = function (slug) {
    if (S.open) { onExternalUpdate(); return; }
    if (Date.now() < (DASH._ownWriteUntil || 0)) return;
    if (origIndicator) origIndicator.call(DASH, slug);
  };

  // The scene panel's "Open script" button (delegated: ids are never put in an inline handler).
  document.addEventListener('click', (e) => {
    const b = e.target.closest && e.target.closest('[data-open-script]');
    if (b) DASH.openScriptEditor(b.getAttribute('data-open-script'));
  });

  // The scene panel's Script card: stats and format status, fetched lazily.
  DASH.refreshScriptCard = async function (sceneId) {
    const card = document.querySelector('.se-card[data-scene="' + CSS.escape(String(sceneId)) + '"]');
    if (!card) return;
    const meta = card.querySelector('.se-card-meta');
    try {
      S.slug = S.slug || slugFromHash();
      const res = await fetch('/api/projects/' + encodeURIComponent(slugFromHash()) + '/scenes/' + encodeURIComponent(sceneId) + '/script');
      if (!res.ok) throw new Error('unavailable');
      const d = await res.json();
      const crit = (d.findings || []).filter(f => f.level === 'critical').length;
      const sp = d.stats.speaking_parts;
      meta.innerHTML = `<span>${d.stats.lines} lines · ${sp} speaking ${sp === 1 ? 'part' : 'parts'}</span>` +
        (crit ? `<span class="se-card-fmt se-card-bad">${crit} critical</span>` : '<span class="se-card-fmt">Format OK</span>');
    } catch (e) { meta.innerHTML = ''; }
  };
})();
