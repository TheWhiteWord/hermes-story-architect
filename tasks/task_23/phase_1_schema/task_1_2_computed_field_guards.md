# Task 1.2: Computed Field Guards

## Goal
Enforce `computed: True` marker across create, edit, describe, and export tools so computed fields are read-only.

## Steps

### 1.2.1: Guard in `story_create.py`
- **File**: `tools/story_create.py`
- **Location**: Line 114, the merge dict comprehension
- **Action**: Skip computed fields:
```python
# Before:
merged = {field: frontmatter_data.get(field, meta["default"]) for field, meta in schema.items()}

# After:
merged = {field: frontmatter_data.get(field, meta["default"]) for field, meta in schema.items() if not meta.get("computed")}
```

### 1.2.2: Guard in `story_edit.py`
- **File**: `tools/story_edit.py`
- **Location**: Lines 149-157, the `for key, value in data.items()` loop
- **Action**: Add computed field check:
```python
for key, value in data.items():
    if key in _FIELDS_TO_SKIP:
        continue
    field_meta = schema.get(key, {})
    if field_meta.get("computed"):
        continue  # Read-only field — derived from other entities
    if key in standard_sections:
        section_updates[key] = value
    elif key in column_map:
        column_updates[column_map[key]] = value
    else:
        extra_updates[key] = value
```
- **Note**: `story_edit.py` does NOT import `ENTITY_SCHEMAS` directly — it uses its own `_ENTITY_COLUMN_MAP`. Need to import `ENTITY_SCHEMAS` or hardcode the computed fields check.

### 1.2.3: Marker in `story_describe.py`
- **File**: `tools/story_describe.py`
- **Location**: `_all_fields()` function (lines 6-21) and the entity schema output (lines 211-235)
- **Action**: In `_all_fields()`, propagate computed marker:
```python
all_fields[field] = {
    "type": meta["type"],
    "description": meta["description"],
    "default": meta["default"],
    "optional": meta.get("optional", True),
    "_entity_types": [entity_type],
}
if meta.get("computed"):
    all_fields[field]["computed"] = True
```
- **Action**: In `handler()`, entity schema output (lines 211-235), add computed marker:
```python
if meta.get("computed"):
    field_schema["computed"] = True
    field_schema["description"] += " (read-only, computed)"
```

### 1.2.4: Strip in `story_export.py`
- **File**: `tools/story_export.py`
- **Location**: `_frontmatter_for()` function (lines 118-206)
- **Action**: For character entity type, strip computed fields from extra before building frontmatter:
```python
# In the character branch (lines 129-133), add:
if entity_type == "character":
    fm["name"] = name
    fm["one_sentence"] = one_sentence
    # Strip computed fields — they are derived at read time
    extra = {k: v for k, v in extra.items() if not ENTITY_SCHEMAS.get("character", {}).get(k, {}).get("computed")}
    fm.update(extra)
    return fm
```
- **Note**: Need to import `ENTITY_SCHEMAS` in `story_export.py`

## Verification
```bash
cd /media/theww/AI/Projects/Plugins/Hermes/hermes-story-architect
python -c "from tools.story_create import handler; from tools.story_edit import handler; from tools.story_describe import handler; from tools.story_export import handler; print('All imports OK')"
```

## Checklist
- [ ] `story_create.py` skips computed fields in merge
- [ ] `story_edit.py` skips computed fields in update loop
- [ ] `story_describe.py` marks computed fields in output
- [ ] `story_export.py` strips computed fields from extra
- [ ] All imports pass
