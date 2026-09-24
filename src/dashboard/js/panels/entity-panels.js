window.DASH = window.DASH || {};

DASH.showActPanel = function(actId) {
  const act = (DASH.story.acts || []).find(a => a.id === actId);
  if (!act) return;

  document.getElementById('panel-type').textContent = 'Act';
  document.getElementById('panel-name').textContent = act.title || act.id;

  const seqRows = (act.sequences_list || []).map(sid => {
    const seq = (DASH.story.sequences || []).find(s => s.id === sid);
    return seq ? `<div class="beat-row" onclick="DASH.showSequencePanel('${sid}')">
      <span class="beat-scene">${seq.title || sid}</span>
      <span class="beat-desc">${seq.scene_count || 0} scenes</span>
    </div>` : '';
  }).join('');

  // Plot threads in this act with scope/type
  const plotRows = (act.plots || []).map(p => {
    const pl = (DASH.story.plots || []).find(x => x.id === p.id);
    if (!pl) return '';
    const scope = pl.plot_scope === 'main' ? 'MAIN' : (pl.plot_type || '');
    const col = pl.plot_scope === 'main' ? '#b07be0' : (DASH.PLOT_TYPE_COLORS[pl.plot_type] || '#888');
    return `<div class="beat-row" onclick="DASH.showPlotPanel('${pl.id}')">
      <span class="beat-scene" style="color:${col}">${pl.name}</span>
      ${scope ? `<span class="beat-desc" style="color:${col}">${scope}</span>` : ''}
      ${p.has_setup ? '<span class="beat-desc">setup</span>' : ''}
      ${p.has_crisis ? '<span class="beat-desc">crisis</span>' : ''}
      ${p.has_climax ? '<span class="beat-desc">climax</span>' : ''}
      ${p.has_payoff ? '<span class="beat-desc">payoff</span>' : ''}
    </div>`;
  }).join('');

  document.getElementById('panel-body').innerHTML = `
    <div><span class="status-badge ${act.status || ''}">${act.status || 'planned'}</span></div>
    ${(() => {
      const projectSpine = (DASH.story.project || {}).spine;
      const actObj = act.act_objective;
      if (!projectSpine && !actObj) return '';
      return `<div style="margin-top:8px">
        ${projectSpine ? `<div style="font-size:var(--font-size-xs);color:var(--muted-foreground);margin-bottom:4px">Story spine: <span style="font-style:italic">${projectSpine}</span></div>` : ''}
        ${actObj ? `<div style="font-size:var(--font-size-xs);color:var(--muted-foreground)">Act objective: <span style="color:var(--foreground);font-weight:500">${actObj}</span></div>` : ''}
      </div>`;
    })()}
    ${plotRows ? `<div><div class="panel-section-title">Plot threads</div>${plotRows}</div>` : ''}
    ${seqRows ? `<div><div class="panel-section-title">Sequences (${act.sequence_count || 0})</div>${seqRows}</div>` : '<div class="panel-muted">No sequences in this act yet.</div>'}
    ${DASH.renderSectionsHtml('act', actId)}
  `;

  document.getElementById('panel-footer').innerHTML = `
    <button class="btn btn-hermes" data-hermes-send="What is the dramatic arc of '${act.title || act.id}'?">Ask Hermes about this act</button>
  `;

  DASH.openPanel();
}


