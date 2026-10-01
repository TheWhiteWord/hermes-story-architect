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

// The dramatic roles a plot holds — must match PLOT_ROLES in core/constants.py.
// One list, so adding a role is an edit here and nowhere else.
DASH.PLOT_ROLES = ['setup', 'complication', 'crisis', 'climax', 'resolution'];

// The `has_<role>` badges on a plot row (act and sequence panels are identical).
DASH.plotRoleBadges = function(p) {
  return DASH.PLOT_ROLES
    .filter(r => p['has_' + r])
    .map(r => `<span class="beat-desc">${r}</span>`)
    .join('');
}

DASH.PLOT_TYPE_COLORS = {
  Contradictory: '#e07070',
  Resonant: '#7b9cf0',
  Complicating: '#e0a86b',
  Setup: '#6bbfb0',
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
