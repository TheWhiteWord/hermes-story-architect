"""Tests for arc entity validation and Phase 3 tool integration (DB-backed)."""
import pytest
from pathlib import Path
from core.entity import validate_entity
from core.constants import ARC_TYPES, ENTITY_SCHEMAS, REQUIRED_FIELDS, WRITE_PATH_SUPPLIED
from core.drafts import validate_shape
from core.db import get_db
from core.writes import create_entity, edit_entity


def _kael(project):
    """The parent every arc beat needs. Six tests set up the same one."""
    create_entity(project, "character", "kael",
                  {"name": "Kael", "story_role": "Protagonist",
                   "one_sentence": "Test"})


def _beat(project, **overrides):
    """Kael's first beat, as five tests set it up."""
    create_entity(project, "arc_beat", "kael-1", {
        "character": "kael",
        "label": "First Doubt", "action": "a", "gap": "g",
        "choice": "c", "shift": "s", "y": 0.5, "order": 1, **overrides})


class TestArcValidation:
    def test_minimal_arc_beat_reports_no_missing_field(self):
        """The schema's non-optional fields are the only ones that can be required.

        `id` can never be satisfied — the write path builds the composite id
        from the slug — and `order`/`y` default to 0, which a falsy check reads
        as absent. None of the three is non-optional, so a beat carrying only
        what the schema asks for must be silent.
        """
        findings = validate_shape([{
            "op": "create", "type": "arc_beat", "id": "kael-1",
            "frontmatter": {"character": "kael", "scene": "s1", "label": "First Doubt"},
        }])
        assert not [f for f in findings if "Missing required field" in f]

    def test_required_fields_is_derived_from_the_schema(self):
        """REQUIRED_FIELDS is not a second copy of the schema.

        It was hand-maintained and drifted: arc_beat demanded an `id` the write
        path ignores, plus five fields the schema marks optional. Deriving it
        means there is nothing left to drift.
        """
        for entity_type, schema in ENTITY_SCHEMAS.items():
            expected = {f for f, m in schema.items()
                        if not m.get("optional", True) and f not in WRITE_PATH_SUPPLIED}
            assert set(REQUIRED_FIELDS[entity_type]) == expected, entity_type

    def test_validate_arc_valid(self):
        fm = {
            "id": "beat-1", "character": "kael", "scene": "central-room-day",
            "label": "First Doubt", "action": "Kael questions the system",
            "gap": "Expected answers, got silence", "choice": "Pushes harder",
            "shift": "positive → mixed", "y": 0.5, "order": 1,
        }
        warnings = validate_entity("arc_beat", fm)
        assert warnings == []

    def test_validate_arc_missing_required(self):
        warnings = validate_entity("arc_beat", {"id": "beat-1"})
        assert any("character" in w for w in warnings)
        assert any("scene" in w for w in warnings)
        assert any("label" in w for w in warnings)

    def test_validate_arc_y_out_of_range(self):
        fm = {"id": "b1", "character": "k", "scene": "s", "label": "L",
              "action": "a", "gap": "g", "choice": "c", "shift": "s", "y": 2.0, "order": 1}
        warnings = validate_entity("arc_beat", fm)
        assert any("y out of range" in w for w in warnings)

    def test_validate_arc_y_negative_ok(self):
        fm = {"id": "b1", "character": "k", "scene": "s", "label": "L",
              "action": "a", "gap": "g", "choice": "c", "shift": "s", "y": -1.0, "order": 1}
        warnings = validate_entity("arc_beat", fm)
        assert not any("y out of range" in w for w in warnings)

    def test_validate_arc_order_not_numeric(self):
        fm = {"id": "b1", "character": "k", "scene": "s", "label": "L",
              "action": "a", "gap": "g", "choice": "c", "shift": "s", "y": 0.0, "order": "first"}
        warnings = validate_entity("arc_beat", fm)
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

    def test_validate_character_value_enums(self):
        warnings = validate_entity("character", {
            "name": "T", "story_role": "Protagonist", "one_sentence": "X",
            "character_value_at_open": "positive", "character_value_at_close": "negative"
        })
        assert not any("Invalid" in w for w in warnings)
        bad = validate_entity("character", {
            "name": "T", "story_role": "Protagonist", "one_sentence": "X",
            "character_value_at_open": "sideways"
        })
        assert any("Invalid character_value_at_open: sideways" in w for w in bad)

    def test_arc_schema_has_all_fields(self):
        arc_schema = ENTITY_SCHEMAS["arc_beat"]
        assert "character" in arc_schema
        assert "scene" in arc_schema
        assert "y" in arc_schema
        assert "is_crisis" in arc_schema

    def test_character_schema_has_arc_fields(self):
        char_schema = ENTITY_SCHEMAS["character"]
        assert "arc_type" in char_schema
        assert "character_value" in char_schema
        assert "arc_complete" in char_schema


