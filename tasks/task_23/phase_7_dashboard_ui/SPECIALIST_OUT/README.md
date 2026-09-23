# Relationship UI — Integration Patch

Three files, ready to paste into the dashboard at the locations below. Syntax-checked with `node --check` (JS file parses clean).

| File | Contains |
|---|---|
| `relationship-ui.patch.css` | 1 new CSS rule |
| `relationship-ui.patch.js` | 9 patches — 4 new functions, 2 full function replacements, 3 inline find/replace snippets |
| `relationship-ui.patch.html` | 2 new HTML blocks |

## Apply in this order

| # | File | Where | Action |
|---|------|-------|--------|
| 1 | CSS | after `.relationship-row` styles, ~line 772 | Add `.panel-perspective` |
| 2 | JS Patch 1 | after `getRoleKey()`, ~line 2061 | Add `relTypeColor()` + `REL_TYPE_COLORS` |
| 3 | JS Patch 2 | inside `normalise()`, ~line 1932 | Replace `related` mapping |
| 4 | JS Patch 3 | inside `initStory()`, ~lines 2003-2009 | Add `buildRelationshipsView()` call |
| 5 | JS Patch 4 | `buildGraphView()`, ~lines 2064-2177 | Replace whole function |
| 6 | JS Patch 5 | `resetGraphLayout()`, ~lines 2179-2184 | Replace whole function |
| 7 | JS Patch 6 | after `showPlotPanel()`, ~line 2954 | Add `showRelationshipPanel()` |
| 8 | JS Patch 7 | after `buildPlotsView()`, ~line 2411 | Add `buildRelationshipsView()` |
| 9 | JS Patch 8 | character panel build code, ~lines 2614-2626 | Replace relationship-row rendering |
| 10 | JS Patch 9 | `loadSampleData()`, ~lines 1858-1914 | Replace/add sample relationship data |
| 11 | HTML Block 1 | after "Characters" nav button, ~line 1379 | Add "Relationships" nav button |
| 12 | HTML Block 2 | after Plots view container, ~line 1536 | Add relationships view container |

## Bugs fixed vs. the original brief

1. `rel.perspectives.forEach(...)` would have thrown — `perspectives` is an object keyed by character id, not an array. Fixed to `Object.values(r.perspectives || {}).forEach(...)` in the graph legend code, and to plain property lookup (`rel.perspectives[a]`) everywhere else.
2. `relTypeColor([types.values().next().value])` passed an array into a function that calls `.toLowerCase()` on it — would return the fallback grey every time. Fixed to pass the string directly.
3. Graph spawn-off-center bug — `network.fit()` now runs once physics stabilizes (plus a 3s fallback), in both `buildGraphView()` and `resetGraphLayout()`.

## One thing worth deciding, not a bug

Patch 8 (character panel) now reads `char.relationships` directly and no longer needs `char.related`. Patch 2 (`normalise()`) still maintains `char.related` for backward compatibility, in case anything else in the 4000-line file reads it (export, search, an older view, etc.). If nothing else in the file touches `related`, patch 2 is safe to skip entirely — worth a quick search across the full file for `.related` before deciding.

## Not covered here

These files patch the **graph, relationship panel, relationship list view, and character panel's relationship section** — the pieces named in the brief. They don't touch anything else in the 4000-line dashboard (auth, other entity types, export/import, etc.), since that wasn't part of what was shared. If any other part of the app reads the old `character.related` / single-perspective relationship shape, it'll need a matching update.
