#!/usr/bin/env node
// The scene Beats tab and the character Journey tab, executed for real.
//
//   node tests/dashboard_tabs_harness.js <dashboard_dir> <payload.json>
//
// `<dashboard_dir>` is `src/dashboard`: the modules under test are the ones the
// dashboard actually loads, not the delivered copies in tasks/. `<payload.json>`
// is what `core.db.get_dashboard_data` produced for the fixture project —
// `{"story": …, "sections": …}` — so the reader is exercised on the shape that
// ships. The fixture's own record is what makes the payload-shaped checks
// meaningful: its first beat is Kael answering himself (the self-directed
// arrow), its second puts a location on a lane, and one of its beats opens a gap.
//
// Two behaviours need a story the fixture does not have — the act focus, and
// the ribbon's fill at 1..48 scenes — and those are fed a synthetic story built
// here. Both functions are pure, so a browser would only echo this output.
'use strict';

const fs = require('fs');
const path = require('path');
const assert = require('assert');

const DASHBOARD = process.argv[2];
const JS = path.join(DASHBOARD, 'js');
const CSS = path.join(DASHBOARD, 'css');
const payload = JSON.parse(fs.readFileSync(process.argv[3], 'utf8'));

// A module writes to `window.DASH`; a bare name like `DASH` then resolves in the
// browser, where `window` IS the global scope. Node's module scope is not, so each
// module text runs in a function whose `window` is the shared object below. The text
// is the repo's own dashboard tree, which is the code under test — never input.
const DASH = {};
const win = { DASH, __SECTIONS__: payload.sections || {} };
const load = f => new Function('window', 'DASH',
  fs.readFileSync(path.join(JS, f), 'utf8'))(win, DASH);

// Load order mirrors JS_ORDER's dependency pairs: the value model, then the data
// layer that reads it, then the tab component, then the two tabs. A wrong order
// here is the failure this file exists to make loud.
for (const f of [
  'colors.js', 'utils.js', 'navigation.js',
  'graph/value-graph.js',
  'graph/track-data.js',
  'panels/panel-manager.js',
  'panels/panel-tabs.js',
  'panels/scene-beats-tab.js',
  'panels/character-journey-tab.js',
]) load(f);

const D = DASH;
D.story = payload.story;          // the tabs' own default read

const fails = [];
function check(name, fn) {
  try { fn(); console.log('  ok   ' + name); }
  catch (e) { fails.push(name + ' -> ' + e.message); console.log('  FAIL ' + name + ' -> ' + e.message); }
}

// ---- a story with more than one act, and one with many scenes ---------------------------
// The act focus needs >= 2 acts to exist at all; the fill rule needs scene counts
// the fixture cannot reach. Same shape as the payload, because that is the
// contract: every field read here is one the payload carries.
function story(nScenes, acts) {
  const chars = ['protag', 'antag', 'mentor'];
  const plots = [
    { id: 'main-plot', name: 'The Resistance', plot_scope: 'main', plot_type: 'Setup', characters: chars },
    { id: 'sub-plot', name: "The Scientists' Last Stand", plot_scope: 'sub', plot_type: 'Contradictory', characters: ['protag'] },
  ];
  const scenes = [];
  for (let i = 0; i < nScenes; i++) {
    const plot = i % 2 ? 'sub-plot' : 'main-plot';
    scenes.push({
      id: 's' + i, name: 'Scene ' + (i + 1), title: 'Scene ' + (i + 1),
      order: i + 1, parent_id: 'seq-' + (i % acts), status: 'written', dramatic_role: 'plot_role',
      characters: chars.slice(0, 1 + (i % 3)), locations: [],
      plots: [{ id: plot, role: ['setup', 'complication', 'crisis', 'climax'][i % 4] }],
      milestone: [['inciting_incident', 'complication', 'crisis', 'climax', 'resolution'][i % 5]],
      value_turns: [{
        plot, value: 'Freedom',
        from: ['free', 'imprisoned', 'broken', 'corrupted'][i % 4],
        to: ['free', 'imprisoned', 'broken', 'corrupted'][(i + 1) % 4],
        effects: [{ character: chars[i % 3], levels: [
          { conflict_level: ['inner', 'personal', 'extra-personal'][i % 3], effect: 'a level' }] }],
      }],
    });
  }
  const actList = [], seqList = [];
  for (let k = 0; k < acts; k++) {
    actList.push({ id: 'act-' + k, name: 'Act ' + (k + 1), order: k + 1 });
    seqList.push({ id: 'seq-' + k, name: 'Sequence ' + (k + 1), order: k + 1, parent_id: 'act-' + k });
  }
  return {
    project: { name: 'probe', value_focus: { major: ['Freedom'], minor: [] } },
    characters: chars.map((c, i) => ({ id: c, name: c[0].toUpperCase() + c.slice(1), role: ['protagonist', 'antagonist', 'mentor'][i], scenes: [] })),
    locations: [{ id: 'the-office', name: 'The Office' }],
    worlds: [{ id: 'the-institute', name: 'The Institute' }],
    relationships: [], plots, scenes, acts: actList, sequences: seqList,
    values: [{ name: 'Freedom', p: 'free', c: 'imprisoned', cd: 'broken', nn: 'corrupted' }],
    scene_beats: [],
  };
}

