# Phase 1: Data Layer — Constants & Entity Schema

## Files to modify

| File | Change |
|------|--------|
| `core/constants.py` | Add ARC_TYPES, arc REQUIRED_FIELDS, arc ENTITY_FOLDERS, arc ENTITY_LABELS, arc ENTITY_SCHEMAS |
| `core/constants.py` | Add arc_type + arc_value fields to `ENTITY_SCHEMAS["character"]` |
| `core/entity.py` | Add arc validation branch (y range, order numeric, arc_type enum) |
| `core/entity.py` | Add arc_type / arc_value enum validation on character entity |

## Files to create

| File | Purpose |
|------|---------|
| `core/paths.py` | Centralized path builder/resolver for flat + nested entities |
| `tests/test_arcs.py` | Tests for Phase 1 validation |

## Step-by-step

### Step 1.1 — Add ARC_TYPES and arc constants to `core/constants.py`

```python
# Add after VALUE_ARCS line:
ARC_TYPES = ["positive", "negative", "flat", "ironic", "absent"]
```

Add to `REQUIRED_FIELDS`:
```python
"arc": ["id", "character", "scene", "label", "action", "gap", "choice", "shift", "y", "order"],
```

Add to `ENTITY_FOLDERS`:
```python
"arc": "arcs",
```

Add to `ENTITY_LABELS`:
```python
"arc": "Arc Beat",
```

Add `NESTED_ENTITIES` dict (after `ENTITY_FOLDERS`):
```python
# Nested entities use {parent_field} in their path: folder/{parent}/{slug}.md
# Non-nested entities use flat paths: folder/{slug}.md
NESTED_ENTITIES = {
    "arc": "character",  # arcs/{character}/{beat_id}.md
}
```

Add to `ENTITY_SCHEMAS` (after `"act"` block):
```python
"arc": {
    "id": {"type": "string", "default": "", "optional": False, "description": "Beat slug (unique within character)"},
    "character": {"type": "string", "default": "", "optional": False, "description": "Character slug this beat belongs to"},
    "scene": {"type": "string", "default": "", "optional": False, "description": "Scene slug where this beat occurs"},
    "label": {"type": "string", "default": "", "optional": False, "description": "Human-readable label (e.g. 'First Doubt')"},
    "action": {"type": "string", "default": "", "optional": False, "description": "What the character does"},
    "gap": {"type": "string", "default": "", "optional": False, "description": "Expectation vs reality gap"},
    "choice": {"type": "string", "default": "", "optional": False, "description": "The choice the character makes"},
    "shift": {"type": "string", "default": "", "optional": False, "description": "Value shift (e.g. 'positive → mixed')"},
    "y": {"type": "number", "default": 0.0, "optional": False, "description": "Value charge (-1.0 to +1.0)"},
    "order": {"type": "number", "default": 0, "optional": False, "description": "Position within character's arc"},
    "is_crisis": {"type": "boolean", "default": False, "optional": True, "description": "Marks a crisis beat"},
    "is_climax": {"type": "boolean", "default": False, "optional": True, "description": "Marks a climax beat"},
},
```

Add to `ENTITY_SCHEMAS["character"]` (existing dict, append after `"knowledge"`):
```python
"arc_type": {"type": "string", "default": "absent", "optional": True, "description": "One of: positive, negative, flat, ironic, absent"},
"arc_value": {"type": "string", "default": "", "optional": True, "description": "Value at stake across this character's arc"},
"arc_value_at_open": {"type": "string", "default": "", "optional": True, "description": "Value charge at arc open (positive/negative/mixed/ironic)"},
"arc_value_at_close": {"type": "string", "default": "", "optional": True, "description": "Value charge at arc close (positive/negative/mixed/ironic)"},
"arc_complete": {"type": "boolean", "default": False, "optional": True, "description": "Whether this character's arc is complete"},
"arc_beat_count": {"type": "number", "default": 0, "optional": True, "description": "Number of arc beats (derived, overwritten by index)"},
```

### Step 1.2 — Create `core/paths.py`

New file with two functions that all tools use instead of inline path logic:

