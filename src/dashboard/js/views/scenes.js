window.DASH = window.DASH || {};

DASH.allScenes = [];

DASH.buildScenesView = function() {
  DASH.allScenes = DASH.story.scenes || [];
  document.getElementById('scenes-subtitle').textContent = DASH.allScenes.length + ' scenes';
  DASH.renderSceneList(DASH.allScenes);
};

DASH.filterScenes = function(query) {
  if (!query.trim()) { DASH.renderSceneList(DASH.allScenes); return; }
  const q = query.toLowerCase();
  const filtered = DASH.allScenes.filter(s => {
    if ((s.heading || '').toLowerCase().includes(q)) return true;
    if ((s.characters || []).some(cid => {
      const c = (DASH.story.characters || []).find(x => x.id === cid);
      return c && c.name.toLowerCase().includes(q);
    })) return true;
    if ((s.locations || []).some(lid => {
      const l = DASH.findLocation(lid);
      return l && l.name.toLowerCase().includes(q);
    })) return true;
    return false;
  });
  DASH.renderSceneList(filtered);
};

DASH.renderSceneItem = function(s) {
  const charTags = (s.characters || []).map(cid => {
    const c = (DASH.story.characters || []).find(x => x.id === cid || String(x.id) === String(cid));
    return c ? `<span class="tag tag-char">${DASH.escapeHtml(c.name)}</span>` : '';
  }).join('');
  const locRefs = s.locations || (s.location ? [s.location] : []);
  const locTags = locRefs.map(lref => {
    const l = DASH.findLocation(lref);
    return l ? `<span class="tag tag-location">${DASH.escapeHtml(l.name)}</span>` : '';
  }).join('');
  // Structural tags: dramatic_role + climax flags (orange)
  const structTags = [];
  if (s.dramatic_role) structTags.push(s.dramatic_role);
  if (s.is_inciting_incident) structTags.push('inciting');
  if (s.is_sequence_climax) structTags.push('seq-climax');
  if (s.is_act_climax) structTags.push('act-climax');
  if (s.is_story_climax) structTags.push('DASH.story-climax');
  const structHtml = structTags.map(t => `<span class="tag tag-struct">${t}</span>`).join('');
  // Arc beat indicator dots
  const arcBeatDots = (s.arc_beats || []).map(ab => {
    const c = (DASH.story.characters || []).find(x => x.id === ab.character || String(x.id) === String(ab.character));
    const color = c ? DASH.roleColor(c.role || c.story_role || '') : '#8a8a8a';
    const label = c ? `${c.name}: ${ab.label || ''}` : '';
    return `<span class="arc-beat-dot-scene" style="background:${color}" title="${DASH.escapeHtml(label)}"></span>`;
  }).join('');
  return `
    <div class="scene-item" data-id="${s.id}">
      <div class="scene-number">${String(s.order || 0).padStart(2, '0')}</div>
      <div class="scene-body">
        <div class="scene-heading">${s.title || s.id}</div>
        ${s.heading ? `<div class="panel-muted" style="font-size:var(--font-size-xs);margin-top:2px;">${DASH.escapeHtml(s.heading)}</div>` : ''}
        <div class="scene-meta">${charTags}${locTags}${structHtml}${arcBeatDots}</div>
      </div>
    </div>
  `;
};

DASH.renderSceneList = function(scenes) {
  const list = document.getElementById('scene-list');
  if (!scenes.length) {
    list.innerHTML = '<div class="empty-state"><div class="empty-state-title">No scenes yet</div><div class="empty-state-sub">Create scenes to see them here.</div></div>';
    return;
  }

  const sequences = DASH.story.sequences || [];
  const acts = DASH.story.acts || [];
  const seqMap = {};
  sequences.forEach(seq => { seqMap[seq.id] = []; });
  const unassigned = [];
  scenes.forEach(s => {
    if (s.sequence_id && seqMap[s.sequence_id]) {
      seqMap[s.sequence_id].push(s);
    } else {
      unassigned.push(s);
    }
  });
  Object.values(seqMap).forEach(arr => arr.sort((a, b) => (a.order || 0) - (b.order || 0)));
  unassigned.sort((a, b) => (a.order || 0) - (b.order || 0));

  let html = '';
  acts.sort((a, b) => (a.order || 0) - (b.order || 0));
  for (const act of acts) {
    const actSeqs = sequences.filter(s => s.act_id === act.id).sort((a, b) => (a.order || 0) - (b.order || 0));
    let actHtml = '';
    for (const seq of actSeqs) {
      const seqScenes = seqMap[seq.id];
      if (!seqScenes.length) continue;
      actHtml += `<div class="scene-sequence-header clickable" onclick="DASH.showSequencePanel('${seq.id}')" style="cursor:pointer;font-size:var(--font-size-sm);color:var(--muted-foreground);padding:6px 10px 2px;font-weight:500;">${DASH.escapeHtml(seq.title || seq.id)}</div>`;
      actHtml += seqScenes.map(s => DASH.renderSceneItem(s)).join('');
    }
    if (actHtml) {
      html += `<div class="DASH.story-section-title clickable" onclick="DASH.showActPanel('${act.id}')" style="cursor:pointer;margin-top:12px">${DASH.escapeHtml(act.title || act.id)}</div>` + actHtml;
    }
  }
  if (unassigned.length) {
    html += `<div class="DASH.story-section-title" style="margin-top:12px">Unassigned</div>`;
    html += unassigned.map(s => DASH.renderSceneItem(s)).join('');
  }

  list.innerHTML = html;
  list.querySelectorAll('.scene-item').forEach(el => {
    el.addEventListener('click', () => DASH.showScenePanel(el.dataset.id));
  });
};
