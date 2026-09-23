# Task 2.1: CRUD Enum & Folder Updates

## Goal
Add `"relationship"` to all CRUD tool enums and import/export folder mappings.

## Steps

### 2.1.1: Add to `story_create.py` entity_type enum
- **File**: `tools/story_create.py`
- **Location**: Line 51, the `enum` list in `_build_schema()`
- **Action**: Add `"relationship"` to the enum list:
```python
"enum": ["project", "character", "location", "world", "plot", "scene", "sequence", "act", "arc_beat", "relationship"],
```
- **Note**: The handler is fully generic — `relations_for_insert("relationship", ...)` returns `[]`, so all data lives in `extra` JSON. No additional handler code needed.

### 2.1.2: Add to `story_edit.py` entity_type enum
- **File**: `tools/story_edit.py`
- **Location**: Line 19, the `enum` list in `SCHEMA`
- **Action**: Add `"relationship"` to the enum list:
```python
"enum": ["character", "location", "world", "plot", "scene", "sequence", "act", "arc_beat", "relationship"],
```
- **Note**: The generic handler works — updates extra JSON via the `else` branch in `_edit_note_db`

### 2.1.3: Add to `story_import.py`
- **File**: `tools/story_import.py`
- **Location**: `_import_all()` function, around line 70
- **Action**: Add import call:
```python
_import_folder(conn, project_path, "relationships", "relationship")
```
- **Note**: Uses the generic `_import_folder` — no special handling needed

### 2.1.4: Add to `story_export.py`
- **File**: `tools/story_export.py`
- **Location**: `_folder_for()` function (lines 209-218)
- **Action**: Add to the dict:
```python
"relationship": "relationships",
```
- **Also**: Add a `"relationship"` case in `_frontmatter_for()` (lines 118-206):
```python
if entity_type == "relationship":
    fm["name"] = name
    if status:
        fm["status"] = status
    fm.update(extra)
    return fm
```

### 2.1.5: Add to `story_retrieve.py` entity_type enum
- **File**: `tools/story_retrieve.py`
- **Location**: Line 14, the `enum` list in `SCHEMA`
- **Action**: Add `"relationship"`:
```python
"enum": ["character", "location", "world", "plot", "project", "scene", "sequence", "act", "arc_beat", "relationship"],
```
- **Note**: The generic handler works — reads sections by entity_id

### 2.1.6: Add `"relationship"` to `story_describe.py` enums
- **File**: `tools/story_describe.py`
- **Location**: Multiple `enum` lists (lines 35, 83, 185)
- **Action**: Add `"relationship"` to all three enum lists
- **Note**: These use `list(ENTITY_SCHEMAS.keys())` so they may auto-update, but verify

## Verification
```bash
cd /media/theww/AI/Projects/Plugins/Hermes/hermes-story-architect
python -c "
from tools.story_create import SCHEMA
from tools.story_edit import SCHEMA as EDIT_SCHEMA
from tools.story_retrieve import SCHEMA as RETRIEVE_SCHEMA
print('create:', 'relationship' in SCHEMA['properties']['entity_type']['enum'])
print('edit:', 'relationship' in EDIT_SCHEMA['properties']['target']['properties']['entity_type']['enum'])
print('retrieve:', 'relationship' in RETRIEVE_SCHEMA['properties']['entity_type']['enum'])
"
```

## Checklist
- [ ] `story_create.py` enum includes `"relationship"`
- [ ] `story_edit.py` enum includes `"relationship"`
- [ ] `story_import.py` imports relationships folder
- [ ] `story_export.py` exports relationships folder
- [ ] `story_retrieve.py` enum includes `"relationship"`
- [ ] `story_describe.py` enums include `"relationship"`
- [ ] All imports pass
