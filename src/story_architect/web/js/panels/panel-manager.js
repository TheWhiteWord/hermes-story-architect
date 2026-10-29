window.DASH = window.DASH || {};

DASH.closePanel = function() { document.getElementById('detail-panel').classList.remove('open'); }



DASH.openPanel = function() { document.getElementById('detail-panel').classList.add('open'); }



// A section body of `[placeholder — type/Section]` is the marker a template
// leaves, not something the author wrote. Nothing that reads sections renders
// it as content: it would typeset an instruction to the writer as if the writer
// had written it. The one predicate, so every reader agrees.
DASH.isPlaceholderSection = function (text) {
  return /^\s*\[placeholder/i.test(String(text == null ? '' : text));
};



DASH.renderSectionsHtml = function(entityType, slug, skip = []) {
  const data = (window.__SECTIONS__ && window.__SECTIONS__[entityType] && window.__SECTIONS__[entityType][slug]);
  if (!data) return '';
  return Object.entries(data)
    .filter(([name]) => !skip.includes(name))
    .filter(([, content]) => !DASH.isPlaceholderSection(content))
    .map(([name, content]) => `
    <div>
      <div class="panel-section-title">${name}</div>
      <div class="panel-text">${DASH.escapeHtml(content).replace(/\n/g, '<br>')}</div>
    </div>
  `).join('');
}



