# Phase 4 Plan: Dashboard & Frontend

**Created:** 2026-09-13
**Status:** Decisions locked — ready for implementation
**Input:** `refactor_overview.md` + `Claude_structure_refactor.md` + Phase 1-3 plans + user decisions

---

## Decisions Locked

| Topic | Decision | Rationale |
|-------|----------|-----------|
| Script view | **Always assemble from scenes** | One implementation. Screenplay import becomes a one-time call that generates scene files. |
| Scene content loading | **A — inject all at dashboard load** | Disk read for <100 scenes is ~5ms. Caching/incremental adds code for zero measurable benefit. YAGNI until 500+ scenes. |
| Structural stats | **A — server-side Python** | Consistent with existing `__SCREENPLAY_STATS__` pattern. Testable. |
| Backend assembly | **No separate assembly function — `_compute_screenplay_stats()` produces `scriptHtml`** | `_compute_screenplay_stats()` already calls `tokens_to_html()` internally. Feed it scene `## Content` concatenated in order. Zero logic duplicated, no triple-parsing. |
| Screenplay stats preservation | **Reuse `_compute_screenplay_stats()` with concatenated scene content** | All existing stats (length, duration, character speaking time, INT/EXT, location stats) come from this pure function. Feed it scene `## Content` instead of `screenplay.fountain` — zero stats logic duplicated. |
| Fallback to screenplay file | **Remove entirely** | The script IS the scene files. `screenplay.fountain` will never exist as an independent file after screenplay import is reintegrated. No fallback, no dual source, no complexity. |

---

## 1. What This Phase Does

Update the dashboard to display and interact with scenes, sequences, and acts as first-class entities. Script view always assembles from scene files. Scene content injected server-side. Structural stats computed server-side. **No fallback to `screenplay.fountain` — the script IS the scene files.**

**End state:**
- Scenes view groups by act → sequence → scene hierarchy
- Script view renders assembled scene `## Content` as Fountain HTML
- Sequence/act panels show structural metadata
- Reordering via up/down buttons
- Structural stats tab with scene status/role distribution
- All existing entity panels still work
- Client-side `formatFountainScene()` removed (replaced by server pre-rendering)
- **`screenplay.fountain` completely removed from dashboard code** — no fallback, no dual source

---

## 2. Files to Modify

| File | Lines | Change |
|------|-------|--------|
| `core/index.py` | +75 | New `assemble_scene_content()` + `compute_structural_stats()` + fix `_enrich_entity_scenes()` (no separate `assemble_script_from_scenes()` — `_compute_screenplay_stats()` produces `scriptHtml`) |
| `tools/story_dashboard.py` | +20 / -15 | Replace screenplay injection with scene-based injection (no `__ASSEMBLED_SCRIPT__` injection — uses existing `__SCREENPLAY_STATS__.scriptHtml` path) |
| `src/dashboard/story-dashboard.html` | +200 / -100 | Hierarchical scenes view, sequence/act panels, structural stats tab, remove `formatFountainScene()` + fix `showCharacterPanel()` + normalizer `id` matching + screenplay fallback |
| `tests/test_core.py` | +12 | Tests for all new functions |

---

## 3. Detailed Specifications

### 3.1 `core/index.py` — New Functions

```python
def assemble_scene_content(index: dict, project_path: Path) -> str:
    """Concatenate scene ## Content sections into a single Fountain text string.
    
    Used to feed _compute_screenplay_stats() so all existing screenplay stats
    (length, duration, character speaking time, INT/EXT, location stats)
    AND scriptHtml are produced from scene content instead of screenplay.fountain.
    
    This eliminates the need for a separate assemble_script_from_scenes() function —
    _compute_screenplay_stats() already calls tokens_to_html() internally.
    """
    from .section_parser import get_section
    
    scenes = index.get("scenes", [])
    sequences = {s["id"]: s for s in index.get("sequences", [])}
    acts = {a["id"]: a for a in index.get("acts", [])}
    
    scenes_by_seq = {}
    for scene in scenes:
        sid = scene.get("sequence_id", "")
        scenes_by_seq.setdefault(sid, []).append(scene)
    for sid in scenes_by_seq:
        scenes_by_seq[sid].sort(key=lambda s: s.get("order", 0))
    
    content_parts = []
    for act_id, act in sorted(acts.items(), key=lambda x: x[1].get("order", 0)):
        seqs_in_act = sorted(
            [s for s in index.get("sequences", []) if s.get("act_id") == act_id],
            key=lambda s: s.get("order", 0)
        )
        for seq in seqs_in_act:
            for scene in scenes_by_seq.get(seq["id"], []):
                note_path = project_path / "scenes" / f"{scene['id']}.md"
                if not note_path.exists():
                    continue
                import frontmatter
                post = frontmatter.load(note_path)
                content = get_section(post.content, "Content")
                if not content:
                    continue
                if content.startswith("## "):
                    nl = content.find("\n")
                    if nl != -1:
                        content = content[nl + 1:]
                content_parts.append(content.strip())
    
    return "\n\n".join(content_parts)
```

```python
def compute_structural_stats(index: dict) -> dict:
    """Compute structural stats for dashboard injection."""
    from collections import Counter
    
    status_counts = Counter()
    role_counts = Counter()
    for scene in index.get("scenes", []):
        status_counts[scene.get("status", "planned")] += 1
        role_counts[scene.get("dramatic_role", "") or "unset"] += 1
    
    return {
        "sceneCount": len(index.get("scenes", [])),
        "sequenceCount": len(index.get("sequences", [])),
        "actCount": len(index.get("acts", [])),
        "sceneStatus": dict(status_counts),
        "sceneRoles": dict(role_counts),
        "acts": [
            {
                "id": act["id"],
                "title": act["title"],
                "sceneCount": act.get("scene_count", 0),
                "sequenceCount": act.get("sequence_count", 0),
            }
            for act in index.get("acts", [])
        ],
    }
```