```python
"""Path builder/resolver — flat and nested entity paths."""
from pathlib import Path
from core.constants import ENTITY_FOLDERS, NESTED_ENTITIES


def build_entity_path(project_path: Path, entity_type: str, slug: str, frontmatter: dict = None) -> Path:
    """Build file path for any entity type.
    
    Nested entities (e.g. arc): project_path / folder / {parent_field} / {slug}.md
    Flat entities: project_path / folder / {slug}.md
    """
    folder = ENTITY_FOLDERS.get(entity_type, "")
    if entity_type in NESTED_ENTITIES:
        parent_id = (frontmatter or {}).get(NESTED_ENTITIES[entity_type], "")
        return project_path / folder / parent_id / f"{slug}.md"
    return project_path / folder / f"{slug}.md"


def find_entity_path(project_path: Path, entity_type: str, slug: str) -> Path | None:
    """Find existing file path for any entity type.
    
    For nested entities, searches subfolders. Returns None if not found.
    """
    folder = ENTITY_FOLDERS.get(entity_type, "")
    flat = project_path / folder / f"{slug}.md"
    if entity_type not in NESTED_ENTITIES:
        return flat if flat.exists() else None
    # Nested: check flat first (backwards compat), then search subfolders
    if flat.exists():
        return flat
    base = project_path / folder
    if not base.exists():
        return None
    for parent_dir in sorted(base.iterdir()):
        if parent_dir.is_dir() and not parent_dir.name.startswith("_") and not parent_dir.name.startswith("."):
            candidate = parent_dir / f"{slug}.md"
            if candidate.exists():
                return candidate
    return None
```

### Step 1.3 — Import ARC_TYPES in `core/entity.py`

Add to existing import block:
```python
VALUE_ARCS, ARC_TYPES,
```

### Step 1.4 — Add arc validation branch in `core/entity.py`

Add after the `entity_type == "act"` block (before `return warnings`):
```python
if entity_type == "arc":
    _validate_numeric(frontmatter, "y", warnings)
    _validate_numeric(frontmatter, "order", warnings)
    _validate_enum(frontmatter, "arc_type", ARC_TYPES, warnings, empty_ok=True)
    if "y" in frontmatter:
        y_val = frontmatter["y"]
        if isinstance(y_val, (int, float)) and not (-1.0 <= float(y_val) <= 1.0):
            warnings.append(f"y out of range: {y_val} (must be -1.0 to +1.0)")
```

### Step 1.5 — Add arc_type / arc_value enum validation on character

Add to existing character validation (inside `if entity_type == "character"` block, after story_role check):
```python
_validate_enum(frontmatter, "arc_type", ARC_TYPES, warnings, empty_ok=True)
_validate_enum(frontmatter, "arc_value_at_open", VALUE_CHARGES, warnings, empty_ok=True)
_validate_enum(frontmatter, "arc_value_at_close", VALUE_CHARGES, warnings, empty_ok=True)
```

### Step 1.6 — Tests: `tests/test_arcs.py`

Create with Phase 1 test classes:

