"""Tests for arc entity validation, path resolution (Phase 1), and index derivation (Phase 2)."""
import pytest
from pathlib import Path
from core.entity import validate_entity
from core.constants import ARC_TYPES, ENTITY_SCHEMAS, NESTED_ENTITIES
from core.paths import build_entity_path, find_entity_path
from core.index import generate_index, _parse_arcs, _enrich_characters_with_arcs, _enrich_scenes_with_arcs, _validate_index


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


# ─── Phase 2: Index Derivation Tests ───

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "save-the-children"


class TestParseArcs:
    def test_parse_arcs_returns_beats(self):
        arcs_folder = FIXTURE_PATH / "arcs"
        beats = _parse_arcs(arcs_folder)
        assert len(beats) == 3

    def test_parse_arcs_inherits_character_from_folder(self):
        arcs_folder = FIXTURE_PATH / "arcs"
        beats = _parse_arcs(arcs_folder)
        for beat in beats:
            assert beat["character"] == "dr-elena-voss"

    def test_parse_arcs_empty_folder(self, tmp_path):
        beats = _parse_arcs(tmp_path / "nonexistent")
        assert beats == []

    def test_parse_arcs_skips_hidden(self, tmp_path):
        arcs = tmp_path / "arcs" / "char"
        arcs.mkdir(parents=True)
        (arcs / "_hidden.md").write_text("---\nid: hidden\n---")
        (arcs / "1.md").write_text("---\nid: 1\n---")
        beats = _parse_arcs(tmp_path / "arcs")
        assert [str(b["id"]) for b in beats] == ["1"]


class TestEnrichCharactersWithArcs:
    def test_character_arc_beats_list(self, tmp_path):
        index = {
            "characters": [{"id": "kael"}, {"id": "mara"}],
            "arcs": [
                {"id": "1", "character": "kael", "label": "Beat 1", "scene": "s1", "y": 0.5, "order": 1, "is_crisis": False, "is_climax": False},
                {"id": "2", "character": "kael", "label": "Beat 2", "scene": "s2", "y": -0.3, "order": 2, "is_crisis": True, "is_climax": False},
                {"id": "3", "character": "mara", "label": "Beat A", "scene": "s3", "y": 0.0, "order": 1, "is_crisis": False, "is_climax": False},
            ],
        }
        _enrich_characters_with_arcs(index)
        kael = next(c for c in index["characters"] if c["id"] == "kael")
        assert len(kael["arc_beats_list"]) == 2
        assert kael["arc_beat_count"] == 2
        assert kael["arc_beats_list"][0]["id"] == "1"
        assert kael["arc_beats_list"][1]["id"] == "2"
        mara = next(c for c in index["characters"] if c["id"] == "mara")
        assert len(mara["arc_beats_list"]) == 1
        assert mara["arc_beat_count"] == 1

    def test_character_no_arcs(self, tmp_path):
        index = {"characters": [{"id": "kael"}], "arcs": []}
        _enrich_characters_with_arcs(index)
        assert index["characters"][0]["arc_beats_list"] == []
        assert index["characters"][0]["arc_beat_count"] == 0

    def test_beats_sorted_by_order(self):
        index = {
            "characters": [{"id": "kael"}],
            "arcs": [
                {"id": "3", "character": "kael", "label": "C", "scene": "", "y": 0.0, "order": 3, "is_crisis": False, "is_climax": False},
                {"id": "1", "character": "kael", "label": "A", "scene": "", "y": 0.0, "order": 1, "is_crisis": False, "is_climax": False},
                {"id": "2", "character": "kael", "label": "B", "scene": "", "y": 0.0, "order": 2, "is_crisis": False, "is_climax": False},
            ],
        }
        _enrich_characters_with_arcs(index)
        beats = index["characters"][0]["arc_beats_list"]
        assert [b["order"] for b in beats] == [1, 2, 3]

    def test_beat_lightweight_fields(self):
        index = {
            "characters": [{"id": "kael"}],
            "arcs": [
                {"id": "1", "character": "kael", "label": "Beat", "scene": "s1", "y": 0.5, "order": 1, "is_crisis": True, "is_climax": True, "extra": "should not appear"},
            ],
        }
        _enrich_characters_with_arcs(index)
        beat = index["characters"][0]["arc_beats_list"][0]
        assert set(beat.keys()) == {"id", "label", "scene", "y", "order", "is_crisis", "is_climax"}


