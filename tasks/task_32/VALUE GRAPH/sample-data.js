// Sample story in the shape of the dashboard payload. For the preview and tests only.
window.DASH = window.DASH || {};
(function (D) {
  const acts = [
    { id: 'act-1', name: 'Act I', order: 1 },
    { id: 'act-2', name: 'Act II', order: 2 },
    { id: 'act-3', name: 'Act III', order: 3 },
  ];
  const sequences = [
    { id: 's-1a', name: 'The audit', order: 1, parent_id: 'act-1' },
    { id: 's-1b', name: 'First doubts', order: 2, parent_id: 'act-1' },
    { id: 's-2a', name: 'The leak', order: 1, parent_id: 'act-2' },
    { id: 's-2b', name: 'Betrayal', order: 2, parent_id: 'act-2' },
    { id: 's-3a', name: 'The hearing', order: 1, parent_id: 'act-3' },
  ];
  const seqOf = i => i < 4 ? 's-1a' : i < 8 ? 's-1b' : i < 12 ? 's-2a' : i < 16 ? 's-2b' : 's-3a';
  const actOf = i => i < 8 ? 'act-1' : i < 16 ? 'act-2' : 'act-3';
  const scenes = Array.from({ length: 20 }, (_, i) => ({
    id: 'sc' + String(i + 1).padStart(2, '0'),
    title: 'Scene ' + (i + 1),
    order: (i % 4) + 1,
    parent_id: seqOf(i), sequence_id: seqOf(i), act_id: actOf(i),
    value_turns: [],
  }));
  // payload lists scenes by id, not by story order: shuffle to prove the order is rebuilt
  const shuffled = scenes.slice().sort((a, b) => a.id < b.id ? 1 : -1);

  // turn(plot, value, from, to, [[character, level, effect], ...])
  function turn(sceneNo, plot, value, from, to, fx) {
    const byChar = {};
    (fx || []).forEach(([c, level, effect]) => { (byChar[c] = byChar[c] || []).push({ conflict_level: level, effect }); });
    scenes[sceneNo - 1].value_turns.push({
      plot, value, from, to,
      effects: Object.keys(byChar).map(c => ({ character: c, levels: byChar[c] })),
    });
  }
  // main plot, Marco
  turn(1, 'main', 'trust', 'loyalty', 'loyalty', [['marco', 'personal', 'Marco still trusts Dana completely.']]);
  turn(3, 'main', 'trust', 'loyalty', 'complicity', [['marco', 'personal', 'Marco covers for Dana.']]);
  turn(6, 'main', 'trust', 'complicity', 'complicity', [['marco', 'inner', 'He tells himself it is temporary.']]);
  turn(7, 'main', 'trust', 'complicity', 'betrayal', [['marco', 'personal', 'Dana lies to his face.'], ['marco', 'inner', 'He doubts his own judgment of people.']]);
  turn(12, 'main', 'trust', 'betrayal', 'fanatic love', [['marco', 'personal', 'He clings to Dana harder.']]);
  turn(14, 'main', 'trust', 'fanatic love', 'betrayal', [['marco', 'inner', 'The illusion breaks.'], ['marco', 'personal', 'Dana confesses.']]);
  turn(18, 'main', 'trust', 'betrayal', 'complicity', [['marco', 'inner', 'He starts to forgive.']]);
  turn(20, 'main', 'trust', 'complicity', 'loyalty', [['marco', 'personal', 'They speak honestly.'], ['marco', 'inner', 'He trusts again, knowingly.'], ['marco', 'extra-personal', 'He testifies for her.']]);
  turn(2, 'main', 'justice', 'justice', 'unfairness', [['marco', 'extra-personal', 'The audit is quietly scoped down.']]);
  turn(5, 'main', 'justice', 'unfairness', 'injustice', [['marco', 'extra-personal', 'His report is buried.']]);
  turn(9, 'main', 'justice', 'injustice', 'tyranny', [['marco', 'extra-personal', 'The board silences the press.'], ['marco', 'personal', 'He is threatened.']]);
  turn(11, 'main', 'justice', 'tyranny', 'injustice', [['marco', 'extra-personal', 'A journalist breaks the story.']]);
  turn(15, 'main', 'justice', 'injustice', 'tyranny', [['marco', 'extra-personal', 'Counter-leak discredits him.']]);
  turn(17, 'main', 'justice', 'tyranny', 'unfairness', [['marco', 'extra-personal', 'A hearing is called.'], ['marco', 'personal', 'Allies return.']]);
  turn(19, 'main', 'justice', 'unfairness', 'justice', [['marco', 'extra-personal', 'The board is censured.'], ['marco', 'inner', 'His faith in the process returns.']]);
  turn(4, 'main', 'pride', 'pride', 'vanity', [['marco', 'inner', 'He enjoys being the hero.']]);
  turn(13, 'main', 'pride', 'vanity', 'humiliation', [['marco', 'inner', 'His mistake is made public.']]);
  // subplot, Dana
  turn(3, 'sub', 'trust', 'loyalty', 'complicity', [['dana', 'inner', 'She decides to hide the file.']]);
  turn(8, 'sub', 'trust', 'complicity', 'betrayal', [['dana', 'inner', 'Guilt sets in.'], ['dana', 'personal', 'She lies to Marco.']]);
  turn(16, 'sub', 'trust', 'loyalty', 'loyalty', [['dana', 'personal', 'A flashback to their first case.']]);   // opens off the carried state: a jump
  turn(10, 'sub', 'mercy', 'mercy', 'leniency', [['dana', 'personal', 'She spares the informant.']]);
  turn(14, 'sub', 'mercy', 'leniency', 'cruelty', [['dana', 'personal', 'She turns on him.']]);
  turn(18, 'sub', 'mercy', 'cruelty', 'cruelty', [['dana', 'inner', 'She cannot stop.']]);
  turn(15, 'sub', 'mercy', 'trustless', 'cruelty', [['dana', 'personal', 'A word that is not in the schema.']]);

  const values = [
    { name: 'trust',   p: 'loyalty', c: 'complicity', cd: 'betrayal',   nn: 'fanatic love' },
    { name: 'justice', p: 'justice', c: 'unfairness', cd: 'injustice',  nn: 'tyranny' },
    { name: 'pride',   p: 'pride',   c: 'vanity',     cd: 'humiliation', nn: 'self-contempt' },
    { name: 'mercy',   p: 'mercy',   c: 'leniency',   cd: 'cruelty',    nn: 'sadism' },
  ];

  // value_focus, same rule as core/value_focus.py: count scenes, top three major (ties at the cut stay major)
  function focusOf(filter) {
    const m = new Map();
    scenes.forEach(s => s.value_turns.forEach(t => {
      if (!filter(t)) return;
      m.set(t.value, (m.get(t.value) || new Set()).add(s.id));
    }));
    const items = [...m.entries()].map(([value, set]) => ({ value, scenes: set.size })).sort((a, b) => b.scenes - a.scenes || (a.value < b.value ? -1 : 1));
    if (items.length < 3) return { major: items, minor: [] };
    const cut = items[2].scenes;
    return { major: items.filter(i => i.scenes >= cut), minor: items.filter(i => i.scenes < cut) };
  }
  const mainFocus = focusOf(t => t.plot === 'main');
  const subFocus = focusOf(t => t.plot === 'sub');
  const majorNames = new Set(mainFocus.major.map(i => i.value));
  const projectFocus = { major: mainFocus.major, minor: subFocus.major.filter(i => !majorNames.has(i.value)) };

  D.story = {
    project: { name: 'The Water Audit', act_count: 3, value_focus: projectFocus },
    acts, sequences, scenes: shuffled, values,
    characters: [{ id: 'marco', name: 'Marco' }, { id: 'dana', name: 'Dana' }],
    plots: [
      { id: 'main', name: 'The audit', plot_scope: 'main', plot_type: '', characters: ['marco'], value_focus: mainFocus },
      { id: 'sub', name: 'Dana\'s secret', plot_scope: 'subplot', plot_type: 'Resonant', characters: ['dana'], value_focus: subFocus },
    ],
  };
  // the same colour rule as colors.js, so the preview matches the app
  D.PLOT_TYPE_COLORS = { Contradictory: '#e07070', Resonant: '#7b9cf0', Complicating: '#e0a86b', Setup: '#6bbfb0' };
  D.plotColor = function (pid) {
    const pl = (D.story.plots || []).find(x => x.id === pid);
    if (!pl) return '#888';
    if (pl.plot_scope === 'main') return '#b07be0';
    return D.PLOT_TYPE_COLORS[pl.plot_type] || '#888';
  };
})(window.DASH);