DASH.showCharacterPanel = function(char) {
  document.getElementById('panel-type').textContent = char.role || char.story_role || 'Character';
  document.getElementById('panel-name').textContent = char.name;

  // Scenes: char.scenes is normalised to an array of scene ids (strings)
  const scenes = (char.scenes || []).map(sid => {
    const s = (DASH.story.scenes || []).find(x => String(x.id) === String(sid));
    if (s) {
      const num = s.number != null ? String(s.number) : '';
      const label = num ? `${num}. ${s.title || s.id}` : (s.title || s.id);
      return `<span class="tag tag-scene" style="cursor:pointer" onclick="DASH.showScenePanel('${s.id}')">${label}</span>`;
    }
    return sid ? `<span class="tag tag-scene">${sid}</span>` : '';
  }).filter(Boolean).join('');

  // Relationships: use relationships[] (new schema) with type + strength
  const rels = (char.relationships || []).map(rel => {
    const c = (DASH.story.characters || []).find(x => x.id === rel.with);
    const nameEl = c
      ? `<button class="relationship-name entity-link" onclick="DASH.showCharacterPanel(DASH.story.characters.find(x=>x.id==='${c.id}'))">${c.name}</button>`
      : `<span class="relationship-name">${rel.with}</span>`;
    const secretIcon = rel.secret ? ' 🔒' : '';
    const typeTag = rel.type ? `<span class="tag" style="background:${DASH.relTypeColor(rel.type)}22;color:${DASH.relTypeColor(rel.type)}">${rel.type}</span>` : '';
    return `
      <div class="relationship-row">
        ${nameEl}${secretIcon}
        ${rel.label ? `<span class="relationship-label">${rel.label}</span>` : ''}
        ${typeTag}
        ${rel.strength !== undefined ? `<span class="relationship-feeling">strength: ${rel.strength > 0 ? '+' : ''}${rel.strength}</span>` : ''}
      </div>`;
  }).join('');

  // Knowledge: may be array (_knowledge_arr) or string
  const knowledgeArr = char._knowledge_arr || (char.knowledge ? [char.knowledge] : []);
  const knowledgeHtml = knowledgeArr.length
    ? knowledgeArr.map(k => `<div class="knowledge-item">${k}</div>`).join('')
    : '';

  document.getElementById('panel-body').innerHTML = `
    <div>
      <div class="panel-section-title">In one sentence</div>
      <div class="panel-text">${char.one_sentence || '—'}</div>
    </div>
    ${char.age ? `<div><div class="panel-section-title">Age</div><div class="panel-muted">${char.age}</div></div>` : ''}
    ${char.goals_short ? `<div>
      <div class="panel-section-title">Immediate goal</div>
      <div class="panel-text">${char.goals_short}</div>
    </div>` : ''}
    ${char.goals_long ? `<div>
      <div class="panel-section-title">Deeper goal</div>
      <div class="panel-muted">${char.goals_long}</div>
    </div>` : ''}
    ${knowledgeHtml ? `<div>
      <div class="panel-section-title">What they know</div>
      ${knowledgeHtml}
    </div>` : ''}
    ${scenes ? `<div>
      <div class="panel-section-title">Appears in</div>
      <div class="panel-tags">${scenes}</div>
    </div>` : ''}
    ${rels ? `<div>
      <div class="panel-section-title">Relationships</div>
      ${rels}
    </div>` : ''}
    <div>
      <div class="panel-section-title">Arc</div>
      ${DASH.arcSectionHtml(char)}
    </div>
    ${DASH.renderSectionsHtml('character', char.id)}
  `;

  document.getElementById('panel-footer').innerHTML = `
    <button class="btn btn-hermes" data-hermes-send="Tell me more about ${char.name}'s character development.">Ask Hermes about ${char.name}</button>
  `;

  DASH.openPanel();

  if (DASH.network) {
    DASH.network.selectNodes([char.id]);
    DASH.network.focus(char.id, { scale: 1.2, animation: { duration: 400, easingFunction: 'easeInOutQuad' } });
  }
}


