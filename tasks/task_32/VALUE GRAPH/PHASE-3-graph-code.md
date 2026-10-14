# Phase 3 — Graph code: clean integration

## Goal

Apply the four fixes to `value-graph.js` so it integrates cleanly with the codebase.

## Fixes

### 3.1 — Replace `esc()` with `DASH.escapeHtml()`

The graph defines its own HTML escaper at line 26-27:

```js
// DELETE:
const esc = s => String(s == null ? '' : s).replace(/[&<>"']/g, c => ...);
```

Every call to `esc(...)` becomes `DASH.escapeHtml(...)`. The behaviour is identical — `utils.js:17` does the same thing.

### 3.2 — Replace monkey-patched `switchView` with `onViewOpened`

**Delete** lines 339-345 (the `if (typeof DASH.switchView === 'function')` wrapper).

**Replace** with:

```js
DASH.onViewOpened(function(view) {
  if (view === 'values') D.renderValues();
});
```

This is the hook added in Phase 2.3. No wrapping, no fragility.

### 3.3 — Replace `Math.random()` SVG IDs with a counter

**Delete** line 251:

```js
const uid = 'vg' + Math.random().toString(36).slice(2, 8);
```

**Replace** with:

```js
let vgUid = 0;
// ... in panel():
const uid = 'vg' + (++vgUid);
```

Deterministic, no collision risk, no non-determinism in tests.

### 3.4 — Replace `\u0001` key separator with nested Map

**Delete** lines 74-93 (the `lines` Map with string keys).

**Replace** with:

```js
const lines = new Map();  // Map<plot, Map<normValue, line>>
scenes.forEach((s, i) => (s.value_turns || []).forEach(t => {
  const plotKey = t.plot;
  const valKey = norm(t.value);
  if (!lines.has(plotKey)) lines.set(plotKey, new Map());
  const byValue = lines.get(plotKey);
  let line = byValue.get(valKey);
  if (!line) {
    line = { key: plotKey + ':' + valKey, plot: t.plot,
             value: (schemas.get(valKey) || {}).name || t.value, turns: [] };
    byValue.set(valKey, line);
  }
  // ... rest unchanged ...
}));

// At return, flatten:
const allLines = [];
lines.forEach(byValue => byValue.forEach(line => allLines.push(line)));
return { ..., lines: allLines, ... };
```

No magic separator character. Plot and value are separate Map keys.

## What the graph draws (unchanged from the plan)

- **Lanes** top-to-bottom: P, C, CD, NN — the ladder's own order.
- **A shift** is a vertical span in its scene's column: ring at `from`, dot at `to`. Colour is the plot's.
- **Same state** (`from` equals `to`) is a dashed pill.
- **Between scenes**: dotted flat line = carried on; dashed slanted = jump.
- **Story order** rebuilt from act → sequence → scene.
- **Hover** for shift details; **click** opens scene panel.
- **Plot view**: strip of three rows (inner, personal, extra-personal) with marks.
- **Unknown word** shows as grey `?`.

## Checklist

- [x] `esc()` → `DASH.escapeHtml()` throughout
- [x] Monkey-patch removed; `DASH.onViewOpened` used instead
- [x] `Math.random()` → counter
- [x] `\u0001` separator → nested Map
- [x] Graph code has no `console.log` or debug remnants
- [x] All functions prefixed with `DASH.` (no globals leaked except `DASH`)

## Final Brief

All 4 fixes applied to `src/dashboard/js/graph/value-graph.js`:

1. **`esc()` → `DASH.escapeHtml()`** — Removed the local `esc()` helper (lines 26-27). All 12 call sites now use `DASH.escapeHtml()`. To make this safe, `DASH.escapeHtml` in `src/dashboard/js/utils.js` was extended to also escape `"` and `'` (matching the original local behaviour). All 42 existing callers of `DASH.escapeHtml` were verified — the extended escaping is strictly safer and renders identically in text content.

2. **Monkey-patch removed** — Already done in Phase 2 (replaced with `D.onViewOpened`). No change needed.

3. **`Math.random()` → counter** — Added `let vgUid = 0` at module scope. `panel()` now uses `'vg' + (++vgUid)` for deterministic, collision-free SVG pattern IDs.

4. **`\u0001` separator → nested Map** — The `lines` Map now uses `Map<plot, Map<normValue, line>>` instead of string keys with a `\u0001` separator. Flattened at return time with `lines.forEach(byValue => byValue.forEach(line => allLines.push(line)))`.

Test suite: 1157 passed, 0 failures.