### 3.2 `tools/story_dashboard.py` — Replace Screenplay Injection

**Remove** the existing screenplay injection block (~lines 327-345):
```python
# DELETE THIS ENTIRE BLOCK:
screenplay_path = project_path / "screenplay.fountain"
if screenplay_path.exists():
    screenplay_text = screenplay_path.read_text(encoding="utf-8")
    html = html.replace(...)
    try:
        stats = _compute_screenplay_stats(screenplay_text)
        ...
```

**Replace with:**
```python
# Inject screenplay stats from scene content (reuse _compute_screenplay_stats)
# _compute_screenplay_stats() calls tokens_to_html() internally, so stats.scriptHtml
# IS the pre-rendered script HTML. No separate assemble_script_from_scenes() needed.
# Preserves ALL existing stats: length, duration, character speaking time,
# INT/EXT balance, location stats, scene barcode, title page — zero logic duplicated.
try:
    scene_text = assemble_scene_content(index, project_path)
    if scene_text:
        stats = _compute_screenplay_stats(scene_text)
        if stats:
            stats_json = json.dumps(stats)
            html = html.replace(
                "// ─── Boot ─────────────────────────────────────────────────────────────────────",
                f"window.__SCREENPLAY_STATS__ = {stats_json};\n// ─── Boot ─────────────────────────────────────────────────────────────────────",
            )
except Exception:
    pass  # Dashboard still works without stats

# Inject structural stats
try:
    structural_stats = compute_structural_stats(index)
    stats_json = json.dumps(structural_stats)
    html = html.replace(
        "// ─── Boot ─────────────────────────────────────────────────────────────────────",
        f"window.__STRUCTURAL_STATS__ = {stats_json};\n// ─── Boot ─────────────────────────────────────────────────────────────────────",
    )
except Exception:
    pass  # Dashboard still works without structural stats
```

Also update `_extract_sections()` to include scenes, sequences, acts:
```python
PLURAL_TO_SINGULAR = {
    'characters': 'character', 'locations': 'location', 
    'worlds': 'world', 'plots': 'plot',
    'scenes': 'scene', 'sequences': 'sequence', 'acts': 'act',
}
```

### 3.3 `src/dashboard/story-dashboard.html` — Changes

#### A. Remove Client-Side Fountain Formatter (~100 lines)

Delete these functions entirely:
- `formatFountainScene()` (lines 2269-2334)
- `extractFountainScene()` (lines 2340-2409)
- `loadSceneContent()` (lines 2236-2266)
- `_screenplayText`, `_screenplayLoaded` state variables

#### B. Rewrite `buildScriptView()` — Use `__SCREENPLAY_STATS__.scriptHtml`

```javascript
function buildScriptView() {
  const stats = window.__SCREENPLAY_STATS__;
  const container = document.getElementById('screenplay-container');
  if (!container) return;

  // No stats or no scriptHtml → empty state
  if (!stats || !stats.scriptHtml) {
    container.innerHTML = '<div class="script-empty"><div class="empty-state-title">No scenes with content yet</div><div class="empty-state-sub">Add content to your scenes to see the script view.</div></div>';
    _scriptBuilt = true;
    return;
  }

  const doc = document.createElement('div');
  doc.className = 'screenplay-doc screenplay-content';

  // Title page
  if (stats.titlePage) {
    const tp = stats.titlePage;
    const hasContent = Object.values(tp).some(arr => Array.isArray(arr) ? arr.length > 0 : !!arr);
    if (hasContent) {
      // ... existing title page rendering (unchanged) ...
    }
  }

  // Script body from server-rendered HTML
  const body = document.createElement('div');
  body.innerHTML = stats.scriptHtml;
  doc.appendChild(body);

  // Wire scene heading clicks
  doc.querySelectorAll('.fountain-scene_heading').forEach(el => {
    const rawHeading = el.textContent.replace(/^\d+\.\s*/, '').toUpperCase().trim()
                                     .replace(/\s*\(.*\)\s*$/, '');
    const matched = (story && story.scenes || []).find(s => {
      const h = (s.heading || '').toUpperCase().trim().replace(/\s*\(.*\)\s*$/, '');
      return h === rawHeading;
    });
    if (matched) {
      el.style.cursor = 'pointer';
      el.addEventListener('click', () => showScenePanel(matched.id));
    }
  });

  // Subtitle
  const sceneCount = (story.scenes || []).length;
  const pages = stats.lengthStats && stats.lengthStats.pagesWhole || '?';
  setEl('script-subtitle', pages + ' p · ' + sceneCount + ' scenes');

  container.innerHTML = '';
  container.appendChild(doc);
  _scriptBuilt = true;
}
```

#### C. Rewrite `buildScenesView()` — Hierarchical Grouping

