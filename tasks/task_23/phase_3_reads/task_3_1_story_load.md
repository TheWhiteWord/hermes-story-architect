# Task 3.1: Read Paths — story_load

## Goal
Update `story_load` to expose relationship entities and computed character relationship summaries.

## Steps

### 3.1.1: Build relationship entities from DB rows
- **File**: `core/db.py`
- **Location**: `get_project_summary()`, in the entity organization loop (around lines 215-275)
- **Action**: Add `relationship` entity handling:
```python
elif etype == "relationship":
    relationships[eid] = {
        "id": eid, "name": name, "status": status,
        "characters": extra.get("characters", []),
        "perspectives": extra.get("perspectives", {}),
        "scenes": extra.get("scenes", []),
        "history": extra.get("history", ""),
    }
```
- **Note**: Must initialize `relationships = {}` dict before the loop

### 3.1.2: Build computed character relationship summary
- **File**: `core/db.py`
- **Location**: After the entity loop, before character output building
- **Action**: Add:
```python
# Computed summary on characters (follows CONVENTION_computed_fields)
char_rel_summary = {}
for rel in relationships.values():
    for char_id in rel["characters"]:
        other_id = [c for c in rel["characters"] if c != char_id][0]
        p = rel["perspectives"].get(char_id, {})
        char_rel_summary.setdefault(char_id, []).append({
            "with": other_id,
            "label": p.get("label", ""),
            "type": p.get("type", ""),
        })
```

### 3.1.3: Add `relationships` to character output in `_build_character`
- **File**: `core/db.py`
- **Location**: `_build_character()` function (lines 367-381)
- **Action**: Add to result dict:
```python
result = {
    # ... existing fields ...
    "rel": char_rels.get(char_id, []),
    "relationships": char_rel_summary.get(char_id, []),
}
```
- **Note**: Keep `rel` for backward compatibility during transition — will remove in Phase 4

### 3.1.4: Add `relationships` to top-level load result
- **File**: `core/db.py`
- **Location**: `result` dict in `get_project_summary()` (lines 492-505)
- **Action**: Add:
```python
result = {
    # ... existing fields ...
    "relationships": relationships,
}
```

## Verification
```bash
cd /media/theww/AI/Projects/Plugins/Hermes/hermes-story-architect
python -c "from core.db import get_project_summary; print('OK')"
```

## Checklist
- [x] Relationship entities built from DB rows
- [x] Computed character relationship summary
- [x] `relationships` field added to character output
- [x] Top-level `relationships` dict in load result
- [x] Import check passes

## Completion Brief

All 4 steps implemented in `core/db.py` (`get_project_summary`):

1. **Relationship entities** (line ~215): Added `relationships = {}` dict and `elif etype == "relationship"` branch in the entity organization loop. Extracts `characters`, `perspectives`, `scenes`, `history` from `extra` JSON.

2. **Computed summary** (line ~372): Added `char_rel_summary` dict built after the entity loop. Iterates relationships, for each character in a relationship, finds the other character and pulls `label`/`type` from their perspective. Used `others[0]` instead of list comprehension indexing for clarity.

3. **Character output** (line ~399): Added `"relationships": char_rel_summary.get(char_id, [])` to `_build_character` result. Added `"relationships": []` to `_omit` defaults. Kept `rel` for backward compat (Phase 4 removes it).

4. **Top-level output** (line ~521): Added `"relationships": relationships` to the `result` dict.

Import check passes. No behavioral change for projects without relationship entities (empty dict, empty summaries).