// ---- payload reader (track-data.js) ------------------------------------------------------
console.log('--- payload reader ---');
check('sceneBeatsOf finds the record by `scene`', function () {
  assert.strictEqual(D.sceneBeatsOf('central-room-day').id, 'central-room-day-beats');
});
check('sceneBeatsOf finds it by parent_id alone', function () {
  const hit = D.sceneBeatsOf('the-offer', { scene_beats: [{ id: 'x', parent_id: 'the-offer' }] });
  assert.strictEqual(hit.id, 'x');
});
check('sceneBeatsOf returns null for a scene with none', function () {
  assert.strictEqual(D.sceneBeatsOf('nowhere'), null);
});
check('a scene and its record resolve to the same record, by either key', function () {
  const st = D.story;
  for (const rec of st.scene_beats) {
    assert.strictEqual(D.sceneBeatsOf(rec.parent_id, st).id, rec.id);
    if (rec.scene) assert.strictEqual(D.sceneBeatsOf(rec.scene, st).id, rec.id);
  }
});

console.log('--- entityRef ---');
check('a character resolves by role', function () {
  const r = D.entityRef('kael');
  assert.strictEqual(r.type, 'character');
  assert.strictEqual(r.name, 'Kael');
  assert.strictEqual(r.color, D.roleColor('Protagonist'));
});
check('a location and a world resolve to their kind colour', function () {
  assert.strictEqual(D.entityRef('the-central-room').type, 'location');
  assert.strictEqual(D.entityRef('the-central-room').color, D.ENTITY_KIND_COLORS.location);
  assert.strictEqual(D.entityRef('the-i').type, 'world');
  assert.strictEqual(D.entityRef('the-i').color, D.ENTITY_KIND_COLORS.world);
});
check('the kind colours are the table, not a second copy of them', function () {
  // ENTITY_KIND_COLORS is the single source for these two: entityRef and the
  // entity views' pips must read the same table, or a chip and its card drift.
  assert.strictEqual(D.entityRef('the-central-room').color, '#6bbfb0');
  assert.strictEqual(D.entityRef('the-i').color, '#e0a86b');
});
check('a relationship resolves by its first perspective type', function () {
  const r = D.entityRef('kael-mira');
  assert.strictEqual(r.type, 'relationship');
  assert.strictEqual(r.color, D.relTypeColor('family'));
});
check('an unknown id is grey and says it is unknown', function () {
  const r = D.entityRef('nobody');
  assert.deepStrictEqual(r, { id: 'nobody', type: 'unknown', name: 'nobody', color: '#8a8a8a' });
});

console.log('--- milestoneLabel ---');
check('labels all six milestones, and strips the plot_ prefix', function () {
  const want = { setup: 'Setup', inciting_incident: 'Inciting Incident', complication: 'Complication',
                 crisis: 'Crisis', climax: 'Climax', resolution: 'Resolution' };
  for (const k of Object.keys(want)) assert.strictEqual(D.milestoneLabel(k), want[k], k);
  assert.strictEqual(D.milestoneLabel('plot_climax'), 'Climax');
});

