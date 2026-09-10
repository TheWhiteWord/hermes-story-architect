# Task 11: Extended View Panels — Sections Integration

## Goal
Render actual note sections (Personality, Background, etc.) in the four entity detail panels, fix plot setups/payoffs `[object Object]`, and rename misleading labels.

## Architecture Decision
- **Index.yaml stays untouched** — it's a summary graph, not a content dump.
- Section content is injected at dashboard generation time: `story_dashboard.py` reads notes → extracts sections via `section_parser` → injects as `window.__SECTIONS__` → panels render on open.
- One shared JS helper (`renderSectionsHtml`) for all four entity types — no duplication.

---

## Task 1: Backend — Inject section content into dashboard

### Verification
- [ ] `tools/story_dashboard.py` `handler()` already reads `index_path` and injects `window.__STORY_DATA__` — confirm injection pattern.
- [ ] `core/section_parser.py` has `list_sections(body)` and `get_section(body, section)` — these are the right tools.
- [ ] `core/constants.py` has `ENTITY_FOLDERS` mapping entity types to folder names — use for path resolution.
- [ ] `tools/story_retrieve.py` already does exactly this: reads note → extracts sections. Check if we can reuse its logic or just inline the equivalent.
- [ ] Assumption: notes are at `project_path / ENTITY_FOLDERS[entity_type] / f"{slug}.md"`. Verify against `story_resolve.py` and `story_retrieve.py`.
- [ ] Assumption: `frontmatter.load()` is already imported/available in `story_dashboard.py`. Check imports.

### Execution
1. In `tools/story_dashboard.py` `handler()`, after loading `yaml_data`:
   - Build a dict: `{entity_type: {slug: {section_name: section_content}}}`
   - For each entity in `characters`, `locations`, `worlds`, `plots`:
     - Resolve note path using `ENTITY_FOLDERS`
     - Read file, extract sections via `get_section(body, name)` for each section in `entity.sections`
     - Store in dict
   - Inject as `window.__SECTIONS__ = {json.dumps(sections_dict)}` alongside `window.__STORY_DATA__`

### Gate
- [ ] Dashboard HTML loads with `window.__SECTIONS__` populated (check via browser console or temp file inspection)
- [ ] No errors in Python execution when notes are missing (graceful skip)

---

## Task 2: Shared JS helper — `renderSectionsHtml()`

### Verification
- [ ] Check existing panel renderers (`showCharacterPanel`, `showLocationPanel`, etc.) for any existing section rendering — there is none currently.
- [ ] Check if `window.__SECTIONS__` structure is accessible in panel scope (it's global, so yes).
- [ ] Assumption: section content is plain text with `## Heading\nbody` format from `get_section()`. Verify output format.

### Execution
1. Add one function in `story-dashboard.html`:
   ```javascript
   function renderSectionsHtml(entityType, slug) {
     const data = (window.__SECTIONS__ && window.__SECTIONS__[entityType] && window.__SECTIONS__[entityType][slug]);
     if (!data) return '';
     return Object.entries(data).map(([name, content]) => `
       <div>
         <div class="panel-section-title">${name}</div>
         <div class="panel-text">${content.replace(/\n/g, '<br>')}</div>
       </div>
     `).join('');
   }
   ```

### Gate
- [ ] Function exists and returns empty string when no data
- [ ] Function renders heading + body when data present

---

## Task 3: Location panel — Rename label + render sections

### Verification
- [ ] `showLocationPanel(locId)` currently renders "Description" heading with `loc.one_sentence` — confirm at line ~2457.
- [ ] Confirm `loc.sections` exists in normalised data (it does — `entity.py` extracts it).

### Execution
1. In `showLocationPanel()`:
   - Change `<div class="panel-section-title">Description</div>` → `<div class="panel-section-title">In one sentence</div>`
   - After the scenes section, add `${renderSectionsHtml('location', loc.id)}`

### Gate
- [ ] Location panel shows "In one sentence" instead of "Description"
- [ ] Location panel renders actual note sections below

---

## Task 4: Character panel — Render sections

### Verification
- [ ] `showCharacterPanel(char)` renders `char.one_sentence` as "In one sentence" — already correct, no rename needed.
- [ ] Confirm `char.sections` exists in normalised data.

### Execution
1. In `showCharacterPanel()`:
   - After the relationships section (or at end of panel-body innerHTML), add `${renderSectionsHtml('character', char.id)}`

### Gate
- [ ] Character panel shows all note sections (Personality, Background, etc.)

---

## Task 5: Plot panel — Fix `[object Object]` + render sections

### Verification
- [ ] `renderBeats()` at line ~2497 handles `string` and `{scene, description}` object — but the `[object Object]` bug means something is still passing raw objects. Trace: `plot._setup_objs` vs `plot.setups` — the normaliser at line 1670 sets `pl._setup_objs = pl.setups` only if items are objects, but `renderBeats` receives `plot._setup_objs || plot.setups`. Check if there's a double-wrapping issue.
- [ ] Confirm: `item.scene` is a string (heading), `item.description` is a string.
- [ ] Check if `renderBeats` is called with already-rendered HTML strings anywhere (type mismatch).

### Execution
1. In `renderBeats()`:
   - Add guard: if `item` is a string, render as-is (existing).
   - If `item` is an object with `scene` property, render scene link + description (existing).
   - Add fallback: if `item` is an object without `scene` (unexpected shape), render `JSON.stringify(item)` as debug — or better, `item.description || item.scene || ''`.
2. In `showPlotPanel()`:
   - After payoffs section, add `${renderSectionsHtml('plot', plot.id)}`

### Gate
- [ ] Setups/payoffs render as clickable scene links, not `[object Object]`
- [ ] Plot panel shows note sections (Summary, Obstacles, Stakes, etc.)

---

## Task 6: World panel — Rename label + render sections

### Verification
- [ ] `showWorldPanel(worldId)` renders "Setting" heading with `world.one_sentence` — confirm at line ~2568.
- [ ] Confirm `world.sections` exists in normalised data.

### Execution
1. In `showWorldPanel()`:
   - Change `<div class="panel-section-title">Setting</div>` → `<div class="panel-section-title">In one sentence</div>`
   - After rules section, add `${renderSectionsHtml('world', world.id)}`

### Gate
- [ ] World panel shows "In one sentence" instead of "Setting"
- [ ] World panel renders note sections

---

## Task 7: CSS — Section content styling

### Verification
- [ ] `.panel-text` already exists and is used for one_sentence display — sections will reuse it.
- [ ] Check if multi-line section content needs any special handling (line-height, max-height, scroll).

### Execution
1. If section content is long, add to `.panel-text` or create `.panel-section-content`:
   ```css
   .panel-text { max-height: 200px; overflow-y: auto; }
   ```
   Only if needed — check existing `.panel-text` usage first.

### Gate
- [ ] Sections render readable, no overflow issues

---

## Dependency Chain
```
Task 1 (backend injection)
  └─ Task 2 (shared helper — needs __SECTIONS__ to exist)
       ├─ Task 3 (location panel)
       ├─ Task 4 (character panel)
       ├─ Task 5 (plot panel)
       └─ Task 6 (world panel)
            └─ Task 7 (CSS polish)
```

Each task gates on the previous: no point rendering sections in panels (3-6) if the helper (2) doesn't work, and no point having the helper if data isn't injected (1).