DASH.showLocationPanel = function(locId) {
  // Deselect all entity cards, select the one clicked
  document.querySelectorAll('#location-list .entity-card').forEach(el => el.classList.remove('selected'));
  const card = document.querySelector(`#location-list .entity-card[data-id="${locId}"]`);
  if (card) card.classList.add('selected');

  const loc = (DASH.story.locations || []).find(l => l.id === locId);
  if (!loc) return;

  document.getElementById('panel-type').textContent = 'Location';
  document.getElementById('panel-name').textContent = loc.name;

  // Backend gives loc.scenes as heading strings; find scene objects by heading
  const sceneRefs = loc._scene_headings || loc.scenes || [];
  const scenes = sceneRefs.map(ref => {
    const s = (DASH.story.scenes || []).find(x =>
      x.heading === ref || String(x.id) === String(ref)
    );
    if (s) {
      const num = s.number != null ? String(s.number) : '';
      const label = num ? `${num}. ${s.heading || s.id}` : (s.heading || s.id);
      return `<span class="tag tag-scene" style="cursor:pointer" onclick="DASH.showScenePanel('${s.id}')">${label}</span>`;
    }
    return `<span class="tag tag-scene">${ref}</span>`;
  }).join('');

  // Find scenes that reference this location for "Appears in" section
  const appearScenes = (DASH.story.scenes || []).filter(s => s.location === loc.id);
  const appearsIn = appearScenes.map(s => {
    const num = s.number != null ? String(s.number) : '';
    const label = num ? `${num}. ${s.heading || s.id}` : (s.heading || s.id);
    return `<span class="tag tag-scene" style="cursor:pointer" onclick="DASH.showScenePanel('${s.id}')">${label}</span>`;
  }).join('');

  // Characters in this location (via their scenes)
  const charIds = new Set();
  sceneRefs.forEach(ref => {
    const s = (DASH.story.scenes || []).find(x => x.heading === ref || String(x.id) === String(ref));
    if (s) (s.characters || []).forEach(cid => charIds.add(cid));
  });
  const charLinks = [...charIds].map(cid => {
    const c = (DASH.story.characters || []).find(x => x.id === cid || String(x.id) === String(cid));
    return c ? `<button class="entity-link" onclick="DASH.showCharacterPanel(DASH.story.characters.find(x=>x.id==='${c.id}'))" style="border-left:2px solid ${DASH.roleColor(c.role)}">${c.name}</button>` : '';
  }).filter(Boolean).join('');

  document.getElementById('panel-body').innerHTML = `
    <div>
      <div class="panel-section-title">In one sentence</div>
      <div class="panel-text">${loc.one_sentence || '—'}</div>
    </div>
    ${loc.mood ? `<div>
      <div class="panel-section-title">Mood</div>
      <div class="panel-text" style="font-style:italic">${loc.mood}</div>
    </div>` : ''}
    ${loc.dramatic_function ? `<div>
      <div class="panel-section-title">Dramatic function</div>
      <div class="panel-text">${loc.dramatic_function}</div>
    </div>` : ''}
    ${loc.world ? `<div>
      <div class="panel-section-title">World</div>
      <div class="panel-text">${loc.world}</div>
    </div>` : ''}
    ${loc.variant_of ? `<div>
      <div class="panel-section-title">Variant of</div>
      ${(() => {
        const v = DASH.findLocation(loc.variant_of);
        return v ? `<button class="entity-link" onclick="DASH.showLocationPanel('${v.id}')">${v.name}</button>` : `<div class="panel-text" style="color:#e0a86b">${loc.variant_of}</div>`;
      })()}
    </div>` : ''}
    ${charLinks ? `<div>
      <div class="panel-section-title">Characters here</div>
      <div style="display:flex;flex-direction:column;gap:4px;">${charLinks}</div>
    </div>` : ''}
    ${appearsIn ? `<div>
      <div class="panel-section-title">Appears in</div>
      <div class="panel-tags">${appearsIn}</div>
    </div>` : ''}
    ${DASH.renderSectionsHtml('location', loc.id)}
  `;

  document.getElementById('panel-footer').innerHTML = `
    <button class="btn btn-hermes" data-hermes-send="Describe ${loc.name} and its role in the DASH.story.">Ask Hermes about this location</button>
  `;

  DASH.openPanel();
}


