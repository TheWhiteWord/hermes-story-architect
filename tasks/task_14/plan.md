# Task 14: Character Arc System — Implementation Plan

> **Scope**: Add character arc data model, index derivation, retrieval, and dashboard visualization.
> **Theory ground**: `skills/story-theory/references/values.md` + `docs/research/arc-visualization-example.html`

---

## Architecture Decisions (Decided)

| Decision | Choice |
|----------|--------|
| Beat file location | `arcs/{character}/{beat_id}.md` (nested by character) |
| Beat frontmatter | `id`, `character`, `scene`, `label`, `action`, `gap`, `choice`, `shift`, `y`, `order` |
|| Beat body sections | `## Action`, `## Gap`, `## Choice`, `## Shift`, `## Development Log` |
| Character frontmatter additions | `arc_type`, `arc_value`, `arc_value_at_open/close`, `arc_complete`, `arc_beat_count` |
| Index derivation | Per-character `arc_beats_list[]`, per-scene `arc_beats[]` |
| Scene→beat linkage | Beat→scene (forward). Index derives `scene.arc_beats[]` (reverse). |
| Value encoding | Linguistic first (Action/Gap/Choice/Shift), Y derived by LLM, stored alongside |
| Value hierarchy | Independent per level, thematically coherent (no rigid parent-child) |

---

## Phase 1: Data Layer — Constants & Entity Schema

### What changes