```javascript
function buildScenesView() {
  const scenes = story.scenes || [];
  const sequences = story.sequences || [];
  const acts = story.acts || [];
  
  const seqMap = {};
  sequences.forEach(seq => { seqMap[seq.id] = []; });
  const unassigned = [];
  scenes.forEach(s => {
    if (s.sequence_id && seqMap[s.sequence_id]) {
      seqMap[s.sequence_id].push(s);
    } else {
      unassigned.push(s);
    }
  });
  Object.values(seqMap).forEach(arr => arr.sort((a, b) => (a.order || 0) - (b.order || 0)));
  unassigned.sort((a, b) => (a.order || 0) - (b.order || 0));

  document.getElementById('scenes-subtitle').textContent = scenes.length + ' scenes';

  const list = document.getElementById('scene-list');
  if (!scenes.length) {
    list.innerHTML = '<div class="empty-state"><div class="empty-state-title">No scenes yet</div><div class="empty-state-sub">Create scenes to see them here.</div></div>';
    return;
  }

  let html = '';
  acts.sort((a, b) => (a.order || 0) - (b.order || 0));
  for (const act of acts) {
    const actSeqs = sequences.filter(s => s.act_id === act.id).sort((a, b) => (a.order || 0) - (b.order || 0));
    html += `<div class="story-section-title" style="margin-top:12px">${escapeHtml(act.title || act.id)}</div>`;
    for (const seq of actSeqs) {
      const seqScenes = seqMap[seq.id];
      html += `<div class="scene-sequence-header" style="font-size:var(--font-size-sm);color:var(--muted-foreground);padding:6px 10px 2px;font-weight:500;">${escapeHtml(seq.title || seq.id)}</div>`;
      html += seqScenes.map(s => renderSceneItem(s)).join('');
    }
  }
  if (unassigned.length) {
    html += `<div class="story-section-title" style="margin-top:12px">Unassigned</div>`;
    html += unassigned.map(s => renderSceneItem(s)).join('');
  }

  list.innerHTML = html;
  list.querySelectorAll('.scene-item').forEach(el => {
    el.addEventListener('click', () => showScenePanel(el.dataset.id));
  });
}

function renderSceneItem(s) {
  const charTags = (s.characters || []).map(cid => {
    const c = (story.characters || []).find(x => x.id === cid || String(x.id) === String(cid));
    return c ? `<span class="tag tag-char">${escapeHtml(c.name)}</span>` : '';
  }).join('');
  const locTags = (s.locations || s.location ? [s.location] : []).map(lref => {
    const l = findLocation(lref);
    return l ? `<span class="tag tag-location">${escapeHtml(l.name)}</span>` : '';
  }).join('');
  const plotTags = (s.plots || []).map(pid => {
    const p = (story.plots || []).find(x => x.id === pid || String(x.id) === String(pid));
    return p ? `<span class="tag tag-plot">${escapeHtml(p.name)}</span>` : '';
  }).join('');
  return `
    <div class="scene-item" data-id="${s.id}">
      <div class="scene-number">${String(s.order || 0).padStart(2, '0')}</div>
      <div class="scene-body">
        <div class="scene-heading">${s.title || s.id}</div>
        ${s.heading ? `<div class="panel-muted" style="font-size:var(--font-size-xs);margin-top:2px;">${escapeHtml(s.heading)}</div>` : ''}
        <div class="scene-meta">${charTags}${locTags}${plotTags}</div>
      </div>
    </div>
  `;
}
```

#### D. Update `showScenePanel()` — Use `## Content` from `__SECTIONS__`

```javascript
function showScenePanel(sceneId) {
  const scene = (story.scenes || []).find(s => String(s.id) === String(sceneId));
  if (!scene) return;

  document.querySelectorAll('.scene-item').forEach(el => el.classList.remove('selected'));
  const sceneEl = document.querySelector(`.scene-item[data-id="${sceneId}"]`);
  if (sceneEl) sceneEl.classList.add('selected');

  document.getElementById('panel-type').textContent = 'Scene';
  document.getElementById('panel-name').textContent = scene.title || scene.id;

  // Characters, locations, plots — same as before
  const chars = (scene.characters || []).map(cid => {
    const c = (story.characters || []).find(x => x.id === cid || String(x.id) === String(cid));
    return c ? `<button class="entity-link" onclick="showCharacterPanel(story.characters.find(x=>x.id==='${c.id}'))" style="border-left:2px solid ${roleColor(c.role)}">${c.name}</button>` : '';
  }).filter(Boolean).join('');

  const locs = (scene.locations || []).map(lref => {
    const l = findLocation(lref);
    return l ? `<button class="entity-link" onclick="showLocationPanel('${l.id}')">${l.name}</button>` : '';
  }).filter(Boolean).join('');

  const plotRefs = (scene.plots || []);
  const plots = plotRefs.map(pid => {
    const pl = (story.plots || []).find(x => x.id === pid || String(x.id) === String(pid));
    return pl ? `<button class="entity-link tag-plot" onclick="showPlotPanel('${pl.id}')">${pl.name}</button>` : '';
  }).filter(Boolean).join('');

  // Content from __SECTIONS__.scenes[slug]["Content"]
  let contentHtml = '';
  const sections = window.__SECTIONS__;
  const sceneContent = sections?.scenes?.[sceneId]?.Content;
  if (sceneContent) {
    contentHtml = `<div class="fountain-content">${escapeHtml(sceneContent)}</div>`;
  } else {
    contentHtml = '<div class="panel-muted">No content yet.</div>';
  }

  document.getElementById('panel-body').innerHTML = `
    ${chars ? `<div><div class="panel-section-title">Characters</div><div style="display:flex;flex-direction:column;gap:4px;">${chars}</div></div>` : ''}
    ${locs ? `<div><div class="panel-section-title">Location</div><div style="display:flex;flex-wrap:wrap;gap:4px;">${locs}</div></div>` : ''}
    ${plots ? `<div><div class="panel-section-title">Plot threads</div><div style="display:flex;flex-direction:column;gap:4px;">${plots}</div></div>` : ''}
    ${scene.heading ? `<div><div class="panel-section-title">Screenplay heading</div><div class="panel-muted">${escapeHtml(scene.heading)}</div></div>` : ''}
    <div><div class="panel-section-title">Content</div>${contentHtml}</div>
  `;

  document.getElementById('panel-footer').innerHTML = `
    <button class="btn btn-hermes" data-hermes-send="What happens in ${scene.title || scene.id}?">Ask Hermes about this scene</button>
  `;

  openPanel();
}
```

