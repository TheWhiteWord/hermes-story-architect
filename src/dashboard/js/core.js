// ─── State ────────────────────────────────────────────────────────────────────
let story = null;
let network = null;
let sidebarExpanded = false;
let currentView = 'graph';

// ─── Boot ─────────────────────────────────────────────────────────────────────
async function boot() {
  try {
    // Injected data takes precedence (avoids fetch('file://') which Electron blocks)
    if (window.__STORY_DATA__) {
      initStory(window.__STORY_DATA__);
      return;
    }

    // Check for project path in URL query param first
    const params = new URLSearchParams(window.location.search);
    const projectPath = params.get('project');
    let indexPath;

    if (projectPath) {
      indexPath = projectPath.replace(/\/$/, '') + '/.story/index.yaml';
    } else {
      indexPath = '.story/index.yaml';
    }

    const res = await fetch('file://' + indexPath);
    if (!res.ok) throw new Error('not found');
    const text = await res.text();
    const data = jsyaml.load(text);
    initStory(data);
  } catch (e) {
    showError();
  }
}

function showError() {
  document.getElementById('loading-screen').style.display = 'none';
  document.getElementById('error-screen').style.display = 'flex';
}

function loadFromFile() {
  document.getElementById('file-input').click();
}

function handleFileLoad(input) {
  const file = input.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = e => {
    try {
      const data = jsyaml.load(e.target.result);
      document.getElementById('error-screen').style.display = 'none';
      document.getElementById('loading-screen').style.display = 'flex';
      initStory(data);
    } catch(err) {
      alert('Could not parse YAML: ' + err.message);
    }
  };
  reader.readAsText(file);
}

function loadSampleData() {
  // Sample data in the REAL backend schema (as per brief) — exercises the normaliser
  const sample = {
    project: { name: "The Water Audit", logline: "A forensic accountant discovers her firm is laundering water-rationing profits for a corporate police state.", genre: "Sci-fi thriller", setting: "Near-future city-state", spine: "", controlling_idea: "", value: "", value_at_open: "", value_at_close: "", inciting_incident_scene_id: "", story_climax_scene_id: "", structure_type: "", scene_count: 3, character_count: 2, location_count: 1, world_count: 1, plot_count: 1 },
    characters: [
      {
        id: "detective-oak", name: "Detective Oak", story_role: "Supporting",
        one_sentence: "Homicide detective investigating the same cartel.",
        sections: ["Personality","Background","Voice","Arc","Relationships"],
        relationships: [{ with: "mara", label: "Partner", type: "ally", strength: 0.5 }],
        scenes: [{ number: 2, heading: "INT. POLICE STATION - DAY" }, { number: 3, heading: "INT. KITCHEN - NIGHT" }],
        goals: { short: "Bring down the cartel's leadership.", long: "Redeem his failure to protect his last partner." }
      },
      {
        id: "mara", name: "Mara Chen", story_role: "Protagonist", age: 34,
        one_sentence: "Forensic accountant who finds her firm laundering cartel money.",
        sections: ["Personality","Background","Voice","Greatest Fear","Secrets","Arc","Relationships","Goals"],
        relationships: [
          { with: "detective-oak", label: "Partner", type: "ally", strength: 0.4 },
          { with: "victor-hale", label: "Boss", type: "enemy", strength: -0.6 }
        ],
        scenes: [{ number: 1, heading: "INT. MARA'S APARTMENT - NIGHT" }, { number: 3, heading: "INT. KITCHEN - NIGHT" }],
        goals: { short: "Find the account number her brother left behind.", long: "Burn the cartel's financial network to the ground." },
        knowledge: ["Her brother Daniel was murdered", "Victor Hale is the cartel's CFO"]
      }
    ],
    locations: [
      { id: "kitchen", name: "The Kitchen", one_sentence: "Commercial kitchen in a closed restaurant.", sections: ["Description","History","Scenes"], scenes: ["INT. KITCHEN - NIGHT"] }
    ],
    worlds: [
      { id: "gilead", name: "Gilead", one_sentence: "Near-future city-state where water is privatized.", sections: ["Description","History","Conflict"], rules: ["Water rationing is enforced by biometric scanners.", "Off-grid water extraction is a capital offense.", "The police are funded by AquaCorp."] }
    ],
    plots: [
      {
        id: "brother-investigation", name: "Brother Investigation", status: "active",
        one_sentence: "Mara follows her brother's account number into the cartel's network.",
        setups: [{ heading: "INT. MARA'S APARTMENT - NIGHT", description: "" }, { heading: "INT. POLICE STATION - DAY", description: "" }],
        payoffs: [{ heading: "INT. KITCHEN - NIGHT", description: "" }],
        characters: ["mara", "detective-oak"],
        sections: ["Summary","Obstacles","Stakes"]
      }
    ],
    scenes: [
      { heading: "INT. MARA'S APARTMENT - NIGHT", scene_number: null, characters: ["mara"], id: 1, locations: [] },
      { heading: "INT. POLICE STATION - DAY", scene_number: null, characters: ["detective-oak"], id: 2, locations: [] },
      { heading: "INT. KITCHEN - NIGHT", scene_number: null, characters: ["detective-oak","mara"], id: 3, locations: ["kitchen"] }
    ],
    story_memory: {
      last_updated: "2026-09-06T14:30:00",
      continuity_risks: ["Mara's skimming hasn't been discovered (ticking clock)", "Oak's investigation is off-books (if his captain finds out, he's burned)"],
      summary: "Mara and Oak are allied but don't fully trust each other. Victor Hale is the cartel's CFO — Mara doesn't know yet."
    },
    relationships: [
      {
        id: "mara-oak",
        name: "Mara & Oak",
        characters: ["mara", "detective-oak"],
        perspectives: {
          mara: { label: "Partner", feeling: "Wary respect — he's useful but unpredictable", type: "ally", strength: 0.4, secret: false },
          "detective-oak": { label: "Partner", feeling: "Brilliant but reckless", type: "ally", strength: 0.5, secret: false }
        },
        scenes: [],
        status: "active",
        history: ""
      },
      {
        id: "mara-victor",
        name: "Mara & Victor",
        characters: ["mara", "victor-hale"],
        perspectives: {
          mara: { label: "Boss", feeling: "Fear — he knows what she's found", type: "enemy", strength: -0.6, secret: true },
          "victor-hale": { label: "Employee", feeling: "Useful asset, potential threat", type: "professional", strength: -0.2, secret: false }
        },
        scenes: [],
        status: "active",
        history: ""
      }
    ]
  };
  document.getElementById('error-screen').style.display = 'none';
  document.getElementById('loading-screen').style.display = 'flex';
  initStory(sample);
}

// ─── Normalise ─────────────────────────────────────────────────────────────────
// Maps real backend schema → internal rendering schema.
// Real schema differences:
//   characters: story_role (not role), relationships[] (not related[]),
//               goals.short/long (not goals_short/long), knowledge as string[]
//   scenes: id as integer (string lookup needs String()), locations as id[] but
//           also sometimes heading strings; characters array is id strings
//   plots: setups/payoffs are [{scene: heading, description}] objects (backend-normalized)
//   locations/worlds: scenes array contains heading strings (not ids)
function normalise(data) {
  const d = JSON.parse(JSON.stringify(data)); // deep clone

  // Characters
  (d.characters || []).forEach(c => {
    // story_role → role
    if (c.story_role && !c.role) c.role = c.story_role;
    // goals object → flat
    if (c.goals && typeof c.goals === 'object') {
      if (!c.goals_short) c.goals_short = c.goals.short;
      if (!c.goals_long)  c.goals_long  = c.goals.long;
    }
    // knowledge: string[] → join for display (keep array for panel)
    if (Array.isArray(c.knowledge)) {
      c._knowledge_arr = c.knowledge;
      c.knowledge = c.knowledge.join(' · ');
    }
    // scenes: [{id, heading}] → map to scene IDs (prefer id match)
    if (Array.isArray(c.scenes) && c.scenes.length && typeof c.scenes[0] === 'object') {
      c._scene_objs = c.scenes;
      c.scenes = c.scenes.map(s => {
        const found = (d.scenes || []).find(sc =>
          String(sc.id) === String(s.id) ||  // match by slug id (preferred)
          sc.heading === s.heading ||          // fallback: heading match
          (sc.heading || '').includes(s.heading || '__NOMATCH__')  // fallback: fuzzy
        );
        return found ? String(found.id) : (s.heading || String(s.id));
      });
    } else {
      // ensure they're strings for consistent lookup
      c.scenes = (c.scenes || []).map(s => String(s));
    }
  });

  // Scenes: ensure id is string, title exists, normalise character/location arrays
  (d.scenes || []).forEach(s => {
    s.id = String(s.id);
    s.title = s.title || s.id;  // ensure title exists
    s.characters = (s.characters || []).map(String);
    // locations: normalize from location (string) or locations (array)
    s.locations = normalizeLocs(s.locations || s.location);
    s.plots = (s.plots || []);
  });

  // Plots: setups/payoffs already normalized by backend to [{heading, number, description}]
  (d.plots || []).forEach(pl => {
    pl.characters = (pl.characters || []).map(String);
  });

  // Locations: scenes may be heading strings — keep for cross-reference
  (d.locations || []).forEach(loc => {
    if (!loc._scene_headings && Array.isArray(loc.scenes)) {
      loc._scene_headings = loc.scenes.filter(s => typeof s === 'string');
    }
  });

  d.worlds = d.worlds || [];
  d.story_memory = d.story_memory || {};

  return d;
}

// ─── Init ──────────────────────────────────────────────────────────────────────
function initStory(data) {
  story = normalise(data);
  story.characters = story.characters || [];
  story.locations  = story.locations  || [];
  story.plots      = story.plots      || [];
  story.scenes     = story.scenes     || [];
  story.worlds     = story.worlds     || [];
  story.story_memory = story.story_memory || {};
  story.relationships = story.relationships || [];

  document.getElementById('loading-screen').style.display = 'none';

  buildGraphView();
  buildScenesView();
  buildLocationsView();
  buildPlotsView();
  buildRelationshipsView();
  buildWorldsView();
  buildStoryView();
}

// ─── Navigation ───────────────────────────────────────────────────────────────
function switchView(view, btn) {
  document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
  document.querySelectorAll('.nav-btn[data-view]').forEach(b => b.classList.remove('active'));
  document.getElementById(view + '-view').classList.add('active');
  btn.classList.add('active');
  currentView = view;
  closePanel();
}

function toggleSidebar() {
  sidebarExpanded = !sidebarExpanded;
  document.getElementById('sidebar').classList.toggle('expanded', sidebarExpanded);
  const icon = document.querySelector('.sidebar-toggle svg path');
  icon.setAttribute('d', sidebarExpanded ? 'M9 3l-4 4 4 4' : 'M5 3l4 4-4 4');
}

function refreshIndex() {
  document.getElementById('loading-screen').style.display = 'flex';
  if (network) { network.destroy(); network = null; }
  setTimeout(boot, 50);
}

// ─── Role Colors ───────────────────────────────────────────────────────────────
const ROLE_COLORS = {
  'protagonist': '#7b9cf0',
  'antagonist':  '#e07070',
  'mentor':      '#b07be0',
  'rival':       '#e0a86b',
  'supporting':  '#6bbfb0',
  'entity':      '#e06b9b',
};

function roleColor(role) {
  if (!role) return '#8a8a8a';
  const r = role.toLowerCase();
  for (const [key, val] of Object.entries(ROLE_COLORS)) {
    if (r.includes(key)) return val;
  }
  return '#8a8a8a';
}