**`core/constants.py`** — Add arc entity type and enums:
- Add `ARC_TYPES = ["positive", "negative", "flat", "ironic", "absent"]`
- Add `arc` to `REQUIRED_FIELDS` with `[ "id", "character", "scene", "label", "action", "gap", "choice", "shift", "y", "order"]`
- Add `arc` to `ENTITY_FOLDERS` → `{"arc": "arcs"}`
- Add `arc` to `ENTITY_LABELS` → `{"arc": "Arc Beat"}`
- Add `arc` to `ENTITY_SCHEMAS` with full field schema:
  - `id`: string, required
  - `character`: string, required (character slug)
  - `scene`: string, required (scene slug)
  - `label`: string, required (e.g. "First Doubt")
  - `action`: string, required
  - `gap`: string, required
  - `choice`: string, required
  - `shift`: string, required (e.g. "positive → mixed")
  - `y`: number, required (-1.0 to +1.0)
  - `order`: number, required (position within character's arc)
  - `is_crisis`: boolean, default False
  - `is_climax`: boolean, default False

**`core/entity.py`** — Extend `validate_entity()` for `arc` type:
- Validate `y` is numeric between -1.0 and +1.0
- Validate `order` is numeric
- Validate `character` exists in character list (cross-reference check)
- Validate `scene` exists in scene list (cross-reference check)
- Validate `arc_type` on character if present

**`core/entity.py`** — Extend character validation:
- Add `arc_type` to character validation (must be one of `ARC_TYPES` if present)
- Add `arc_value`, `arc_value_at_open`, `arc_value_at_close` validation
- Add `arc_complete` boolean validation

### New files
None.

### Tests to add
- `test_arcs.py` — Validate arc entity frontmatter validation
- `test_arcs.py` — Validate character arc field validation
- `test_arcs.py` — Validate cross-reference (beat.character → character exists, beat.scene → scene exists)

---

## Phase 2: Index Derivation

### What changes

**`core/index.py`** — Add arc parsing and derivation:
1. Parse `arcs/` folder for all beat files (nested: `arcs/{character}/{beat_id}.md`)
2. Add `index["arcs"] = _parse_arcs(project_path / "arcs")`
3. Add `_enrich_characters_with_arcs(index)`:
   - Group beats by `character` field
   - Sort by `order`
   - Build `character["arc_beats_list"]` = `[{id, label, scene, y, order}, ...]` (lightweight)
   - Set `character["arc_beat_count"]` = len(list)
4. Add `_enrich_scenes_with_arcs(index)`:
   - Group beats by `scene` field
   - Build `scene["arc_beats"]` = `[{char: <character_slug>, beat_id: <beat_id>}, ...]`
5. Add arc validation to `_validate_index()`:
   - `beat["character"]` exists in character list
   - `beat["scene"]` exists in scene list
   - `beat["y"]` is within [-1.0, +1.0]
   - `beat["order"]` is numeric

### New files
None.

### Tests to add
- `test_arcs.py` — Index derivation: character.arc_beats_list populated correctly
- `test_arcs.py` — Index derivation: scene.arc_beats populated correctly
- `test_arcs.py` — Index derivation: arc_beat_count set correctly
- `test_arcs.py` — Validation: unknown character slug in beat warns
- `test_arcs.py` — Validation: unknown scene slug in beat warns
- `test_arcs.py` — Validation: y out of range warns

---

## Phase 3: Tools — Create, Edit, Retrieve

### What changes

**`tools/story_create.py`** — Two additions:

1. **When creating a character** — create `arcs/{character}/` directory + set arc frontmatter defaults:
```python
# After character file is written:
arc_folder = project_path / "arcs" / slug
arc_folder.mkdir(exist_ok=True)
# Frontmatter already has arc defaults from ENTITY_SCHEMAS["character"]
```

2. **Support `entity_type: "arc"`** — create beat files via the same tool:
- Path: `arcs/{character}/{beat_id}.md` (nested, not flat)
- Standard sections: `["Action", "Gap", "Choice", "Shift", "Development Log"]`
- Parent validation: `character` must exist, `scene` must exist
- No auto-order (order is explicit in frontmatter)
- Schema defaults from `ENTITY_SCHEMAS["arc"]`

```python
# Path construction for nested arcs
if entity_type == "arc":
    character = frontmatter_data.get("character", "")
    file_path = project_path / folder / character / f"{slug}.md"
else:
    file_path = project_path / folder / f"{slug}.md"
```

**`tools/story_edit.py`** — Support editing arc beats:
- Add `arc` as editable entity type
- Allow editing any beat field
- Support adding new beats (creates new file in `arcs/{character}/`)
- Support removing beats (moves to `_recycle-bin/`)

**`tools/story_retrieve.py`** — Support retrieving beat sections:
- `story_retrieve arcs/{character}/{beat_id}` → loads full beat note
- `story_retrieve arcs/{character}/{beat_id} ## Beat Notes` → loads only notes section
- `story_retrieve arcs/{character}/{beat_id} ## Development Log` → loads only log section

**`tools/story_index.py`** — Index regeneration now includes arcs:
- Already calls `generate_index()` which includes arcs after Phase 2
- No additional changes needed if `_parse_arcs()` is added to `generate_index()`

### New files
None.

### Tests to add
- `test_arcs.py` — story_create: arc folder created with character
- `test_arcs.py` — story_create: arc beat created with entity_type="arc"
- `test_arcs.py` — story_create: arc beat path is arcs/{character}/{beat_id}.md
- `test_arcs.py` — story_create: arc beat validates character exists
- `test_arcs.py` — story_create: arc beat validates scene exists
- `test_arcs.py` — story_edit: can edit beat frontmatter fields
- `test_arcs.py` — story_edit: can add new beat file
- `test_arcs.py` — story_retrieve: can load full beat note
- `test_arcs.py` — story_retrieve: can load specific beat section

---

## Phase 4: Dashboard — Arc Visualization

### What changes

**`tools/story_dashboard.py`** — Add arc visualization to Characters view (extended panel pattern):
1. Inside Characters tab, add arc graph panel (below/right of character network graph)
2. Read `character.arc_beats_list[]` from index (already contains y values)
3. X-axis: narrative progression (0.0–1.0, derived from scene order)
4. Y-axis: value charge (-1.0 to +1.0)
5. Plot each character as a separate colored line
6. Crisis beats: yellow dot; Climax beats: white circle
7. Hover/click beat → shows label + value
8. Sanity check warnings (too flat, too jagged)
9. Scene view: show arc beat dot indicators (colored by character) if scene has `arc_beats`

### New files
None.

### Reference files (work from these)
| File | Why |
|------|-----|
| `tasks/task_14/arc-panel-demo.html` | Specialist's working demo — contains all arc graph CSS/JS. Integrate this into the existing dashboard. |
| `tasks/task_14/arc-visualization-brief.md` | What we asked the specialist for |
| `tasks/task_14/arc-visualization-feedback.md` | Integration notes returned to the specialist |
| `src/dashboard/story-dashboard.html` | Existing dashboard — Network tab pattern, sidebar structure, CSS tokens |
| `skills/story-theory/references/values.md` | Theory grounding for the visualization
### Tests to add
- `test_arcs.py` — Dashboard: arc graph renders within Characters view
- `test_arcs.py` — Dashboard: arc graph renders with correct number of lines
- `test_arcs.py` — Dashboard: beat points plotted at correct y positions
- `test_arcs.py` — Dashboard: scenes with arc beats show indicator dots

---

## Phase 5: Integration with Existing Views

### What changes

**`tools/story_dashboard.py`** — Extend existing views:
1. **Characters view**: add arc indicator badge on character nodes (up/down/flat/ironic)
2. **Scenes view**: show arc beat dot indicators (colored by character) if scene has `arc_beats`
3. **Structure view** (if exists): optionally overlay arc beats on act timeline

### New files
None.

### Tests to add
- `test_arcs.py` — Dashboard: character nodes show arc badge
- `test_arcs.py` — Dashboard: scenes with arc beats show indicator dots

---

## Phase 6: Fixtures & Test Data

### What changes

**`tests/fixtures/save-the-children/`** — Add arc test data:
1. Create `arcs/` folder structure
2. Add 2-3 beats for one character (e.g., `arcs/dr-elena-voss/1.md`)
3. Update `dr-elena-voss.md` frontmatter with arc fields
4. Ensure index generation includes arcs

### New files
- `tests/fixtures/save-the-children/arcs/dr-elena-voss/1.md`
- `tests/fixtures/save-the-children/arcs/dr-elena-voss/2.md`
- `tests/fixtures/save-the-children/arcs/dr-elena-voss/3.md`

### Tests to add
- `test_arcs.py` — Full integration: arc beats appear in index for save-the-children fixture
- `test_arcs.py` — Full integration: scene.arc_beats populated for referenced scenes

---

## Phase 7: Documentation & Skill References

### What changes

**`skills/story-loader/references/index-format.md`** — Document:
- Arc entity schema
- How arcs appear in index (character.arc_beats_list, scene.arc_beats)
- Retrieval patterns for arc beats

**`skills/story-editor/references/`** — Add arc edit patterns:
- How to create a new beat
- How to edit beat frontmatter
- How to retrieve beat content for reasoning
- How to add to development log

**`skills/story-theory/SKILL.md`** — Link to values.md reference

### New files
None (updates to existing files).

---

## File Inventory

### Files to modify

| File | Phase | What |
|------|-------|------|
| `core/constants.py` | 1 | Add ARC_TYPES, arc schema, arc folder/label |
| `core/entity.py` | 1 | Add arc validation, extend character validation |
| `core/index.py` | 2 | Add _parse_arcs, _enrich_characters_with_arcs, _enrich_scenes_with_arcs |
| `tools/story_create.py` | 3 | Create arc skeleton with character folder + support entity_type="arc" for beats |
| `tools/story_edit.py` | 3 | Support arc entity editing |
| `tools/story_retrieve.py` | 3 | Support beat retrieval |
| `tools/story_dashboard.py` | 4, 5 | Extend Characters view with arc panel + scene beat indicators |
| `skills/story-loader/references/index-format.md` | 7 | Document arc index format |
| `skills/story-editor/references/continuity-checks.md` | 7 | Add arc edit patterns |
| `tests/fixtures/save-the-children/characters/dr-elena-voss.md` | 6 | Add arc frontmatter |

### Files to create

| File | Phase | What |
|------|-------|------|
| `tests/test_arcs.py` | 1-6 | All arc tests |
| `tests/fixtures/save-the-children/arcs/dr-elena-voss/1.md` | 6 | Beat fixture |
| `tests/fixtures/save-the-children/arcs/dr-elena-voss/2.md` | 6 | Beat fixture |
| `tests/fixtures/save-the-children/arcs/dr-elena-voss/3.md` | 6 | Beat fixture |

### Files already created (research phase)

| File | What |
|------|------|
| `skills/story-theory/references/values.md` | Theory reference for values |
| `docs/research/arc-visualization-example.html` | Graph mockup |

---

## Test Coverage Requirements

| Test Area | Count | Key Cases |
|-----------|-------|-----------|
| Entity validation | 5 | arc fields, character arc fields, cross-refs, y range, order type |
| Index derivation | 6 | arc_beats_list, scene.arc_beats, beat_count, warnings |
| Create tool | 1 | Arc skeleton created |
| Edit tool | 3 | Edit frontmatter, add beat, remove beat |
| Retrieve tool | 3 | Full note, specific section, nonexistent |
| Dashboard | 5 | Sidebar, graph render, beat points, badges, dots |
| Fixtures/Integration | 2 | Index includes arcs, scene.arc_beats correct |
| **Total** | **25** | |

---

## Risk & Verification Checklist

Before calling Phase N complete:

- [ ] Phase 1: `pytest tests/test_arcs.py -k "validate"` passes
- [ ] Phase 2: `pytest tests/test_arcs.py -k "index"` passes
- [ ] Phase 3: `pytest tests/test_arcs.py -k "tool"` passes
- [ ] Phase 4: Dashboard opens Arcs view, renders graph with fixture data
- [ ] Phase 5: Character badges render, scene dots appear
- [ ] Phase 6: Full integration tests pass with save-the-children fixture
- [ ] Phase 7: Skill docs updated, references cross-linked

---

## Open Questions for Task Creation

These will be resolved when creating individual implementation tasks:

1. **Nested folder parsing**: How does `_parse_arcs()` handle `arcs/{character}/{beat_id}.md`? Recursive glob vs. explicit path construction.
2. **Beat ID uniqueness**: Globally unique or unique within character? (Decision: globally unique, e.g., `beat-2` is fine since path includes character)
3. **Beat file naming**: Numeric (`1.md`) or descriptive (`first-doubt.md`)? (Decision: numeric for order, frontmatter has descriptive `label`)
4. **Development log versioning**: Does the LLM append to `## Development Log` or overwrite? (Decision: append with timestamps)
5. **Dashboard graph spline**: Straight lines between points or smooth curve? (Decision: straight lines first, spline if time permits)
6. **Arc view with no beats**: What does the Arcs view show when no beats exist? (Decision: empty state with "Design arc with Hermes" prompt)

---

## Estimated Task Breakdown

| Phase | Tasks | Est. Lines |
|-------|-------|------------|
| 1. Constants & Schema | 3 tasks | ~60 |
| 2. Index Derivation | 2 tasks | ~80 |
| 3. Tools | 4 tasks | ~100 |
| 4. Dashboard Arc View | 3 tasks | ~150 |
| 5. Dashboard Integration | 2 tasks | ~50 |
| 6. Fixtures | 2 tasks | ~40 |
| 7. Documentation | 2 tasks | ~30 |
| **Total** | **18 tasks** | **~510 lines** |

---

## Next Steps

1. Review this plan with user for any gaps or changes
2. Break each phase into individual implementation tasks with full specs
3. Begin Phase 1 implementation
4. **Development log versioning**: Does the LLM append to `## Development Log` or overwrite? (Decision: append with timestamps)
5. **Dashboard graph spline**: Straight lines between points or smooth curve? (Decision: straight lines first, spline if time permits)
6. **Arc view with no beats**: What does the Arcs view show when no beats exist? (Decision: empty state with "Design arc with Hermes" prompt)

---

## Estimated Task Breakdown

| Phase | Tasks | Est. Lines |
|-------|-------|------------|
| 1. Constants & Schema | 3 tasks | ~60 |
| 2. Index Derivation | 2 tasks | ~80 |
| 3. Tools | 4 tasks | ~100 |
| 4. Dashboard Arc View | 3 tasks | ~150 |
| 5. Dashboard Integration | 2 tasks | ~50 |
| 6. Fixtures | 2 tasks | ~40 |
| 7. Documentation | 2 tasks | ~30 |
| **Total** | **18 tasks** | **~510 lines** |

---

## Next Steps

1. Review this plan with user for any gaps or changes
2. Break each phase into individual implementation tasks with full specs
3. Begin Phase 1 implementation
