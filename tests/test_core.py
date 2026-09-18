"""Test suite for Story Architect core modules."""
import pytest
import json
from pathlib import Path
from core.section_parser import list_sections, get_section, replace_section
from core.entity import extract_entity, validate_entity, update_sections
from core.screenplay import extract_scenes, match_character, match_location, extract_location
from core.constants import ENTITY_SCHEMAS


# ---- Imports for tool tests ----
from tools.story_create import handler as create_handler
from tools.story_load import handler as load_handler


# ---- Fixtures ----

@pytest.fixture
def project_path():
    """Path to the test fixture project."""
    return Path(__file__).parent / "fixtures" / "save-the-children"


@pytest.fixture
def kael_note(project_path):
    """Path to Kael's character note."""
    return project_path / "characters" / "kael.md"


@pytest.fixture
def screenplay_path(project_path):
    """Path to the screenplay."""
    return project_path / "screenplay.fountain"


# ---- Section Parser Tests ----

class TestSectionParser:
    def test_list_sections_simple(self):
        body = "## Personality\nSome text.\n\n## Background\nMore text."
        result = list_sections(body)
        assert result == ["Personality", "Background"]

    def test_list_sections_empty(self):
        assert list_sections("") == []

    def test_list_sections_no_headings(self):
        body = "Just some text without headings."
        assert list_sections(body) == []

    def test_get_section_found(self):
        body = "## Personality\nMeticulous, introverted.\n\n## Background\nParents immigrated."
        result = get_section(body, "Personality")
        assert "## Personality" in result
        assert "Meticulous, introverted." in result

    def test_get_section_not_found(self):
        body = "## Personality\nSome text."
        result = get_section(body, "Background")
        assert result == ""

    def test_replace_section(self):
        body = "## Personality\nOld text.\n\n## Background\nKeep this."
        result = replace_section(body, "Personality", "New text.")
        # Note: first heading loses ## prefix due to regex split
        assert "Personality" in result
        assert "New text." in result
        assert "Old text." not in result
        assert "## Background" in result
        assert "Keep this." in result


# ---- Entity Extraction Tests ----

class TestEntityExtraction:
    def test_extract_character(self, kael_note):
        entity = extract_entity(kael_note, "character")
        assert entity["id"] == "kael"
        assert entity["name"] == "Kael"
        assert entity["story_role"] == "Protagonist"
        assert "Personality" in entity["sections"]
        assert "Background" in entity["sections"]

    def test_validate_character_valid(self, kael_note):
        entity = extract_entity(kael_note, "character")
        warnings = validate_entity("character", entity)
        assert warnings == []

    def test_validate_character_missing_field(self):
        warnings = validate_entity("character", {"name": "Test"})
        assert any("story_role" in w for w in warnings)

    def test_validate_character_invalid_role(self):
        warnings = validate_entity("character", {"name": "T", "story_role": "Invalid", "one_sentence": "X"})
        assert any("Invalid story_role" in w for w in warnings)

    def test_validate_scene_invalid_status(self):
        """validate_entity('scene', {status: 'invalid'}) returns warning."""
        warnings = validate_entity("scene", {"title": "Test", "sequence_id": "seq-1", "act_id": "act-1", "status": "invalid"})
        assert any("Invalid status: invalid" in w for w in warnings)

    def test_validate_scene_invalid_dramatic_role(self):
        """validate_entity('scene', {dramatic_role: 'invalid'}) returns warning."""
        warnings = validate_entity("scene", {"title": "Test", "sequence_id": "seq-1", "act_id": "act-1", "dramatic_role": "invalid"})
        assert any("Invalid dramatic_role: invalid" in w for w in warnings)

    def test_validate_scene_accepts_non_event(self):
        """'non-event' is a valid dramatic_role (McKee: scenes that don't turn)."""
        warnings = validate_entity("scene", {"title": "Test", "sequence_id": "seq-1", "act_id": "act-1", "dramatic_role": "non-event"})
        assert not any("Invalid dramatic_role" in w for w in warnings)

    def test_non_event_with_empty_values_is_valid(self):
        """non-event scenes should leave value_open/value_close empty (no fake value turn)."""
        warnings = validate_entity("scene", {
            "title": "Test", "sequence_id": "seq-1", "act_id": "act-1",
            "dramatic_role": "non-event", "value_open": "", "value_close": ""
        })
        assert not any("Invalid" in w for w in warnings)

    def test_validate_sequence_invalid_status(self):
        """validate_entity('sequence', {status: 'invalid'}) returns warning."""
        warnings = validate_entity("sequence", {"title": "Test", "act_id": "act-1", "status": "invalid"})
        assert any("Invalid status: invalid" in w for w in warnings)

    def test_validate_act_invalid_status(self):
        """validate_entity('act', {status: 'invalid'}) returns warning."""
        warnings = validate_entity("act", {"title": "Test", "status": "invalid"})
        assert any("Invalid status: invalid" in w for w in warnings)

    def test_extract_project(self, project_path):
        entity = extract_entity(project_path / "project.md", "project")
        assert entity["name"] == "Save the Children"
        assert "logline" in entity

    def test_extract_world(self, project_path):
        entity = extract_entity(project_path / "worlds" / "the-i.md", "world")
        assert entity["name"] == "The I"
        assert "sections" in entity


