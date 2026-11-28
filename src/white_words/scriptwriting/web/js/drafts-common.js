window.DASH = window.DASH || {};

// What the reader and compare screens share: their routes, how a draft is named, how an
// entity's values are shown, and the order entity types are listed in.
(function (D) {
  const esc = (s) => String(s == null ? '' : s)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  const enc = encodeURIComponent;
  const dec = (s) => { try { return decodeURIComponent(s); } catch (e) { return s; } };

  const TYPES = [
    ['project', 'Project'], ['act', 'Acts'], ['sequence', 'Sequences'], ['scene', 'Scenes'], ['scene_beats', 'Scene beats'],
    ['character', 'Characters'], ['relationship', 'Relationships'], ['location', 'Locations'], ['world', 'Worlds'],
    ['plot', 'Plots'], ['value', 'Values'],
  ];
  const typeRank = (t) => { const i = TYPES.findIndex((x) => x[0] === t); return i < 0 ? TYPES.length : i; };
  const typeLabel = (t) => { const f = TYPES.find((x) => x[0] === t); return f ? f[1] : String(t).replace(/_/g, ' '); };
  const typeWord = (t) => String(t).replace(/_/g, ' ');
  const keyLabel = (k) => String(k).replace(/_/g, ' ');

  // ─── routes: #/drafts/<slug>/read/<ref> and #/drafts/<slug>/compare/<a>/<b> ───
  function parse(hash) {
    const m = /^#\/drafts\/([^/]+)\/(read|compare|merge)\/(.+)$/.exec(hash || '');
    if (!m) return { kind: 'list' };
    const slug = dec(m[1]);
    const refs = m[3].split('/').map(dec);
    if (m[2] === 'read' && refs[0]) return { kind: 'read', slug, ref: refs[0] };
    if (m[2] === 'merge' && refs[0]) return { kind: 'merge', slug, session: refs[0] };
    if (m[2] === 'compare' && refs[0] && refs[1]) return { kind: 'compare', slug, a: refs[0], b: refs[1] };
    return { kind: 'list' };
  }
  function href(r) {
    if (r.kind === 'read') return '#/drafts/' + enc(r.slug) + '/read/' + enc(r.ref);
    if (r.kind === 'merge') return '#/drafts/' + enc(r.slug) + '/merge/' + enc(r.session);
    if (r.kind === 'compare') return '#/drafts/' + enc(r.slug) + '/compare/' + enc(r.a) + '/' + enc(r.b);
    return '#/';
  }

  // ─── refs: `snapshot:<id>` is a saved draft, `branch:<id>` a branch's open draft ───
  function refLabel(ref, hist) {
    const i = String(ref).indexOf(':');
    const kind = ref.slice(0, i);
    const id = ref.slice(i + 1);
    if (kind === 'branch') {
      const b = ((hist && hist.branches) || []).find((x) => x.id === id);
      return b ? b.name + ' · open draft' : ref;
    }
    const s = ((hist && hist.snapshots) || []).find((x) => x.id === id);
    return s ? s.label : ref;
  }
  function refOptions(hist) {
    const branches = (hist && hist.branches) || [];
    const name = {};
    branches.forEach((b) => { name[b.id] = b.name; });
    return [
      { group: 'Open drafts', items: branches.map((b) => ({ ref: 'branch:' + b.id, label: b.name + (b.is_current ? ' (current)' : '') + ' · open draft' })) },
      { group: 'Saved drafts', items: ((hist && hist.snapshots) || []).slice().reverse().map((s) => ({ ref: 'snapshot:' + s.id, label: s.label + ' · ' + (name[s.branch_id] || 'deleted branch') })) },
    ];
  }

  // ─── values ───
  const empty = '<span class="dv-empty">empty</span>';
  // `name(id)` turns an id found in a value into the entity's name, so a list of characters
  // reads as names; the id stays in the tooltip.
  function fmtScalar(v, name) {
    const n = name && typeof v === 'string' ? name(v) : undefined;
    return n && n !== v ? '<span title="' + esc(v) + '">' + esc(n) + '</span>' : esc(v);
  }
  function fmtValue(v, name) {
    if (v == null || v === '' || (Array.isArray(v) && !v.length)) return empty;
    if (Array.isArray(v)) {
      return '<ul class="dv-list">' + v.map((x) => '<li>' + (x && typeof x === 'object' ? fmtObject(x, name) : fmtScalar(x, name)) + '</li>').join('') + '</ul>';
    }
    if (typeof v === 'object') return fmtObject(v, name);
    return fmtScalar(v, name);
  }
  function fmtObject(o, name) {
    return Object.keys(o).map((k) => '<span class="dv-k">' + esc(keyLabel(k)) + '</span> ' + (o[k] && typeof o[k] === 'object' ? esc(JSON.stringify(o[k])) : fmtScalar(o[k], name))).join(' · ');
  }

  D.draftsCommon = { esc, enc, typeRank, typeLabel, typeWord, keyLabel, parse, href, refLabel, refOptions, fmtValue, TYPES };
})(window.DASH);
