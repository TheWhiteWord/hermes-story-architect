# Phase 2 — Frontend wiring: CSS, JS, nav hook, view block

## Goal

Make the graph code loadable by the dashboard and openable from the sidebar.

## What to change

### 2.1 — Copy assets

```
value-graph.css  →  src/dashboard/css/value-graph.css
value-graph.js   →  src/dashboard/js/graph/value-graph.js
```

### 2.2 — Add to `CSS_ORDER` and `JS_ORDER`

**File**: `tools/story_dashboard.py`

```python
CSS_ORDER = ["base.css", "components.css", "views.css", "statistics.css",
             "graph.css", "value-graph.css"]          # <-- NEW

JS_ORDER = [
    "core.js", "colors.js", "utils.js", "navigation.js", "data-load.js",
    "views/scenes.js", "views/locations.js", "views/plots.js",
    "views/relationships.js", "views/worlds.js", "views/story.js",
    "panels/panel-manager.js", "panels/entity-panels.js", "panels/memory-dialog.js",
    "graph/network.js", "graph/arc-graph.js",
    "graph/value-graph.js",                             # <-- NEW
    "statistics/statistics.js", "statistics/charts.js",
    "script-view.js",
]
```

`graph/value-graph.js` goes **after** `graph/arc-graph.js` and before `statistics/` — it reads `DASH.story` at call time, not load time, so order is not critical, but keeping `graph/` files together is conventional.

### 2.3 — Add `DASH.onViewOpened` hook (replaces monkey-patching)

**File**: `src/dashboard/js/navigation.js`

Add a hook registry at the top:

```js
DASH._viewOpenedHooks = [];
DASH.onViewOpened = function(fn) { DASH._viewOpenedHooks.push(fn); };
```

Call the hooks at the end of `DASH.switchView`:

```js
DASH.switchView = function(view, btn) {
  // ... existing code ...
  DASH._viewOpenedHooks.forEach(fn => fn(view));
  DASH.closePanel();
};
```

The graph registers its callback — no wrapping, no monkey-patching:

```js
// in value-graph.js
DASH.onViewOpened(function(view) {
  if (view === 'values') D.renderValues();
});
```

### 2.4 — Normalise `values` in `core.js`

**File**: `src/dashboard/js/core.js`, in `DASH.normalise` (around line 79):

```js
d.values = d.values || [];
```

Place alongside the other defaults (`d.worlds`, `d.story_memory`, etc.).

### 2.5 — Call `buildValuesView` in `initStory`

**File**: `src/dashboard/js/core.js`, in `DASH.initStory` (around line 104):

```js
DASH.buildStoryView();
DASH.buildValuesView();       // <-- NEW
```

### 2.6 — Add sidebar button and view block

**File**: `src/dashboard/index.html`

Sidebar button — copy the markup pattern of neighbours (same `<svg class="nav-icon" viewBox="0 0 16 16" fill="none">`):

```html
<button class="nav-btn" data-view="values" onclick="DASH.switchView('values', this)">
  <svg class="nav-icon" viewBox="0 0 16 16" fill="none">
    <path d="M2 12l3-4 3 2 3-6 3 4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
  </svg>
  <span class="nav-label">Values</span>
</button>
```

View block — copy the pattern of other `.view` blocks:

```html
<div class="view" id="values-view">
  <div class="view-header">
    <div class="view-title">Values</div>
    <div class="view-subtitle" id="values-subtitle">—</div>
  </div>
  <div class="view-body" id="values-body"></div>
</div>
```

## Checklist

- [x] CSS/JS copied to correct locations
- [x] `value-graph.css` added to `CSS_ORDER`
- [x] `graph/value-graph.js` added to `JS_ORDER`
- [x] `DASH.onViewOpened` hook added to `navigation.js`
- [x] `d.values = d.values || []` in `core.js:normalise`
- [x] `DASH.buildValuesView()` in `core.js:initStory`
- [x] Sidebar button + view block in `index.html`
- [x] No `<link>` or `<script src>` tags — inlining only

## Final Brief

All 8 changes applied:

1. **`value-graph.css`** copied to `src/dashboard/css/value-graph.css`
2. **`value-graph.js`** copied to `src/dashboard/js/graph/value-graph.js`
3. **`tools/story_dashboard.py`**: `value-graph.css` added to `CSS_ORDER`; `graph/value-graph.js` added to `JS_ORDER` (after `graph/arc-graph.js`)
4. **`src/dashboard/js/navigation.js`**: Added `DASH._viewOpenedHooks` array + `DASH.onViewOpened` hook registry at top; `DASH._viewOpenedHooks.forEach(fn => fn(view))` called in `switchView` before `closePanel()`
5. **`src/dashboard/js/graph/value-graph.js`**: Replaced monkey-patch of `DASH.switchView` with `D.onViewOpened(function(view) { if (view === 'values') D.renderValues(); })`
6. **`src/dashboard/js/core.js`**: `d.values = d.values || []` in `normalise`; `DASH.story.values = DASH.story.values || []` in `initStory`
7. **`src/dashboard/js/core.js`**: `DASH.buildValuesView()` called in `initStory` after `buildStoryView()`
8. **`src/dashboard/index.html`**: Values sidebar button added (before Worlds); Values view block added (after Worlds, before Script)

Test suite: passed.
