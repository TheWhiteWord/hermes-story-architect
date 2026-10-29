window.DASH = window.DASH || {};

DASH.plotScopeBadge = function(pl) {
  if (pl.plot_scope === 'main') {
    const arc = pl.value_arc || '';
    return `<span class="tag" style="background:rgba(176,123,224,0.18);color:#b07be0">MAIN${arc ? ' · ' + arc.toUpperCase() : ''}</span>`;
  }
  const pt = pl.plot_type || '';
  if (pt) {
    const col = DASH.PLOT_TYPE_COLORS[pt] || '#888';
    return `<span class="tag" style="background:${col}22;color:${col}">${pt.toUpperCase()}</span>`;
  }
  return '';
};

DASH.buildPlotsView = function() {
  const plots = DASH.story.plots || [];
  const main = plots.filter(p => p.plot_scope === 'main');
  const subs = plots.filter(p => p.plot_scope !== 'main');
  document.getElementById('plots-subtitle').textContent = plots.length + ' threads';
  const list = document.getElementById('plot-list');
  if (!plots.length) {
    list.innerHTML = '<div class="empty-state"><div class="empty-state-title">No plots</div></div>';
    return;
  }

  function renderPlotCard(pl) {
    const charTags = (pl.characters || []).map(cid => {
      const c = (DASH.story.characters || []).find(x => x.id === cid || String(x.id) === String(cid));
      return c ? `<span class="tag tag-char">${c.name}</span>` : '';
    }).join('');
    const scopeBadge = DASH.plotScopeBadge(pl);
    return `
      <div class="entity-card" data-id="${pl.id}" onclick="DASH.showPlotPanel('${pl.id}')">
        <div class="entity-card-pip" style="background:${pl.plot_scope === 'main' ? '#b07be0' : (DASH.PLOT_TYPE_COLORS[pl.plot_type] || '#888')}"></div>
        <div class="entity-card-body">
          <div class="entity-card-name" style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
            ${pl.name}
            ${scopeBadge}
            <span class="status-badge ${pl.status || ''}">${pl.status || 'active'}</span>
          </div>
          <div class="entity-card-sub">${pl.one_sentence || ''}</div>
          ${charTags ? `<div class="entity-card-meta">${charTags}</div>` : ''}
        </div>
      </div>`;
  }

  let html = '';
  if (main.length) {
    html += `<div class="DASH.story-section-title" style="margin-bottom:6px">Main Plot</div>`;
    html += main.map(renderPlotCard).join('');
  }
  if (subs.length) {
    if (main.length) html += `<div class="DASH.story-section-title" style="margin:12px 0 6px">Subplots</div>`;
    html += subs.map(renderPlotCard).join('');
  }
  list.innerHTML = html;
};
