#!/usr/bin/env node
// The projects page's render functions and the branch graph's layout, executed for real.
//
//   node tests/projects_harness.js
//
// `web/js/projects.js` and `web/js/history-graph.js` are browser modules. This runs the
// repo's own files with no DOM (the controller only wires itself up when there is one)
// and asserts the markup and geometry they produce. The payloads are the shapes
// `GET /api/projects` and `GET /api/projects/<slug>/history/` return; if the API
// changes, this file has to change with it, which is the point.
'use strict';

const path = require('path');

global.window = global;
const JS = path.join(__dirname, '..', 'src', 'white_words', 'scriptwriting', 'web', 'js');
require(path.join(JS, 'history-graph.js'));
require(path.join(JS, 'text-diff.js'));
require(path.join(JS, 'drafts-common.js'));
require(path.join(JS, 'reader.js'));
require(path.join(JS, 'compare.js'));
require(path.join(JS, 'projects.js'));
require(path.join(JS, 'draft-chip.js'));

const R = global.DASH.projectsRender;
const G = global.DASH.historyGraph;
let ran = 0;
const failures = [];

function check(name, cond, detail) {
  ran += 1;
  if (cond) console.log('ok   ' + name);
  else { failures.push(name); console.log('FAIL ' + name + (detail ? '\n     ' + detail : '')); }
}

const NOW = Date.parse('2026-11-26T12:00:00Z');
const snap = (id, branch, label, parents, extra) => Object.assign({ id, branch_id: branch, seq: 1, label, note: '', created_at: '2026-11-26T11:00:00+00:00', parents }, extra || {});
const branch = (id, base, extra) => Object.assign({ id, name: id, base_snapshot_id: base, is_current: false, created_at: '2026-11-26T10:00:00+00:00', pending_merge_parents: [] }, extra || {});

// main: d1 → d2; alt branched from d1 with d3; alt is current and has 2 open changes.
const history = () => ({
  branches: [branch('alt', 'd3', { is_current: true, created_at: '2026-11-26T10:00:00+00:00' }), branch('main', 'd2')],
  snapshots: [snap('d1', 'main', 'Draft 1', []), snap('d2', 'main', 'Draft 2', ['d1']), snap('d3', 'alt', 'Garden <opening>', ['d1'], { note: 'alt take' })],
  current: 'alt',
  head: { alt: { changed: true, changes: 2 }, main: { changed: false, changes: 0 } },
  picked_from: [],
});

// ─── time ───
check('a minute-old save reads in minutes', R.ago('2026-11-26T11:58:00Z', NOW) === '2 mins ago');
check('a fresh save reads just now', R.ago('2026-11-26T11:59:40Z', NOW) === 'just now');
check('an hour-old save reads in hours', R.ago('2026-11-26T11:00:00Z', NOW) === '1 hour ago');
check('an unparseable time reads as nothing', R.ago('not a date', NOW) === '');

// ─── the card ───
const listed = (extra) => Object.assign({ slug: 'save-the-children', name: 'Save the Children', has_db: true, current_branch: 'alt', current_draft: 'Garden opening', branch_count: 2, last_saved: '2026-11-26T11:00:00Z', changes_since_save: 3 }, extra || {});
let html = R.cardHtml(listed(), { open: false }, NOW);
check('a collapsed card has no body', !/class="pj-body"/.test(html));
check('the card names branch, draft and branch count', /alt · Garden opening · 2 branches · saved 1 hour ago/.test(html));
check('unsaved changes show as a count since the draft', /3 changes since Garden opening/.test(html));
check('a clean project says up to date', /up to date/.test(R.cardHtml(listed({ changes_since_save: 0 }), { open: false }, NOW)));
check('one change is singular', /1 change since/.test(R.cardHtml(listed({ changes_since_save: 1 }), { open: false }, NOW)));
check('a project with no history says so and shows no chip', /No drafts saved yet/.test(R.cardHtml(listed({ branch_count: 0, current_draft: null, current_branch: null, changes_since_save: 0 }), { open: false }, NOW)) && !/pj-chip/.test(R.cardHtml(listed({ branch_count: 0 }), { open: false }, NOW)));
check('a project with no database cannot be opened', /data-act="open"[^>]* disabled/.test(R.cardHtml(listed({ has_db: false }), { open: false }, NOW)));
check('the toggle reports its state to assistive tech', /aria-expanded="false"/.test(html) && /aria-expanded="true"/.test(R.cardHtml(listed(), { open: true, hist: { state: 'loading' } }, NOW)));
check('an opening card says it is loading', /Loading history/.test(R.cardHtml(listed(), { open: true, hist: { state: 'loading' } }, NOW)));
check('a failed history load shows the server sentence', /boom &lt;b&gt;/.test(R.cardHtml(listed(), { open: true, hist: { state: 'error', message: 'boom <b>' } }, NOW)));

