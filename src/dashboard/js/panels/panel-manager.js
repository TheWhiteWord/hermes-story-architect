window.DASH = window.DASH || {};

DASH.closePanel = function() { document.getElementById('detail-panel').classList.remove('open'); }



DASH.openPanel = function() { document.getElementById('detail-panel').classList.add('open'); }



DASH.renderSectionsHtml = function(entityType, slug, skip = []) {
  const data = (window.__SECTIONS__ && window.__SECTIONS__[entityType] && window.__SECTIONS__[entityType][slug]);
  if (!data) return '';
  return Object.entries(data)
    .filter(([name]) => !skip.includes(name))
    .map(([name, content]) => `
    <div>
      <div class="panel-section-title">${name}</div>
      <div class="panel-text">${DASH.escapeHtml(content).replace(/\n/g, '<br>')}</div>
    </div>
  `).join('');
}