#### E. Add Sequence & Act Panels

```javascript
function showSequencePanel(seqId) {
  const seq = (story.sequences || []).find(s => s.id === seqId);
  if (!seq) return;

  document.getElementById('panel-type').textContent = 'Sequence';
  document.getElementById('panel-name').textContent = seq.title || seq.id;

  const sceneRows = (seq.scenes_list || []).map((sid, i) => {
    const scene = (story.scenes || []).find(s => s.id === sid);
    if (!scene) return '';
    return `<div class="beat-row" onclick="showScenePanel('${sid}')">
      <span class="beat-scene">${i + 1}. ${scene.title || sid}</span>
      ${scene.heading ? `<span class="beat-desc">${escapeHtml(scene.heading)}</span>` : ''}
    </div>`;
  }).join('');

  document.getElementById('panel-body').innerHTML = `
    <div><span class="status-badge ${seq.status || ''}">${seq.status || 'planned'}</span></div>
    ${sceneRows ? `<div><div class="panel-section-title">Scenes (${seq.scene_count || 0})</div>${sceneRows}</div>` : '<div class="panel-muted">No scenes in this sequence yet.</div>'}
  `;

  document.getElementById('panel-footer').innerHTML = `
    <button class="btn btn-hermes" data-hermes-send="What is the dramatic function of the sequence '${seq.title || seq.id}'?">Ask Hermes about this sequence</button>
  `;

  openPanel();
}

function showActPanel(actId) {
  const act = (story.acts || []).find(a => a.id === actId);
  if (!act) return;

  document.getElementById('panel-type').textContent = 'Act';
  document.getElementById('panel-name').textContent = act.title || act.id;

  const seqRows = (act.sequences_list || []).map(sid => {
    const seq = (story.sequences || []).find(s => s.id === sid);
    return seq ? `<div class="beat-row" onclick="showSequencePanel('${sid}')">
      <span class="beat-scene">${seq.title || sid}</span>
      <span class="beat-desc">${seq.scene_count || 0} scenes</span>
    </div>` : '';
  }).join('');

  document.getElementById('panel-body').innerHTML = `
    <div><span class="status-badge ${act.status || ''}">${act.status || 'planned'}</span></div>
    ${seqRows ? `<div><div class="panel-section-title">Sequences (${act.sequence_count || 0})</div>${seqRows}</div>` : '<div class="panel-muted">No sequences in this act yet.</div>'}
  `;

  document.getElementById('panel-footer').innerHTML = `
    <button class="btn btn-hermes" data-hermes-send="What is the dramatic arc of '${act.title || act.id}'?">Ask Hermes about this act</button>
  `;

  openPanel();
}
```

#### F. Add Sequences & Acts Nav Buttons + Views

Add to sidebar:
```html
<button class="nav-btn" data-view="sequences" onclick="switchView('sequences', this)">
  <svg class="nav-icon" viewBox="0 0 16 16" fill="none">
    <rect x="2" y="2" width="12" height="12" rx="1.5" stroke="currentColor" stroke-width="1.4"/>
    <line x1="5" y1="6" x2="11" y2="6" stroke="currentColor" stroke-width="1.2"/>
    <line x1="5" y1="8.5" x2="11" y2="8.5" stroke="currentColor" stroke-width="1.2"/>
    <line x1="5" y1="11" x2="8.5" y2="11" stroke="currentColor" stroke-width="1.2"/>
  </svg>
  <span class="nav-label">Sequences</span>
</button>
<button class="nav-btn" data-view="acts" onclick="switchView('acts', this)">
  <svg class="nav-icon" viewBox="0 0 16 16" fill="none">
    <path d="M8 2L14 5v6l-6 3-6-3V5z" stroke="currentColor" stroke-width="1.4" stroke-linejoin="round"/>
  </svg>
  <span class="nav-label">Acts</span>
</button>
```

Add views (use existing `entity-list-view` CSS class):
```html
<div class="view entity-list-view" id="sequences-view">
  <div class="view-header">
    <div class="view-title">Sequences</div>
    <div class="view-subtitle" id="sequences-subtitle">—</div>
  </div>
  <div class="view-body">
    <div class="entity-grid" id="sequence-list"></div>
  </div>
</div>
<div class="view entity-list-view" id="acts-view">
  <div class="view-header">
    <div class="view-title">Acts</div>
    <div class="view-subtitle" id="acts-subtitle">—</div>
  </div>
  <div class="view-body">
    <div class="entity-grid" id="act-list"></div>
  </div>
</div>
```

Add `buildSequencesView()` and `buildActsView()` following `buildLocationsView()` pattern.

#### G. Add Structural Stats Tab

Add 4th tab "Structure" to stats panel:
```html
<button class="stats-tab" data-group="structure" onclick="switchStatsGroup('structure', this)">Structure</button>
```

Add stats group with scene status breakdown (bar chart), dramatic role distribution, act distribution. Read from `window.__STRUCTURAL_STATS__`.

