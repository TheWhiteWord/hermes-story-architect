window.DASH = window.DASH || {};

// Reading a saved draft (or a branch's open draft) without opening it: its screenplay and
// its entities, with nothing to edit. `html` is pure; `show` loads and wires it.
(function (D) {
  const C = D.draftsCommon;
  const esc = C.esc;

  function entityName(e) {
    const f = (e && e.fields) || {};
    return f.name || f.title || (e && e.id) || '';
  }

  function detailHtml(e, name) {
    if (!e) return '<p class="pj-empty">Pick an entity to read it.</p>';
    const fields = Object.keys(e.fields || {}).filter((k) => k !== 'type' && k !== 'name' && k !== 'title');
    const shown = fields.filter((k) => { const v = e.fields[k]; return !(v == null || v === '' || (Array.isArray(v) && !v.length)); });
    const secs = Object.keys(e.sections || {}).filter((h) => String(e.sections[h] || '').trim());
    return '<h2 class="dr-name">' + esc(entityName(e)) + '</h2><span class="pj-chip">' + esc(C.typeWord(e.type)) + '</span>'
      + (shown.length ? '<dl class="dr-fields">' + shown.map((k) => '<dt>' + esc(C.keyLabel(k)) + '</dt><dd>' + C.fmtValue(e.fields[k], name) + '</dd>').join('') + '</dl>' : '')
      + secs.map((h) => '<h3 class="pj-sub">' + esc(h) + '</h3><div class="dr-sec">' + esc(e.sections[h]) + '</div>').join('')
      + (!shown.length && !secs.length ? '<p class="pj-empty">Nothing written yet.</p>' : '');
  }

  function listHtml(m) {
    const groups = {};
    m.entities.forEach((e) => { (groups[e.type] = groups[e.type] || []).push(e); });
    return Object.keys(groups).sort((a, b) => C.typeRank(a) - C.typeRank(b)).map((t) =>
      '<h3 class="pj-sub">' + esc(C.typeLabel(t)) + ' · ' + groups[t].length + '</h3>'
      + groups[t].map((e) => {
        const on = m.selected && m.selected.id === e.id && m.selected.type === e.type;
        return '<button class="dr-item' + (on ? ' on' : '') + '" data-rd="pick" data-type="' + esc(e.type) + '" data-id="' + esc(e.id) + '"' + (on ? ' aria-current="true"' : '') + '>' + esc(e.name) + '</button>';
      }).join('')).join('');
  }

  function html(m) {
    const byId = {};
    m.entities.forEach((e) => { byId[e.id] = e.name; });
    const name = (id) => byId[id];
    const tab = (id, label) => '<button class="dr-tab' + (m.tab === id ? ' on' : '') + '" role="tab" aria-selected="' + (m.tab === id) + '" data-rd="tab" data-tab="' + id + '">' + label + '</button>';
    const body = m.tab === 'script'
      ? (m.html ? '<div class="screenplay-doc screenplay-content dr-script">' + m.html + '</div>' : '<p class="pj-empty">This draft has no scenes with script text yet.</p>')
      : '<div class="dr-cols"><nav class="dr-list" aria-label="Entities">' + listHtml(m) + '</nav><article class="dr-detail">' + detailHtml(m.detail, name) + '</article></div>';
    return '<div class="pj-inner dr"><header class="dr-head"><a class="btn" href="#/">← Projects</a><h1>' + esc(m.projectName) + '</h1>'
      + '<span class="pj-chip">' + esc(m.label) + '</span><span class="pj-chip">read-only</span></header>'
      + '<div class="dr-tabs" role="tablist">' + tab('script', 'Script') + tab('entities', 'Entities') + '</div>' + body + '</div>';
  }

  D.reader = { html, detailHtml };

  if (typeof document === 'undefined') return;

  async function show(el, route, ctx) {
    const { slug, ref } = route;
    el.onclick = null;
    el.onchange = null;
    el.innerHTML = '<div class="pj-inner"><p class="pj-empty">Loading…</p></div>';
    const q = encodeURIComponent(ref);
    let m;
    try {
      const [hist, idx, script] = await Promise.all([
        D.historyApi(slug, 'GET', '/'),
        D.historyApi(slug, 'GET', '/read/' + q + '/entities'),
        D.historyApi(slug, 'GET', '/read/' + q + '/script'),
      ]);
      m = { projectName: ctx.projectName(slug), label: C.refLabel(ref, hist), tab: 'script', html: script.html, entities: idx.entities, selected: null, detail: null };
    } catch (e) {
      el.innerHTML = '<div class="pj-inner"><a class="btn" href="#/">← Projects</a><p class="pj-empty bad">' + esc(e.message) + '</p></div>';
      return;
    }
    const draw = () => { const top = el.scrollTop; el.innerHTML = html(m); el.scrollTop = top; };

    async function pick(type, id) {
      m.selected = { type, id };
      try { m.detail = await D.historyApi(slug, 'GET', '/read/' + q + '/entities/' + encodeURIComponent(type) + '/' + encodeURIComponent(id)); }
      catch (e) { m.detail = null; D.efToast && D.efToast(e.message, 'bad'); }
      draw();
    }

    el.onclick = (e) => {
      const t = e.target.closest('[data-rd]');
      if (!t) return;
      if (t.dataset.rd === 'tab') {
        m.tab = t.dataset.tab;
        if (m.tab === 'entities' && !m.selected && m.entities.length) { const first = m.entities.find((x) => x.type === 'scene') || m.entities[0]; pick(first.type, first.id); return; }
        draw();
      } else if (t.dataset.rd === 'pick') pick(t.dataset.type, t.dataset.id);
    };
    draw();
  }

  D.reader.show = show;
})(window.DASH);