function getRoleKey(role) {
  if (!role) return 'other';
  const r = role.toLowerCase();
  for (const key of Object.keys(ROLE_COLORS)) {
    if (r.includes(key)) return key;
  }
  return 'other';
}

const REL_TYPE_COLORS = {
  'ally':         '#6bbfb0',
  'enemy':        '#e07070',
  'family':       '#7b9cf0',
  'romantic':     '#e06b9b',
  'professional': '#e0a86b',
  'mentor':       '#b07be0',
  'rival':        '#e0a86b',
  'custom':       '#8a8a8a',
  'neutral':      '#7a8a9a',
};

function relTypeColor(type) {
  if (!type) return '#8a8a8a';
  return REL_TYPE_COLORS[type.toLowerCase()] || '#8a8a8a';
}

// ─── Graph View ────────────────────────────────────────────────────────────────
function buildGraphView() {
  const chars = story.characters || [];
  document.getElementById('graph-subtitle').textContent = chars.length + ' characters';

  const fgColor = getComputedStyle(document.documentElement).getPropertyValue('--foreground').trim() || '#e8e8e8';
  const mutedColor = getComputedStyle(document.documentElement).getPropertyValue('--muted-foreground').trim() || '#8a8a8a';

  const nodes = new vis.DataSet(chars.map(c => {
    const role = c.role || c.story_role || '';
    const col = roleColor(role);
    return {
      id: c.id,
      label: c.name,
      color: {
        background: col + '22',
        border: col,
        highlight: { background: col + '44', border: col },
        hover: { background: col + '33', border: col }
      },
      font: { color: fgColor, size: 12, face: 'inherit' },
      borderWidth: 1.5,
      borderWidthSelected: 2,
      size: 22,
      shape: 'dot'
    };
  }));

  const edges = [];
  const rels = story.relationships || [];

  // Average all strength values per character pair (both directions, all rels)
  const pairStrength = {};
  rels.forEach(rel => {
    if (!rel.characters || rel.characters.length < 2) return;
    const [a, b] = rel.characters;
    const key = [a, b].sort().join('::');
    const pa = (rel.perspectives || {})[a] || {};
    const pb = (rel.perspectives || {})[b] || {};
    pairStrength[key] = pairStrength[key] || [];
    if (pa.strength !== undefined) pairStrength[key].push(pa.strength);
    if (pb.strength !== undefined) pairStrength[key].push(pb.strength);
  });
  const avgStrength = {};
  for (const key in pairStrength) {
    const vals = pairStrength[key];
    avgStrength[key] = vals.length ? vals.reduce((a, b) => a + b, 0) / vals.length : 0;
  }

  rels.forEach(rel => {
    if (!rel.characters || rel.characters.length < 2) return;
    const [a, b] = rel.characters;
    const pa = (rel.perspectives || {})[a] || {};
    const pb = (rel.perspectives || {})[b] || {};
    const fontCfg = { color: mutedColor, size: 9, align: 'middle', strokeWidth: 2, strokeColor: '#1a1a1a' };
    const key = [a, b].sort().join('::');
    const TYPE_PROXIMITY = { family: 0, romantic: 10, ally: 40, neutral: 50, professional: 60, mentor: 70, rival: 80, enemy: 100, custom: 50 };
    const typeOffset = Math.max(
      TYPE_PROXIMITY[pa.type] ?? 40,
      TYPE_PROXIMITY[pb.type] ?? 40
    );
    const spring = 80 + typeOffset * 1.5 + (1 - (avgStrength[key] || 0)) * 40;

    edges.push({
      from: a, to: b,
      label: pa.label || '',
      color: { color: relTypeColor(pa.type) + 'aa', highlight: relTypeColor(pa.type) },
      font: fontCfg,
      width: 1.5,
      dashes: pa.secret || false,
      length: spring,
      smooth: { enabled: false },
      relId: rel.id
    });

    edges.push({
      from: b, to: a,
      label: pb.label || '',
      color: { color: relTypeColor(pb.type) + 'aa', highlight: relTypeColor(pb.type) },
      font: fontCfg,
      width: 1.5,
      dashes: pb.secret || false,
      length: spring,
      relId: rel.id
    });
  });

  // Unlinked entities: add virtual neutral edges to protagonist(s) only
  const linkedIds = new Set();
  edges.forEach(e => { linkedIds.add(e.from); linkedIds.add(e.to); });
  const protagonists = chars.filter(c => (c.role || c.story_role || '').toLowerCase().includes('protagonist'));
  chars.forEach(c => {
    if (linkedIds.has(c.id)) return;
    protagonists.forEach(p => {
      if (p.id === c.id) return;
      edges.push({
        from: c.id, to: p.id,
        label: '',
        color: { color: '#7a8a9a11', highlight: '#7a8a9a' },
        font: { color: mutedColor, size: 9, align: 'middle', strokeWidth: 2, strokeColor: '#1a1a1a' },
        width: 0.5,
        dashes: true,
        length: 80 + 50 * 1.5,
        smooth: { enabled: false },
        relId: '_virtual_'
      });
    });
  });

  const edgeDataSet = new vis.DataSet(edges);
  const container = document.getElementById('network-canvas');

  const options = {
    nodes: { borderWidthSelected: 2 },
    edges: { arrows: { to: { enabled: true, scaleFactor: 0.5 } } },
    physics: {
      enabled: true,
      solver: 'barnesHut',
      barnesHut: { gravitationalConstant: -500, centralGravity: 0.01, springConstant: 0.15, springLength: 150, damping: 0.4 }
    },
    interaction: { hover: true, tooltipDelay: 200, hideEdgesOnDrag: false },
    layout: { randomSeed: 42 }
  };

  network = new vis.Network(container, { nodes, edges: edgeDataSet }, options);

  // Fit after initial stabilization
  network.once('stabilizationIterationsDone', () => {
    network.fit({ animation: { duration: 400, easingFunction: 'easeInOutQuad' } });
  });

  network.on('hoverNode', params => {
    const nodeId = params.node;
    const char = chars.find(c => c.id === nodeId);
    if (!char) return;
    const role = char.role || char.story_role || '';
    const arcType = char.arc_type || 'absent';
    const arcValue = char.arc_value || '';
    const arcBeatCount = char.arc_beats_list ? char.arc_beats_list.length : 0;
    const tt = document.getElementById('arc-beat-tooltip');
    if (!tt) return;
    document.getElementById('tt-label').textContent = char.name;
    document.getElementById('tt-char').textContent = role;
    let shiftText = '';
    if (arcBeatCount > 0) {
      shiftText = arcType + (arcValue ? ' · ' + arcValue : '') + ' · ' + arcBeatCount + ' beats';
    } else {
      shiftText = arcType;
    }
    document.getElementById('tt-shift').textContent = shiftText;
    document.getElementById('tt-value').innerHTML = '';
    tt.classList.add('visible');
    positionArcTooltip({ clientX: params.event.clientX, clientY: params.event.clientY });
  });
  network.on('blurNode', () => hideArcTooltip());

  network.on('click', params => {
    if (params.nodes.length > 0) {
      const charId = params.nodes[0];
      const char = chars.find(c => c.id === charId);
      if (char) showCharacterPanel(char);
    } else if (params.edges.length > 0) {
      const edgeId = params.edges[0];
      const edge = edgeDataSet.get(edgeId);
      if (edge && edge.relId) {
        const rel = rels.find(r => r.id === edge.relId);
        if (rel) showRelationshipPanel(rel);
      }
    }
  });

  const legend = document.getElementById('graph-legend');
  const seen_roles = new Set();
  chars.forEach(c => seen_roles.add(getRoleKey(c.role)));
  const roleLegend = [...seen_roles].map(role => {
    const charsInRole = chars.filter(c => getRoleKey(c.role) === role);
    const arcChars = charsInRole.filter(c => c.arc_type && c.arc_type !== 'absent');
    const arcBadge = arcChars.length > 0 ? ` <span style="color:var(--muted-foreground);font-size:9px">(${arcChars.length} arc)</span>` : '';
    return `
      <div class="legend-item">
        <div class="legend-dot" style="background:${ROLE_COLORS[role] || '#8a8a8a'}"></div>
        <span>${role.charAt(0).toUpperCase() + role.slice(1)}</span>${arcBadge}
      </div>`;
  }).join('');

  const usedRelTypes = new Set();
  rels.forEach(r => { Object.values(r.perspectives || {}).forEach(p => { if (p.type) usedRelTypes.add(p.type); }); });
  const relLegend = [...usedRelTypes].map(t => `
    <div class="legend-item">
      <div class="legend-dot" style="background:${relTypeColor(t)};width:16px;height:3px;border-radius:0;margin-left:3px"></div>
      <span>${t}</span>
    </div>`).join('');

  legend.innerHTML = roleLegend + (relLegend ? '<div style="height:4px"></div>' + relLegend : '');
}

function resetGraphLayout() {
  if (network) {
    network.setOptions({ physics: { enabled: true } });
    setTimeout(() => {
      network.setOptions({ physics: { enabled: false } });
      network.fit({ animation: { duration: 400, easingFunction: 'easeInOutQuad' } });
    }, 3000);
  }
}

// ─── Scenes View ───────────────────────────────────────────────────────────────
let allScenes = [];

function buildScenesView() {
  allScenes = story.scenes || [];
  document.getElementById('scenes-subtitle').textContent = allScenes.length + ' scenes';
  renderSceneList(allScenes);
}

// Helper: normalize location field (string, array, or undefined) to array
function normalizeLocs(loc) {
  if (!loc) return [];
  if (Array.isArray(loc)) return loc;
  return [loc];
}

// Helper: find location by id OR by heading string (backend sometimes uses headings)
function findLocation(ref) {
  return (story.locations || []).find(l =>
    l.id === ref || l.id === String(ref) ||
    (l._scene_headings || []).includes(ref) ||
    l.name === ref
  );
}

function renderSceneList(scenes) {
  const list = document.getElementById('scene-list');
  if (!scenes.length) {
    list.innerHTML = '<div class="empty-state"><div class="empty-state-title">No scenes yet</div><div class="empty-state-sub">Create scenes to see them here.</div></div>';
    return;
  }

  const sequences = story.sequences || [];
  const acts = story.acts || [];
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
      actHtml += `<div class="scene-sequence-header clickable" onclick="DASH.showSequencePanel('${seq.id}')" style="cursor:pointer;font-size:var(--font-size-sm);color:var(--muted-foreground);padding:6px 10px 2px;font-weight:500;">${escapeHtml(seq.title || seq.id)}</div>`;
      actHtml += seqScenes.map(s => renderSceneItem(s)).join('');
    }
    if (actHtml) {
      html += `<div class="story-section-title clickable" onclick="DASH.showActPanel('${act.id}')" style="cursor:pointer;margin-top:12px">${escapeHtml(act.title || act.id)}</div>` + actHtml;
    }
  }
  if (unassigned.length) {
    html += `<div class="story-section-title" style="margin-top:12px">Unassigned</div>`;
    html += unassigned.map(s => renderSceneItem(s)).join('');
  }

  list.innerHTML = html;
  list.querySelectorAll('.scene-item').forEach(el => {
    el.addEventListener('click', () => showScenePanel(el.dataset.id));
  });
}

