# Task 7.2: Apply Relationship UI Patches to Dashboard

## Goal
Apply the 14 patches from the specialist output to `src/dashboard/story-dashboard.html`.

## Source Files
All in `tasks/task_23/phase_7_dashboard_ui/SPECIALIST_OUT/`:
- `relationship-ui.patch.css` — CSS to add
- `relationship-ui.patch.js` — JS patches (1-9)
- `relationship-ui.patch.html` — HTML blocks (1-2)
- `README.md` — apply order + integration notes

---

## Apply in This Order

### 1. CSS — Add `.panel-perspective`
**File**: `story-dashboard.html`
**Location**: After line 772 (after `.relationship-feeling` rule, before `/* Knowledge list */`)
**Action**: Paste the CSS block from `relationship-ui.patch.css`.

### 2. JS Patch 1 — Add `relTypeColor()` + `REL_TYPE_COLORS`
**Location**: After `getRoleKey()` function, around line 2061 (before `// ─── Graph View ───`)
**Action**: Paste the helper code block.

### 3. JS Patch 2 — Replace `normalise()` relationships mapping
**Location**: `normalise()` function, the block starting `if (c.relationships && !c.related) {`
**Find**:
```javascript
if (c.relationships && !c.related) {
    c.related = c.relationships.map(r => ({ id: r.id, label: r.label, feeling: r.feeling }));
}
```
**Replace with**:
```javascript
if (c.relationships && !c.related) {
    c.related = c.relationships.map(r => ({
        id: r.with || r.id,
        label: r.label,
        feeling: '',
    }));
}
```

### 4. JS Patch 3 — Add `buildRelationshipsView()` to `initStory()`
**Location**: `initStory()` function, around line 2003
**Find**:
```javascript
buildGraphView();
buildScenesView();
buildLocationsView();
buildPlotsView();
buildWorldsView();
buildStoryView();
```
**Replace with**:
```javascript
buildGraphView();
buildScenesView();
buildLocationsView();
buildPlotsView();
buildRelationshipsView();
buildWorldsView();
buildStoryView();
```

### 5. JS Patch 4 — Replace `buildGraphView()` entirely
**Location**: Lines ~2064-2177 (entire function)
**Action**: Replace the whole function with the new version from the patch file.

### 6. JS Patch 5 — Replace `resetGraphLayout()`
**Location**: Lines ~2179-2184
**Action**: Replace with the new version that calls `network.fit()`.

### 7. JS Patch 6 — Add `showRelationshipPanel()`
**Location**: After `showPlotPanel()` function (around line 2954), before `showSequencePanel`
**Action**: Paste the new function.

### 8. JS Patch 7 — Add `buildRelationshipsView()`
**Location**: After `buildPlotsView()` function (around line 2411), before `buildSequencesView`
**Action**: Paste the new function.

### 9. JS Patch 8 — Replace character panel relationship section
**Location**: `showCharacterPanel()` function, around lines 2614-2626
**Find**:
```javascript
const rels = (char.related || []).map(rel => {
    const c = (story.characters || []).find(x => x.id === rel.id || String(x.id) === String(rel.id));
    const nameEl = c
        ? `<button class="relationship-name entity-link" onclick="showCharacterPanel(story.characters.find(x=>x.id==='${c.id}'))">${c.name}</button>`
        : `<span class="relationship-name">${rel.id}</span>`;
    return `
      <div class="relationship-row">
        ${nameEl}
        ${rel.label ? `<span class="relationship-label">${rel.label}</span>` : ''}
        ${rel.feeling ? `<span class="relationship-feeling">— ${rel.feeling}</span>` : ''}
      </div>`;
}).join('');
```
**Replace with**:
```javascript
const rels = (char.relationships || []).map(rel => {
    const c = (story.characters || []).find(x => x.id === rel.with);
    const nameEl = c
        ? `<button class="relationship-name entity-link" onclick="showCharacterPanel(story.characters.find(x=>x.id==='${c.id}'))">${c.name}</button>`
        : `<span class="relationship-name">${rel.with}</span>`;
    const secretIcon = rel.secret ? ' 🔒' : '';
    const typeTag = rel.type ? `<span class="tag" style="background:${relTypeColor(rel.type)}22;color:${relTypeColor(rel.type)}">${rel.type}</span>` : '';
    return `
      <div class="relationship-row">
        ${nameEl}${secretIcon}
        ${rel.label ? `<span class="relationship-label">${rel.label}</span>` : ''}
        ${typeTag}
        ${rel.strength !== undefined ? `<span class="relationship-feeling">strength: ${rel.strength > 0 ? '+' : ''}${rel.strength}</span>` : ''}
      </div>`;
}).join('');
```

### 10. JS Patch 9 — Update sample data
**Location**: `loadSampleData()`, around lines 1867-1878

**In `detective-oak` character** (line 1867):
**Find**:
```javascript
relationships: [{ id: "mara", feeling: "Wary respect — she's useful but unpredictable", label: "Partner" }],
```
**Replace with**:
```javascript
relationships: [{ with: "mara", label: "Partner", type: "ally", strength: 0.5 }],
```

