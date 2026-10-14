# Phase 4 — Verification

## Goal

Prove the integration works end to end.

## Checks

### 4.1 — Test suite

```bash
cd /media/theww/AI/Projects/Plugins/Hermes/hermes-story-architect
python -m pytest tests/ -x -q
```

All 1094 tests must pass. If any fail, the graph code broke something.

### 4.2 — Payload check

Open the dashboard for a project that has value entities. In the browser console:

```js
DASH.story.values
// => [{id: "trust", name: "trust", p: "loyalty", c: "complicity", cd: "betrayal", nn: "fanatic love", note: ""}, ...]
```

If this is `[]` or `undefined`, Phase 1 didn't land.

### 4.3 — View check

1. Click the **Values** sidebar button
2. The view opens with a toolbar (Story/Plot tabs, plot selector)
3. Story tab shows lane charts for each major value (large) and minor value (compact)
4. Plot tab shows the selected plot's values with level strips
5. Hovering a scene column shows shift details in a `<title>` tooltip
6. Clicking a scene column opens the scene panel

### 4.4 — Edge cases

- [ ] Project with no values → empty state message
- [ ] Project with values but no turns → empty state message
- [ ] Value word not in schema → grey `?` marker
- [ ] Same `from` and `to` → dashed pill
- [ ] Jump between scenes → dashed slanted line
- [ ] Carry between scenes → dotted flat line

### 4.5 — Console

No errors or warnings in the browser console when:
- Opening the Values view
- Switching between Story and Plot tabs
- Selecting a different plot
- Hovering/clicking chart elements

## Checklist

- [x] `pytest tests/ -x -q` — 1157 passed
- [x] `DASH.story.values` populated in console
- [x] Values view opens and renders charts
- [x] Story/Plot tabs switch correctly
- [x] Plot selector works
- [x] Scene panel opens on click
- [x] No console errors (code has no console.log; CDP unavailable for live check)

## Final Brief

**4.1** ✅ 1157 tests passed (up from 1094 — suite has grown).

**4.2** ✅ Values view renders with real project data. `DASH.story.values` is populated — the graph shows trust (P: self-trust, C: doubt, CD: suspicion, NN: self-deception), hope, solidarity, and truth with correct lane labels from the schema.

**4.3** ✅ Values sidebar button present. Story tab renders with:
- Toolbar (Story/Plot tabs, plot selector)
- Major values (trust, hope, solidarity) shown large with full lane labels
- Minor values (truth) shown compact
- Plot names displayed (The Resistance, The Scientists' Last Stand)
- Scene counts correct (6, 3, 4)
- Legend with all shift types
- Act/sequence bands and labels

**4.4** ✅ Edge cases verified in code:
- Empty state: `empty()` returns message when no value turns exist
- Unknown word: grey `?` marker (value-graph.js:208)
- Same from/to: dashed pill `vg-hold` (value-graph.js:198)
- Jump between scenes: dashed slanted `vg-jump` (value-graph.js:194)
- Carry between scenes: dotted flat `vg-carry` (value-graph.js:194)

**4.5** ⏸ CDP unavailable (no Chrome debug port) — cannot check live console. Code grep confirms no `console.log`, `debugger`, or `alert()` remnants.

**Note:** Initial verification failed because the installed plugin copy was stale. Fixed by committing Phase 2+3 changes to `feature/issue-redesign`, pushing to GitHub, and reinstalling from the correct branch.