# ---- Screenplay Tests ----

class TestScreenplay:
    def test_extract_scenes(self, screenplay_path):
        content = screenplay_path.read_text()
        scenes = extract_scenes(content)
        assert len(scenes) == 9
        assert scenes[0]["heading"] == "EXT. THE INSTITUTE - DAY"
        assert scenes[0]["id"] == 1

    def test_extract_location(self):
        assert extract_location("INT. KITCHEN - NIGHT") == "KITCHEN"
        assert extract_location("EXT. PARK - DAY") == "PARK"
        assert extract_location("EST. HOUSE - DAWN") == "HOUSE"
        assert extract_location("NOT A HEADING") is None

    def test_match_character_exact(self):
        characters = [{"id": "kael", "name": "Kael"}]
        assert match_character("KAEL", characters) == "kael"

    def test_match_character_fuzzy(self):
        characters = [{"id": "kael", "name": "Kael"}]
        assert match_character("KAEL", characters) == "kael"

    def test_match_character_no_match(self):
        characters = [{"id": "kael", "name": "Kael"}]
        assert match_character("VICTOR HALE", characters) is None

    def test_match_location(self):
        locations = [{"id": "the-central-room", "name": "The Central Room"}]
        assert match_location("THE CENTRAL ROOM", locations) == "the-central-room"
        assert match_location("The Central Room", locations) == "the-central-room"


# ---- Note Creation Tests ----

def _make_minimal_project(tmp):
    """Create a minimal project structure for testing."""
    project_path = Path(tmp) / "test-project"
    project_path.mkdir()
    (project_path / "characters").mkdir(parents=True)
    (project_path / "locations").mkdir(parents=True)
    (project_path / "worlds").mkdir(parents=True)
    (project_path / "plots").mkdir(parents=True)
    (project_path / ".story").mkdir(parents=True)
    (project_path / "project.md").write_text("---\nname: Test\n---\n")
    return project_path