DASH.showPlotPanel = function(plotId) {
  document.querySelectorAll('#plot-list .entity-card').forEach(el => el.classList.remove('selected'));
  const card = document.querySelector(`#plot-list .entity-card[data-id="${plotId}"]`);
  if (card) card.classList.add('selected');

  const plot = (DASH.story.plots || []).find(p => p.id === plotId || String(p.id) === String(plotId));
  if (!plot) return;

  const scope = plot.plot_scope === 'main' ? 'MAIN' : (plot.plot_type || '');
  const col = plot.plot_scope === 'main' ? '#b07be0' : (DASH.PLOT_TYPE_COLORS[plot.plot_type] || '#888');
  const scopeHtml = scope ? `<span class="tag" style="background:${col}22;color:${col}">${scope}</span>` : '';
  const arcHtml = (plot.plot_scope === 'main' && plot.value_arc) ? `<div style="margin-top:4px"><span style="color:var(--muted-foreground);font-size:var(--font-size-xs);text-transform:uppercase;letter-spacing:0.06em">Value Arc</span><div style="font-size:var(--font-size-sm);color:var(--foreground)">${plot.value_arc}</div></div>` : '';

  document.getElementById('panel-type').textContent = plot.plot_scope === 'main' ? 'Main Plot' : 'Subplot';
  document.getElementById('panel-name').textContent = plot.name;

  const chars = (plot.characters || []).map(cid => {
    const c = (DASH.story.characters || []).find(x => x.id === cid || String(x.id) === String(cid));
    return c
      ? `<button class="entity-link" onclick="DASH.showCharacterPanel(DASH.story.characters.find(x=>x.id==='${c.id}'))" style="border-left:2px solid ${DASH.roleColor(c.role)}">${c.name}</button>`
      : '';
  }).filter(Boolean).join('');

  // Setups/payoffs: [{scene_id, description}] (backend-normalized)
  function renderBeats(arr) {
    if (!arr || !arr.length) return '';
    return arr.map(item => {
      if (typeof item === 'string') {
        return `<div class="beat-row">${item}</div>`;
      }
      // Backend normalizes to {scene_id, description}
      const sceneObj = (DASH.story.scenes || []).find(s => String(s.id) === String(item.scene_id));
      const displayNum = sceneObj && sceneObj.order != null ? String(sceneObj.order) : '';
      const sceneName = sceneObj ? (sceneObj.title || sceneObj.id) : (item.scene_id || '');
      if (!sceneName) return '';
      const sceneLink = sceneObj
        ? `<span class="beat-scene" onclick="DASH.showScenePanel('${sceneObj.id}')" style="cursor:pointer">${displayNum ? displayNum + '. ' : ''}${sceneName}</span>`
        : `<span class="beat-scene">${displayNum ? displayNum + '. ' : ''}${sceneName}</span>`;
      return `<div class="beat-row">${sceneLink}${item.description ? `<span class="beat-desc">${item.description}</span>` : ''}</div>`;
    }).join('');
  }

  const setupObjs = plot.setups || [];
  const crisisObjs = plot.crisis || [];
  const climaxObjs = plot.climax || [];
  const payoffObjs = plot.payoffs || [];
  const setupsHtml = renderBeats(setupObjs);
  const crisisHtml = renderBeats(crisisObjs);
  const climaxHtml = renderBeats(climaxObjs);
  const payoffsHtml = renderBeats(payoffObjs);

  document.getElementById('panel-body').innerHTML = `
    <div>
      <div class="panel-section-title">Thread</div>
      <div class="panel-text">${plot.one_sentence || '—'}</div>
    </div>
    <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap">
      ${scopeHtml}
      <span class="status-badge ${plot.status || ''}">${plot.status || 'active'}</span>
    </div>
    ${arcHtml}
    ${chars ? `<div>
      <div class="panel-section-title">Characters involved</div>
      <div style="display:flex;flex-direction:column;gap:4px;">${chars}</div>
    </div>` : ''}
    ${setupsHtml ? `<div>
      <div class="panel-section-title">Setups</div>
      ${setupsHtml}
    </div>` : ''}
    ${crisisHtml ? `<div>
      <div class="panel-section-title">Crisis</div>
      ${crisisHtml}
    </div>` : ''}
    ${climaxHtml ? `<div>
      <div class="panel-section-title">Climax</div>
      ${climaxHtml}
    </div>` : ''}
    ${payoffsHtml ? `<div>
      <div class="panel-section-title">Payoffs</div>
      ${payoffsHtml}
    </div>` : ''}
    ${DASH.renderSectionsHtml('plot', plot.id)}
  `;

  document.getElementById('panel-footer').innerHTML = '';
  DASH.openPanel();
}


