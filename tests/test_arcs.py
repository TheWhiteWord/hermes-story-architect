"""Tests for arc entity validation and Phase 3 tool integration (DB-backed)."""
import pytest
from pathlib import Path
from core.entity import validate_entity
from core.constants import ARC_TYPES, ENTITY_SCHEMAS


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


# ─── Phase 3: Tool Integration Tests (DB-backed) ───

import json


class TestArcCreateTool:
    def test_create_arc_beat(self, tmp_path):
        """story_create with entity_type='arc' creates DB entity."""
        from tools.story_create import handler as create_handler
        from core.db import get_db


        create_handler({
            "entity_type": "character", "slug": "kael", "project": str(tmp_path),
            "frontmatter": {"name": "Kael", "story_role": "Protagonist", "one_sentence": "Test"}
        })

        result = create_handler({
            "entity_type": "arc", "slug": "1", "project": str(tmp_path),
            "frontmatter": {
                "id": "1", "character": "kael",
                "label": "First Doubt", "action": "Kael questions",
                "gap": "Expected answers", "choice": "Pushes harder",
                "shift": "positive → mixed", "y": 0.5, "order": 1,
            }
        })
        data = json.loads(result)
        assert data["success"] is True

        # Verify DB state — arc entity with composite ID
        conn = get_db(tmp_path)
        try:
            row = conn.execute(
                "SELECT id, type, name, parent_id FROM entities WHERE id='kael-1'"
            ).fetchone()
            assert row is not None
            assert row[0] == "kael-1"
            assert row[1] == "arc"
            assert row[2] == "First Doubt"
            assert row[3] == "kael"
        finally:
            conn.close()

    def test_create_arc_standard_sections(self, tmp_path):
        """Arc beat in DB includes Action/Gap/Choice/Shift/Development Log sections."""
        from tools.story_create import handler as create_handler
        from core.db import get_db

        create_handler({
            "entity_type": "character", "slug": "kael", "project": str(tmp_path),
            "frontmatter": {"name": "Kael", "story_role": "Protagonist", "one_sentence": "Test"}
        })

        create_handler({
            "entity_type": "arc", "slug": "1", "project": str(tmp_path),
            "frontmatter": {
                "id": "1", "character": "kael",
                "label": "First Doubt", "action": "a", "gap": "g",
                "choice": "c", "shift": "s", "y": 0.5, "order": 1,
            }
        })

        # Verify sections in DB
        conn = get_db(tmp_path)
        try:
            rows = conn.execute(
                "SELECT heading FROM sections WHERE entity_id='kael-1' ORDER BY rowid"
            ).fetchall()
            headings = [r[0] for r in rows]
            assert "Action" in headings
            assert "Gap" in headings
            assert "Choice" in headings
            assert "Shift" in headings
            assert "Development Log" in headings
        finally:
            conn.close()

    def test_create_arc_character_not_found(self, tmp_path):
        """Arc creation fails if character doesn't exist."""
        from tools.story_create import handler as create_handler

        result = create_handler({
            "entity_type": "arc", "slug": "1", "project": str(tmp_path),
            "frontmatter": {
                "id": "1", "character": "nonexistent",
                "label": "Test", "action": "a", "gap": "g",
                "choice": "c", "shift": "s", "y": 0.0, "order": 1,
            }
        })
        data = json.loads(result)
        assert "error" in data
        assert "Character not found" in data["error"]

    def test_create_arc_scene_not_found(self, tmp_path):
        """Arc creation fails if scene doesn't exist."""
        from tools.story_create import handler as create_handler

        create_handler({
            "entity_type": "character", "slug": "kael", "project": str(tmp_path),
            "frontmatter": {"name": "Kael", "story_role": "Protagonist", "one_sentence": "Test"}
        })

        result = create_handler({
            "entity_type": "arc", "slug": "1", "project": str(tmp_path),
            "frontmatter": {
                "id": "1", "character": "kael", "scene": "nonexistent-scene",
                "label": "Test", "action": "a", "gap": "g",
                "choice": "c", "shift": "s", "y": 0.0, "order": 1,
            }
        })
        data = json.loads(result)
        assert "error" in data
        assert "Scene not found" in data["error"]


