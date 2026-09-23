# Task 1.1: Relationship Entity Schema

## Goal
Add `relationship` as a first-class entity type with full schema definition.

## Steps

### 1.1.1: Add `relationship` entity schema to `ENTITY_SCHEMAS`
- **File**: `core/constants.py`
- **Action**: Add new entity type `"relationship"` to `ENTITY_SCHEMAS` dict (after `arc_beat`)
- **Schema**:
```python
"relationship": {
    "name": {"type": "string", "default": "", "optional": False, "description": "Display name (e.g. 'Kael & Mira')"},
    "type": {"type": "string", "default": "relationship", "optional": False, "description": "Always 'relationship'"},
    "characters": {"type": "list", "default": [], "optional": False, "description": "Exactly two character slugs"},
    "perspectives": {"type": "object", "default": {}, "optional": False, "description": "Per-character relationship view", "sub_fields": {
        "label": {"type": "string", "description": "Relationship label from this character's POV"},
        "feeling": {"type": "string", "description": "Emotional stance"},
        "type": {"type": "string", "description": "Category: ally/enemy/family/romantic/professional/mentor/rival/custom"},
        "strength": {"type": "number", "description": "Intensity -1.0 to 1.0"},
        "secret": {"type": "boolean", "description": "Hidden from other character"},
    }},
    "scenes": {"type": "list", "default": [], "optional": True, "description": "Scenes where this relationship is featured"},
    "status": {"type": "string", "default": "active", "optional": True, "description": "active/resolved/complex"},
    "history": {"type": "string", "default": "", "optional": True, "description": "How this relationship evolved"},
}
```

### 1.1.2: Update character `relationships` field to computed
- **File**: `core/constants.py`
- **Action**: Replace existing `relationships` field in `ENTITY_SCHEMAS["character"]` (line 52):
```python
"relationships": {
    "type": "list", "default": [], "optional": True, "computed": True,
    "description": "Computed summary of relationship entities (read-only, derived from relationships/)"
},
```

### 1.1.3: Add `arc_beats_list` as computed field on character
- **File**: `core/constants.py`
- **Action**: Add to `ENTITY_SCHEMAS["character"]`:
```python
"arc_beats_list": {
    "type": "list", "default": [], "optional": True, "computed": True,
    "description": "Computed list of arc beats for this character (read-only, derived from arc_beat entities)"
},
```
- **Note**: `arc_beats_list` is currently implicit (only in `db.py:822-842`), not in schema

### 1.1.4: Add `"relationship"` to `ENTITY_LABELS`
- **File**: `core/constants.py`
- **Action**: Add `"relationship": "Relationship"` to `ENTITY_LABELS` dict (line 31-41)

### 1.1.5: Add `"relationship"` to `REQUIRED_FIELDS`
- **File**: `core/constants.py`
- **Action**: Add `"relationship": ["name", "characters", "perspectives"]` to `REQUIRED_FIELDS` dict (line 19-29)

## Verification
```bash
cd /media/theww/AI/Projects/Plugins/Hermes/hermes-story-architect
python -c "from core.constants import ENTITY_SCHEMAS; print('relationship' in ENTITY_SCHEMAS); print(ENTITY_SCHEMAS['relationship']['name'])"
```

## Checklist
- [ ] `relationship` entity schema added to `ENTITY_SCHEMAS`
- [ ] Character `relationships` field marked as `computed: True`
- [ ] `arc_beats_list` added as computed field on character
- [ ] `ENTITY_LABELS` includes `"relationship"`
- [ ] `REQUIRED_FIELDS` includes `"relationship"`
- [ ] Import check passes
