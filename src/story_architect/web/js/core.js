// ─── Boot ─────────────────────────────────────────────────────────────────────
window.DASH = window.DASH || {};

let story = null;

let network = null;


DASH.askAgent = function(text) {
  try { navigator.clipboard.writeText(text); } catch (e) {}
  alert('Prompt copied to clipboard. Paste it into Hermes chat.');
};

document.addEventListener('click', function(e){
  const b = e.target && e.target.closest && e.target.closest('[data-hermes-send]');
  if (b) { e.preventDefault(); DASH.askAgent(b.getAttribute('data-hermes-send')); }
});
DASH.boot = async function() {
  try {
    const m = (location.hash || '').match(/^#\/p\/(.+)$/);
    if (!m) {
      await DASH.showPicker();
      return;
    }
    const slug = decodeURIComponent(m[1]);
    const res = await fetch('/api/projects/' + encodeURIComponent(slug) + '/dashboard');
    if (!res.ok) { DASH.showError(); return; }
    const data = await res.json();
    window.__STORY_DATA__ = data.story_data;
    window.__SECTIONS__ = data.sections;
    window.__SCREENPLAY_STATS__ = data.screenplay_stats;
    document.getElementById('loading-screen').style.display = 'none';
    DASH.initStory(data.story_data);
    DASH.watchUpdates(slug);
  } catch (e) {
    DASH.showError();
  }
};

DASH.showPicker = async function() {
  try {
    const res = await fetch('/api/projects');
    const data = await res.json();
    const projects = (data.projects || []);
    const app = document.getElementById('app');
    const loading = document.getElementById('loading-screen');
    if (loading) loading.style.display = 'none';
    let html = '<div style="padding:2rem"><h2>Projects</h2>';
    if (!projects.length) {
      html += '<p>No projects found. Create one under projects/.</p>';
    } else {
      html += '<ul>' + projects.map(p => '<li><a href="#/p/' + encodeURIComponent(p.slug) + '">' + (p.name || p.slug) + '</a></li>').join('') + '</ul>';
    }
    html += '</div>';
    if (app) app.innerHTML = html;
  } catch (e) {
    DASH.showError();
  }
};

DASH.watchUpdates = function(slug) {
  try {
    if (DASH._es) DASH._es.close();
    const es = new EventSource('/api/projects/' + encodeURIComponent(slug) + '/events');
    DASH._es = es;
    es.addEventListener('update', function() {
      DASH.showUpdateIndicator(slug);
    });
    es.onerror = function() { /* auto-reconnect by browser */ };
  } catch (e) {}
};

DASH.showUpdateIndicator = function(slug) {
  let el = document.getElementById('sa-update-banner');
  if (!el) {
    el = document.createElement('div');
    el.id = 'sa-update-banner';
    el.style.cssText = 'position:fixed;top:8px;right:8px;background:#222;color:#fff;padding:8px 12px;border-radius:6px;z-index:9999;font-size:13px;';
    el.innerHTML = 'Project updated <button id="sa-refresh-btn">Refresh</button>';
    document.body.appendChild(el);
    document.getElementById('sa-refresh-btn').onclick = function() { DASH.refreshProject(slug); };
  }
  el.style.display = 'block';
};

DASH.refreshProject = async function(slug) {
  window.location.reload();
};

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
    // goals_short / goals_long arrive flat, from the DB and from the sample
    // alike. There is no nested `goals` object anywhere in the system.
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

  // Plots: role fields already normalized by backend to [{scene_id, description}]
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
  d.values = d.values || [];
  d.story_memory = d.story_memory || { status: "ready", usage: "0/3000", counts: {}, categories: {} };
  d.story_memory.categories = d.story_memory.categories || {};

  return d;
}

DASH.initStory = function(data) {
  DASH.story = DASH.normalise(data);
  DASH.story.characters = DASH.story.characters || [];
  DASH.story.locations  = DASH.story.locations  || [];
  DASH.story.plots      = DASH.story.plots      || [];
  DASH.story.scenes     = DASH.story.scenes     || [];
  DASH.story.worlds     = DASH.story.worlds     || [];
  DASH.story.values     = DASH.story.values     || [];
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
  DASH.buildValuesView();
  DASH.buildScriptView();
}
