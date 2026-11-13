// Script editor — the logic that has no DOM. Kept apart so it can be run under
// node (tests/script_editor_harness.js) and so editor.js stays about rendering.
//
// The server owns what a cue resolves to, what a warning means and how blocks
// become Fountain (core/scene_script.py). Nothing here re-implements those: this
// module is only the *editing* rules — which block a keypress makes, how a
// cue's autocomplete is ranked, whether the page differs from what was loaded.
window.DASH = window.DASH || {};

DASH.SEModel = (function () {
  'use strict';

  // Enter at the end of a block makes this; Tab converts the current block to this.
  // Final Draft's flow: a cue leads to dialogue, dialogue leads back to action.
  const NEXT_ON_ENTER = {
    action: 'action', character: 'dialogue', parenthetical: 'dialogue',
    dialogue: 'action', transition: 'action', note: 'action', raw: 'action',
  };
  const TAB_TYPE = {
    action: 'character', character: 'dialogue', parenthetical: 'dialogue',
    dialogue: 'parenthetical', transition: 'action', note: 'action', raw: 'action',
  };
  // The order the element list shows, and its Ctrl+n shortcut (1 is the heading).
  const ELEMENTS = [
    { type: 'heading', label: 'Scene heading' },
    { type: 'action', label: 'Action' },
    { type: 'character', label: 'Character' },
    { type: 'parenthetical', label: 'Parenthetical' },
    { type: 'dialogue', label: 'Dialogue' },
    { type: 'transition', label: 'Transition' },
    { type: 'note', label: 'Note' },
  ];
  const GUTTER = {
    heading: 'Heading', action: 'Action', character: 'Character', parenthetical: 'Paren.',
    dialogue: 'Dialogue', transition: 'Transition', note: 'Note', raw: 'Fountain',
  };
  // A cue, a parenthetical and a transition are one line; the rest may span lines.
  const SINGLE_LINE = new Set(['character', 'parenthetical', 'transition']);
  const INT_EXT = ['INT.', 'EXT.', 'INT./EXT.', 'EST.'];
  const TIMES = ['DAY', 'NIGHT', 'DUSK', 'DAWN', 'CONTINUOUS', 'LATER'];

  // Text a block is allowed to hold, for its type.
  function normalizeText(type, text) {
    let t = String(text == null ? '' : text);
    if (SINGLE_LINE.has(type)) t = t.replace(/\s*\n\s*/g, ' ');
    if (type === 'character' || type === 'transition') t = t.toUpperCase();
    return t;
  }

  // Wrap a parenthetical's text in parentheses once the person is done with it.
  function wrapParenthetical(text) {
    const t = String(text || '').trim();
    if (!t) return '';
    const inner = t.replace(/^\(+/, '').replace(/\)+$/, '').trim();
    return inner ? '(' + inner + ')' : '';
  }

  const clone = (blocks) => blocks.map(b => ({ type: b.type, text: b.text }));

  function insertAfter(blocks, i, type, text) {
    const out = clone(blocks);
    out.splice(i + 1, 0, { type, text: text || '' });
    return { blocks: out, index: i + 1 };
  }
  function convert(blocks, i, type) {
    const out = clone(blocks);
    const b = out[i];
    b.type = type;
    b.text = normalizeText(type, b.text);
    if (type === 'parenthetical' && !b.text.trim()) b.text = '()';
    return out;
  }
  function removeAt(blocks, i) {
    const out = clone(blocks);
    out.splice(i, 1);
    return out;
  }
  // Enter in the middle of a block: what is after the caret moves to a new
  // block of the same kind (action and dialogue; a one-line block never splits).
  function splitAt(blocks, i, pos) {
    const out = clone(blocks);
    const b = out[i];
    const after = b.text.slice(pos);
    b.text = b.text.slice(0, pos).replace(/\s+$/, '');
    out.splice(i + 1, 0, { type: b.type, text: after.replace(/^\s+/, '') });
    return { blocks: out, index: i + 1 };
  }

  // What Enter does at (blocks[i], caret). Returns an action the editor applies.
  function onEnter(blocks, i, pos) {
    const b = blocks[i];
    const empty = !b.text.trim();
    if (empty) {
      return b.type === 'action' ? { kind: 'none' } : { kind: 'convert', type: 'action' };
    }
    const atEnd = pos >= b.text.length;
    if (!atEnd && !SINGLE_LINE.has(b.type) && b.type !== 'raw') return { kind: 'split', pos };
    return { kind: 'insert', type: NEXT_ON_ENTER[b.type] || 'action' };
  }

  // The state the page is judged "unsaved" against.
  function snapshot(state) {
    return JSON.stringify({
      b: state.blocks.map(b => [b.type, b.text]),
      h: [state.H.forced ? 1 : 0, state.H.int_ext, state.H.location, state.H.place,
          state.H.time_of_day, state.H.forced_heading],
      c: Array.from(state.extraCast).sort(),
    });
  }

  // The heading as shown. The server composes the real one; this is only the
  // preview, so it follows the same rules: a forced heading is shown verbatim,
  // an unusable composed one is empty, the location and place are upper-cased,
  // and a time is always emitted (UNSPECIFIED when unset).
  function composeHeading(H, locationName) {
    if (H.forced) return H.forced_heading || '';
    if (!H.int_ext) return '';
    const name = String(locationName || '').trim().replace(/\s+/g, ' ').toUpperCase();
    if (!name) return '';
    const place = String(H.place || '').trim().replace(/\s+/g, ' ').toUpperCase();
    return H.int_ext + ' ' + name + (place ? ' - ' + place : '') +
      ' - ' + (H.time_of_day || 'UNSPECIFIED');
  }

  // Can this page be saved? Mirrors the hard rule the server enforces on a
  // structured heading (it needs int_ext + location); the rest the server
  // refuses itself.
  function saveBlocker(state) {
    const H = state.H;
    if (H.forced) {
      return /^\s*(\.[^.]|int|ext|est|i\/e)/i.test(H.forced_heading || '')
        ? '' : 'The heading must be a scene heading.';
    }
    if (!H.int_ext) return 'Choose INT/EXT for the scene heading.';
    if (!H.location) return 'Set a location in the scene heading.';
    if ((H.place || '').includes(' - ')) return "The place cannot contain ' - '.";
    return '';
  }

  // Autocomplete for a character cue.
  //   registry:   [{id,name,story_role}]            every registered character
  //   castIds:    ids in this scene's cast           (ranked first)
  //   here:       [{cue,name}]                       unregistered speakers in this script
  //   elsewhere:  [{cue,name,scenes}]                unregistered speakers in other scenes
  // An unregistered name is offered, never forced: typing one is always allowed.
  function acItems(query, registry, castIds, here, elsewhere) {
    const q = String(query || '').trim().toUpperCase();
    const inCast = new Set(castIds || []);
    const hit = (s) => !q || String(s).toUpperCase().includes(q);
    const items = [];
    const reg = (registry || []).filter(c => hit(c.name));
    reg.sort((a, b) => (inCast.has(b.id) - inCast.has(a.id)) || a.name.localeCompare(b.name));
    reg.forEach(c => items.push({
      kind: 'registered', id: c.id, label: c.name, insert: c.name.toUpperCase(),
      role: c.story_role, tag: inCast.has(c.id) ? 'in scene' : 'registered',
    }));
    const seen = new Set(items.map(i => i.insert));
    (here || []).filter(a => hit(a.cue) && !seen.has(a.cue)).forEach(a => {
      seen.add(a.cue);
      items.push({ kind: 'adhoc', label: a.name, insert: a.cue, tag: 'unregistered · this scene' });
    });
    (elsewhere || []).filter(a => hit(a.cue) && !seen.has(a.cue)).forEach(a => {
      seen.add(a.cue);
      items.push({ kind: 'adhoc', label: a.name, insert: a.cue,
                   tag: 'unregistered · ' + a.scenes + (a.scenes === 1 ? ' scene' : ' scenes') });
    });
    const out = items.slice(0, 8);
    if (q && !seen.has(q)) {
      out.push({ kind: 'new', label: 'Use “' + q + '”', insert: q, tag: 'not registered' });
    }
    return out;
  }

  // Which line the caret is on, in a textarea's value: the arrow keys leave a
  // block only from its first or last line.
  function caretEdges(value, start, end) {
    return {
      onFirstLine: value.lastIndexOf('\n', start - 1) === -1 || start === 0,
      onLastLine: value.indexOf('\n', end) === -1,
      atStart: start === 0 && end === 0,
      atEnd: start === value.length && end === value.length,
    };
  }

  // The preview the scene panel card shows: the first words of the action, not the heading.
  function previewLines(content, n) {
    const lines = String(content || '').split('\n').map(s => s.trim()).filter(Boolean);
    if (lines.length && /^(\.[^.]|int|ext|est|i\/e)/i.test(lines[0])) lines.shift();
    return lines.slice(0, n || 2).join(' ');
  }

  return {
    NEXT_ON_ENTER, TAB_TYPE, ELEMENTS, GUTTER, SINGLE_LINE, INT_EXT, TIMES,
    normalizeText, wrapParenthetical, insertAfter, convert, removeAt, splitAt,
    onEnter, snapshot, composeHeading, saveBlocker, acItems, caretEdges, previewLines,
  };
})();
