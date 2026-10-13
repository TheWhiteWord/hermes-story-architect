window.DASH = window.DASH || {};

DASH.normalizeLocs = function(loc) {
  if (!loc) return [];
  if (Array.isArray(loc)) return loc;
  return [loc];
}

DASH.findLocation = function(ref) {
  return (DASH.story.locations || []).find(l =>
    l.id === ref || l.id === String(ref) ||
    (l._scene_headings || []).includes(ref) ||
    l.name === ref
  );
}

DASH.escapeHtml = function(text) {
  return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

DASH.fmtDurationShort = function(sec) {
  if (!sec || isNaN(sec)) return '0s';
  sec = Math.round(sec);
  if (sec < 60) return sec + 's';
  const m = Math.floor(sec / 60);
  if (m < 60) return m + 'm';
  return Math.floor(m / 60) + 'h ' + (m % 60) + 'm';
}

DASH.fmtDuration = function(sec) {
  sec = Math.round(sec || 0);
  const h = Math.floor(sec / 3600);
  const m = Math.floor((sec % 3600) / 60);
  const s = sec % 60;
  if (h > 0) return h + ':' + String(m).padStart(2,'0') + ':' + String(s).padStart(2,'0');
  return m + ':' + String(s).padStart(2,'0');
}

DASH.setEl = function(id, val) {
  const el = document.getElementById(id);
  if (el) el.textContent = val;
}

DASH.setBar = function(baseId, count, total) {
  const pct = total > 0 ? Math.round((count / total) * 100) : 0;
  DASH.setEl(baseId, count + ' (' + pct + '%)');
  const bar = document.getElementById(baseId + '_bar');
  if (bar) bar.style.width = pct + '%';
}

// The colour of a value chip: the plots that contributed it, as a
// gradient when a value shifts in more than one plot (a tricolor chip for
// a value shared across three). Main plot is purple; every other plot
// gets a deterministic hue from its id. A value from no known plot
// (older payload) is muted.
DASH.valueChipStyle = function(plots) {
  const cols = (plots || []).map(pid => DASH.plotColor(pid));
  if (!cols.length) return 'background:var(--card);color:var(--muted-foreground);border:1px solid var(--border)';
  if (cols.length === 1) return `background:${cols[0]}22;color:${cols[0]}`;
  const stops = cols.map((c, i) => `${c} ${Math.round(i * 100 / (cols.length - 1))}%`).join(',');
  return `background:linear-gradient(135deg, ${stops});color:var(--foreground)`;
};

// Major/minor value chips for a computed `value_focus` on a unit
// (plot/sequence/act/project). `scenes` is the count of scenes in which
// the value shifts, shown only when > 1 — a single scene needs no number.
DASH.valueFocusHtml = function(focus) {
  const f = focus || {};
  const chips = (list) => (list || []).map(it =>
    `<span class="tag" style="font-size:var(--font-size-xs);${DASH.valueChipStyle(it.plots)}">${DASH.escapeHtml(it.value || '')}${it.scenes > 1 ? ' ×' + it.scenes : ''}</span>`
  ).join('');
  const majors = chips(f.major);
  const minors = chips(f.minor);
  if (!majors && !minors) return '';
  // Each group on its own line, labelled — a unit with both reads as two
  // facts (what dominates, what fades) instead of one blurred row.
  return `<div style="display:flex;flex-direction:column;gap:4px;margin-top:4px">
    ${majors ? `<div style="display:flex;flex-wrap:wrap;gap:4px;align-items:center"><span style="font-size:var(--font-size-xs);color:var(--muted-foreground);margin-right:2px">dominant:</span>${majors}</div>` : ''}
    ${minors ? `<div style="display:flex;flex-wrap:wrap;gap:4px;align-items:center"><span style="font-size:var(--font-size-xs);color:var(--muted-foreground);margin-right:2px">minor:</span>${minors}</div>` : ''}
  </div>`;
}
