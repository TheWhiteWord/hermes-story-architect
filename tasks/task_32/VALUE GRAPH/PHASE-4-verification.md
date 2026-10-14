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

- [ ] `pytest tests/ -x -q` — 1094 passed
- [ ] `DASH.story.values` populated in console
- [ ] Values view opens and renders charts
- [ ] Story/Plot tabs switch correctly
- [ ] Plot selector works
- [ ] Scene panel opens on click
- [ ] No console errors