class TestEnrichScenesWithArcs:
    def test_scene_arc_beats(self):
        index = {
            "scenes": [{"id": "scene-a"}, {"id": "scene-b"}],
            "arcs": [
                {"id": "1", "character": "kael", "scene": "scene-a", "label": "Beat 1", "y": 0.5, "order": 1, "is_crisis": False, "is_climax": False},
                {"id": "2", "character": "mara", "scene": "scene-a", "label": "Beat 2", "y": -0.2, "order": 1, "is_crisis": False, "is_climax": True},
                {"id": "3", "character": "kael", "scene": "scene-b", "label": "Beat 3", "y": 0.0, "order": 2, "is_crisis": False, "is_climax": False},
            ],
        }
        _enrich_scenes_with_arcs(index)
        scene_a = next(s for s in index["scenes"] if s["id"] == "scene-a")
        assert len(scene_a["arc_beats"]) == 2
        assert scene_a["arc_beats"][0]["character"] == "kael"
        assert scene_a["arc_beats"][0]["beat_id"] == "1"
        assert scene_a["arc_beats"][1]["character"] == "mara"
        scene_b = next(s for s in index["scenes"] if s["id"] == "scene-b")
        assert len(scene_b["arc_beats"]) == 1

    def test_scene_without_arc_beats(self):
        index = {"scenes": [{"id": "lonely"}], "arcs": []}
        _enrich_scenes_with_arcs(index)
        assert "arc_beats" not in index["scenes"][0]

    def test_arc_beats_not_set_when_empty(self):
        index = {"scenes": [{"id": "s1"}], "arcs": [{"id": "1", "character": "k", "scene": "other", "label": "", "y": 0, "order": 1}]}
        _enrich_scenes_with_arcs(index)
        assert "arc_beats" not in index["scenes"][0]


class TestFullIndexArcIntegration:
    def test_index_includes_arcs(self):
        index = generate_index(FIXTURE_PATH)
        assert "arcs" in index
        assert len(index["arcs"]) == 3

    def test_index_character_arc_beats_list(self):
        index = generate_index(FIXTURE_PATH)
        elena = next(c for c in index["characters"] if c["id"] == "dr-elena-voss")
        assert "arc_beats_list" in elena
        assert len(elena["arc_beats_list"]) == 3
        assert elena["arc_beat_count"] == 3
        for beat in elena["arc_beats_list"]:
            assert "action" not in beat  # lightweight — only graph fields

    def test_index_character_without_arcs_empty(self):
        index = generate_index(FIXTURE_PATH)
        marcus = next(c for c in index["characters"] if c["id"] == "marcus-chen")
        assert "arc_beats_list" in marcus
        assert marcus["arc_beats_list"] == []
        assert marcus["arc_beat_count"] == 0

    def test_index_scene_arc_beats(self):
        index = generate_index(FIXTURE_PATH)
        central_day = next((s for s in index["scenes"] if s["id"] == "central-room-day"), None)
        assert central_day is not None
        assert "arc_beats" in central_day
        assert len(central_day["arc_beats"]) == 1
        assert central_day["arc_beats"][0]["character"] == "dr-elena-voss"

    def test_project_arc_count(self):
        index = generate_index(FIXTURE_PATH)
        assert index["project"]["arc_count"] == 3


class TestArcValidationWarnings:
    def test_unknown_character_warns(self, tmp_path, capsys):
        index = {
            "project": {},
            "characters": [{"id": "kael"}],
            "locations": [],
            "worlds": [],
            "plots": [],
            "acts": [],
            "sequences": [],
            "scenes": [{"id": "s1"}],
            "arcs": [{"id": "1", "character": "ghost", "scene": "s1", "label": "", "y": 0, "order": 1}],
        }
        _enrich_characters_with_arcs(index)
        _enrich_scenes_with_arcs(index)
        import io
        from contextlib import redirect_stdout
        f = io.StringIO()
        with redirect_stdout(f):
            _validate_index(index)
        output = f.getvalue()
        assert "unknown character ghost" in output

    def test_unknown_scene_warns(self, tmp_path):
        import io
        from contextlib import redirect_stdout
        index = {
            "project": {},
            "characters": [{"id": "k"}],
            "locations": [],
            "worlds": [],
            "plots": [],
            "acts": [],
            "sequences": [],
            "scenes": [{"id": "s1"}],
            "arcs": [{"id": "1", "character": "k", "scene": "nonexistent", "label": "", "y": 0, "order": 1}],
        }
        f = io.StringIO()
        with redirect_stdout(f):
            _validate_index(index)
        output = f.getvalue()
        assert "unknown scene nonexistent" in output

    def test_y_out_of_range_warns(self):
        import io
        from contextlib import redirect_stdout
        index = {
            "project": {},
            "characters": [{"id": "k"}],
            "locations": [],
            "worlds": [],
            "plots": [],
            "acts": [],
            "sequences": [],
            "scenes": [{"id": "s1"}],
            "arcs": [{"id": "1", "character": "k", "scene": "s1", "label": "", "y": 2.0, "order": 1}],
        }
        f = io.StringIO()
        with redirect_stdout(f):
            _validate_index(index)
        output = f.getvalue()
        assert "y out of range" in output

    def test_no_warnings_for_valid_arc(self):
        import io
        from contextlib import redirect_stdout
        index = {
            "project": {},
            "characters": [{"id": "k"}],
            "locations": [],
            "worlds": [],
            "plots": [],
            "acts": [],
            "sequences": [],
            "scenes": [{"id": "s1"}],
            "arcs": [{"id": "1", "character": "k", "scene": "s1", "label": "Beat", "y": 0.5, "order": 1}],
        }
        f = io.StringIO()
        with redirect_stdout(f):
            _validate_index(index)
        output = f.getvalue()
        assert "arc beat" not in output