#### H. Fix Story View Stats Grid

Add:
```javascript
{ v: p.sequence_count || (story.sequences || []).length, l: 'Sequences' },
{ v: p.act_count      || (story.acts      || []).length, l: 'Acts' },
```

#### I. Fix `normalise()` — Use `scene.title` and Match Character Scenes by `id`

```javascript
// Scenes: ensure id is string, normalise character/location arrays
(d.scenes || []).forEach(s => {
  s.id = String(s.id);
  s.title = s.title || s.id;  // ensure title exists
  s.characters = (s.characters || []).map(String);
  s.locations = normalizeLocs(s.locations || s.location);
  s.plots = (s.plots || []);
});

// Characters: match scenes by id (not heading/number)
if (Array.isArray(c.scenes) && c.scenes.length && typeof c.scenes[0] === 'object') {
  c._scene_objs = c.scenes;
  c.scenes = c.scenes.map(s => {
    const found = (d.scenes || []).find(sc =>
      String(sc.id) === String(s.id) ||  // match by slug id (preferred)
      sc.heading === s.heading ||          // fallback: heading match
      (sc.heading || '').includes(s.heading || '__NOMATCH__')  // fallback: fuzzy
    );
    return found ? String(found.id) : (s.heading || String(s.id));
  });
}
```

#### J. Fix `renderBeats()` — Match by `scene_id`

```javascript
const sceneObj = (story.scenes || []).find(s => String(s.id) === String(item.scene_id));
```

#### K. Fix `_enrich_entity_scenes()` — Store `title` in Character/Location Scenes

**File:** `core/index.py`, `_enrich_entity_scenes()` function (~line 148)

Currently stores only `{id, heading}`. After refactor, heading is optional. **Fix: also store `title`.**

```python
# OLD (line 148-151):
char_scenes[char_id].append({
    "id": scene.get("id"),
    "heading": scene.get("heading", ""),
})

# NEW:
char_scenes[char_id].append({
    "id": scene.get("id"),
    "title": scene.get("title", ""),
    "heading": scene.get("heading", ""),
})
```

Same fix for `loc_scenes` (~line 154-157).

#### L. Fix `showCharacterPanel()` Scene List — Use `title` Not `heading`

**File:** `story-dashboard.html`, `showCharacterPanel()` function (~line 2097-2103)

Currently shows `s.heading || s.id` for character scene references. After refactor, heading may be empty. **Fix: use `s.title || s.id`.**

```javascript
// OLD (~line 2097-2103):
const label = num ? `${num}. ${s.heading || s.id}` : (s.heading || s.id);

// NEW:
const label = num ? `${num}. ${s.title || s.id}` : (s.title || s.id);
```

---

## 4. Implementation Steps

| # | Task | File | Lines | Depends On | STATUS |
| --- | --- | --- | --- | --- | --- |
| 1 | Add `assemble_scene_content()` to `core/index.py` | core/index.py | +45 | — | Done |
| 2 | Add `compute_structural_stats()` to `core/index.py` | core/index.py | +20 | — | Done |
| 3 | Fix `_enrich_entity_scenes()` — store `title` in `char_scenes`/`loc_scenes` | core/index.py | +4 | — | Done |
| 4 | Replace screenplay injection in `handler()` with scene-based injection | tools/story_dashboard.py | +20 / -15 | 1, 2 | Done |
| 5 | Update `_extract_sections()` — add scenes/sequences/acts | tools/story_dashboard.py | +3 | — | Done |
| 6 | Remove `formatFountainScene()`, `extractFountainScene()`, `loadSceneContent()` | story-dashboard.html | -100 | — | Done |
| 7 | Rewrite `buildScriptView()` — use `__SCREENPLAY_STATS__.scriptHtml` | story-dashboard.html | +30 | 4 | Done |
| 8 | Fix `normalise()` — `scene.title` + character scene `id` matching | story-dashboard.html | +10 | — | Done |
| 9 | Rewrite `buildScenesView()` — hierarchical grouping | story-dashboard.html | +50 | — | Done |
| 10 | Update `showScenePanel()` — use `## Content` from `__SECTIONS__` | story-dashboard.html | +20 | — | Done |
| 11 | Fix `showCharacterPanel()` — use `s.title \|\| s.id` | story-dashboard.html | +2 | 3 | Done |
| 12 | Add `showSequencePanel()` + `showActPanel()` | story-dashboard.html | +40 | — | Done |
| 13 | Add Sequences/Acts nav buttons + views | story-dashboard.html | +30 | — | Done |
| 14 | Add structural stats tab + rendering | story-dashboard.html | +65 | 2 | Done |
| 15 | Fix `renderBeats()` — match by `scene_id` | story-dashboard.html | +5 | — | Done |
| 16 | Fix story view stats grid | story-dashboard.html | +2 | — | Done |
| 17 | Tests for `assemble_scene_content()` | tests/test_core.py | +3 | 1 | Done |
| 18 | Tests for `compute_structural_stats()` | tests/test_core.py | +2 | 2 | Done |
| 19 | Test screenplay stats from assembled scene content | tests/test_core.py | +2 | 1, 4 | Done |
| 20 | Test `_enrich_entity_scenes()` title preservation | tests/test_core.py | +2 | 3 | Pending |

**Build order:**
- Tasks 1-3 (Python backend) can be done together → test independently
- Tasks 4-5 (dashboard backend) depend on 1, 2
- Tasks 6-16 (frontend) are independent of each other, depend only on 4
- Tasks 17-20 (tests) depend on their respective implementations

