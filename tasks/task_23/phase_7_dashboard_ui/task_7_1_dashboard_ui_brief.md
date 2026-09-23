# Task 7.1: Dashboard UI Brief for Relationship Refactor

## Goal
Produce a complete brief for a UI specialist agent to update the dashboard's relationship visualization. The brief provides everything needed: current UI context, new data structures, specific changes, and drop-in code replacements.

## Deliverable
A self-contained document the UI specialist can work from without reading the codebase.

---

## Part 1: Current Dashboard Context

### Technology Stack
- Single-file HTML dashboard: `src/dashboard/story-dashboard.html`
- vis-network (CDN) for the network graph
- D3.js (CDN) for statistics charts
- js-yaml (CDN) for sample data loading
- No build step — plain HTML/CSS/JS injected with `window.__STORY_DATA__`

### CSS Design System (relevant tokens)
```
--foreground: #e8e8e8 (main text)
--muted-foreground: #8a8a8a (secondary text)
--accent: #7b9cf0 (highlight/interactive)
--border: rgba(255,255,255,0.1)
--card: rgba(255,255,255,0.04)
--panel-bg: #181818 (opaque panel background)
--radius: 6px
--gap: 12px
--font-size-xs: 10px, sm: 11px, base: 13px, lg: 15px
```

### Existing Relationship UI

**Network Graph** (`buildGraphView`, line ~2064):
- Characters are nodes (circles with labels)
- Edges come from `c.related` array on each character
- Old data shape: `{ id: "mara", label: "Partner", feeling: "Wary respect" }`
- Each relationship creates ONE edge from `char.id` → `rel.id`
- Edge label shows `rel.label`
- Multiple relationships between same pair: vis-network renders parallel curves
- Dedup: `[from, to].sort()` was used to collapse bidirectional edges

**Character Panel** (`showCharacterPanel`, line ~2599):
- Shows character details in right-side panel
- Relationship section iterates `char.related` (mapped from `char.relationships` by normalizer)
- Each row: clickable name (navigates to that character) + label + feeling text
- CSS class: `.relationship-row` with `.relationship-name`, `.relationship-label`, `.relationship-feeling`

**Normalizer** (line ~1925):
- Maps backend schema → internal rendering schema
- Key mapping: `character.relationships[]` → `character.related[]` (with `{id, label, feeling}` shape)
- Also maps: `story_role` → `role`, `goals.short/long` → flat fields

**Sample Data** (line ~1858):
- `loadSampleData()` provides hardcoded story for preview
- Uses old `relationships: [{id, label, feeling}]` format on characters

### Sidebar Navigation
Current tabs: Story, Characters, Scenes, Locations, Plots, Worlds, Script
Plan: Add "Relationships" tab between Characters and Plots.

### Existing Panel System
- Right-side `#detail-panel` with `.panel-header`, `.panel-body`, `.panel-footer`
- Panel sections use `.panel-section-title` (uppercase, letter-spaced)
- Entity links: `.entity-link` class for clickable cross-references
- Tags: `.tag` class with variants (`.tag-scene`, `.tag-location`, etc.)
- Status badges: `.status-badge.active`, `.status-badge.building`

### Interaction Patterns
- Click character card → `showCharacterPanel(char)` opens panel
- Click entity-link in panel → navigates to that entity's panel
- Graph nodes clickable → opens character panel
- `data-hermes-send` attribute on buttons → sends prompt to Hermes
- `btn-hermes` style for Hermes action buttons

---

## Part 2: New Data Structure

### Change Summary
Relationships move from being embedded in character files to **first-class entities** with their own type, schema, and storage. Characters get a **computed** `relationships` summary derived from these entities.

### New: `relationship` Entity Type
```json
{
  "id": "kael-mira",
  "name": "Kael & Mira",
  "type": "relationship",
  "characters": ["kael", "mira"],
  "perspectives": {
    "kael": {
      "label": "Closest friend",
      "feeling": "Trusts her feelings more than their own logic",
      "type": "family",
      "strength": 0.9,
      "secret": false
    },
    "mira": {
      "label": "Friend, anchor",
      "feeling": "Understands his silences",
      "type": "romantic",
      "strength": 0.7,
      "secret": true
    }
  },
  "scenes": ["central-room-day", "central-room-night"],
  "status": "active",
  "history": ""
}
```