// ─── escaping and handlers ───
const hostile = history();
hostile.snapshots[2].label = '"><img src=x onerror=alert(1)>';
hostile.branches[1].name = '</div><script>alert(2)</script>';
const hostileHtml = R.cardHtml(listed({ name: '<b>x</b>' }), { open: true, hist: { state: 'ready', data: hostile } }, NOW);
check('no label or name can open a tag', !/<img src=x|<script>|<b>x/.test(hostileHtml));
check('no inline handler is built anywhere', !/\bon[a-z]+\s*=\s*["']/.test(hostileHtml.replace(/data-[a-z]+="[^"]*"/g, '')));

// ─── the open card ───
const open = (h, extra) => R.cardHtml(listed(extra), { open: true, hist: { state: 'ready', data: h } }, NOW);
html = open(history());
check('Save draft is enabled when the open draft changed', /data-act="save"(?![^>]*disabled)/.test(html));
const clean = history();
clean.head.alt = { changed: false, changes: 0 };
check('Save draft is disabled when nothing changed', /data-act="save"[^>]* disabled/.test(open(clean)));
check('the current branch offers Open, the other Switch and open', /data-act="open"[^>]*>Open</.test(html) && (html.match(/data-act="switch"/g) || []).length === 1);
check('the current branch cannot be deleted', /data-act="delete-branch"[^>]*data-id="alt"[^>]* disabled/.test(html) && /data-act="delete-branch"[^>]*data-id="main"(?![^>]* disabled)/.test(html));
check('a draft a branch starts from cannot be deleted', /data-act="delete-draft"[^>]*data-id="d3"[^>]* disabled/.test(html) && /data-act="delete-draft"[^>]*data-id="d2"[^>]* disabled/.test(html));
check('a draft nothing starts from can be deleted', /data-act="delete-draft"[^>]*data-id="d1"(?![^>]* disabled)/.test(html));
check('drafts are listed newest first', html.indexOf('data-row="snapshot:d3"') < html.indexOf('data-row="snapshot:d1"'));
check('a branch row says what its open draft holds', /Open draft: 2 changes since Garden &lt;opening&gt;/.test(html) && /Open draft: no changes since Draft 2/.test(html));
check('a project with no history offers a first save', /Save first draft/.test(open({ branches: [], snapshots: [], current: null, head: {}, picked_from: [] })));

// ─── graph geometry ───
const g = G.layout(history());
const node = (kind, id) => g.nodes.find((n) => n.kind === kind && n.id === id);
check('the branch holding the first draft is the top lane even on a tie', node('draft', 'd1').y < node('draft', 'd3').y);
check('a child sits one column right of its parent', node('draft', 'd2').x === node('draft', 'd1').x + G.DX && node('draft', 'd3').x === node('draft', 'd1').x + G.DX);
check('a branch tip sits one column right of its draft', node('tip', 'main').x === node('draft', 'd2').x + G.DX && node('tip', 'alt').x === node('draft', 'd3').x + G.DX);
check('the tip carries its change count', node('tip', 'alt').changes === 2 && node('tip', 'alt').changed && !node('tip', 'main').changed);
check('edges are parents plus one tip edge per branch', g.edges.filter((e) => e.kind === 'parent').length === 2 && g.edges.filter((e) => e.kind === 'tip').length === 2);
check('the canvas holds every node', g.nodes.every((n) => n.x < g.width && n.y < g.height));

const merged = history();
merged.snapshots.push(snap('d4', 'main', 'Merged', ['d2', 'd3']));
merged.branches[1].base_snapshot_id = 'd4';
const gm = G.layout(merged);
check('a second parent is a merge edge', gm.edges.filter((e) => e.kind === 'merge').length === 1);
check('a merge sits right of both parents', gm.nodes.find((n) => n.id === 'd4').x > gm.nodes.find((n) => n.id === 'd3').x);