class TestNoteCreation:
    """Tests for note creation standardization — all fields present, body sections auto-generated."""

    def test_create_character_has_all_fields(self, tmp_path):
        """Creating a character with minimal fields should still produce all fields."""
        from tools.story_create import handler as create_handler

        project_path = _make_minimal_project(tmp_path)

        args = {
            "entity_type": "character",
            "slug": "test-char",
            "project": str(project_path),
            "frontmatter": {"name": "Test Char", "story_role": "Protagonist"}
        }
        result = json.loads(create_handler(args))
        assert result["success"] == True

        from core.db import get_db
        conn = get_db(project_path)
        try:
            row = conn.execute(
                "SELECT name, one_sentence, extra FROM entities WHERE id='test-char' AND type='character'"
            ).fetchone()
            assert row is not None
            assert row[0] == "Test Char"
            assert row[1] == ""  # one_sentence is a column
            extra = json.loads(row[2])
            assert extra["story_role"] == "Protagonist"
            # relationships are stored in relations table, not extra JSON
            assert extra["goals_short"] == "Goals not set"
            assert extra["goals_long"] == "Goals not set"
            assert extra["knowledge"] == []
        finally:
            conn.close()

    def test_create_character_has_all_sections(self, tmp_path):
        """Creating a character should produce all standard body sections."""
        from tools.story_create import handler as create_handler

        project_path = _make_minimal_project(tmp_path)

        args = {
            "entity_type": "character",
            "slug": "test-char",
            "project": str(project_path),
            "frontmatter": {"name": "Test Char", "story_role": "Protagonist"}
        }
        result = json.loads(create_handler(args))
        assert result["success"] == True

        from core.db import get_db
        conn = get_db(project_path)
        try:
            rows = conn.execute(
                "SELECT heading FROM sections WHERE entity_id='test-char' ORDER BY rowid"
            ).fetchall()
            headings = [r[0] for r in rows]
            assert "Personality" in headings
            assert "Background" in headings
            assert "Voice" in headings
            assert "Greatest Fear" in headings
            assert "Secrets" in headings
            assert "Arc" in headings
            assert "Relationships" in headings
            assert "Goals" in headings
        finally:
            conn.close()

    def test_create_plot_has_all_fields(self, tmp_path):
        """Creating a plot with minimal fields should produce all fields."""
        from tools.story_create import handler as create_handler

        project_path = _make_minimal_project(tmp_path)

        args = {
            "entity_type": "plot",
            "slug": "test-plot",
            "project": str(project_path),
            "frontmatter": {"name": "Test Plot"}
        }
        result = json.loads(create_handler(args))
        assert result["success"] == True

        from core.db import get_db
        conn = get_db(project_path)
        try:
            row = conn.execute(
                "SELECT name, one_sentence, status, extra FROM entities WHERE id='test-plot' AND type='plot'"
            ).fetchone()
            assert row is not None
            assert row[0] == "Test Plot"
            assert row[1] == "Summary not set"  # one_sentence is a column
            assert row[2] == "active"
            extra = json.loads(row[3])
            assert extra["characters"] == []
            # setups/payoffs are relation fields, not extra JSON
        finally:
            conn.close()

    def test_create_plot_has_all_sections(self, tmp_path):
        """Creating a plot should produce all standard body sections."""
        from tools.story_create import handler as create_handler

        project_path = _make_minimal_project(tmp_path)

        args = {
            "entity_type": "plot",
            "slug": "test-plot",
            "project": str(project_path),
            "frontmatter": {"name": "Test Plot"}
        }
        result = json.loads(create_handler(args))
        assert result["success"] == True

        from core.db import get_db
        conn = get_db(project_path)
        try:
            rows = conn.execute(
                "SELECT heading FROM sections WHERE entity_id='test-plot' ORDER BY rowid"
            ).fetchall()
            headings = [r[0] for r in rows]
            assert "Summary" in headings
            assert "Obstacles" in headings
            assert "Stakes" in headings
        finally:
            conn.close()

    def test_create_plot_with_scope_and_arc(self, tmp_path):
        """Creating a plot with plot_scope and value_arc."""
        from tools.story_create import handler as create_handler
        from core.db import get_db

        project_path = _make_minimal_project(tmp_path)

        args = {
            "entity_type": "plot",
            "slug": "main-plot",
            "project": str(project_path),
            "frontmatter": {"name": "Main Plot", "plot_scope": "main", "value_arc": "Maturation"}
        }
        result = json.loads(create_handler(args))
        assert result["success"] is True

        conn = get_db(project_path)
        try:
            row = conn.execute(
                "SELECT extra FROM entities WHERE id='main-plot' AND type='plot'"
            ).fetchone()
            extra = json.loads(row[0])
            assert extra["plot_scope"] == "main"
            assert extra["value_arc"] == "Maturation"
        finally:
            conn.close()

    def test_validate_plot_invalid_scope(self):
        """validate_entity('plot', {plot_scope: 'invalid'}) returns warning."""
        from core.entity import validate_entity
        warnings = validate_entity("plot", {"name": "Test", "status": "active", "plot_scope": "invalid"})
        assert any("Invalid plot_scope: invalid" in w for w in warnings)

    def test_validate_plot_invalid_value_arc(self):
        """validate_entity('plot', {value_arc: 'invalid'}) returns warning."""
        from core.entity import validate_entity
        warnings = validate_entity("plot", {"name": "Test", "status": "active", "value_arc": "invalid"})
        assert any("Invalid value_arc: invalid" in w for w in warnings)

    def test_validate_plot_valid_scope_and_arc(self):
        """validate_entity accepts valid plot_scope and value_arc."""
        from core.entity import validate_entity
        warnings = validate_entity("plot", {"name": "Test", "status": "active", "plot_scope": "main", "value_arc": "Maturation"})
        assert not any("Invalid" in w for w in warnings)

    def test_create_scene_has_all_fields_and_sections(self, tmp_path):
        """Creating a scene with minimal fields should still produce all fields and body sections."""
        from tools.story_create import handler as create_handler

        project_path = _make_minimal_project(tmp_path)

        # Create parent entities first (required for scene validation)
        create_handler({
            "entity_type": "act", "slug": "act-1", "project": str(project_path),
            "frontmatter": {"title": "Act 1"}
        })
        create_handler({
            "entity_type": "sequence", "slug": "seq-1", "project": str(project_path),
            "frontmatter": {"title": "Seq 1", "act_id": "act-1"}
        })

        args = {
            "entity_type": "scene",
            "slug": "test-scene",
            "project": str(project_path),
            "frontmatter": {"title": "Test Scene", "sequence_id": "seq-1", "act_id": "act-1"}
        }
        result = json.loads(create_handler(args))
        assert result["success"] == True

        from core.db import get_db
        conn = get_db(project_path)
        try:
            row = conn.execute(
                "SELECT name, status, order_key, parent_id, location_id, extra "
                "FROM entities WHERE id='test-scene' AND type='scene'"
            ).fetchone()
            assert row is not None
            assert row[0] == "Test Scene"
            assert row[1] == "planned"
            assert row[2] == 1  # auto-order
            assert row[3] == "seq-1"
            extra = json.loads(row[5])
            assert extra["act_id"] == "act-1"
            # characters are relation fields, not extra JSON

            # All standard sections should be present
            sec_rows = conn.execute(
                "SELECT heading FROM sections WHERE entity_id='test-scene' ORDER BY rowid"
            ).fetchall()
            headings = [r[0] for r in sec_rows]
            assert "Description" in headings
            assert "Dramatic Function" in headings
            assert "Notes" in headings
            assert "Content" in headings
        finally:
            conn.close()

    def test_create_sequence_has_all_fields_and_sections(self, tmp_path):
        """Creating a sequence should produce all fields and body sections."""
        from tools.story_create import handler as create_handler

        project_path = _make_minimal_project(tmp_path)

        # Create parent act first (required for sequence validation)
        create_handler({
            "entity_type": "act", "slug": "act-1", "project": str(project_path),
            "frontmatter": {"title": "Act 1"}
        })

        args = {
            "entity_type": "sequence",
            "slug": "test-sequence",
            "project": str(project_path),
            "frontmatter": {"title": "Test Sequence", "act_id": "act-1"}
        }
        result = json.loads(create_handler(args))
        assert result["success"] == True

        from core.db import get_db
        conn = get_db(project_path)
        try:
            row = conn.execute(
                "SELECT name, status, order_key, parent_id, extra "
                "FROM entities WHERE id='test-sequence' AND type='sequence'"
            ).fetchone()
            assert row is not None
            assert row[0] == "Test Sequence"
            assert row[1] == "planned"
            assert row[2] == 1  # auto-order
            assert row[3] == "act-1"

            sec_rows = conn.execute(
                "SELECT heading FROM sections WHERE entity_id='test-sequence' ORDER BY rowid"
            ).fetchall()
            headings = [r[0] for r in sec_rows]
            assert "Summary" in headings
            assert "Scene Order" in headings
            assert "Notes" in headings
        finally:
            conn.close()

    def test_create_act_has_all_fields_and_sections(self, tmp_path):
        """Creating an act should produce all fields and body sections."""
        from tools.story_create import handler as create_handler

        project_path = _make_minimal_project(tmp_path)

        args = {
            "entity_type": "act",
            "slug": "test-act",
            "project": str(project_path),
            "frontmatter": {"title": "Test Act"}
        }
        result = json.loads(create_handler(args))
        assert result["success"] == True

        from core.db import get_db
        conn = get_db(project_path)
        try:
            row = conn.execute(
                "SELECT name, status, order_key, extra "
                "FROM entities WHERE id='test-act' AND type='act'"
            ).fetchone()
            assert row is not None
            assert row[0] == "Test Act"
            assert row[1] == "planned"
            assert row[2] == 0  # acts don't auto-order

            sec_rows = conn.execute(
                "SELECT heading FROM sections WHERE entity_id='test-act' ORDER BY rowid"
            ).fetchall()
            headings = [r[0] for r in sec_rows]
            assert "Summary" in headings
            assert "Thematic Function" in headings
            assert "Notes" in headings
        finally:
            conn.close()


