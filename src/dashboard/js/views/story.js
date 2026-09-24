window.DASH = window.DASH || {};

DASH.buildStoryView = function() {
  const p = DASH.story.project || {};
  const mem = DASH.story.story_memory || {};

  document.getElementById('story-project-name').textContent = p.name || 'Story';
  document.getElementById('story-subtitle').textContent = [p.genre, p.setting].filter(Boolean).join(' · ');

  const body = document.getElementById('story-body');

  // Project stats
  const statsGrid = [
    { v: p.scene_count     || (DASH.story.scenes     || []).length, l: 'Scenes' },
    { v: p.character_count || (DASH.story.characters || []).length, l: 'Characters' },
    { v: p.location_count  || (DASH.story.locations  || []).length || null, l: 'Locations' },
    { v: p.world_count     || (DASH.story.worlds     || []).length || null, l: 'Worlds' },
    { v: p.plot_count      || (DASH.story.plots      || []).length || null, l: 'Plots' },
    { v: p.sequence_count  || (DASH.story.sequences  || []).length, l: 'Sequences' },
    { v: p.act_count       || (DASH.story.acts       || []).length, l: 'Acts' },
  ].filter(s => s.v != null && s.v > 0);

  const statsHtml = `
    <div>
      <div class="DASH.story-section-title">Project</div>
      <div class="project-card">
        <div class="project-logline">${p.logline || ''}</div>
        ${statsGrid.map(s => `<div class="project-stat"><div class="project-stat-value">${s.v}</div><div class="project-stat-label">${s.l}</div></div>`).join('')}
      </div>
    </div>`;

  // Structure section (spine, controlling idea, value arc, structure type, key scenes)
  const structure = [];

  if (p.spine) structure.push(`<div style="margin-bottom:6px"><span style="color:var(--muted-foreground);font-size:var(--font-size-xs);text-transform:uppercase;letter-spacing:0.06em">Spine</span><div style="font-size:var(--font-size-sm);color:var(--foreground);margin-top:2px">${p.spine}</div></div>`);

  if (p.controlling_idea) structure.push(`<div style="margin-bottom:6px"><span style="color:var(--muted-foreground);font-size:var(--font-size-xs);text-transform:uppercase;letter-spacing:0.06em">Controlling Idea</span><div style="font-size:var(--font-size-sm);color:var(--foreground);margin-top:2px">${p.controlling_idea}</div></div>`);

  const valueArc = [];
  if (p.value) valueArc.push(`<span style="color:var(--muted-foreground);font-size:var(--font-size-xs)">${p.value}</span>`);
  if (p.value_at_open) valueArc.push(`<span style="color:var(--muted-foreground);font-size:var(--font-size-xs)">${p.value_at_open}</span>`);
  if (p.value_at_close) valueArc.push(`<span style="color:var(--muted-foreground);font-size:var(--font-size-xs)">${p.value_at_close}</span>`);
  if (valueArc.length) structure.push(`<div style="margin-bottom:6px"><span style="color:var(--muted-foreground);font-size:var(--font-size-xs);text-transform:uppercase;letter-spacing:0.06em">Value Arc</span><div style="font-size:var(--font-size-sm);color:var(--foreground);margin-top:2px;display:flex;gap:6px;align-items:center">${valueArc.join(' → ')}</div></div>`);

  if (p.structure_type) structure.push(`<div style="margin-bottom:6px"><span style="color:var(--muted-foreground);font-size:var(--font-size-xs);text-transform:uppercase;letter-spacing:0.06em">Structure</span><div style="font-size:var(--font-size-sm);color:var(--foreground);margin-top:2px">${p.structure_type}</div></div>`);

  // Key scenes: inciting incident, story climax — clickable
  const keyScenes = [];
  if (p.inciting_incident_scene_id) {
    const sid = p.inciting_incident_scene_id;
    const scene = (DASH.story.scenes || []).find(s => String(s.id) === String(sid));
    const label = scene ? scene.title : sid;
    keyScenes.push(`<div style="margin-bottom:6px"><span style="color:var(--muted-foreground);font-size:var(--font-size-xs);text-transform:uppercase;letter-spacing:0.06em">Inciting Incident</span><div style="margin-top:2px"><button class="entity-link" onclick="DASH.showScenePanel('${sid}')" style="font-size:var(--font-size-sm);padding:0;background:none;border:none;cursor:pointer;color:var(--accent);text-decoration:underline">${label}</button></div></div>`);
  }
  if (p.story_climax_scene_id) {
    const sid = p.story_climax_scene_id;
    const scene = (DASH.story.scenes || []).find(s => String(s.id) === String(sid));
    const label = scene ? scene.title : sid;
    keyScenes.push(`<div style="margin-bottom:6px"><span style="color:var(--muted-foreground);font-size:var(--font-size-xs);text-transform:uppercase;letter-spacing:0.06em">Story Climax</span><div style="margin-top:2px"><button class="entity-link" onclick="DASH.showScenePanel('${sid}')" style="font-size:var(--font-size-sm);padding:0;background:none;border:none;cursor:pointer;color:var(--accent);text-decoration:underline">${label}</button></div></div>`);
  }

  const structureHtml = (structure.length || keyScenes.length) ? `
    <div>
      <div class="DASH.story-section-title">Structure</div>
      <div style="padding:12px;background:var(--card);border:1px solid var(--border);border-radius:var(--radius)">
        ${structure.join('')}
        ${keyScenes.join('')}
      </div>
    </div>` : '';

  // Plots
  const plots = DASH.story.plots || [];
  const mainPlots = plots.filter(p => p.plot_scope === 'main');
  const subPlots = plots.filter(p => p.plot_scope !== 'main');
  const allPlotItems = [...mainPlots, ...subPlots];
  const plotsHtml = allPlotItems.length ? `
    <div>
      <div class="DASH.story-section-title">Active plot threads</div>
      <div class="plot-list">
        ${allPlotItems.map(pl => {
          const scope = pl.plot_scope === 'main' ? 'MAIN' : (pl.plot_type || '');
          const col = pl.plot_scope === 'main' ? '#b07be0' : (DASH.PLOT_TYPE_COLORS[pl.plot_type] || '#888');
          return `<div class="plot-item" onclick="DASH.showPlotPanel('${pl.id}')">
            <div class="plot-header">
              <span class="plot-name">${pl.name}</span>
              ${scope ? `<span class="tag" style="background:${col}22;color:${col};font-size:var(--font-size-xs)">${scope}</span>` : ''}
              <span class="status-badge ${pl.status || ''}">${pl.status || 'active'}</span>
            </div>
            <div class="plot-sentence">${pl.one_sentence || ''}</div>
          </div>`;
        }).join('')}
      </div>
    </div>` : '';

  // Continuity risks
  const risks = mem.continuity_risks || [];
  const risksHtml = risks.length ? `
    <div>
      <div class="DASH.story-section-title">Continuity risks</div>
      <div class="risk-list">
        ${risks.map(r => `<div class="risk-item">${r}</div>`).join('')}
      </div>
    </div>` : '';

  // Hermes ask button
  const hermesHtml = p.name ? `
    <div style="padding-top:4px;">
      <button class="btn btn-hermes" data-hermes-send="Give me an overview of ${p.name}.">Ask Hermes about this DASH.story</button>
    </div>` : '';

  body.innerHTML = statsHtml + structureHtml + plotsHtml + risksHtml + hermesHtml;
};
