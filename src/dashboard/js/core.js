// ─── Boot ─────────────────────────────────────────────────────────────────────
window.DASH = window.DASH || {};

let story = null;

let network = null;


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

DASH.boot();