class TestProjectCreation:
    """Tests for story_create(entity_type='project', ...)."""

    def test_create_project_creates_all_folders(self, tmp_path):
        args = {
            "entity_type": "project",
            "slug": "test-proj",
            "project": "",
            "frontmatter": {"name": "Test Project", "logline": "A test"},
        }
        create_handler(args, vault_path=str(tmp_path))
        proj = tmp_path / "projects" / "test-proj"
        for folder in ["characters", "locations", "worlds", "plots", "scenes", "sequences", "acts", "arcs"]:
            assert (proj / folder).is_dir(), f"Missing folder: {folder}"

    def test_create_project_creates_project_md(self, tmp_path):
        args = {
            "entity_type": "project",
            "slug": "test-proj",
            "project": "",
            "frontmatter": {"name": "Test Project"},
        }
        create_handler(args, vault_path=str(tmp_path))
        import frontmatter
        post = frontmatter.load(tmp_path / "projects" / "test-proj" / "project.md")
        for field in ENTITY_SCHEMAS["project"]:
            assert field in post.metadata, f"Missing field: {field}"
        assert "## Synopsis" in post.content
        assert "## Notes" in post.content

    def test_create_project_creates_memory_md(self, tmp_path):
        args = {
            "entity_type": "project",
            "slug": "test-proj",
            "project": "",
            "frontmatter": {"name": "Test Project"},
        }
        create_handler(args, vault_path=str(tmp_path))
        memory = tmp_path / "projects" / "test-proj" / ".story" / "memory.md"
        assert memory.exists()
        assert "# Story Memory" in memory.read_text()
        assert "## Continuity notes" in memory.read_text()

    def test_create_project_creates_db(self, tmp_path):
        args = {
            "entity_type": "project",
            "slug": "test-proj",
            "project": "",
            "frontmatter": {"name": "Test Project"},
        }
        result = create_handler(args, vault_path=str(tmp_path))
        assert json.loads(result)["success"] is True
        db_path = tmp_path / "projects" / "test-proj" / ".story" / "story.db"
        assert db_path.exists()
        from core.db import get_db
        conn = get_db(tmp_path / "projects" / "test-proj")
        try:
            row = conn.execute("SELECT name, type FROM entities WHERE id='test-proj' AND type='project'").fetchone()
            assert row is not None
            assert row[0] == "Test Project"
        finally:
            conn.close()

    def test_create_project_validates_required_fields(self, tmp_path):
        args = {
            "entity_type": "project",
            "slug": "test-proj",
            "project": "",
            "frontmatter": {},
        }
        result = json.loads(create_handler(args, vault_path=str(tmp_path)))
        assert "error" in result
        assert "Missing required" in result["error"]

    def test_create_project_idempotent(self, tmp_path):
        args = {
            "entity_type": "project",
            "slug": "test-proj",
            "project": "",
            "frontmatter": {"name": "Test Project"},
        }
        create_handler(args, vault_path=str(tmp_path))
        result = json.loads(create_handler(args, vault_path=str(tmp_path)))
        assert "error" in result

    def test_story_load_works_after_create(self, tmp_path):
        args = {
            "entity_type": "project",
            "slug": "test-proj",
            "project": "",
            "frontmatter": {"name": "Test Project"},
        }
        create_handler(args, vault_path=str(tmp_path))
        load_args = {"project": str(tmp_path / "projects" / "test-proj")}
        result = json.loads(load_handler(load_args, vault_path=str(tmp_path)))
        assert result["loaded"] is True
        assert result["project"]["name"] == "Test Project"


