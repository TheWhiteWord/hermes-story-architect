window.DASH = window.DASH || {};

let sidebarExpanded = false;

let currentView = 'graph';

DASH._viewOpenedHooks = [];
DASH.onViewOpened = function(fn) { DASH._viewOpenedHooks.push(fn); };

DASH.valueGraphLink = function(target) {
  const isPlot = target !== 'story';
  const state = `DASH.valueGraphState.tab='${isPlot ? 'plot' : 'story'}';DASH.valueGraphState.plot=${isPlot ? `'${target}'` : 'null'};`;
  return `<button class="vg-link" onclick="DASH.switchView('values', document.querySelector('[data-view=values]'));${state}DASH.renderValues();" title="View graph">
    <svg width="12" height="12" viewBox="0 0 16 16" fill="none"><path d="M2 12l3-4 3 2 3-6 3 4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
  </button>`;
};

DASH.switchView = function(view, btn) {
  document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
  document.querySelectorAll('.nav-btn[data-view]').forEach(b => b.classList.remove('active'));
  document.getElementById(view + '-view').classList.add('active');
  btn.classList.add('active');
  DASH.currentView = view;
  if (view === 'graph' && DASH.network) {
    DASH.network.redraw();
    DASH.network.fit();
  }
  DASH._viewOpenedHooks.forEach(fn => fn(view));
  DASH.closePanel();
}

DASH.toggleSidebar = function() {
  DASH.sidebarExpanded = !DASH.sidebarExpanded;
  document.getElementById('sidebar').classList.toggle('expanded', DASH.sidebarExpanded);
  const icon = document.querySelector('.sidebar-toggle svg path');
  icon.setAttribute('d', DASH.sidebarExpanded ? 'M9 3l-4 4 4 4' : 'M5 3l4 4-4 4');
}

DASH.refreshIndex = function() {
  document.getElementById('loading-screen').style.display = 'flex';
  if (DASH.network) { DASH.network.destroy(); DASH.network = null; }
  setTimeout(DASH.boot, 50);
}

DASH.switchGraphTab = function(tab) {
  document.querySelectorAll('.graph-tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.graph-tab-content').forEach(c => c.classList.remove('active'));
  document.getElementById('tab-' + tab)?.classList.add('active');
  const content = document.getElementById('graph-tab-' + tab);
  if (content) {
    content.classList.add('active');
    content.style.display = '';
  }
  const netLegend = document.getElementById('graph-legend');
  if (netLegend) netLegend.style.display = (tab === 'network') ? '' : 'none';
  if (tab === 'arcgraph') { DASH.buildCharsGrid(); DASH.buildArcGraph(); DASH.updateLegend(); }
}

DASH._origSwitchView = DASH.switchView;
