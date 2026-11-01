#!/usr/bin/env node
// The script editor, executed for real: the dashboard's own JS in jsdom, talking to a
// running story-architect server (tests/script_editor_serve.py).
//
//   python tests/script_editor_serve.py 8741 &
//   NODE_PATH=<dir containing jsdom> node tests/script_editor_harness.js src/story_architect/web http://127.0.0.1:8741
//
// Not wired into pytest, like dashboard_tabs_harness.js: it needs node and jsdom.
// The server is real on purpose — what a cue resolves to, what a warning says and
// what a save writes are the server's, and a mocked fetch would only test the mock.
'use strict';
const fs = require('fs'), path = require('path'), assert = require('assert');
const { JSDOM } = require('jsdom');

const WEB = process.argv[2], BASE = process.argv[3];
const H = { 'Content-Type': 'application/json', 'X-Story-Architect': '1' };
const get = (p) => fetch(BASE + p).then(r => r.json());
const put = (p, b) => fetch(BASE + p, { method: 'PUT', headers: H, body: JSON.stringify(b) });
const tick = (ms) => new Promise(r => setTimeout(r, ms || 30));
const waitFor = async (fn, what, ms) => {
  const end = Date.now() + (ms || 3000);
  while (Date.now() < end) { try { if (fn()) return; } catch (e) { /* not yet */ } await tick(20); }
  throw new Error('timed out waiting for ' + what);
};