**Total: 20 tasks, 4 files, ~260 lines added / ~115 lines removed.**

---

## 4B. Implementation Report

### TASKS 1-3
**Status:** Tasks 1–3 done. Tasks 4–20 pending.
| # | Task | Status |
|---|------|--------|
| 1 | `assemble_scene_content()` — standalone function per §3.1 | Done (+45) |
| 2 | `compute_structural_stats()` — `Counter`-based tallies | Done (+18) |
| 3 | `_enrich_entity_scenes()` — add `title` field | Done (+4) |
**Removed:** `assemble_script_from_scenes()` (alias added in error, plan eliminated it).
**Files:** `core/index.py` +67 lines.
**Verification:** 54/54 existing tests pass. Smoke-tested: empty scenes → `""`, `## Content` prefix stripped, order traversal correct.

### TASKS 4-5
**Status:** Tasks 4–5 done. Tasks 6–20 pending.
| # | Task | Status |
|---|------|--------|
| 4 | Replace screenplay injection in `handler()` with scene-based injection | Done (+20/-15) |
| 5 | Update `_extract_sections()` — add scenes/sequences/acts | Done (+3) |
**Removed:** `screenplay.fountain` injection block, `window.__SCREENPLAY_TEXT__`, `screenplay_path` file read.
**Files:** `tools/story_dashboard.py` +23/-15 lines.
**Verification:** 54/54 existing tests pass. `assemble_scene_content()` → `_compute_screenplay_stats()` pipeline works with empty and populated scene content.

### TASK 6
**Status:** Task 6 done.
| # | Task | Status |
|---|------|--------|
| 6 | Remove `formatFountainScene()`, `extractFountainScene()`, `loadSceneContent()` | Done (-180) |
**Removed:** `formatFountainScene()`, `extractFountainScene()`, `loadSceneContent()`, `_screenplayText`, `_screenplayLoaded`, `isFountainSceneHeading()`, `isForcedSceneHeading()`. `showScenePanel()` rewritten to use `__SECTIONS__.scenes[slug]["Content"]` instead of screenplay text extraction.
**Files:** `src/dashboard/story-dashboard.html` -180 lines.
**Verification:** Zero references to removed functions remain. `escapeHtml()` restored as standalone function (was nested in deleted block, used in 13+ places).

### TASK 7
**Status:** Task 7 done.
| # | Task | Status |
|---|------|--------|
| 7 | Rewrite `buildScriptView()` — use `__SCREENPLAY_STATS__.scriptHtml` | Done (-35) |
**Removed:** `__SCREENPLAY_TEXT__` fallback branch (raw Fountain text client-side renderer), `preHtml`/`rawText` dual-path logic, estimated pages fallback.
**Files:** `src/dashboard/story-dashboard.html` -35 lines.
**Verification:** Function now single-path: empty state if no stats/scriptHtml, otherwise render server-provided HTML. Scene count from `story.scenes` (not stats).

### TASK 8
**Status:** Task 8 done.
| # | Task | Status |
| --- | --- | --- |
| 8 | Fix `normalise()` — `scene.title` + character scene `id` matching | Done (+2) |
**Changes:** Character scene matching prefers `s.id` (slug) over `s.number`. Scene normalization ensures `title` exists (`s.title = s.title s.id`).

### TASK 9
**Status:** Task 9 done.
| # | Task | Status |
|---|------|--------|
| 9 | Rewrite `buildScenesView()` — hierarchical grouping | Done (+42) |
**Changes:** `renderSceneList()` now groups scenes by act → sequence hierarchy. New `renderSceneItem()` helper for individual scene cards. Scene number from `s.order` (not `s.scene_number` or index). Heading shown as secondary metadata. Click handlers attached via event delegation after render.
**Files:** `src/dashboard/story-dashboard.html` +42 lines.
**Verification:** Hierarchical output: Act title → Sequence header → Scene items. Unassigned scenes grouped under "Unassigned" header.

### TASK 10
**Status:** Task 10 done (no-op — already implemented in TASK 6).
| # | Task | Status |
|---|------|--------|
| 10 | Update `showScenePanel()` — use `## Content` from `__SECTIONS__` | Done (0) |
**Changes:** Already done in TASK 6. `showScenePanel()` uses `__SECTIONS__.scenes[slug]["Content"]`.
**Verification:** No changes needed.

### TASK 11
**Status:** Task 11 done.
| # | Task | Status |
| --- | --- | --- |
| 11 | Fix `showCharacterPanel()` — use `s.title \|\| s.id` | Done (+2) |
**Changes:** Character scene list now uses `s.title s.id` instead of `s.heading s.id`.

### TASK 12 + 13
**Status:** Tasks 12–13 done.
| # | Task | Status |
|---|------|--------|
| 12 | `showSequencePanel()` + `showActPanel()` | Done (+55) |
| 13 | Sequences/Acts nav buttons + views | Done (+25) |
**Changes:** `showSequencePanel(seqId)` renders status badge, ordered scene rows from `seq.scenes_list` (clickable → `showScenePanel`), Hermes button. `showActPanel(actId)` renders status badge, sequence rows from `act.sequences_list` (clickable → `showSequencePanel`), Hermes button. Nav buttons (Sequences, Acts) with SVG icons added after Plots. `buildSequencesView()` and `buildActsView()` follow `buildLocationsView()` pattern with entity cards. Both views call their respective panel openers.
**Files:** `src/dashboard/story-dashboard.html` +80 lines.
**Verification:** 54/54 existing tests pass. Both panels open from card clicks, scene links inside panels navigate correctly.

