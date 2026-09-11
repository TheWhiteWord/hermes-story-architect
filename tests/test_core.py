"""Test suite for Story Architect core modules."""
import pytest
import json
from pathlib import Path
from core.section_parser import list_sections, get_section, replace_section
from core.entity import extract_entity, validate_entity, update_sections
from core.screenplay import extract_scenes, match_character, match_location, extract_location


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

        note_path = project_path / "characters" / "test-char.md"
        import frontmatter as fm
        post = fm.load(note_path)

        # All schema fields should be present
        assert "name" in post.metadata
        assert "story_role" in post.metadata
        assert "one_sentence" in post.metadata
        assert "relationships" in post.metadata
        assert "goals_short" in post.metadata
        assert "goals_long" in post.metadata
        assert "knowledge" in post.metadata

        # Provided values should be preserved
        assert post.metadata["name"] == "Test Char"
        assert post.metadata["story_role"] == "Protagonist"

        # Missing fields should be empty defaults
        assert post.metadata["one_sentence"] == ""
        assert post.metadata["relationships"] == []
        assert post.metadata["goals_short"] == ""
        assert post.metadata["goals_long"] == ""
        assert post.metadata["knowledge"] == []

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

        note_path = project_path / "characters" / "test-char.md"
        import frontmatter as fm
        post = fm.load(note_path)

        # All standard sections should be present
        body = post.content
        assert "## Personality" in body
        assert "## Background" in body
        assert "## Voice" in body
        assert "## Greatest Fear" in body
        assert "## Secrets" in body
        assert "## Arc" in body
        assert "## Relationships" in body
        assert "## Goals" in body

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

        note_path = project_path / "plots" / "test-plot.md"
        import frontmatter as fm
        post = fm.load(note_path)

        # All plot schema fields should be present
        assert "name" in post.metadata
        assert "one_sentence" in post.metadata
        assert "status" in post.metadata
        assert "characters" in post.metadata
        assert "setups" in post.metadata
        assert "payoffs" in post.metadata

        # Provided values preserved
        assert post.metadata["name"] == "Test Plot"

        # Defaults filled in
        assert post.metadata["status"] == "active"
        assert post.metadata["characters"] == []
        assert post.metadata["setups"] == []
        assert post.metadata["payoffs"] == []

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

        note_path = project_path / "plots" / "test-plot.md"
        import frontmatter as fm
        post = fm.load(note_path)

        body = post.content
        assert "## Summary" in body
        assert "## Obstacles" in body
        assert "## Stakes" in body


# ---- Integration Test ----

class TestIndexGeneration:
    def test_generate_index(self, project_path):
        from core.index import generate_index
        index = generate_index(project_path)
        
        assert index["project"]["name"] == "Save the Children"
        assert len(index["characters"]) == 6
        assert len(index["locations"]) == 2
        assert len(index["worlds"]) == 2
        assert len(index["plots"]) == 2
        assert len(index["scenes"]) == 9
        
        # Check character scenes were synced from screenplay
        kael = next(c for c in index["characters"] if c["id"] == "kael")
        assert len(kael["scenes"]) > 0
        
        # Check scene characters were matched
        scene1 = next(s for s in index["scenes"] if s["id"] == 1)
        assert isinstance(scene1["characters"], list)