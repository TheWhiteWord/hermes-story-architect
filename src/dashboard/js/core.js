// ─── Boot ─────────────────────────────────────────────────────────────────────
window.DASH = window.DASH || {};

let story = null;

let network = null;

let _scriptBuilt = false;


DASH.boot = async function() {
  try {
    // Injected data takes precedence (avoids fetch('file://') which Electron blocks)
    if (window.__STORY_DATA__) {
      DASH.initStory(window.__STORY_DATA__);
      return;
    }

    // Check for project path in URL query param first
    const params = new URLSearchParams(window.location.search);
    const projectPath = params.get('project');
    let indexPath;

    if (projectPath) {
      indexPath = projectPath.replace(/\/$/, '') + '/.DASH.story/index.yaml';
    } else {
      indexPath = '.DASH.story/index.yaml';
    }

    const res = await fetch('file://' + indexPath);
    if (!res.ok) throw new Error('not found');
    const text = await res.text();
    const data = jsyaml.load(text);
    DASH.initStory(data);
  } catch (e) {
    DASH.showError();
  }
}

DASH.showError = function() {
  document.getElementById('loading-screen').style.display = 'none';
  document.getElementById('error-screen').style.display = 'flex';
}

DASH.normalise = function(data) {
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
    s.locations = DASH.normalizeLocs(s.locations || s.location);
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

DASH.initStory = function(data) {
  DASH.story = DASH.normalise(data);
  DASH.story.characters = DASH.story.characters || [];
  DASH.story.locations  = DASH.story.locations  || [];
  DASH.story.plots      = DASH.story.plots      || [];
  DASH.story.scenes     = DASH.story.scenes     || [];
  DASH.story.worlds     = DASH.story.worlds     || [];
  DASH.story.story_memory = DASH.story.story_memory || {};
  DASH.story.relationships = DASH.story.relationships || [];

  document.getElementById('loading-screen').style.display = 'none';

  DASH.buildGraphView();
  DASH.buildScenesView();
  DASH.buildLocationsView();
  DASH.buildPlotsView();
  DASH.buildRelationshipsView();
  DASH.buildWorldsView();
  DASH.buildStoryView();
}

DASH.buildScriptView = function() {
  const stats = window.__SCREENPLAY_STATS__;
  const container = document.getElementById('screenplay-container');
  if (!container) return;

  // No stats or no scriptHtml → empty state
  if (!stats || !stats.scriptHtml) {
    container.innerHTML = '<div class="script-empty"><div class="empty-state-title">No scenes with content yet</div><div class="empty-state-sub">Add content to your scenes to see the script view.</div></div>';
    DASH._scriptBuilt = true;
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
          <span class="tp-title">${DASH.escapeHtml(titleName)}</span>
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
    const matched = (DASH.story && DASH.story.scenes || []).find(s => {
      const h = (s.heading || '').toUpperCase().trim().replace(/\s*\(.*\)\s*$/, '');
      return h === rawHeading;
    });
    if (matched) {
      el.style.cursor = 'pointer';
      el.addEventListener('click', () => {
        DASH.showScenePanel(matched.id);
      });
    }
  });

  // Subtitle
  const sceneCount = (DASH.story.scenes || []).length;
  const pages = stats.lengthStats && stats.lengthStats.pagesWhole || '?';
  DASH.setEl('script-subtitle', pages + ' p · ' + sceneCount + ' scenes');

  container.innerHTML = '';
  container.appendChild(doc);
  DASH._scriptBuilt = true;
}