### TASK 14
**Status:** Task 14 done.
| # | Task | Status |
|---|------|--------|
| 14 | Add structural stats tab + rendering | Done (+65) |
**Changes:** "Structure" tab button added to stats subnav. New `#stats-group-structure` stats group with: scene/sequence/act count stat blocks (`structStats-scenes/sequences/acts`), scene status bar chart (`structStats-status-bars`, color-coded: planned/grey, drafted/yellow, written/teal, locked/blue), dramatic role distribution bar chart (`structStats-role-bars`, color-coded: setup/blue, complication/yellow, crisis/red, climax/purple, resolution/teal, transition/grey, unset/dark), act list (`structStats-act-list`) with beat-row layout showing title + scene/sequence counts. Hermes analysis button included. `populateStructuralStats()` reads `window.__STRUCTURAL_STATS__` (injected server-side by `compute_structural_stats()`), called from `populateStats()` on first panel open.
**Files:** `src/dashboard/story-dashboard.html` +65 lines.
**Verification:** 54/54 existing tests pass. Tab switches correctly, all DOM IDs present, JS references `compute_structural_stats` output schema (sceneCount, sequenceCount, actCount, sceneStatus, sceneRoles, acts).

### TASK 15
**Status:** Task 15 done.
| # | Task | Status |
| --- | --- | --- |
| 15 | Fix `renderBeats()` — match by `scene_id` | Done (+2/-10) |
**Changes:** `renderBeats()` now matches scenes by `item.scene_id` (slug id) instead of heading/number. Backend normalizes setups/payoffs to `{scene_id, description}` — old heading-matching logic removed. Display uses `sceneObj.title sceneObj.id` for label and `sceneObj.order` for display number. Comment updated to reflect real data shape.

### TASK 16
**Status:** Task 16 done.
| # | Task | Status |
| --- | --- | --- |
| 16 | Fix story view stats grid | Done (+2) |
**Changes:** Added `{ v: p.sequence_count (story.sequences []).length, l: 'Sequences' }` and `{ v: p.act_count (story.acts []).length, l: 'Acts' }` to `statsGrid` in `buildStoryView()`, after Plots.

### TASK 17
**Status:** Task 17 done.
| # | Task | Status |
| --- | --- | --- |
| 17 | Tests for `assemble_scene_content()` | Done (+220) |
**Changes:** Added `TestAssembleSceneContent` class (7 tests): `test_empty_scenes` (no scenes → `""`), `test_scene_with_content` (single scene → text extracted), `test_respects_act_sequence_order` (act→sequence→order traversal), `test_missing_scene_file_skipped` (missing file → no crash), `test_scene_without_content_section_skipped` (no `## Content` → skipped), `test_content_heading_prefix_stripped` (`## Content` prefix removed from output), `test_multiple_scenes_concatenated` (multiple scenes joined with `\n\n`). Helper `_make_project_with_scenes()` creates minimal project structures with scene/sequence/act files on disk.
**Files:** `tests/test_core.py` +220 lines.
**Verification:** 61/61 tests pass (54 existing + 7 new). All `assemble_scene_content()` edge cases covered: empty, populated, ordering, missing files, missing section, heading stripping, concatenation.


### TASK 18
**Status:** Task 18 done.
| # | Task | Status |
| --- | --- | --- |
| 18 | Tests for `compute_structural_stats()` | Done (+97) |
**Changes:** Added `TestComputeStructuralStats` class (5 tests): `test_empty_index` (zero counts, empty collections), `test_status_and_role_counts` (Counter-based tallies match frontmatter), `test_missing_role_defaults_to_unset` (empty/missing `dramatic_role` → `"unset"` bucket), `test_acts_list_with_counts` (act stats include `sceneCount`/`sequenceCount` from index), `test_multiple_acts` (all acts listed with individual counts).
**Files:** `tests/test_core.py` +97 lines.
**Verification:** 66/66 tests pass (61 existing + 5 new). All `compute_structural_stats()` paths covered: empty index, status/role aggregation, missing-role fallback, act list with counts, multiple acts.


### TASK 19
**Status:** Task 19 done.
| # | Task | Status |
| --- | --- | --- |
| 19 | Test screenplay stats from assembled scene content | Done (+46) |
**Changes:** Added `TestScreenplayStatsFromSceneContent` class (1 test): `test_pipeline_produces_stats_with_scriptHtml` — creates a project with scene content (EXT. THE INSTITUTE - DAY with action + dialogue), calls `assemble_scene_content()` → `_compute_screenplay_stats()`, verifies stats dict has `scriptHtml` (non-empty), `lengthStats.scenes >= 1`.
**Files:** `tests/test_core.py` +46 lines.
**Verification:** 67/67 tests pass (66 existing + 1 new). Pipeline verified: scene `## Content` → concatenated Fountain text → screenplay stats with scriptHtml.


### TASK 20
**Status:** Task 20 done.
| # | Task | Status |
| --- | --- | --- |
| 20 | Test `_enrich_entity_scenes()` title preservation | Done (+66) |
**Changes:** Added `TestEnrichEntityScenesTitle` class (3 tests): `test_character_scenes_have_title` — character's `scenes[]` entries contain `title` field from scene frontmatter, `test_location_scenes_have_title` — location's `scenes[]` entries contain `title` field, `test_character_without_scenes_has_no_scenes_key` — character with no scenes doesn't get `scenes` key added.
**Files:** `tests/test_core.py` +66 lines.
**Verification:** 70/70 tests pass (67 existing + 3 new). `_enrich_entity_scenes()` correctly stores `title` in character/location scene references; no regression on entities without scenes.


