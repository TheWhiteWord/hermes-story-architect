window.DASH = window.DASH || {};

DASH.buildRelationshipsView = function() {
  const rels = DASH.story.relationships || [];
  document.getElementById('relationships-subtitle').textContent = rels.length + ' relationships';
  const list = document.getElementById('relationship-list');

  if (!rels.length) {
    list.innerHTML = '<div class="empty-state"><div class="empty-state-title">No relationships</div></div>';
    return;
  }

  list.innerHTML = rels.map(rel => {
    const charA = (DASH.story.characters || []).find(c => c.id === rel.characters[0]);
    const charB = (DASH.story.characters || []).find(c => c.id === rel.characters[1]);
    const pa = (rel.perspectives || {})[rel.characters[0]] || {};
    const pb = (rel.perspectives || {})[rel.characters[1]] || {};

    const charTags = rel.characters.map(cid => {
      const c = (DASH.story.characters || []).find(x => x.id === cid);
      return c ? `<span class="tag tag-char">${c.name}</span>` : '';
    }).join('');

    const types = new Set();
    if (pa.type) types.add(pa.type);
    if (pb.type) types.add(pb.type);
    const typeTags = [...types].map(t =>
      `<span class="tag" style="background:${DASH.relTypeColor(t)}22;color:${DASH.relTypeColor(t)}">${t}</span>`
    ).join('');

    const strengths = [pa.strength, pb.strength].filter(s => s !== undefined);
    const avgStrength = strengths.length ? strengths.reduce((sum, s) => sum + s, 0) / strengths.length : null;
    const strengthHtml = avgStrength !== null ? `
      <div style="display:flex;align-items:center;gap:4px;margin-top:4px">
        <div style="flex:1;height:3px;background:var(--border);border-radius:2px;overflow:hidden">
          <div style="width:${Math.abs(avgStrength) * 50}%;height:100%;background:${avgStrength >= 0 ? '#6bbfb0' : '#e07070'};margin-left:${avgStrength >= 0 ? '50%' : (50 - Math.abs(avgStrength) * 50) + '%'}"></div>
        </div>
        <span style="font-size:var(--font-size-xs);color:var(--muted-foreground)">${avgStrength > 0 ? '+' : ''}${avgStrength.toFixed(1)}</span>
      </div>` : '';

    const pipColor = types.size ? DASH.relTypeColor(types.values().next().value) : '#8a8a8a';

    return `
      <div class="entity-card" data-id="${rel.id}" onclick="DASH.showRelationshipPanel(DASH.story.relationships.find(r=>r.id==='${rel.id}'))">
        <div class="entity-card-pip" style="background:${pipColor}"></div>
        <div class="entity-card-body">
          <div class="entity-card-name" style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
            ${rel.name || `${rel.characters[0]} & ${rel.characters[1]}`}
            <span class="status-badge ${rel.status || ''}">${rel.status || 'active'}</span>
          </div>
          <div class="entity-card-sub">${charTags}</div>
          ${typeTags ? `<div class="entity-card-meta">${typeTags}</div>` : ''}
          ${strengthHtml ? `<div class="entity-card-meta">${strengthHtml}</div>` : ''}
        </div>
      </div>`;
  }).join('');
};
