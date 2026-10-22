// Tabs for the detail panel.
//
// entity-panels.js renders a panel in one go. This file leaves that alone: it wraps a
// show*Panel function, lets it render, then lifts what it rendered into an "Overview" tab and
// adds the tabs a module registered for that kind of entity. A module needs two calls:
//
//   DASH.panelTabs.register('scene', id => [ {id, label, wide, render(pane, id), footer(id), dot} ])
//   DASH.panelTabs.decorate('showScenePanel', 'scene', args => args[0])
//
// Remove both calls and the panel is exactly what it was. Load after panels/entity-panels.js.
window.DASH = window.DASH || {};

(function (D) {
  'use strict';

  const registry = {};                          // kind -> id => [tab] (or null when there is nothing to add)
  const memory = { tab: {}, wide: true };       // last tab per kind, and the widen preference
  let current = null;                           // { kind, id, tabs, footer, ro }
  let wired = false;

  const $ = id => document.getElementById(id);
  const esc = s => (D.escapeHtml ? D.escapeHtml(s) : String(s));

  function setWide(on) {
    const p = $('detail-panel');
    if (p) p.classList.toggle('panel-wide', !!on);
    const w = document.querySelector('#panel-body .ptab-widen');
    if (w) w.setAttribute('aria-pressed', on ? 'true' : 'false');
  }

  function stripHtml(tabs) {
    const btns = tabs.map(t =>
      `<button class="ptab" type="button" data-tab="${esc(t.id)}">${esc(t.label)}${t.dot ? '<span class="ptab-dot" title="' + esc(t.dot) + '"></span>' : ''}</button>`
    ).join('');
    return `<div class="ptab-strip">${btns}<button class="ptab-widen" type="button" title="Widen the panel" aria-pressed="false"><svg viewBox="0 0 16 16" width="13" height="13" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M1.5 8h13M4.5 5 1.5 8l3 3M11.5 5l3 3-3 3"/></svg></button></div>`;
  }

  function renderPane(tab, pane, ctx) {
    if (typeof tab.render !== 'function') return;
    const out = tab.render(pane, ctx.id);
    if (typeof out === 'string') pane.innerHTML = out;
  }

  function activate(id) {
    const c = current;
    if (!c) return;
    const tab = c.tabs.find(t => t.id === id);
    if (!tab) return;
    memory.tab[c.kind] = id;
    const body = $('panel-body');
    body.querySelectorAll('.ptab').forEach(b => b.classList.toggle('active', b.dataset.tab === id));
    body.querySelectorAll('.ptab-pane').forEach(p => p.classList.toggle('active', p.dataset.pane === id));
    const pane = body.querySelector('.ptab-pane[data-pane="' + id + '"]');
    const widen = body.querySelector('.ptab-widen');
    if (widen) widen.style.display = tab.wide ? '' : 'none';
    setWide(!!tab.wide && memory.wide);
    const foot = $('panel-footer');
    if (foot) foot.innerHTML = tab.footer ? tab.footer(c.id) : c.footer;
    c.active = id;
    if (pane && !pane.dataset.ready) { pane.dataset.ready = '1'; renderPane(tab, pane, c); }
    if (c.ro) c.ro.disconnect();
    // a tab that draws to a width asks to be redrawn when the panel is resized (widen, window)
    if (tab.redraw && pane && typeof ResizeObserver !== 'undefined') {
      let last = pane.clientWidth, timer = 0;
      c.ro = new ResizeObserver(() => {
        clearTimeout(timer);
        timer = setTimeout(() => {
          const w = pane.clientWidth;
          if (Math.abs(w - last) < 8) return;
          last = w;
          renderPane(tab, pane, c);
        }, 120);
      });
      c.ro.observe(pane);
    }
  }

  function wireOnce() {
    if (wired) return;
    const body = $('panel-body');
    if (!body) return;
    wired = true;
    body.addEventListener('click', ev => {
      const tabBtn = ev.target.closest && ev.target.closest('.ptab');
      if (tabBtn) { activate(tabBtn.dataset.tab); return; }
      const widen = ev.target.closest && ev.target.closest('.ptab-widen');
      if (widen) {
        memory.wide = !memory.wide;
        setWide(memory.wide);
        return;
      }
      // any element carrying data-ent="type:id" opens that entity's own panel
      const ent = ev.target.closest && ev.target.closest('[data-ent]');
      if (ent) { ev.preventDefault(); D.panelTabs.openEntity(ent.dataset.ent); }
    });
  }

  function mount(kind, id) {
    if (current && current.ro) current.ro.disconnect();
    current = null;
    const tabsFor = registry[kind], body = $('panel-body');
    const tabs = tabsFor && body ? tabsFor(id) : null;
    if (!tabs || !tabs.length) { setWide(false); return; }
    wireOnce();
    const foot = $('panel-footer');
    const all = [{ id: 'overview', label: 'Overview' }].concat(tabs);
    const overview = body.innerHTML;                         // what the panel function just rendered
    body.innerHTML = stripHtml(all)
      + all.map(t => `<div class="ptab-pane" data-pane="${esc(t.id)}"${t.id === 'overview' ? ' data-ready="1"' : ''}>${t.id === 'overview' ? overview : ''}</div>`).join('');
    current = { kind, id, tabs: all, footer: foot ? foot.innerHTML : '', ro: null, active: null };
    const wanted = memory.tab[kind];
    activate(all.some(t => t.id === wanted) ? wanted : 'overview');
  }

  // "type:id" -> that entity's own panel. The panel functions take an id, except the
  // character and relationship panels, which take the object.
  function openEntity(ref) {
    const cut = String(ref).indexOf(':');
    const type = String(ref).slice(0, cut), id = String(ref).slice(cut + 1);
    const st = D.story || {};
    const find = list => (st[list] || []).find(x => String(x.id) === id);
    if (type === 'character' && D.showCharacterPanel) { const c = find('characters'); if (c) D.showCharacterPanel(c); }
    else if (type === 'location' && D.showLocationPanel) D.showLocationPanel(id);
    else if (type === 'world' && D.showWorldPanel) D.showWorldPanel(id);
    else if (type === 'relationship' && D.showRelationshipPanel) { const r = find('relationships'); if (r) D.showRelationshipPanel(r); }
    else if (type === 'scene' && D.showScenePanel) D.showScenePanel(id);
  }

  function register(kind, tabsFor) { registry[kind] = tabsFor; }

  function decorate(fnName, kind, idOf) {
    const base = D[fnName];
    if (typeof base !== 'function' || base.__tabbed) return;
    const wrapped = function () {
      const out = base.apply(this, arguments);
      try { mount(kind, idOf(Array.prototype.slice.call(arguments))); }
      catch (e) { if (window.console) console.error('panel tabs:', e); }
      return out;
    };
    wrapped.__tabbed = true;
    D[fnName] = wrapped;
  }

  // Panels without tabs, and closing, put the panel back to its normal width.
  ['openPanel', 'closePanel'].forEach(name => {
    const base = D[name];
    if (typeof base !== 'function') return;
    D[name] = function () {
      if (current && current.ro) current.ro.disconnect();
      current = null;
      setWide(false);
      return base.apply(this, arguments);
    };
  });

  D.panelTabs = { register, decorate, mount, activate, openEntity };
})(window.DASH);