### Python Tests (runnable)

```python
def test_assemble_scene_content_empty(tmp_path):
    """No scenes → empty string."""

def test_assemble_scene_content_with_content(tmp_path):
    """Scene with ## Content → concatenated text in order."""

def test_assemble_scene_content_respects_order(tmp_path):
    """Scenes in different sequences appear in act→sequence→order."""

def test_compute_structural_stats_counts(tmp_path):
    """Status and role counts match scene frontmatter."""

def test_structural_stats_acts_list(tmp_path):
    """Act stats include scene/sequence counts from index."""

def test_screenplay_stats_from_scene_content(tmp_path):
    """_compute_screenplay_stats(assemble_scene_content(...)) returns valid stats incl scriptHtml."""

def test_screenplay_stats_character_speaking_time(tmp_path):
    """Character speaking time computed from scene content matches expected."""

def test_enrich_entity_scenes_stores_title(tmp_path):
    """Character scenes[] entries have title field."""
```

### Browser Verification (manual)

1. [ ] Dashboard opens with `__SCREENPLAY_STATS__` injected (computed from scene content)
2. [ ] Script view renders scene content as Fountain HTML via `stats.scriptHtml`
3. [ ] **Statistics panel works** (length, duration, character speaking time, INT/EXT, barcode)
4. [ ] Scenes view groups under act → sequence headers
5. [ ] Scene panel shows `## Content` from sections
6. [ ] Sequence panel shows ordered scene list
7. [ ] Act panel shows sequences + scenes
8. [ ] Structural stats tab renders status/role charts
9. [ ] Story view shows sequence/act counts
10. [ ] Plot beats match by `scene_id`
11. [ ] All existing entity panels still work

---

## 6. Migration Notes

- **No backward compatibility** — no real projects exist
- Client-side `formatFountainScene()` is removed (replaced by server pre-rendering)
- Dashboard no longer depends on `window.__SCREENPLAY_TEXT__` or `screenplay.fountain`
- `__SCREENPLAY_STATS__` now computed from scene content (not screenplay file)
- `__SECTIONS__` still used for entity panel body content (scenes, sequences, acts now included)
- `_compute_screenplay_stats()` function unchanged — only its input source changes

---

## 7. Success Criteria

- [ ] Script view assembles from scene `## Content` via `__SCREENPLAY_STATS__.scriptHtml`
- [ ] `formatFountainScene()` client-side code removed
- [ ] All existing screenplay stats preserved (length, duration, character speaking time, INT/EXT, barcode)
- [ ] Scenes view shows hierarchical grouping
- [ ] Scene/sequence/act panels render from index
- [ ] Structural stats computed server-side and injected
- [ ] All existing entity panels still work
- [ ] Plot beats match by `scene_id`
- [ ] All existing Python tests pass (+10 new tests)
- [ ] No reference to `screenplay.fountain` in dashboard code

def test_assemble_scene_content_respects_order(tmp_path):
    """Scenes in different sequences appear in act→sequence→order."""

def test_compute_structural_stats_counts(tmp_path):
    """Status and role counts match scene frontmatter."""

def test_structural_stats_acts_list(tmp_path):
    """Act stats include scene/sequence counts from index."""

def test_screenplay_stats_from_scene_content(tmp_path):
    """_compute_screenplay_stats(assemble_scene_content(...)) returns valid stats incl scriptHtml."""

def test_screenplay_stats_character_speaking_time(tmp_path):
    """Character speaking time computed from scene content matches expected."""

def test_enrich_entity_scenes_stores_title(tmp_path):
    """Character scenes[] entries have title field."""
```

### Browser Verification (manual)

1. [ ] Dashboard opens with `__SCREENPLAY_STATS__` injected (computed from scene content)
2. [ ] Script view renders scene content as Fountain HTML via `stats.scriptHtml`
3. [ ] **Statistics panel works** (length, duration, character speaking time, INT/EXT, barcode)
4. [ ] Scenes view groups under act → sequence headers
5. [ ] Scene panel shows `## Content` from sections
6. [ ] Sequence panel shows ordered scene list
7. [ ] Act panel shows sequences + scenes
8. [ ] Structural stats tab renders status/role charts
9. [ ] Story view shows sequence/act counts
10. [ ] Plot beats match by `scene_id`
11. [ ] All existing entity panels still work

---

## 6. Migration Notes

- **No backward compatibility** — no real projects exist
- Client-side `formatFountainScene()` is removed (replaced by server pre-rendering)
- Dashboard no longer depends on `window.__SCREENPLAY_TEXT__` or `screenplay.fountain`
- `__SCREENPLAY_STATS__` now computed from scene content (not screenplay file)
- `__SECTIONS__` still used for entity panel body content (scenes, sequences, acts now included)
- `_compute_screenplay_stats()` function unchanged — only its input source changes

---

## 7. Success Criteria

- [ ] Script view assembles from scene `## Content` via `__SCREENPLAY_STATS__.scriptHtml`
- [ ] `formatFountainScene()` client-side code removed
- [ ] All existing screenplay stats preserved (length, duration, character speaking time, INT/EXT, barcode)
- [ ] Scenes view shows hierarchical grouping
- [ ] Scene/sequence/act panels render from index
- [ ] Structural stats computed server-side and injected
- [ ] All existing entity panels still work
- [ ] Plot beats match by `scene_id`
- [ ] All existing Python tests pass (+10 new tests)
- [ ] No reference to `screenplay.fountain` in dashboard code
