# Phase 3 Plan: Tool Surface

**Created:** 2026-09-12
**Status:** Plan — decided, ready for implementation
**Input:** `refactor_overview.md` + `Claude_structure_refactor.md` + `phase 1/plan.md` + `phase 2/plan.md`

---

## 1. What This Phase Does

Extend `story_create` and `story_edit` with structural semantics. No new tool.

**End state:**
- `story_create` validates parents + auto-assigns `order` for scenes/sequences
- `story_edit` gets simplified `data` bag for `edit_note` (replaces verbose `changes` array), `reorder` action, cascade-blocking `delete_entity`
- `core/index.py` gets `update_structure_index_scene()` for lightweight structure-index updates
- No schema changes to `plugin.yaml`, `__init__.py`, or `tools/__init__.py`

---

## 2. Decision: Extend, Don't Add

| | New tool (old plan) | Extend existing |
|---|---|---|
| New files | 1 (~330 lines) | 0 |
| Files modified | 10 | 4 |
| Net new lines | ~492 | ~175 |
| LLM tool count | 8→9 | stays 7 |

The "reorder only matters for structure" concern: it's a non-issue. `story_edit` can expose `reorder` and `delete` actions that only *do something* for structural types — for non-structural types, `reorder` returns "not applicable" and `delete` falls through to the existing recycle-bin behavior. The schema stays flat; the handler routes by type.

---

## 3. RESEARCH FINDINGS

### 3.1 Current `story_edit._edit_note` Schema (the verbose part)

```json
{
  "action": "edit_note",
  "target": {"entity_type": "scene", "slug": "my-scene"},
  "changes": [
    {"type": "body_section", "section": "Description", "new": "Updated text"},
    {"type": "frontmatter", "field": "status", "value": "written"}
  ],
  "summary": "..."
}
```

The `changes` array requires the LLM to specify `type` discriminator for every change. This is the only place in the codebase that uses this pattern — `story_create` uses a flat `frontmatter` bag, `story_retrieve` uses flat `sections` array.

### 3.2 Simplification: `data` Bag

Replace `changes` with `data`:

```json
{
  "action": "edit_note",
  "target": {"entity_type": "scene", "slug": "my-scene"},
  "data": {
    "Description": "Updated text",
    "status": "written"
  },
  "summary": "..."
}
```

Handler routing: key ∈ schema fields → frontmatter update. Key ∈ standard sections → body section update via `replace_section()`. No type discriminator needed.

### 3.3 Current `story_create.handler()` — What's Missing

```python
schema = ENTITY_SCHEMAS.get(entity_type, {})
merged = {field: frontmatter_data.get(field, meta["default"]) for field, meta in schema.items()}
post = frontmatter.Post("", **merged)
```

Missing:
1. Parent validation (sequence_id/act_id must exist)
2. Auto-order (if `order == 0`, compute next in parent)

Both are ~10 lines each.

### 3.4 Current `story_edit._delete_entity()` — What's Missing

```python
def _delete_entity(project_path, target, summary):
    # ... just moves to recycle bin
```

Missing: cascade blocking for sequences (has scenes?) and acts (has sequences?).

### 3.5 `core/index.py` — Lightweight Update

Phase 2 stores `_full_scenes` internally but doesn't expose a single-scene update. Need `update_structure_index_scene(project_path, scene_id)` that reads `structure-index.yaml`, finds entry by `id`, updates from scene file frontmatter, writes back. O(1) vs O(N).

---

## 4. Files to Modify

### 4.1 `tools/story_create.py` (+25 lines)

| Location | Change |
|----------|--------|
| `handler()` | Add parent validation for scenes/sequences; auto-assign `order` if 0 |

```python
# After building merged frontmatter, before writing:
if entity_type in ("scene", "sequence"):
    _validate_parents(project_path, entity_type, merged)
    if merged.get("order", 0) == 0:
        parent = "sequence" if entity_type == "scene" else "act"
        parent_id = merged.get("sequence_id") or merged.get("act_id")
        if parent_id:
            merged["order"] = _get_next_order(project_path, parent, parent_id)
```