console.log('--- characterTrack ---');
const tr = D.characterTrack('kael', D.story);
check('rows cover every scene that names the character', function () {
  // Presence alone earns a row: the track shows the scenes where nothing was
  // recorded too, grouped as "present, nothing recorded" in the timeline.
  assert.strictEqual(tr.rows.length, 3);
});
check('a row carries its turns', function () { assert.strictEqual(tr.rows[0].turns.length, 2); });
check('protagonist is true when a plot names them', function () {
  assert.strictEqual(tr.protagonist, true);
});
check('coverage counts beats and changes', function () {
  // Two of the fixture's three records are empty placeholders. They must not be
  // counted as beat lists, or the Journey tab disagrees with the Beats tab's own
  // empty state on the same rows.
  assert.strictEqual(tr.coverage.withBeats, 1);
  assert.strictEqual(tr.coverage.appears, 3);
  assert.ok(tr.coverage.changes >= 1, 'the record changes Kael');
});
check('the path reports the deepest rung', function () {
  const p = tr.paths.find(x => x.value === 'Freedom');
  assert.ok(p, 'no Freedom path');
  // Kael is carried from `imprisoned` (rung 2) to `free` (rung 0): the deepest
  // rung visited is 2, whatever the last state is.
  assert.strictEqual(p.first, 'imprisoned');
  assert.strictEqual(p.deepestRung, 2);
});
check('deepestRung is a rung index, never the rung\'s word', function () {
  // The index/word confusion this rename exists to kill: the LLM-facing
  // `story_load` view says `deepest` and means the word ("imprisoned"), so a
  // value here is only ever 0..3 — never a string, never out of range.
  tr.paths.forEach(function (p) {
    assert.ok(p.deepestRung === null ||
      (typeof p.deepestRung === 'number' && p.deepestRung >= 0 && p.deepestRung <= 3),
      'deepestRung is ' + JSON.stringify(p.deepestRung));
  });
});

console.log('--- sections: a placeholder is not content ---');
check('isPlaceholderSection marks the marker and nothing else', function () {
  assert.strictEqual(D.isPlaceholderSection('[placeholder — scene/Objective]'), true);
  assert.strictEqual(D.isPlaceholderSection('  [PLACEHOLDER — plot/Notes]'), true);
  assert.strictEqual(D.isPlaceholderSection('Objective: not filled in'), false);
  assert.strictEqual(D.isPlaceholderSection('The lock was never engaged.'), false);
  assert.strictEqual(D.isPlaceholderSection(''), false);
  assert.strictEqual(D.isPlaceholderSection(null), false);
});
check('renderSectionsHtml drops a placeholder section and keeps a real one', function () {
  const html = D.renderSectionsHtml('scene', 'central-room-day');
  assert.ok(!html.includes('[placeholder'), 'a placeholder reached the markup: ' + html.slice(0, 200));
  assert.ok(html.includes('the door that was always open'), 'the real section was dropped with it');
});
check('a scene of only placeholders renders no section at all', function () {
  const saved = win.__SECTIONS__;
  win.__SECTIONS__ = {scene: {x: {Objective: '[placeholder — scene/Objective]',
                                  Notes: '[placeholder — scene/Notes]'}}};
  assert.strictEqual(D.renderSectionsHtml('scene', 'x'), '');
  win.__SECTIONS__ = saved;
});
check('the Beats tab notes are the shared renderer, and drop placeholders', function () {
  const html = D.renderSceneBeats('central-room-day', D.story, 680);
  assert.ok(!html.includes('[placeholder'));
  assert.ok(html.includes('The lock is the scene'), 'the real note was dropped with it');
});

