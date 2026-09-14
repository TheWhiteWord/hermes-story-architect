# Task 13 (cont.): Story-Level Structural Fields — Dashboard & Validation

**Created:** 2026-09-14
**Status:** Plan — ready for task decomposition → ✅ COMPLETED
**Input:** Task 13 refactor (unified index) + McKee hierarchy discussion

---

## 1. Principle

The data model already has all the right fields. `ENTITY_SCHEMAS["project"]` has `spine`, `controlling_idea`, `value`, `value_at_open`, `value_at_close`, `inciting_incident_scene_id`, `story_climax_scene_id`, `structure_type`. Both `index-format.md` files document them. The gap is:

1. The dashboard doesn't render them
2. The index validator doesn't cross-check the new scene references
3. The act panel doesn't show the story spine as context for the act objective

No new data model changes. No new fields. Just surfacing what's already there.

---

## 2. Current State

| File | What's Missing |
|------|----------------|
| `src/dashboard/story-dashboard.html` → `buildStoryView()` | Only shows name, logline, genre, setting, counts. Ignores spine, controlling idea, value arc, structure type, inciting incident, story climax. |
| `src/dashboard/story-dashboard.html` → `showActPanel()` | Shows `act_objective` but not the story spine it serves. |
| `src/dashboard/story-dashboard.html` → hardcoded fallback (line ~1590) | Default project object has old fields only. |
| `core/index.py` → `_validate_index()` | Doesn't validate `inciting_incident_scene_id` / `story_climax_scene_id` against scene IDs. |

---

## 3. End State

- Story view shows: spine, controlling idea, value arc (open → close), structure type, inciting incident scene, story climax scene — all null-safe
- Act panel shows: "Story spine: ..." as muted reference line above the act's own objective
- Index validator warns if `inciting_incident_scene_id` or `story_climax_scene_id` reference non-existent scenes
- Hardcoded fallback includes new fields (empty strings)

---

## 4. Task Decomposition

### Task A: Dashboard Story View — Render New Fields

**File:** `src/dashboard/story-dashboard.html`
**Function:** `buildStoryView()`

**Location:** Separate "Structure" section below the project-card (not inside the grid).

**Styling:** Inline styles — no new CSS classes. Use existing `story-section-title` for the section header, and muted text style for field values.

**Scene references:** Clickable `<button class="entity-link">` that calls `showScenePanel(sceneId)` — same pattern as character/location links elsewhere.

**Implementation:**

After `statsHtml` (line ~2112), before plots:

```javascript
// Structure section (spine, controlling idea, value arc, structure type, key scenes)
const structure = [];

if (p.spine) structure.push(`<div style="margin-bottom:6px"><span style="color:var(--muted-foreground);font-size:var(--font-size-xs);text-transform:uppercase;letter-spacing:0.06em">Spine</span><div style="font-size:var(--font-size-sm);color:var(--foreground);margin-top:2px">${p.spine}</div></div>`);

if (p.controlling_idea) structure.push(`<div style="margin-bottom:6px"><span style="color:var(--muted-foreground);font-size:var(--font-size-xs);text-transform:uppercase;letter-spacing:0.06em">Controlling Idea</span><div style="font-size:var(--font-size-sm);color:var(--foreground);margin-top:2px">${p.controlling_idea}</div></div>`);

const valueArc = [];
if (p.value) valueArc.push(`<span style="color:var(--muted-foreground);font-size:var(--font-size-xs)">${p.value}</span>`);
if (p.value_open) valueArc.push(`<span style="color:var(--muted-foreground);font-size:var(--font-size-xs)">${p.value_open}</span>`);
if (p.value_close) valueArc.push(`<span style="color:var(--muted-foreground);font-size:var(--font-size-xs)">${p.value_close}</span>`);
if (valueArc.length) structure.push(`<div style="margin-bottom:6px"><span style="color:var(--muted-foreground);font-size:var(--font-size-xs);text-transform:uppercase;letter-spacing:0.06em">Value Arc</span><div style="font-size:var(--font-size-sm);color:var(--foreground);margin-top:2px;display:flex;gap:6px;align-items:center">${valueArc.join(' → ')}</div></div>`);

if (p.structure_type) structure.push(`<div style="margin-bottom:6px"><span style="color:var(--muted-foreground);font-size:var(--font-size-xs);text-transform:uppercase;letter-spacing:0.06em">Structure</span><div style="font-size:var(--font-size-sm);color:var(--foreground);margin-top:2px">${p.structure_type}</div></div>`);

// Key scenes: inciting incident, story climax — clickable
const keyScenes = [];
if (p.inciting_incident_scene_id) {
  const sid = p.inciting_incident_scene_id;
  const scene = (story.scenes || []).find(s => String(s.id) === String(sid));
  const label = scene ? scene.title : sid;
  keyScenes.push(`<div style="margin-bottom:6px"><span style="color:var(--muted-foreground);font-size:var(--font-size-xs);text-transform:uppercase;letter-spacing:0.06em">Inciting Incident</span><div style="margin-top:2px"><button class="entity-link" onclick="showScenePanel('${sid}')" style="font-size:var(--font-size-sm);padding:0;background:none;border:none;cursor:pointer;color:var(--accent);text-decoration:underline">${label}</button></div></div>`);
}
if (p.story_climax_scene_id) {
  const sid = p.story_climax_scene_id;
  const scene = (story.scenes || []).find(s => String(s.id) === String(sid));
  const label = scene ? scene.title : sid;
  keyScenes.push(`<div style="margin-bottom:6px"><span style="color:var(--muted-foreground);font-size:var(--font-size-xs);text-transform:uppercase;letter-spacing:0.06em">Story Climax</span><div style="margin-top:2px"><button class="entity-link" onclick="showScenePanel('${sid}')" style="font-size:var(--font-size-sm);padding:0;background:none;border:none;cursor:pointer;color:var(--accent);text-decoration:underline">${label}</button></div></div>`);
}

const structureHtml = (structure.length || keyScenes.length) ? `
  <div>
    <div class="story-section-title">Structure</div>
    <div style="padding:12px;background:var(--card);border:1px solid var(--border);border-radius:var(--radius)">
      ${structure.join('')}
      ${keyScenes.join('')}
    </div>
  </div>` : '';
```

