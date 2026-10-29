"""Test suite for Story Architect core modules."""
import pytest
import json
from pathlib import Path
from story_architect.core.section_parser import list_sections, get_section, replace_section
from story_architect.core.entity import extract_entity, validate_entity, update_sections
from story_architect.core.screenplay import extract_scenes, match_character, match_location, extract_location
from story_architect.core.constants import ENTITY_SCHEMAS
from story_architect.core.writes import (create_entity, create_project, delete_entity,
                          edit_entity, reorder)


# ---- Imports for tool tests ----
from story_architect.tools.story_load import handler as load_handler


# ---- Fixtures ----

@pytest.fixture
def project_path():
    """Path to the test fixture project."""
    return Path(__file__).parent / "fixtures" / "save-the-children"


@pytest.fixture
def kael_note(project_path):
    """Path to Kael's character note — `Kael.md`, named for the title."""
    return project_path / "characters" / "Kael.md"


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
        assert "Identity" in entity["sections"]
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

    def test_non_event_scene_is_valid(self):
        """A non-event scene is legal with no value fields at all.

        Value lives in `value_turns` since the B1/B2 redesign; a scene that
        serves no plot simply has none.
        """
        warnings = validate_entity("scene", {
            "title": "Test", "sequence_id": "seq-1", "act_id": "act-1",
            "dramatic_role": "non-event",
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
        entity = extract_entity(project_path / "worlds" / "The I.md", "world")
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

        project_path = _make_minimal_project(tmp_path)

        result = create_entity(project_path, "character", "test-char",
            {"name": "Test Char", "story_role": "Protagonist"})
        assert result["success"] == True

        from story_architect.core.db import get_db
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
            # B12: an unfilled optional field is stored empty. It used to be
            # stored as the prose "Goals not set", which the enum check then
            # rejected as a value the user had actually chosen.
            assert extra["goals_short"] == ""
            assert extra["goals_long"] == ""
            assert extra["knowledge"] == []
        finally:
            conn.close()

    def test_create_character_has_all_sections(self, tmp_path):
        """Creating a character should produce all standard body sections."""

        project_path = _make_minimal_project(tmp_path)

        result = create_entity(project_path, "character", "test-char",
            {"name": "Test Char", "story_role": "Protagonist"})
        assert result["success"] == True

        from story_architect.core.db import get_db
        conn = get_db(project_path)
        try:
            rows = conn.execute(
                "SELECT heading FROM sections WHERE entity_id='test-char' ORDER BY rowid"
            ).fetchall()
            headings = [r[0] for r in rows]
            assert "Identity" in headings
            assert "Desires" in headings
            assert "Background" in headings
            assert "Contradictions" in headings
            assert "Psychology" in headings
            assert "Arc" in headings
            assert "Relationships" in headings
            assert "Voice" in headings
            assert "Notes" in headings
        finally:
            conn.close()

    def test_create_plot_has_all_fields(self, tmp_path):
        """Creating a plot with minimal fields should produce all fields."""

        project_path = _make_minimal_project(tmp_path)

        result = create_entity(project_path, "plot", "test-plot",
            {"name": "Test Plot"})
        assert result["success"] == True

        from story_architect.core.db import get_db
        conn = get_db(project_path)
        try:
            row = conn.execute(
                "SELECT name, one_sentence, status, extra FROM entities WHERE id='test-plot' AND type='plot'"
            ).fetchone()
            assert row is not None
            assert row[0] == "Test Plot"
            assert row[1] == ""  # one_sentence is a column, and unfilled (B12)
            assert row[2] == "active"
            extra = json.loads(row[3])
            assert extra["characters"] == []
            # role fields are relation fields, not extra JSON
        finally:
            conn.close()

    def test_create_plot_has_all_sections(self, tmp_path):
        """Creating a plot should produce all standard body sections."""

        project_path = _make_minimal_project(tmp_path)

        result = create_entity(project_path, "plot", "test-plot",
            {"name": "Test Plot"})
        assert result["success"] == True

        from story_architect.core.db import get_db
        conn = get_db(project_path)
        try:
            rows = conn.execute(
                "SELECT heading FROM sections WHERE entity_id='test-plot' ORDER BY rowid"
            ).fetchall()
            headings = [r[0] for r in rows]
            assert "Summary" in headings
            assert "Role" in headings
            assert "Threads" in headings
            assert "Value" in headings
            assert "Characters" in headings
            assert "Notes" in headings
        finally:
            conn.close()

    def test_create_plot_with_scope_and_arc(self, tmp_path):
        """Creating a plot with plot_scope and value_arc."""
        from story_architect.core.db import get_db

        project_path = _make_minimal_project(tmp_path)

        result = create_entity(project_path, "plot", "main-plot",
            {"name": "Main Plot", "plot_scope": "main", "value_arc": "Maturation"})
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
        from story_architect.core.entity import validate_entity
        warnings = validate_entity("plot", {"name": "Test", "status": "active", "plot_scope": "invalid"})
        assert any("Invalid plot_scope: invalid" in w for w in warnings)

    def test_validate_plot_invalid_value_arc(self):
        """validate_entity('plot', {value_arc: 'invalid'}) returns warning."""
        from story_architect.core.entity import validate_entity
        warnings = validate_entity("plot", {"name": "Test", "status": "active", "value_arc": "invalid"})
        assert any("Invalid value_arc: invalid" in w for w in warnings)

    def test_validate_plot_valid_scope_and_arc(self):
        """validate_entity accepts valid plot_scope and value_arc."""
        from story_architect.core.entity import validate_entity
        warnings = validate_entity("plot", {"name": "Test", "status": "active", "plot_scope": "main", "value_arc": "Maturation"})
        assert not any("Invalid" in w for w in warnings)

    def test_create_scene_has_all_fields_and_sections(self, tmp_path):
        """Creating a scene with minimal fields should still produce all fields and body sections."""

        project_path = _make_minimal_project(tmp_path)

        # Create parent entities first (required for scene validation)
        create_entity(project_path, "act", "act-1",
            {"title": "Act 1"})
        create_entity(project_path, "sequence", "seq-1",
            {"title": "Seq 1", "act_id": "act-1"})

        result = create_entity(project_path, "scene", "test-scene",
            {"title": "Test Scene", "sequence_id": "seq-1", "act_id": "act-1"})
        assert result["success"] == True

        from story_architect.core.db import get_db
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
            assert "Content" in headings
            assert "Objective" in headings
            # Conflict and Beats stay on the scene: it is created first, so it
            # is where the scene is planned. `scene_beats` keeps its own
            # Conflict/Findings for how the finished scene works.
            assert "Conflict" in headings
            assert "Beats" in headings
            assert "Value Turn" in headings
            assert "Dramatic Function" in headings
            assert "Production" in headings
            assert "Notes" in headings
        finally:
            conn.close()

    def test_create_sequence_has_all_fields_and_sections(self, tmp_path):
        """Creating a sequence should produce all fields and body sections."""

        project_path = _make_minimal_project(tmp_path)

        # Create parent act first (required for sequence validation)
        create_entity(project_path, "act", "act-1",
            {"title": "Act 1"})

        result = create_entity(project_path, "sequence", "test-sequence",
            {"title": "Test Sequence", "act_id": "act-1"})
        assert result["success"] == True

        from story_architect.core.db import get_db
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
            assert "Purpose" in headings
            assert "Value Arc" in headings
            assert "Progression" in headings
            assert "Sequence Climax" in headings
            assert "Plots" in headings
            assert "Notes" in headings
        finally:
            conn.close()

    def test_create_act_has_all_fields_and_sections(self, tmp_path):
        """Creating an act should produce all fields and body sections."""

        project_path = _make_minimal_project(tmp_path)

        result = create_entity(project_path, "act", "test-act",
            {"title": "Test Act"})
        assert result["success"] == True

        from story_architect.core.db import get_db
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
            assert "Objective" in headings
            assert "Value Arc" in headings
            assert "Reversal" in headings
            assert "Notes" in headings
        finally:
            conn.close()


class TestProjectCreation:
    """Tests for create_project."""

    def test_create_project_is_db_only(self, tmp_path):
        create_project("test-proj", {"name": "Test Project", "logline": "A test"}, tmp_path)
        proj = tmp_path / "projects" / "test-proj"
        assert (proj / ".story" / "story.db").exists()
        assert not (proj / "project.md").exists()
        for folder in ["characters", "locations", "worlds", "plots", "scenes", "sequences", "acts", "arcs"]:
            assert not (proj / folder).exists(), f"Unexpected folder: {folder}"

    def test_create_project_does_not_create_project_markdown(self, tmp_path):
        create_project("test-proj", {"name": "Test Project"}, tmp_path)
        assert not (tmp_path / "projects" / "test-proj" / "project.md").exists()

    def test_create_project_does_not_require_memory_file(self, tmp_path):
        create_project("test-proj", {"name": "Test Project"}, tmp_path)
        project = tmp_path / "projects" / "test-proj"
        assert not (project / ".story" / "memory.md").exists()
        from story_architect.core.db import get_db, get_project_memory, empty_memory
        conn = get_db(project)
        try:
            extra = json.loads(conn.execute("SELECT extra FROM entities WHERE type='project'").fetchone()[0])
        finally:
            conn.close()
        assert extra["memory"] == empty_memory()
        assert get_project_memory(project) == empty_memory()

    def test_create_project_creates_db(self, tmp_path):
        result = create_project("test-proj", {"name": "Test Project"}, tmp_path)
        assert result["success"] is True
        db_path = tmp_path / "projects" / "test-proj" / ".story" / "story.db"
        assert db_path.exists()
        from story_architect.core.db import get_db
        conn = get_db(tmp_path / "projects" / "test-proj")
        try:
            row = conn.execute("SELECT name, type FROM entities WHERE id='test-proj' AND type='project'").fetchone()
            assert row is not None
            assert row[0] == "Test Project"
        finally:
            conn.close()

    def test_create_project_validates_required_fields(self, tmp_path):
        with pytest.raises(ValueError, match="Missing required"):
            create_project("test-proj", {}, tmp_path)

    def test_create_project_idempotent(self, tmp_path):
        create_project("test-proj", {"name": "Test Project"}, tmp_path)
        with pytest.raises(ValueError):
            create_project("test-proj", {"name": "Test Project"}, tmp_path)

    def test_story_load_works_after_create(self, tmp_path):
        create_project("test-proj", {"name": "Test Project"}, tmp_path)
        load_args = {"project": str(tmp_path / "projects" / "test-proj")}
        result = json.loads(load_handler(load_args, root_path=str(tmp_path)))
        assert result["loaded"] is True
        assert result["project"]["name"] == "Test Project"
        # Nested structure present
        assert "acts" in result
        assert "characters" in result
        assert "plots" in result
        assert "worlds" in result
        assert "orphaned_locations" not in result or isinstance(result["orphaned_locations"], list)
        assert "unfilled" not in result  # moved to view="unfilled" (task_21 spec §3.5)
        assert "memory" in result
        assert "memory_outline" not in result
        assert set(result["memory"]["categories"]) == {
            "decisions", "directions", "open_questions", "continuity_warnings"
        }
        # Old keys gone
        assert "entities" not in result


def _make_project_with_structure(tmp):
    """Create a project with acts/sequences/scenes folders for tool surface tests."""
    project_path = _make_minimal_project(tmp)
    (project_path / "scenes").mkdir(parents=True, exist_ok=True)
    (project_path / "sequences").mkdir(parents=True, exist_ok=True)
    (project_path / "acts").mkdir(parents=True, exist_ok=True)
    return project_path


class TestPhase3ToolSurface:
    """Tests for Phase 3: edit data bag, reorder, cascade blocking, auto-order, parent validation."""

    def test_edit_note_with_data_bag(self, tmp_path):
        """edit_entity with a data bag updates entity columns + sections in DB."""
        project_path = _make_project_with_structure(tmp_path)

        # Create parents (now writes DB directly)
        create_entity(project_path, "act", "act-1",
            {"title": "Act 1"})
        create_entity(project_path, "sequence", "seq-1",
            {"title": "Seq 1", "act_id": "act-1"})
        create_entity(project_path, "scene", "test-scene",
            {"title": "Test Scene", "sequence_id": "seq-1", "act_id": "act-1"})

        # Edit with data bag: frontmatter field + body section
        result = edit_entity(project_path, "scene", "test-scene",
            {"status": "written", "Content": "Updated content text."},
            "Update status and content")
        assert result["success"] is True

        # Assert on DB state
        from story_architect.core.db import get_db
        conn = get_db(project_path)
        row = conn.execute("SELECT status FROM entities WHERE id='test-scene'").fetchone()
        assert row[0] == "written"
        sec_row = conn.execute(
            "SELECT body FROM sections WHERE entity_id='test-scene' AND heading='Content'"
        ).fetchone()
        assert "Updated content text." in sec_row[0]
        conn.close()

    def test_reorder_scene_within_sequence(self, tmp_path):
        """Reorder scenes → order_key renumbered 1-2-3 in DB."""
        from story_architect.core.db import get_db

        project_path = _make_project_with_structure(tmp_path)

        create_entity(project_path, "act", "act-1",
            {"title": "Act 1"})
        create_entity(project_path, "sequence", "seq-1",
            {"title": "Seq 1", "act_id": "act-1"})
        for slug in ["scene-1", "scene-2", "scene-3"]:
            create_entity(project_path, "scene", slug,
                {"title": f"Scene {slug[-1]}", "sequence_id": "seq-1", "act_id": "act-1"})

        # Reorder: move scene-3 to front
        result = reorder(project_path, "scene", ["scene-3", "scene-1", "scene-2"],
                         "Reorder scenes")
        assert result["success"] is True

        # Assert DB order_key values
        conn = get_db(project_path)
        try:
            rows = conn.execute(
                "SELECT id, order_key FROM entities WHERE type='scene' ORDER BY order_key"
            ).fetchall()
            assert [r[0] for r in rows] == ["scene-3", "scene-1", "scene-2"]
            assert [r[1] for r in rows] == [1, 2, 3]
        finally:
            conn.close()

    def test_delete_sequence_with_scenes_blocked(self, tmp_path):
        """Delete sequence with child scenes → refused."""
        project_path = _make_project_with_structure(tmp_path)

        create_entity(project_path, "act", "act-1",
            {"title": "Act 1"})
        create_entity(project_path, "sequence", "seq-1",
            {"title": "Seq 1", "act_id": "act-1"})
        create_entity(project_path, "scene", "scene-1",
            {"title": "Scene 1", "sequence_id": "seq-1", "act_id": "act-1"})

        result = delete_entity(project_path, "sequence", "seq-1",
                               "Delete seq-1", True)
        assert "Cannot delete" in result["error"]
        assert [c["id"] for c in result["blocking_children"]] == ["scene-1"]

        # Entity should still exist (delete was blocked)
        from story_architect.core.db import get_db
        conn = get_db(project_path)
        row = conn.execute("SELECT id FROM entities WHERE id='seq-1'").fetchone()
        assert row is not None
        conn.close()

    def test_delete_act_with_sequences_blocked(self, tmp_path):
        """Delete act with child sequences → refused."""
        project_path = _make_project_with_structure(tmp_path)

        create_entity(project_path, "act", "act-1",
            {"title": "Act 1"})
        create_entity(project_path, "sequence", "seq-1",
            {"title": "Seq 1", "act_id": "act-1"})

        result = delete_entity(project_path, "act", "act-1", "Delete act-1", True)
        assert "Cannot delete" in result["error"]
        assert [c["id"] for c in result["blocking_children"]] == ["seq-1"]

        # Entity should still exist (delete was blocked)
        from story_architect.core.db import get_db
        conn = get_db(project_path)
        row = conn.execute("SELECT id FROM entities WHERE id='act-1'").fetchone()
        assert row is not None
        conn.close()



    def test_delete_character_soft_delete(self, tmp_path):
        """Delete character without children → gone from every read."""
        project_path = _make_project_with_structure(tmp_path)

        create_entity(project_path, "character", "solo-char",
            {"name": "Solo", "story_role": "Minor"})

        result = delete_entity(project_path, "character", "solo-char",
                               "Delete solo-char", True)
        assert result["success"] is True

        # The row survives, flagged — that is what makes restore an exact
        # inverse (task_18 soft delete). What must be true is that no reader
        # can see it any more.
        import sqlite3
        conn = sqlite3.connect(str(project_path / ".story" / "story.db"))
        conn.execute("PRAGMA journal_mode=WAL")
        row = conn.execute(
            "SELECT is_deleted FROM entities WHERE id='solo-char'").fetchone()
        live = conn.execute(
            "SELECT count(*) FROM entities WHERE id='solo-char' AND is_deleted=0"
        ).fetchone()[0]
        conn.close()
        assert row == (1,), "delete must flag the row, not erase it"
        assert live == 0, "deleted entity must be invisible to readers"

    def test_create_scene_auto_order(self, tmp_path):
        """Create scene without order → auto-assigned next position."""
        project_path = _make_project_with_structure(tmp_path)

        create_entity(project_path, "act", "act-1",
            {"title": "Act 1"})
        create_entity(project_path, "sequence", "seq-1",
            {"title": "Seq 1", "act_id": "act-1"})

        # Create first scene — auto-order = 1
        create_entity(project_path, "scene", "scene-a",
            {"title": "Scene A", "sequence_id": "seq-1", "act_id": "act-1"})
        # Create second scene — auto-order = 2
        result = create_entity(project_path, "scene", "scene-b",
            {"title": "Scene B", "sequence_id": "seq-1", "act_id": "act-1"})
        assert result["success"] is True

        # Verify auto-order in DB
        from story_architect.core.db import get_db
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
        project_path = _make_project_with_structure(tmp_path)

        create_entity(project_path, "act", "act-1",
            {"title": "Act 1"})

        # No seq-99 exists — scene creation should fail
        with pytest.raises(ValueError, match="seq-99|Sequence"):
            create_entity(project_path, "scene", "orphan",
                {"title": "Orphan", "sequence_id": "seq-99", "act_id": "act-1"})

# ---- Phase 4: screenplay stats from DB scene content ----

class TestScreenplayStatsFromSceneContent:
    """Tests for get_screenplay_text → _compute_screenplay_stats pipeline."""

    def test_pipeline_produces_stats_with_scriptHtml(self, tmp_path):
        """_compute_screenplay_stats(get_screenplay_text(...)) returns valid stats incl scriptHtml."""
        from story_architect.core.db import get_db, get_screenplay_text
        import importlib.util

        project_path = tmp_path / "test-project"
        project_path.mkdir()
        (project_path / ".story").mkdir()
        (project_path / "project.md").write_text("---\nname: Test\n---\n")

        create_entity(project_path, "act", "act-1",
            {"title": "Act 1"})
        create_entity(project_path, "sequence", "seq-1",
            {"title": "Seq 1", "act_id": "act-1"})
        create_entity(project_path, "scene", "scene-1",
            {"title": "The Institute", "sequence_id": "seq-1", "act_id": "act-1"})

        # Update the Content section (created empty alongside the entity)
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
        from story_architect.core.entity import unfilled_fields
        extra = {"story_role": "Protagonist", "goals_short": "", "goals_long": ""}
        result = unfilled_fields("character", extra)
        assert "goals_short" in result
        assert "goals_long" in result

    def test_unfilled_fields_skips_filled(self):
        from story_architect.core.entity import unfilled_fields
        extra = {"story_role": "Protagonist", "goals_short": "Escaped from prison", "goals_long": ""}
        result = unfilled_fields("character", extra)
        assert "goals_short" not in result
        assert "goals_long" in result

    def test_unfilled_fields_only_optional(self):
        from story_architect.core.entity import unfilled_fields
        # story_role is required (optional: False), should not appear even if at default
        extra = {"story_role": "", "goals_short": ""}
        result = unfilled_fields("character", extra)
        assert "story_role" not in result
        assert "goals_short" in result

    def test_unfilled_fields_scene_location(self):
        from story_architect.core.entity import unfilled_fields
        extra = {"location": "", "heading": "", "dramatic_role": ""}
        result = unfilled_fields("scene", extra)
        assert "location" in result
        assert "heading" in result
        # dramatic_role is at default "" but also optional — should appear
        assert "dramatic_role" in result

    def test_unfilled_fields_plot_type(self):
        from story_architect.core.entity import unfilled_fields
        extra = {"plot_type": "", "value_arc": "", "one_sentence": ""}
        result = unfilled_fields("plot", extra)
        assert "plot_type" in result
        assert "value_arc" in result
        assert "one_sentence" in result

    def test_unfilled_fields_skips_status(self):
        """status is a workflow state, never reported as unfilled."""
        from story_architect.core.entity import unfilled_fields
        extra = {"status": "planned", "heading": "", "dramatic_role": ""}
        result = unfilled_fields("scene", extra)
        assert "status" not in result
        assert "heading" in result
        assert "dramatic_role" in result

    def test_unfilled_fields_skips_booleans(self):
        """Boolean fields are not 'unfilled'."""
        from story_architect.core.entity import unfilled_fields
        extra = {"is_crisis": False, "is_climax": False, "action": ""}
        result = unfilled_fields("scene_beats", extra)
        assert "is_crisis" not in result
        assert "is_climax" not in result

    def test_unfilled_fields_skips_numbers(self):
        """Numeric fields (act_count) are not 'unfilled'."""
        from story_architect.core.entity import unfilled_fields
        extra = {"act_count": 0, "action": ""}
        result = unfilled_fields("project", extra)
        assert "act_count" not in result

    def test_unfilled_fields_plot_scope_empty(self):
        """plot_scope at empty default is flagged; at 'main' is not."""
        from story_architect.core.entity import unfilled_fields
        extra_empty = {"plot_scope": ""}
        result = unfilled_fields("plot", extra_empty)
        assert "plot_scope" in result
        extra_main = {"plot_scope": "main"}
        result = unfilled_fields("plot", extra_main)
        assert "plot_scope" not in result

    def test_unfilled_fields_subfields_perspectives(self):
        """perspectives: bare → parent name; partial → parent.key per missing char."""
        from story_architect.core.entity import unfilled_fields
        bare = {"name": "Kael & Mira", "characters": ["kael", "mira"]}
        assert "perspectives" in unfilled_fields("relationship", bare)
        partial = {**bare, "perspectives": {"kael": {"label": "Friend"}}}
        result = unfilled_fields("relationship", partial)
        assert "perspectives" not in result
        assert "perspectives.mira" in result
        assert "perspectives.kael" not in result
        full = {**bare, "perspectives": {"kael": {"label": "Friend"}, "mira": {"label": "Anchor"}}}
        assert "perspectives.mira" not in unfilled_fields("relationship", full)

    def test_unfilled_fields_subfields_plot_beats(self):
        """Both sides report the gap now, and they mean different things.

        The plot's six role fields are computed, and it used to follow that
        they were therefore never gaps — the reasoning being that a derived
        value has no stored value to be missing. But a plot whose crisis is
        unfulfilled IS missing its crisis, and an author asking the plot what
        it still needs was told nothing. So the role fields are reported, while
        remaining unwritable: the scene's `plot_roles` is where a role is
        actually written, and it follows the sub_fields rule (an entry present
        = filled).
        """
        from story_architect.core.entity import unfilled_fields
        # The plot side: an unfilled role is named. All five, every time —
        # that is the question "what does this plot still need".
        bare = {"name": "X", "status": "active"}
        result = unfilled_fields("plot", bare)
        for field in ("setups", "complications", "crisis", "climax",
                      "resolutions"):
            assert field in result, f"{field} is an unfulfilled plot role"

        # And it stops being reported once the role row exists.
        filled = {"name": "X", "status": "active", "crisis": [1]}
        assert "crisis" not in unfilled_fields("plot", filled)

        # The scene side: no roles written is a real gap, one entry is filled.
        assert "plot_roles" in unfilled_fields("scene", {"title": "S"})
        with_role = {"title": "S", "plot_roles": [
            {"plot": "the-plot", "role": "setup", "description": "d"}]}
        assert "plot_roles" not in unfilled_fields("scene", with_role)

    def test_unfilled_fields_sequence(self):
        from story_architect.core.entity import unfilled_fields
        extra = {"purpose": "", "primary_plot": ""}
        result = unfilled_fields("sequence", extra)
        assert "purpose" in result
        assert "primary_plot" in result

    def test_unfilled_fields_act(self):
        from story_architect.core.entity import unfilled_fields
        extra = {"act_objective": ""}
        result = unfilled_fields("act", extra)
        assert "act_objective" in result

    def test_get_unfilled_map(self, tmp_path):
        from story_architect.core.db import get_unfilled_map

        project_path = _make_minimal_project(tmp_path)

        result = create_entity(project_path, "character", "test-char",
            {"name": "Test Char", "story_role": "Protagonist"})
        assert result["success"]

        unfilled = get_unfilled_map(project_path)
        # Inverted shape — field name → [entity slugs]
        assert "goals_short" in unfilled
        assert "test-char" in unfilled["goals_short"]
        assert "goals_long" in unfilled

    def test_get_project_summary_excludes_unfilled(self, tmp_path):
        from story_architect.core.db import get_project_summary

        project_path = _make_minimal_project(tmp_path)

        create_entity(project_path, "character", "test-char",
            {"name": "Test Char", "story_role": "Protagonist"})

        summary = get_project_summary(project_path)
        # Unfilled moved to view="unfilled" (task_21 spec §3.5) — backend get_unfilled_map
        assert "unfilled" not in summary


# ---- Value Schema Tests (task_27 phase 1) ----

# A scene's turn is `value_turns`, whose words come from a `value` entity.

