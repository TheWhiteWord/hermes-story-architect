window.DASH = window.DASH || {};

// The projects page: every project, and for each one its drafts, branches and graph.
// The render functions are pure (state in, markup out) so tests/projects_harness.js can
// run them for real; the controller below them owns the fetches and the dialogs.
(function (D) {
  const esc = (s) => String(s == null ? '' : s)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  const plural = (n, w) => n + ' ' + w + (n === 1 ? '' : /(ch|sh|s|x)$/.test(w) ? 'es' : 's');

  function ago(iso, now) {
    const t = Date.parse(iso);
    if (isNaN(t)) return '';
    const s = Math.max(0, ((now || Date.now()) - t) / 1000);
    if (s < 60) return 'just now';
    if (s < 3600) return plural(Math.floor(s / 60), 'min') + ' ago';
    if (s < 86400) return plural(Math.floor(s / 3600), 'hour') + ' ago';
    if (s < 86400 * 14) return plural(Math.floor(s / 86400), 'day') + ' ago';
    return new Date(t).toLocaleDateString();
  }

  function metaText(p, now) {
    if (!p.has_db) return 'No story database yet';
    if (!p.branch_count) return 'No drafts saved yet';
    const where = [p.current_branch, p.current_draft].filter(Boolean).join(' · ');
    return where + ' · ' + plural(p.branch_count, 'branch') + (p.last_saved ? ' · saved ' + ago(p.last_saved, now) : '');
  }

  function chip(p) {
    if (!p.has_db || !p.branch_count) return '';
    return p.changes_since_save > 0
      ? '<span class="pj-chip changed">' + esc(plural(p.changes_since_save, 'change') + ' since ' + (p.current_draft || 'save')) + '</span>'
      : '<span class="pj-chip">up to date</span>';
  }

  const link = (r, label) => '<a class="btn" href="' + esc(D.draftsCommon.href(r)) + '">' + esc(label) + '</a>';
  const btn = (act, label, attrs, cls) => '<button class="btn ' + (cls || '') + '" data-act="' + act + '"' + (attrs || '') + '>' + esc(label) + '</button>';
  const attr = (k, v) => ' data-' + k + '="' + esc(v) + '"';

  function branchRows(slug, s) {
    const cur = s.branches.find((b) => b.is_current);
    const baseLabel = {};
    s.snapshots.forEach((d) => { baseLabel[d.id] = d.label; });
    return s.branches.map((b) => {
      const h = (s.head || {})[b.id] || {};
      const state = h.changed ? plural(h.changes, 'change') + ' since ' + (baseLabel[b.base_snapshot_id] || 'its draft') : 'no changes since ' + (baseLabel[b.base_snapshot_id] || 'its draft');
      return '<div class="pj-row" data-row="branch:' + esc(b.id) + '">'
        + '<div class="pj-row-main"><span class="pj-row-name">' + esc(b.name) + '</span>'
        + (b.is_current ? ' <span class="pj-chip current">current</span>' : '')
        + '<div class="pj-row-sub' + (h.changed ? ' changed' : '') + '">Open draft: ' + esc(state) + '</div></div>'
        + '<div class="pj-row-actions">'
        + (b.is_current ? btn('open', 'Open', attr('slug', slug), 'btn-primary') : btn('switch', 'Switch and open', attr('slug', slug) + attr('id', b.id), 'btn-primary'))
        + link({ kind: 'read', slug, ref: 'branch:' + b.id }, 'Read')
        + link(b.is_current ? { kind: 'compare', slug, a: 'snapshot:' + b.base_snapshot_id, b: 'branch:' + b.id } : { kind: 'compare', slug, a: 'branch:' + b.id, b: 'branch:' + (cur ? cur.id : b.id) }, 'Compare')
        + btn('rename', 'Rename', attr('slug', slug) + attr('id', b.id) + attr('name', b.name))
        + btn('delete-branch', 'Delete', attr('slug', slug) + attr('id', b.id) + attr('name', b.name) + (b.is_current ? ' disabled title="Switch to another branch first."' : ''))
        + '</div></div>';
    }).join('');
  }

  function draftRows(slug, s, now) {
    const cur = s.branches.find((b) => b.is_current);
    const branchName = {};
    const baseOf = {};
    s.branches.forEach((b) => { branchName[b.id] = b.name; baseOf[b.base_snapshot_id] = b.name; });
    return s.snapshots.slice().reverse().map((d) => {
      const pinned = baseOf[d.id];
      return '<div class="pj-row" data-row="snapshot:' + esc(d.id) + '">'
        + '<div class="pj-row-main"><span class="pj-row-name">' + esc(d.label) + '</span> <span class="pj-chip">' + esc(branchName[d.branch_id] || 'deleted branch') + '</span>'
        + '<div class="pj-row-sub">' + esc(ago(d.created_at, now)) + (d.note ? ' · ' + esc(d.note) : '') + '</div></div>'
        + '<div class="pj-row-actions">'
        + link({ kind: 'read', slug, ref: 'snapshot:' + d.id }, 'Read')
        + link({ kind: 'compare', slug, a: 'snapshot:' + d.id, b: 'branch:' + (cur ? cur.id : '') }, 'Compare')
        + btn('branch', 'Branch from here', attr('slug', slug) + attr('id', d.id) + attr('name', d.label))
        + btn('delete-draft', 'Delete', attr('slug', slug) + attr('id', d.id) + attr('name', d.label) + (pinned ? ' disabled title="' + esc('Where the open draft of ' + pinned + ' starts.') + '"' : ''))
        + '</div></div>';
    }).join('');
  }

  function historyHtml(slug, s, now) {
    if (!s.branches.length) {
      return '<p class="pj-empty">No drafts yet. Saving one records the project as it is now; from then on you can branch from it, compare drafts and merge them.</p>'
        + '<div class="pj-actions">' + btn('save', 'Save first draft', attr('slug', slug), 'btn-primary') + '</div>';
    }
    const cur = s.branches.find((b) => b.is_current);
    const h = cur && (s.head || {})[cur.id];
    const unchanged = h && !h.changed;
    return '<div class="pj-actions">'
      + btn('save', 'Save draft', attr('slug', slug) + (unchanged ? ' disabled title="Nothing has changed since the last draft."' : ''), 'btn-primary')
      + '<span class="pj-hint">Saves the open draft of ' + esc(cur ? cur.name : 'the current branch') + '.</span></div>'
      + '<div class="pj-graph">' + D.historyGraph.svg(s) + '</div>'
      + '<h3 class="pj-sub">Branches</h3>' + branchRows(slug, s)
      + '<h3 class="pj-sub">Drafts</h3>' + draftRows(slug, s, now);
  }

  function cardHtml(p, st, now) {
    const open = !!(st && st.open);
    const h = st && st.hist;
    let body = '';
    if (open) {
      if (!h || h.state === 'loading') body = '<p class="pj-empty">Loading history…</p>';
      else if (h.state === 'error') body = '<p class="pj-empty bad">' + esc(h.message) + '</p>';
      else body = historyHtml(p.slug, h.data, now);
    }
    const id = 'pj-body-' + p.slug.replace(/[^a-z0-9_-]/gi, '_');
    return '<section class="pj-card' + (open ? ' open' : '') + '" data-slug="' + esc(p.slug) + '">'
      + '<div class="pj-head"><button class="pj-toggle" data-act="toggle"' + attr('slug', p.slug) + ' aria-expanded="' + open + '" aria-controls="' + id + '">'
      + '<span class="pj-chev" aria-hidden="true"></span><span class="pj-name">' + esc(p.name || p.slug) + '</span></button>'
      + '<span class="pj-meta">' + esc(metaText(p, now)) + '</span>' + chip(p)
      + '<button class="btn btn-primary" data-act="open"' + attr('slug', p.slug) + (p.has_db ? '' : ' disabled') + '>Open</button></div>'
      + (open ? '<div class="pj-body" id="' + id + '">' + body + '</div>' : '')
      + '</section>';
  }

  function pageHtml(projects, state, now) {
    const list = projects.length
      ? projects.map((p) => cardHtml(p, state[p.slug], now)).join('')
      : '<p class="pj-empty">No projects found. Create one under projects/.</p>';
    return '<div class="pj-inner"><header class="pj-top"><img src="icons/favicon.svg" width="26" height="26" alt=""><h1>Projects</h1></header>' + list + '</div>';
  }

  D.projectsRender = { ago, metaText, cardHtml, historyHtml, pageHtml };

  if (typeof document === 'undefined') return;

  // ─── controller ───────────────────────────────────────────────────────────

  const S = { projects: [], state: {} };
  const pageEl = () => document.getElementById('projects-page');
  const stateOf = (slug) => (S.state[slug] = S.state[slug] || { open: false, hist: null });
  const toast = (m, kind) => (D.efToast ? D.efToast(m, kind) : console.warn(m));

  const ctx = { projectName: (slug) => (S.projects.find((p) => p.slug === slug) || {}).name || slug };

  // The projects page has three faces, chosen by the hash: the list, a draft to read, and
  // two drafts to compare. Leaving a sub-page re-reads the list, since drafts may have
  // been saved or switched in between.
  async function route() {
    const el = pageEl();
    if (!el) return;
    const r = D.draftsCommon.parse(location.hash);
    if (r.kind === 'read') { D.reader.show(el, r, ctx); return; }
    if (r.kind === 'compare') { D.compare.show(el, r, ctx); return; }
    if (r.kind === 'merge') { D.merge.show(el, r, ctx); return; }
    el.onclick = null;
    el.onchange = null;
    try { await loadList(); } catch (e) { /* the cards keep what they had */ }
    render();
    S.projects.filter((p) => stateOf(p.slug).open).forEach((p) => loadHistory(p.slug));
  }

  function render() {
    const el = pageEl();
    if (!el) return;
    const top = el.scrollTop;
    el.innerHTML = pageHtml(S.projects, S.state, Date.now());
    el.scrollTop = top;
    // A graph opens at its newest drafts and keeps wherever the reader scrolled it to.
    el.querySelectorAll('.pj-card').forEach((card) => {
      const sc = card.querySelector('.hg-scroll');
      const x = stateOf(card.dataset.slug).graphX;
      if (sc) sc.scrollLeft = x == null ? sc.scrollWidth : x;
    });
  }

  async function loadList() {
    const res = await fetch('/api/projects');
    S.projects = (await res.json()).projects || [];
  }

  async function loadHistory(slug) {
    const st = stateOf(slug);
    if (!st.hist || st.hist.state !== 'ready') { st.hist = { state: 'loading' }; render(); }
    try {
      st.hist = { state: 'ready', data: await D.historyApi(slug, 'GET', '/') };
    } catch (e) {
      st.hist = { state: 'error', message: e.message };
    }
    render();
  }

  async function refresh(slug) {
    try { await loadList(); } catch (e) { /* the cards keep what they had */ }
    await loadHistory(slug);
  }

  const historyOf = (slug) => { const h = stateOf(slug).hist; return h && h.state === 'ready' ? h.data : null; };
  const { field, val, checked, attempt } = D.historyDialogs;

  function saveDialog(slug) {
    const data = historyOf(slug);
    const cur = data && data.branches.find((b) => b.is_current);
    const next = cur ? Math.max.apply(null, [0].concat(data.snapshots.filter((s) => s.branch_id === cur.id).map((s) => s.seq))) + 1 : 1;
    D.historyDialogs.saveDraft({ slug, branchName: cur ? cur.name : null, next, onSaved: () => refresh(slug) });
  }

  function branchDialog(slug, snapshotId, label) {
    D.efDialog({
      kicker: 'Branch', title: 'Branch from “' + label + '”', confirm: 'Create branch',
      bodyHtml: field('Branch name', '<input class="ef-input" data-f="name" maxlength="60" placeholder="e.g. darker ending">', 'Where this draft goes next. The draft itself never changes.')
        + '<label class="pj-check"><input type="checkbox" data-f="open" checked> Switch to the new branch and open it</label>',
      onConfirm: async (dlg) => {
        const name = val(dlg, 'name');
        if (!name) { dlg.error('Give the branch a name.'); return; }
        let made;
        const ok = await attempt(dlg, async () => {
          made = await D.historyApi(slug, 'POST', '/branches', { snapshot: snapshotId, name });
          if (checked(dlg, 'open')) await D.historyApi(slug, 'POST', '/switch', { branch: made.id, confirm: true });
        });
        if (!ok) return;
        dlg.close();
        if (checked(dlg, 'open')) D.openProject(slug); else { toast('Created “' + name + '”.'); refresh(slug); }
      },
    }).el.querySelector('[data-f="name"]').focus();
  }

  function renameDialog(slug, branchId, name) {
    const d = D.efDialog({
      kicker: 'Rename', title: 'Rename “' + name + '”', confirm: 'Rename',
      bodyHtml: field('Branch name', '<input class="ef-input" data-f="name" maxlength="60" value="' + esc(name) + '">', 'Only the label changes; the drafts do not move.'),
      onConfirm: async (dlg) => {
        const next = val(dlg, 'name');
        if (!next) { dlg.error('Give the branch a name.'); return; }
        if (await attempt(dlg, () => D.historyApi(slug, 'PATCH', '/branches/' + encodeURIComponent(branchId), { name: next }))) { dlg.close(); refresh(slug); }
      },
    });
    const el = d.el.querySelector('[data-f="name"]'); el.focus(); el.select();
  }

  function deleteDialog(slug, kind, id, name) {
    const branch = kind === 'branch';
    D.efDialog({
      kicker: 'Delete', title: 'Delete ' + (branch ? 'branch' : 'draft') + ' “' + name + '”?', confirm: 'Delete',
      bodyHtml: '<p class="pj-dlg">' + (branch
        ? 'Its open draft is discarded, and so is every draft that only this branch reaches. Drafts another branch reaches stay.'
        : 'Drafts built on it are kept and join its parent, so the history stays connected. A later merge may find a less exact common ancestor and show more conflicts.')
        + ' This cannot be undone.</p>',
      onConfirm: async (dlg) => {
        const path = (branch ? '/branches/' : '/snapshots/') + encodeURIComponent(id);
        if (await attempt(dlg, () => D.historyApi(slug, 'DELETE', path, { confirm: true }))) {
          dlg.close(); toast('Deleted “' + name + '”.'); refresh(slug);
        }
      },
    });
  }

  async function switchAndOpen(slug, branchId) {
    try {
      await D.historyApi(slug, 'POST', '/switch', { branch: branchId, confirm: true });
      D.openProject(slug);
    } catch (e) { toast(e.message, 'bad'); }
  }

  function flash(key) {
    const row = Array.prototype.find.call(pageEl().querySelectorAll('[data-row]'), (r) => r.dataset.row === key);
    if (!row) return;
    row.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
    row.classList.add('pj-flash');
    setTimeout(() => row.classList.remove('pj-flash'), 1400);
  }

  function onClick(e) {
    const node = e.target.closest('.hg-node');
    if (node) { flash(node.dataset.snapshot ? 'snapshot:' + node.dataset.snapshot : 'branch:' + node.dataset.branch); return; }
    const t = e.target.closest('[data-act]');
    if (!t || t.disabled) return;
    const { act, slug, id, name } = t.dataset;
    if (act === 'toggle') {
      const st = stateOf(slug);
      st.open = !st.open;
      if (st.open) loadHistory(slug); else render();
    } else if (act === 'open') D.openProject(slug);
    else if (act === 'switch') switchAndOpen(slug, id);
    else if (act === 'save') saveDialog(slug);
    else if (act === 'branch') branchDialog(slug, id, name);
    else if (act === 'rename') renameDialog(slug, id, name);
    else if (act === 'delete-branch') deleteDialog(slug, 'branch', id, name);
    else if (act === 'delete-draft') deleteDialog(slug, 'draft', id, name);
  }

  D.showPicker = async function () {
    try {
      await loadList();
      await D.hideLoading();   // the splash draws out before it is replaced
      const app = document.getElementById('app');
      if (!app) return;
      app.innerHTML = '<div id="projects-page"></div>';
      pageEl().addEventListener('click', onClick);
      pageEl().addEventListener('scroll', (e) => {
        const card = e.target.closest && e.target.closest('.pj-card');
        if (card && e.target.classList.contains('hg-scroll')) stateOf(card.dataset.slug).graphX = e.target.scrollLeft;
      }, true);
      window.addEventListener('hashchange', route);
      await route();
      // The draft chip in the writing view sends you here with its project's history open.
      let ask = null;
      try { ask = sessionStorage.getItem('ww:expand'); sessionStorage.removeItem('ww:expand'); } catch (e) { /* private mode */ }
      if (ask && S.projects.some((p) => p.slug === ask)) { stateOf(ask).open = true; loadHistory(ask); }
    } catch (e) {
      D.showError();
    }
  };
})(window.DASH);