function renderSceneItem(s) {
  const charTags = (s.characters || []).map(cid => {
    const c = (story.characters || []).find(x => x.id === cid || String(x.id) === String(cid));
    return c ? `<span class="tag tag-char">${escapeHtml(c.name)}</span>` : '';
  }).join('');
  const locRefs = s.locations || (s.location ? [s.location] : []);
  const locTags = locRefs.map(lref => {
    const l = findLocation(lref);
    return l ? `<span class="tag tag-location">${escapeHtml(l.name)}</span>` : '';
  }).join('');
  // Structural tags: dramatic_role + climax flags (orange)
  const structTags = [];
  if (s.dramatic_role) structTags.push(s.dramatic_role);
  if (s.is_inciting_incident) structTags.push('inciting');
  if (s.is_sequence_climax) structTags.push('seq-climax');
  if (s.is_act_climax) structTags.push('act-climax');
  if (s.is_story_climax) structTags.push('story-climax');
  const structHtml = structTags.map(t => `<span class="tag tag-struct">${t}</span>`).join('');
  // Arc beat indicator dots
  const arcBeatDots = (s.arc_beats || []).map(ab => {
    const c = (story.characters || []).find(x => x.id === ab.character || String(x.id) === String(ab.character));
    const color = c ? roleColor(c.role || c.story_role || '') : '#8a8a8a';
    const label = c ? `${c.name}: ${ab.label || ''}` : '';
    return `<span class="arc-beat-dot-scene" style="background:${color}" title="${escapeHtml(label)}"></span>`;
  }).join('');
  return `
    <div class="scene-item" data-id="${s.id}">
      <div class="scene-number">${String(s.order || 0).padStart(2, '0')}</div>
      <div class="scene-body">
        <div class="scene-heading">${s.title || s.id}</div>
        ${s.heading ? `<div class="panel-muted" style="font-size:var(--font-size-xs);margin-top:2px;">${escapeHtml(s.heading)}</div>` : ''}
        <div class="scene-meta">${charTags}${locTags}${structHtml}${arcBeatDots}</div>
      </div>
    </div>
  `;
}

function filterScenes(query) {
  if (!query.trim()) { renderSceneList(allScenes); return; }
  const q = query.toLowerCase();
  const filtered = allScenes.filter(s => {
    if ((s.heading || '').toLowerCase().includes(q)) return true;
    if ((s.characters || []).some(cid => {
      const c = (story.characters || []).find(x => x.id === cid);
      return c && c.name.toLowerCase().includes(q);
    })) return true;
    if ((s.locations || []).some(lid => {
      const l = findLocation(lid);
      return l && l.name.toLowerCase().includes(q);
    })) return true;
    return false;
  });
  renderSceneList(filtered);
}

// ─── Locations View ────────────────────────────────────────────────────────────
function buildLocationsView() {
  const locs = story.locations || [];
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
      const v = findLocation(l.variant_of);
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
}

// ─── Plots View ────────────────────────────────────────────────────────────────
const PLOT_TYPE_COLORS = {
  Contradictory: '#e07070',
  Resonant: '#7b9cf0',
  Complicating: '#e0a86b',
  Setup: '#6bbfb0',
};

function plotScopeBadge(pl) {
  if (pl.plot_scope === 'main') {
    const arc = pl.value_arc || '';
    return `<span class="tag" style="background:rgba(176,123,224,0.18);color:#b07be0">MAIN${arc ? ' · ' + arc.toUpperCase() : ''}</span>`;
  }
  const pt = pl.plot_type || '';
  if (pt) {
    const col = PLOT_TYPE_COLORS[pt] || '#888';
    return `<span class="tag" style="background:${col}22;color:${col}">${pt.toUpperCase()}</span>`;
  }
  return '';
}

function buildPlotsView() {
  const plots = story.plots || [];
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
      const c = (story.characters || []).find(x => x.id === cid || String(x.id) === String(cid));
      return c ? `<span class="tag tag-char">${c.name}</span>` : '';
    }).join('');
    const scopeBadge = plotScopeBadge(pl);
    return `
      <div class="entity-card" data-id="${pl.id}" onclick="DASH.showPlotPanel('${pl.id}')">
        <div class="entity-card-pip" style="background:${pl.plot_scope === 'main' ? '#b07be0' : (PLOT_TYPE_COLORS[pl.plot_type] || '#888')}"></div>
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
    html += `<div class="story-section-title" style="margin-bottom:6px">Main Plot</div>`;
    html += main.map(renderPlotCard).join('');
  }
  if (subs.length) {
    if (main.length) html += `<div class="story-section-title" style="margin:12px 0 6px">Subplots</div>`;
    html += subs.map(renderPlotCard).join('');
  }
  list.innerHTML = html;
}


function buildRelationshipsView() {
  const rels = story.relationships || [];
  document.getElementById('relationships-subtitle').textContent = rels.length + ' relationships';
  const list = document.getElementById('relationship-list');

  if (!rels.length) {
    list.innerHTML = '<div class="empty-state"><div class="empty-state-title">No relationships</div></div>';
    return;
  }

  list.innerHTML = rels.map(rel => {
    const charA = (story.characters || []).find(c => c.id === rel.characters[0]);
    const charB = (story.characters || []).find(c => c.id === rel.characters[1]);
    const pa = (rel.perspectives || {})[rel.characters[0]] || {};
    const pb = (rel.perspectives || {})[rel.characters[1]] || {};

    const charTags = rel.characters.map(cid => {
      const c = (story.characters || []).find(x => x.id === cid);
      return c ? `<span class="tag tag-char">${c.name}</span>` : '';
    }).join('');

    const types = new Set();
    if (pa.type) types.add(pa.type);
    if (pb.type) types.add(pb.type);
    const typeTags = [...types].map(t =>
      `<span class="tag" style="background:${relTypeColor(t)}22;color:${relTypeColor(t)}">${t}</span>`
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

    const pipColor = types.size ? relTypeColor(types.values().next().value) : '#8a8a8a';

    return `
      <div class="entity-card" data-id="${rel.id}" onclick="DASH.showRelationshipPanel(story.relationships.find(r=>r.id==='${rel.id}'))">
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
}

// ─── Worlds View ───────────────────────────────────────────────────────────────
function buildWorldsView() {
  const worlds = story.worlds || [];
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
      const v = (story.worlds || []).find(x => x.id === w.variant_of);
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
}