Then change `body.innerHTML = statsHtml + plotsHtml + risksHtml + hermesHtml;` to:
```javascript
body.innerHTML = statsHtml + structureHtml + plotsHtml + risksHtml + hermesHtml;
```

**Check:** Dashboard opens with new fields visible when present, absent when empty strings. Scene links call `showScenePanel`. No JS errors on null/undefined.

---

### Task B: Dashboard Act Panel — Show Story Spine + Act Objective

**File:** `src/dashboard/story-dashboard.html`
**Function:** `showActPanel()` (line ~2480)

**Current state:** Shows status badge + sequences list. Does NOT show `act_objective` or story spine.

**Changes:**

1. Add `act_objective` display (if present)
2. Add story spine as muted reference line above the act objective

In `showActPanel()`, after the status badge and before sequences:

```javascript
// Show story spine + act objective (McKee hierarchy: act objective serves story spine)
const projectSpine = (story.project || {}).spine;
const actObj = act.act_objective;
const spineAndObjective = (projectSpine || actObj) ? `
  <div style="margin-top:8px">
    ${projectSpine ? `<div style="font-size:var(--font-size-xs);color:var(--muted-foreground);margin-bottom:4px">Story spine: <span style="font-style:italic">${projectSpine}</span></div>` : ''}
    ${actObj ? `<div style="font-size:var(--font-size-xs);color:var(--muted-foreground)">Act objective: <span style="color:var(--foreground);font-weight:500">${actObj}</span></div>` : ''}
  </div>` : '';
```

Insert after the status badge div, before the sequences block.

**Check:** Act panel shows "Story spine: ..." when project.spine is set, "Act objective: ..." when act.act_objective is set. Both visible together makes the McKee connection explicit. No errors when either is missing.

---

### Task C: Index Validator — Cross-Check New Scene Refs

**File:** `core/index.py`
**Function:** `_validate_index()` (line ~221)

**Verified:** `scene_ids` set exists (line 228). Pattern matches existing `climax_scene_id` check. `index["project"]` always present (set by `_parse_project()`). Empty strings are falsy → skip safely.

**Implementation:**

After the act climax check (line ~249), before the scenes loop (line ~251):

```python
# Validate project-level scene references
project = index.get("project", {})
for field in ("inciting_incident_scene_id", "story_climax_scene_id"):
    scene_id = project.get(field, "")
    if scene_id and scene_id not in scene_ids:
        print(f"Warning: project.{field} references unknown scene {scene_id}")
```

**Check:** Run `story_index` on a project with `inciting_incident_scene_id: bad-slug` → prints warning. Valid references → no warning. Empty string → no warning.