DASH.showRelationshipPanel = function(rel) {
  const a = rel.characters[0];
  const b = rel.characters[1];
  const charA = (DASH.story.characters || []).find(c => c.id === a);
  const charB = (DASH.story.characters || []).find(c => c.id === b);
  const pa = (rel.perspectives || {})[a] || {};
  const pb = (rel.perspectives || {})[b] || {};

  const nameA = charA
    ? `<button class="entity-link" onclick="DASH.showCharacterPanel(DASH.story.characters.find(x=>x.id==='${a}'))" style="border-left:2px solid ${DASH.roleColor(charA.role)}">${charA.name}</button>`
    : `<span class="panel-muted">${a}</span>`;
  const nameB = charB
    ? `<button class="entity-link" onclick="DASH.showCharacterPanel(DASH.story.characters.find(x=>x.id==='${b}'))" style="border-left:2px solid ${DASH.roleColor(charB.role)}">${charB.name}</button>`
    : `<span class="panel-muted">${b}</span>`;

  function perspectiveHtml(charName, charRole, p) {
    if (!charName) return '';
    const col = DASH.relTypeColor(p.type);
    const typeTag = p.type ? `<span class="tag" style="background:${col}22;color:${col}">${p.type}</span>` : '';
    const secretBadge = p.secret ? `<span class="tag" style="background:rgba(224,107,155,0.18);color:#e06b9b">secret 🔒</span>` : '';
    const strengthBar = p.strength !== undefined ? `
      <div style="display:flex;align-items:center;gap:6px;margin-top:4px">
        <div style="flex:1;height:3px;background:var(--border);border-radius:2px;overflow:hidden">
          <div style="width:${Math.abs(p.strength) * 50}%;height:100%;background:${p.strength >= 0 ? col : '#e07070'};margin-left:${p.strength >= 0 ? '50%' : (50 - Math.abs(p.strength) * 50) + '%'}"></div>
        </div>
        <span style="font-size:var(--font-size-xs);color:var(--muted-foreground)">${p.strength > 0 ? '+' : ''}${p.strength}</span>
      </div>` : '';
    return `
      <div class="panel-perspective" style="flex:1">
        <div style="font-size:var(--font-size-sm);font-weight:500;margin-bottom:4px">${charName}</div>
        ${charRole ? `<div style="font-size:var(--font-size-xs);color:var(--muted-foreground);margin-bottom:6px">${charRole}</div>` : ''}
        <div style="display:flex;flex-wrap:wrap;gap:4px;margin-bottom:4px">${typeTag}${secretBadge}</div>
        ${p.label ? `<div style="font-size:var(--font-size-sm);margin-bottom:2px">${p.label}</div>` : ''}
        ${p.feeling ? `<div style="font-size:var(--font-size-xs);color:var(--muted-foreground);font-style:italic">${p.feeling}</div>` : ''}
        ${strengthBar}
      </div>`;
  }

  const sceneTags = (rel.scenes || []).map(sid => {
    const s = (DASH.story.scenes || []).find(x => String(x.id) === String(sid));
    if (s) {
      const num = s.number != null ? String(s.number) : '';
      const label = num ? `${num}. ${s.title || s.id}` : (s.title || s.id);
      return `<span class="tag tag-scene" style="cursor:pointer" onclick="DASH.showScenePanel('${s.id}')">${label}</span>`;
    }
    return sid ? `<span class="tag tag-scene">${sid}</span>` : '';
  }).filter(Boolean).join('');

  document.getElementById('panel-type').textContent = 'Relationship';
  document.getElementById('panel-name').textContent = rel.name || `${a} & ${b}`;

  document.getElementById('panel-body').innerHTML = `
    <div>
      <div class="panel-section-title">Characters</div>
      <div style="display:flex;gap:8px;flex-wrap:wrap">${nameA}${nameB}</div>
    </div>
    <div>
      <div class="panel-section-title">Perspectives</div>
      <div style="display:flex;gap:16px">
        ${perspectiveHtml(charA?.name, charA?.role, pa)}
        ${perspectiveHtml(charB?.name, charB?.role, pb)}
      </div>
    </div>
    ${sceneTags ? `<div>
      <div class="panel-section-title">Scenes</div>
      <div class="panel-tags">${sceneTags}</div>
    </div>` : ''}
    ${rel.status ? `<div>
      <div class="panel-section-title">Status</div>
      <span class="status-badge ${rel.status}">${rel.status}</span>
    </div>` : ''}
    ${rel.history ? `<div>
      <div class="panel-section-title">History</div>
      <div class="panel-text">${DASH.escapeHtml(rel.history).replace(/\n/g, '<br>')}</div>
    </div>` : ''}
  `;

  document.getElementById('panel-footer').innerHTML = `
    <button class="btn btn-hermes" data-hermes-send="Update the relationship between ${charA?.name || a} and ${charB?.name || b}. Current status: ${rel.status || 'active'}. Tell me what changed and why.">Edit with Hermes</button>
  `;

  DASH.openPanel();
}