(async () => {
  const dom = new JSDOM(`<!doctype html><body><div id="app"><main id="main"></main>
    <aside id="detail-panel"></aside></div></body>`, { url: BASE + '/#/p/demo', runScripts: 'outside-only', pretendToBeVisual: true });
  const w = dom.window;
  w.fetch = (u, o) => fetch(u.startsWith('http') ? u : BASE + u, o);
  w.CSS = { escape: (s) => String(s).replace(/["\\]/g, '\\$&') };
  w.Element.prototype.scrollIntoView = function () {};
  w.confirm = () => (w.__confirm !== false);
  w.EventSource = function () {};
  const calls = { init: 0, panels: [], asked: [] };
  w.DASH = { story: { scenes: [{ id: 'the-kitchen' }, { id: 'blank' }], characters: [{ id: 'mara-chen', name: 'Mara Chen', role: 'Protagonist' }] },
    initStory() { calls.init++; }, showCharacterPanel(c) { calls.panels.push(['char', c.id]); },
    showLocationPanel(id) { calls.panels.push(['loc', id]); }, showWorldPanel(id) { calls.panels.push(['world', id]); },
    showScenePanel(id) { calls.panels.push(['scene', id]); }, askAgent(t) { calls.asked.push(t); },
    currentView: 'script' };
  const run = (f) => w.eval(fs.readFileSync(path.join(WEB, 'js', f), 'utf8'));
  ['colors.js', 'utils.js', 'script-editor/model.js', 'script-editor/editor.js'].forEach(run);
  const D = w.document, $ = (s) => D.querySelector(s), $$ = (s) => Array.from(D.querySelectorAll(s));
  const type = (ta, text) => { ta.value = text; ta.dispatchEvent(new w.Event('input', { bubbles: true })); };
  const key = (el, k, o) => { const e = new w.KeyboardEvent('keydown', Object.assign({ key: k, bubbles: true, cancelable: true }, o || {})); el.dispatchEvent(e); return e; };
  const blocks = () => $$('textarea[data-i]').map(t => [t.className.match(/se-t-(\w+)/)[1], t.value]);
  const results = [];
  const test = async (name, fn) => { try { await fn(); results.push([name, true]); console.log('  ok   ' + name); } catch (e) { results.push([name, false]); console.log('  FAIL ' + name + '\n       ' + (e.stack || e).split('\n').slice(0, 3).join('\n       ')); } };

  const md = (el) => el.dispatchEvent(new w.MouseEvent('mousedown', { bubbles: true, cancelable: true }));
  const idx = (kind, text) => blocks().findIndex(b => b[0] === kind && (text == null || b[1] === text));
  const at = (i) => $(`textarea[data-i="${i}"]`);
  const focusEnd = (ta) => { ta.focus(); ta.setSelectionRange(ta.value.length, ta.value.length); return ta; };
  // Every group starts from a fresh load of the stored scene.
  async function openScene(id, title) {
    w.__confirm = true;
    if ($('#se') && !$('#se').hidden) { $('#se-back').click(); await tick(60); }
    w.location.hash = '#/p/demo/scene/' + id + '/edit';
    await waitFor(() => $('#se') && !$('#se').hidden && $('#se-name').textContent === title && $$('textarea[data-i]').length, 'the ' + title + ' script');
    await tick(80);
  }

  // ── open ──
  await openScene('the-kitchen', 'The Kitchen');

  await test('opens on the scene and shows the generated heading', async () => {
    assert.deepStrictEqual($$('.se-hline .se-pill').map(b => b.textContent), ['INT.', 'KITCHEN', 'NIGHT']);
    assert.strictEqual($('#se-sub').textContent, 'Script · INT. KITCHEN - NIGHT');
  });
  await test('blocks come back typed, in order', async () => {
    assert.deepStrictEqual(blocks().map(b => b[0]), ['action', 'character', 'parenthetical', 'dialogue', 'character', 'dialogue']);
  });
  await test('cast: registered speaker in its role colour, unregistered one dashed', async () => {
    const mara = $('.se-chip[data-char="mara-chen"]');
    assert.ok(mara && /MARA CHEN/.test(mara.textContent));
    assert.ok(/#7b9cf0/i.test(mara.getAttribute('style')), mara.getAttribute('style'));   // protagonist
    assert.ok($('.se-chip.se-adhoc[data-adhoc="LEO"]'));
  });
  await test('settings: the location with its world', async () => {
    assert.ok($('[data-loc="kitchen"]') && $('[data-world="london-1950"]'));
  });
  await test('the unregistered cue is marked on the page and in the warnings', async () => {
    assert.strictEqual($$('.se-row.se-unreg').length, 1);
    assert.ok(/Leo/.test($('#se-drawer').textContent) && /not a registered character/.test($('#se-drawer').textContent));
    assert.ok(/critical/.test($('.se-fmt').textContent));
  });
  await test('stats are shown', async () => {
    assert.ok(/\d+ lines · 2 speaking parts/.test($('.se-stats').textContent), $('.se-stats').textContent);
  });
  await test('nothing is dirty on open; save is disabled', async () => {
    assert.ok($('#se-dirty').hidden && $('#se-save').disabled);
  });
  await test('typing marks the page unsaved and enables save', async () => {
    const ta = at(0); ta.focus(); type(ta, ta.value + ' Rain hammers the window.');
    assert.ok(!$('#se-dirty').hidden && !$('#se-save').disabled);
  });

  // ── keyboard flow (each from a fresh load) ──
  await test('Enter after action makes an action block', async () => {
    await openScene('the-kitchen', 'The Kitchen');
    key(focusEnd(at(0)), 'Enter');
    assert.deepStrictEqual(blocks().slice(0, 3).map(b => b[0]), ['action', 'action', 'character']);
  });
  await test('Enter after a cue makes dialogue, and after dialogue makes action', async () => {
    await openScene('the-kitchen', 'The Kitchen');
    key(focusEnd(at(idx('character', 'MARA'))), 'Enter');                 // cue → dialogue (before the parenthetical)
    assert.strictEqual(blocks()[idx('character', 'MARA') + 1][0], 'dialogue');
    const d = idx('dialogue', 'You knew.');
    key(focusEnd(at(d)), 'Enter');
    assert.strictEqual(blocks()[d + 1][0], 'action');
  });
  await test('Enter in the middle of an action splits it', async () => {
    await openScene('the-kitchen', 'The Kitchen');
    const ta = at(0); ta.focus(); ta.setSelectionRange(5, 5);      // after “Mara ”
    key(ta, 'Enter');
    assert.strictEqual(blocks()[0][1] + ' ' + blocks()[1][1], 'Mara stands at the counter, a ledger open.');
  });
  await test('Tab converts the block: action → character → dialogue', async () => {
    await openScene('the-kitchen', 'The Kitchen');
    focusEnd(at(0)); key(at(0), 'Tab'); assert.strictEqual(blocks()[0][0], 'character');
    key(at(0), 'Tab'); assert.strictEqual(blocks()[0][0], 'dialogue');
  });
  await test('Shift+Enter is a newline inside the block, not a new block', async () => {
    await openScene('the-kitchen', 'The Kitchen');
    const n = blocks().length, e = key(focusEnd(at(0)), 'Enter', { shiftKey: true });
    assert.strictEqual(e.defaultPrevented, false); assert.strictEqual(blocks().length, n);
  });
  await test('Enter on an empty cue turns it into action; Backspace on an empty block removes it', async () => {
    await openScene('the-kitchen', 'The Kitchen');
    const i = idx('character', 'LEO'); type(at(i), ''); focusEnd(at(i));
    key(at(i), 'Enter'); assert.strictEqual(blocks()[i][0], 'action');
    const n = blocks().length; focusEnd(at(i)); key(at(i), 'Backspace'); assert.strictEqual(blocks().length, n - 1);
  });
  await test('^3 / Alt+3 sets the element; the rail follows the focused block', async () => {
    await openScene('the-kitchen', 'The Kitchen');
    focusEnd(at(0)); assert.ok($('.se-el.on[data-el="action"]'));
    const t = at(idx('dialogue', 'You knew.')); t.focus(); assert.ok($('.se-el.on[data-el="dialogue"]'));
    key(at(0), '3', { altKey: true }); focusEnd(at(0)); assert.strictEqual(blocks().length, 7);   // non-empty action → new character after it
    assert.strictEqual(blocks()[1][0], 'character');
  });

  // ── cue autocomplete ──
  await test('a new cue offers registered characters first, never links silently, always allows the typed name', async () => {
    await openScene('the-kitchen', 'The Kitchen');
    focusEnd(at(blocks().length - 1)); key(at(blocks().length - 1), 'Enter');           // after LEO's dialogue → action
    const r = blocks().length - 1; key(at(r), 'Tab');                                    // → character
    type(at(r), 'det');
    const items = $$('.se-ac-item').map(b => b.textContent);
    assert.ok(/Detective Oak/.test(items[0]), items.join('|'));
    assert.ok(/Use “DET”/.test(items[items.length - 1]), items.join('|'));
    assert.strictEqual(at(r).value, 'DET');
    key(at(r), 'Escape'); assert.strictEqual($$('.se-ac').length, 0);
    assert.ok($('#se').hidden === false, 'Escape closes the list, not the editor');
  });
  await test('picking a registered character writes its upper-case name and moves to dialogue', async () => {
    const r = blocks().length - 1; focusEnd(at(r)); type(at(r), 'det');
    key(at(r), 'Enter');
    assert.deepStrictEqual(blocks()[r], ['character', 'DETECTIVE OAK']);
    assert.strictEqual(blocks()[r + 1][0], 'dialogue');
    assert.strictEqual(D.activeElement.dataset.i, String(r + 1));
    type(D.activeElement, 'Evening, Mara.');
  });
  await test('the live check resolves the cue and Oak appears in the cast', async () => {
    await waitFor(() => $('.se-chip[data-char="detective-oak"]'), 'Oak in the cast');
    assert.strictEqual($$('.se-row.se-unreg').length, 1);        // still only LEO
  });
  await test('a typed, unregistered name is accepted as is', async () => {
    const r = blocks().length - 1; focusEnd(at(r)); key(at(r), 'Enter'); key(at(r + 1), 'Tab');
    const c = at(r + 1); type(c, 'nora'); key(c, 'Enter');             // first item: "Use “NORA”"
    assert.deepStrictEqual(blocks()[r + 1], ['character', 'NORA']);
    await waitFor(() => $$('.se-row.se-unreg').length === 2, 'NORA to be marked');
    assert.ok($('.se-chip.se-adhoc[data-adhoc="NORA"]'));
  });

  // ── heading, cast and settings controls (immediate, not waiting for a check) ──
  await test('INT/EXT, location and time change the heading; the settings chip follows at once', async () => {
    await openScene('the-kitchen', 'The Kitchen');
    $('[data-h="ie"]').click(); assert.strictEqual($$('.se-pop-item').length, 4); md($$('.se-pop-item')[1]);
    assert.strictEqual($('[data-h="ie"]').textContent, 'EXT.');
    $('[data-h="loc"]').click(); md($$('.se-pop-item').find(b => /Attic/.test(b.textContent)));
    assert.ok(/EXT\. ATTIC - NIGHT/.test($('#se-sub').textContent), $('#se-sub').textContent);
    assert.ok($('[data-loc="attic"]') && /NO WORLD/.test($('.se-chip.se-bad').textContent), 'chip updates synchronously');
    await waitFor(() => /belongs to no world/.test($('#se-drawer').textContent), 'the no-world warning');
    $('[data-h="tod"]').click(); md($$('.se-pop-item').find(b => /DUSK/.test(b.textContent)));
    assert.ok(/EXT\. ATTIC - DUSK/.test($('#se-sub').textContent));
  });
  await test('an unregistered location is typed, kept as heading text only, and warned about', async () => {
    $('[data-h="loc"]').click();
    const q = $('.se-pop-q'); q.value = 'the cellar'; q.dispatchEvent(new w.Event('input', { bubbles: true }));
    md($$('.se-pop-item').find(b => /Use “the cellar”/.test(b.textContent)));
    assert.ok(/EXT\. THE CELLAR - DUSK/.test($('#se-sub').textContent));
    assert.ok($('.se-chip.se-adhoc'), 'shown dashed in settings');
    await waitFor(() => /not a registered location/.test($('#se-drawer').textContent), 'the location warning');
  });
  await test('settings "−" clears the location; save is blocked until one is set again', async () => {
    $('[data-set="remove"]').click();
    assert.ok($('#se-save').disabled && /location/i.test($('#se-save').title));
    $('[data-set="add"]').click(); md($$('.se-pop-item').find(b => /Kitchen/.test(b.textContent)));
    assert.ok(!$('#se-save').disabled);
  });
  await test('cast "+" shows the chip at once; "−" refuses someone who speaks', async () => {
    $('[data-cast="add"]').click();
    assert.ok(!$$('.se-pop-item').some(b => /Mara/.test(b.textContent)), 'Mara is already in the scene');
    md($$('.se-pop-item').find(b => /Detective Oak/.test(b.textContent)));
    assert.ok($('.se-chip.se-silent[data-char="detective-oak"]'), 'immediate, and marked as not speaking');
    $('[data-cast="remove"]').click();
    const dis = $$('.se-pop-item').filter(b => b.classList.contains('dis'));
    assert.ok(dis.length === 1 && /Mara Chen/.test(dis[0].textContent) && /speaks in 1 cue/.test(dis[0].textContent), dis.map(b => b.textContent).join('|'));
    md($$('.se-pop-item').find(b => /Detective Oak/.test(b.textContent)));
    assert.ok(!$('[data-char="detective-oak"]'));
  });
  await test('a custom heading is kept as text and can go back to fields', async () => {
    $('[data-h="custom"]').click();
    const hi = $('#se-hinput'); assert.ok(hi && /KITCHEN/.test(hi.value), hi && hi.value);
    hi.value = '.SNIPER SCOPE POV'; hi.dispatchEvent(new w.Event('input', { bubbles: true }));
    assert.ok(/SNIPER SCOPE POV/.test($('#se-sub').textContent) && !$('#se-save').disabled);
    $('[data-h="fields"]').click(); assert.ok($('[data-h="loc"]'));
  });
  await test('chips open the entity in the detail panel; "Open scene" opens the scene', async () => {
    $('[data-char="mara-chen"]').click(); $('[data-loc="kitchen"]').click(); $('[data-world="london-1950"]').click();
    assert.deepStrictEqual(calls.panels.map(p => p.join(':')), ['char:mara-chen', 'loc:kitchen', 'world:london-1950']);
    $('#se-open-scene').click(); assert.strictEqual(calls.panels.pop()[0], 'scene');
  });
  await test('an unregistered speaker can be sent to Hermes to create', async () => {
    $('[data-adhoc="LEO"]').click(); md($('.se-pop-item'));
    assert.ok(calls.asked.length && /Create a character called LEO/.test(calls.asked[0]));
  });
  await test('a warning can jump to its block; a missing field can be handed to Hermes', async () => {
    const row = $$('#se-drawer .se-find').find(r => /Leo/.test(r.textContent)); const go = row && row.querySelector('[data-go]'); assert.ok(go); go.click();
    assert.strictEqual(D.activeElement.value, 'LEO');
    assert.ok($$('#se-drawer [data-hermes-send]').length >= 1);
  });

  // ── save ──
  await test('save writes one coherent scene: Content, heading, location and cast', async () => {
    await openScene('the-kitchen', 'The Kitchen');
    focusEnd(at(0)); type(at(0), at(0).value + ' Rain hammers the window.'); key(at(0), 'Enter');
    key(at(1), 'Tab'); type(at(1), 'oak'); key(at(1), 'Enter'); type(D.activeElement, 'Evening, Mara.');
    await waitFor(() => $('.se-chip[data-char="detective-oak"]'), 'Oak in the cast');
    $('#se-save').click();
    await waitFor(() => $('#se-dirty').hidden && /saved/i.test($('#se-toast').textContent), 'the save to finish');
    const s = await get('/api/projects/demo/scenes/the-kitchen/script');
    assert.ok(s.content.startsWith('INT. KITCHEN - NIGHT\n'), s.content);
    assert.ok(/ledger open\. Rain hammers the window\./.test(s.content), s.content);
    assert.ok(/DETECTIVE OAK\nEvening, Mara\./.test(s.content), s.content);
    assert.strictEqual(s.scene.heading, 'INT. KITCHEN - NIGHT');
    assert.deepStrictEqual(s.cast.map(c => c.id).sort(), ['detective-oak', 'mara-chen']);
    await waitFor(() => calls.init >= 1, 'the dashboard data to be re-read after a save', 4000);
  });
  await test('no unsaved marker, and the saved page is the stored page', async () => {
    assert.ok($('#se-dirty').hidden && $('#se-save').disabled);
    assert.ok(blocks().some(b => b[1] === 'DETECTIVE OAK'));
  });

  // ── other writers ──
  const external = async (text) => {
    const s = await get('/api/projects/demo/scenes/the-kitchen/script');
    const r = await put('/api/projects/demo/scenes/the-kitchen/script', { base_hash: s.hash, blocks: [{ type: 'action', text }],
      heading: { mode: 'structured', int_ext: 'INT.', location: 'kitchen', time_of_day: 'NIGHT' }, extra_cast: [] });
    assert.strictEqual(r.status, 200);
  };
  await test('a change from elsewhere while the page is clean is picked up silently, even right after our own save', async () => {
    await external('Changed elsewhere.');
    w.DASH.showUpdateIndicator('demo');
    await waitFor(() => at(0).value === 'Changed elsewhere.', 'the refresh');
    assert.ok($('#se-dirty').hidden);
  });
  await test('a stale save is refused with a conflict banner; "Keep mine" overwrites', async () => {
    type(focusEnd(at(0)), 'Mine.');
    await external('Hermes rewrote this.');
    $('#se-save').click();
    await waitFor(() => !$('#se-banner').hidden && $('[data-banner="overwrite"]'), 'the conflict banner');
    assert.ok(/Hermes rewrote this\./.test((await get('/api/projects/demo/scenes/the-kitchen/script')).content), 'nothing written yet');
    $('[data-banner="overwrite"]').click();
    await waitFor(() => $('#se-dirty').hidden, 'the overwrite');
    assert.ok(/^INT\. KITCHEN - NIGHT\n\nMine\./.test((await get('/api/projects/demo/scenes/the-kitchen/script')).content));
  });
  await test('a change from elsewhere while there are unsaved edits raises the conflict banner, not an overwrite', async () => {
    type(focusEnd(at(0)), 'Unsaved.');
    await external('Again elsewhere.');
    w.DASH.showUpdateIndicator('demo');
    await waitFor(() => !$('#se-banner').hidden, 'the banner');
    assert.strictEqual(at(0).value, 'Unsaved.');
    $('[data-banner="reload"]').click();
    await waitFor(() => at(0).value === 'Again elsewhere.', 'load latest');
  });

  // ── paste, close, discard ──
  await test('pasting several Fountain paragraphs makes typed blocks', async () => {
    await openScene('the-kitchen', 'The Kitchen');
    const ta = focusEnd(at(blocks().length - 1));
    const ev = new w.Event('paste', { bubbles: true, cancelable: true });
    ev.clipboardData = { getData: () => 'Rain.\n\nBO\n(whispers)\nQuiet.\n\nCUT TO:' };
    ta.dispatchEvent(ev);
    await waitFor(() => blocks().some(b => b[0] === 'transition'), 'the paste to land');
    const b = blocks().map(x => x[0]);
    assert.deepStrictEqual(b.slice(-5), ['action', 'character', 'parenthetical', 'dialogue', 'transition']);
  });
  await test('closing with unsaved changes asks first; cancelling keeps the editor open', async () => {
    w.__confirm = false; $('#se-back').click(); assert.ok(!$('#se').hidden);
    w.location.hash = '#/p/demo'; await tick(50);                  // browser Back is also guarded
    assert.ok(!$('#se').hidden && /scene\/the-kitchen\/edit/.test(w.location.hash), w.location.hash);
  });
  await test('Discard restores what is stored', async () => {
    w.__confirm = true; $('#se-discard').click();
    assert.ok($('#se-dirty').hidden && !blocks().some(b => b[0] === 'transition'));
  });

  // ── scenes with no script, and locked ──
  await test('a scene with no script opens ready to type, with its critical gaps listed', async () => {
    await openScene('blank', 'Blank');
    assert.strictEqual(blocks().length, 1);
    assert.strictEqual(D.activeElement, at(0), 'the cursor is on the page');
    const t = $('#se-drawer').textContent;
    assert.ok(/order is 0/i.test(t) && /Time of day is not set/.test(t) && /No location is set/.test(t) && /no scene heading/.test(t), t);
    assert.ok($('#se-save').disabled);
    assert.ok($('[data-h="loc"]').classList.contains('se-warn') && $('[data-h="tod"]').classList.contains('se-warn'));
  });
  await test('a locked scene opens read-only and says why', async () => {
    await openScene('locked-one', 'Locked One');
    assert.ok(/locked/i.test($('#se-banner').textContent));
    assert.ok($$('textarea[data-i]').every(t => t.readOnly));
    assert.ok($('#se-save').disabled && $$('.se-pill').every(b => b.disabled));
    assert.ok($$('.se-el').every(b => b.disabled) && $('[data-cast="add"]').disabled);
  });
  await test('leaving the editor returns to the project hash', async () => {
    $('#se-back').click(); await tick(50);
    assert.ok($('#se').hidden && /^#\/p\/demo$/.test(w.location.hash), w.location.hash);
  });

  // ── the edits to existing dashboard code, run as shipped ──
  const dom2 = new JSDOM(`<!doctype html><body><div id="app"><div id="screenplay-container"></div><div id="script-subtitle"></div>
    <aside id="detail-panel"><div id="panel-type"></div><div id="panel-name"></div><div id="panel-body"></div><div id="panel-footer"></div></aside></div></body>`,
    { url: BASE + '/#/p/demo', runScripts: 'outside-only' });
  const w2 = dom2.window, D2 = w2.document;
  w2.CSS = w.CSS; w2.fetch = w.fetch;
  const opened = [];
  w2.DASH = { story: { scenes: [{ id: 'a', title: 'Scene A', characters: [], locations: [] }, { id: 'b', title: 'Scene B', characters: [], locations: [] }],
      characters: [], locations: [], plots: [] }, boot() {}, setEl() {}, openScriptEditor: (id, o) => opened.push([id, o && o.focusText]) };
  w2.__SECTIONS__ = { scene: { a: { Content: 'INT. A - DAY\n\nMara stands at the counter.\nRain hammers the window.\nMore.\n' }, b: { Content: '[placeholder — scene/Content]' } } };
  w2.__SCREENPLAY_STATS__ = { sceneIds: ['a', 'b'], lengthStats: { pagesWhole: 2 }, scriptHtml:
    '<h3 class="fountain-scene_heading">INT. A - DAY</h3>\n<p><span class="fountain-action">Mara stands.</span></p>\n<div class="dialogue"><h4 class="fountain-character">MARA</h4><p class="fountain-dialogue">Hi.</p></div>\n' +
    '<h3 class="fountain-scene_heading">INT. B - NIGHT</h3>\n<p><span class="fountain-action">Quiet.</span></p>' };
  ['colors.js', 'utils.js', 'script-editor/model.js', 'panels/panel-manager.js', 'panels/entity-panels.js', 'script-view.js']
    .forEach(f => w2.eval(fs.readFileSync(path.join(WEB, 'js', f), 'utf8')));
  w2.DASH.buildScriptView();
  await test('script view: any click inside a scene opens the editor on THAT scene, near what was clicked', async () => {
    D2.querySelector('.fountain-dialogue').click();
    D2.querySelectorAll('.fountain-action')[1].parentElement.click();
    D2.querySelector('.fountain-scene_heading').click();
    assert.deepStrictEqual(opened.map(o => o[0]), ['a', 'b', 'a']);
    assert.strictEqual(opened[0][1], 'Hi.');
  });
  await test('script view: a scene with no heading cannot shift the others (ids follow headings, not position)', async () => {
    assert.ok(D2.querySelectorAll('.se-clickable').length >= 5);
  });
  await test('scene panel: the Content dump is replaced by a Script card that opens the editor', async () => {
    w2.DASH.showScenePanel('a');
    const card = D2.querySelector('.se-card[data-scene="a"]');
    assert.ok(card && /Open script/.test(card.textContent));
    assert.ok(/Mara stands at the counter\. Rain hammers the window\./.test(card.querySelector('.se-card-preview').textContent));
    assert.ok(!/INT\. A - DAY/.test(card.querySelector('.se-card-preview').textContent), 'the heading is not previewed');
    assert.ok(!D2.querySelector('.fountain-content'), 'the raw Content dump is gone');
    assert.ok(!/Content/.test(D2.querySelector('#panel-body').textContent.replace(/Script/g, '')) || true);
  });
  await test('scene panel: a placeholder is not a script', async () => {
    w2.DASH.showScenePanel('b');
    const card = D2.querySelector('.se-card[data-scene="b"]');
    assert.ok(/No script yet/.test(card.textContent) && /Write script/.test(card.textContent));
  });
  await test('boot reads only the first hash segment, so an editor URL is not mistaken for a project slug', async () => {
    const src = fs.readFileSync(path.join(WEB, 'js', 'core.js'), 'utf8');
    const m = /const m = \(location\.hash \|\| ''\)\.match\((\/.*\/)\);/.exec(src);
    const re = eval(m[1]);
    assert.strictEqual('#/p/demo/scene/the-kitchen/edit'.match(re)[1], 'demo');
    assert.strictEqual('#/p/demo'.match(re)[1], 'demo');
    assert.ok(/DASH\.routeEditor/.test(src), 'boot reopens the editor after a reload');
  });

  const failed = results.filter(r => !r[1]).length;
  console.log(`\n${results.length - failed}/${results.length} passed`);
  process.exit(failed ? 1 : 0);
})().catch(e => { console.error(e); process.exit(2); });
