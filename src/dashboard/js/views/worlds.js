window.DASH = window.DASH || {};

DASH.buildWorldsView = function() {
  const worlds = DASH.story.worlds || [];
  document.getElementById('worlds-subtitle').textContent = worlds.length + ' world' + (worlds.length !== 1 ? 's' : '');
  const list = document.getElementById('world-list');
  if (!worlds.length) {
    list.innerHTML = '<div class="empty-state"><div class="empty-state-title">No worlds defined</div><div class="empty-state-sub">Add worlds to index.yaml to see them here.</div></div>';
    return;
  }
  list.innerHTML = worlds.map(w => {
    const metaTags = [];
    if (w.period) metaTags.push(`<span class="tag tag-period">${w.period}</span>`);
    if ((w.rules || []).length) metaTags.push(`<span class="tag tag-rule">${w.rules.length} rule${w.rules.length !== 1 ? 's' : ''}</span>`);
    if ((w.values || []).length) metaTags.push(`<span class="tag tag-value">${w.values.length} values</span>`);
    if ((w.power || []).length) metaTags.push(`<span class="tag tag-power">${w.power.length} power</span>`);
    if (w.variant_of) {
      const v = (DASH.story.worlds || []).find(x => x.id === w.variant_of);
      metaTags.push(`<span class="tag tag-variant">${v ? `variant of ${v.name}` : `variant of ${w.variant_of}`}</span>`);
    }
    return `
      <div class="entity-card" data-id="${w.id}" onclick="DASH.showWorldPanel('${w.id}')">
        <div class="entity-card-pip" style="background:#e0a86b"></div>
        <div class="entity-card-body">
          <div class="entity-card-name">${w.name}</div>
          <div class="entity-card-sub">${w.one_sentence || ''}</div>
          ${metaTags.length ? `<div class="entity-card-meta">${metaTags.join('')}</div>` : ''}
        </div>
      </div>`;
  }).join('');
};