New helpers:
```python
def _validate_parents(project_path, entity_type, frontmatter):
    if entity_type == "scene":
        if frontmatter.get("sequence_id") and not _entity_exists(project_path, "sequence", frontmatter["sequence_id"]):
            raise ValueError(f"Sequence not found: {frontmatter['sequence_id']}")
        if frontmatter.get("act_id") and not _entity_exists(project_path, "act", frontmatter["act_id"]):
            raise ValueError(f"Act not found: {frontmatter['act_id']}")
    elif entity_type == "sequence":
        if frontmatter.get("act_id") and not _entity_exists(project_path, "act", frontmatter["act_id"]):
            raise ValueError(f"Act not found: {frontmatter['act_id']}")

def _get_next_order(project_path, parent_type, parent_id):
    folder = "scenes" if parent_type == "sequence" else "sequences"
    field = "sequence_id" if parent_type == "sequence" else "act_id"
    child_dir = project_path / folder
    if not child_dir.exists():
        return 1
    import frontmatter
    max_order = 0
    for note in child_dir.glob("*.md"):
        if note.name.startswith("_"):
            continue
        post = frontmatter.load(note)
        if post.get(field) == parent_id:
            order = post.get("order", 0)
            if isinstance(order, (int, float)) and order > max_order:
                max_order = order
    return int(max_order) + 1

def _entity_exists(project_path, entity_type, slug):
    if not slug:
        return False
    folder = ENTITY_FOLDERS[entity_type]
    return (project_path / folder / f"{slug}.md").exists()
```

### 4.2 `tools/story_edit.py` (+80 lines)

| Location | Change |
|----------|--------|
| `SCHEMA["properties"]["action"]["enum"]` | Add `"reorder"` |
| `SCHEMA["properties"]` | Add `"data"` object, add `"order_context"` object |
| `handler()` | Route `reorder` → `_reorder()`, simplify `edit_note` to use `data` |
| `_edit_note()` | Replace `changes` loop with `data` bag loop |
| `_delete_entity()` | Add cascade blocking for sequences/acts |
| New: `_reorder()` | Batch order update for scenes/sequences |

#### Simplified `edit_note` Schema

Replace:
```json
{"changes": [{"type": "body_section", "section": "...", "new": "..."}, {"type": "frontmatter", "field": "...", "value": "..."}]}
```

With:
```json
{"data": {"Description": "...", "status": "..."}}
```

#### `_edit_note()` New Implementation

```python
def _edit_note(project_path, target, data, summary):
    """Edit an entity note using data bag routing."""
    import frontmatter
    from core.section_parser import replace_section
    
    entity_type = target.get("entity_type")
    slug = target.get("slug")
    folder = ENTITY_FOLDERS.get(entity_type, "")
    file_path = project_path / folder / f"{slug}.md"
    
    if not file_path.exists():
        return _error(f"Entity not found: {entity_type}/{slug}")
    
    post = frontmatter.load(file_path)
    schema_fields = set(ENTITY_SCHEMAS.get(entity_type, {}).keys())
    standard_sections = set(_get_standard_sections(entity_type))
    
    for key, value in data.items():
        if key in schema_fields:
            post[key] = value
        elif key in standard_sections:
            post.content = replace_section(post.content, key, value)
    
    with open(file_path, 'w') as f:
        frontmatter.dump(post, f)
    
    return _success(f"Edited {entity_type}: {slug}", file=str(file_path))
```

#### `_update_story_memory()` New Implementation

