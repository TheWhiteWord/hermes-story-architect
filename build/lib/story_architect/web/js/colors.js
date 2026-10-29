window.DASH = window.DASH || {};

DASH.ROLE_COLORS = {
  'protagonist': '#7b9cf0',
  'antagonist':  '#e07070',
  'mentor':      '#b07be0',
  'rival':       '#e0a86b',
  'supporting':  '#6bbfb0',
  'entity':      '#e06b9b',
};

DASH.REL_TYPE_COLORS = {
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

// The colour of an entity kind that carries no role of its own: a location, a
// world. These are the colours the entity views already paint their pips with
// (views/locations.js, views/worlds.js) and the tags already use
// (.tag-location, .tag-variant), so the chips in the panel tabs and the cards
// in the views are the same colour rather than two copies that can drift.
// Kept as literals and not as the role tokens: an ally is also teal, and
// --role-supporting would make a relationship chip indistinguishable from a
// place.
DASH.ENTITY_KIND_COLORS = {
  location: '#6bbfb0',
  world:    '#e0a86b',
};

// The dramatic roles a plot holds — must match PLOT_ROLES in core/constants.py.
// One list, so adding a role is an edit here and nowhere else.
DASH.PLOT_ROLES = ['setup', 'inciting_incident', 'complication', 'crisis', 'climax', 'resolution'];

// The `has_<role>` badges on a plot row (act and sequence panels are identical).
DASH.plotRoleBadges = function(p) {
  return DASH.PLOT_ROLES
    .filter(r => p['has_' + r])
    .map(r => `<span class="entity-row-sub">${r.replace(/_/g, ' ')}</span>`)
    .join(' ');
}

DASH.PLOT_TYPE_COLORS = {
  Contradictory: '#e07070',
  Resonant: '#7b9cf0',
  Complicating: '#e0a86b',
  Setup: '#6bbfb0',
};

// The colour of a plot: main is purple, subplots use their plot_type's
// colour from PLOT_TYPE_COLORS — the same rule the plot threads and
// value-turn chips already use, so a value's chips match its plot.
DASH.plotColor = function(pid) {
  const pl = (DASH.story.plots || []).find(x => x.id === pid);
  if (!pl) return '#888';
  if (pl.plot_scope === 'main') return '#b07be0';
  return DASH.PLOT_TYPE_COLORS[pl.plot_type] || '#888';
};

DASH.roleColor = function(role) {
  if (!role) return '#8a8a8a';
  const r = role.toLowerCase();
  for (const [key, val] of Object.entries(DASH.ROLE_COLORS)) {
    if (r.includes(key)) return val;
  }
  return '#8a8a8a';
}

DASH.getRoleKey = function(role) {
  if (!role) return 'other';
  const r = role.toLowerCase();
  for (const key of Object.keys(DASH.ROLE_COLORS)) {
    if (r.includes(key)) return key;
  }
  return 'other';
}

DASH.relTypeColor = function(type) {
  if (!type) return '#8a8a8a';
  return DASH.REL_TYPE_COLORS[type.toLowerCase()] || '#8a8a8a';
}