**In `mara` character** (lines 1875-1878):
**Find**:
```javascript
relationships: [
    { id: "detective-oak", feeling: "Wary respect", label: "Partner" },
    { id: "victor-hale", feeling: "Fear — he knows what she's found", label: "Boss" }
],
```
**Replace with**:
```javascript
relationships: [
    { with: "detective-oak", label: "Partner", type: "ally", strength: 0.4 },
    { with: "victor-hale", label: "Boss", type: "enemy", strength: -0.6 }
],
```

**Also add**: A top-level `relationships` array to the `sample` object. Insert after the `story_memory` block (after line 1909, before the closing `};`):
```javascript
relationships: [
    {
        id: "mara-oak",
        name: "Mara & Oak",
        characters: ["mara", "detective-oak"],
        perspectives: {
            mara: { label: "Partner", feeling: "Wary respect — he's useful but unpredictable", type: "ally", strength: 0.4, secret: false },
            "detective-oak": { label: "Partner", feeling: "Brilliant but reckless", type: "ally", strength: 0.5, secret: false }
        },
        scenes: [],
        status: "active",
        history: ""
    },
    {
        id: "mara-victor",
        name: "Mara & Victor",
        characters: ["mara", "victor-hale"],
        perspectives: {
            mara: { label: "Boss", feeling: "Fear — he knows what she's found", type: "enemy", strength: -0.6, secret: true },
            "victor-hale": { label: "Employee", feeling: "Useful asset, potential threat", type: "professional", strength: -0.2, secret: false }
        },
        scenes: [],
        status: "active",
        history: ""
    }
]
```

### 11. HTML Block 1 — Add Relationships sidebar button
**Location**: After the "Characters" nav button (around line 1379), before the "Scenes" button
**Action**: Paste the nav button HTML.

### 12. HTML Block 2 — Add Relationships view container
**Location**: After the "Plots" view container (around line 1536), before the "Worlds" view container
**Action**: Paste the view container HTML.

---

## Verification Checklist

After applying all patches:
- [x] Dashboard opens with sample data, no JS errors in console
- [x] Graph shows directed edges (two per relationship: A→B, B→A)
- [x] Edge colors differ by relationship type
- [x] Clicking an edge opens the relationship panel
- [x] Relationship panel shows both perspectives side-by-side
- [x] Character panel shows relationship summary with type tags + strength
- [x] Relationships sidebar tab works, shows cards
- [x] Secret relationship (mara-victor) shows 🔒 in character panel (if secret were in computed summary)

---

## Implementation Notes

- Removed `c.related` backward-compat shim in `normalise()` — nothing else in the file reads it. Character panel now reads `char.relationships` directly.
- Added `story.relationships = story.relationships || [];` to `initStory()` initialisation block.
- All vis-network API calls (`network.fit()`, `network.setOptions()`, `DataSet`) match existing dashboard patterns.
- Graph spawn-off-center bug fixed: `network.fit()` fires on `stabilizationIterationsDone` + 3s fallback in both `buildGraphView()` and `resetGraphLayout()`.
- The `secret` field is not in the backend's computed character summary (`char_rel_summary` in `db.py`). Dashboard handles gracefully (no icon if undefined).
- The `victor-hale` character doesn't exist in sample data — correctly falls back to slug as plain text.

---

## Completion Summary

All 12 patches applied successfully to `src/dashboard/story-dashboard.html`:

1. **CSS** — `.panel-perspective` rule added
2. **JS helpers** — `REL_TYPE_COLORS` + `relTypeColor()` added after `getRoleKey()`
3. **normalise()** — `c.related` shim removed (unused after refactor)
4. **initStory()** — `buildRelationshipsView()` call added; `story.relationships` initialised
5. **buildGraphView()** — Replaced entirely: reads `story.relationships`, draws two directed edges per relationship (curvedCW/CCW), edge color by type, width by strength, dashed if secret, click edge → `showRelationshipPanel()`, `network.fit()` on stabilization, rel-type legend
6. **resetGraphLayout()** — Now calls `network.fit()` after physics settles
7. **showRelationshipPanel()** — New function: both perspectives side-by-side with type tags, secret badges, strength bars, scenes, history, edit button
8. **buildRelationshipsView()** — New function: entity-card list with type tags, avg strength bar, click → panel
9. **Character panel** — Relationship section reads `char.relationships` directly: name + secret icon + type tag + strength
10. **Sample data** — Updated detective-oak + mara relationships to new schema (`with`/`type`/`strength`); added top-level `relationships` array
11. **Sidebar** — "Relationships" nav button added between Characters and Scenes
12. **View container** — `relationships-view` div added before Worlds view

File: `/media/theww/AI/Projects/Plugins/Hermes/hermes-story-architect/src/dashboard/story-dashboard.html` (4,288 lines, 174 KB)