class TestArcEditTool:
    def test_edit_arc_frontmatter(self, tmp_path):
        """story_edit can modify arc beat frontmatter in DB."""
        from tools.story_create import handler as create_handler
        from tools.story_edit import handler as edit_handler
        from core.db import get_db

        create_handler({
            "entity_type": "character", "slug": "kael", "project": str(tmp_path),
            "frontmatter": {"name": "Kael", "story_role": "Protagonist", "one_sentence": "Test"}
        })
        create_handler({
            "entity_type": "arc", "slug": "1", "project": str(tmp_path),
            "frontmatter": {
                "id": "1", "character": "kael",
                "label": "First Doubt", "action": "a", "gap": "g",
                "choice": "c", "shift": "s", "y": 0.5, "order": 1,
            }
        })

        result = edit_handler({
            "action": "edit_note",
            "target": {"entity_type": "arc", "slug": "1", "project": str(tmp_path)},
            "data": {"label": "Updated Label", "y": -0.3},
            "summary": "Update label and y"
        })
        assert json.loads(result)["success"] is True

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
        """story_edit can update arc body sections in DB."""
        from tools.story_create import handler as create_handler
        from tools.story_edit import handler as edit_handler
        from core.db import get_db

        create_handler({
            "entity_type": "character", "slug": "kael", "project": str(tmp_path),
            "frontmatter": {"name": "Kael", "story_role": "Protagonist", "one_sentence": "Test"}
        })
        create_handler({
            "entity_type": "arc", "slug": "1", "project": str(tmp_path),
            "frontmatter": {
                "id": "1", "character": "kael",
                "label": "First Doubt", "action": "a", "gap": "g",
                "choice": "c", "shift": "s", "y": 0.5, "order": 1,
            }
        })

        result = edit_handler({
            "action": "edit_note",
            "target": {"entity_type": "arc", "slug": "1", "project": str(tmp_path)},
            "data": {"Action": "New action content here."},
            "summary": "Update action section"
        })
        assert json.loads(result)["success"] is True

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
        from tools.story_create import handler as create_handler
        from tools.story_retrieve import handler as retrieve_handler

        create_handler({
            "entity_type": "character", "slug": "kael", "project": str(tmp_path),
            "frontmatter": {"name": "Kael", "story_role": "Protagonist", "one_sentence": "Test"}
        })
        create_handler({
            "entity_type": "arc", "slug": "1", "project": str(tmp_path),
            "frontmatter": {
                "id": "1", "character": "kael",
                "label": "First Doubt", "action": "Kael questions the system",
                "gap": "Expected answers", "choice": "Pushes harder",
                "shift": "positive → mixed", "y": 0.5, "order": 1,
            }
        })

        result = retrieve_handler({
            "project": str(tmp_path),
            "entity_type": "arc",
            "slug": "1",
            "sections": ["all"]
        })
        data = json.loads(result)
        assert data["entity_type"] == "arc"
        assert data["slug"] == "1"
        assert "## Action" in data["content"]
        assert "## Development Log" in data["content"]

    def test_retrieve_arc_specific_section(self, tmp_path):
        """story_retrieve can load specific arc beat section."""
        from tools.story_create import handler as create_handler
        from tools.story_retrieve import handler as retrieve_handler

        create_handler({
            "entity_type": "character", "slug": "kael", "project": str(tmp_path),
            "frontmatter": {"name": "Kael", "story_role": "Protagonist", "one_sentence": "Test"}
        })
        create_handler({
            "entity_type": "arc", "slug": "1", "project": str(tmp_path),
            "frontmatter": {
                "id": "1", "character": "kael",
                "label": "First Doubt", "action": "a", "gap": "g",
                "choice": "c", "shift": "s", "y": 0.5, "order": 1,
            }
        })

        result = retrieve_handler({
            "project": str(tmp_path),
            "entity_type": "arc",
            "slug": "1",
            "sections": ["Action"]
        })
        data = json.loads(result)
        assert "Action" in data["sections"]

    def test_retrieve_arc_not_found(self, tmp_path):
        """story_retrieve returns error for nonexistent arc beat."""
        from tools.story_retrieve import handler as retrieve_handler

        result = retrieve_handler({
            "project": str(tmp_path),
            "entity_type": "arc",
            "slug": "999",
            "sections": ["all"]
        })
        data = json.loads(result)
        assert "error" in data


class TestArcLoadTool:
    def test_load_includes_arc_count(self, tmp_path):
        """story_load confirmation includes character count."""
        from tools.story_create import handler as create_handler
        from tools.story_load import handler as load_handler

        create_handler({
            "entity_type": "character", "slug": "kael", "project": str(tmp_path),
            "frontmatter": {"name": "Kael", "story_role": "Protagonist", "one_sentence": "Test"}
        })
        create_handler({
            "entity_type": "arc", "slug": "1", "project": str(tmp_path),
            "frontmatter": {
                "id": "1", "character": "kael",
                "label": "Beat", "action": "a", "gap": "g",
                "choice": "c", "shift": "s", "y": 0.0, "order": 1,
            }
        })

        result = load_handler({
            "project": str(tmp_path)
        })
        data = json.loads(result)
        # New format: no arc count, but character count present
        assert "1 characters" in data["confirmation"]
        # Arc beats no longer in load output; verified via story_retrieve
        assert "kael" in data["characters"]


class TestArcToolIntegrationFixture:
    """Integration tests using save-the-children fixture (read-only)."""

    FIXTURE_PATH = Path(__file__).parent / "fixtures" / "save-the-children"

    def test_retrieve_arc_from_fixture(self):
        """story_retrieve loads existing arc beat from fixture."""
        from tools.story_import import handler as import_handler
        from tools.story_retrieve import handler as retrieve_handler

        # Import fixture to DB
        import_handler({"project": str(self.FIXTURE_PATH)})

        result = retrieve_handler({
            "project": str(self.FIXTURE_PATH),
            "entity_type": "arc",
            "slug": "1",
            "sections": ["all"]
        })
        data = json.loads(result)
        assert data["entity_type"] == "arc"
        assert data["slug"] == "1"
        assert "## Action" in data["content"]

    def test_retrieve_arc_action_section_from_fixture(self):
        """story_retrieve loads specific section from fixture arc beat."""
        from tools.story_retrieve import handler as retrieve_handler

        result = retrieve_handler({
            "project": str(self.FIXTURE_PATH),
            "entity_type": "arc",
            "slug": "2",
            "sections": ["Action"]
        })
        data = json.loads(result)
        assert "Action" in data["sections"]

    def test_load_fixture_includes_arc_count(self):
        """story_load confirmation includes fixture character count."""
        from tools.story_load import handler as load_handler

        result = load_handler({
            "project": str(self.FIXTURE_PATH)
        })
        data = json.loads(result)
        # New format: character count instead of arc count
        assert "characters" in data["confirmation"]
        # Arc beats no longer in load output; verified via story_retrieve
        assert "kael" in data["characters"]