DASH.showScenePanel = function(sceneId) {
  const scene = (DASH.story.scenes || []).find(s => String(s.id) === String(sceneId));
  if (!scene) return;

  document.querySelectorAll('.scene-item').forEach(el => el.classList.remove('selected'));
  const sceneEl = document.querySelector(`.scene-item[data-id="${sceneId}"]`);
  if (sceneEl) sceneEl.classList.add('selected');

  document.getElementById('panel-type').textContent = 'Scene';
  document.getElementById('panel-name').textContent = scene.title || scene.id;

  const chars = (scene.characters || []).map(cid => {
    const c = (DASH.story.characters || []).find(x => x.id === cid || String(x.id) === String(cid));
    return c
      ? `<button class="entity-link" onclick="DASH.showCharacterPanel(DASH.story.characters.find(x=>x.id==='${c.id}'))" style="border-left:2px solid ${DASH.roleColor(c.role)}">${c.name}</button>`
      : '';
  }).filter(Boolean).join('');

  const locs = (scene.locations || []).map(lref => {
    const l = DASH.findLocation(lref);
    return l ? `<button class="entity-link" onclick="DASH.showLocationPanel('${l.id}')">${l.name}</button>` : '';
  }).filter(Boolean).join('');

  // Plots: backend populates scene.plots from plot setups/payoffs
  const plotRefs = (scene.plots || []);
  const plots = plotRefs.map(pref => {
    const pid = (typeof pref === 'object' && pref !== null) ? pref.id : pref;
    const beat = (typeof pref === 'object' && pref !== null) ? (pref.beat || '') : '';
    const pl = (DASH.story.plots || []).find(x => x.id === pid || String(x.id) === String(pid));
    if (!pl) return '';
    const scope = pl.plot_scope === 'main' ? 'MAIN' : (pl.plot_type || '');
    const col = pl.plot_scope === 'main' ? '#b07be0' : (DASH.PLOT_TYPE_COLORS[pl.plot_type] || '#888');
    const beatLabel = beat ? ` · ${beat.toUpperCase()}` : '';
    const scopeLabel = scope ? ` · ${scope}` : '';
    return `<button class="entity-link" onclick="DASH.showPlotPanel('${pl.id}')" style="border-left:2px solid ${col}">${pl.name}<span style="color:${col};font-size:var(--font-size-xs);margin-left:4px">${scopeLabel}${beatLabel}</span></button>`;
  }).filter(Boolean).join('');

  // Content from __SECTIONS__.scenes[slug]["Content"]
  let contentHtml = '';
  const sections = window.__SECTIONS__;
  const sceneContent = sections?.scene?.[sceneId]?.Content;
  if (sceneContent) {
    contentHtml = `<div class="fountain-content">${DASH.escapeHtml(sceneContent)}</div>`;
  } else {
    contentHtml = '<div class="panel-muted">No content yet.</div>';
  }

  // Dramatic metadata — only show positive values
  const dramaTags = [];
  if (scene.dramatic_role) dramaTags.push({ l: 'role', v: scene.dramatic_role });
  if (scene.is_inciting_incident) dramaTags.push({ l: 'inciting', v: 'Inciting Incident' });
  if (scene.is_sequence_climax) dramaTags.push({ l: 'seq-climax', v: 'Sequence Climax' });
  if (scene.is_act_climax) dramaTags.push({ l: 'act-climax', v: 'Act Climax' });
  if (scene.is_story_climax) dramaTags.push({ l: 'DASH.story-climax', v: 'Story Climax' });

  const valueArc = [scene.value, scene.value_open, scene.value_close].filter(Boolean);
  const conflicts = (scene.conflict_levels || []).filter(Boolean);

  const dramaHtml = (dramaTags.length || valueArc.length || conflicts.length) ? `
    <div>
      <div style="display:flex;flex-wrap:wrap;gap:4px;margin-bottom:8px">
        ${dramaTags.map(t => `<span class="tag tag-struct">${t.v}</span>`).join('')}
        ${conflicts.map(c => `<span class="tag tag-char" style="font-size:var(--font-size-xs)">${c}</span>`).join('')}
      </div>
      ${valueArc.length ? `<div style="font-size:var(--font-size-xs);color:var(--muted-foreground);margin-bottom:8px">Value arc: ${valueArc.join(' → ')}</div>` : ''}
    </div>` : '';

  document.getElementById('panel-body').innerHTML = `
    ${dramaHtml}
    ${chars ? `<div>
      <div class="panel-section-title">Characters</div>
      <div style="display:flex;flex-direction:column;gap:4px;">${chars}</div>
    </div>` : ''}
    ${locs ? `<div>
      <div class="panel-section-title">Location</div>
      <div style="display:flex;flex-wrap:wrap;gap:4px;">${locs}</div>
    </div>` : ''}
    ${plots ? `<div>
      <div class="panel-section-title">Plot threads</div>
      <div style="display:flex;flex-direction:column;gap:4px;">${plots}</div>
    </div>` : ''}
    ${scene.heading ? `<div>
      <div class="panel-section-title">Screenplay heading</div>
      <div class="panel-muted">${DASH.escapeHtml(scene.heading)}</div>
    </div>` : ''}
    <div>
      <div class="panel-section-title">Content</div>
      ${contentHtml}
    </div>
    ${DASH.renderSectionsHtml('scene', sceneId, ['Content'])}
  `;

  document.getElementById('panel-footer').innerHTML = `
    <button class="btn btn-hermes" data-hermes-send="What happens in ${scene.title || scene.id}?">Ask Hermes about this scene</button>
  `;

  DASH.openPanel();
}


