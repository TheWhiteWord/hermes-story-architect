# Task 1.3: Validation & Column Mapping

## Goal
Add relationship validation rules and DB column/relation mapping.

## Steps

### 1.3.1: Add relationship validation to `validate_entity()`
- **File**: `core/entity.py`
- **Location**: After the `arc_beat` validation block (around line 88)
- **Action**: Add validation for relationship entity:
```python
if entity_type == "relationship":
    chars = frontmatter.get("characters", [])
    if len(chars) != 2:
        warnings.append(f"relationship requires exactly 2 characters, got {len(chars)}")
    perspectives = frontmatter.get("perspectives", {})
    for char in chars:
        if char not in perspectives:
            warnings.append(f"Missing perspective for character: {char}")
    for char, p in perspectives.items():
        if "strength" in p and isinstance(p["strength"], (int, float)):
            if not (-1.0 <= float(p["strength"]) <= 1.0):
                warnings.append(f"strength out of range for {char}: {p['strength']}")
```

### 1.3.2: Add column mapping for relationship
- **File**: `core/entity.py`
- **Location**: `ENTITY_COLUMN_MAP` dict (lines 122-132)
- **Action**: Add:
```python
"relationship": {"name": "name", "type": "type", "status": "status"},
```

### 1.3.3: Add relation fields mapping for relationship
- **File**: `core/entity.py`
- **Location**: `_RELATION_FIELDS` dict (lines 138-150)
- **Action**: Add:
```python
"relationship": {},  # No relation fields — all data in extra JSON
```
- **Note**: This is critical — `relations_for_insert()` will return `[]` for relationship, so all data (characters, perspectives, scenes, history) goes into `extra` JSON via `columns_for_insert()`

### 1.3.4: Add standard sections for relationship
- **Files**: `core/entity.py` (`standard_sections` function, lines 169-183) AND `tools/story_create.py` (`_get_standard_sections` function, lines 306-319) AND `tools/story_edit.py` (`_get_standard_sections` function, lines 370-382)
- **Action**: Add to all three locations:
```python
"relationship": ["Description", "History", "Dynamics", "Scenes", "Notes"],
```

### 1.3.5: Add `"relationship"` to `story_edit.py` `_ENTITY_COLUMN_MAP`
- **File**: `tools/story_edit.py`
- **Location**: Lines 46-55
- **Action**: Add:
```python
"relationship": {"name": "name", "status": "status"},
```
- **Note**: `story_edit.py` has its own duplicate column map that must be kept in sync

## Verification
```bash
cd /media/theww/AI/Projects/Plugins/Hermes/hermes-story-architect
python -c "from core.entity import ENTITY_COLUMN_MAP, _RELATION_FIELDS, standard_sections; print('relationship' in ENTITY_COLUMN_MAP); print('relationship' in _RELATION_FIELDS); print('relationship' in standard_sections('relationship'))"
```

## Checklist
- [ ] Relationship validation in `validate_entity()`
- [ ] Column mapping for relationship
- [ ] Relation fields mapping (empty — all extra)
- [ ] Standard sections in all 3 files
- [ ] `story_edit.py` column map updated
- [ ] Import check passes