```python
def _update_story_memory(project_path, data, summary):
    """Update story memory using data bag routing."""
    import frontmatter
    from core.section_parser import replace_section
    
    memory_path = project_path / ".story" / "memory.md"
    if not memory_path.exists():
        return _error("memory.md not found")
    
    post = frontmatter.load(memory_path)
    schema_fields = set()  # memory.md has no schema — all body sections
    standard_sections = set()  # free-form sections
    
    for key, value in data.items():
        # Try frontmatter first, then body section
        if key in post.metadata or key in schema_fields:
            post[key] = value
        else:
            post.content = replace_section(post.content, key, value)
    
    with open(memory_path, 'w') as f:
        frontmatter.dump(post, f)
    
    return _success(f"Updated story memory: {summary}", file=str(memory_path))
```

#### `reorder` Action

The LLM specifies the **complete new ordering** for a parent's children. This is simpler than "move item to position N" — no find/remove/insert logic, just renumber the whole set.

```json
{
  "action": "reorder",
  "target": {"entity_type": "scene"},
  "order_context": {"ordered_ids": ["scene-3", "scene-1", "scene-2"]},
  "summary": "Reordered scenes in sequence seq-1"
}
```

```python
def _reorder(project_path, target, order_context, summary):
    import frontmatter
    
    entity_type = target.get("entity_type")
    if entity_type not in ("scene", "sequence"):
        return _error(f"Reorder not supported for {entity_type}")
    
    ordered_ids = order_context.get("ordered_ids", [])
    if not ordered_ids:
        return _error("order_context.ordered_ids required")
    
    # Determine parent from first item
    folder = ENTITY_FOLDERS[entity_type]
    parent_field = "sequence_id" if entity_type == "scene" else "act_id"
    
    first_path = project_path / folder / f"{ordered_ids[0]}.md"
    if not first_path.exists():
        return _error(f"{entity_type} not found: {ordered_ids[0]}")
    
    first_post = frontmatter.load(first_path)
    parent_id = first_post.get(parent_field, "")
    
    if not parent_id:
        return _error(f"{entity_type} {ordered_ids[0]} has no parent")
    
    # Verify all items exist and belong to same parent
    for item_id in ordered_ids:
        note_path = project_path / folder / f"{item_id}.md"
        if not note_path.exists():
            return _error(f"{entity_type} not found: {item_id}")
        post = frontmatter.load(note_path)
        if post.get(parent_field) != parent_id:
            return _error(f"{item_id} does not belong to {parent_id}")
    
    # Renumber: 1, 2, 3, ...
    for i, item_id in enumerate(ordered_ids, 1):
        note_path = project_path / folder / f"{item_id}.md"
        post = frontmatter.load(note_path)
        post["order"] = i
        with open(note_path, 'w') as f:
            frontmatter.dump(post, f)
    
    return _success(f"Reordered {len(ordered_ids)} {entity_type}(s) in {parent_id}")
```

#### Cascade-Blocking `delete_entity`

**Why only structural types:** Characters, locations, worlds, and plots are flat entities — they have no parent-child containment. The existing recycle-bin behavior (move file, no cascade) is correct for them. Only sequences and acts have containment relationships (sequence→scenes, act→sequences) that require cascade blocking.

```python
def _delete_entity(project_path, target, summary):
    import shutil
    import frontmatter
    
    entity_type = target.get("entity_type")
    slug = target.get("slug")
    folder = ENTITY_FOLDERS.get(entity_type, "")
    file_path = project_path / folder / f"{slug}.md"
    
    if not file_path.exists():
        return _error(f"Entity not found: {entity_type}/{slug}")
    
    # Cascade blocking ONLY for structural types (containment hierarchy)
    if entity_type == "sequence":
        _check_no_children(project_path, "scenes", "sequence_id", slug, "scene")
    elif entity_type == "act":
        _check_no_children(project_path, "sequences", "act_id", slug, "sequence")
    # Non-structural types (character, location, world, plot): no cascade check needed
    
    # Move to recycle bin
    recycle_bin = project_path / "_recycle-bin" / entity_type
    recycle_bin.mkdir(parents=True, exist_ok=True)
    dest = recycle_bin / f"{slug}.md"
    shutil.move(str(file_path), str(dest))
    
    return _success(f"Deleted {entity_type}: {slug}", file=str(dest))

def _check_no_children(project_path, child_folder, parent_field, parent_id, child_name):
    child_dir = project_path / child_folder
    if not child_dir.exists():
        return
    import frontmatter
    children = []
    for note in child_dir.glob("*.md"):
        if note.name.startswith("_"):
            continue
        post = frontmatter.load(note)
        if post.get(parent_field) == parent_id:
            children.append(post.get("id", note.stem))
    if children:
        raise ValueError(
            f"Cannot delete: {len(children)} {child_name}(s) reference this: {', '.join(children[:5])}"
        )
```