const pending = history();
pending.branches[1].pending_merge_parents = ['d3'];
pending.picked_from = [{ branch: 'main', source: { kind: 'snapshot', id: 'd1' } }, { branch: 'main', source: { kind: 'snapshot', id: 'd1' } }, { branch: 'main', source: { kind: 'snapshot', id: 'gone' } }];
const gp = G.layout(pending);
check('a pending merge parent is a dashed edge to the tip', gp.edges.filter((e) => e.kind === 'pending').length === 1);
const complete = history();
complete.branches[1].pending_merge_parents = ['d3'];
complete.picked_from = [{ branch: 'main', source: { kind: 'snapshot', id: 'd3' } }];
check('a pick already drawn as a pending merge is not drawn twice', G.layout(complete).edges.filter((e) => e.kind === 'pick').length === 0);
check('a pick is one edge however often it was applied, and one from a missing draft is dropped', gp.edges.filter((e) => e.kind === 'pick').length === 1);

const orphan = history();
orphan.snapshots[0].branch_id = 'deleted-branch';
check('a draft on a deleted branch lands on a lane that reaches it', Number.isFinite(G.layout(orphan).nodes.find((n) => n.id === 'd1').y));
check('an empty history lays out without throwing', G.layout({ branches: [], snapshots: [] }).nodes.length === 0);

const svg = G.svg(history());
check('branch names are in their own column, outside the scrolling canvas', /<svg class="hg-lanes"[^>]*aria-hidden="true">[\s\S]*<div class="hg-scroll"><svg class="hg"/.test(svg) && !/<div class="hg-scroll">[\s\S]*hg-lane /.test(svg));
check('a lane label carries the full branch name', /<title>alt<\/title>alt/.test(svg));
check('the svg names its size for assistive tech', /role="img" aria-label="Branch graph: 2 branches, 3 drafts"/.test(svg));
check('graph nodes carry their ids as data, never as handlers', /data-snapshot="d1"/.test(svg) && /data-branch="alt"/.test(svg) && !/onclick/.test(svg));
check('the svg escapes a draft label', !/<opening>/.test(svg) && /Garden &lt;opening&gt;/.test(svg));
check('a long label is clipped', /…/.test(G.svg(Object.assign(history(), { snapshots: [snap('d1', 'main', 'A very long draft name indeed', [])] }))));

