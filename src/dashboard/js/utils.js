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