def _make_project_with_structure(tmp):
    """Create a project with acts/sequences/scenes folders for tool surface tests."""
    project_path = _make_minimal_project(tmp)
    (project_path / "scenes").mkdir(parents=True, exist_ok=True)
    (project_path / "sequences").mkdir(parents=True, exist_ok=True)
    (project_path / "acts").mkdir(parents=True, exist_ok=True)
    return project_path


class TestPhase3ToolSurface:
    """Tests for Phase 3 tool surface: edit_note data bag, reorder, cascade blocking, auto-order, parent validation, structure-index update."""

    def test_edit_note_with_data_bag(self, tmp_path):
        """edit_note with data bag updates entity columns + sections in DB."""
        from tools.story_create import handler as create_handler
        from tools.story_edit import handler as edit_handler

        project_path = _make_project_with_structure(tmp_path)

        # Create parents (now writes DB directly)
        create_handler({
            "entity_type": "act", "slug": "act-1", "project": str(project_path),
            "frontmatter": {"title": "Act 1"}
        })
        create_handler({
            "entity_type": "sequence", "slug": "seq-1", "project": str(project_path),
            "frontmatter": {"title": "Seq 1", "act_id": "act-1"}
        })
        create_handler({
            "entity_type": "scene", "slug": "test-scene", "project": str(project_path),
            "frontmatter": {"title": "Test Scene", "sequence_id": "seq-1", "act_id": "act-1"}
        })

        # Edit with data bag: frontmatter field + body section
        result = edit_handler({
            "action": "edit_note",
            "target": {"entity_type": "scene", "slug": "test-scene", "project": str(project_path)},
            "data": {"status": "written", "Description": "Updated description text."},
            "summary": "Update status and description"
        })
        assert json.loads(result)["success"] is True

        # Assert on DB state
        from core.db import get_db
        conn = get_db(project_path)
        row = conn.execute("SELECT status FROM entities WHERE id='test-scene'").fetchone()
        assert row[0] == "written"
        sec_row = conn.execute(
            "SELECT body FROM sections WHERE entity_id='test-scene' AND heading='Description'"
        ).fetchone()
        assert "Updated description text." in sec_row[0]
        conn.close()

    def test_reorder_scene_within_sequence(self, tmp_path):
        """Reorder scenes → order_key renumbered 1-2-3 in DB."""
        from tools.story_create import handler as create_handler
        from tools.story_edit import handler as edit_handler
        from core.db import get_db

        project_path = _make_project_with_structure(tmp_path)

        create_handler({
            "entity_type": "act", "slug": "act-1", "project": str(project_path),
            "frontmatter": {"title": "Act 1"}
        })
        create_handler({
            "entity_type": "sequence", "slug": "seq-1", "project": str(project_path),
            "frontmatter": {"title": "Seq 1", "act_id": "act-1"}
        })
        for slug in ["scene-1", "scene-2", "scene-3"]:
            create_handler({
                "entity_type": "scene", "slug": slug, "project": str(project_path),
                "frontmatter": {"title": f"Scene {slug[-1]}", "sequence_id": "seq-1", "act_id": "act-1"}
            })

        # Reorder: move scene-3 to front
        result = edit_handler({
            "action": "reorder",
            "target": {"entity_type": "scene", "project": str(project_path)},
            "order_context": {"ordered_ids": ["scene-3", "scene-1", "scene-2"]},
            "summary": "Reorder scenes"
        })
        assert json.loads(result)["success"] is True

        # Assert DB order_key values
        conn = get_db(project_path)
        try:
            rows = conn.execute(
                "SELECT id, order_key FROM entities WHERE type='scene' AND is_deleted=0 ORDER BY order_key"
            ).fetchall()
            assert [r[0] for r in rows] == ["scene-3", "scene-1", "scene-2"]
            assert [r[1] for r in rows] == [1, 2, 3]
        finally:
            conn.close()

    def test_delete_sequence_with_scenes_blocked(self, tmp_path):
        """Delete sequence with child scenes → error."""
        from tools.story_create import handler as create_handler
        from tools.story_edit import handler as edit_handler

        project_path = _make_project_with_structure(tmp_path)

        create_handler({
            "entity_type": "act", "slug": "act-1", "project": str(project_path),
            "frontmatter": {"title": "Act 1"}
        })
        create_handler({
            "entity_type": "sequence", "slug": "seq-1", "project": str(project_path),
            "frontmatter": {"title": "Seq 1", "act_id": "act-1"}
        })
        create_handler({
            "entity_type": "scene", "slug": "scene-1", "project": str(project_path),
            "frontmatter": {"title": "Scene 1", "sequence_id": "seq-1", "act_id": "act-1"}
        })

        result = edit_handler({
            "action": "delete_entity",
            "target": {"entity_type": "sequence", "slug": "seq-1", "project": str(project_path)},
            "summary": "Delete seq-1"
        })
        parsed = json.loads(result)
        assert "error" in parsed
        assert "Cannot delete" in parsed["error"] or "reference" in parsed["error"]

        # Entity should NOT be soft-deleted
        from core.db import get_db
        conn = get_db(project_path)
        row = conn.execute("SELECT is_deleted FROM entities WHERE id='seq-1'").fetchone()
        assert row[0] == 0
        conn.close()

    def test_delete_act_with_sequences_blocked(self, tmp_path):
        """Delete act with child sequences → error."""
        from tools.story_create import handler as create_handler
        from tools.story_edit import handler as edit_handler

        project_path = _make_project_with_structure(tmp_path)

        create_handler({
            "entity_type": "act", "slug": "act-1", "project": str(project_path),
            "frontmatter": {"title": "Act 1"}
        })
        create_handler({
            "entity_type": "sequence", "slug": "seq-1", "project": str(project_path),
            "frontmatter": {"title": "Seq 1", "act_id": "act-1"}
        })

        result = edit_handler({
            "action": "delete_entity",
            "target": {"entity_type": "act", "slug": "act-1", "project": str(project_path)},
            "summary": "Delete act-1"
        })
        parsed = json.loads(result)
        assert "error" in parsed
        assert "Cannot delete" in parsed["error"] or "reference" in parsed["error"]

        # Entity should NOT be soft-deleted
        from core.db import get_db
        conn = get_db(project_path)
        row = conn.execute("SELECT is_deleted FROM entities WHERE id='act-1'").fetchone()
        assert row[0] == 0
        conn.close()



    def test_delete_character_soft_delete(self, tmp_path):
        """Delete character without children → soft delete in DB."""
        from tools.story_create import handler as create_handler
        from tools.story_edit import handler as edit_handler

        project_path = _make_project_with_structure(tmp_path)

        create_handler({
            "entity_type": "character", "slug": "solo-char", "project": str(project_path),
            "frontmatter": {"name": "Solo", "story_role": "Minor"}
        })

        result = edit_handler({
            "action": "delete_entity",
            "target": {"entity_type": "character", "slug": "solo-char", "project": str(project_path)},
            "summary": "Delete solo-char"
        })
        parsed = json.loads(result)
        assert parsed["success"] is True

        # Verify via direct sqlite3 connection (get_db uses WAL snapshot, may read stale)
        import sqlite3
        conn = sqlite3.connect(str(project_path / ".story" / "story.db"))
        conn.execute("PRAGMA journal_mode=WAL")
        row = conn.execute("SELECT is_deleted FROM entities WHERE id='solo-char'").fetchone()
        conn.close()
        assert row[0] == 1

    def test_create_scene_auto_order(self, tmp_path):
        """Create scene without order → auto-assigned next position."""
        from tools.story_create import handler as create_handler

        project_path = _make_project_with_structure(tmp_path)

        create_handler({
            "entity_type": "act", "slug": "act-1", "project": str(project_path),
            "frontmatter": {"title": "Act 1"}
        })
        create_handler({
            "entity_type": "sequence", "slug": "seq-1", "project": str(project_path),
            "frontmatter": {"title": "Seq 1", "act_id": "act-1"}
        })

        # Create first scene — auto-order = 1
        create_handler({
            "entity_type": "scene", "slug": "scene-a", "project": str(project_path),
            "frontmatter": {"title": "Scene A", "sequence_id": "seq-1", "act_id": "act-1"}
        })
        # Create second scene — auto-order = 2
        result = create_handler({
            "entity_type": "scene", "slug": "scene-b", "project": str(project_path),
            "frontmatter": {"title": "Scene B", "sequence_id": "seq-1", "act_id": "act-1"}
        })
        assert json.loads(result)["success"] is True

        # Verify auto-order in DB
        from core.db import get_db
        conn = get_db(project_path)
        try:
            row_a = conn.execute("SELECT order_key FROM entities WHERE id='scene-a'").fetchone()
            row_b = conn.execute("SELECT order_key FROM entities WHERE id='scene-b'").fetchone()
            assert row_a[0] == 1
            assert row_b[0] == 2
        finally:
            conn.close()

    def test_create_scene_validates_parent(self, tmp_path):
        """Create scene with non-existent sequence_id → error."""
        from tools.story_create import handler as create_handler
        from tools.story_edit import handler as edit_handler

        project_path = _make_project_with_structure(tmp_path)

        create_handler({
            "entity_type": "act", "slug": "act-1", "project": str(project_path),
            "frontmatter": {"title": "Act 1"}
        })

        # No seq-99 exists — scene creation should fail
        result = create_handler({
            "entity_type": "scene", "slug": "orphan", "project": str(project_path),
            "frontmatter": {"title": "Orphan", "sequence_id": "seq-99", "act_id": "act-1"}
        })
        parsed = json.loads(result)
        assert "error" in parsed
        assert "seq-99" in parsed["error"] or "Sequence" in parsed["error"]

        # No scene file should have been created
        assert not (project_path / "scenes" / "orphan.md").exists()

