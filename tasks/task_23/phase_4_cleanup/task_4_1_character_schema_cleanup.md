# Task 4.1: Character Schema Cleanup

## Goal
Remove old relationship handling from character processing in `get_project_summary`.

## Context
The old system stores relationships as `character_relationship` relations (via `relations_for_insert` in `entity.py:146`). The `get_project_summary` function in `db.py` reads these into `char_rels` dict (line 177) and exposes them as `char["rel"]` (line 378). The new system uses `relationship` entities with a computed `relationships` field on characters.

## Steps

### 4.1.1: Remove `char_rels` construction from `get_project_summary`
- **File**: `core/db.py`
- **Location**: Lines 177, 186-195
- **Action**: Remove `char_rels = {}` initialization and the `character_relationship` branch in the relations loop:
```python
# REMOVE these lines from the relations loop:
elif kind == "character_relationship":
    try:
        parsed = json.loads(note) if note else {}
    except (json.JSONDecodeError, TypeError):
        parsed = {}
    char_rels.setdefault(from_id, []).append({
        "id": to_id,
        "label": parsed.get("label", ""),
        "feeling": parsed.get("feeling", ""),
    })
```
- **Also remove**: `char_rels = {}` from line 177

### 4.1.2: Remove `rel` from `_build_character` in `get_project_summary`
- **File**: `core/db.py`
- **Location**: Lines 378, 380-381
- **Action**: Remove `"rel": char_rels.get(char_id, []),` from the result dict
- **Action**: Remove `"rel": []` from the `_omit` defaults

### 4.1.3: Remove `character_relationship` from `_RELATION_FIELDS`
- **File**: `core/entity.py`
- **Location**: Line 146
- **Action**: Remove `"character": {"relationships": ("character_relationship", True)},` from `_RELATION_FIELDS`
- **Note**: This means `relations_for_insert("character", ...)` no longer creates relationship relation rows

### 4.1.4: Remove `relationships` from `_extra_for` skip set in `story_import.py`
- **File**: `tools/story_import.py`
- **Location**: Line 252
- **Action**: Remove `"relationships"` from the character skip set:
```python
# Before:
"character": {"name", "one_sentence", "id", "relationships"},
# After:
"character": {"name", "one_sentence", "id"},
```
- **Note**: The old import path put `relationships` into extra JSON; the new system stores them in `relationship` entities instead

### 4.1.5: Remove `character_relationship` handling from `story_export.py`
- **File**: `tools/story_export.py`
- **Location**: Lines 64-81 (the `if entity_type == "character":` branch in `_export_all`)
- **Action**: Remove the entire character relationship denormalization block
- **Note**: The new export writes `relationship` entities from their own folder, not from character relations

### 4.1.6: Remove `character_relationship` handling from `story_edit.py`
- **File**: `tools/story_edit.py`
- **Location**: Lines 179-211 (the relation update block in `_edit_note_db`)
- **Action**: This block iterates `_RELATION_FIELDS` — since we removed `character` from `_RELATION_FIELDS` in 4.1.3, this block will naturally skip character relationships. No direct edit needed.

## Verification
```bash
cd /media/theww/AI/Projects/Plugins/Hermes/hermes-story-architect
python -c "from core.entity import _RELATION_FIELDS; print('character' not in _RELATION_FIELDS or 'relationships' not in _RELATION_FIELDS.get('character', {}))"
```

## Cleanup Checklist
- [x] `char_rels` removed from `get_project_summary`
- [x] `rel` field removed from character output in load
- [x] `character_relationship` removed from `_RELATION_FIELDS`
- [x] `relationships` removed from import skip set
- [x] Character relationship denormalization removed from export
- [x] No references to `char_rels` remain in `db.py`
- [x] No references to `character_relationship` remain in entity.py

## Notes
- The `## Relationships` body section on characters remains as a standard section — it's prose, not structured data
- The `relationships` field on character is now computed (Phase 1.2), so no explicit removal needed — the convention handles it
- The old `character_relationship` relation kind may still exist in DBs created before this change — that's fine, the new code simply won't read or write it

## Completion Summary

All tasks completed. Changes made:

1. **`core/db.py`**: Removed `char_rels = {}` initialization and the `character_relationship` branch from `get_project_summary`'s relations loop. Removed `"rel"` from `_build_character` result dict and `_omit` defaults. Removed stale `character_relationship` denormalization from `get_dashboard_data` (was overwriting the correct computed summary).

2. **`core/entity.py`**: Removed `"character": {"relationships": ("character_relationship", True)}` from `_RELATION_FIELDS`. Removed dead `character_relationship` branch in `relations_for_insert`.

3. **`tools/story_import.py`**: Removed `"relationships"` from character skip set in `_extra_for`. Removed dead `character` relationship insertion block from `_insert_relations`.

4. **`tools/story_export.py`**: Removed character relationship denormalization block from `_export_all`.

**Verification**: No references to `char_rels`, `character_relationship`, or `"rel"` field remain in `db.py`, `entity.py`, `story_import.py`, `story_export.py`, or `story_edit.py`. The `relationships` field on characters is now fully handled by the computed field convention (Phase 1.2).
