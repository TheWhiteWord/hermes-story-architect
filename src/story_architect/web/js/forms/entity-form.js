// Entity form — create, edit and delete an entity by hand.
//
// One renderer for every type. The server describes each type as a form spec
// (`/form-spec`, built from ENTITY_SCHEMAS), so a field added to the schema
// appears here with no change to this file. Nothing here knows what a
// "character" is; it knows kinds: text, textarea, select, ref, list, computed.
//
//   DASH.openEntityForm({ type, id?, values? })   id => edit, no id => create
//
// State lives in S, not in the DOM: typing never re-renders (focus is safe);
// a tab / step change does. Messages come from the server's dry run
// (`/check`, debounced) and are shown only for fields the person has touched
// (or after they press save), so a fresh form isn't born full of red.
window.DASH = window.DASH || {};
(function (D) {
  'use strict';

  const h = (s) => String(s == null ? '' : s).replace(/[&<>"']/g,
    (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const clone = (v) => JSON.parse(JSON.stringify(v));
  const eq = (a, b) => JSON.stringify(a) === JSON.stringify(b);
  const slugFromHash = () => { const m = (location.hash || '').match(/^#\/p\/([^/?]+)/); return m ? decodeURIComponent(m[1]) : null; };
  const LISTS = { character: 'characters', location: 'locations', world: 'worlds', plot: 'plots', value: 'values' };
  const PANEL_TYPES = ['character', 'location', 'world'];

  let specs = null, rootEl = null, toastTimer = 0, menuEl = null;
  const S = { open: false };

  // ─── API ─────────────────────────────────────────────────────────────────
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

  function toast(msg, kind) {
    let t = document.querySelector('.ef-toast');
    if (!t) { t = document.createElement('div'); document.body.appendChild(t); }
    t.className = 'ef-toast' + (kind === 'bad' ? ' bad' : '');
    t.textContent = msg;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => t.remove(), kind === 'bad' ? 6000 : 3200);
  }

  // ─── Values: normalise, diff, dirty ──────────────────────────────────────
  const editable = () => S.spec.fields.filter((f) => f.kind !== 'computed' && f.kind !== 'unsupported' && f.kind !== 'reflist');
  const nameKey = () => S.spec.name_key;

  function norm(values) {
    const out = {};
    editable().forEach((f) => {
      let v = values[f.key];
      if (f.kind === 'list') v = (v || []).map((x) => String(x).trim()).filter(Boolean);
      else if (typeof v === 'string') v = v.trim();
      out[f.key] = v;
    });
    return out;
  }
  const trimSections = (sec) => { const o = {}; Object.keys(sec).forEach((k) => { o[k] = String(sec[k] || '').trim(); }); return o; };
  const changedFields = () => { const a = norm(S.orig.values), b = norm(S.values); return editable().filter((f) => !eq(a[f.key], b[f.key])); };
  const changedSections = () => S.spec.sections.filter((n) => String(S.orig.sections[n] || '').trim() !== String(S.sections[n] || '').trim());
  const isDirty = () => !eq(norm(S.base.values), norm(S.values)) || !eq(trimSections(S.base.sections), trimSections(S.sections));
  const payload = () => ({ id: S.id, base_version: S.orig && S.orig.version, values: norm(S.values), sections: trimSections(S.sections) });

  function blankState(spec, prefill) {
    const values = {};
    spec.fields.forEach((f) => {
      if (f.kind === 'computed' || f.kind === 'unsupported') return;
      values[f.key] = f.kind === 'list' || f.kind === 'reflist' ? [] : f.kind === 'toggle' ? false : '';
    });
    Object.assign(values, prefill || {});
    const sections = {}; spec.sections.forEach((n) => { sections[n] = ''; });
    return { values, sections, computed: {}, version: null };
  }

  const refName = (type, id) => {
    const e = ((D.story || {})[LISTS[type]] || []).find((x) => x.id === id);
    return e ? (e.name || e.title || id) : id;
  };

  // ─── Open / close ────────────────────────────────────────────────────────
  D.openEntityForm = async function (opts) {
    if (S.open || !opts || !opts.type) return;
    const slug = slugFromHash(); if (!slug) return;
    S.slug = slug;
    try { if (!specs) specs = (await api('/form-spec')).types; }
    catch (e) { toast('Couldn’t open the form: ' + e.message, 'bad'); return; }
    const spec = specs[opts.type]; if (!spec) return;
    let orig;
    if (opts.id) {
      try { orig = await api('/entities/' + opts.type + '/' + encodeURIComponent(opts.id) + '/form'); }
      catch (e) { toast(e.message, 'bad'); return; }
    } else orig = blankState(spec, opts.values);
    Object.assign(S, {
      open: true, mode: opts.id ? 'edit' : 'create', type: opts.type, id: opts.id || null, spec,
      orig, base: clone(orig), values: clone(orig.values), sections: clone(orig.sections),
      tab: 'fields', step: 'form', discard: false, busy: false, conflict: false, preview: null,
      errors: {}, warnings: {}, newId: null, touched: new Set(), submitted: false, seq: 0, timer: 0,
      trigger: document.activeElement,
    });
    render(); focusFirst();
  };

  function close() {
    clearTimeout(S.timer); S.seq++;
    S.open = false; rootEl.classList.remove('open'); rootEl.innerHTML = '';
    if (S.trigger && S.trigger.focus) { try { S.trigger.focus(); } catch (e) { /* element gone */ } }
  }

  function requestClose() {
    if (S.discard) { S.discard = false; syncFooter(); return; }
    if (S.step !== 'form') { S.step = 'form'; S.conflict = false; render(); return; }
    if (isDirty()) { S.discard = true; syncFooter(); return; }
    close();
  }

  // ─── Render ──────────────────────────────────────────────────────────────
  function render() {
    const kind = S.spec.label;
    rootEl.classList.add('open');
    rootEl.innerHTML = `<div class="ef-card" role="dialog" aria-modal="true" aria-label="${h(kind)}">
      <div class="ef-head">
        <div class="ef-titles">
          <div class="ef-kicker">${h(kind)} · ${S.mode === 'edit' ? 'Editing' : 'New'}</div>
          <div class="ef-name" id="ef-name"></div>
          <div class="ef-id" id="ef-id"></div>
        </div>
        <button class="ef-x-close" data-act="close" aria-label="Close">×</button>
      </div>
      ${S.step === 'form' ? tabsHtml() : ''}
      <div class="ef-body" id="ef-body"></div>
      <div class="ef-foot" id="ef-foot"></div>
    </div>`;
    renderBody(); syncFooter(); paintHeader();
  }

  function tabsHtml() {
    const filled = S.spec.sections.filter((n) => String(S.sections[n] || '').trim()).length;
    const tab = (id, label, extra) => `<button class="ef-tab${S.tab === id ? ' active' : ''}" data-act="tab" data-tab="${id}">${label}${extra || ''}<i class="ef-dot" data-dot="${id}"></i></button>`;
    return `<div class="ef-tabs">${tab('fields', 'Fields')}${S.spec.sections.length ? tab('sections', 'Sections', `<small>${filled}/${S.spec.sections.length}</small>`) : ''}</div>`;
  }

  function renderBody() {
    const body = document.getElementById('ef-body'); if (!body) return;
    const top = body.scrollTop;
    body.innerHTML = S.step === 'review' ? reviewHtml() : S.step === 'delete' ? deleteHtml()
      : `<div class="ef-banner" id="ef-banner"></div>` + (S.tab === 'sections' ? sectionsHtml() : fieldsHtml());
    body.scrollTop = top;
    body.querySelectorAll('textarea').forEach(autosize);
    paintMessages();
  }

  function fieldsHtml() {
    const normal = S.spec.fields.filter((f) => f.kind !== 'computed').map(fieldHtml).join('');
    const derived = S.mode === 'edit' ? S.spec.fields.filter((f) => f.kind === 'computed').map(derivedHtml).join('') : '';
    return normal + (derived ? `<div class="ef-derived">${derived}</div>` : '');
  }

  function fieldHtml(f) {
    const locked = S.mode === 'edit' && f.locked_on_edit;
    const note = locked ? f.locked_on_edit : f.help;
    return `<div class="ef-field">
      <label class="ef-label" for="ef-f-${h(f.key)}">${h(f.label)}${f.required ? '<abbr class="ef-req" title="Required">*</abbr>' : ''}</label>
      ${widget(f, locked)}
      ${note ? `<div class="ef-help">${h(note)}</div>` : ''}
      <div class="ef-msg" data-msg="${h(f.key)}"></div></div>`;
  }

  function widget(f, locked) {
    const v = S.values[f.key], id = `id="ef-f-${h(f.key)}" data-key="${h(f.key)}"`;
    switch (f.kind) {
      case 'text': return `<input class="ef-input" ${id} value="${h(v)}" autocomplete="off"${locked ? ' disabled' : ''}>`;
      case 'number': return `<input class="ef-input" type="number" ${id} value="${h(v)}">`;
      case 'textarea': return `<textarea class="ef-input" ${id} rows="2">${h(v)}</textarea>`;
      case 'toggle': return `<input type="checkbox" ${id}${v ? ' checked' : ''}>`;
      case 'select':
        return `<select class="ef-input" ${id}><option value="">—</option>${f.options.map((o) => `<option${o === v ? ' selected' : ''}>${h(o)}</option>`).join('')}</select>`;
      case 'ref': return refSelect(f, id, v);
      case 'list': return listWidget(f, v || []);
      default: return `<div class="ef-note">Not editable here yet — ask the agent.</div>`;
    }
  }

  // A picker over entities that exist, so a link can't point at nothing.
  function refSelect(f, id, v) {
    const all = ((D.story || {})[LISTS[f.ref]] || []).filter((e) => e.id !== S.id);
    all.sort((a, b) => String(a.name || a.title).localeCompare(String(b.name || b.title)));
    const known = all.some((e) => e.id === v);
    return `<select class="ef-input" ${id}><option value="">— none —</option>
      ${v && !known ? `<option value="${h(v)}" selected>${h(v)} (missing)</option>` : ''}
      ${all.map((e) => `<option value="${h(e.id)}"${e.id === v ? ' selected' : ''}>${h(e.name || e.title || e.id)}</option>`).join('')}</select>`;
  }

  function listWidget(f, items) {
    return `<div class="ef-list">${items.map((it, i) => `<div class="ef-row">
        <input class="ef-input" data-list="${h(f.key)}" data-i="${i}" value="${h(it)}" autocomplete="off">
        <button class="ef-rm" data-act="list-del" data-key="${h(f.key)}" data-i="${i}" aria-label="Remove" title="Remove">×</button></div>`).join('')}
      <button class="ef-add" data-act="list-add" data-key="${h(f.key)}">+ Add</button></div>`;
  }

  function derivedHtml(f) {
    const rows = (S.orig.computed || {})[f.key] || [];
    return `<div class="ef-field"><div class="ef-label">${h(f.label)}</div>
      <div class="ef-ro${rows.length ? '' : ' none'}">${rows.length ? rows.map((r) => `<div>${h(r.display)}</div>`).join('') : 'None yet'}</div>
      ${f.hint ? `<div class="ef-note">${h(f.hint)}</div>` : ''}</div>`;
  }

  function sectionsHtml() {
    return S.spec.sections.map((n) => `<div class="ef-field">
      <label class="ef-label" for="ef-s-${h(n)}">${h(n)}</label>
      <textarea class="ef-input ef-area" id="ef-s-${h(n)}" data-section="${h(n)}" rows="4">${h(S.sections[n])}</textarea></div>`).join('');
  }

  function autosize(el) {
    el.style.height = 'auto';
    el.style.height = Math.max(el.scrollHeight + 2, el.classList.contains('ef-area') ? 84 : 34) + 'px';
  }

  // ─── Review (edit) ───────────────────────────────────────────────────────
  function fmtScalar(f, v) {
    if (v === '' || v == null) return '—';
    if (f.kind === 'ref') return refName(f.ref, v);
    if (f.kind === 'toggle') return v ? 'Yes' : 'No';
    return String(v);
  }
  const clip = (s) => { s = String(s || '').trim(); return !s ? '—' : (s.length > 260 ? s.slice(0, 260) + '…' : s); };

  function reviewHtml() {
    const a = norm(S.orig.values), b = norm(S.values), rows = [];
    changedFields().forEach((f) => {
      let was, now;
      if (f.kind === 'list') {
        const x = a[f.key] || [], y = b[f.key] || [];
        was = x.length ? x.map((i) => y.includes(i) ? h(i) : `<span class="del">${h(i)}</span>`).join('<br>') : '—';
        now = y.length ? y.map((i) => x.includes(i) ? h(i) : `<span class="add">${h(i)}</span>`).join('<br>') : '—';
      } else { was = h(fmtScalar(f, a[f.key])); now = h(fmtScalar(f, b[f.key])); }
      rows.push(diff(f.label, was, now));
    });
    changedSections().forEach((n) => rows.push(diff(n, h(clip(S.orig.sections[n])), h(clip(S.sections[n])))));
    const banner = S.conflict
      ? `<div class="ef-banner info on">This was changed since you opened it — probably by the agent.
         <button class="btn" data-act="rebase">Apply my edits on top of the latest</button></div>` : '';
    return `${banner}<div class="ef-sub">Check what will change in “${h(S.values[nameKey()] || S.id)}”.</div>${rows.join('') || '<div class="ef-sub">Nothing changed.</div>'}`;
  }
  const diff = (label, was, now) => `<div class="ef-diff"><div class="ef-diff-h">${h(label)}</div>
    <div class="ef-diff-b"><div class="was">${was}</div><div class="now">${now}</div></div></div>`;

  // ─── Delete ──────────────────────────────────────────────────────────────
  function deleteHtml() {
    const p = S.preview;
    if (!p) return '<div class="ef-sub">Checking what this affects…</div>';
    const list = (items) => `<ul>${items.map((i) => `<li>${h(i)}</li>`).join('')}</ul>`;
    const kind = (t) => (specs[t] ? specs[t].label : t);
    const also = p.also_deleted.map((e) => `${kind(e.type)}: ${e.name}`);
    const rels = p.relationships.map((e) => e.name);
    return `<div class="ef-impact">
      <div class="ef-sub">Delete ${h(p.entity.label.toLowerCase())} “${h(p.entity.name)}”?</div>
      ${also.length ? `<h4>Also deleted</h4>${list(also)}` : ''}
      ${rels.length ? `<h4>Relationships removed with them</h4>${list(rels)}` : ''}
      ${p.effects.length ? `<h4>Also changes</h4>${list(p.effects)}` : ''}
      ${p.blockers.length ? `<div class="block"><h4>Can’t delete yet</h4>${list(p.blockers)}</div>` : ''}
      ${!p.effects.length && !also.length && !rels.length && !p.blockers.length ? '<div class="ef-note">Nothing else uses it.</div>' : ''}
      ${p.can_delete ? '<div class="ef-note">It can be restored later by asking the agent.</div>' : ''}</div>`;
  }

  // ─── Footer ──────────────────────────────────────────────────────────────
  function footerHtml() {
    if (S.discard) return `<div class="grow">Discard your changes?</div>
      <button class="btn btn-ghost" data-act="keep">Keep editing</button><button class="btn btn-danger" data-act="discard">Discard</button>`;
    if (S.step === 'review') return `<button class="btn" data-act="back">Back</button><div class="grow"></div>
      <button class="btn btn-primary" data-act="confirm"${S.busy ? ' disabled' : ''}>${S.busy ? 'Saving…' : 'Confirm and save'}</button>`;
    if (S.step === 'delete') {
      const p = S.preview;
      return `<button class="btn" data-act="back">Back</button><div class="grow"></div>
        <button class="btn btn-danger" data-act="confirm-delete"${!p || !p.can_delete || S.busy ? ' disabled' : ''}>${S.busy ? 'Deleting…' : 'Delete'}</button>`;
    }
    const edit = S.mode === 'edit';
    return `${edit ? '<button class="btn btn-danger btn-ghost" data-act="ask-delete">Delete…</button>' : ''}<div class="grow"></div>
      <button class="btn" data-act="close">Cancel</button>
      <button class="btn btn-primary" data-act="save"${S.busy || (edit && !isDirty()) ? ' disabled' : ''}>${edit ? 'Review changes' : 'Create'}</button>`;
  }
  function syncFooter() { const f = document.getElementById('ef-foot'); if (f) f.innerHTML = footerHtml(); }

  function paintHeader() {
    const n = document.getElementById('ef-name'), i = document.getElementById('ef-id'); if (!n) return;
    const v = String(S.values[nameKey()] || '').trim();
    n.textContent = v || (S.mode === 'create' ? `New ${S.spec.label.toLowerCase()}` : S.id);
    n.classList.toggle('empty', !v);
    i.textContent = S.mode === 'edit' ? 'id: ' + S.id : (S.newId && v ? 'id: ' + S.newId : '');
  }

  // Messages show for a field once it's been touched, or after a save attempt.
  function paintMessages() {
    const show = (k) => S.submitted || S.touched.has(k);
    document.querySelectorAll('#ef-body [data-msg]').forEach((el) => {
      const k = el.dataset.msg, err = show(k) && S.errors[k], warn = show(k) && !err && S.warnings[k];
      el.textContent = err || warn || '';
      el.className = 'ef-msg' + (err ? ' err' : warn ? ' warn' : '');
      const input = el.parentElement.querySelector('.ef-input');
      if (input) input.classList.toggle('ef-invalid', !!err);
    });
    const b = document.getElementById('ef-banner');
    if (b) { const m = S.errors._form; b.textContent = m || ''; b.className = 'ef-banner' + (m ? ' on' : ''); }
    const dot = document.querySelector('[data-dot="fields"]');
    if (dot) dot.classList.toggle('on', S.tab !== 'fields' && Object.keys(S.errors).some((k) => k !== '_form' && show(k)));
  }

  function jumpToFirstError() {
    const key = Object.keys(S.errors).find((k) => k !== '_form');
    if (key && S.tab !== 'fields') { S.tab = 'fields'; render(); }
    else if (S.step !== 'form') { S.step = 'form'; render(); }
    const el = key && document.querySelector(`[data-key="${CSS.escape(key)}"]`);
    if (el) { el.scrollIntoView({ block: 'center' }); el.focus(); }
  }

  function focusFirst() {
    const el = document.querySelector('#ef-body .ef-input:not(:disabled)'); if (el) el.focus();
  }

  // ─── Live check, save, delete ────────────────────────────────────────────
  function scheduleCheck() { clearTimeout(S.timer); S.timer = setTimeout(runCheck, 350); }
  async function runCheck() {
    const seq = ++S.seq;
    try {
      const r = await api('/entities/' + S.type + '/check', { method: 'POST', body: JSON.stringify(payload()) });
      if (seq !== S.seq || !S.open) return;
      S.errors = r.errors || {}; S.warnings = r.warnings || {}; S.newId = r.id;
      paintMessages(); paintHeader();
    } catch (e) { /* a failed dry run is not worth interrupting typing for */ }
  }

  function failed(e) {
    if (e.status === 422) {
      S.errors = (e.body && e.body.errors) || { _form: e.message };
      S.warnings = (e.body && e.body.warnings) || {};
      S.submitted = true; S.step = 'form'; render(); jumpToFirstError();
    } else if (e.status === 409 && e.body.code === 'conflict') {
      S.conflict = true; S.step = 'review'; render();
    } else toast(e.message, 'bad');
  }

  async function save() {
    if (S.busy) return;
    S.submitted = true; S.busy = true; syncFooter();
    try {
      if (S.mode === 'create') {
        D._ownWriteUntil = Date.now() + 8000;
        finish(await api('/entities/' + S.type, { method: 'POST', body: JSON.stringify(payload()) }), 'Created');
        return;
      }
      const r = await api('/entities/' + S.type + '/check', { method: 'POST', body: JSON.stringify(payload()) });
      S.errors = r.errors || {}; S.warnings = r.warnings || {};
      if (!r.ok) { render(); jumpToFirstError(); return; }
      S.step = 'review'; render();
    } catch (e) { failed(e); }
    finally { S.busy = false; syncFooter(); }
  }

  async function confirmSave() {
    if (S.busy) return;
    S.busy = true; syncFooter();
    try {
      D._ownWriteUntil = Date.now() + 8000;
      const res = await api('/entities/' + S.type + '/' + encodeURIComponent(S.id), { method: 'PUT', body: JSON.stringify(payload()) });
      finish(res, 'Saved');
    } catch (e) { failed(e); }
    finally { S.busy = false; syncFooter(); }
  }

  // The agent committed while the form was open. Keep what the person changed,
  // and take everything they did NOT touch from the latest, so their stale copy
  // of an untouched field can't undo the agent's edit.
  async function rebase() {
    try {
      const fresh = await api('/entities/' + S.type + '/' + encodeURIComponent(S.id) + '/form');
      const mine = (a, b, k) => !eq(a[k], b[k]);
      const values = clone(fresh.values), sections = clone(fresh.sections);
      Object.keys(S.values).forEach((k) => { if (mine(norm(S.base.values), norm(S.values), k)) values[k] = S.values[k]; });
      Object.keys(S.sections).forEach((k) => { if (String(S.base.sections[k] || '').trim() !== String(S.sections[k] || '').trim()) sections[k] = S.sections[k]; });
      S.orig = fresh; S.base = clone(fresh); S.values = values; S.sections = sections; S.conflict = false;
      render();
    } catch (e) { toast(e.message, 'bad'); }
  }

  async function askDelete() {
    S.step = 'delete'; S.preview = null; render();
    try { S.preview = await api('/entities/' + S.type + '/' + encodeURIComponent(S.id) + '/delete-preview'); }
    catch (e) { toast(e.message, 'bad'); S.step = 'form'; render(); return; }
    renderBody(); syncFooter();
  }

  async function confirmDelete() {
    if (S.busy) return;
    S.busy = true; syncFooter();
    try {
      D._ownWriteUntil = Date.now() + 8000;
      await api('/entities/' + S.type + '/' + encodeURIComponent(S.id), { method: 'DELETE' });
      const name = S.preview.entity.name, id = S.id;
      close();
      if (D._formTarget && D._formTarget.id === id && D.closePanel) D.closePanel();
      if (D.reloadData) await D.reloadData();
      toast(`Deleted “${name}”`);
    } catch (e) {
      if (e.status === 409 && e.body.blockers) { S.preview.blockers = e.body.blockers; S.preview.can_delete = false; renderBody(); }
      else toast(e.message, 'bad');
    } finally { S.busy = false; syncFooter(); }
  }

  async function finish(res, verb) {
    const type = S.type, name = res.values[nameKey()] || res.id;
    close();
    if (D.reloadData) await D.reloadData(); else location.reload();
    if (PANEL_TYPES.includes(type) && D.panelTabs) D.panelTabs.openEntity(type + ':' + res.id);
    toast(`${verb} “${name}”`);
  }

  // ─── Events ──────────────────────────────────────────────────────────────
  function act(name, el) {
    switch (name) {
      case 'close': requestClose(); break;
      case 'tab': S.tab = el.dataset.tab; render(); focusFirst(); break;
      case 'save': save(); break;
      case 'back': S.step = 'form'; S.conflict = false; render(); break;
      case 'confirm': confirmSave(); break;
      case 'rebase': rebase(); break;
      case 'ask-delete': askDelete(); break;
      case 'confirm-delete': confirmDelete(); break;
      case 'keep': S.discard = false; syncFooter(); break;
      case 'discard': close(); break;
      case 'list-add': {
        const k = el.dataset.key; (S.values[k] = S.values[k] || []).push('');
        renderBody(); const rows = document.querySelectorAll(`[data-list="${CSS.escape(k)}"]`); rows[rows.length - 1].focus(); break;
      }
      case 'list-del': {
        S.values[el.dataset.key].splice(+el.dataset.i, 1); renderBody(); afterEdit(); break;
      }
    }
  }

  function afterEdit() { scheduleCheck(); syncFooter(); paintHeader(); }

  function onInput(e) {
    const el = e.target;
    if (el.dataset.key != null) {
      S.values[el.dataset.key] = el.type === 'checkbox' ? el.checked : el.value;
      S.touched.add(el.dataset.key);
    } else if (el.dataset.list != null) {
      S.values[el.dataset.list][+el.dataset.i] = el.value; S.touched.add(el.dataset.list);
    } else if (el.dataset.section != null) {
      S.sections[el.dataset.section] = el.value;
    } else return;
    if (el.tagName === 'TEXTAREA') autosize(el);
    afterEdit();
  }

  function onKey(e) {
    if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); requestClose(); return; }
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) { e.preventDefault(); const b = rootEl.querySelector('.ef-foot .btn-primary:not([disabled])'); if (b) b.click(); return; }
    if (e.key === 'Enter' && e.target.dataset && e.target.dataset.list != null) {
      e.preventDefault();
      const k = e.target.dataset.list, i = +e.target.dataset.i;
      if (!String(S.values[k][i] || '').trim()) return;
      S.values[k].splice(i + 1, 0, ''); renderBody();
      const rows = document.querySelectorAll(`[data-list="${CSS.escape(k)}"]`); if (rows[i + 1]) rows[i + 1].focus();
      return;
    }
    if (e.key === 'Tab') {                               // keep focus inside the dialog
      const f = [...rootEl.querySelectorAll('button:not([disabled]), input:not([disabled]), select, textarea')].filter((n) => n.offsetParent);
      if (!f.length) return;
      const first = f[0], last = f[f.length - 1];
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
    }
  }

  // ─── Entry points ────────────────────────────────────────────────────────
  // The panel's Edit button follows whichever character / location / world
  // panel is open. A panel function announces its entity just before it calls
  // openPanel; any other panel announces nothing, so the button hides itself.
  function syncEditButton() {
    const b = document.getElementById('panel-edit'); if (b) b.classList.toggle('on', !!D._formTarget);
  }

  function wrapPanels() {
    const wrap = (fn, type) => {
      const base = D[fn]; if (typeof base !== 'function') return;
      D[fn] = function (arg) {
        D._pendingFormTarget = { type, id: arg && typeof arg === 'object' ? arg.id : arg };
        try { return base.apply(this, arguments); } finally { D._pendingFormTarget = null; }
      };
    };
    wrap('showCharacterPanel', 'character'); wrap('showLocationPanel', 'location'); wrap('showWorldPanel', 'world');
    const open = D.openPanel, close_ = D.closePanel;
    D.openPanel = function () { const r = open.apply(this, arguments); D._formTarget = D._pendingFormTarget || null; syncEditButton(); return r; };
    D.closePanel = function () { D._formTarget = null; syncEditButton(); return close_.apply(this, arguments); };
  }

  function closeMenu() { if (menuEl) { menuEl.remove(); menuEl = null; } }

  // Values have no list or panel of their own, so the Values view gets a menu.
  D.openValuesMenu = function (btn) {
    if (menuEl) { closeMenu(); return; }
    const vals = ((D.story || {}).values || []).slice().sort((a, b) => String(a.name).localeCompare(String(b.name)));
    menuEl = document.createElement('div'); menuEl.className = 'ef-menu';
    menuEl.innerHTML = vals.map((v) => `<button data-vid="${h(v.id)}">${h(v.name)}<small>${h(v.p)} → ${h(v.nn)}</small></button>`).join('')
      + '<button class="new" data-vnew>+ New value</button>';
    const r = btn.getBoundingClientRect();
    menuEl.style.top = (r.bottom + 4) + 'px'; menuEl.style.right = (window.innerWidth - r.right) + 'px';
    menuEl.addEventListener('click', (e) => {
      const b = e.target.closest('button'); if (!b) return;
      closeMenu();
      D.openEntityForm(b.dataset.vid ? { type: 'value', id: b.dataset.vid } : { type: 'value' });
    });
    document.body.appendChild(menuEl);
    setTimeout(() => document.addEventListener('click', function off(e) {
      if (menuEl && !menuEl.contains(e.target)) closeMenu();
      document.removeEventListener('click', off);
    }), 0);
  };

  function init() {
    rootEl = document.createElement('div');
    rootEl.className = 'ef-backdrop'; rootEl.id = 'entity-form-root';
    document.body.appendChild(rootEl);
    rootEl.addEventListener('click', (e) => {
      const t = e.target.closest('[data-act]');
      if (t) act(t.dataset.act, t); else if (e.target === rootEl) requestClose();
    });
    rootEl.addEventListener('input', onInput);
    rootEl.addEventListener('focusout', (e) => {
      const k = e.target.dataset && (e.target.dataset.key || e.target.dataset.list);
      if (k && S.open) { S.touched.add(k); paintMessages(); }
    });
    rootEl.addEventListener('keydown', onKey);
    wrapPanels();
    const edit = document.getElementById('panel-edit');
    if (edit) edit.addEventListener('click', () => { if (D._formTarget) D.openEntityForm(D._formTarget); });
  }
  init();
})(window.DASH);
