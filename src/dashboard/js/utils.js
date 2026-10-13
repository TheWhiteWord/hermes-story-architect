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

// Major/minor value chips for a computed `value_focus` on a unit
// (plot/sequence/act/project). Major is purple (the unit's spine values),
// minor is the muted default tag. `scenes` is the count of scenes in which
// the value shifts, shown only when > 1 — a single scene needs no number.
DASH.valueFocusHtml = function(focus) {
  const f = focus || {};
  const chips = (list) => (list || []).map(it =>
    `<span class="tag tag-mood" style="font-size:var(--font-size-xs)">${DASH.escapeHtml(it.value || '')}${it.scenes > 1 ? ' ×' + it.scenes : ''}</span>`
  ).join('');
  const majors = chips(f.major);
  const minors = chips(f.minor);
  if (!majors && !minors) return '';
  return `<div style="display:flex;flex-wrap:wrap;gap:4px;align-items:center;margin-top:4px">
    ${majors}
    ${minors ? `<span style="font-size:var(--font-size-xs);color:var(--muted-foreground);margin:0 2px">minor:</span>${minors}` : ''}
  </div>`;
}