# ─── Phase 3: Tool Integration Tests (DB-backed) ───

import json


class TestArcCreateTool:
    def test_create_arc_beat(self, tmp_path):
        """An arc beat is created with its own id; the character is parent_id."""
        _kael(tmp_path)

        data = create_entity(tmp_path, "arc_beat", "kael-first-doubt",
                             {
                                 "character": "kael",
                                 "label": "First Doubt", "action": "Kael questions",
                                 "gap": "Expected answers", "choice": "Pushes harder",
                                 "shift": "positive → mixed", "y": 0.5, "order": 1,
                             })
        assert data["success"] is True

        # Verify DB state — the id is the slug; parent_id carries the character
        conn = get_db(tmp_path)
        try:
            row = conn.execute(
                "SELECT id, type, name, parent_id FROM entities WHERE id='kael-first-doubt'"
            ).fetchone()
            assert row is not None
            assert row[0] == "kael-first-doubt"
            assert row[1] == "arc_beat"
            assert row[2] == "First Doubt"
            assert row[3] == "kael"
        finally:
            conn.close()

    def test_create_arc_standard_sections(self, tmp_path):
        """Arc beat in DB includes Action/Gap/Choice/Shift/Development Log sections."""
        _kael(tmp_path)
        create_entity(tmp_path, "arc_beat", "kael-1",
                      {"character": "kael",
                       "label": "First Doubt", "action": "a", "gap": "g",
                       "choice": "c", "shift": "s", "y": 0.5, "order": 1})

        # Verify sections in DB
        conn = get_db(tmp_path)
        try:
            rows = conn.execute(
                "SELECT heading FROM sections WHERE entity_id='kael-1' ORDER BY rowid"
            ).fetchall()
            headings = [r[0] for r in rows]
            assert "Action" in headings
            assert "The Gap" in headings
            assert "Choice" in headings
            assert "Value Shift" in headings
            assert "Notes" in headings
        finally:
            conn.close()

    def test_create_arc_character_not_found(self, tmp_path):
        """Arc creation fails if character doesn't exist."""
        with pytest.raises(ValueError, match="Character not found"):
            create_entity(tmp_path, "arc_beat", "1",
                          {"id": "1", "character": "nonexistent",
                           "label": "Test", "action": "a", "gap": "g",
                           "choice": "c", "shift": "s", "y": 0.0, "order": 1})

    def test_create_arc_scene_not_found(self, tmp_path):
        """Arc creation fails if scene doesn't exist."""
        _kael(tmp_path)
        with pytest.raises(ValueError, match="Scene not found"):
            create_entity(tmp_path, "arc_beat", "1",
                          {"id": "1", "character": "kael", "scene": "nonexistent-scene",
                           "label": "Test", "action": "a", "gap": "g",
                           "choice": "c", "shift": "s", "y": 0.0, "order": 1})


class TestArcEditTool:
    def test_edit_arc_frontmatter(self, tmp_path):
        """An edit can modify arc beat frontmatter in DB."""
        _kael(tmp_path)
        _beat(tmp_path)

        assert edit_entity(tmp_path, "arc_beat", "kael-1",
                           {"label": "Updated Label", "y": -0.3},
                           "Update label and y")["success"] is True

        # Assert on DB state (label → name column, y → extra JSON)
        conn = get_db(tmp_path)
        try:
            row = conn.execute(
                "SELECT name, extra FROM entities WHERE id='kael-1'"
            ).fetchone()
            assert row[0] == "Updated Label"
            extra = json.loads(row[1])
            assert extra["y"] == -0.3
        finally:
            conn.close()

    def test_edit_arc_body_section(self, tmp_path):
        """An edit can update arc body sections in DB."""
        _kael(tmp_path)
        _beat(tmp_path)

        assert edit_entity(tmp_path, "arc_beat", "kael-1",
                           {"Action": "New action content here."},
                           "Update action section")["success"] is True

        # Assert on DB state
        conn = get_db(tmp_path)
        try:
            row = conn.execute(
                "SELECT body FROM sections WHERE entity_id='kael-1' AND heading='Action'"
            ).fetchone()
            assert "New action content here." in row[0]
        finally:
            conn.close()


