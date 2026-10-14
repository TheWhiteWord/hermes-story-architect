# Value graphs: integration

Two graphs on one new **Values** view: **Story** (every major, then every minor value, all plots) and **Plot** (the values of one plot, with the conflict levels of each shift). Pure SVG, no libraries, nothing stored.

## Files

| File | Goes to |
|---|---|
| `value-graph.js` | `src/dashboard/js/graph/value-graph.js` |
| `value-graph.css` | `src/dashboard/css/value-graph.css` |
| `preview.html`, `sample-data.js` | anywhere, to see the graphs without the app (open `preview.html`; `?tab=plot&plot=sub` presets the tab and plot) |

## 1. Request for the local agent: one addition to the payload

The dashboard payload has each scene's `value_turns` and each unit's `value_focus`, but **not the value schemas**. The graph needs them to place a word (`betrayal`) on a lane (CD).

- File: `core/db.py`, `get_dashboard_data`.
- Add a top-level `values` list to `story_data`, one entry per `value` entity:

```json
"values": [ { "id": "trust", "name": "trust", "p": "loyalty", "c": "complicity", "cd": "betrayal", "nn": "fanatic love", "note": "" } ]
```

- Sketch, unverified (the loop over `ent_rows` currently has no `value` branch):

```python
values = []                      # next to characters, scenes, ...
...
elif etype == "value":
    values.append({"id": eid, "name": e[2],
                   **{k: extra.get(k, "") for k in ("p", "c", "cd", "nn", "note")}})
...
story_data = {..., "values": values}
```

- Please confirm: where the value's name is stored (column or `extra`), and the field names `p`, `c`, `cd`, `nn`.
- Already in the payload and used as is: `scenes[].value_turns` (with `effects[].levels[]`), `scenes[].sequence_id`, `sequences[].parent_id` (the act), `order` on acts, sequences and scenes, `plots[].value_focus`, `project.value_focus`.

## 2. Frontend edits

**`index.html`**

1. In `<head>`, next to the other stylesheets: `<link rel="stylesheet" href="css/value-graph.css">`
2. Scripts: add `<script src="js/graph/value-graph.js"></script>` **after `navigation.js`**. It wraps `DASH.switchView` so the charts are drawn when the view is opened (a hidden view has no width to draw into).
3. A sidebar button, copying the markup of its neighbours (use the same attributes on the `<svg>`):

```html
<button class="nav-btn" data-view="values" onclick="DASH.switchView('values', this)">
  <svg class="nav-icon" viewBox="0 0 16 16" fill="none"><path d="M2 12l3-4 3 2 3-6 3 4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
  <span class="nav-label">Values</span>
</button>
```

4. The view, next to the other `.view` blocks:

```html
<div class="view" id="values-view">
  <div class="view-header">
    <div class="view-title">Values</div>
    <div class="view-subtitle" id="values-subtitle">—</div>
  </div>
  <div class="view-body" id="values-body"></div>
</div>
```

**`js/core.js`**

```js
// in DASH.normalise, with the other defaults:
d.values = d.values || [];

// in DASH.initStory, after DASH.buildStoryView():
DASH.buildValuesView();
```

Scene clicks call `DASH.showScenePanel(id)`, which already exists.

## 3. What is drawn

- **Lanes**, top to bottom: P, C, CD, NN, the ladder's own order (distance from the ideal). The lane labels are the value's own words from its schema. NN is hatched, and its end markers are rings.
- **A shift** is a vertical span in its scene's column: small ring where it opens (`from`), dot where it ends (`to`). Colour is the plot's (`DASH.plotColor`), so it matches the chips.
- **Same state** (`from` equals `to`) is a dashed pill.
- **Between scenes:** a dotted flat line means the value carried on. A dashed slanted line means the next scene opens somewhere else (flashback, time skip, or a break), which is the "jump" fact.
- **Story order** is rebuilt from act, sequence and scene, because the payload lists scenes by id and a scene's `order` restarts in each sequence.
- **Hover** a scene column for each shift and the effect on each character. **Click** opens the scene panel.
- **Plot view:** under each value, a strip of three rows (inner, personal, extra-personal) with a mark wherever a shift touches that level.
- **A word not in the schema** shows as a grey `?`, so a stale word is visible.

## 4. Checked, and not

Checked: rendered with the sample data in headless Chromium, no console errors; tab and plot switching; click-through; the cases of no schemas and no turns.

Not checked: against the real payload, the real nav styling, and the `.view-body` layout in the app.
