# Value graphs: integration plan

Two graphs on one new **Values** view: **Story** (every major, then every minor value, all plots) and **Plot** (the values of one plot, with the conflict levels of each shift). Pure SVG, no libraries, nothing stored.

## Files

| File | Goes to |
|---|---|
| `value-graph.css` | `src/dashboard/css/value-graph.css` |
| `value-graph.js` | `src/dashboard/js/graph/value-graph.js` |
| `preview.html`, `sample-data.js` | stay in `tasks/task_32/VALUE GRAPH/` for standalone preview |

## What the dashboard loader actually does

`tools/story_dashboard.py` does **not** serve `<link>` or `<script src>` tags. It inlines:

- `CSS_ORDER` (line 8) — CSS filenames concatenated into `<!-- CSS_PLACEHOLDER -->`
- `JS_ORDER` (lines 9-17) — JS file paths concatenated into `<!-- JS_PLACEHOLDER -->`

So the integration is: copy the file, add its name to the order list. No HTML `<link>`/`<script>` edits.

## Key dependencies (all already exist)

| Dependency | Location | Status |
|---|---|---|
| `DASH.plotColor(pid)` | `js/colors.js:46` | ✅ exists |
| `DASH.escapeHtml(s)` | `js/utils.js:17` | ✅ exists |
| `DASH.showScenePanel(id)` | `js/panels/entity-panels.js:390` | ✅ exists |
| `scenes[].value_turns` | `core/db.py:1103` | ✅ in payload |
| `plots[].value_focus` | `core/db.py:1393` | ✅ in payload |
| `project.value_focus` | `core/db.py:1389` | ✅ in payload |
| value schemas (`p,c,cd,nn,note`) | `core/constants.py:303-316` | ✅ in DB |

**Missing**: `values` array in the payload. The graph needs it to place a word (`betrayal`) on a lane (CD).

## Fixes applied to the graph code

| Issue | Fix |
|---|---|
| `esc()` reinvents `DASH.escapeHtml` | Use `DASH.escapeHtml()` throughout |
| Monkey-patches `DASH.switchView` | Add `DASH.onViewOpened` hook in `navigation.js`; graph registers a callback |
| `Math.random()` for SVG pattern IDs | Simple counter (`let vgUid = 0`) |
| `\u0001` string key separator | Nested `Map` keyed by `plot`, then by `value` |

## Phases

| Phase | File | What |
|---|---|---|
| 1 | [PHASE-1-backend.md](PHASE-1-backend.md) | Add `values` to `core/db.py:get_dashboard_data` |
| 2 | [PHASE-2-frontend-wiring.md](PHASE-2-frontend-wiring.md) | CSS/JS order, normalise, nav hook, index.html |
| 3 | [PHASE-3-graph-code.md](PHASE-3-graph-code.md) | Clean graph JS with all fixes applied |
| 4 | [PHASE-4-verification.md](PHASE-4-verification.md) | Test suite + live dashboard check |
