// Entity form — create, edit and delete an entity by hand.
//
// One renderer for every type. The server describes each type as a form spec
// (`/form-spec`, built from ENTITY_SCHEMAS), so a field added to the schema
// appears here with no change to this file. Nothing here knows what a
// "character" is; it knows kinds: text, textarea, select, ref, reflist, list,
// perspectives (a card per chosen entity), repeater (a stack of small cards), linked,
// computed.
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
  const LISTS = { character: 'characters', location: 'locations', world: 'worlds', plot: 'plots', value: 'values', scene: 'scenes', sequence: 'sequences', act: 'acts' };
  const PANEL_TYPES = ['character', 'location', 'world', 'plot', 'relationship'];
  const PANELS = { plot: 'showPlotPanel', scene: 'showScenePanel', sequence: 'showSequencePanel', act: 'showActPanel' };
  const blankPersp = () => ({ label: '', feeling: '', type: '', strength: '', secret: false });

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

  D.efToast = toast;

  // ─── Values: normalise, diff, dirty ──────────────────────────────────────
  const editable = () => S.spec.fields.filter((f) => f.kind !== 'computed' && f.kind !== 'linked' && f.kind !== 'unsupported');
  const nameKey = () => S.spec.name_key;
  // A field with `show_if` only exists while its condition holds; hidden, it counts as its default.
  const visible = (f) => !f.show_if || Object.keys(f.show_if).every((k) => S.values[k] === f.show_if[k]);
  const dependedOn = (key) => S.spec.fields.some((g) => g.show_if && key in g.show_if);

  function norm(values) {
    const out = {};
    editable().forEach((f) => {
      let v = values[f.key];
      if (f.show_if && !Object.keys(f.show_if).every((k) => values[k] === f.show_if[k])) v = clone(f.default);
      else if (f.kind === 'list' || f.kind === 'reflist') v = (v || []).map((x) => String(x).trim()).filter(Boolean);
      else if (f.kind === 'repeater') {
        v = (v || []).map((r) => { const o = {}; f.fields.forEach((sf) => { o[sf.key] = String(r[sf.key] == null ? '' : r[sf.key]).trim(); }); return o; })
          .filter((r) => Object.values(r).some(Boolean));
      } else if (f.kind === 'perspectives') {
        const o = {};
        Object.keys(v || {}).forEach((id) => { const p = v[id] || {}; o[id] = {
          label: String(p.label || '').trim(), feeling: String(p.feeling || '').trim(), type: String(p.type || '').trim(),
          strength: p.strength === '' || p.strength == null ? '' : Number(p.strength), secret: !!p.secret }; });
        v = o;
      } else if (typeof v === 'string') v = v.trim();
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
      values[f.key] = clone(f.default);
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
      errors: {}, warnings: {}, newId: null, touched: new Set(), nameTyped: false, submitted: false, seq: 0, timer: 0,
      trigger: document.activeElement,
    });
    render(); focusFirst();
  };

  function goScript() {
    const id = S.id; close();
    if (D.openScriptEditor) D.openScriptEditor(id);
  }

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
    rootEl.innerHTML = `<div class="ef-card" role="dialog" aria-modal="true" aria-label="${h(kind)}" tabindex="-1">
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
    if (!rootEl.contains(document.activeElement)) rootEl.querySelector('.ef-card').focus();   // keep focus inside
  }

  function tabsHtml() {
    const filled = S.spec.sections.filter((n) => String(S.sections[n] || '').trim()).length;
    const tab = (id, label, extra) => `<button class="ef-tab${S.tab === id ? ' active' : ''}" data-act="tab" data-tab="${id}">${label}${extra || ''}<i class="ef-dot" data-dot="${id}"></i></button>`;
    const script = S.spec.script_link && S.mode === 'edit' ? tab('script', 'Script') : '';
    return `<div class="ef-tabs">${tab('fields', 'Fields')}${S.spec.sections.length ? tab('sections', 'Sections', `<small>${filled}/${S.spec.sections.length}</small>`) : ''}${script}</div>`;
  }

  function renderBody() {
    const body = document.getElementById('ef-body'); if (!body) return;
    const top = body.scrollTop;
    body.innerHTML = S.step === 'review' ? reviewHtml() : S.step === 'delete' ? deleteHtml()
      : `<div class="ef-banner" id="ef-banner"></div>` + (S.tab === 'sections' ? sectionsHtml() : S.tab === 'script' ? scriptHtml() : fieldsHtml());
    body.scrollTop = top;
    body.querySelectorAll('textarea').forEach(autosize);
    paintMessages();
  }

  function fieldsHtml() {
    let last = null, html = '';
    S.spec.fields.filter((f) => f.kind !== 'computed' && f.kind !== 'linked' && visible(f)).forEach((f) => {
      if ((f.group || null) !== last) { last = f.group || null; if (last) html += `<h3 class="ef-group">${h(last)}</h3>`; }
      html += fieldHtml(f);
    });
    const derived = S.mode === 'edit' ? derivedBlock() : '';
    return html + (derived ? `<div class="ef-derived">${derived}</div>` : '');
  }

  function fieldHtml(f) {
    const locked = S.mode === 'edit' && f.locked_on_edit;
    const note = locked ? f.locked_on_edit : f.help;
    const err = `<div class="ef-msg" data-msg="${h(f.key)}"></div>`;
    if (f.kind === 'perspectives') return `<div class="ef-field"><div class="ef-label">${h(f.label)}</div>${perspectivesHtml(f)}${err}</div>`;
    if (f.kind === 'repeater') return `<div class="ef-field"><div class="ef-label">${h(f.label)}</div>${repeaterHtml(f)}${note ? `<div class="ef-help">${h(note)}</div>` : ''}${err}</div>`;
    if (f.kind === 'toggle') return `<div class="ef-field">${widget(f, locked)}${note ? `<div class="ef-help">${h(note)}</div>` : ''}${err}</div>`;
    return `<div class="ef-field">
      <label class="ef-label" for="ef-f-${h(f.key)}">${h(f.label)}${f.required ? '<abbr class="ef-req" title="Required">*</abbr>' : ''}</label>
      ${widget(f, locked)}
      ${note ? `<div class="ef-help">${h(note)}</div>` : ''}${err}</div>`;
  }

  function widget(f, locked) {
    const v = S.values[f.key], id = `id="ef-f-${h(f.key)}" data-key="${h(f.key)}"`;
    switch (f.kind) {
      case 'text': return `<input class="ef-input" ${id} value="${h(v)}" autocomplete="off"${locked ? ' disabled' : ''}>`;
      case 'number': return `<input class="ef-input" type="number" ${id} value="${h(v)}"${numAttrs(f)}>`;
      case 'textarea': return `<textarea class="ef-input" ${id} rows="2">${h(v)}</textarea>`;
      case 'toggle': return `<label class="ef-check"><input type="checkbox" ${id}${v ? ' checked' : ''}> <span>${h(f.label)}</span></label>`;
      case 'select': return selectHtml(f, id, v);
      case 'ref': return refSelect(f, id, v, locked);
      case 'reflist': return refListWidget(f, v || []);
      case 'list': return listWidget(f, v || []);
      default: return `<div class="ef-note">Not editable here yet — ask the agent.</div>`;
    }
  }

  const numAttrs = (f) => ['min', 'max', 'step'].filter((k) => f[k] != null).map((k) => ` ${k}="${f[k]}"`).join('') + (f.integer ? ' step="1"' : '');

  function selectHtml(f, attrs, v) {
    const lab = (o) => h((f.option_labels || {})[o] || o);
    const stray = v && !f.options.includes(v) ? `<option value="${h(v)}" selected>${h(v)}</option>` : '';     // keep a stored value we don't list
    return `<select class="ef-input" ${attrs}>${f.allow_blank ? '<option value="">—</option>' : ''}${stray}
      ${f.options.map((o) => `<option value="${h(o)}"${o === v ? ' selected' : ''}>${lab(o)}</option>`).join('')}</select>`;
  }

  // A sequence is named with its act, so "Scene 3" in two acts can't be confused.
  function optLabel(type, e) {
    const n = e.name || e.title || e.id;
    if (type !== 'sequence') return n;
    const a = ((D.story || {}).acts || []).find((x) => x.id === e.act_id);
    return a ? `${a.title || a.id} › ${n}` : n;
  }
  function optSort(type) {
    if (type !== 'sequence') return (a, b) => String(a.name || a.title).localeCompare(String(b.name || b.title));
    const act = (e) => { const a = ((D.story || {}).acts || []).find((x) => x.id === e.act_id); return a ? (a.order || 0) : 0; };
    return (a, b) => act(a) - act(b) || (a.order || 0) - (b.order || 0);
  }

  // A picker over entities that exist, so a link can't point at nothing.
  function refSelect(f, id, v, locked) {
    const all = ((D.story || {})[LISTS[f.ref]] || []).filter((e) => e.id !== S.id).sort(optSort(f.ref));
    const known = all.some((e) => e.id === v);
    return `<select class="ef-input" ${id}${locked ? ' disabled' : ''}><option value="">${f.required ? '— choose —' : '— none —'}</option>
      ${v && !known ? `<option value="${h(v)}" selected>${h(v)} (missing)</option>` : ''}
      ${all.map((e) => `<option value="${h(e.id)}"${e.id === v ? ' selected' : ''}>${h(optLabel(f.ref, e))}</option>`).join('')}</select>`;
  }

  const entityName = (type, id) => refName(type, id);
  function entityOptions(type, chosen, current) {
    const all = ((D.story || {})[LISTS[type]] || []).filter((e) => e.id === current || !chosen.includes(e.id)).sort(optSort(type));
    const known = all.some((e) => e.id === current);
    return `<option value="">— choose —</option>${current && !known ? `<option value="${h(current)}" selected>${h(current)} (missing)</option>` : ''}`
      + all.map((e) => `<option value="${h(e.id)}"${e.id === current ? ' selected' : ''}>${h(optLabel(type, e))}</option>`).join('');
  }

  // Several entities of one kind. `count` fixes the number of slots (a relationship's two characters);
  // otherwise rows grow and shrink. A character already picked in one slot is not offered in another.
  function refListWidget(f, items) {
    const rows = f.count ? Array.from({ length: f.count }, (_, i) => items[i] || '') : items;
    const chosen = rows.filter(Boolean);
    return `<div class="ef-list">${rows.map((cur, i) => `<div class="ef-row">
        <select class="ef-input" id="ef-f-${h(f.key)}-${i}" data-ref="${h(f.key)}" data-i="${i}" aria-label="${h((f.row_labels || [])[i] || f.label)}">${entityOptions(f.ref, chosen, cur)}</select>
        ${f.count ? '' : `<button class="ef-rm" data-act="ref-del" data-key="${h(f.key)}" data-i="${i}" aria-label="Remove" title="Remove">×</button>`}</div>
        ${f.count && (f.row_labels || [])[i] ? `<div class="ef-note ef-rowlabel">${h(f.row_labels[i])}</div>` : ''}`).join('')}
      ${f.count ? '' : `<button class="ef-add" data-act="ref-add" data-key="${h(f.key)}">+ ${h(f.add_label || 'Add')}</button>`}</div>`;
  }

  // One card per chosen entity — they appear only once that entity is picked.
  function perspectivesHtml(f) {
    const ids = (S.values[f.keyed_by] || []).filter(Boolean), cards = S.values[f.key] || {};
    if (!ids.length) return '<div class="ef-note">Pick the characters first — each gets a card here.</div>';
    return ids.map((cid) => {
      const other = ids.length === 2 ? ids.find((x) => x !== cid) : null;
      const title = other ? `How ${entityName(f.ref, cid)} sees ${entityName(f.ref, other)}` : entityName(f.ref, cid);
      const p = cards[cid] || blankPersp();
      const sub = f.fields.map((sf) => {
        const path = `${f.key}.${cid}.${sf.key}`, at = `data-pc="${h(cid)}" data-pf="${h(sf.key)}" data-path="${h(path)}" id="ef-p-${h(cid)}-${h(sf.key)}"`;
        let w;
        if (sf.kind === 'select') w = selectHtml(sf, at, p[sf.key]);
        else if (sf.kind === 'number') w = `<input class="ef-input" type="number" ${at} value="${h(p[sf.key])}"${numAttrs(sf)}>`;
        else if (sf.kind === 'toggle') w = `<label class="ef-check"><input type="checkbox" ${at}${p[sf.key] ? ' checked' : ''}> <span>${h(sf.label)}</span></label>`;
        else w = `<input class="ef-input" ${at} value="${h(p[sf.key])}" autocomplete="off">`;
        return `<div class="ef-field${sf.kind === 'toggle' ? ' ef-wide' : ''}">${sf.kind === 'toggle' ? '' : `<label class="ef-label" for="ef-p-${h(cid)}-${h(sf.key)}">${h(sf.label)}</label>`}${w}
          ${sf.help ? `<div class="ef-help">${h(sf.help)}</div>` : ''}<div class="ef-msg" data-msg="${h(path)}"></div></div>`;
      }).join('');
      return `<div class="ef-sub-card"><div class="ef-sub-card-h">${h(title)}</div><div class="ef-grid">${sub}</div></div>`;
    }).join('');
  }

  // A stack of small cards (a scene's plot roles). A card appears only when added.
  const newCard = (f) => { const o = {}; f.fields.forEach((sf) => { o[sf.key] = sf.kind === 'select' && !sf.allow_blank ? sf.options[0] : ''; }); return o; };

  function repeaterHtml(f) {
    const items = S.values[f.key] || [];
    const chosen = (sf) => items.map((r) => r[sf.key]).filter(Boolean);
    return `<div class="ef-list">${items.map((it, i) => `<div class="ef-sub-card">
        <div class="ef-sub-card-h">${h(f.label.replace(/s$/, ''))} ${i + 1}
          <button class="ef-rm ef-rm-card" data-act="rep-del" data-key="${h(f.key)}" data-i="${i}" aria-label="Remove" title="Remove">×</button></div>
        <div class="ef-grid">${f.fields.map((sf) => {
          const path = `${f.key}.${i}.${sf.key}`, at = `data-rk="${h(f.key)}" data-ri="${i}" data-rf="${h(sf.key)}" data-path="${h(path)}" id="ef-r-${h(f.key)}-${i}-${h(sf.key)}"`;
          const w = sf.kind === 'ref' ? `<select class="ef-input" ${at}>${entityOptions(sf.ref, chosen(sf).filter((x) => x !== it[sf.key]), it[sf.key])}</select>`
            : sf.kind === 'select' ? selectHtml(sf, at, it[sf.key])
            : `<input class="ef-input" ${at} value="${h(it[sf.key])}" autocomplete="off">`;
          return `<div class="ef-field${sf.key === 'description' ? ' ef-wide' : ''}"><label class="ef-label" for="ef-r-${h(f.key)}-${i}-${h(sf.key)}">${h(sf.label)}</label>${w}
            ${sf.help ? `<div class="ef-help">${h(sf.help)}</div>` : ''}<div class="ef-msg" data-msg="${h(path)}"></div></div>`;
        }).join('')}</div></div>`).join('')}
      <button class="ef-add" data-act="rep-add" data-key="${h(f.key)}">+ ${h(f.add_label || 'Add')}</button></div>`;
  }

  // What the script editor owns on a scene. Shown here so the form tells the whole story,
  // never edited here so the heading line and these fields can't disagree.
  function scriptHtml() {
    const rows = S.spec.fields.filter((f) => f.kind === 'linked').map((f) => {
      const r = (S.orig.computed || {})[f.key] || [];
      return `<div class="ef-field"><div class="ef-label">${h(f.label)}</div>
        <div class="ef-ro${r.length ? '' : ' none'}">${r.length ? r.map((x) => `<div>${h(x.display)}</div>`).join('') : 'Not set'}</div></div>`;
    }).join('');
    return `<div class="ef-note">The script, its heading, location, time of day and cast are written together in the script editor, so they always agree.</div>
      ${rows}<div><button class="btn" data-act="open-script">Edit in script editor →</button></div>`;
  }

  function listWidget(f, items) {
    return `<div class="ef-list">${items.map((it, i) => `<div class="ef-row">
        <input class="ef-input" data-list="${h(f.key)}" data-i="${i}" value="${h(it)}" autocomplete="off">
        <button class="ef-rm" data-act="list-del" data-key="${h(f.key)}" data-i="${i}" aria-label="Remove" title="Remove">×</button></div>`).join('')}
      <button class="ef-add" data-act="list-add" data-key="${h(f.key)}">+ Add</button></div>`;
  }

  // Derived fields: shown when they have something to show. Several empty ones collapse into
  // a single line, so a new plot doesn't open with seven "None yet".
  function derivedBlock() {
    const fs = S.spec.fields.filter((f) => f.kind === 'computed');
    const rowsOf = (f) => (S.orig.computed || {})[f.key] || [];
    const full = fs.filter((f) => rowsOf(f).length), empty = fs.filter((f) => !rowsOf(f).length);
    const one = (f) => `<div class="ef-field"><div class="ef-label">${h(f.label)}</div>
      <div class="ef-ro${rowsOf(f).length ? '' : ' none'}">${rowsOf(f).length ? rowsOf(f).map((r) => `<div>${h(r.display)}</div>`).join('') : 'None yet'}</div>
      ${f.hint ? `<div class="ef-note">${h(f.hint)}</div>` : ''}</div>`;
    let html = full.map(one).join('');
    if (empty.length === 1 && !full.length) html = one(empty[0]);
    else if (empty.length) {
      const hints = [...new Set(empty.map((f) => f.hint).filter(Boolean))];
      html += `<div class="ef-field"><div class="ef-label">Not used yet</div>
        <div class="ef-ro none">${empty.map((f) => h(f.label)).join(' · ')}</div>
        ${hints.length === 1 ? `<div class="ef-note">${h(hints[0])}</div>` : ''}</div>`;
    }
    return html;
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
      if (f.kind === 'perspectives') { const r = persDiff(f, a[f.key] || {}, b[f.key] || {}); was = r[0]; now = r[1]; }
      else if (f.kind === 'list' || f.kind === 'reflist' || f.kind === 'repeater') {
        const rec = (r) => f.fields.map((sf) => sf.kind === 'ref' ? (r[sf.key] ? refName(sf.ref, r[sf.key]) : '')
          : sf.kind === 'select' ? ((sf.option_labels || {})[r[sf.key]] || r[sf.key]) : r[sf.key]).filter(Boolean).join(' · ');
        const items = (v) => f.kind === 'repeater' ? (v || []).map((r) => [JSON.stringify(r), rec(r)])
          : (v || []).map((i) => [i, f.kind === 'reflist' ? refName(f.ref, i) : i]);
        const x = items(a[f.key]), y = items(b[f.key]);
        const xs = x.map((i) => i[0]), ys = y.map((i) => i[0]);
        was = x.length ? x.map(([id, n]) => ys.includes(id) ? h(n) : `<span class="del">${h(n)}</span>`).join('<br>') : '—';
        now = y.length ? y.map(([id, n]) => xs.includes(id) ? h(n) : `<span class="add">${h(n)}</span>`).join('<br>') : '—';
      } else { was = h(fmtScalar(f, a[f.key])); now = h(fmtScalar(f, b[f.key])); }
      rows.push(diff(f.label, was, now));
    });
    changedSections().forEach((n) => rows.push(diff(n, h(clip(S.orig.sections[n])), h(clip(S.sections[n])))));
    const banner = S.conflict
      ? `<div class="ef-banner info on">This was changed since you opened it — probably by the agent.
         <button class="btn" data-act="rebase">Apply my edits on top of the latest</button></div>` : '';
    return `${banner}<div class="ef-sub">Check what will change in “${h(S.values[nameKey()] || S.id)}”.</div>${rows.join('') || '<div class="ef-sub">Nothing changed.</div>'}`;
  }
  // Only the card fields that changed, one line each, "Kael · Label: Friend".
  function persDiff(f, before, after) {
    const was = [], now = [];
    Object.keys(Object.assign({}, before, after)).forEach((cid) => {
      const x = before[cid], y = after[cid], who = entityName(f.ref, cid);
      f.fields.forEach((sf) => {
        const xv = x ? x[sf.key] : '', yv = y ? y[sf.key] : '';
        if (eq(xv, yv)) return;
        const show = (v) => sf.kind === 'toggle' ? (v ? 'yes' : 'no') : (v === '' || v == null ? '—' : String(v));
        const lab = sf.kind === 'toggle' ? 'Hidden' : sf.label;
        was.push(x ? `${h(who)} · ${h(lab)}: ${h(show(xv))}` : '—');
        now.push(y ? `<span class="add">${h(who)} · ${h(lab)}: ${h(show(yv))}</span>` : `<span class="del">${h(who)} removed</span>`);
      });
    });
    return [was.join('<br>') || '—', now.join('<br>') || '—'];
  }
  const diff = (label, was, now) => `<div class="ef-diff"><div class="ef-diff-h">${h(label)}</div>
    <div class="ef-diff-b"><div class="was">${was}</div><div class="now">${now}</div></div></div>`;

  // ─── Delete ──────────────────────────────────────────────────────────────
  function deleteHtml() {
    const p = S.preview;
    if (!p) return '<div class="ef-sub">Checking what this affects…</div>';
    const list = (items) => `<ul>${items.map((i) => `<li>${h(i)}</li>`).join('')}</ul>`;
    const also = p.also_deleted.map((e) => `${e.label || e.type}: ${e.name}`);
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
    if (S.discard) return `<div class="grow">${S.discard === 'script' ? 'Discard your changes and open the script editor?' : 'Discard your changes?'}</div>
      <button class="btn btn-ghost" data-act="keep">Keep editing</button><button class="btn btn-danger" data-act="discard">${S.discard === 'script' ? 'Discard and open' : 'Discard'}</button>`;
    if (S.step === 'review') return `<button class="btn" data-act="back">Back</button><div class="grow"></div>
      <button class="btn btn-primary" data-act="confirm"${S.busy ? ' disabled' : ''}>${S.busy ? 'Saving…' : 'Confirm and save'}</button>`;
    if (S.step === 'delete') {
      const p = S.preview;
      return `<button class="btn" data-act="back">Back</button><div class="grow"></div>
        <button class="btn btn-danger" data-act="confirm-delete"${!p || !p.can_delete || S.busy ? ' disabled' : ''}>${S.busy ? 'Deleting…' : 'Delete'}</button>`;
    }
    const edit = S.mode === 'edit';
    return `${edit && !S.spec.singleton ? '<button class="btn btn-danger btn-ghost" data-act="ask-delete">Delete…</button>' : ''}<div class="grow"></div>
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

  // Errors show for a field once it's been touched, or after a save attempt; warnings always do.
  function paintMessages() {
    const show = (k) => S.submitted || S.touched.has(k);
    document.querySelectorAll('#ef-body [data-msg]').forEach((el) => {
      const k = el.dataset.msg, err = show(k) && S.errors[k], warn = !err && S.warnings[k];   // a warning is worth seeing at once
      el.textContent = err || warn || '';
      el.className = 'ef-msg' + (err ? ' err' : warn ? ' warn' : '');
      el.parentElement.querySelectorAll('.ef-input').forEach((i) => i.classList.toggle('ef-invalid', !!err));
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
    const k = key && CSS.escape(key);
    const el = key && document.querySelector(`[data-key="${k}"],[data-path="${k}"],[data-ref="${k}"]`);
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

  function reopenPanel(type, id) {
    if (PANELS[type] && D[PANELS[type]]) D[PANELS[type]](id);
    else if (PANEL_TYPES.includes(type) && D.panelTabs) D.panelTabs.openEntity(type + ':' + id);
  }

  async function finish(res, verb) {
    const type = S.type, name = res.values[nameKey()] || res.id;
    close();
    if (D.reloadData) await D.reloadData(); else location.reload();
    reopenPanel(type, res.id);
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
      case 'discard': if (S.discard === 'script') goScript(); else close(); break;
      case 'list-add': {
        const k = el.dataset.key; (S.values[k] = S.values[k] || []).push('');
        renderBody(); const rows = document.querySelectorAll(`[data-list="${CSS.escape(k)}"]`); rows[rows.length - 1].focus(); break;
      }
      case 'ref-add': {
        const k = el.dataset.key; (S.values[k] = S.values[k] || []).push('');
        renderBody(); const rows = document.querySelectorAll(`[data-ref="${CSS.escape(k)}"]`); rows[rows.length - 1].focus(); break;
      }
      case 'ref-del': {
        S.values[el.dataset.key].splice(+el.dataset.i, 1); syncPersp(); renderBody(); afterEdit(); break;
      }
      case 'rep-add': {
        const f = field(el.dataset.key); (S.values[f.key] = S.values[f.key] || []).push(newCard(f));
        renderBody(); afterEdit(); const first = document.querySelectorAll(`[data-rk="${CSS.escape(f.key)}"][data-rf="${f.fields[0].key}"]`);
        if (first.length) first[first.length - 1].focus(); break;
      }
      case 'rep-del': {
        S.values[el.dataset.key].splice(+el.dataset.i, 1); renderBody(); afterEdit(); break;
      }
      case 'open-script': if (isDirty()) { S.discard = 'script'; syncFooter(); } else goScript(); break;
      case 'list-del': {
        S.values[el.dataset.key].splice(+el.dataset.i, 1); renderBody(); afterEdit(); break;
      }
    }
  }

  function afterEdit() { scheduleCheck(); syncFooter(); paintHeader(); }

  const field = (key) => S.spec.fields.find((f) => f.key === key);
  const persField = () => S.spec.fields.find((f) => f.kind === 'perspectives');

  // Keep exactly one card per chosen entity: new picks get a blank card, dropped ones lose theirs.
  function syncPersp() {
    const f = persField(); if (!f) return;
    const ids = (S.values[f.keyed_by] || []).filter(Boolean), cur = S.values[f.key] || {}, next = {};
    ids.forEach((id) => { next[id] = cur[id] || blankPersp(); });
    S.values[f.key] = next;
  }

  // A relationship is usually named for its two people; fill it in until the person writes their own.
  function autoName() {
    const a = S.spec.auto_name; if (!a || S.mode !== 'create' || S.nameTyped) return;   // typed, not merely visited
    const f = field(a.from), ids = (S.values[a.from] || []).filter(Boolean);
    S.values[nameKey()] = ids.length && ids.length === (f.count || ids.length) ? ids.map((id) => entityName(f.ref, id)).join(a.join) : '';
  }

  function onInput(e) {
    const el = e.target, d = el.dataset;
    let rerender = false;
    if (d.key != null) {
      S.values[d.key] = el.type === 'checkbox' ? el.checked : el.value;
      S.touched.add(d.key); rerender = dependedOn(d.key);
      if (d.key === nameKey()) S.nameTyped = true;
    } else if (d.ref != null) {
      const arr = S.values[d.ref] = S.values[d.ref] || [];
      while (arr.length <= +d.i) arr.push('');
      arr[+d.i] = el.value; S.touched.add(d.ref);
      syncPersp(); autoName(); rerender = true;              // the other slot's choices and the cards depend on this
    } else if (d.rk != null) {
      S.values[d.rk][+d.ri][d.rf] = el.value; S.touched.add(d.path);
      rerender = d.rf === 'plot';                              // the other cards' choices exclude this one
    } else if (d.pc != null) {
      const f = persField(), cards = S.values[f.key] = S.values[f.key] || {};
      (cards[d.pc] = cards[d.pc] || blankPersp())[d.pf] = el.type === 'checkbox' ? el.checked : el.value;
      S.touched.add(d.path);
    } else if (d.list != null) {
      S.values[d.list][+d.i] = el.value; S.touched.add(d.list);
    } else if (d.section != null) {
      S.sections[d.section] = el.value;
    } else return;
    if (el.tagName === 'TEXTAREA') autosize(el);
    if (rerender) { const id = el.id; renderBody(); const n = id && document.getElementById(id); if (n) n.focus(); }
    afterEdit();
  }

  function onKey(e) {
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
    wrap('showPlotPanel', 'plot'); wrap('showRelationshipPanel', 'relationship');
    wrap('showScenePanel', 'scene'); wrap('showSequencePanel', 'sequence'); wrap('showActPanel', 'act');
    const open = D.openPanel, close_ = D.closePanel;
    D.openPanel = function () { const r = open.apply(this, arguments); D._formTarget = D._pendingFormTarget || null; syncEditButton(); return r; };
    D.closePanel = function () { D._formTarget = null; syncEditButton(); return close_.apply(this, arguments); };
  }

  // The project is one record that always exists; the server finds it whatever id we name.
  D.openProjectForm = function () { D.openEntityForm({ type: 'project', id: slugFromHash() }); };

  // "+ New" in the Scenes tab: three kinds of thing can be made there.
  D.openStructureMenu = function (btn) {
    if (menuEl) { closeMenu(); return; }
    menuEl = document.createElement('div'); menuEl.className = 'ef-menu';
    menuEl.innerHTML = [['scene', 'Scene', 'a scene in a sequence'], ['sequence', 'Sequence', 'a group of scenes in an act'], ['act', 'Act', 'a part of the story']]
      .map(([t, n, d]) => `<button data-new="${t}">${n}<small>${d}</small></button>`).join('');
    const r = btn.getBoundingClientRect();
    menuEl.style.top = (r.bottom + 4) + 'px'; menuEl.style.right = (window.innerWidth - r.right) + 'px';
    menuEl.addEventListener('click', (e) => { const b = e.target.closest('button'); if (!b) return; closeMenu(); D.openEntityForm({ type: b.dataset.new }); });
    document.body.appendChild(menuEl);
    setTimeout(() => document.addEventListener('click', function off(e) {
      if (menuEl && !menuEl.contains(e.target)) closeMenu();
      document.removeEventListener('click', off);
    }), 0);
  };

  // A small confirm dialog in the same style, for things that aren't a form (Reorder's review).
  //   const d = DASH.efDialog({ title, kicker, bodyHtml, confirm, onConfirm }); d.error(html); d.busy(bool); d.close();
  D.efDialog = function (o) {
    const el = document.createElement('div'); el.className = 'ef-backdrop open';
    el.innerHTML = `<div class="ef-card ef-card-sm" role="dialog" aria-modal="true" tabindex="-1">
      <div class="ef-head"><div class="ef-titles"><div class="ef-kicker">${h(o.kicker || '')}</div><div class="ef-name">${h(o.title || '')}</div></div>
        <button class="ef-x-close" data-d="close" aria-label="Close">×</button></div>
      <div class="ef-body"><div class="ef-banner" data-d="err"></div>${o.bodyHtml || ''}</div>
      <div class="ef-foot"><div class="grow"></div><button class="btn" data-d="close">${h(o.cancel || 'Cancel')}</button>
        <button class="btn btn-primary" data-d="ok">${h(o.confirm || 'OK')}</button></div></div>`;
    document.body.appendChild(el);
    const api_ = {
      close() { el.remove(); document.removeEventListener('keydown', esc, true); if (o.onClose) o.onClose(); },
      error(html) { const b = el.querySelector('[data-d=err]'); b.innerHTML = html || ''; b.className = 'ef-banner' + (html ? ' on' : ''); },
      busy(on) { const b = el.querySelector('[data-d=ok]'); b.disabled = !!on; b.textContent = on ? 'Working…' : (o.confirm || 'OK'); },
      el,
    };
    const esc = (e) => { if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); api_.close(); } };
    document.addEventListener('keydown', esc, true);
    el.addEventListener('click', (e) => {
      const t = e.target.closest('[data-d]');
      if (t && t.dataset.d === 'close' || e.target === el) api_.close();
      else if (t && t.dataset.d === 'ok' && o.onConfirm) o.onConfirm(api_);
    });
    el.querySelector('.ef-card').focus();
    return api_;
  };

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
      const k = e.target.dataset && (e.target.dataset.key || e.target.dataset.list || e.target.dataset.path || e.target.dataset.ref);
      if (k && S.open) { S.touched.add(k); paintMessages(); }
    });
    rootEl.addEventListener('keydown', onKey);
    // Escape must work wherever focus is — a re-render can drop it onto the page behind.
    document.addEventListener('keydown', (e) => {
      if (S.open && e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); requestClose(); }
    }, true);
    wrapPanels();
    const edit = document.getElementById('panel-edit');
    if (edit) edit.addEventListener('click', () => { if (D._formTarget) D.openEntityForm(D._formTarget); });
  }
  init();
})(window.DASH);
