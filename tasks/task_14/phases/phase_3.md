# Phase 3: Tools — Create, Edit, Retrieve Arc Beats

## Prerequisite

Phase 1 + Phase 2 complete. Constants, schema, index derivation, and `core/paths.py` exist.

## Files to modify

| File | Change |
|------|--------|
| `tools/story_create.py` | Add `arc` to `_get_standard_sections()` |
| `tools/story_create.py` | Use `build_entity_path()` for path construction |
| `tools/story_create.py` | Add parent validation for arc (character exists, scene exists) |
| `tools/story_edit.py` | Add `arc` to `target.entity_type` enum |
| `tools/story_edit.py` | Use `find_entity_path()` for path resolution |
| `tools/story_retrieve.py` | Add `arc` to `entity_type` enum |
| `tools/story_retrieve.py` | Use `find_entity_path()` for path resolution |
| `tools/story_load.py` | Add arc count to confirmation string |

## Key Design Decision: Centralized Path Logic

All path construction and resolution goes through `core/paths.py`:
- `build_entity_path(project_path, type, slug, frontmatter)` — builds path for any entity type
- `find_entity_path(project_path, type, slug)` — finds existing file for any entity type

No inline `if entity_type == "arc"` in any tool. The nested-vs-flat logic lives in one place.

## Step-by-step

### Step 3.1 — `story_create.py`: Add arc sections

In `_get_standard_sections()`, add:
```python
"arc": ["Action", "Gap", "Choice", "Shift", "Development Log"],
```

### Step 3.2 — `story_create.py`: Use `build_entity_path()`

Replace the existing path construction (around line 102-103):
```python
# OLD:
folder = ENTITY_FOLDERS[entity_type]
file_path = project_path / folder / f"{slug}.md"

# NEW:
from core.paths import build_entity_path
file_path = build_entity_path(project_path, entity_type, slug, frontmatter_data)
```

The `build_entity_path()` function handles both flat and nested paths automatically.

### Step 3.3 — `story_create.py`: Add arc parent validation

After the existing parent validation block (line 113-122), add:
```python
if entity_type == "arc":
    if frontmatter_data.get("character") and not _entity_exists(project_path, "character", frontmatter_data["character"]):
        raise ValueError(f"Character not found: {frontmatter_data['character']}")
    if frontmatter_data.get("scene") and not _entity_exists(project_path, "scene", frontmatter_data["scene"]):
        raise ValueError(f"Scene not found: {frontmatter_data['scene']}")
```

### Step 3.4 — `story_edit.py`: Add arc to enum

In `SCHEMA > properties > target > properties > entity_type > enum`, add `"arc"`.

### Step 3.5 — `story_edit.py`: Use `find_entity_path()`

Replace the existing path construction in `_edit_note()` (around line 102-103):
```python
# OLD:
folder = ENTITY_FOLDERS.get(entity_type, "")
file_path = project_path / folder / f"{slug}.md"

# NEW:
from core.paths import find_entity_path
file_path = find_entity_path(project_path, entity_type, slug)
if not file_path:
    return json.dumps({"error": f"Entity not found: {entity_type}/{slug}"})
```

### Step 3.6 — `story_retrieve.py`: Add arc to enum

In `SCHEMA > properties > entity_type > enum`, add `"arc"`.

### Step 3.7 — `story_retrieve.py`: Use `find_entity_path()`

Replace the existing path construction in `handler()` (around line 53-57):
```python
# OLD:
folder = ENTITY_FOLDERS[entity_type]
if entity_type == "project":
    file_path = project_path / "project.md"
else:
    file_path = project_path / folder / f"{slug}.md"

# NEW:
from core.paths import find_entity_path
if entity_type == "project":
    file_path = project_path / "project.md"
else:
    file_path = find_entity_path(project_path, entity_type, slug)
    if not file_path:
        return json.dumps({"error": f"Entity not found: {entity_type}/{slug}"})
```

### Step 3.8 — `story_load.py`: Add arc count to confirmation

Update the confirmation string (line 44-52) to include arcs:
```python
confirmation = (
    f"Loaded {index['project']['name']} — "
    f"{len(index.get('arcs', []))} arc beats, "
    f"{len(index.get('scenes', []))} scenes, "
    ...
)
```

## Legacy cleanup

None — additive only.

## Naming convention check

- Arc sections: `Action`, `Gap`, `Choice`, `Shift`, `Development Log` (matches plan)
- Path pattern: `arcs/{character}/{beat_id}.md` (handled by `core/paths.py`)
- No existing arc tool code to clean up

## Final checklist (unmarked)

- [ ] `story_create.py`: arc sections added to `_get_standard_sections()`
- [ ] `story_create.py`: uses `build_entity_path()` for path construction
- [ ] `story_create.py`: arc validates character exists
- [ ] `story_create.py`: arc validates scene exists
- [ ] `story_edit.py`: arc added to target enum
- [ ] `story_edit.py`: uses `find_entity_path()` for path resolution
- [ ] `story_retrieve.py`: arc added to entity_type enum
- [ ] `story_retrieve.py`: uses `find_entity_path()` for path resolution
- [ ] `story_load.py`: arc count in confirmation string
- [ ] Tests added to `test_arcs.py` for create/edit/retrieve
- [ ] `pytest tests/test_arcs.py` passes
- [ ] Existing `test_core.py` tests still pass