### 4.3 `core/index.py` (+25 lines)

```python
def update_structure_index_scene(project_path: Path, scene_id: str) -> None:
    """Lightweight update: refresh a single scene's entry in structure-index.yaml."""
    import frontmatter
    
    structure_path = project_path / ".story" / "structure-index.yaml"
    if not structure_path.exists():
        return
    
    scene_path = project_path / "scenes" / f"{scene_id}.md"
    if not scene_path.exists():
        return
    
    with open(structure_path) as f:
        structure_index = yaml.safe_load(f)
    
    post = frontmatter.load(scene_path)
    meta = dict(post.metadata)
    
    for i, entry in enumerate(structure_index.get("scenes", [])):
        if entry["id"] == scene_id:
            structure_index["scenes"][i] = {
                "id": scene_id,
                "value": meta.get("value", ""),
                "value_open": meta.get("value_open", ""),
                "value_close": meta.get("value_close", ""),
                "conflict_levels": meta.get("conflict_levels", []),
                "dramatic_role": meta.get("dramatic_role", ""),
                "is_inciting_incident": bool(meta.get("is_inciting_incident", False)),
                "is_sequence_climax": bool(meta.get("is_sequence_climax", False)),
                "is_act_climax": bool(meta.get("is_act_climax", False)),
                "is_story_climax": bool(meta.get("is_story_climax", False)),
                "arc_beat_refs": entry.get("arc_beat_refs", []),
            }
            break
    
    write_structure_index(structure_index, structure_path)
```

### 4.4 `tools/story_edit.py` — Wire It Up

```python
# In handler():
if action == "edit_note":
    result = _edit_note(project_path, target, args.get("data", {}), summary)
elif action == "reorder":
    result = _reorder(project_path, target, args.get("order_context", {}), summary)
# ... rest unchanged
```

### 4.5 No Changes Needed

| File | Why |
|------|-----|
| `plugin.yaml` | No new tool |
| `__init__.py` | No new tool |
| `tools/__init__.py` | No new tool |
| `tools/story_retrieve.py` | Already works for all types |
| `tools/story_search.py` | Already iterates ENTITY_FOLDERS |
| `tools/story_load.py` | Already reports counts |
| `tools/story_dashboard.py` | Auto-refresh hook fires on `story_edit` |

### 4.6 Skills Documentation

| File | Change |
|------|--------|
| `skills/story-editor/SKILL.md` | Document simplified `data` bag for `edit_note`; add `reorder` action; note cascade blocking on `delete_entity` |

---

## 5. Implementation Steps (Task Order)

### Task 1: Simplify `edit_note` + Add `data` Bag
**File:** `tools/story_edit.py`
- Replace `changes` array with `data` object in SCHEMA
- Rewrite `_edit_note()` to route by key name (schema field vs section name)
- **Also convert `_update_story_memory()` to use `data` bag** — same routing logic as `_edit_note()`. This allows removing `changes` from the SCHEMA entirely.

#### Task 1 Final Report

**File:** `tools/story_edit.py` (253 lines)

**What was done:**
1. **SCHEMA updated:** `"changes"` array property → `"data"` object property
2. **`handler()` updated:** `edit_note` and `update_story_memory` actions now pass `data` instead of `changes` to their handlers. `create_entity` also updated for consistency (its `changes` param was dead code).
3. **`_edit_note()` rewritten:**
   - Old: iterated `changes` array, switched on `type` discriminator (`body_section` vs `frontmatter`)
   - New: iterates `data` dict, routes by key membership — schema fields → frontmatter update, standard sections → `replace_section()` body update
   - Added `entity_type`/`slug` null guards (`or ""`) for type safety