// ─── the draft chip ───
const C = global.DASH.draftChip;
const status = (extra) => Object.assign({ branch_count: 2, current_branch: 'alt', current_draft: 'Garden opening', changes_since_save: 0, next_draft_number: 2 }, extra || {});
check('an unknown status draws nothing', C.render(null) === '');
check('a project with no history offers a first save', /No drafts yet/.test(C.render(status({ branch_count: 0 }))) && /Save first draft/.test(C.render(status({ branch_count: 0 }))));
check('the chip names branch and draft', /alt · Garden opening/.test(C.render(status())));
check('a clean project has Save draft disabled and says why', /data-dc="save" disabled title="Nothing has changed since Garden opening\."/.test(C.render(status())) && !/dc-chip changed/.test(C.render(status())));
check('unsaved changes mark the chip and enable Save draft', /dc-chip changed/.test(C.render(status({ changes_since_save: 3 }))) && /3 changes/.test(C.render(status({ changes_since_save: 3 }))) && /data-dc="save">Save draft/.test(C.render(status({ changes_since_save: 3 }))));
check('one change is singular', /· 1 change"/.test(C.render(status({ changes_since_save: 1 }))));
check('the chip links to the projects page by data attribute, not a handler', /data-dc="projects"/.test(C.render(status())) && !/\bon[a-z]+\s*=/.test(C.render(status())));
check('a hostile branch or draft name cannot open a tag', !/<img|<script/.test(C.render(status({ current_branch: '<img src=x>', current_draft: '"><script>' }))));

// ─── links from the projects page ───
const hrefs = (h) => (h.match(/href="([^"]+)"/g) || []).map((x) => decodeURIComponent(x.slice(6, -1)));
const rows = open(history());
check('a branch row links to reading its open draft', hrefs(rows).includes('#/drafts/save-the-children/read/branch:alt'));
check('the current branch compares its last draft with its open draft', hrefs(rows).includes('#/drafts/save-the-children/compare/snapshot:d3/branch:alt'));
check('another branch compares its open draft with the current branch', hrefs(rows).includes('#/drafts/save-the-children/compare/branch:main/branch:alt'));
check('a draft compares with the current branch', hrefs(rows).includes('#/drafts/save-the-children/compare/snapshot:d1/branch:alt') && hrefs(rows).includes('#/drafts/save-the-children/read/snapshot:d1'));

// ─── the line diff ───
const T = global.DASH.textDiff;
const tag = (ops) => ops.map((o) => o.op[0] + o.text).join('|');
check('equal text is all unchanged lines', tag(T.lines('a\nb', 'a\nb')) === 'ea|eb');
check('an edit in the middle is one deletion and one addition', tag(T.lines('a\nb\nc', 'a\nX\nc')) === 'ea|db|aX|ec');
check('text added to an empty field is all additions', tag(T.lines('', 'x\ny')) === 'ax|ay');
check('text removed entirely is all deletions', tag(T.lines('x\ny', null)) === 'dx|dy');
const longText = Array.from({ length: 30 }, (_, i) => 'line ' + i).join('\n');
const folded = T.collapse(T.lines(longText, longText.replace('line 15', 'LINE 15')), 2);
check('a long unchanged run folds to a gap with its size and keeps two lines of context', folded.filter((o) => o.op === 'gap').map((o) => o.skipped).join() === '13,12' && folded.length === 8);
const pinned = T.collapse([{ op: 'eq', k: 'h' }, { op: 'eq' }, { op: 'eq' }, { op: 'eq' }, { op: 'eq' }, { op: 'add' }], 1, true);
check('a pinned first row survives folding', pinned[0].k === 'h' && pinned[1].op === 'gap' && pinned[1].skipped === 3);
check('without pinning the first row folds like any other', T.collapse([{ op: 'eq' }, { op: 'eq' }, { op: 'eq' }, { op: 'add' }], 1)[0].op === 'gap');
const big = (tag) => Array.from({ length: 500 }, (_, i) => tag + i).join('\n');
check('two huge unrelated texts diff without hanging, as delete-then-add', (() => { const t = Date.now(); const d = T.lines(big('a'), big('b')); return d.length === 1000 && d[0].op === 'del' && d[999].op === 'add' && Date.now() - t < 2000; })());

const bk = (...xs) => xs.map((x) => ({ type: x[0], text: x[1] }));
const btag = (ops) => ops.map((o) => o.op[0] + o.block.type[0] + ':' + o.block.text).join('|');
check('equal blocks are all unchanged', btag(T.blocks(bk(['action', 'a']), bk(['action', 'a']))) === 'ea:a');
check('a block that changed text is one deletion and one addition', btag(T.blocks(bk(['dialogue', 'x'], ['action', 'a']), bk(['dialogue', 'y'], ['action', 'a']))) === 'dd:x|ad:y|ea:a');
check('the same text as another kind of block is a change', btag(T.blocks(bk(['action', 'KAEL']), bk(['character', 'KAEL']))) === 'da:KAEL|ac:KAEL');
check('a missing side is all additions or all deletions', btag(T.blocks(null, bk(['action', 'a']))) === 'aa:a' && btag(T.blocks(bk(['action', 'a']), undefined)) === 'da:a');

// ─── routes, refs and values ───
const K = global.DASH.draftsCommon;
check('a project page hash is the list', K.parse('').kind === 'list' && K.parse('#/').kind === 'list' && K.parse('#/p/x').kind === 'list');
check('a read route round-trips a slug with a space and a ref with a colon', (() => { const r = { kind: 'read', slug: 'my proj', ref: 'snapshot:s-1' }; const p = K.parse(K.href(r)); return p.kind === 'read' && p.slug === 'my proj' && p.ref === 'snapshot:s-1'; })());
check('a compare route round-trips both refs', (() => { const p = K.parse(K.href({ kind: 'compare', slug: 'p', a: 'branch:main', b: 'snapshot:d' })); return p.kind === 'compare' && p.a === 'branch:main' && p.b === 'snapshot:d'; })());
check('a compare route missing its second draft is the list', K.parse('#/drafts/p/compare/snapshot%3Aa').kind === 'list');
check('a malformed escape does not throw', K.parse('#/drafts/%E0%A4%A/read/x').kind === 'read');
const hist = history();
check('a branch ref reads as its open draft and a draft ref as its label', K.refLabel('branch:alt', hist) === 'alt · open draft' && K.refLabel('snapshot:d1', hist) === 'Draft 1' && K.refLabel('snapshot:gone', hist) === 'snapshot:gone');
const opts = K.refOptions(hist);
check('the pickers list open drafts first and saved drafts newest first', opts[0].group === 'Open drafts' && opts[0].items.length === 2 && /\(current\)/.test(opts[0].items.find((i) => i.ref === 'branch:alt').label) && opts[1].items[0].ref === 'snapshot:d3');
check('an empty value reads as empty, not as nothing', /dv-empty/.test(K.fmtValue('')) && /dv-empty/.test(K.fmtValue([])) && /dv-empty/.test(K.fmtValue(null)));
check('an id inside a value is shown as the entity name, with the id as its tooltip', K.fmtValue(['kael'], (id) => (id === 'kael' ? 'Kael' : undefined)) === '<ul class="dv-list"><li><span title="kael">Kael</span></li></ul>');
check('a value cannot open a tag', !/<img/.test(K.fmtValue('<img src=x>')) && !/<img/.test(K.fmtValue({ a: '<img src=x>' })));

// ─── the reader ───
const Rd = global.DASH.reader;
const entities = [
  { id: 's1', type: 'scene', name: 'The <b>farm</b>', one_sentence: '' },
  { id: 'a1', type: 'act', name: 'Act I', one_sentence: '' },
  { id: 'k', type: 'character', name: 'Kael', one_sentence: '' },
];
const rm = (extra) => Object.assign({ projectName: 'Oz', label: 'Draft 7', tab: 'entities', html: '<h3 class="fountain-scene_heading" data-scenenumber="1">INT. FARM</h3>', entities, selected: null, detail: null }, extra || {});
let rh = Rd.html(rm());
check('the reader says it is read-only and names the draft', /read-only/.test(rh) && /Draft 7/.test(rh));
check('entity types are listed in story order, not arrival order', rh.indexOf('Acts · 1') < rh.indexOf('Scenes · 1') && rh.indexOf('Scenes · 1') < rh.indexOf('Characters · 1'));
check('an entity name cannot open a tag', !/<b>farm/.test(rh) && /The &lt;b&gt;farm&lt;\/b&gt;/.test(rh));
check('nothing is selected until the reader picks', /Pick an entity to read it/.test(rh) && !/dr-item on/.test(rh));
const detail = { id: 's1', type: 'scene', fields: { title: 'The farm', status: 'locked', characters: ['k'], one_sentence: '', location: null }, sections: { Content: 'KAEL stands.', Notes: '  ' } };
rh = Rd.html(rm({ selected: { type: 'scene', id: 's1' }, detail }));
check('the selected entity is marked and its populated fields and sections are shown', /dr-item on" data-rd="pick" data-type="scene" data-id="s1"/.test(rh) && /<dt>status<\/dt>/.test(rh) && /KAEL stands/.test(rh));
check('empty fields and blank sections are left out', !/<dt>one sentence/.test(rh) && !/<dt>location/.test(rh) && !/>Notes</.test(rh));
check('ids inside values read as names', /<span title="k">Kael<\/span>/.test(rh));
check('the script tab shows the screenplay as the Script view sets it, scene number included', /screenplay-doc screenplay-content dr-script"><h3 class="fountain-scene_heading" data-scenenumber="1">INT\. FARM/.test(Rd.html(rm({ tab: 'script' }))));
check('an empty screenplay says there is no script text yet', /no scenes with script text yet/.test(Rd.html(rm({ tab: 'script', html: '' }))));
check('the reader has no inline handlers', !/\bon[a-z]+\s*=\s*["']/.test(rh.replace(/data-[a-z]+="[^"]*"/g, '')));

// ─── compare ───
const Cp = global.DASH.compare;
const cm = (diff, extra) => Object.assign({
  projectName: 'Oz', a: 'snapshot:d1', b: 'branch:alt', hist: history(), labels: { a: 'Draft 1', b: 'alt · open draft' }, tab: 'entities', showSame: false,
  names: { s1: { name: 'The <i>farm</i>', type: 'scene' }, k: { name: 'Kael', type: 'character' }, sq: { name: 'Road', type: 'sequence' }, s2: { name: 'Gate', type: 'scene' }, s3: { name: 'Poppy', type: 'scene' }, a1: { name: 'Act I', type: 'act' } },
  diff: Object.assign({ entities: {}, order: {}, script: [] }, diff),
}, extra || {});
const changed = (id, f, sec) => ({ id, type: 'scene', status: 'changed', fields: f || {}, sections: sec || {} });
check('two identical drafts say so and offer no tabs', (() => { const h = Cp.html(cm({ entities: { s1: { id: 's1', type: 'scene', status: 'unchanged', fields: {}, sections: {} } } })); return /identical/.test(h) && !/role="tablist"/.test(h); })());
check('the summary is singular for one difference', Cp.summary(cm({ entities: { s1: changed('s1', { status: { a: 'x', b: 'y' } }) } })).text === '1 entity differs (1 changed)');
check('the summary counts kinds, order changes and scenes', Cp.summary(cm({ entities: { s1: changed('s1'), s2: { id: 's2', type: 'scene', status: 'added' }, s3: { id: 's3', type: 'scene', status: 'removed' } }, order: { 'scene:sq': { a: ['s1'], b: ['s2'] } }, script: [{ id: 's1', status: 'edited', placement: {}, text: {} }, { id: 's2', status: 'added', placement: {}, text: {} }] })).text === '3 entities differ (1 changed, 1 added, 1 removed) · 1 order change · 2 scenes differ in the script');
let ch = Cp.html(cm({ entities: { s1: changed('s1', { status: { a: 'planned', b: 'locked' }, characters: { a: ['k'], b: [] } }, { Notes: { a: 'one', b: 'two' } }) } }));
check('a changed entity shows both values and a line diff', /cp-val a">planned/.test(ch) && /cp-val b">locked/.test(ch) && /ln del/.test(ch) && /ln add/.test(ch));
check('ids in a changed value read as names', /<span title="k">Kael<\/span>/.test(ch));
check('an entity name from the data cannot open a tag', !/<i>farm/.test(ch) && /The &lt;i&gt;farm&lt;\/i&gt;/.test(ch));
const contentChange = { Content: { a: 'one\ntwo', b: 'one\nTWO\nthree' }, Objective: { a: 'old', b: 'new' } };
ch = Cp.html(cm({ entities: { s1: changed('s1', {}, contentChange) } }));
check('a scene\'s Content is summarised, not diffed, in the entities tab', /Script text changed · <span class="plus">\+2<\/span> <span class="minus">−1<\/span> lines/.test(ch) && !/<div class="ln (add|del)"><span class="g" aria-hidden="true">[+−]<\/span>(TWO|three)/.test(ch));
check('the summary links to that scene in the Script tab', /data-cp="goto" data-scene="s1"/.test(ch));
check('other sections of a scene still show their diff', /<div class="ln del"><span class="g" aria-hidden="true">−<\/span>old/.test(ch) && /<div class="ln add"><span class="g" aria-hidden="true">\+<\/span>new/.test(ch));
check('a section called Content on another kind of entity is still diffed', /ln add/.test(Cp.html(cm({ entities: { k: Object.assign(changed('k', {}, { Content: { a: 'x', b: 'y' } }), { type: 'character' }) } }))));
check('the first three changed entities open and the rest stay folded', (() => { const e = {}; ['s1', 's2', 's3', 'k'].forEach((id) => { e[id] = changed(id, { status: { a: '1', b: '2' } }); }); return (Cp.html(cm({ entities: e })).match(/<details class="cp-ent" open>/g) || []).length === 3; })());
ch = Cp.html(cm({ entities: { s2: { id: 's2', type: 'scene', status: 'added' }, s3: { id: 's3', type: 'scene', status: 'removed' } } }));
check('an added or removed entity says which draft holds it', /only in alt · open draft/.test(ch) && /only in Draft 1/.test(ch));
ch = Cp.html(cm({ order: { 'scene:sq': { a: ['s1', 's3'], b: ['s1', 's2'] } }, entities: { s1: changed('s1', { status: { a: 'a', b: 'b' } }) } }));
check('an order change marks what left and what arrived, under the parent name', /Order of scenes in Road/.test(ch) && /<li class="del">Poppy/.test(ch) && /<li class="add">Gate/.test(ch));
const blk = (...xs) => xs.map(([type, text]) => ({ type, text }));
const heading = ['heading', 'INT. THE ROAD - DAY'];
const script = [
  { id: 's1', status: 'edited', placement: { a: { act: 'a1', sequence: 'sq', position: 1 }, b: { act: 'a1', sequence: 'sq', position: 1 } }, text: { a: 'one', b: 'two' }, number: { a: 1, b: 1 },
    blocks: { a: blk(heading, ['action', 'Dorothy waits.'], ['character', 'DOROTHY'], ['dialogue', 'Hello.']), b: blk(heading, ['action', 'Dorothy waits.'], ['character', 'DOROTHY'], ['dialogue', 'Hello <b>there</b>.']) } },
  { id: 's2', status: 'moved', placement: { a: { act: 'a1', sequence: 'sq', position: 2 }, b: { act: 'a1', sequence: 'sq', position: 1 } }, text: { a: 'same', b: 'same' }, number: { a: 3, b: 2 }, blocks: { a: blk(heading), b: blk(heading) } },
  { id: 's3', status: 'unchanged', placement: { a: { act: 'a1', sequence: 'sq', position: 3 }, b: { act: 'a1', sequence: 'sq', position: 3 } }, text: { a: 'x', b: 'x' }, number: { a: 2, b: 3 }, blocks: { a: blk(heading), b: blk(heading) } },
];
let sh = Cp.html(cm({ script }, { tab: 'script' }));
check('the script tab hides unchanged scenes behind a toggle that counts them', !/Poppy/.test(sh) && /Show 1 unchanged scene</.test(sh));
check('ticking the toggle shows them', /Poppy/.test(Cp.html(cm({ script }, { tab: 'script', showSame: true }))));
check('a scene row says its number in the script, not its position in a sequence', /scene 1 · Act I · Road/.test(sh) && !/#\d/.test(sh));
check('a scene whose number moved says how', /scene 3 → 2/.test(sh));
check('a moved scene shows no text diff', !/screenplay-doc/.test(Cp.html(cm({ script: [script[1]] }, { tab: 'script' }))));
check('a scene that is new says so, one that left says what it was, one with no text says that', (() => {
  const row = (number, status) => Cp.html(cm({ script: [{ id: 's1', status, placement: {}, text: {}, number, blocks: { a: null, b: null } }] }, { tab: 'script' }));
  return /scene 4 \(new\)/.test(row({ a: null, b: 4 }, 'added')) && /was scene 4/.test(row({ a: 4, b: null }, 'removed')) && /no script text/.test(row({ a: null, b: null }, 'added'));
})());
check('a script diff is set as a screenplay, in the Script view classes', /screenplay-doc screenplay-content cs/.test(sh) && /<h4 class="fountain-character">DOROTHY<\/h4>/.test(sh) && /<p class="fountain-dialogue">/.test(sh) && /<p class="fountain-action">Dorothy waits\./.test(sh));
check('a heading carries the scene number of the side it is on, and stays visible when the change is further down', /data-scenenumber="1"/.test(sh) && sh.indexOf('fountain-scene_heading') < sh.indexOf('cs-row del'));
check('only the changed block is marked; the unchanged blocks are context', (sh.match(/class="cs-row add"/g) || []).length === 1 && (sh.match(/class="cs-row del"/g) || []).length === 1);
check('script text cannot open a tag', !/<b>there/.test(sh) && /Hello &lt;b&gt;there&lt;\/b&gt;/.test(sh));
const bigBlocks = Array.from({ length: 40 }, (_, i) => ({ type: 'action', text: 'LINE ' + i }));
sh = Cp.html(cm({ script: [{ id: 's2', status: 'added', placement: { b: { act: 'a1', sequence: 'sq', position: 1 } }, text: { a: null, b: 'x' }, number: { a: null, b: 5 }, blocks: { a: null, b: bigBlocks } }] }, { tab: 'script' }));
check('a long new scene folds after a screenful and says how much is hidden', /Show 16 more blocks/.test(sh) && (sh.match(/class="cs-row add"/g) || []).length === 40);
check('each picker offers every draft and marks the selected one', (() => { const h = Cp.html(cm({ entities: { s1: changed('s1') } })); return /<option value="snapshot:d1" selected>/.test(h) && /<option value="branch:alt" selected>/.test(h) && /Open drafts/.test(h) && /Saved drafts/.test(h); })());
check('compare has no inline handlers', !/\bon[a-z]+\s*=\s*["']/.test(ch.replace(/data-[a-z]+="[^"]*"/g, '')));

console.log(failures.length ? '\n' + failures.length + ' FAILED' : '\nall checks passed (' + ran + ' checks)');
process.exit(failures.length ? 1 : 0);
