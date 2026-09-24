window.DASH = window.DASH || {};

let sidebarExpanded = false;

let currentView = 'graph';

DASH.switchView = function(view, btn) {
  document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
  document.querySelectorAll('.nav-btn[data-view]').forEach(b => b.classList.remove('active'));
  document.getElementById(view + '-view').classList.add('active');
  btn.classList.add('active');
  DASH.currentView = view;
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