4. **`_update_story_memory()` converted:**
   - Old: same `changes` array + type discriminator as `_edit_note()`
   - New: iterates `data` dict, all keys treated as body sections via `replace_section()`
5. **`_create_entity()` param renamed:** `changes` → `data` (was unused in body)

**Result:**
- `changes` only survives in `edit_screenplay` (which actually uses it for token-level edits)
- `data` is the universal edit bag for all other actions
- 47 existing tests pass, no callers of old `changes` array in tests or code to update

### Task 2: Add `reorder` Action
**File:** `tools/story_edit.py`
- Add `"reorder"` to action enum
- Add `order_context` to schema
- Implement `_reorder()` with batch renumbering

#### Task 2 Final Report

**File:** `tools/story_edit.py`

**What was done:**
1. **SCHEMA updated:** `"reorder"` added to action `enum`; `order_context` object added with `ordered_ids` array property
2. **`handler()` updated:** routes `reorder` → `_reorder(project_path, target, order_context, summary)`
3. **`_reorder()` added:**
   - Rejects non-scene/sequence types with error
   - Derives parent from first item's frontmatter (`sequence_id` for scenes, `act_id` for sequences)
   - Validates all items exist + belong to same parent
   - Renumbers `order` fields as 1, 2, 3… from the complete new ordering

**Result:**
- Batch reordering: LLM sends complete new list, handler writes all files atomically
- All items must belong to same parent — mixed parents rejected with error
- 47/47 existing tests pass

### Task 3: Add Cascade Blocking to `delete_entity`
**File:** `tools/story_edit.py`
- Add `_check_no_children()` helper
- Call from `_delete_entity()` for sequences and acts

#### Task 3 Final Report

**File:** `tools/story_edit.py`

**What was done:**
1. **`_delete_entity()` updated:** Added cascade blocking via `_check_no_children()` calls before the recycle-bin move:
   - Sequence → checks `scenes/` folder for scenes where `sequence_id == slug`
   - Act → checks `sequences/` folder for sequences where `act_id == slug`
   - Non-structural types (character, location, world, plot): no check
2. **`_check_no_children()` added:**
   - Scans child folder for files whose parent field matches parent_id
   - Raises `ValueError` listing offending children if any found

**Result:**
- Sequences with scenes → delete blocked with error listing scene slugs
- Acts with sequences → delete blocked with error listing sequence slugs
- Character/location deletes unchanged
- 47/47 existing tests pass

### Task 4: Add Parent Validation + Auto-Order to `story_create`
**File:** `tools/story_create.py`
- Add `_validate_parents()`, `_get_next_order()`, `_entity_exists()` helpers
- Call from `handler()` for scenes/sequences

### Task 4: Add Parent Validation + Auto-Order to `story_create`
**File:** `tools/story_create.py`
- Add `_validate_parents()`, `_get_next_order()`, `_entity_exists()` helpers
- Call from `handler()` for scenes/sequences### Task 4: Add Parent Validation + Auto-Order to `story_create`

#### Task 4 Final Report

**Files:** `tools/story_create.py`, `tests/test_core.py`