```python
"""Tests for arc entity validation and path resolution (Phase 1)."""
import pytest
from pathlib import Path
from core.entity import validate_entity
from core.constants import ARC_TYPES, ENTITY_SCHEMAS, NESTED_ENTITIES
from core.paths import build_entity_path, find_entity_path


class TestArcValidation:
    def test_validate_arc_valid(self):
        fm = {
            "id": "beat-1", "character": "kael", "scene": "central-room-day",
            "label": "First Doubt", "action": "Kael questions the system",
            "gap": "Expected answers, got silence", "choice": "Pushes harder",
            "shift": "positive → mixed", "y": 0.5, "order": 1,
        }
        warnings = validate_entity("arc", fm)
        assert warnings == []

    def test_validate_arc_missing_required(self):
        warnings = validate_entity("arc", {"id": "beat-1"})
        assert any("character" in w for w in warnings)
        assert any("scene" in w for w in warnings)
        assert any("y" in w for w in warnings)

    def test_validate_arc_y_out_of_range(self):
        fm = {"id": "b1", "character": "k", "scene": "s", "label": "L",
              "action": "a", "gap": "g", "choice": "c", "shift": "s", "y": 2.0, "order": 1}
        warnings = validate_entity("arc", fm)
        assert any("y out of range" in w for w in warnings)

    def test_validate_arc_y_negative_ok(self):
        fm = {"id": "b1", "character": "k", "scene": "s", "label": "L",
              "action": "a", "gap": "g", "choice": "c", "shift": "s", "y": -1.0, "order": 1}
        warnings = validate_entity("arc", fm)
        assert not any("y out of range" in w for w in warnings)

    def test_validate_arc_order_not_numeric(self):
        fm = {"id": "b1", "character": "k", "scene": "s", "label": "L",
              "action": "a", "gap": "g", "choice": "c", "shift": "s", "y": 0.0, "order": "first"}
        warnings = validate_entity("arc", fm)
        assert any("order" in w and "must be a number" in w for w in warnings)

    def test_validate_character_arc_type_valid(self):
        warnings = validate_entity("character", {
            "name": "Test", "story_role": "Protagonist", "one_sentence": "X", "arc_type": "negative"
        })
        assert not any("Invalid arc_type" in w for w in warnings)

    def test_validate_character_arc_type_invalid(self):
        warnings = validate_entity("character", {
            "name": "Test", "story_role": "Protagonist", "one_sentence": "X", "arc_type": "invalid"
        })
        assert any("Invalid arc_type" in w for w in warnings)

    def test_validate_character_arc_value_enums(self):
        warnings = validate_entity("character", {
            "name": "T", "story_role": "Protagonist", "one_sentence": "X",
            "arc_value_at_open": "positive", "arc_value_at_close": "negative"
        })
        assert not any("Invalid" in w for w in warnings)

    def test_arc_schema_has_all_fields(self):
        arc_schema = ENTITY_SCHEMAS["arc"]
        assert "character" in arc_schema
        assert "scene" in arc_schema
        assert "y" in arc_schema
        assert "is_crisis" in arc_schema

    def test_character_schema_has_arc_fields(self):
        char_schema = ENTITY_SCHEMAS["character"]
        assert "arc_type" in char_schema
        assert "arc_value" in char_schema
        assert "arc_complete" in char_schema


class TestPathResolution:
    def test_build_flat_entity_path(self, tmp_path):
        path = build_entity_path(tmp_path, "character", "kael")
        assert path == tmp_path / "characters" / "kael.md"

    def test_build_nested_arc_path(self, tmp_path):
        path = build_entity_path(tmp_path, "arc", "1", {"character": "kael"})
        assert path == tmp_path / "arcs" / "kael" / "1.md"

    def test_find_flat_entity_path(self, tmp_path):
        (tmp_path / "characters").mkdir()
        (tmp_path / "characters" / "kael.md").write_text("test")
        path = find_entity_path(tmp_path, "character", "kael")
        assert path == tmp_path / "characters" / "kael.md"

    def test_find_nested_arc_path(self, tmp_path):
        (tmp_path / "arcs" / "kael").mkdir(parents=True)
        (tmp_path / "arcs" / "kael" / "1.md").write_text("test")
        path = find_entity_path(tmp_path, "arc", "1")
        assert path == tmp_path / "arcs" / "kael" / "1.md"

    def test_find_nonexistent_returns_none(self, tmp_path):
        path = find_entity_path(tmp_path, "arc", "999")
        assert path is None

    def test_nested_entities_constant(self):
        assert "arc" in NESTED_ENTITIES
        assert NESTED_ENTITIES["arc"] == "character"
```

## Legacy cleanup

None — this is additive only. No existing arc code to remove.

## Naming convention check

- `ARC_TYPES` (uppercase, matches `VALID_ROLES`, `VALUE_CHARGES` pattern)
- `arc_type` (lowercase, matches `value_arc`, `plot_type` pattern)
- `arc_value_at_open` / `arc_value_at_close` (matches `value_at_open` / `value_at_close` pattern on project)
- No existing arc field names to check against — this is a new entity



- [x] `ARC_TYPES` added to constants.py
- [x] `arc` added to `REQUIRED_FIELDS`
- [x] `arc` added to `ENTITY_FOLDERS`
- [x] `arc` added to `ENTITY_LABELS`
- [x] `arc` added to `ENTITY_SCHEMAS` with all fields
- [x] `arc_type` / `arc_value` / `arc_value_at_open` / `arc_value_at_close` / `arc_complete` added to character schema
- [x] `NESTED_ENTITIES` dict added to constants.py
- [x] `core/paths.py` created with `build_entity_path()` and `find_entity_path()`
- [x] `ARC_TYPES` imported in entity.py
- [x] Arc validation branch added to `validate_entity()`
- [x] Character arc field validation added
- [x] `test_arcs.py` created with `TestArcValidation` and `TestPathResolution` classes
- [x] `pytest tests/test_arcs.py` passes (16/16)
- [x] No existing tests broken (`pytest tests/test_core.py` — 73/73)

**Note:** Arc content fields (label, action, gap, choice, shift, y) are optional — allows beat shells to be created during scene planning, content filled later. Structural anchors only (id, character, scene, order) remain required.