DASH.showSequencePanel = function(seqId) {
  const seq = (DASH.story.sequences || []).find(s => s.id === seqId);
  if (!seq) return;

  document.getElementById('panel-type').textContent = 'Sequence';
  document.getElementById('panel-name').textContent = seq.title || seq.id;

  const sceneRows = (seq.scenes_list || []).map((sid, i) => {
    const scene = (DASH.story.scenes || []).find(s => s.id === sid);
    if (!scene) return '';
    return `<div class="beat-row" onclick="DASH.showScenePanel('${sid}')">
      <span class="beat-scene">${i + 1}. ${scene.title || sid}</span>
      ${scene.heading ? `<span class="beat-desc">${DASH.escapeHtml(scene.heading)}</span>` : ''}
    </div>`;
  }).join('');

  // Plot threads in this sequence with scope/type
  const plotRows = (seq.plots || []).map(p => {
    const pl = (DASH.story.plots || []).find(x => x.id === p.id);
    if (!pl) return '';
    const scope = pl.plot_scope === 'main' ? 'MAIN' : (pl.plot_type || '');
    const col = pl.plot_scope === 'main' ? '#b07be0' : (DASH.PLOT_TYPE_COLORS[pl.plot_type] || '#888');
    return `<div class="beat-row" onclick="DASH.showPlotPanel('${pl.id}')">
      <span class="beat-scene" style="color:${col}">${pl.name}</span>
      ${scope ? `<span class="beat-desc" style="color:${col}">${scope}</span>` : ''}
      ${p.has_setup ? '<span class="beat-desc">setup</span>' : ''}
      ${p.has_crisis ? '<span class="beat-desc">crisis</span>' : ''}
      ${p.has_climax ? '<span class="beat-desc">climax</span>' : ''}
      ${p.has_payoff ? '<span class="beat-desc">payoff</span>' : ''}
    </div>`;
  }).join('');

  document.getElementById('panel-body').innerHTML = `
    <div><span class="status-badge ${seq.status || ''}">${seq.status || 'planned'}</span></div>
    ${plotRows ? `<div><div class="panel-section-title">Plot threads</div>${plotRows}</div>` : ''}
    ${sceneRows ? `<div><div class="panel-section-title">Scenes (${seq.scene_count || 0})</div>${sceneRows}</div>` : '<div class="panel-muted">No scenes in this sequence yet.</div>'}
    ${DASH.renderSectionsHtml('sequence', seqId)}
  `;

  document.getElementById('panel-footer').innerHTML = `
    <button class="btn btn-hermes" data-hermes-send="What is the dramatic function of the sequence '${seq.title || seq.id}'?">Ask Hermes about this sequence</button>
  `;

  DASH.openPanel();
}


