// Reorder — move scenes between (or within) sequences, and sequences between (or within) acts.
//
// The Scenes tab's grouped list turns into draggable rows. The browser edits a COPY of the tree
// and sends the whole target shape to the server, which validates it, says in words what moves
// (`/structure/plan`), and writes it through the same path the agent uses (`/structure/apply`).
// Nothing is written until the person has read that list and confirmed.
//
// Every move has a keyboard path: ↑ ↓ within a list, and "Move to…" across lists.
window.DASH = window.DASH || {};
(function (D) {
  'use strict';

  const h = (s) => String(s == null ? '' : s).replace(/[&<>"']/g,
    (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const clone = (v) => JSON.parse(JSON.stringify(v));
  const slugFromHash = () => { const m = (location.hash || '').match(/^#\/p\/([^/?]+)/); return m ? decodeURIComponent(m[1]) : null; };
  const toast = (m, k) => { if (D.efToast) D.efToast(m, k); };

  let R = null;          // { tree, orig, version, drag, focus, moved }
  const view = () => document.getElementById('scenes-view');

  async function api(path, opts) {
    const o = Object.assign({ headers: { 'Content-Type': 'application/json', 'X-Story-Architect': '1' } }, opts || {});
    const res = await fetch('/api/projects/' + encodeURIComponent(slugFromHash()) + path, o);
    const j = await res.json().catch(() => ({}));
    if (!res.ok) { const e = new Error((j.error && j.error.message) || res.statusText); e.status = res.status; e.body = j.error || {}; throw e; }
    return j;
  }

  // ─── The working copy ────────────────────────────────────────────────────
  const shape = (tree) => tree.acts.map((a) => ({ id: a.id, sequences: a.sequences.map((q) => ({ id: q.id, scenes: q.scenes.map((s) => s.id) })) }));
  const dirty = () => !!R && JSON.stringify(shape(R.tree)) !== JSON.stringify(shape(R.orig));

  function find(kind, id) {
    if (kind === 'act') return { list: R.tree.acts, i: R.tree.acts.findIndex((a) => a.id === id), parent: null };
    for (const a of R.tree.acts) {
      if (kind === 'sequence') { const i = a.sequences.findIndex((q) => q.id === id); if (i >= 0) return { list: a.sequences, i, parent: a.id }; }
      else for (const q of a.sequences) { const i = q.scenes.findIndex((s) => s.id === id); if (i >= 0) return { list: q.scenes, i, parent: q.id }; }
    }
    if (kind === 'scene') return { list: R.tree.unassigned, i: R.tree.unassigned.findIndex((s) => s.id === id), parent: '_unassigned' };
    return null;
  }

  function listOf(kind, parentId) {
    if (kind === 'act') return R.tree.acts;
    if (kind === 'sequence') return (R.tree.acts.find((a) => a.id === parentId) || {}).sequences;
    for (const a of R.tree.acts) { const q = a.sequences.find((x) => x.id === parentId); if (q) return q.scenes; }
    return null;
  }

  // `index` is a position in the destination list as it is BEFORE the item is lifted out.
  function moveTo(kind, id, parentId, index) {
    const from = find(kind, id), dest = listOf(kind, parentId);
    if (!from || !dest) return;
    const [item] = from.list.splice(from.i, 1);
    let idx = index === 'end' ? dest.length : index;
    if (dest === from.list && idx > from.i) idx -= 1;
    dest.splice(Math.max(0, Math.min(idx, dest.length)), 0, item);
    R.moved.add(id);
  }

  // ─── Render ──────────────────────────────────────────────────────────────
  const grip = '<span class="ro-grip" aria-hidden="true">⋮⋮</span>';
  const btn = (ro, kind, id, label, glyph, off) => `<button class="ro-btn" data-ro="${ro}" data-kind="${kind}" data-id="${h(id)}" aria-label="${label}" title="${label}"${off ? ' disabled' : ''}>${glyph}</button>`;

  function sequenceOptions(curSeq) {
    return '<option value="">Move to…</option>' + R.tree.acts.map((a) => {
      const opts = a.sequences.filter((q) => q.id !== curSeq).map((q) => `<option value="${h(q.id)}">${h(q.title)}</option>`).join('');
      return opts ? `<optgroup label="${h(a.title)}">${opts}</optgroup>` : '';
    }).join('');
  }
  const actOptions = (curAct) => '<option value="">Move to…</option>'
    + R.tree.acts.filter((a) => a.id !== curAct).map((a) => `<option value="${h(a.id)}">${h(a.title)}</option>`).join('');

  function sceneRow(s, i, n, inSeq) {
    const moved = R.moved.has(s.id) ? ' ro-moved' : '';
    return `<div class="ro-scene${moved}" draggable="true" data-kind="scene" data-id="${h(s.id)}">
      ${grip}${inSeq ? `<span class="ro-num">${i + 1}</span>` : ''}
      <span class="ro-title">${h(s.title)}</span>${s.heading ? `<span class="ro-sub">${h(s.heading)}</span>` : ''}
      <span class="ro-ctl">${inSeq ? btn('up', 'scene', s.id, 'Move up', '↑', i === 0) + btn('down', 'scene', s.id, 'Move down', '↓', i === n - 1) : ''}
        <select class="ro-select" data-ro="moveto" data-kind="scene" data-id="${h(s.id)}" aria-label="Move ${h(s.title)} to">${sequenceOptions(inSeq ? find('scene', s.id).parent : null)}</select></span></div>`;
  }

  function render() {
    const list = document.getElementById('scene-list'); if (!list) return;
    list.innerHTML = R.tree.acts.map((a, ai) => `<div class="ro-act" data-actblock="${h(a.id)}">
      <div class="ro-head ro-act-h${R.moved.has(a.id) ? ' ro-moved' : ''}" draggable="true" data-kind="act" data-id="${h(a.id)}">${grip}
        <span class="ro-title">${h(a.title)}</span>
        <span class="ro-ctl">${btn('up', 'act', a.id, 'Move act up', '↑', ai === 0)}${btn('down', 'act', a.id, 'Move act down', '↓', ai === R.tree.acts.length - 1)}</span></div>
      <div class="ro-children">${a.sequences.length ? a.sequences.map((q, qi) => `<div class="ro-seq" data-seqblock="${h(q.id)}">
          <div class="ro-head ro-seq-h${R.moved.has(q.id) ? ' ro-moved' : ''}" draggable="true" data-kind="sequence" data-id="${h(q.id)}">${grip}
            <span class="ro-title">${h(q.title)}</span>
            <span class="ro-ctl">${btn('up', 'sequence', q.id, 'Move sequence up', '↑', qi === 0)}${btn('down', 'sequence', q.id, 'Move sequence down', '↓', qi === a.sequences.length - 1)}
              <select class="ro-select" data-ro="moveto" data-kind="sequence" data-id="${h(q.id)}" aria-label="Move ${h(q.title)} to act">${actOptions(a.id)}</select></span></div>
          <div class="ro-children">${q.scenes.length ? q.scenes.map((s, si) => sceneRow(s, si, q.scenes.length, true)).join('')
            : `<div class="ro-empty" data-drop="seq" data-id="${h(q.id)}">No scenes — drop one here</div>`}</div></div>`).join('')
        : `<div class="ro-empty" data-drop="act" data-id="${h(a.id)}">No sequences — drop one here</div>`}</div></div>`).join('')
      + (R.tree.unassigned.length ? `<div class="ro-unassigned-h">Unassigned</div><div class="ro-children" style="margin-left:0">${R.tree.unassigned.map((s) => sceneRow(s, 0, 0, false)).join('')}</div>` : '');
    if (R.focus) {
      const f = R.focus;
      const el = list.querySelector(`[data-ro="${f.ro}"][data-id="${CSS.escape(f.id)}"]:not([disabled])`)
        || list.querySelector(`[data-ro="${f.ro === 'up' ? 'down' : 'up'}"][data-id="${CSS.escape(f.id)}"]:not([disabled])`);
      if (el) el.focus();
      R.focus = null;
    }
    const review = document.getElementById('reorder-review'); if (review) review.disabled = !dirty();
  }

  // ─── Events ──────────────────────────────────────────────────────────────
  function onClick(e) {
    const b = e.target.closest('[data-ro=up],[data-ro=down]'); if (!R || !b) return;
    const { kind, id } = b.dataset, f = find(kind, id), step = b.dataset.ro === 'up' ? -1 : 1;
    if (!f) return;
    moveTo(kind, id, f.parent, step < 0 ? f.i - 1 : f.i + 2);     // +2: "after the next one", measured before lifting
    R.focus = { ro: b.dataset.ro, id }; render();
  }

  function onChange(e) {
    const s = e.target.closest('[data-ro=moveto]'); if (!R || !s || !s.value) return;
    moveTo(s.dataset.kind, s.dataset.id, s.value, 'end'); render();
  }

  // Where a drop would land. Over a row: before or after it, by which half the cursor is in.
  // Over a header or an empty slot: into that parent, at the start.
  function dropSpec(e) {
    const d = R && R.drag; if (!d) return null;
    const t = e.target;
    const half = (el) => { const r = el.getBoundingClientRect(); return e.clientY < r.top + r.height / 2; };
    if (d.kind === 'scene') {
      const row = t.closest('.ro-scene'), head = t.closest('.ro-seq-h'), slot = t.closest('[data-drop=seq]');
      if (row) { const f = find('scene', row.dataset.id); if (f.parent === '_unassigned') return null; const up = half(row); return { el: row, parent: f.parent, index: f.i + (up ? 0 : 1), cls: up ? 'before' : 'after' }; }
      if (head) return { el: head, parent: head.dataset.id, index: 0, cls: 'into' };
      if (slot) return { el: slot, parent: slot.dataset.id, index: 0, cls: 'into' };
    } else if (d.kind === 'sequence') {
      const block = t.closest('[data-seqblock]'), head = t.closest('.ro-act-h'), slot = t.closest('[data-drop=act]');
      if (block) { const f = find('sequence', block.dataset.seqblock), up = half(block); return { el: block, parent: f.parent, index: f.i + (up ? 0 : 1), cls: up ? 'before' : 'after' }; }
      if (head) return { el: head, parent: head.dataset.id, index: 0, cls: 'into' };
      if (slot) return { el: slot, parent: slot.dataset.id, index: 0, cls: 'into' };
    } else if (d.kind === 'act') {
      const block = t.closest('[data-actblock]');
      if (block) { const f = find('act', block.dataset.actblock), up = half(block); return { el: block, parent: null, index: f.i + (up ? 0 : 1), cls: up ? 'before' : 'after' }; }
    }
    return null;
  }

  const clearMarks = () => document.querySelectorAll('.ro-drop-before,.ro-drop-after,.ro-drop-into')
    .forEach((n) => n.classList.remove('ro-drop-before', 'ro-drop-after', 'ro-drop-into'));

  function onDragStart(e) {
    const el = e.target.closest('[data-kind][draggable=true]'); if (!R || !el) return;
    R.drag = { kind: el.dataset.kind, id: el.dataset.id };
    e.dataTransfer.effectAllowed = 'move'; e.dataTransfer.setData('text/plain', R.drag.kind + ':' + R.drag.id);
    setTimeout(() => el.classList.add('ro-dragging'), 0);
  }
  function onDragOver(e) {
    if (!R || !R.drag) return;
    const spec = dropSpec(e); clearMarks();
    if (!spec) return;
    e.preventDefault(); e.dataTransfer.dropEffect = 'move';
    spec.el.classList.add('ro-drop-' + spec.cls);
  }
  function onDrop(e) {
    if (!R || !R.drag) return;
    const spec = dropSpec(e); clearMarks();
    if (!spec) return;
    e.preventDefault();
    moveTo(R.drag.kind, R.drag.id, spec.parent, spec.index); R.drag = null; render();
  }
  function onDragEnd() { if (R) R.drag = null; clearMarks(); document.querySelectorAll('.ro-dragging').forEach((n) => n.classList.remove('ro-dragging')); }

  // ─── Enter / leave ───────────────────────────────────────────────────────
  D.reorderActive = () => !!R;

  function leave(redraw) {
    R = null;
    const v = view(); if (v) v.classList.remove('reordering');
    if (redraw && D.renderSceneList) D.renderSceneList(D.allScenes || []);
  }
  D.reorderExit = () => { if (R) leave(false); };

  function start(tree) {
    R = { tree: clone(tree), orig: clone(tree), version: tree.version, drag: null, focus: null, moved: new Set() };
    const search = document.getElementById('scene-search'); if (search) search.value = '';
    view().classList.add('reordering'); render();
  }

  D.toggleReorder = async function () {
    if (R) return;
    try { start(await api('/structure')); } catch (e) { toast(e.message, 'bad'); }
  };

  D.reorderCancel = function () {
    if (!R) return;
    if (!dirty()) { leave(true); return; }
    D.efDialog({ kicker: 'Reorder', title: 'Discard the new order?', bodyHtml: '<div class="ef-sub">Nothing has been saved yet.</div>',
      confirm: 'Discard', cancel: 'Keep editing', onConfirm: (d) => { d.close(); leave(true); } });
  };

  function conflict() {
    D.efDialog({ kicker: 'Reorder', title: 'The story changed', confirm: 'Reload Reorder', cancel: 'Close',
      bodyHtml: '<div class="ef-sub">Something was added, removed or moved since you opened Reorder — probably by the agent. Your arrangement can’t be applied safely, so it needs to start again from the current order.</div>',
      onConfirm: async (d) => { d.close(); try { start(await api('/structure')); } catch (e) { toast(e.message, 'bad'); } } });
  }

  D.reorderReview = async function () {
    if (!R || !dirty()) return;
    const body = JSON.stringify({ base_version: R.version, acts: shape(R.tree) });
    let plan;
    try { plan = await api('/structure/plan', { method: 'POST', body }); }
    catch (e) { if (e.status === 409) conflict(); else toast(e.message, 'bad'); return; }
    if (plan.unchanged) { toast('Nothing to change'); return; }
    const n = plan.changes.length;
    D.efDialog({
      kicker: 'Reorder', title: `Apply ${n} change${n === 1 ? '' : 's'}?`, confirm: 'Apply order',
      bodyHtml: `<ul class="ef-moves">${plan.changes.map((c) => `<li>${h(c.text)}</li>`).join('')}</ul>
        <div class="ef-note">Scene numbers and the script follow the new order. Scripts themselves are not changed.</div>`,
      onConfirm: async (d) => {
        d.busy(true);
        try {
          D._ownWriteUntil = Date.now() + 8000;
          await api('/structure/apply', { method: 'POST', body });
          d.close(); leave(false);
          if (D.reloadData) await D.reloadData();
          toast(`Order saved · ${n} change${n === 1 ? '' : 's'}`);
        } catch (e) {
          d.close();
          if (e.status === 409) conflict(); else { toast(e.message, 'bad'); }
        }
      },
    });
  };

  function init() {
    const list = document.getElementById('scene-list'); if (!list) return;
    list.addEventListener('click', onClick);
    list.addEventListener('change', onChange);
    list.addEventListener('dragstart', onDragStart);
    list.addEventListener('dragover', onDragOver);
    list.addEventListener('drop', onDrop);
    list.addEventListener('dragend', onDragEnd);
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && R && !document.querySelector('.ef-backdrop.open')) { e.preventDefault(); D.reorderCancel(); }
    });
  }
  init();
})(window.DASH);