console.log('--- Beats tab ---');
const sb = D.renderSceneBeats('central-room-day', D.story, 680);
check('renders the driver chip', function () { assert.ok(sb.includes('Kael')); });
check('renders the objective', function () { assert.ok(sb.includes('whether the door was ever locked')); });
check('renders the turning point', function () { assert.ok(sb.includes('The handle turns')); });
check('renders both beat rows', function () {
  assert.ok(sb.includes('id="sb-b0"'), 'beat 0');
  assert.ok(sb.includes('id="sb-b1"'), 'beat 1');
});
check('the gap beat renders as a gap row, the other as mere activity', function () {
  assert.strictEqual((sb.match(/class="sb-gap"/g) || []).length, 1);
  assert.strictEqual((sb.match(/class="sb-beat is-activity"/g) || []).length, 1);
});
check('renders the crack marker on the gap arrow', function () { assert.ok(sb.includes('sb-crack')); });
check('the beat whose actor answers themselves draws the self-directed arrow', function () {
  assert.ok(sb.includes('is-self'), sb.match(/class="sb-link[^"]*"/g));
});
check('the self-directed arrowhead sits at the turn, not on the answering bubble', function () {
  // The path comes back to the lane it left, so the tip is mid-path: the defect
  // was a head at the coordinate the path never reaches.
  const link = sb.match(/is-self" style="grid-column:[^"]*">\s*<svg[^>]*><path d="M ([\d.]+) \d+ C ([\d.]+)/);
  assert.ok(link, 'no self-directed arrow found');
  const tip = sb.match(/is-self[\s\S]{0,300}?<i class="sb-tip" style="left:([\d.]+)%"/);
  assert.ok(tip, 'no arrowhead found');
  assert.strictEqual(Number(tip[1]), Number(link[2]), 'the head is not at the turn');
});
check('a scene with a placeholder record says the list is missing beside its header', function () {
  // The pane is not empty — the scene's value turns still render — so an empty
  // state keyed on the whole pane would stay silent while the strip's dot warns.
  const html = D.renderSceneBeats('central-room-night', D.story, 680);
  assert.ok(html.includes('is-missing') && html.includes('Beat list missing'), html.slice(0, 200));
  assert.ok(html.includes('sb-vals'), 'the header vanished with the message');
});
check('puts the location on a lane of its own', function () {
  assert.ok(sb.includes('The Central Room'), 'the room never became a lane');
});
check('gives the circumstance lane the world actor when a beat has no actor', function () {
  const html = D.renderSceneBeats('x', {
    scenes: [{ id: 'x', status: 'written', dramatic_role: 'plot_role' }],
    scene_beats: [{ id: 'xb', scene: 'x', beats: [
      { action: { surface: 'The lights fail' }, reaction: { by: 'kael', surface: 'He looks up' } }] }],
    characters: [{ id: 'kael', name: 'Kael', role: 'Protagonist' }],
  }, 680);
  assert.ok(html.includes('Circumstance'), html.slice(0, 200));
});
check('renders the closing changes, characters before places', function () {
  assert.ok(sb.includes('No longer believes the door was locked'));
  assert.ok(sb.includes('Stops being a boundary and becomes an exit'));
  assert.ok(sb.indexOf('No longer believes') < sb.indexOf('Stops being a boundary'));
});
check('renders the true-character card', function () {
  assert.ok(sb.includes('He needs the truth more than he needs to be innocent of it.'));
});
check('renders the analysis notes from __SECTIONS__', function () {
  assert.ok(sb.includes('The lock is the scene&#39;s whole mechanism') || sb.includes("The lock is the scene's whole mechanism"));
});
check('hides a placeholder note rather than showing it as content', function () {
  const html = D.renderSceneBeats('central-room-night', D.story, 680);
  assert.ok(!html.includes('[placeholder'), html.slice(0, 300));
});
check('stacks into one column when narrow', function () {
  assert.ok(D.renderSceneBeats('central-room-day', D.story, 300).includes('is-stacked'));
});
check('draws lanes when there is room', function () {
  assert.ok(!D.renderSceneBeats('central-room-day', D.story, 680).includes('is-stacked'));
});

console.log('--- Beats tab: the empty states ---');
check('a record with no beats says the list is missing', function () {
  const html = D.renderSceneBeats('the-core-day', D.story, 680);
  assert.ok(html.includes('is-missing') && html.includes('Beat list missing'), html.slice(0, 200));
});
check('a written scene with no record at all says the list is missing', function () {
  const html = D.renderSceneBeats('x', { scenes: [{ id: 'x', status: 'written', dramatic_role: 'plot_role' }] }, 680);
  assert.ok(html.includes('is-missing') && html.includes('Beat list missing'), html.slice(0, 200));
});
check('a planned scene says the list has not been started', function () {
  const html = D.renderSceneBeats('x', { scenes: [{ id: 'x', status: 'planned' }] }, 680);
  assert.ok(html.includes('Not started') && !html.includes('is-missing'), html.slice(0, 200));
});
check('a transition scene says a beat list is not expected', function () {
  const html = D.renderSceneBeats('x', { scenes: [{ id: 'x', dramatic_role: 'transition' }] }, 680);
  assert.ok(html.includes('No beat list') && !html.includes('is-missing'), html.slice(0, 200));
});

// ---- Journey tab -------------------------------------------------------------------------
console.log('--- Journey tab ---');
const jr = D.renderCharacterJourney('kael', D.story, { width: 680 });
check('renders the coverage stats', function () { assert.ok(jr.includes('jr-stats')); });
check('the stats say how much is on record, not how much exists', function () {
  assert.ok(jr.includes('beat lists exist for 1'), jr.match(/jr-cover[^<]*<\/div>/));
});
check('renders the value chip', function () { assert.ok(jr.includes('Freedom')); });
check('renders the conflict levels reached', function () {
  assert.ok(jr.includes('inner') && jr.includes('extra-pers.'));
});
check('renders the ribbon svg', function () { assert.ok(jr.includes('jr-svg')); });
check('renders the depth rungs', function () { assert.ok(jr.includes('NN')); });
check('labels the milestone via D.milestoneLabel', function () {
  assert.ok(jr.includes('Climax'), jr.slice(0, 800));
});
check('the timeline names every milestone on record', function () {
  assert.ok(jr.includes('Inciting Incident') && jr.includes('Resolution'));
});
check('renders the timeline', function () { assert.ok(jr.includes('jr-timeline')); });
check('renders the wants line for the driving scene', function () { assert.ok(jr.includes('wants')); });
check('nothing-to-trace state for an absent character', function () {
  assert.ok(D.renderCharacterJourney('nobody', D.story, {}).includes('Nothing to trace yet'));
});
check('the ribbon shares the value graph axis, and labels it `plot`', function () {
  // Phase 2 removed the `.replace('>beats</text>', '>plot</text>')` chain: the
  // label is the axis's own parameter, so the graph's two callers keep 'beats'
  // and the ribbon cannot drift from either by a string edit.
  assert.ok(jr.includes('>plot</text>'), 'the ribbon does not label the axis');
  assert.ok(!jr.includes('>beats</text>'), 'the ribbon still says beats');
  assert.strictEqual(D.valueAxisSvg(D.valueModel(D.story), { slot: 40, labelW: 58, W: 400 }).includes('>beats</text>'), true,
    'the value graph\'s own caller lost its label');
  assert.strictEqual(D.valueAxisSvg(D.valueModel(D.story), { slot: 40, labelW: 58, W: 400 }, null).includes('>beats</text>'), true,
    'the value graph\'s second caller lost its label');
});

console.log('--- Journey tab: the act focus ---');
const multi = story(6, 3);
const jrMulti = D.renderCharacterJourney('protag', multi, { width: 680 });
check('a story with acts offers the act focus', function () {
  assert.ok(jrMulti.includes('jr-focus'), 'no act focus in a three-act story');
  assert.ok(jrMulti.includes('data-act="all"') && jrMulti.includes('data-act="1"'));
});
check('one act focus is on, and it is All by default', function () {
  assert.ok(jrMulti.includes('jr-chip on" data-act="all"'), jrMulti.match(/jr-chip[^>]*/g).join(' '));
});
check('focusing an act narrows the ribbon to that act\'s scenes', function () {
  const all = D.renderCharacterJourney('protag', multi, { width: 680 });
  const one = D.renderCharacterJourney('protag', multi, { width: 680, act: 0 });
  const count = h => (h.match(/class="jr-hit/g) || []).length;
  assert.ok(count(one) < count(all), `act focus drew ${count(one)} of ${count(all)} columns`);
  assert.ok(one.includes('jr-chip on" data-act="0"'));
});
check('a single-act story offers no act focus at all', function () {
  assert.ok(!jr.includes('jr-focus'), 'a one-act story has nothing to focus');
});

console.log('--- Journey tab: the ribbon fills its pane ---');
// Ground truth is the width the panel rendered, read out of the svg it produced
// — never a copy of the rule.
function ribbon(nScenes, paneW) {
  const st = story(nScenes, Math.max(1, Math.ceil(nScenes / 4)));
  const html = D.renderCharacterJourney('protag', st, { width: paneW });
  const W = Number((html.match(/<svg class="vg-svg jr-svg" width="([\d.]+)"/) || [])[1]);
  const slot = Number((html.match(/<rect class="jr-hit[^"]*"[^>]*width="([\d.]+)"/) || [])[1]);
  return { n: D.valueModel(st).n, W, slot, share: Math.round(W / paneW * 100) };
}
check('the slot is max(MIN_SLOT, (W - LABEL_W - PAD_R) / n)', function () {
  // LABEL_W = 58 and PAD_R = 8 are the ribbon's own constants, read from the
  // source: a change to them is a change to this arithmetic. The ribbon's width
  // is the unrounded slot times the scene count, so the raw attribute is what
  // the assertion compares.
  const r = ribbon(3, 647);
  assert.strictEqual(r.slot, (647 - 58 - 8) / 3, 'the slot rule moved');
  assert.strictEqual(r.W, Math.ceil(58 + r.slot * 3 + 8), 'the ribbon width does not follow the slot');
});
check('the ribbon fills the pane, and is no longer capped', function () {
  // MAX_SLOT = 46 used to bind exactly where the fill was worst: a short story.
  assert.ok(ribbon(1, 647).share === 100, 'a one-scene ribbon does not fill');
  assert.ok(ribbon(3, 647).share === 100, 'a three-scene ribbon does not fill');
});
check('below MIN_SLOT the ribbon overflows its pane, and .jr-scroll scrolls it', function () {
  // The excess scrolling is what .jr-scroll's overflow-x is for; the marks stop
  // touching their neighbours. 12px is the floor, so 680/12 needs 60+ scenes.
  const r = ribbon(80, 647);
  assert.strictEqual(r.slot, 12, 'the floor is not 12px');
  assert.ok(r.W > 647, `an 80-scene ribbon is ${r.W}px, inside a 647px pane`);
});
check('the fill share holds from one scene to forty-eight', function () {
  for (const n of [1, 2, 3, 5, 8, 12, 20, 30, 48]) {
    const r = ribbon(n, 680);
    assert.ok(r.share >= 99, `${n} scenes fill ${r.share}%`);
  }
});

// ---- CSS contracts ------------------------------------------------------------------------
console.log('--- CSS contracts ---');
const TAB_CSS = ['panel-tabs.css', 'scene-beats.css', 'character-journey.css'];
const TAB_JS = ['panel-tabs.js', 'scene-beats-tab.js', 'character-journey-tab.js'];
const tabCss = TAB_CSS.map(f => fs.readFileSync(path.join(CSS, f), 'utf8')).join('\n');
// The pool a class can be defined in: every dashboard stylesheet, plus the three
// tab stylesheets. A tab must not depend on another tab's file.
const pool = fs.readdirSync(CSS).map(f => fs.readFileSync(path.join(CSS, f), 'utf8')).join('\n');
const baseCss = fs.readFileSync(path.join(CSS, 'base.css'), 'utf8');
const readCss = f => fs.readFileSync(path.join(CSS, f), 'utf8');
const classesIn = src => {
  const used = new Set();
  const re = /class=\\?"([^"$]*)/g; let m;
  while ((m = re.exec(src))) m[1].split(/\s+/).forEach(c => { if (/^[A-Za-z][\w-]*$/.test(c)) used.add(c); });
  return used;
};

check('--c-gap and --c-choice are declared once, in base.css', function () {
  assert.ok(/--c-gap\s*:/.test(baseCss), '--c-gap');
  assert.ok(/--c-choice\s*:/.test(baseCss), '--c-choice');
  assert.strictEqual((tabCss.match(/--c-gap\s*:/g) || []).length, 0, 'redeclared in a tab css');
  assert.strictEqual((tabCss.match(/--c-choice\s*:/g) || []).length, 0, 'redeclared in a tab css');
});
check('--panel-w-wide is declared and used', function () {
  assert.ok(/--panel-w-wide\s*:/.test(baseCss), 'token');
  assert.ok(readCss('components.css').includes('--panel-w-wide'), '.panel-wide rule');
});
check('every class the tab JS emits has a rule somewhere', function () {
  const used = new Set();
  for (const f of TAB_JS) classesIn(fs.readFileSync(path.join(JS, 'panels', f), 'utf8')).forEach(c => used.add(c));
  const missing = [...used].filter(c => pool.indexOf('.' + c) === -1);
  assert.deepStrictEqual(missing, [], 'no rule for: ' + missing.join(', '));
});
check('every class a tab emits resolves in the dashboard\'s CSS or its own', function () {
  // The journey tab once read `.sb-k` / `.sb-diamond` out of the beat tab's
  // stylesheet: a rename in one file silently broke the other. So a class must
  // belong to the dashboard's own CSS or to the tab's own stylesheet — never to
  // another tab's.
  const own = TAB_CSS.map(readCss);
  const foreign = [];
  TAB_JS.forEach((jsFile, k) => {
    const mine = fs.readdirSync(CSS).filter(f => !TAB_CSS.includes(f))
      .map(readCss).join('\n') + '\n' + own[k];
    classesIn(fs.readFileSync(path.join(JS, 'panels', jsFile), 'utf8')).forEach(c => {
      if (!mine.includes('.' + c)) foreign.push(jsFile + ' -> .' + c);
    });
  });
  assert.deepStrictEqual(foreign, [], 'classes with no rule in the dashboard or the tab: ' + foreign.join(', '));
});
check('every var() a tab stylesheet uses resolves', function () {
  // A custom property is either declared in the assembled CSS, or set inline by
  // the tab JS that uses it (`--c`, `--lane`, `--n`, `--a`, `--r`). An undeclared
  // token is a rule that silently falls back to nothing.
  const declared = new Set();
  for (const f of fs.readdirSync(CSS)) (readCss(f).match(/--[\w-]+\s*:/g) || []).forEach(d => declared.add(d.replace(/\s*:$/, '')));
  const inline = new Set();
  for (const f of TAB_JS) (fs.readFileSync(path.join(JS, 'panels', f), 'utf8').match(/--[\w-]+\s*:/g) || [])
    .forEach(d => inline.add(d.replace(/\s*:$/, '')));
  const bad = [...new Set((tabCss.match(/var\((--[\w-]+)/g) || []).map(m => m.slice(4)))]
    .filter(t => !declared.has(t) && !inline.has(t));
  assert.deepStrictEqual(bad, [], 'undeclared tokens: ' + bad.join(', '));
});
check('every data-* a tab reads is one it emits, or a documented protocol', function () {
  // `data-ent` and `data-hermes-send` are the protocol the panel and Hermes speak;
  // the rest must be emitted by the tab JS itself, or the read returns undefined.
  const PROTOCOL = new Set(['ent', 'hermes-send']);
  const js = TAB_JS.map(f => fs.readFileSync(path.join(JS, 'panels', f), 'utf8')).join('\n');
  const emitted = new Set((js.match(/data-[\w-]+\s*=/g) || []).map(m => m.match(/data-([\w-]+)/)[1]));
  const read = new Set();
  for (const m of js.matchAll(/dataset\.([\w-]+)/g)) read.add(m[1]);
  for (const m of js.matchAll(/closest\(\s*'\[data-([\w-]+)\]/g)) read.add(m[1]);
  for (const m of js.matchAll(/querySelector\(['"]\[data-([\w-]+)/g)) read.add(m[1]);
  const orphans = [...read].filter(k => !emitted.has(k) && !PROTOCOL.has(k));
  assert.deepStrictEqual(orphans, [], 'read but never emitted: ' + orphans.join(', '));
});

if (fails.length) { console.log('\n' + fails.length + ' FAILED'); process.exit(1); }
console.log('\nall checks passed');
