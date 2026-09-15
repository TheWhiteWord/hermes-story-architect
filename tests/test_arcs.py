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
        assert any("order" in w for w in warnings)

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