DASH.showWorldPanel = function(worldId) {
  document.querySelectorAll('#world-list .entity-card').forEach(el => el.classList.remove('selected'));
  const card = document.querySelector(`#world-list .entity-card[data-id="${worldId}"]`);
  if (card) card.classList.add('selected');

  const world = (DASH.story.worlds || []).find(w => w.id === worldId);
  if (!world) return;

  document.getElementById('panel-type').textContent = 'World';
  document.getElementById('panel-name').textContent = world.name;

  const rules = (world.rules || []).map(r =>
    `<div class="world-rule">${r}</div>`
  ).join('');

  const sections = (world.sections || []).join(', ');

  // Plots in this world
  const worldPlots = (DASH.story.plots || []).filter(pl =>
    (pl.worlds || []).includes(worldId) ||
    (pl.world === worldId)
  );
  const plotLinks = worldPlots.map(pl =>
    `<button class="entity-link" onclick="DASH.showPlotPanel('${pl.id}')">${pl.name}</button>`
  ).join('');

  document.getElementById('panel-body').innerHTML = `
    <div>
      <div class="panel-section-title">In one sentence</div>
      <div class="panel-text">${world.one_sentence || '—'}</div>
    </div>
    ${world.period ? `<div>
      <div class="panel-section-title">Period</div>
      <div class="panel-text">${world.period}</div>
    </div>` : ''}
    ${(world.values && world.values.length) ? `<div>
      <div class="panel-section-title">Values</div>
      <div class="panel-text">${world.values.map(v => `<div class="world-rule">${v}</div>`).join('')}</div>
    </div>` : ''}
    ${(world.power && world.power.length) ? `<div>
      <div class="panel-section-title">Power</div>
      <div class="panel-text">${world.power.map(p => `<div class="world-rule">${p}</div>`).join('')}</div>
    </div>` : ''}
    ${rules ? `<div>
      <div class="panel-section-title">Rules</div>
      ${rules}
    </div>` : ''}
    ${world.variant_of ? `<div>
      <div class="panel-section-title">Variant of</div>
      ${(() => {
        const v = (DASH.story.worlds || []).find(w => w.id === world.variant_of);
        return v ? `<button class="entity-link" onclick="DASH.showWorldPanel('${v.id}')">${v.name}</button>` : `<div class="panel-text" style="color:#e0a86b">${world.variant_of}</div>`;
      })()}
    </div>` : ''}
    ${plotLinks ? `<div>
      <div class="panel-section-title">Plot threads</div>
      <div style="display:flex;flex-direction:column;gap:4px;">${plotLinks}</div>
    </div>` : ''}
    ${DASH.renderSectionsHtml('world', world.id)}
  `;

  document.getElementById('panel-footer').innerHTML = '';
  DASH.openPanel();
}


