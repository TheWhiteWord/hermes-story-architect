window.DASH = window.DASH || {};

DASH.buildLocationsView = function() {
  const locs = DASH.story.locations || [];
  document.getElementById('locations-subtitle').textContent = locs.length + ' locations';
  const list = document.getElementById('location-list');
  if (!locs.length) {
    list.innerHTML = '<div class="empty-state"><div class="empty-state-title">No locations</div></div>';
    return;
  }
  list.innerHTML = locs.map(l => {
    const sceneHeadings = (l._scene_headings || l.scenes || []);
    const sceneTags = sceneHeadings.slice(0, 4).map(h =>
      `<span class="tag tag-scene">${h}</span>`
    ).join('');
    const metaTags = [];
    if (l.mood) metaTags.push(`<span class="tag tag-mood">${l.mood}</span>`);
    if (l.variant_of) {
      const v = DASH.findLocation(l.variant_of);
      metaTags.push(`<span class="tag tag-variant">${v ? `variant of ${v.name}` : `variant of ${l.variant_of}`}</span>`);
    }
    return `
      <div class="entity-card" data-id="${l.id}" onclick="DASH.showLocationPanel('${l.id}')">
        <div class="entity-card-pip" style="background:#6bbfb0"></div>
        <div class="entity-card-body">
          <div class="entity-card-name">${l.name}</div>
          <div class="entity-card-sub">${l.one_sentence || ''}</div>
          ${l.dramatic_function ? `<div class="entity-card-sub" style="font-style:italic;margin-top:2px">${l.dramatic_function}</div>` : ''}
          ${sceneTags ? `<div class="entity-card-meta">${sceneTags}</div>` : ''}
          ${metaTags.length ? `<div class="entity-card-meta">${metaTags.join('')}</div>` : ''}
        </div>
      </div>`;
  }).join('');
};