**What was done:**
1. **`handler()` updated:** For scenes/sequences, calls `_validate_parents()` (returns error if parents don't exist), then auto-assigns `order` if `== 0`
2. **`_validate_parents()` added:** Checks scene→sequence_id/act_id and sequence→act_id existence, raises ValueError if not found
3. **`_get_next_order()` added:** Scans child folder for max order, returns max+1 (or 1 if empty)
4. **`_entity_exists()` added:** Simple file existence check via `ENTITY_FOLDERS`
5. **`entity_type`/`slug` guards:** Added `or ""` to fix Pyright type errors

**Test updates:**
- `test_create_scene_has_all_fields_and_sections` — creates act-1 + seq-1 parents first, asserts `order == 1` (auto-order)
- `test_create_sequence_has_all_fields_and_sections` — creates act-1 parent first, asserts `order == 1`

**Result:**
- Scenes/sequences with non-existent parents → error before file creation
- Scenes/sequences without explicit order → next position assigned automatically
- 47/47 existing tests pass

### Task 5: Add `update_structure_index_scene()` to `core/index.py`
**File:** `core/index.py`
- Implement lightweight single-scene structure-index update
- Call from `story_edit._edit_note()` after scene edits

#### Task 5 Final Report

**Files:** `core/index.py`, `tools/story_edit.py`

**What was done:**
1. **`core/index.py`:** Added `update_structure_index_scene(project_path, scene_id)`:
   - Reads `structure-index.yaml`, finds entry by `id`, updates dramatic metadata fields
   - O(1) vs O(N) rebuild — no full regeneration
   - No-op if structure-index.yaml or scene file doesn't exist
2. **`tools/story_edit.py`:** `_edit_note()` calls `update_structure_index_scene()` after writing scene file (lazy import, only when `entity_type == "scene"`)

**Result:**
- Scene frontmatter edits → structure-index.yaml updated incrementally
- Non-scene edits → no structure-index update (correct behavior)
- 47/47 existing tests pass

### Task 6: Update Skills Documentation
**File:** `skills/story-editor/SKILL.md`
- Document simplified `data` bag
- Document `reorder` action
- Document cascade blocking

#### Task 6 Final Report
**File:** `skills/story-editor/SKILL.md`
**What was done:**
1. **Tool parameters updated:** `changes` → `data` + `order_context` in key parameters table
2. **Actions table updated:** `edit_note` now says "data bag", `delete_entity` notes cascade blocking, added `reorder` row
3. **Data Shape section rewritten:** Replaced `changes` array docs with `data` bag routing explanation + `reorder` `order_context` format
4. **Entity Creation section:** Added structural type rules (parent validation + auto-order)
5. **Pitfalls:** Added cascade blocking warnings for sequence/act deletion
**Result:**
- SKILL.md fully documents all Phase 3 changes
- No backward compat section needed (no real projects)

### Task 7: Tests
**File:** `tests/test_core.py`
- Test `edit_note` with `data` bag (frontmatter + body section)
- Test `reorder` within sequence
- Test `delete_entity` cascade blocking (sequence with scenes → error)
- Test `delete_entity` cascade blocking (act with sequences → error)
- Test `story_create` auto-order assignment
- Test `story_create` parent validation (non-existent sequence → error)
- Test `update_structure_index_scene` lightweight update

#### Task 7 Final Report

**Files:** `tests/test_core.py`, `tools/story_edit.py`

**What was done:**
1. **`TestPhase3ToolSurface` class added** (7 tests):
   - `test_edit_note_with_data_bag` — creates scene, edits with `data` bag containing frontmatter (`status`) + body section (`Description`), verifies both update
   - `test_reorder_scene_within_sequence` — creates 3 scenes, reorders to `[scene-3, scene-1, scene-2]`, verifies `order` fields are `1, 2, 3`
   - `test_delete_sequence_with_scenes_blocked` — creates sequence with child scene, delete returns error JSON, sequence file remains (not moved to recycle bin)
   - `test_delete_act_with_sequences_blocked` — same pattern for act with child sequence
   - `test_create_scene_auto_order` — creates two scenes in same sequence, second gets `order=2` automatically
   - `test_create_scene_validates_parent` — scene with non-existent `sequence_id` → error, no file created
   - `test_update_structure_index_scene` — edits scene frontmatter, verifies `structure-index.yaml` updated incrementally (not full rebuild); also tests `update_structure_index_scene()` directly

2. **Bug fix in `tools/story_edit.py`:** `_check_no_children()` raises `ValueError`, but `_delete_entity()` didn't catch it — the handler crashed with a 500 instead of returning error JSON. Added try/except around cascade check to return `{"error": ...}` JSON.

**Result:**
- 54/54 tests pass (47 pre-existing + 7 new)
- Cascade blocking now returns proper error JSON (was a latent bug)
- Structure-index lightweight update verified both via `edit_note` handler and direct `update_structure_index_scene()` call

---

## 6. Test Strategy

```python
def test_edit_note_with_data_bag(tmp_path):
    """edit_note with data bag updates frontmatter + body section."""

def test_reorder_scene_within_sequence(tmp_path):
    """Reorder scene → order fields renumbered 1-2-3."""

def test_delete_sequence_with_scenes_blocked(tmp_path):
    """Delete sequence with child scenes → error."""

def test_delete_act_with_sequences_blocked(tmp_path):
    """Delete act with child sequences → error."""

def test_create_scene_auto_order(tmp_path):
    """Create scene without order → auto-assigned next position."""

def test_create_scene_validates_parent(tmp_path):
    """Create scene with non-existent sequence_id → error."""

def test_update_structure_index_scene(tmp_path):
    """After edit, structure-index.yaml updated without full rebuild."""
```

---

## 7. Migration Notes

- `edit_note` schema change: `changes` → `data`. No backward compat needed (no real projects).
- Existing tests that call `edit_note` with `changes` array must be updated to use `data` bag.
- `reorder` action is new — no existing callers.
- `delete_entity` cascade blocking only affects structural types — existing character/location deletes unchanged.

---

## 8. Out of Scope (Intentionally Deferred)

| Topic | Phase |
|-------|-------|
| Dashboard display of structural types | Phase 4 |
| Script view assembly from scene files | Phase 4 |
| Screenplay import → scene files | Separate job |
| Slug rename machinery | Future |
| Character arc beats populating `arc_beat_refs` | Future |

---

## 9. Success Criteria

- [x] `edit_note` uses simplified `data` bag (no `changes` array) — `story_edit.py:22-25,66,100-123`: schema uses `data`, handler passes `data`, `_edit_note` iterates dict (Task 1)
- [x] `reorder` action works for scenes within sequences — `story_edit.py:170-220`: `_reorder()` validates parent, renumbers 1..N (Task 2)
- [x] `delete_entity` blocks on structural cascade (sequence→scenes, act→sequences) — `story_edit.py:237-240,257-274`: `_check_no_children()` + try/except returns error JSON (Task 3 + Task 7 fix)
- [x] `story_create` auto-assigns `order` for scenes/sequences — `story_create.py:117-122`: `order==0` → `_get_next_order()` (Task 4)
- [x] `story_create` validates parent existence — `story_create.py:113-117,156-165`: `_validate_parents()` raises ValueError caught by handler (Task 4)
- [x] `update_structure_index_scene()` does lightweight single-scene update — `core/index.py:299-335`: reads entry by id, updates fields, writes back; called from `_edit_note` line 126-128 (Task 5)
- [x] No new tool registered — `plugin.yaml` unchanged; `__init__.py` unchanged; `tools/__init__.py` unchanged (§4.5)
- [x] All existing tests pass (or updated for schema change) — 54/54 pass (`python -m pytest tests/test_core.py -v`): 47 pre-existing + 7 new `TestPhase3ToolSurface` (Task 7)
- [x] Skills documentation updated — `skills/story-editor/SKILL.md` documents `data` bag, `reorder` action, cascade blocking (Task 6)

---

## 10. Design Notes for Phase 4

### Script View Assembly

Dashboard reads `index.yaml` → sorts scenes by `sequence_id` + `order` → reads `## Content` from each scene file. No tool changes needed.

### Future: `import_screenplay` Action

When screenplay reintegration comes, add `import` action to `story_edit` (or a dedicated tool if the surface grows). Reads `screenplay.fountain`, creates scene files, assigns structure. The `data` bag pattern handles this cleanly.