// ─── Story View ────────────────────────────────────────────────────────────────
function buildStoryView() {
  const p = story.project || {};
  const mem = story.story_memory || {};

  document.getElementById('story-project-name').textContent = p.name || 'Story';
  document.getElementById('story-subtitle').textContent = [p.genre, p.setting].filter(Boolean).join(' · ');

  const body = document.getElementById('story-body');

  // Project stats
  const statsGrid = [
    { v: p.scene_count     || (story.scenes     || []).length, l: 'Scenes' },
    { v: p.character_count || (story.characters || []).length, l: 'Characters' },
    { v: p.location_count  || (story.locations  || []).length || null, l: 'Locations' },
    { v: p.world_count     || (story.worlds     || []).length || null, l: 'Worlds' },
    { v: p.plot_count      || (story.plots      || []).length || null, l: 'Plots' },
    { v: p.sequence_count  || (story.sequences  || []).length, l: 'Sequences' },
    { v: p.act_count       || (story.acts       || []).length, l: 'Acts' },
  ].filter(s => s.v != null && s.v > 0);

  const statsHtml = `
    <div>
      <div class="story-section-title">Project</div>
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
    const scene = (story.scenes || []).find(s => String(s.id) === String(sid));
    const label = scene ? scene.title : sid;
    keyScenes.push(`<div style="margin-bottom:6px"><span style="color:var(--muted-foreground);font-size:var(--font-size-xs);text-transform:uppercase;letter-spacing:0.06em">Inciting Incident</span><div style="margin-top:2px"><button class="entity-link" onclick="DASH.showScenePanel('${sid}')" style="font-size:var(--font-size-sm);padding:0;background:none;border:none;cursor:pointer;color:var(--accent);text-decoration:underline">${label}</button></div></div>`);
  }
  if (p.story_climax_scene_id) {
    const sid = p.story_climax_scene_id;
    const scene = (story.scenes || []).find(s => String(s.id) === String(sid));
    const label = scene ? scene.title : sid;
    keyScenes.push(`<div style="margin-bottom:6px"><span style="color:var(--muted-foreground);font-size:var(--font-size-xs);text-transform:uppercase;letter-spacing:0.06em">Story Climax</span><div style="margin-top:2px"><button class="entity-link" onclick="DASH.showScenePanel('${sid}')" style="font-size:var(--font-size-sm);padding:0;background:none;border:none;cursor:pointer;color:var(--accent);text-decoration:underline">${label}</button></div></div>`);
  }

  const structureHtml = (structure.length || keyScenes.length) ? `
    <div>
      <div class="story-section-title">Structure</div>
      <div style="padding:12px;background:var(--card);border:1px solid var(--border);border-radius:var(--radius)">
        ${structure.join('')}
        ${keyScenes.join('')}
      </div>
    </div>` : '';

  // Plots
  const plots = story.plots || [];
  const mainPlots = plots.filter(p => p.plot_scope === 'main');
  const subPlots = plots.filter(p => p.plot_scope !== 'main');
  const allPlotItems = [...mainPlots, ...subPlots];
  const plotsHtml = allPlotItems.length ? `
    <div>
      <div class="story-section-title">Active plot threads</div>
      <div class="plot-list">
        ${allPlotItems.map(pl => {
          const scope = pl.plot_scope === 'main' ? 'MAIN' : (pl.plot_type || '');
          const col = pl.plot_scope === 'main' ? '#b07be0' : (PLOT_TYPE_COLORS[pl.plot_type] || '#888');
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
      <div class="story-section-title">Continuity risks</div>
      <div class="risk-list">
        ${risks.map(r => `<div class="risk-item">${r}</div>`).join('')}
      </div>
    </div>` : '';

  // Hermes ask button
  const hermesHtml = p.name ? `
    <div style="padding-top:4px;">
      <button class="btn btn-hermes" data-hermes-send="Give me an overview of ${p.name}.">Ask Hermes about this story</button>
    </div>` : '';

  body.innerHTML = statsHtml + structureHtml + plotsHtml + risksHtml + hermesHtml;
}

// ─── Detail Panel ──────────────────────────────────────────────────────────────
function openPanel() { document.getElementById('detail-panel').classList.add('open'); }
function closePanel() { document.getElementById('detail-panel').classList.remove('open'); }

// ─── Sections Renderer ───────────────────────────────────────────────────────
function renderSectionsHtml(entityType, slug) {
  const data = (window.__SECTIONS__ && window.__SECTIONS__[entityType] && window.__SECTIONS__[entityType][slug]);
  if (!data) return '';
  return Object.entries(data).map(([name, content]) => `
    <div>
      <div class="panel-section-title">${name}</div>
      <div class="panel-text">${escapeHtml(content).replace(/\n/g, '<br>')}</div>
    </div>
  `).join('');
}

function arcSectionHtml(char) {
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
            <span class="arc-beat-dot" style="background:${roleColor(char.role || char.story_role || '')}"></span>
            <span style="font-size:var(--font-size-sm)">${escapeHtml(b.label || b.id)}</span>
            <span class="panel-muted" style="margin-left:auto;font-size:var(--font-size-xs)">${escapeHtml(b.shift || '')}</span>
          </div>
        `).join('')}
      </div>`;
  }
  return `
    <div class="panel-muted" style="font-size:var(--font-size-sm)">No beats designed</div>
    <button class="btn btn-hermes" data-hermes-send="Design a character arc for ${char.name} showing their value shift across the story.">Design arc with Hermes</button>`;
}

function showCharacterPanel(char) {
  document.getElementById('panel-type').textContent = char.role || char.story_role || 'Character';
  document.getElementById('panel-name').textContent = char.name;

  // Scenes: char.scenes is normalised to an array of scene ids (strings)
  const scenes = (char.scenes || []).map(sid => {
    const s = (story.scenes || []).find(x => String(x.id) === String(sid));
    if (s) {
      const num = s.number != null ? String(s.number) : '';
      const label = num ? `${num}. ${s.title || s.id}` : (s.title || s.id);
      return `<span class="tag tag-scene" style="cursor:pointer" onclick="DASH.showScenePanel('${s.id}')">${label}</span>`;
    }
    return sid ? `<span class="tag tag-scene">${sid}</span>` : '';
  }).filter(Boolean).join('');

  // Relationships: use relationships[] (new schema) with type + strength
  const rels = (char.relationships || []).map(rel => {
    const c = (story.characters || []).find(x => x.id === rel.with);
    const nameEl = c
      ? `<button class="relationship-name entity-link" onclick="DASH.showCharacterPanel(story.characters.find(x=>x.id==='${c.id}'))">${c.name}</button>`
      : `<span class="relationship-name">${rel.with}</span>`;
    const secretIcon = rel.secret ? ' 🔒' : '';
    const typeTag = rel.type ? `<span class="tag" style="background:${relTypeColor(rel.type)}22;color:${relTypeColor(rel.type)}">${rel.type}</span>` : '';
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
      ${arcSectionHtml(char)}
    </div>
    ${renderSectionsHtml('character', char.id)}
  `;

  document.getElementById('panel-footer').innerHTML = `
    <button class="btn btn-hermes" data-hermes-send="Tell me more about ${char.name}'s character development.">Ask Hermes about ${char.name}</button>
  `;

  openPanel();

  if (network) {
    network.selectNodes([char.id]);
    network.focus(char.id, { scale: 1.2, animation: { duration: 400, easingFunction: 'easeInOutQuad' } });
  }
}

function showScenePanel(sceneId) {
  const scene = (story.scenes || []).find(s => String(s.id) === String(sceneId));
  if (!scene) return;

  document.querySelectorAll('.scene-item').forEach(el => el.classList.remove('selected'));
  const sceneEl = document.querySelector(`.scene-item[data-id="${sceneId}"]`);
  if (sceneEl) sceneEl.classList.add('selected');

  document.getElementById('panel-type').textContent = 'Scene';
  document.getElementById('panel-name').textContent = scene.title || scene.id;

  const chars = (scene.characters || []).map(cid => {
    const c = (story.characters || []).find(x => x.id === cid || String(x.id) === String(cid));
    return c
      ? `<button class="entity-link" onclick="DASH.showCharacterPanel(story.characters.find(x=>x.id==='${c.id}'))" style="border-left:2px solid ${roleColor(c.role)}">${c.name}</button>`
      : '';
  }).filter(Boolean).join('');

  const locs = (scene.locations || []).map(lref => {
    const l = findLocation(lref);
    return l ? `<button class="entity-link" onclick="DASH.showLocationPanel('${l.id}')">${l.name}</button>` : '';
  }).filter(Boolean).join('');

  // Plots: backend populates scene.plots from plot setups/payoffs
  const plotRefs = (scene.plots || []);
  const plots = plotRefs.map(pref => {
    const pid = (typeof pref === 'object' && pref !== null) ? pref.id : pref;
    const beat = (typeof pref === 'object' && pref !== null) ? (pref.beat || '') : '';
    const pl = (story.plots || []).find(x => x.id === pid || String(x.id) === String(pid));
    if (!pl) return '';
    const scope = pl.plot_scope === 'main' ? 'MAIN' : (pl.plot_type || '');
    const col = pl.plot_scope === 'main' ? '#b07be0' : (PLOT_TYPE_COLORS[pl.plot_type] || '#888');
    const beatLabel = beat ? ` · ${beat.toUpperCase()}` : '';
    const scopeLabel = scope ? ` · ${scope}` : '';
    return `<button class="entity-link" onclick="DASH.showPlotPanel('${pl.id}')" style="border-left:2px solid ${col}">${pl.name}<span style="color:${col};font-size:var(--font-size-xs);margin-left:4px">${scopeLabel}${beatLabel}</span></button>`;
  }).filter(Boolean).join('');

  // Content from __SECTIONS__.scenes[slug]["Content"]
  let contentHtml = '';
  const sections = window.__SECTIONS__;
  const sceneContent = sections?.scene?.[sceneId]?.Content;
  if (sceneContent) {
    contentHtml = `<div class="fountain-content">${escapeHtml(sceneContent)}</div>`;
  } else {
    contentHtml = '<div class="panel-muted">No content yet.</div>';
  }

  // Dramatic metadata — only show positive values
  const dramaTags = [];
  if (scene.dramatic_role) dramaTags.push({ l: 'role', v: scene.dramatic_role });
  if (scene.is_inciting_incident) dramaTags.push({ l: 'inciting', v: 'Inciting Incident' });
  if (scene.is_sequence_climax) dramaTags.push({ l: 'seq-climax', v: 'Sequence Climax' });
  if (scene.is_act_climax) dramaTags.push({ l: 'act-climax', v: 'Act Climax' });
  if (scene.is_story_climax) dramaTags.push({ l: 'story-climax', v: 'Story Climax' });

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
      <div class="panel-muted">${escapeHtml(scene.heading)}</div>
    </div>` : ''}
    <div>
      <div class="panel-section-title">Content</div>
      ${contentHtml}
    </div>
  `;

  document.getElementById('panel-footer').innerHTML = `
    <button class="btn btn-hermes" data-hermes-send="What happens in ${scene.title || scene.id}?">Ask Hermes about this scene</button>
  `;

  openPanel();
}

function escapeHtml(text) {
  return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function showLocationPanel(locId) {
  // Deselect all entity cards, select the one clicked
  document.querySelectorAll('#location-list .entity-card').forEach(el => el.classList.remove('selected'));
  const card = document.querySelector(`#location-list .entity-card[data-id="${locId}"]`);
  if (card) card.classList.add('selected');

  const loc = (story.locations || []).find(l => l.id === locId);
  if (!loc) return;

  document.getElementById('panel-type').textContent = 'Location';
  document.getElementById('panel-name').textContent = loc.name;

  // Backend gives loc.scenes as heading strings; find scene objects by heading
  const sceneRefs = loc._scene_headings || loc.scenes || [];
  const scenes = sceneRefs.map(ref => {
    const s = (story.scenes || []).find(x =>
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
  const appearScenes = (story.scenes || []).filter(s => s.location === loc.id);
  const appearsIn = appearScenes.map(s => {
    const num = s.number != null ? String(s.number) : '';
    const label = num ? `${num}. ${s.heading || s.id}` : (s.heading || s.id);
    return `<span class="tag tag-scene" style="cursor:pointer" onclick="DASH.showScenePanel('${s.id}')">${label}</span>`;
  }).join('');

  // Characters in this location (via their scenes)
  const charIds = new Set();
  sceneRefs.forEach(ref => {
    const s = (story.scenes || []).find(x => x.heading === ref || String(x.id) === String(ref));
    if (s) (s.characters || []).forEach(cid => charIds.add(cid));
  });
  const charLinks = [...charIds].map(cid => {
    const c = (story.characters || []).find(x => x.id === cid || String(x.id) === String(cid));
    return c ? `<button class="entity-link" onclick="DASH.showCharacterPanel(story.characters.find(x=>x.id==='${c.id}'))" style="border-left:2px solid ${roleColor(c.role)}">${c.name}</button>` : '';
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
        const v = findLocation(loc.variant_of);
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
    ${renderSectionsHtml('location', loc.id)}
  `;

  document.getElementById('panel-footer').innerHTML = `
    <button class="btn btn-hermes" data-hermes-send="Describe ${loc.name} and its role in the story.">Ask Hermes about this location</button>
  `;

  openPanel();
}

function showPlotPanel(plotId) {
  document.querySelectorAll('#plot-list .entity-card').forEach(el => el.classList.remove('selected'));
  const card = document.querySelector(`#plot-list .entity-card[data-id="${plotId}"]`);
  if (card) card.classList.add('selected');

  const plot = (story.plots || []).find(p => p.id === plotId || String(p.id) === String(plotId));
  if (!plot) return;

  const scope = plot.plot_scope === 'main' ? 'MAIN' : (plot.plot_type || '');
  const col = plot.plot_scope === 'main' ? '#b07be0' : (PLOT_TYPE_COLORS[plot.plot_type] || '#888');
  const scopeHtml = scope ? `<span class="tag" style="background:${col}22;color:${col}">${scope}</span>` : '';
  const arcHtml = (plot.plot_scope === 'main' && plot.value_arc) ? `<div style="margin-top:4px"><span style="color:var(--muted-foreground);font-size:var(--font-size-xs);text-transform:uppercase;letter-spacing:0.06em">Value Arc</span><div style="font-size:var(--font-size-sm);color:var(--foreground)">${plot.value_arc}</div></div>` : '';

  document.getElementById('panel-type').textContent = plot.plot_scope === 'main' ? 'Main Plot' : 'Subplot';
  document.getElementById('panel-name').textContent = plot.name;

  const chars = (plot.characters || []).map(cid => {
    const c = (story.characters || []).find(x => x.id === cid || String(x.id) === String(cid));
    return c
      ? `<button class="entity-link" onclick="DASH.showCharacterPanel(story.characters.find(x=>x.id==='${c.id}'))" style="border-left:2px solid ${roleColor(c.role)}">${c.name}</button>`
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
      const sceneObj = (story.scenes || []).find(s => String(s.id) === String(item.scene_id));
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
    ${renderSectionsHtml('plot', plot.id)}
  `;

  document.getElementById('panel-footer').innerHTML = '';
  openPanel();
}

function showRelationshipPanel(rel) {
  const a = rel.characters[0];
  const b = rel.characters[1];
  const charA = (story.characters || []).find(c => c.id === a);
  const charB = (story.characters || []).find(c => c.id === b);
  const pa = (rel.perspectives || {})[a] || {};
  const pb = (rel.perspectives || {})[b] || {};

  const nameA = charA
    ? `<button class="entity-link" onclick="DASH.showCharacterPanel(story.characters.find(x=>x.id==='${a}'))" style="border-left:2px solid ${roleColor(charA.role)}">${charA.name}</button>`
    : `<span class="panel-muted">${a}</span>`;
  const nameB = charB
    ? `<button class="entity-link" onclick="DASH.showCharacterPanel(story.characters.find(x=>x.id==='${b}'))" style="border-left:2px solid ${roleColor(charB.role)}">${charB.name}</button>`
    : `<span class="panel-muted">${b}</span>`;

  function perspectiveHtml(charName, charRole, p) {
    if (!charName) return '';
    const col = relTypeColor(p.type);
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
    const s = (story.scenes || []).find(x => String(x.id) === String(sid));
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
      <div class="panel-text">${escapeHtml(rel.history).replace(/\n/g, '<br>')}</div>
    </div>` : ''}
  `;

  document.getElementById('panel-footer').innerHTML = `
    <button class="btn btn-hermes" data-hermes-send="Update the relationship between ${charA?.name || a} and ${charB?.name || b}. Current status: ${rel.status || 'active'}. Tell me what changed and why.">Edit with Hermes</button>
  `;

  openPanel();
}

function showSequencePanel(seqId) {
  const seq = (story.sequences || []).find(s => s.id === seqId);
  if (!seq) return;

  document.getElementById('panel-type').textContent = 'Sequence';
  document.getElementById('panel-name').textContent = seq.title || seq.id;

  const sceneRows = (seq.scenes_list || []).map((sid, i) => {
    const scene = (story.scenes || []).find(s => s.id === sid);
    if (!scene) return '';
    return `<div class="beat-row" onclick="DASH.showScenePanel('${sid}')">
      <span class="beat-scene">${i + 1}. ${scene.title || sid}</span>
      ${scene.heading ? `<span class="beat-desc">${escapeHtml(scene.heading)}</span>` : ''}
    </div>`;
  }).join('');

  // Plot threads in this sequence with scope/type
  const plotRows = (seq.plots || []).map(p => {
    const pl = (story.plots || []).find(x => x.id === p.id);
    if (!pl) return '';
    const scope = pl.plot_scope === 'main' ? 'MAIN' : (pl.plot_type || '');
    const col = pl.plot_scope === 'main' ? '#b07be0' : (PLOT_TYPE_COLORS[pl.plot_type] || '#888');
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
  `;

  document.getElementById('panel-footer').innerHTML = `
    <button class="btn btn-hermes" data-hermes-send="What is the dramatic function of the sequence '${seq.title || seq.id}'?">Ask Hermes about this sequence</button>
  `;

  openPanel();
}

function showActPanel(actId) {
  const act = (story.acts || []).find(a => a.id === actId);
  if (!act) return;

  document.getElementById('panel-type').textContent = 'Act';
  document.getElementById('panel-name').textContent = act.title || act.id;

  const seqRows = (act.sequences_list || []).map(sid => {
    const seq = (story.sequences || []).find(s => s.id === sid);
    return seq ? `<div class="beat-row" onclick="DASH.showSequencePanel('${sid}')">
      <span class="beat-scene">${seq.title || sid}</span>
      <span class="beat-desc">${seq.scene_count || 0} scenes</span>
    </div>` : '';
  }).join('');

  // Plot threads in this act with scope/type
  const plotRows = (act.plots || []).map(p => {
    const pl = (story.plots || []).find(x => x.id === p.id);
    if (!pl) return '';
    const scope = pl.plot_scope === 'main' ? 'MAIN' : (pl.plot_type || '');
    const col = pl.plot_scope === 'main' ? '#b07be0' : (PLOT_TYPE_COLORS[pl.plot_type] || '#888');
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
      const projectSpine = (story.project || {}).spine;
      const actObj = act.act_objective;
      if (!projectSpine && !actObj) return '';
      return `<div style="margin-top:8px">
        ${projectSpine ? `<div style="font-size:var(--font-size-xs);color:var(--muted-foreground);margin-bottom:4px">Story spine: <span style="font-style:italic">${projectSpine}</span></div>` : ''}
        ${actObj ? `<div style="font-size:var(--font-size-xs);color:var(--muted-foreground)">Act objective: <span style="color:var(--foreground);font-weight:500">${actObj}</span></div>` : ''}
      </div>`;
    })()}
    ${plotRows ? `<div><div class="panel-section-title">Plot threads</div>${plotRows}</div>` : ''}
    ${seqRows ? `<div><div class="panel-section-title">Sequences (${act.sequence_count || 0})</div>${seqRows}</div>` : '<div class="panel-muted">No sequences in this act yet.</div>'}
  `;

  document.getElementById('panel-footer').innerHTML = `
    <button class="btn btn-hermes" data-hermes-send="What is the dramatic arc of '${act.title || act.id}'?">Ask Hermes about this act</button>
  `;

  openPanel();
}

function showWorldPanel(worldId) {
  document.querySelectorAll('#world-list .entity-card').forEach(el => el.classList.remove('selected'));
  const card = document.querySelector(`#world-list .entity-card[data-id="${worldId}"]`);
  if (card) card.classList.add('selected');

  const world = (story.worlds || []).find(w => w.id === worldId);
  if (!world) return;

  document.getElementById('panel-type').textContent = 'World';
  document.getElementById('panel-name').textContent = world.name;

  const rules = (world.rules || []).map(r =>
    `<div class="world-rule">${r}</div>`
  ).join('');

  const sections = (world.sections || []).join(', ');

  // Plots in this world
  const worldPlots = (story.plots || []).filter(pl =>
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
        const v = (story.worlds || []).find(w => w.id === world.variant_of);
        return v ? `<button class="entity-link" onclick="DASH.showWorldPanel('${v.id}')">${v.name}</button>` : `<div class="panel-text" style="color:#e0a86b">${world.variant_of}</div>`;
      })()}
    </div>` : ''}
    ${plotLinks ? `<div>
      <div class="panel-section-title">Plot threads</div>
      <div style="display:flex;flex-direction:column;gap:4px;">${plotLinks}</div>
    </div>` : ''}
    ${renderSectionsHtml('world', world.id)}
  `;

  document.getElementById('panel-footer').innerHTML = '';
  openPanel();
}

// ═══════════════════════════════════════════════════════════════════════════════
// SCRIPT VIEW & STATISTICS PANEL
// ═══════════════════════════════════════════════════════════════════════════════

// ─── Helpers ───────────────────────────────────────────────────────────────────
function fmtDurationShort(sec) {
  if (!sec || isNaN(sec)) return '0s';
  sec = Math.round(sec);
  if (sec < 60) return sec + 's';
  const m = Math.floor(sec / 60);
  if (m < 60) return m + 'm';
  return Math.floor(m / 60) + 'h ' + (m % 60) + 'm';
}

function fmtDuration(sec) {
  sec = Math.round(sec || 0);
  const h = Math.floor(sec / 3600);
  const m = Math.floor((sec % 3600) / 60);
  const s = sec % 60;
  if (h > 0) return h + ':' + String(m).padStart(2,'0') + ':' + String(s).padStart(2,'0');
  return m + ':' + String(s).padStart(2,'0');
}

function setEl(id, val) {
  const el = document.getElementById(id);
  if (el) el.textContent = val;
}

function setBar(baseId, count, total) {
  const pct = total > 0 ? Math.round((count / total) * 100) : 0;
  setEl(baseId, count + ' (' + pct + '%)');
  const bar = document.getElementById(baseId + '_bar');
  if (bar) bar.style.width = pct + '%';
}

// ─── Sortable plain table ───────────────────────────────────────────────────────
// No DataTables dependency needed for 5-20 rows.
function sortTable(tableId, colIdx) {
  const table = document.getElementById(tableId);
  if (!table) return;
  const th = table.querySelectorAll('thead th')[colIdx];
  const isNum = th.dataset.type === 'num';
  const wasAsc = th.classList.contains('sort-asc');
  const wasDesc = th.classList.contains('sort-desc');
  // Reset all headers
  table.querySelectorAll('thead th').forEach(h => h.classList.remove('sort-asc','sort-desc'));
  if (!wasAsc && !wasDesc) {
    th.classList.add(isNum ? 'sort-desc' : 'sort-asc');
  } else {
    th.classList.add(wasDesc ? 'sort-asc' : 'sort-desc');
  }
  const asc = th.classList.contains('sort-asc');

  const tbody = table.querySelector('tbody');
  const rows = [...tbody.querySelectorAll('tr')];
  rows.sort((a, b) => {
    const aText = a.cells[colIdx]?.textContent.trim() || '';
    const bText = b.cells[colIdx]?.textContent.trim() || '';
    if (isNum) {
      // extract leading number (handles "1:23" duration, plain integers, etc.)
      const aNum = parseFloat(a.cells[colIdx]?.dataset.sort || aText) || 0;
      const bNum = parseFloat(b.cells[colIdx]?.dataset.sort || bText) || 0;
      return asc ? aNum - bNum : bNum - aNum;
    }
    return asc ? aText.localeCompare(bText) : bText.localeCompare(aText);
  });
  rows.forEach(r => tbody.appendChild(r));
}

// ─── Script View ────────────────────────────────────────────────────────────────
let _scriptBuilt = false;

function buildScriptView() {
  const stats = window.__SCREENPLAY_STATS__;
  const container = document.getElementById('screenplay-container');
  if (!container) return;

  // No stats or no scriptHtml → empty state
  if (!stats || !stats.scriptHtml) {
    container.innerHTML = '<div class="script-empty"><div class="empty-state-title">No scenes with content yet</div><div class="empty-state-sub">Add content to your scenes to see the script view.</div></div>';
    _scriptBuilt = true;
    return;
  }

  const doc = document.createElement('div');
  doc.className = 'screenplay-doc screenplay-content';

  // ── Title page ──
  if (stats.titlePage) {
    const tp = stats.titlePage;
    const hasContent = Object.values(tp).some(arr => Array.isArray(arr) ? arr.length > 0 : !!arr);
    if (hasContent) {
      const titleTokens = (tp.cc || []);
      const titleText = titleTokens.map(t => t.text || t).join('\n');
      const tl = (tp.tl || []).map(t => t.text || t).join('<br>');
      const tr = (tp.tr || []).map(t => t.text || t).join('<br>');
      const bl = (tp.bl || []).map(t => t.text || t).join('<br>');
      const br = (tp.br || []).map(t => t.text || t).join('<br>');

      // Split title page tokens into title + credit lines
      const titleLines = titleText.split('\n');
      const titleName = titleLines[0] || '';
      const creditLines = titleLines.slice(1).join('<br>');

      const tpEl = document.createElement('div');
      tpEl.className = 'screenplay-title-page';
      tpEl.innerHTML = `
        <div class="title-tl">${tl}</div>
        <div class="title-tc"></div>
        <div class="title-tr">${tr}</div>
        <div class="title-cc">
          <span class="tp-title">${escapeHtml(titleName)}</span>
          ${creditLines ? `<span class="tp-credit">${creditLines}</span>` : ''}
        </div>
        <div class="title-bl">${bl}</div>
        <div class="title-br">${br}</div>
      `;
      doc.appendChild(tpEl);
    }
  }

  // ── Screenplay body (server-rendered HTML) ──
  const body = document.createElement('div');
  body.innerHTML = stats.scriptHtml;

  // Insert soft page breaks every ~8 scene headings
  let headingCount = 0;
  let pageNum = 1;
  body.querySelectorAll('.fountain-scene_heading').forEach(el => {
    headingCount++;
    if (headingCount > 1 && headingCount % 8 === 1) {
      pageNum++;
      const br = document.createElement('hr');
      br.className = 'screenplay-page-break';
      br.setAttribute('data-page', 'p. ' + pageNum);
      el.parentNode.insertBefore(br, el);
    }
  });

  doc.appendChild(body);

  // ── Wire scene heading clicks ──
  doc.querySelectorAll('.fountain-scene_heading').forEach(el => {
    const rawHeading = el.textContent.replace(/^\d+\.\s*/, '').toUpperCase().trim()
                                     .replace(/\s*\(.*\)\s*$/, '');
    const matched = (story && story.scenes || []).find(s => {
      const h = (s.heading || '').toUpperCase().trim().replace(/\s*\(.*\)\s*$/, '');
      return h === rawHeading;
    });
    if (matched) {
      el.style.cursor = 'pointer';
      el.addEventListener('click', () => {
        showScenePanel(matched.id);
      });
    }
  });

  // Subtitle
  const sceneCount = (story.scenes || []).length;
  const pages = stats.lengthStats && stats.lengthStats.pagesWhole || '?';
  setEl('script-subtitle', pages + ' p · ' + sceneCount + ' scenes');

  container.innerHTML = '';
  container.appendChild(doc);
  _scriptBuilt = true;
}

// ─── Statistics Panel ───────────────────────────────────────────────────────────
let _statsPopulated = false;
let _structuralStatsPopulated = false;
let _currentBarcodeMode = 'type';

function openStatsPanel() {
  if (!_scriptBuilt) buildScriptView();

  const stats = window.__SCREENPLAY_STATS__;
  if (!stats) {
    // No stats available — show panel with empty state message
    document.getElementById('stats-panel').classList.add('open');
    closePanel(); // close entity panel if open
    return;
  }

  if (!_statsPopulated) {
    populateStats(stats);
    _statsPopulated = true;
  }

  document.getElementById('stats-panel').classList.add('open');
  closePanel();

  // Re-render the active chart in case it was first rendered while hidden
  requestAnimationFrame(() => {
    const activeGroup = document.querySelector('.stats-group.active');
    if (activeGroup) {
      const id = activeGroup.id.replace('stats-group-', '');
      _renderChartsForGroup(id);
    }
  });
}

function closeStatsPanel() {
  document.getElementById('stats-panel').classList.remove('open');
}

function switchStatsGroup(group, btn) {
  document.querySelectorAll('.stats-group').forEach(g => g.classList.remove('active'));
  document.querySelectorAll('.stats-tab').forEach(b => b.classList.remove('active'));
  document.getElementById('stats-group-' + group).classList.add('active');
  btn.classList.add('active');
  // Charts must be drawn into a visible container
  requestAnimationFrame(() => _renderChartsForGroup(group));
}

function _renderChartsForGroup(group) {
  const stats = window.__SCREENPLAY_STATS__;
  if (!stats) return;
  // requestAnimationFrame ensures layout has settled before reading dimensions
  requestAnimationFrame(() => {
    if (group === 'overview')    renderDurationChart(stats);
    if (group === 'characters')  renderCharacterChart(stats);
    if (group === 'scenes')      renderBarcodeChart(_currentBarcodeMode);
    // No D3 charts for 'structure' — static HTML rendered in populateStructuralStats()
  });
}

// ─── Populate all stat elements ─────────────────────────────────────────────────
function populateStats(stats) {
  const ls = stats.lengthStats    || {};
  const ds = stats.durationStats  || {};
  const cs = stats.characterStats || {};
  const lo = stats.locationStats  || {};
  const ss = stats.sceneStats     || {};

  // ── Overview: Length ──
  setEl('lengthStats-pagesWhole', ls.pagesWhole  || '—');
  setEl('lengthStats-scenes',     ls.scenes      || '—');
  setEl('lengthStats-words',      (ls.words      || 0).toLocaleString());
  setEl('lengthStats-lines',      (ls.lines      || 0).toLocaleString());
  setEl('lengthStats-characters', (ls.characters || 0).toLocaleString());

  // ── Overview: Duration ──
  setEl('durationStats-total',    fmtDurationShort(ds.total));
  setEl('durationStats-action',   fmtDurationShort(ds.action));
  setEl('durationStats-dialogue', fmtDurationShort(ds.dialogue));

  const totalMin = Math.round((ds.total || 0) / 60);
  const actionPct = ds.total > 0 ? Math.round(((ds.action || 0) / ds.total) * 100) : 0;
  const lengthLabel = totalMin < 60 ? 'a short film' :
                      totalMin < 90 ? 'an hour-long film' :
                      totalMin < 120 ? 'a feature film' : 'an epic feature';
  const balanceLabel = actionPct > 65 ? 'action-heavy' :
                       actionPct < 35 ? 'dialogue-heavy' : 'balanced';
  setEl('durationStats-summary',
    `The screenplay is the length of ${lengthLabel}. It is ${balanceLabel} (${actionPct}% action).`);

  // ── Characters ──
  setEl('characterStats-count',      cs.characterCount || (cs.characters || []).length);
  setEl('characterStats-monologues', cs.monologues || 0);

  // Character table
  const chars = cs.characters || [];
  const cTbody = document.querySelector('#characterStats-table tbody');
  if (cTbody) {
    cTbody.innerHTML = chars.map(c => {
      const secs = c.secondsSpoken || 0;
      return `<tr>
        <td><span class="char-pip" style="background:${c.color || '#888'}"></span>${escapeHtml(c.name)}</td>
        <td data-sort="${secs}">${fmtDuration(secs)}</td>
        <td>${c.speakingParts || 0}</td>
        <td>${c.wordsSpoken || 0}</td>
        <td>${c.monologues || 0}</td>
      </tr>`;
    }).join('');
    // Default sort: duration desc
    sortTable('characterStats-table', 1);
  }

  // ── Scenes: counts ──
  const scenes = ss.scenes || [];
  setEl('sceneStats-count',    scenes.length || ls.scenes || 0);
  setEl('locationStats-count', lo.locationsCount || (lo.locations || []).length);

  // INT/EXT bars
  const tc = ss.typeCounts || {};
  const totalType = (tc.int || 0) + (tc.ext || 0) + (tc.mixed || 0);
  setBar('sceneprop-type_int',   tc.int   || 0, totalType);
  setBar('sceneprop-type_ext',   tc.ext   || 0, totalType);
  setBar('sceneprop-type_mixed', tc.mixed || 0, totalType);

  // Time-of-day bars
  const timec = ss.timeCounts || {};
  const totalTime = Object.values(timec).reduce((a, b) => a + b, 0);
  setBar('sceneprop-time_day',     timec.day     || 0, totalTime);
  setBar('sceneprop-time_night',   timec.night   || 0, totalTime);
  setBar('sceneprop-time_morning', timec.morning || 0, totalTime);
  setBar('sceneprop-time_evening', timec.evening || 0, totalTime);
  setBar('sceneprop-time_dawn',    timec.dawn    || 0, totalTime);
  setBar('sceneprop-time_dusk',    timec.dusk    || 0, totalTime);

  // Location table
  const locs = lo.locations || [];
  const lTbody = document.querySelector('#locationStats-table tbody');
  if (lTbody) {
    lTbody.innerHTML = locs.map(l => {
      const type = (l.interior_exterior || []).join('/').toUpperCase() || '—';
      return `<tr>
        <td><span class="char-pip" style="background:${l.color || '#888'}"></span>${escapeHtml(l.name)}</td>
        <td>${l.number_of_scenes || 0}</td>
        <td>${type}</td>
      </tr>`;
    }).join('');
    sortTable('locationStats-table', 1);
  }

  // ── Structural stats (from window.__STRUCTURAL_STATS__) ──
  if (!_structuralStatsPopulated) {
    populateStructuralStats();
    _structuralStatsPopulated = true;
  }
}

function populateStructuralStats() {
  const ss = window.__STRUCTURAL_STATS__;
  if (!ss) return;

  setEl('structStats-scenes', ss.sceneCount || '—');
  setEl('structStats-sequences', ss.sequenceCount || '—');
  setEl('structStats-acts', ss.actCount || '—');

  // Scene status bars
  const statusContainer = document.getElementById('structStats-status-bars');
  if (statusContainer) {
    const statusColors = { planned: '#888', drafted: '#e0c96b', written: '#6bbfb0', locked: '#7b9cf0' };
    const status = ss.sceneStatus || {};
    const total = Object.values(status).reduce((a, b) => a + b, 0);
    statusContainer.innerHTML = Object.entries(status).map(([key, count]) => {
      const pct = total > 0 ? Math.round((count / total) * 100) : 0;
      return `<div class="duration-bar-row">
        <span class="duration-bar-label">${escapeHtml(key)}</span>
        <div class="duration-bar-track"><div class="duration-bar-fill" style="background:${statusColors[key] || '#888'};width:${pct}%"></div></div>
        <span class="duration-bar-value">${count}</span>
      </div>`;
    }).join('') || '<div class="panel-muted" style="font-size:var(--font-size-xs);">No scenes.</div>';
  }

  // Dramatic role bars
  const roleContainer = document.getElementById('structStats-role-bars');
  if (roleContainer) {
    const roleColors = { setup: '#7b9cf0', complication: '#e0c96b', crisis: '#e07070', climax: '#b07be0', resolution: '#6bbfb0', transition: '#888', unset: '#444' };
    const roles = ss.sceneRoles || {};
    const total = Object.values(roles).reduce((a, b) => a + b, 0);
    roleContainer.innerHTML = Object.entries(roles).map(([key, count]) => {
      const pct = total > 0 ? Math.round((count / total) * 100) : 0;
      return `<div class="duration-bar-row">
        <span class="duration-bar-label">${escapeHtml(key)}</span>
        <div class="duration-bar-track"><div class="duration-bar-fill" style="background:${roleColors[key] || '#888'};width:${pct}%"></div></div>
        <span class="duration-bar-value">${count}</span>
      </div>`;
    }).join('') || '<div class="panel-muted" style="font-size:var(--font-size-xs);">No roles assigned.</div>';
  }

  // Plot coverage bars
  const plotContainer = document.getElementById('structStats-plot-coverage');
  if (plotContainer) {
    const plotColors = { main: '#b07be0', Contradictory: '#e07070', Resonant: '#7b9cf0', Complicating: '#e0a86b', Setup: '#6bbfb0' };
    const coverage = ss.plotCoverage || [];
    if (coverage.length) {
      const maxCount = Math.max(...coverage.map(p => p.sceneCount));
      plotContainer.innerHTML = coverage.map(p => {
        const col = plotColors[p.plot_scope] || (plotColors[p.plot_type] || '#888');
        const pct = maxCount > 0 ? Math.round((p.sceneCount / maxCount) * 100) : 0;
        const label = p.plot_scope === 'main' ? `${p.name} (MAIN)` : p.name;
        return `<div class="duration-bar-row">
          <span class="duration-bar-label" style="color:${col}">${escapeHtml(label)}</span>
          <div class="duration-bar-track"><div class="duration-bar-fill" style="background:${col};width:${pct}%"></div></div>
          <span class="duration-bar-value">${p.sceneCount} (${p.coveragePct}%)</span>
        </div>`;
      }).join('');
    } else {
      plotContainer.innerHTML = '<div class="panel-muted" style="font-size:var(--font-size-xs);">No plot coverage data.</div>';
    }
  }

  // Act list
  const actContainer = document.getElementById('structStats-act-list');
  if (actContainer) {
    const acts = ss.acts || [];
    actContainer.innerHTML = acts.map(a =>
      `<div class="beat-row">
        <span class="beat-scene">${escapeHtml(a.title || a.id)}</span>
        <span class="beat-desc">${a.sceneCount || 0} scenes · ${a.sequenceCount || 0} sequences</span>
      </div>`
    ).join('') || '<div class="panel-muted" style="font-size:var(--font-size-xs);">No acts.</div>';
  }

  // Arc design summary
  const arcContainer = document.getElementById('structStats-arc-summary');
  if (arcContainer) {
    const chars = story.characters || [];
    const charsWithArcs = chars.filter(c => c.arc_type && c.arc_type !== 'absent' && c.arc_beats_list && c.arc_beats_list.length > 0);
    const totalArcBeats = chars.reduce((sum, c) => sum + (c.arc_beats_list ? c.arc_beats_list.length : 0), 0);
    if (charsWithArcs.length > 0) {
      arcContainer.innerHTML = `<div style="margin-bottom:6px;font-size:var(--font-size-sm);color:var(--foreground);margin-top:2px">${charsWithArcs.length} characters · ${totalArcBeats} beats designed</div>` +
        charsWithArcs.map(c => {
          const col = roleColor(c.role || c.story_role || '');
          return `<div style="display:flex;align-items:center;gap:6px;margin-bottom:4px">
            <span class="legend-dot" style="background:${col}"></span>
            <span style="font-size:var(--font-size-sm)">${escapeHtml(c.name)}</span>
            <span class="panel-muted" style="margin-left:auto;font-size:var(--font-size-xs)">${c.arc_type} · ${c.arc_beats_list.length} beats</span>
          </div>`;
        }).join('');
    } else {
      arcContainer.innerHTML = '<div class="panel-muted" style="font-size:var(--font-size-xs);">No character arcs designed.</div>';
    }
  }
}

// ─── D3 Charts ─────────────────────────────────────────────────────────────────
let _chartObservers = {};

function _ensureChartRendered(containerId, renderFn) {
  const container = document.getElementById(containerId);
  if (!container) return;
  // Clean up previous observer for this container
  if (_chartObservers[containerId]) {
    _chartObservers[containerId].disconnect();
    delete _chartObservers[containerId];
  }
  // Render immediately
  renderFn();
  // Observe resize — re-render when container reaches final size (after CSS transition)
  const ro = new ResizeObserver(entries => {
    for (const entry of entries) {
      if (entry.contentRect.width > 0) {
        renderFn();
      }
    }
  });
  ro.observe(container);
  _chartObservers[containerId] = ro;
}

function renderDurationChart(stats) {
  _ensureChartRendered('durationStats-lengthchart', () => {
    _renderDurationChart(stats);
  });
}

function _renderDurationChart(stats) {
  const container = document.getElementById('durationStats-lengthchart');
  if (!container || !window.d3) return;
  container.innerHTML = '';

  const ds = stats.durationStats || {};
  const actionData    = ds.lengthchart_action   || [];
  const dialogueData  = ds.lengthchart_dialogue || [];
  if (!actionData.length && !dialogueData.length) return;

  // Pad to same length
  const len = Math.max(actionData.length, dialogueData.length);
  const aData = actionData.concat(Array(len - actionData.length).fill(0));
  const dData = dialogueData.concat(Array(len - dialogueData.length).fill(0));

  const W = container.clientWidth  || 320;
  const H = container.clientHeight || 72;
  const mg = { top: 6, right: 8, bottom: 16, left: 26 };
  const w = W - mg.left - mg.right;
  const h = H - mg.top  - mg.bottom;

  const svg = d3.select(container).append('svg').attr('width', W).attr('height', H);
  const g   = svg.append('g').attr('transform', `translate(${mg.left},${mg.top})`);

  const x    = d3.scaleLinear().domain([0, len - 1]).range([0, w]);
  const maxY = d3.max([...aData, ...dData]) || 1;
  const y    = d3.scaleLinear().domain([0, maxY]).range([h, 0]);

  const area = (data, fill) => d3.area()
    .x((d, i) => x(i)).y0(h).y1(d => y(d))
    .curve(d3.curveCatmullRom)(data);
  const line = (data) => d3.line()
    .x((d, i) => x(i)).y(d => y(d))
    .curve(d3.curveCatmullRom)(data);

  g.append('path').attr('d', area(aData)).attr('fill', 'rgba(123,156,240,0.12)');
  g.append('path').attr('d', area(dData)).attr('fill', 'rgba(107,191,176,0.12)');
  g.append('path').attr('d', line(aData)).attr('fill','none').attr('stroke','#7b9cf0').attr('stroke-width',1.5);
  g.append('path').attr('d', line(dData)).attr('fill','none').attr('stroke','#6bbfb0').attr('stroke-width',1.5);

  g.append('g').attr('transform',`translate(0,${h})`)
    .call(d3.axisBottom(x).ticks(4).tickFormat(i => Math.round((i/(len-1||1))*100)+'%'))
    .selectAll('text').style('font-size','9px').attr('fill','var(--muted-foreground)');
  g.append('g')
    .call(d3.axisLeft(y).ticks(3).tickFormat(d => fmtDurationShort(d)))
    .selectAll('text').style('font-size','9px').attr('fill','var(--muted-foreground)');
  g.selectAll('.domain,.tick line').attr('stroke','rgba(255,255,255,0.12)');

  // Legend
  const leg = svg.append('g').attr('transform', `translate(${mg.left + w - 86},${mg.top + 2})`);
  leg.append('circle').attr('r',4).attr('cx',5).attr('cy',5).attr('fill','#7b9cf0');
  leg.append('text').attr('x',12).attr('y',9).text('Action').style('font-size','8px').attr('fill','var(--muted-foreground)');
  leg.append('circle').attr('r',4).attr('cx',5).attr('cy',17).attr('fill','#6bbfb0');
  leg.append('text').attr('x',12).attr('y',21).text('Dialogue').style('font-size','8px').attr('fill','var(--muted-foreground)');
}

function renderCharacterChart(stats) {
  const container = document.getElementById('characterStats-lengthchart');
  if (!container || !window.d3) return;
  container.innerHTML = '';

  const chars = ((stats.characterStats || {}).characters || []).slice(0, 8);
  if (!chars.length) return;

  const W  = container.clientWidth  || 320;
  const H  = container.clientHeight || 110;
  const mg = { top: 6, right: 8, bottom: 18, left: 70 };
  const w  = W - mg.left - mg.right;
  const h  = H - mg.top  - mg.bottom;

  const svg = d3.select(container).append('svg').attr('width',W).attr('height',H);
  const g   = svg.append('g').attr('transform',`translate(${mg.left},${mg.top})`);

  const maxSec = d3.max(chars, c => c.secondsSpoken || 0) || 1;
  const x = d3.scaleLinear().domain([0, maxSec]).range([0, w]);
  const y = d3.scaleBand().domain(chars.map(c => c.name)).range([0, h]).padding(0.25);

  g.selectAll('rect').data(chars).enter().append('rect')
    .attr('x', 0)
    .attr('y', d => y(d.name))
    .attr('height', y.bandwidth())
    .attr('width', d => x(d.secondsSpoken || 0))
    .attr('fill', d => d.color || '#7b9cf0')
    .attr('rx', 2);

  g.append('g').call(d3.axisLeft(y).tickSize(0))
    .selectAll('text').style('font-size','9px').attr('dx','-3').attr('fill','var(--muted-foreground)');
  g.append('g').attr('transform',`translate(0,${h})`)
    .call(d3.axisBottom(x).ticks(4).tickFormat(d => fmtDurationShort(d)))
    .selectAll('text').style('font-size','9px').attr('fill','var(--muted-foreground)');
  g.selectAll('.domain,.tick line').attr('stroke','rgba(255,255,255,0.12)');
}

function renderBarcodeChart(mode) {
  _currentBarcodeMode = mode;
  const container = document.getElementById('sceneStats-timechart');
  if (!container || !window.d3) return;
  container.innerHTML = '';

  const stats  = window.__SCREENPLAY_STATS__;
  const scenes = stats && stats.sceneStats && stats.sceneStats.scenes || [];
  if (!scenes.length) return;

  const TYPE_COL = { int:'#7b9cf0', ext:'#6bbfb0', mixed:'#e0a86b', other:'#555' };
  const TIME_COL = {
    dawn:'#e06b9b', morning:'#e07070', day:'#e0c96b',
    afternoon:'#e0c96b', evening:'#b07be0', dusk:'#6bbfb0',
    night:'#7b9cf0', continuous:'#555', later:'#555', unspecified:'#333'
  };

  const W   = container.clientWidth || 320;
  const H   = container.clientHeight || 44;
  const pad = 3;
  const bw  = Math.max(1.5, (W - pad * 2) / scenes.length);

  const svg = d3.select(container).append('svg').attr('width', W).attr('height', H);
  svg.selectAll('rect').data(scenes).enter().append('rect')
    .attr('x',      (d, i) => pad + i * bw)
    .attr('y',      0)
    .attr('width',  Math.max(1, bw - 0.5))
    .attr('height', H)
    .attr('fill',   d => mode === 'type'
      ? (TYPE_COL[d.locType] || TYPE_COL.other)
      : (TIME_COL[d.locTime] || TIME_COL.unspecified))
    .attr('rx', 1)
    .append('title').text(d => d.text || d.number);
}

// ─── switchView wrapper ────────────────────────────────────────────────────────
// Wraps the existing switchView to add script-tab lazy-build and stats panel cleanup.
// Must come AFTER the original switchView definition.
const _origSwitchView = switchView;
switchView = function(view, btn) {
  _origSwitchView(view, btn);

  if (view === 'script') {
    if (!_scriptBuilt) buildScriptView();
  } else {
    closeStatsPanel();
  }
};

// ─── Start ─────────────────────────────────────────────────────────────────────
// ─── Arc Graph & Graph Tabs ────────────────────────────────────────────────────

function switchGraphTab(tab) {
  document.querySelectorAll('.graph-tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.graph-tab-content').forEach(c => c.classList.remove('active'));
  document.getElementById('tab-' + tab)?.classList.add('active');
  const content = document.getElementById('graph-tab-' + tab);
  if (content) {
    content.classList.add('active');
    content.style.display = '';
  }
  const netLegend = document.getElementById('graph-legend');
  if (netLegend) netLegend.style.display = (tab === 'network') ? '' : 'none';
  if (tab === 'arcgraph') { buildCharsGrid(); buildArcGraph(); updateLegend(); }
}

/* ─── State ─────────────────────────────────────────────────── */
let arcUseSpline = false;
let arcShowLabels = true;
let arcMutedChars = new Set();

/* ─── Character cards ───────────────────────────────────────── */
function getArcTypeClass(type) {
  const map = {
    negative: 'arc-type-negative',
    positive: 'arc-type-positive',
    flat:     'arc-type-flat',
    ironic:   'arc-type-ironic',
    absent:   'arc-type-absent',
  };
  return map[type] || 'arc-type-flat';
}

function buildCharsGrid() {
  const grid = document.getElementById('chars-grid');
  if (!grid) return;
  grid.innerHTML = '';
  (story.characters || []).forEach(char => {
    const color = roleColor(char.role || char.story_role || '');
    const div = document.createElement('div');
    div.className = 'char-card';
    div.innerHTML = `
      <div class="char-name" style="color:${color}">${escapeHtml(char.name)}</div>
      <div class="char-role">
        <span class="char-role-dot" style="background:${color}"></span>
        ${escapeHtml(char.role || char.story_role || '')}
      </div>
      <div class="char-arc-type">
        <span class="arc-type-badge ${getArcTypeClass(char.arc_type)}">${char.arc_type || 'absent'}</span>
        ${char.arc_value ? `<span style="font-size:10px;color:var(--muted-foreground)">${escapeHtml(char.arc_value)}</span>` : ''}
      </div>
      ${char.arc_beat_count > 0
        ? `<div class="char-beat-count">${char.arc_beat_count} beat${char.arc_beat_count !== 1 ? 's' : ''}</div>`
        : `<div class="char-beat-count" style="color:#555">No arc designed</div>`}
    `;
    div.addEventListener('click', () => {
      const wasSelected = div.classList.contains('selected');
      document.querySelectorAll('.char-card').forEach(c => c.classList.remove('selected'));
      if (!wasSelected) {
        div.classList.add('selected');
        arcMutedChars = new Set((story.characters || []).filter(c => c.id !== char.id).map(c => c.id));
      } else {
        arcMutedChars = new Set();
      }
      buildArcGraph();
      updateLegend();
    });
    grid.appendChild(div);
  });
}

/* ─── Arc Graph ─────────────────────────────────────────────── */
const ARC_GW = 760;
const ARC_GH = 320;
const ARC_PAD = { top: 28, right: 40, bottom: 36, left: 42 };

function arcXScale(t) {
  return ARC_PAD.left + t * (ARC_GW - ARC_PAD.left - ARC_PAD.right);
}
function arcYScale(v) {
  return ARC_PAD.top + (1 - (v + 1) / 2) * (ARC_GH - ARC_PAD.top - ARC_PAD.bottom);
}

function buildArcGraph() {
  const wrap = document.getElementById('arc-graph-wrap');
  if (!wrap) return;

  const chars = (story.characters || []).filter(c =>
    c.arc_type && c.arc_type !== 'absent' && c.arc_beats_list && c.arc_beats_list.length > 0
  );

  if (chars.length === 0) {
    wrap.innerHTML = `
      <div class="arc-empty">
        <div class="arc-empty-icon">&#9670;</div>
        <div class="arc-empty-title">No arc trajectories yet</div>
        <div class="arc-empty-text">Design a character arc to see value trajectories plotted here.</div>
        <button class="btn btn-hermes" data-hermes-send="Design a character arc for the protagonist showing their value shift across the story.">Design arc with Hermes</button>
      </div>`;
    return;
  }

  const actCount = story.project.act_count || 3;
  const acts = story.acts || [];
  const scenes = story.scenes || [];

  // Map scene → act index and scene order within that act
  const actById = {};
  acts.forEach((a, i) => { actById[a.id] = i; });
  const scenesInActMap = {};
  scenes.forEach(s => {
    if (s.act_id != null) {
      (scenesInActMap[s.act_id] = scenesInActMap[s.act_id] || []).push(s);
    }
  });
  Object.values(scenesInActMap).forEach(list => list.sort((a, b) => a.order - b.order));
  const sceneActIdx = {};  // scene id → { actIdx, idxInAct, countInAct }
  scenes.forEach(s => {
    if (s.act_id != null && scenesInActMap[s.act_id]) {
      const list = scenesInActMap[s.act_id];
      sceneActIdx[s.id] = {
        actIdx: actById[s.act_id] != null ? actById[s.act_id] : -1,
        idxInAct: list.findIndex(x => x.id === s.id),
        countInAct: list.length,
      };
    }
  });

  function beatX(char, beat) {
    const info = sceneActIdx[beat.scene];
    if (!info || info.actIdx === -1) {
      // Fallback: use beat order within character arc
      return (beat.order - 1) / (char.arc_beat_count || 1);
    }
    const innerPos = info.countInAct > 1 ? info.idxInAct / (info.countInAct - 1) : 0.5;
    return (info.actIdx + innerPos) / actCount;
  }

  // Sanity warnings
  const warnings = [];
  chars.forEach(char => {
    const ys = char.arc_beats_list.map(b => b.y);
    const maxDelta = Math.max(...ys.map((y, i) => i > 0 ? Math.abs(y - ys[i-1]) : 0));
    const range = Math.max(...ys) - Math.min(...ys);
    if (range < 0.2) warnings.push(`"${char.name}" arc is flat — nothing dramatic happens`);
    if (maxDelta > 0.8) warnings.push(`"${char.name}" has a single beat jump > 0.8 — consider splitting`);
  });

  let svg = `<svg viewBox="0 0 ${ARC_GW} ${ARC_GH}" class="arc-graph" id="arc-svg">`;

  // Grid lines
  for (let v = -1; v <= 1; v += 0.5) {
    const y = arcYScale(v);
    const cls = v === 0 ? 'arc-zero-line' : 'arc-grid-line';
    svg += `<line x1="${ARC_PAD.left}" y1="${y}" x2="${ARC_GW - ARC_PAD.right}" y2="${y}" class="${cls}"/>`;
    svg += `<text x="${ARC_PAD.left - 5}" y="${y}" class="arc-axis-label" text-anchor="end" dominant-baseline="central">${v > 0 ? '+' : ''}${v.toFixed(1)}</text>`;
  }

  // Y-axis label
  svg += `<text x="9" y="${ARC_GH/2}" class="arc-axis-label" text-anchor="middle" transform="rotate(-90,9,${ARC_GH/2})">value charge</text>`;

  // Equal-width act bands from act_count (renders even with no act files)
  const actBandwidth = (ARC_GW - ARC_PAD.left - ARC_PAD.right) / actCount;
  for (let i = 0; i < actCount; i++) {
    const x = ARC_PAD.left + i * actBandwidth;
    const act = acts[i];
    const label = act ? (act.title || act.id || `Act ${i+1}`) : `Act ${i+1}`;
    const cls = i % 2 === 0 ? 'even' : 'odd';
    svg += `<rect x="${x}" y="${ARC_PAD.top - 8}" width="${actBandwidth}" height="${ARC_GH - ARC_PAD.top - ARC_PAD.bottom + 12}" class="arc-act-band ${cls}"/>`;
    if (i > 0) {
      svg += `<line x1="${x}" y1="${ARC_PAD.top - 8}" x2="${x}" y2="${ARC_GH - ARC_PAD.bottom + 4}" class="arc-act-line"/>`;
    }
    svg += `<text x="${x + 4}" y="${ARC_PAD.top - 4}" class="arc-act-label">${escapeHtml(label)}</text>`;
  }

  // Arc lines + beat dots
  chars.forEach(char => {
    const color = roleColor(char.role || char.story_role || '');
    const muted = arcMutedChars.has(char.id) ? ' muted' : '';
    const beats = [...(char.arc_beats_list || [])].sort((a, b) => a.order - b.order);
    const pts = beats.map(b => [arcXScale(beatX(char, b)), arcYScale(b.y)]);

    if (arcUseSpline && pts.length > 2) {
      svg += `<path class="arc-line${muted}" d="${catmullRomPath(pts)}" stroke="${color}" stroke-opacity="${muted ? '0.15' : '0.8'}"/>`;
    } else {
      svg += `<polyline class="arc-line${muted}" points="${pts.map(p => p.join(',')).join(' ')}" stroke="${color}" stroke-opacity="${muted ? '0.15' : '0.8'}"/>`;
    }

    beats.forEach(beat => {
      const bx = arcXScale(beatX(char, beat));
      const by = arcYScale(beat.y);
      let r = 5, extraClass = '', fill = color, stroke = 'none', strokeW = 0;
      if (beat.is_crisis) { r = 7; fill = '#ffd93d'; extraClass = ' crisis'; }
      else if (beat.is_climax) { r = 7; fill = 'transparent'; stroke = color; strokeW = 2; extraClass = ' climax'; }
      const yDisp = beat.y >= 0 ? `+${beat.y.toFixed(2)}` : beat.y.toFixed(2);
      svg += `<circle class="arc-beat-dot${extraClass}${muted}" cx="${bx}" cy="${by}" r="${r}" fill="${fill}" stroke="${stroke}" stroke-width="${strokeW}" data-label="${escapeHtml(beat.label)}" data-char="${escapeHtml(char.name)}" data-shift="${escapeHtml(beat.shift || '')}" data-y="${yDisp}" onmouseenter="DASH.showArcTooltip(event, this)" onmouseleave="DASH.hideArcTooltip()"/>`;
      if (arcShowLabels && !arcMutedChars.has(char.id)) {
        svg += `<text class="beat-label" x="${bx}" y="${by - (beat.is_crisis || beat.is_climax ? 12 : 10)}" text-anchor="middle">${escapeHtml(beat.label)}</text>`;
      }
    });
  });

  // X-axis (scene names at bottom, positioned within their act band)
  (story.scenes || []).forEach(scene => {
    const info = sceneActIdx[scene.id];
    let x;
    if (info && info.actIdx !== -1) {
      const innerPos = info.countInAct > 1 ? info.idxInAct / (info.countInAct - 1) : 0.5;
      x = ARC_PAD.left + (info.actIdx + innerPos) * actBandwidth;
    } else {
      return; // skip scenes with no act mapping
    }
    const y = ARC_GH - ARC_PAD.bottom + 14;
    const hasBeats = scene.arc_beats && scene.arc_beats.length > 0;
    if (hasBeats) {
      svg += `<text x="${x}" y="${y}" class="arc-axis-label" text-anchor="middle">${escapeHtml((scene.title || scene.id || '').split('—')[0].trim())}</text>`;
      svg += `<line x1="${x}" y1="${ARC_GH - ARC_PAD.bottom}" x2="${x}" y2="${ARC_GH - ARC_PAD.bottom + 4}" class="arc-grid-line"/>`;
    }
  });

  svg += '</svg>';
  wrap.innerHTML = svg;

  // Warnings
  const warningsEl = document.getElementById('arc-warnings');
  if (warningsEl) {
    warningsEl.innerHTML = warnings.map(w => `
      <div class="arc-warning">
        <span class="arc-warning-icon">&#9888;</span>
        <span>${escapeHtml(w)}</span>
      </div>
    `).join('');
  }
}

function catmullRomPath(pts, alpha = 0.5) {
  if (pts.length < 2) return '';
  const d = [`M ${pts[0][0]} ${pts[0][1]}`];
  for (let i = 0; i < pts.length - 1; i++) {
    const p0 = pts[Math.max(i - 1, 0)];
    const p1 = pts[i];
    const p2 = pts[i + 1];
    const p3 = pts[Math.min(i + 2, pts.length - 1)];
    const cp1x = p1[0] + (p2[0] - p0[0]) / 6;
    const cp1y = p1[1] + (p2[1] - p0[1]) / 6;
    const cp2x = p2[0] - (p3[0] - p1[0]) / 6;
    const cp2y = p2[1] - (p3[1] - p1[1]) / 6;
    d.push(`C ${cp1x} ${cp1y}, ${cp2x} ${cp2y}, ${p2[0]} ${p2[1]}`);
  }
  return d.join(' ');
}

/* ─── Legend ────────────────────────────────────────────────── */
function updateLegend() {
  const legend = document.getElementById('arc-legend');
  if (!legend) return;
  const chars = (story.characters || []).filter(c =>
    c.arc_type && c.arc_type !== 'absent' && c.arc_beats_list && c.arc_beats_list.length > 0
  );
  legend.innerHTML = chars.map(char => {
    const color = roleColor(char.role || char.story_role || '');
    const muted = arcMutedChars.has(char.id) ? ' muted' : '';
    return `<div class="legend-item${muted}" onclick="DASH.toggleArcCharMute('${char.id}')">
      <div class="legend-line" style="background:${color}"></div>
      <span>${escapeHtml(char.name)}</span>
      <span class="legend-arc-type">${char.arc_type}</span>
    </div>`;
  }).join('') + `
    <div class="legend-item" style="gap:12px;margin-left:auto">
      <div style="display:flex;align-items:center;gap:4px"><div class="legend-dot" style="background:#ffd93d"></div><span>crisis</span></div>
      <div style="display:flex;align-items:center;gap:4px"><div class="legend-dot" style="background:transparent;border:1px solid #e8e8e8"></div><span>climax</span></div>
    </div>`;
}

function toggleArcCharMute(charId) {
  if (arcMutedChars.has(charId)) arcMutedChars.delete(charId);
  else arcMutedChars.add(charId);
  document.querySelectorAll('.char-card').forEach(c => c.classList.remove('selected'));
  buildArcGraph();
  updateLegend();
}

function toggleArcSpline() {
  arcUseSpline = !arcUseSpline;
  document.getElementById('btn-spline')?.classList.toggle('btn-primary', arcUseSpline);
  buildArcGraph();
}

function toggleArcLabels() {
  arcShowLabels = !arcShowLabels;
  document.getElementById('btn-labels')?.classList.toggle('btn-primary', arcShowLabels);
  buildArcGraph();
}

/* ─── Tooltip ───────────────────────────────────────────────── */
function showArcTooltip(e, el) {
  const tt = document.getElementById('arc-beat-tooltip');
  if (!tt) return;
  document.getElementById('tt-label').textContent = el.dataset.label;
  document.getElementById('tt-char').textContent = el.dataset.char;
  document.getElementById('tt-shift').textContent = el.dataset.shift || '';
  document.getElementById('tt-value').innerHTML = `Value charge: <strong>${el.dataset.y}</strong>`;
  tt.classList.add('visible');
  positionArcTooltip(e);
}
function hideArcTooltip() {
  const tt = document.getElementById('arc-beat-tooltip');
  if (tt) tt.classList.remove('visible');
}
function positionArcTooltip(e) {
  const tt = document.getElementById('arc-beat-tooltip');
  if (!tt) return;
  tt.style.left = Math.min(e.clientX + 14, window.innerWidth - 220) + 'px';
  tt.style.top = Math.max(e.clientY - 40, 8) + 'px';
}
document.addEventListener('mousemove', e => {
  const tt = document.getElementById('arc-beat-tooltip');
  if (tt?.classList.contains('visible')) positionArcTooltip(e);
});

boot();