---

### Task D: Hardcoded Fallback — Update Default Project

**File:** `src/dashboard/story-dashboard.html`
**Function:** `loadSampleData()` (line ~1587)
**Line:** 1590

**Current state:**
```javascript
project: { name: "The Water Audit", logline: "A forensic accountant...", genre: "Sci-fi thriller", setting: "Near-future city-state", scene_count: 3, character_count: 2, location_count: 1, world_count: 1, plot_count: 1 },
```

**Change:** Add new fields with empty string defaults:
```javascript
project: { name: "The Water Audit", logline: "A forensic accountant...", genre: "Sci-fi thriller", setting: "Near-future city-state", spine: "", controlling_idea: "", value: "", value_at_open: "", value_at_close: "", inciting_incident_scene_id: "", story_climax_scene_id: "", structure_type: "", scene_count: 3, character_count: 2, location_count: 1, world_count: 1, plot_count: 1 },
```

**Verified:** `normalise()` doesn't process `project` — new fields pass through as-is. Dashboard A's code uses `if (p.field)` guards — empty strings are falsy, so sections render absent. No JS errors.

**Check:** Dashboard opens with `loadSampleData()` (no `__STORY_DATA__`) → no console errors. Story view doesn't crash on missing/empty new fields.

---

### Task E: Scene Panel — Dramatic Metadata Block

**File:** `src/dashboard/story-dashboard.html`
**Function:** `showScenePanel()` (line ~2243)

**Scope:** The detail panel that opens when clicking a specific scene (not the main Scenes list). Shows only truthy/positive values — booleans only if `true`, strings only if non-empty, arrays only if non-empty.

**Current state:** Shows Characters, Location, Plot threads, Screenplay heading, Content. Ignores `dramatic_role`, climax flags, value arc, conflict levels.

**Implementation:**

Insert at the top of the panel-body innerHTML (before Characters):

```javascript
// Dramatic metadata — only show positive values
const dramaTags = [];
if (scene.dramatic_role) dramaTags.push({ l: 'role', v: scene.dramatic_role });
if (scene.is_inciting_incident) dramaTags.push({ l: 'inciting', v: 'Inciting Incident' });
if (scene.is_sequence_climax) dramaTags.push({ l: 'seq-climax', v: 'Sequence Climax' });
if (scene.is_act_climax) dramaTags.push({ l: 'act-climax', v: 'Act Climax' });
if (scene.is_story_climax) dramaTags.push({ l: 'story-climax', v: 'Story Climax' });

const valueArc = [scene.value, scene.value_open, scene.value_close].filter(Boolean);
const conflicts = (scene.conflict_levels || []).filter(Boolean);

const dramaHtml = (dramaTags.length || valueArc.length || conflicts.length) ? `
  <div>
    <div style="display:flex;flex-wrap:wrap;gap:4px;margin-bottom:8px">
      ${dramaTags.map(t => `<span class="tag tag-plot">${t.v}</span>`).join('')}
      ${conflicts.map(c => `<span class="tag tag-char" style="font-size:var(--font-size-xs)">${c}</span>`).join('')}
    </div>
    ${valueArc.length ? `<div style="font-size:var(--font-size-xs);color:var(--muted-foreground);margin-bottom:8px">Value arc: ${valueArc.join(' → ')}</div>` : ''}
  </div>` : '';
```

Then prepend `dramaHtml` to the existing `panel-body` innerHTML.

**Check:** Scene panel shows "Inciting Incident", "Sequence Climax", etc. as small tags when flags are true. Shows value arc as a compact line when populated. No visible output when all fields are empty/false. No console errors.

---

## 5. Task Order

1. **A** (dashboard story view) — prerequisite for B
2. **B** (act panel spine + objective) — depends on A's pattern
3. **C** (validator) — independent, can run anytime
4. **D** (fallback) — independent, trivial
5. **E** (scene panel drama) — independent, uses existing `showScenePanel()` pattern

A → B → E (→ C → D anywhere, parallel)

---

## 6. Verification

- Open dashboard on `browser-verification-test` project
- Story view shows: spine, controlling idea, value arc, structure type (when fields are populated)
- Act panel shows: "Story spine: ..." above act objective
- Scene panel shows: "Inciting Incident", "Sequence Climax" as small tags (when true)
- Run `story_index` — no false warnings on valid data
- Temporarily break a `inciting_incident_scene_id` in project.md → `story_index` prints warning
- Reload dashboard → no JS console errors