### New: Computed Summary on Characters
```json
{
  "id": "kael",
  "name": "Kael",
  "relationships": [
    { "with": "mira", "label": "Closest friend", "type": "family", "strength": 0.9 },
    { "with": "the-administrator", "label": "Antagonist", "type": "rival", "strength": -0.3 }
  ]
}
```

**Key difference**: Old format had `id` (character slug). New format has `with` (character slug). New format adds `type` and `strength`, removes `feeling` (feeling is now in the full entity's perspectives).

### New: Top-level `relationships` Array in `story_data`
```json
{
  "story_data": {
    "characters": [...],
    "relationships": [
      { "id": "kael-mira", "name": "Kael & Mira", "characters": ["kael", "mira"], "perspectives": {...}, "scenes": [...], "status": "active" }
    ],
    "scenes": [...],
    "plots": [...]
  }
}
```

**Note**: `relationships` is now a top-level array in `story_data`, NOT embedded in each character.

---

## Part 3: Required UI Changes

### 3.1 Network Graph — Read from `story.relationships`

**Current** (`buildGraphView`, line ~2064):
```javascript
// OLD: iterates characters, reads c.related
(c.related || []).forEach(rel => {
    edges.push({ from: c.id, to: rel.id, label: rel.label, ... });
});
```

**New**: Iterate `story.relationships` instead:
```javascript
// NEW: iterate relationship entities
(story.relationships || []).forEach(rel => {
    const [a, b] = rel.characters;
    const pa = rel.perspectives[a];
    const pb = rel.perspectives[b];

    // Edge a → b with a's perspective
    edges.push({
        from: a, to: b,
        label: pa?.label || '',
        color: relTypeColor(pa?.type),
        width: 1 + (pa?.strength || 0) * 2,
        dashes: pa?.secret || false,
    });

    // Edge b → a with b's perspective (if asymmetric)
    if (pb && (pb.label !== pa?.label || pb.feeling !== pa?.feeling)) {
        edges.push({
            from: b, to: a,
            label: pb.label || '',
            color: relTypeColor(pb.type),
            width: 1 + (pb.strength || 0) * 2,
            dashes: pb.secret || false,
        });
    }
});
```

**Edge styling by type** (suggested color mapping):
```
ally: #6bbfb0 (teal)
enemy: #e07070 (red)
family: #7b9cf0 (blue)
romantic: #e06b9b (pink)
professional: #e0a86b (orange)
mentor: #b07be0 (purple)
rival: #e0a86b (orange)
custom: #8a8a8a (gray)
```

**Edge thickness**: `1 + (strength + 1) * 2` (strength is -1.0 to 1.0, so thickness ranges 1-5)

**Multiple edges between same pair**: vis-network renders parallel curves automatically.

### 3.2 Character Panel — Use Computed Summary

**Current** (line ~2614):
```javascript
const rels = (char.related || []).map(rel => {
    const c = story.characters.find(x => x.id === rel.id);
    const nameBtn = c
        ? `<button class="relationship-name entity-link" onclick="showCharacterPanel(story.characters.find(x=>x.id==='${c.id}'))">${c.name}</button>`
        : `<span class="relationship-name">${rel.id}</span>`;
    return `
      <div class="relationship-row">
        ${nameBtn}
        ${rel.label ? `<span class="relationship-label">${rel.label}</span>` : ''}
        ${rel.feeling ? `<span class="relationship-feeling">— ${rel.feeling}</span>` : ''}
      </div>`;
});
```

**New**:
```javascript
const rels = (char.relationships || []).map(rel => {
    const c = story.characters.find(x => x.id === rel.with);
    const nameBtn = c
        ? `<button class="relationship-name entity-link" onclick="showCharacterPanel(story.characters.find(x=>x.id==='${c.id}'))">${c.name}</button>`
        : `<span class="relationship-name">${rel.with}</span>`;
    const secretIcon = rel.secret ? ' 🔒' : '';
    const typeTag = rel.type ? `<span class="tag" style="background:${relTypeColor(rel.type)}22;color:${relTypeColor(rel.type)}">${rel.type}</span>` : '';
    return `
      <div class="relationship-row">
        ${nameBtn}${secretIcon}
        ${rel.label ? `<span class="relationship-label">${rel.label}</span>` : ''}
        ${typeTag}
        ${rel.strength !== undefined ? `<span class="relationship-feeling">strength: ${rel.strength > 0 ? '+' : ''}${rel.strength}</span>` : ''}
      </div>`;
});
```

### 3.3 New: Relationship Panel

Clicking a relationship (edge or list item) should open a panel showing:
- Relationship name as title
- Both characters as entity links
- Both perspectives side-by-side:
  - Character A → B: label, feeling, type, strength, secret indicator
  - Character B → A: label, feeling, type, strength, secret indicator
- Scenes list (clickable entity links)
- Status badge
- Edit button (calls `story_edit` with `entity_type="relationship"`)

**Panel structure** (follows existing `.panel-*` CSS):
```html
<div class="panel-header">
  <div class="panel-title-block">
    <div class="panel-entity-type">Relationship</div>
    <div class="panel-name">Kael & Mira</div>
  </div>
  <button class="panel-close">✕</button>
</div>
<div class="panel-body">
  <div class="panel-section-title">Characters</div>
  <!-- entity links to both characters -->
  
  <div class="panel-section-title">Perspectives</div>
  <!-- two-column: A→B | B→A -->
  
  <div class="panel-section-title">Scenes</div>
  <!-- scene entity links -->
  
  <div class="panel-section-title">Status</div>
  <!-- status badge -->
</div>
```

### 3.4 New: Relationships Sidebar Tab

Add between "Characters" and "Plots":
```html
<button class="nav-btn" data-view="relationships" onclick="switchView('relationships', this)">
  <svg class="nav-icon">...</svg>
  <span class="nav-label">Relationships</span>
</button>
```

New view:
```html
<div class="view entity-list-view" id="relationships-view">
  <div class="view-header">
    <div class="view-title">Relationships</div>
    <div class="view-subtitle" id="relationships-subtitle">—</div>
  </div>
  <div class="view-body">
    <div class="entity-grid" id="relationship-list"></div>
  </div>
</div>
```

Each relationship card shows: name, both characters, type badges, status, strength indicator.

### 3.5 Normalizer Updates

**Current** (line ~1932):
```javascript
if (c.relationships && !c.related) {
    c.related = c.relationships.map(r => ({ id: r.id, label: r.label, feeling: r.feeling }));
}
```

**New**: The normalizer should handle BOTH old and new format:
```javascript
// New format: { with, label, type, strength }
if (c.relationships && !c.related) {
    c.related = c.relationships.map(r => ({
        id: r.with || r.id,
        label: r.label,
        feeling: '',  // feeling moved to perspectives in full entity
    }));
}
```

Also update `loadSampleData()` (line ~1858) to use new format:
```javascript
// OLD:
relationships: [{ id: "mara", feeling: "Wary respect", label: "Partner" }]
// NEW:
relationships: [{ with: "mara", label: "Partner", type: "ally", strength: 0.5 }]
```

### 3.6 Remove Old Graph Dedup

**Current** (line ~2094): `[from, to].sort()` collapses bidirectional edges.

**New**: Remove this — each relationship entity produces its own directed edge(s). Multiple edges between same pair are valid (same pair, multiple relationships).

---

## Part 4: Drop-In Replacements

### Replacement 1: `buildGraphView` edge construction
**Location**: Inside `buildGraphView()` function
**Replace**: The `(c.related || []).forEach(...)` loop
**With**: New iteration over `story.relationships` as shown in 3.1

### Replacement 2: Character panel relationship section
**Location**: Inside `showCharacterPanel()` function
**Replace**: `(char.related || []).map(rel => { ... })` block
**With**: New iteration over `char.relationships` as shown in 3.2

### Replacement 3: Normalizer relationship mapping
**Location**: `normalise()` function
**Replace**: `if (c.relationships && !c.related) { ... }` block
**With**: Updated mapping as shown in 3.5

### Replacement 4: `loadSampleData()` sample characters
**Location**: `loadSampleData()` function
**Replace**: `relationships: [{ id: "mara", feeling: "...", label: "Partner" }]` entries
**With**: `relationships: [{ with: "mara", label: "Partner", type: "ally", strength: 0.5 }]` entries

### Replacement 5: Add sidebar button
**Location**: In `<nav id="sidebar">`, after the Characters button
**Add**: Relationships nav button as shown in 3.4

### Replacement 6: Add relationships view
**Location**: In `<main id="main">`, after the graph view
**Add**: Relationships view div as shown in 3.4

---

## Part 5: Design Notes & Freedom

### What the UI specialist should feel free to improve:
- **Edge rendering**: Current graph uses simple arrows. Consider curved edges for bidirectional relationships, or color-coded edges by type.
- **Relationship type icons**: Instead of text badges, consider icons (⚔️ enemy, ❤️ romantic, 👪 family, 🤝 ally, etc.)
- **Strength visualization**: Current plan uses edge thickness. Could also use opacity or a dedicated strength bar in the relationship panel.
- **Secret indicator**: Currently just 🔒. Could use dashed edges + a "secret" badge in the panel.
- **Relationship card design**: Current entity cards are simple. Could show a mini graph of the relationship (two nodes + edge).
- **Filtering**: Relationships view could filter by type, status, or character.
- **Graph legend**: Add a legend for edge colors/thickness.

### What should NOT change:
- Overall layout structure (sidebar + main + detail panel)
- CSS design tokens (colors, spacing, typography)
- Panel system (header/body/footer pattern)
- Entity link navigation pattern
- Hermes integration (`data-hermes-send` attribute)

### Constraints:
- Must work with vis-network's existing API
- Must handle missing/undefined fields gracefully (strength, secret, type are optional)
- Must maintain backward compatibility with old data format during transition
- Dashboard is a single HTML file — no external dependencies beyond CDN scripts already included

---

## Part 6: File Locations

| File | Lines | Purpose |
|------|-------|---------|
| `src/dashboard/story-dashboard.html` | ~762-772 | `.relationship-row` CSS classes |
| `src/dashboard/story-dashboard.html` | ~1858-1913 | `loadSampleData()` sample data |
| `src/dashboard/story-dashboard.html` | ~1925-1989 | `normalise()` function |
| `src/dashboard/story-dashboard.html` | ~2064-2100 | `buildGraphView()` function |
| `src/dashboard/story-dashboard.html` | ~2599-2630 | `showCharacterPanel()` function |
| `src/dashboard/story-dashboard.html` | ~1356-1444 | Sidebar navigation HTML |
| `src/dashboard/story-dashboard.html` | ~1459-1537 | View containers HTML |

---

## Checklist for UI Specialist
- [ ] Network graph reads from `story.relationships` (not `c.related`)
- [ ] Edge colors by relationship type
- [ ] Edge thickness by strength
- [ ] Dashed edges for secret perspectives
- [ ] Bidirectional edges when perspectives differ
- [ ] Character panel shows new computed summary format
- [ ] Secret indicator (🔒) on relationships
- [ ] Type badges/tags on relationships
- [ ] Strength display (numeric or visual)
- [ ] New relationship panel with side-by-side perspectives
- [ ] Relationships sidebar tab added
- [ ] Relationships list view with cards
- [ ] Normalizer handles both old and new format
- [ ] Sample data updated to new format
- [ ] Old `[from, to].sort()` dedup removed
- [ ] Dashboard renders without errors
- [ ] Manual testing with sample data

## Verification for Backend
```bash
cd /media/theww/AI/Projects/Plugins/Hermes/hermes-story-architect
python -c "
from core.db import get_dashboard_data
from pathlib import Path
data = get_dashboard_data(Path('tests/fixtures/save-the-children'))
rels = data.get('story_data', {}).get('relationships', [])
print(f'Relationships in story_data: {len(rels)}')
for r in rels[:3]:
    print(f'  {r[\"id\"]}: {r[\"characters\"]} status={r[\"status\"]}')
chars = data.get('story_data', {}).get('characters', [])
for c in chars[:2]:
    rel_summary = c.get('relationships', [])
    print(f'  {c[\"id\"]} computed summary: {rel_summary}')
"
```
