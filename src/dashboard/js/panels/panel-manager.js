window.DASH = window.DASH || {};

DASH.closePanel = function() { document.getElementById('detail-panel').classList.remove('open'); }



DASH.openPanel = function() { document.getElementById('detail-panel').classList.add('open'); }



DASH.renderSectionsHtml = function(entityType, slug) {
  const data = (window.__SECTIONS__ && window.__SECTIONS__[entityType] && window.__SECTIONS__[entityType][slug]);
  if (!data) return '';
  return Object.entries(data).map(([name, content]) => `
    <div>
      <div class="panel-section-title">${name}</div>
      <div class="panel-text">${DASH.escapeHtml(content).replace(/\n/g, '<br>')}</div>
    </div>
  `).join('');
}


DASH.arcSectionHtml = function(char) {
  const arcBeats = char.arc_beats_list || [];
  const arcType = char.arc_type || 'absent';
  const arcValue = char.arc_value || '';
  if (arcBeats.length > 0) {
    return `
      <div class="panel-muted" style="font-size:var(--font-size-sm);margin-bottom:8px">
        ${arcBeats.length} beats designed (${arcType}${arcValue ? ' · ' + arcValue : ''})
      </div>
      <div class="arc-beat-list">
        ${arcBeats.map(b => `
          <div class="arc-beat-item" style="display:flex;align-items:center;gap:6px;margin-bottom:4px">
            <span class="arc-beat-dot" style="background:${DASH.roleColor(char.role || char.story_role || '')}"></span>
            <span style="font-size:var(--font-size-sm)">${DASH.escapeHtml(b.label || b.id)}</span>
            <span class="panel-muted" style="margin-left:auto;font-size:var(--font-size-xs)">${DASH.escapeHtml(b.shift || '')}</span>
          </div>
        `).join('')}
      </div>`;
  }
  return `
    <div class="panel-muted" style="font-size:var(--font-size-sm)">No beats designed</div>
    <button class="btn btn-hermes" data-hermes-send="Design a character arc for ${char.name} showing their value shift across the DASH.story.">Design arc with Hermes</button>`;
}