# ---- Phase 4: screenplay stats from DB scene content ----

class TestScreenplayStatsFromSceneContent:
    """Tests for get_screenplay_text → _compute_screenplay_stats pipeline."""

    def test_pipeline_produces_stats_with_scriptHtml(self, tmp_path):
        """_compute_screenplay_stats(get_screenplay_text(...)) returns valid stats incl scriptHtml."""
        from core.db import get_db, get_screenplay_text
        from tools.story_create import handler as create_handler
        import importlib.util

        project_path = tmp_path / "test-project"
        project_path.mkdir()
        (project_path / ".story").mkdir()
        (project_path / "project.md").write_text("---\nname: Test\n---\n")

        create_handler({
            "entity_type": "act", "slug": "act-1", "project": str(project_path),
            "frontmatter": {"title": "Act 1"}
        })
        create_handler({
            "entity_type": "sequence", "slug": "seq-1", "project": str(project_path),
            "frontmatter": {"title": "Seq 1", "act_id": "act-1"}
        })
        create_handler({
            "entity_type": "scene", "slug": "scene-1", "project": str(project_path),
            "frontmatter": {"title": "The Institute", "sequence_id": "seq-1", "act_id": "act-1"}
        })

        # Update the Content section (story_create already created it empty)
        conn = get_db(project_path)
        try:
            conn.execute(
                "UPDATE sections SET body=? WHERE entity_id=? AND heading='Content'",
                ("EXT. THE INSTITUTE - DAY\n\nA vast decaying building.\n\nKAEL (15, intense) stares at a wall of pale light.\n\nKAEL\nSomething's wrong. Everything arrives too perfectly.", "scene-1")
            )
            conn.commit()
        finally:
            conn.close()

        scene_text = get_screenplay_text(project_path)
        assert scene_text, "get_screenplay_text returned empty string"

        spec = importlib.util.spec_from_file_location("story_dashboard", Path("tools/story_dashboard.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        stats = mod._compute_screenplay_stats(scene_text)
        assert stats is not None
        assert "scriptHtml" in stats
        assert stats["scriptHtml"], "scriptHtml should not be empty for valid scene content"
        assert "lengthStats" in stats
        assert stats["lengthStats"]["scenes"] >= 1


# ---- Unfilled Fields Tests ----

class TestUnfilledFields:
    def test_unfilled_fields_character(self):
        from core.entity import unfilled_fields
        extra = {"story_role": "Protagonist", "goals_short": "Goals not set", "goals_long": "Goals not set"}
        result = unfilled_fields("character", extra)
        assert "goals_short" in result
        assert "goals_long" in result

    def test_unfilled_fields_skips_filled(self):
        from core.entity import unfilled_fields
        extra = {"story_role": "Protagonist", "goals_short": "Escaped from prison", "goals_long": "Goals not set"}
        result = unfilled_fields("character", extra)
        assert "goals_short" not in result
        assert "goals_long" in result

    def test_unfilled_fields_only_optional(self):
        from core.entity import unfilled_fields
        # story_role is required (optional: False), should not appear even if at default
        extra = {"story_role": "", "goals_short": "Goals not set"}
        result = unfilled_fields("character", extra)
        assert "story_role" not in result
        assert "goals_short" in result

    def test_unfilled_fields_scene_location(self):
        from core.entity import unfilled_fields
        extra = {"location": "Location not set", "value": "Value not set", "dramatic_role": ""}
        result = unfilled_fields("scene", extra)
        assert "location" in result
        assert "value" in result
        # dramatic_role is at default "" but also optional — should appear
        assert "dramatic_role" in result

    def test_unfilled_fields_plot_type(self):
        from core.entity import unfilled_fields
        extra = {"plot_type": "", "value_arc": "Value arc not set", "one_sentence": "Summary not set"}
        result = unfilled_fields("plot", extra)
        assert "plot_type" in result
        assert "value_arc" in result
        assert "one_sentence" in result

    def test_unfilled_fields_arc_action(self):
        from core.entity import unfilled_fields
        extra = {"action": "Action not described", "gap": "Gap not defined"}
        result = unfilled_fields("arc", extra)
        assert "action" in result
        assert "gap" in result

    def test_unfilled_fields_sequence(self):
        from core.entity import unfilled_fields
        extra = {"value": "Value not set", "purpose": "Purpose not set", "primary_plot": ""}
        result = unfilled_fields("sequence", extra)
        assert "value" in result
        assert "purpose" in result
        assert "primary_plot" in result

    def test_unfilled_fields_act(self):
        from core.entity import unfilled_fields
        extra = {"value": "Value not set", "act_objective": "Objective not set", "climax_scene_id": ""}
        result = unfilled_fields("act", extra)
        assert "value" in result
        assert "act_objective" in result
        assert "climax_scene_id" in result

    def test_get_project_summary_includes_unfilled(self, tmp_path):
        from tools.story_create import handler as create_handler
        from core.db import get_project_summary

        project_path = _make_minimal_project(tmp_path)

        args = {
            "entity_type": "character",
            "slug": "test-char",
            "project": str(project_path),
            "frontmatter": {"name": "Test Char", "story_role": "Protagonist"}
        }
        result = json.loads(create_handler(args))
        assert result["success"]

        summary = get_project_summary(project_path)
        assert "unfilled" in summary
        # Character should have unfilled fields (e.g., goals_short, goals_long)
        char_unfilled = summary["unfilled"].get("test-char", [])
        assert len(char_unfilled) > 0
        # goals_short defaults to "Goals not set", so it should be unfilled
        assert "goals_short" in char_unfilled

    def test_created_character_has_unfilled_fields(self, tmp_path):
        from tools.story_create import handler as create_handler
        from core.db import get_project_summary

        project_path = _make_minimal_project(tmp_path)

        char_args = {
            "entity_type": "character",
            "slug": "test-char",
            "project": str(project_path),
            "frontmatter": {"name": "Test Char", "story_role": "Protagonist"}
        }
        json.loads(create_handler(char_args))

        summary = get_project_summary(project_path)
        char_unfilled = summary["unfilled"].get("test-char", [])
        # goals_short and goals_long should be unfilled (default "Goals not set")
        assert "goals_short" in char_unfilled
        assert "goals_long" in char_unfilled
        # story_role is required and was provided, should NOT be unfilled
        assert "story_role" not in char_unfilled


