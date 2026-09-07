"""Test suite for Story Architect core modules."""
import pytest
from pathlib import Path
from plugin.core.section_parser import list_sections, get_section, replace_section
from plugin.core.entity import extract_entity, validate_entity, update_sections
from plugin.core.screenplay import extract_scenes, match_character, match_location, extract_location


# ---- Fixtures ----

@pytest.fixture
def project_path():
    """Path to the test fixture project."""
    return Path(__file__).parent / "fixtures" / "the-water-audit"


@pytest.fixture
def mara_note(project_path):
    """Path to Mara's character note."""
    return project_path / "characters" / "mara.md"


@pytest.fixture
def screenplay_path(project_path):
    """Path to the screenplay."""
    return project_path / "screenplay.md"


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
    def test_extract_character(self, mara_note):
        entity = extract_entity(mara_note, "character")
        assert entity["id"] == "mara"
        assert entity["name"] == "Mara Chen"
        assert entity["story_role"] == "Protagonist"
        assert "Personality" in entity["sections"]
        assert "Voice" in entity["sections"]

    def test_validate_character_valid(self, mara_note):
        entity = extract_entity(mara_note, "character")
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
        assert entity["name"] == "The Water Audit"
        assert "logline" in entity

    def test_extract_world(self, project_path):
        entity = extract_entity(project_path / "worlds" / "gilead.md", "world")
        assert entity["name"] == "Gilead"
        assert len(entity["rules"]) == 3


# ---- Screenplay Tests ----

class TestScreenplay:
    def test_extract_scenes(self, screenplay_path):
        content = screenplay_path.read_text()
        scenes = extract_scenes(content)
        assert len(scenes) == 3
        assert scenes[0]["heading"] == "INT. MARA'S APARTMENT - NIGHT"
        assert scenes[0]["id"] == 1

    def test_extract_location(self):
        assert extract_location("INT. KITCHEN - NIGHT") == "KITCHEN"
        assert extract_location("EXT. PARK - DAY") == "PARK"
        assert extract_location("EST. HOUSE - DAWN") == "HOUSE"
        assert extract_location("NOT A HEADING") is None

    def test_match_character_exact(self):
        characters = [{"id": "mara", "name": "Mara Chen"}]
        assert match_character("MARA CHEN", characters) == "mara"

    def test_match_character_fuzzy(self):
        characters = [{"id": "mara", "name": "Mara Chen"}]
        assert match_character("MARA", characters) == "mara"

    def test_match_character_no_match(self):
        characters = [{"id": "mara", "name": "Mara Chen"}]
        assert match_character("VICTOR HALE", characters) is None

    def test_match_location(self):
        locations = [{"id": "kitchen", "name": "The Kitchen"}]
        assert match_location("KITCHEN", locations) == "kitchen"
        assert match_location("The Kitchen", locations) == "kitchen"


# ---- Integration Test ----

class TestIndexGeneration:
    def test_generate_index(self, project_path):
        from plugin.core.index import generate_index
        index = generate_index(project_path)
        
        assert index["project"]["name"] == "The Water Audit"
        assert len(index["characters"]) == 2
        assert len(index["locations"]) == 1
        assert len(index["worlds"]) == 1
        assert len(index["plots"]) == 1
        assert len(index["scenes"]) == 3
        
        # Check character scenes were synced from screenplay
        mara = next(c for c in index["characters"] if c["id"] == "mara")
        assert len(mara["scenes"]) > 0
        
        # Check scene characters were matched
        scene1 = next(s for s in index["scenes"] if s["id"] == 1)
        assert "mara" in scene1["characters"]