class TestArcRetrieveTool:
    def test_retrieve_arc_full(self, tmp_path):
        """story_retrieve can load full arc beat note."""
        from tools.story_retrieve import handler as retrieve_handler

        _kael(tmp_path)
        _beat(tmp_path, action="Kael questions the system",
              gap="Expected answers", choice="Pushes harder",
              shift="positive → mixed")

        result = retrieve_handler({
            "project": str(tmp_path),
            "entity_type": "arc_beat",
            "id": ["kael-1"],
            "sections": ["all"]
        })
        data = json.loads(result)
        assert data["entity_type"] == "arc_beat"
        entity = data["entities"][0]
        assert entity["id"] == "kael-1"
        assert "Action" in entity["sections"]
        assert "Notes" in entity["sections"]

    def test_retrieve_arc_specific_section(self, tmp_path):
        """story_retrieve can load specific arc beat section."""
        from tools.story_retrieve import handler as retrieve_handler

        _kael(tmp_path)
        _beat(tmp_path)

        result = retrieve_handler({
            "project": str(tmp_path),
            "entity_type": "arc_beat",
            "id": ["1"],
            "sections": ["Action"]
        })
        data = json.loads(result)
        assert "Action" in data["entities"][0]["sections"]

    def test_retrieve_arc_not_found(self, tmp_path):
        """story_retrieve returns error for nonexistent arc beat."""
        from tools.story_retrieve import handler as retrieve_handler

        result = retrieve_handler({
            "project": str(tmp_path),
            "entity_type": "arc_beat",
            "id": ["999"],
            "sections": ["all"]
        })
        data = json.loads(result)
        assert "error" in data


class TestArcLoadTool:
    def test_load_includes_arc_count(self, tmp_path):
        """story_load confirmation includes character count."""
        from tools.story_load import handler as load_handler

        _kael(tmp_path)
        _beat(tmp_path, label="Beat", y=0.0)

        result = load_handler({
            "project": str(tmp_path)
        })
        data = json.loads(result)
        # New format: no arc count, but character count present
        assert "1 characters" in data["confirmation"]
        # Arc beats no longer in load output; verified via story_retrieve
        assert any(c["id"] == "kael" for c in data["characters"])


class TestArcToolIntegrationFixture:
    """Integration tests using save-the-children fixture (read-only). Each test
    copies the fixture to a temp dir so no .story/story.db is created in the repo."""

    def test_retrieve_arc_from_fixture(self, fixture_path):
        """story_retrieve loads existing arc beat from fixture."""
        from tools.story_import import handler as import_handler
        from tools.story_retrieve import handler as retrieve_handler

        # Import fixture to DB (in temp)
        import_handler({"project": str(fixture_path), "root_path": fixture_path.parent})

        result = retrieve_handler({
            "project": str(fixture_path),
            "entity_type": "arc_beat",
            "id": ["1"],
            "sections": ["all"],
            "root_path": fixture_path.parent,
        })
        data = json.loads(result)
        assert data["entity_type"] == "arc_beat"
        entity = data["entities"][0]
        assert entity["id"].endswith("-1")
        assert "Action" in entity["sections"]

    def test_retrieve_arc_action_section_from_fixture(self, fixture_path):
        """story_retrieve loads specific section from fixture arc beat."""
        from tools.story_import import handler as import_handler
        from tools.story_retrieve import handler as retrieve_handler

        import_handler({"project": str(fixture_path), "root_path": fixture_path.parent})

        result = retrieve_handler({
            "project": str(fixture_path),
            "entity_type": "arc_beat",
            "id": ["2"],
            "sections": ["Action"],
            "root_path": fixture_path.parent,
        })
        data = json.loads(result)
        assert "Action" in data["entities"][0]["sections"]

    def test_load_fixture_includes_arc_count(self, fixture_path):
        """story_load confirmation includes fixture character count."""
        from tools.story_import import handler as import_handler
        from tools.story_load import handler as load_handler

        import_handler({"project": str(fixture_path), "root_path": fixture_path.parent})

        result = load_handler({
            "project": str(fixture_path),
            "root_path": fixture_path.parent,
        })
        data = json.loads(result)
        # New format: character count instead of arc count
        assert "characters" in data["confirmation"]
        # Arc beats no longer in load output; verified via story_retrieve
        assert any(c["id"] == "kael" for c in data["characters"])
