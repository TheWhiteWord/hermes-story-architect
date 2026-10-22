// Track data: what the new panel tabs read. No DOM, no drawing.
//
// Reads what the dashboard payload carries:
//   DASH.story.scene_beats[]   {id, scene, driver, scene_objective, turning_point,
//                               changes:[{entity, change}],
//                               true_character:[{character, dilemma, choice_reveals}],
//                               beats:[{action:{by,surface,subtext}, reaction:{by,surface,subtext}, gap}]}
//   DASH.story.scenes[]        value_turns:[{plot, value, from, to, effects:[{character, levels:[{conflict_level, effect}]}]}]
//   DASH.story.plots[].characters   the protagonists of a plot
//
// Story order is not rebuilt here: DASH.valueModel (value-graph.js) already orders scenes by
// act, sequence and scene, and draws the bands, so the character track and the value graph
// can never disagree about where a scene sits.
//
// Mirrors the LLM-facing `view="track"` in tools/story_load.py: the same rows, with the
// scenes where nothing was recorded kept here, because a picture can show them for free.
window.DASH = window.DASH || {};

(function (D) {
  'use strict';

  const LANES = ['p', 'c', 'cd', 'nn'];               // rung 0..3: distance from the ideal
  const norm = s => String(s == null ? '' : s).trim().toLowerCase();
  const arr = x => (Array.isArray(x) ? x : []);
  const S = story => story || D.story || {};

  // The record a scene owns, or null. `scene` is the field; parent_id is what the payload
  // carries for any entity, so either finds it.
  D.sceneBeatsOf = function (sceneId, story) {
    return arr(S(story).scene_beats).find(sb => String(sb.scene || sb.parent_id) === String(sceneId)) || null;
  };

  // Who or what an id names, with the colour the dashboard already gives that kind of entity:
  // characters by role, locations teal, worlds amber, relationships by their type.
  D.entityRef = function (id, story) {
    const st = S(story), sid = String(id == null ? '' : id);
    let e = arr(st.characters).find(x => String(x.id) === sid);
    if (e) {
      const role = e.role || e.story_role || '';
      return { id: sid, type: 'character', name: e.name || sid, role, color: D.roleColor ? D.roleColor(role) : '#8a8a8a' };
    }
    e = arr(st.locations).find(x => String(x.id) === sid);
    if (e) return { id: sid, type: 'location', name: e.name || sid, color: '#6bbfb0' };
    e = arr(st.worlds).find(x => String(x.id) === sid);
    if (e) return { id: sid, type: 'world', name: e.name || sid, color: '#e0a86b' };
    e = arr(st.relationships).find(x => String(x.id) === sid);
    if (e) {
      const first = Object.values(e.perspectives || {})[0] || {};
      return { id: sid, type: 'relationship', name: e.name || sid, color: D.relTypeColor ? D.relTypeColor(first.type) : '#8a8a8a' };
    }
    return { id: sid, type: 'unknown', name: sid, color: '#8a8a8a' };
  };

  // The rung of a word on a value's ladder (0 positive .. 3 negation of the negation), or null.
  function rungFinder(model) {
    return (value, word) => {
      const sc = model.schemas.get(norm(value)), w = norm(word);
      if (!sc || !w) return null;
      for (let r = 0; r < 4; r++) if (norm(sc[LANES[r]]) === w) return r;
      return norm(sc.name) === w ? 0 : null;           // a value's own name is its positive word
    };
  }

  // One character across the story, in story order.
  //
  //   rows       one per scene where the character appears or has anything recorded
  //   coverage   how much of that is actually written down (the picture must not look
  //              complete when it is not)
  //   paths      per (plot, value): the states the character is carried through
  //   protagonist  true when a plot names them, or a value turn reaches them: only then do
  //              conflict levels and value paths exist
  D.characterTrack = function (charId, story) {
    const st = S(story), id = String(charId);
    if (!D.valueModel) return null;
    const model = D.valueModel(st);
    const rungOf = rungFinder(model);
    const sbByScene = new Map(arr(st.scene_beats).map(sb => [String(sb.scene || sb.parent_id), sb]));
    const plotsOf = arr(st.plots).filter(p => arr(p.characters).map(String).includes(id)).map(p => p.id);

    const rows = [];
    model.scenes.forEach((s, i) => {
      const sb = sbByScene.get(String(s.id)) || null;
      const inCast = arr(s.characters).map(String).includes(id);
      const drives = !!sb && String(sb.driver) === id;
      const beats = sb ? arr(sb.beats) : [];
      const acted = beats.filter(b => b && b.action && String(b.action.by) === id).length;
      const answered = beats.filter(b => b && b.reaction && String(b.reaction.by) === id).length;
      const changes = sb ? arr(sb.changes).filter(c => c && String(c.entity) === id).map(c => c.change).filter(Boolean) : [];
      const choices = sb ? arr(sb.true_character).filter(t => t && String(t.character) === id) : [];
      const turns = [];
      arr(s.value_turns).forEach(t => arr(t.effects).forEach(e => {
        if (String(e.character) !== id) return;
        const levels = {};
        arr(e.levels).forEach(l => { if (l && l.conflict_level) levels[l.conflict_level] = l.effect || ''; });
        turns.push({
          plot: t.plot, value: t.value, from: t.from, to: t.to,
          fromRung: rungOf(t.value, t.from), toRung: rungOf(t.value, t.to), levels,
        });
      }));
      if (!(inCast || acted || answered || drives || changes.length || choices.length || turns.length)) return;
      rows.push({
        i, id: s.id, title: s.title || s.name || s.id, number: i + 1, status: s.status || '',
        inCast, drives, objective: drives ? (sb.scene_objective || '') : '',
        change: changes.join(' '), choices, acted, answered, turns,
        hasBeats: !!sb, milestone: arr(s.milestone),
      });
    });

    // value paths: every turn of one value under one plot, in story order
    const byKey = new Map();
    rows.forEach(r => r.turns.forEach(t => {
      const key = t.plot + '\u0000' + norm(t.value);
      if (!byKey.has(key)) byKey.set(key, { plot: t.plot, value: (model.schemas.get(norm(t.value)) || {}).name || t.value, steps: [] });
      byKey.get(key).steps.push({ i: r.i, from: t.from, to: t.to, fromRung: t.fromRung, toRung: t.toRung });
    }));
    const paths = [...byKey.values()].map(p => {
      const rungs = [];
      p.steps.forEach(s => { if (s.fromRung != null) rungs.push(s.fromRung); if (s.toRung != null) rungs.push(s.toRung); });
      return Object.assign(p, {
        first: p.steps[0].from, last: p.steps[p.steps.length - 1].to,
        deepest: rungs.length ? Math.max.apply(null, rungs) : null,
      });
    });

    const coverage = {
      appears: rows.length,
      withBeats: rows.filter(r => r.hasBeats).length,
      drives: rows.filter(r => r.drives).length,
      changes: rows.filter(r => r.change).length,
      choices: rows.reduce((n, r) => n + r.choices.length, 0),
      effects: rows.filter(r => r.turns.length).length,
    };
    return {
      id, model, rows, paths, coverage, plots: plotsOf,
      protagonist: plotsOf.length > 0 || paths.length > 0,
    };
  };

  // Where a row sits in the structure, from the bands the model already holds.
  D.trackPlace = function (model, i) {
    const band = list => list.find(b => i >= b.start && i <= b.end) || null;
    return { act: band(model.acts), seq: band(model.seqs) };
  };
})(window.DASH);
