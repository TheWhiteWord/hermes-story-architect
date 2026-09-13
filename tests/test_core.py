"""Test suite for Story Architect core modules."""
import pytest
import json
from pathlib import Path
from core.section_parser import list_sections, get_section, replace_section
from core.entity import extract_entity, validate_entity, update_sections
from core.screenplay import extract_scenes, match_character, match_location, extract_location
from core.constants import ENTITY_SCHEMAS


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

        note_path = project_path / "scenes" / "test-scene.md"
        import frontmatter as fm
        post = fm.load(note_path)

        # All schema fields should be present
        for field in ENTITY_SCHEMAS["scene"]:
            assert field in post.metadata, f"Missing field: {field}"

        # Provided values preserved
        assert post.metadata["title"] == "Test Scene"
        assert post.metadata["sequence_id"] == "seq-1"
        assert post.metadata["act_id"] == "act-1"

        # Missing fields should be empty defaults
        assert post.metadata["status"] == "planned"
        # Auto-order assigned since parent exists
        assert post.metadata["order"] == 1
        assert post.metadata["characters"] == []
        assert post.metadata["plots"] == []

        # All standard sections should be present
        body = post.content
        assert "## Description" in body
        assert "## Dramatic Function" in body
        assert "## Notes" in body
        assert "## Content" in body

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

        note_path = project_path / "sequences" / "test-sequence.md"
        import frontmatter as fm
        post = fm.load(note_path)

        for field in ENTITY_SCHEMAS["sequence"]:
            assert field in post.metadata, f"Missing field: {field}"

        assert post.metadata["title"] == "Test Sequence"
        assert post.metadata["act_id"] == "act-1"
        assert post.metadata["status"] == "planned"
        # Auto-order assigned since parent exists
        assert post.metadata["order"] == 1

        body = post.content
        assert "## Summary" in body
        assert "## Scene Order" in body
        assert "## Notes" in body

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

        note_path = project_path / "acts" / "test-act.md"
        import frontmatter as fm
        post = fm.load(note_path)

        for field in ENTITY_SCHEMAS["act"]:
            assert field in post.metadata, f"Missing field: {field}"

        assert post.metadata["title"] == "Test Act"
        assert post.metadata["status"] == "planned"
        assert post.metadata["order"] == 0

        body = post.content
        assert "## Summary" in body
        assert "## Thematic Function" in body
        assert "## Notes" in body


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
        # Phase 2: scenes come from files only — fixture now has 3 scene files
        assert len(index["scenes"]) == 3
        assert len(index["sequences"]) == 1
        assert len(index["acts"]) == 1
        
        # Character scenes come from file scenes only
        kael = next(c for c in index["characters"] if c["id"] == "kael")
        assert len(kael.get("scenes", [])) == 3  # central-room-day, central-room-night, the-core-day

        mira = next(c for c in index["characters"] if c["id"] == "mira")
        assert len(mira.get("scenes", [])) == 2  # central-room-day, the-core-day

        # Location scenes from file scenes
        central_room = next(l for l in index["locations"] if l["id"] == "the-central-room")
        assert len(central_room.get("scenes", [])) == 2  # central-room-day, central-room-night

        # Sequence and act counts
        assert index["project"]["sequence_count"] == 1
        assert index["project"]["act_count"] == 1


class TestSceneIndex:
    """Tests for scene/sequence/act index generation (Task 3)."""

    def test_index_includes_scenes_from_files(self, tmp_path):
        """generate_index walks scenes/ folder and includes entries."""
        from core.index import generate_index

        project_path = tmp_path / "proj"
        project_path.mkdir()
        (project_path / "scenes").mkdir()
        (project_path / "project.md").write_text("---\nname: Test\n---\n")

        (project_path / "scenes" / "test-scene.md").write_text(
            "---\nid: test-scene\ntitle: Test Scene\nsequence_id: seq-1\nact_id: act-1\n---\n"
        )

        index = generate_index(project_path)
        scene_ids = [s["id"] for s in index["scenes"]]
        assert "test-scene" in scene_ids

    def test_index_includes_sequences_and_acts(self, tmp_path):
        """generate_index parses sequences/ and acts/ folders."""
        from core.index import generate_index

        project_path = tmp_path / "proj"
        project_path.mkdir()
        (project_path / "sequences").mkdir()
        (project_path / "acts").mkdir()
        (project_path / "project.md").write_text("---\nname: Test\n---\n")

        (project_path / "sequences" / "seq-1.md").write_text(
            "---\nid: seq-1\ntitle: Seq One\nact_id: act-1\n---\n"
        )
        (project_path / "acts" / "act-1.md").write_text(
            "---\nid: act-1\ntitle: Act One\n---\n"
        )

        index = generate_index(project_path)
        assert len(index["sequences"]) == 1
        assert len(index["acts"]) == 1
        assert index["project"]["sequence_count"] == 1
        assert index["project"]["act_count"] == 1

    def test_project_has_sequence_and_act_counts(self, tmp_path):
        """_parse_project adds sequence_count and act_count."""
        from core.index import generate_index

        project_path = tmp_path / "proj"
        project_path.mkdir()
        (project_path / "project.md").write_text("---\nname: Test\n---\n")

        index = generate_index(project_path)
        assert index["project"]["sequence_count"] == 0
        assert index["project"]["act_count"] == 0

    def test_index_cross_reference_validation(self, tmp_path, capsys):
        """Scene with non-existent sequence_id triggers validation warning."""
        from core.index import generate_index

        project_path = tmp_path / "proj"
        project_path.mkdir()
        (project_path / "scenes").mkdir()
        (project_path / "project.md").write_text("---\nname: Test\n---\n")

        (project_path / "scenes" / "orphan.md").write_text(
            "---\nid: orphan\ntitle: Orphan\nsequence_id: nonexistent\nact_id: act-1\n---\n"
        )

        index = generate_index(project_path)
        captured = capsys.readouterr()
        assert "unknown sequence" in captured.out

    def test_scene_act_mismatch_warns(self, tmp_path, capsys):
        """Scene.act_id != sequence.act_id triggers warning."""
        from core.index import generate_index

        project_path = tmp_path / "proj"
        project_path.mkdir()
        (project_path / "scenes").mkdir()
        (project_path / "sequences").mkdir()
        (project_path / "acts").mkdir()
        (project_path / "project.md").write_text("---\nname: Test\n---\n")

        (project_path / "sequences" / "seq-1.md").write_text(
            "---\nid: seq-1\ntitle: Seq\nact_id: act-a\n---\n"
        )
        (project_path / "scenes" / "scene-1.md").write_text(
            "---\nid: scene-1\ntitle: Scene\nsequence_id: seq-1\nact_id: act-b\n---\n"
        )

        index = generate_index(project_path)
        captured = capsys.readouterr()
        assert "act_id" in captured.out

    def test_enriches_structure_lists(self, tmp_path):
        """_enrich_structure builds sequence.scenes_list, act.sequences_list, act.scenes_list."""
        from core.index import generate_index

        project_path = tmp_path / "proj"
        project_path.mkdir()
        (project_path / "scenes").mkdir()
        (project_path / "sequences").mkdir()
        (project_path / "acts").mkdir()
        (project_path / "project.md").write_text("---\nname: Test\n---\n")

        (project_path / "sequences" / "seq-1.md").write_text(
            "---\nid: seq-1\ntitle: Seq One\nact_id: act-1\norder: 1\n---\n"
        )
        (project_path / "sequences" / "seq-2.md").write_text(
            "---\nid: seq-2\ntitle: Seq Two\nact_id: act-1\norder: 2\n---\n"
        )
        (project_path / "acts" / "act-1.md").write_text(
            "---\nid: act-1\ntitle: Act One\norder: 1\n---\n"
        )
        (project_path / "scenes" / "s1.md").write_text(
            "---\nid: s1\ntitle: S1\nsequence_id: seq-1\nact_id: act-1\norder: 1\n---\n"
        )
        (project_path / "scenes" / "s2.md").write_text(
            "---\nid: s2\ntitle: S2\nsequence_id: seq-1\nact_id: act-1\norder: 2\n---\n"
        )

        index = generate_index(project_path)

        seq1 = next(s for s in index["sequences"] if s["id"] == "seq-1")
        assert seq1["scenes_list"] == ["s1", "s2"]

        act1 = next(a for a in index["acts"] if a["id"] == "act-1")
        assert act1["sequences_list"] == ["seq-1", "seq-2"]
        assert set(act1["scenes_list"]) == {"s1", "s2"}

    def test_plot_setups_use_scene_id(self, tmp_path):
        """Plot setups/payoffs reference scene_id (not heading/number)."""
        from core.index import generate_index

        project_path = tmp_path / "proj"
        project_path.mkdir()
        (project_path / "plots").mkdir()
        (project_path / "scenes").mkdir()
        (project_path / "project.md").write_text("---\nname: Test\n---\n")

        (project_path / "scenes" / "key-scene.md").write_text(
            "---\nid: key-scene\ntitle: Key Scene\nsequence_id: seq-1\nact_id: act-1\n---\n"
        )
        (project_path / "plots" / "main.md").write_text(
            "---\nid: main\nname: Main Plot\nsetups:\n  - scene_id: key-scene\n    description: Setup here\n---\n"
        )

        index = generate_index(project_path)

        # Scene should have plot reference
        scene = next(s for s in index["scenes"] if s["id"] == "key-scene")
        assert "main" in scene.get("plots", [])

        # Plot setup should be normalized to {scene_id, description}
        plot = next(p for p in index["plots"] if p["id"] == "main")
        assert plot["setups"][0] == {"scene_id": "key-scene", "description": "Setup here"}

    def test_plot_unknown_scene_warns(self, tmp_path, capsys):
        """Plot referencing non-existent scene triggers warning."""
        from core.index import generate_index

        project_path = tmp_path / "proj"
        project_path.mkdir()
        (project_path / "plots").mkdir()
        (project_path / "project.md").write_text("---\nname: Test\n---\n")

        (project_path / "plots" / "main.md").write_text(
            "---\nid: main\nname: Main Plot\nsetups:\n  - scene_id: ghost-scene\n    description: Missing\n---\n"
        )

        index = generate_index(project_path)
        captured = capsys.readouterr()
        assert "unknown scene" in captured.out


class TestStructureIndex:
    """Tests for structure index generation (Phase 2, Task 9)."""

    def test_structure_index_includes_story(self, tmp_path):
        """Project structural fields appear in structure-index story key."""
        from core.index import generate_structure_index, generate_index

        project_path = tmp_path / "proj"
        project_path.mkdir()
        (project_path / "project.md").write_text(
            "---\n"
            "name: Test\n"
            "logline: A test logline\n"
            "value: Trust\n"
            "value_at_open: positive\n"
            "value_at_close: ironic\n"
            "spine: A protagonist wants truth\n"
            "controlling_idea: Truth wins\n"
            "inciting_incident_scene_id: opening\n"
            "story_climax_scene_id: finale\n"
            "structure_type: Classical\n"
            "---\n"
        )

        index = generate_index(project_path)
        structure = generate_structure_index(index)

        assert "story" in structure
        assert structure["story"]["id"] == "story"
        assert structure["story"]["value"] == "Trust"
        assert structure["story"]["value_open"] == "positive"
        assert structure["story"]["value_close"] == "ironic"
        assert structure["story"]["spine"] == "A protagonist wants truth"
        assert structure["story"]["controlling_idea"] == "Truth wins"
        assert structure["story"]["inciting_incident_scene_id"] == "opening"
        assert structure["story"]["story_climax_scene_id"] == "finale"
        assert structure["story"]["structure_type"] == "Classical"

        # Main index project should NOT have structural fields
        assert "spine" not in index["project"]
        assert "controlling_idea" not in index["project"]
        assert "value" not in index["project"]
        assert "value_at_open" not in index["project"]
        assert "value_at_close" not in index["project"]
        assert "inciting_incident_scene_id" not in index["project"]
        assert "story_climax_scene_id" not in index["project"]
        assert "structure_type" not in index["project"]

        # But should still have navigation fields
        assert index["project"]["name"] == "Test"
        assert index["project"]["logline"] == "A test logline"

    def test_structure_index_includes_file_scenes(self, tmp_path):
        """File scenes with dramatic metadata appear in structure index."""
        from core.index import generate_structure_index, generate_index

        project_path = tmp_path / "proj"
        project_path.mkdir()
        (project_path / "scenes").mkdir()
        (project_path / "project.md").write_text("---\nname: Test\n---\n")

        (project_path / "scenes" / "scene-1.md").write_text(
            "---\nid: scene-1\ntitle: Scene One\nsequence_id: seq-1\nact_id: act-1\n"
            "value: Trust\nvalue_open: positive\nvalue_close: negative\n"
            "conflict_levels: [inner, personal]\ndramatic_role: setup\n"
            "is_inciting_incident: true\nis_sequence_climax: false\n"
            "is_act_climax: false\nis_story_climax: false\n---\n"
        )

        index = generate_index(project_path)
        structure = generate_structure_index(index)

        assert len(structure["scenes"]) == 1
        assert structure["scenes"][0]["id"] == "scene-1"
        assert structure["scenes"][0]["value"] == "Trust"
        assert structure["scenes"][0]["value_open"] == "positive"
        assert structure["scenes"][0]["value_close"] == "negative"
        assert structure["scenes"][0]["conflict_levels"] == ["inner", "personal"]
        assert structure["scenes"][0]["dramatic_role"] == "setup"
        assert structure["scenes"][0]["is_inciting_incident"] is True
        assert structure["scenes"][0]["is_sequence_climax"] is False
        assert structure["scenes"][0]["is_act_climax"] is False
        assert structure["scenes"][0]["is_story_climax"] is False

    def test_structure_index_includes_sequences_and_acts(self, tmp_path):
        """Sequences and acts appear in structure index."""
        from core.index import generate_structure_index, generate_index

        project_path = tmp_path / "proj"
        project_path.mkdir()
        (project_path / "sequences").mkdir()
        (project_path / "acts").mkdir()
        (project_path / "project.md").write_text("---\nname: Test\n---\n")

        (project_path / "sequences" / "seq-1.md").write_text(
            "---\nid: seq-1\ntitle: Seq One\nact_id: act-1\n"
            "value: Trust\nvalue_open: positive\nvalue_close: negative\n"
            "climax_scene_id: scene-1\n---\n"
        )
        (project_path / "acts" / "act-1.md").write_text(
            "---\nid: act-1\ntitle: Act One\n"
            "value: Trust\nvalue_open: positive\nvalue_close: negative\n"
            "climax_scene_id: scene-1\n---\n"
        )

        index = generate_index(project_path)
        structure = generate_structure_index(index)

        assert len(structure["sequences"]) == 1
        assert structure["sequences"][0]["id"] == "seq-1"
        assert structure["sequences"][0]["value"] == "Trust"
        assert structure["sequences"][0]["climax_scene_id"] == "scene-1"

        assert len(structure["acts"]) == 1
        assert structure["acts"][0]["id"] == "act-1"
        assert structure["acts"][0]["value"] == "Trust"
        assert structure["acts"][0]["climax_scene_id"] == "scene-1"

    def test_structure_index_scene_fields(self, tmp_path):
        """All dramatic metadata fields present with correct types."""
        from core.index import generate_structure_index, generate_index

        project_path = tmp_path / "proj"
        project_path.mkdir()
        (project_path / "scenes").mkdir()
        (project_path / "project.md").write_text("---\nname: Test\n---\n")

        (project_path / "scenes" / "scene-1.md").write_text(
            "---\nid: scene-1\ntitle: Scene\nsequence_id: seq-1\nact_id: act-1\n"
            "value: Freedom\nvalue_open: mixed\nvalue_close: ironic\n"
            "conflict_levels: [inner]\ndramatic_role: crisis\n"
            "is_inciting_incident: true\nis_sequence_climax: true\n"
            "is_act_climax: true\nis_story_climax: false\n---\n"
        )

        index = generate_index(project_path)
        structure = generate_structure_index(index)

        scene = structure["scenes"][0]
        expected_keys = {
            "id", "value", "value_open", "value_close",
            "conflict_levels", "dramatic_role",
            "is_inciting_incident", "is_sequence_climax",
            "is_act_climax", "is_story_climax", "arc_beat_refs",
        }
        assert set(scene.keys()) == expected_keys

        # Boolean fields are actual bools
        assert isinstance(scene["is_inciting_incident"], bool)
        assert isinstance(scene["is_sequence_climax"], bool)
        assert isinstance(scene["is_act_climax"], bool)
        assert isinstance(scene["is_story_climax"], bool)
        # conflict_levels is a list
        assert isinstance(scene["conflict_levels"], list)

    def test_structure_index_arc_beat_refs_empty(self, tmp_path):
        """arc_beat_refs is [] for all scenes."""
        from core.index import generate_structure_index, generate_index

        project_path = tmp_path / "proj"
        project_path.mkdir()
        (project_path / "scenes").mkdir()
        (project_path / "project.md").write_text("---\nname: Test\n---\n")

        (project_path / "scenes" / "scene-1.md").write_text(
            "---\nid: scene-1\ntitle: Scene\nsequence_id: seq-1\nact_id: act-1\n---\n"
        )

        index = generate_index(project_path)
        structure = generate_structure_index(index)

        for scene in structure["scenes"]:
            assert scene["arc_beat_refs"] == []

    def test_index_scenes_are_files_only(self, project_path):
        """index['scenes'] contains only file scenes, not screenplay scenes."""
        from core.index import generate_index

        index = generate_index(project_path)

        # Fixture has 3 scene files and 9 screenplay scenes
        # After Phase 2: only file scenes
        assert len(index["scenes"]) == 3
        scene_ids = {s["id"] for s in index["scenes"]}
        assert scene_ids == {"central-room-day", "central-room-night", "the-core-day"}

    def test_index_scenes_stripped_for_navigation(self, project_path):
        """Main index scene entries lack dramatic metadata."""
        from core.index import generate_index

        index = generate_index(project_path)

        for scene in index["scenes"]:
            # Should NOT have dramatic metadata
            assert "value" not in scene or scene.get("value", "") == ""
            assert "value_open" not in scene or scene.get("value_open", "") == ""
            assert "value_close" not in scene or scene.get("value_close", "") == ""
            assert "conflict_levels" not in scene or scene.get("conflict_levels", []) == []
            assert "dramatic_role" not in scene or scene.get("dramatic_role", "") == ""
            assert "is_inciting_incident" not in scene or scene.get("is_inciting_incident", False) is False
            assert "is_sequence_climax" not in scene or scene.get("is_sequence_climax", False) is False
            assert "is_act_climax" not in scene or scene.get("is_act_climax", False) is False
            assert "is_story_climax" not in scene or scene.get("is_story_climax", False) is False

    def test_sequence_scene_count(self, project_path):
        """sequence.scene_count equals number of scenes in sequence."""
        from core.index import generate_index

        index = generate_index(project_path)

        seq = next(s for s in index["sequences"] if s["id"] == "seq-discovery")
        assert seq["scene_count"] == 3
        assert seq["scenes_list"] == ["central-room-day", "central-room-night", "the-core-day"]

    def test_act_sequence_and_scene_counts(self, project_path):
        """act.sequence_count and act.scene_count are present and correct."""
        from core.index import generate_index

        index = generate_index(project_path)

        act = next(a for a in index["acts"] if a["id"] == "act-1")
        assert act["sequence_count"] == 1
        assert act["scene_count"] == 3
        assert act["sequences_list"] == ["seq-discovery"]

    def test_character_scenes_from_files_only(self, project_path):
        """Character.scenes cross-references built from file scenes only."""
        from core.index import generate_index

        index = generate_index(project_path)

        kael = next(c for c in index["characters"] if c["id"] == "kael")
        kael_scene_ids = [s["id"] for s in kael.get("scenes", [])]
        assert set(kael_scene_ids) == {"central-room-day", "central-room-night", "the-core-day"}


# ---- Phase 3: Tool Surface Tests (Task 7) ----

def _make_project_with_structure(tmp, with_structure_index=False):
    """Create a project with acts/sequences/scenes folders for structural tests."""
    project_path = _make_minimal_project(tmp)
    (project_path / "scenes").mkdir(parents=True, exist_ok=True)
    (project_path / "sequences").mkdir(parents=True, exist_ok=True)
    (project_path / "acts").mkdir(parents=True, exist_ok=True)
    if with_structure_index:
        from core.index import refresh_index
        refresh_index(project_path)
    return project_path


class TestPhase3ToolSurface:
    """Tests for Phase 3 tool surface: edit_note data bag, reorder, cascade blocking, auto-order, parent validation, structure-index update."""

    def test_edit_note_with_data_bag(self, tmp_path):
        """edit_note with data bag updates frontmatter + body section."""
        from tools.story_create import handler as create_handler
        from tools.story_edit import handler as edit_handler

        project_path = _make_project_with_structure(tmp_path)

        # Create parents
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

        import frontmatter
        post = frontmatter.load(project_path / "scenes" / "test-scene.md")
        assert post.metadata["status"] == "written"
        assert "Updated description text." in post.content

    def test_reorder_scene_within_sequence(self, tmp_path):
        """Reorder scenes → order fields renumbered 1-2-3."""
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

        import frontmatter
        orders = {}
        for slug in ["scene-1", "scene-2", "scene-3"]:
            post = frontmatter.load(project_path / "scenes" / f"{slug}.md")
            orders[slug] = post.metadata["order"]
        assert orders == {"scene-1": 2, "scene-2": 3, "scene-3": 1}

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

        # Sequence file should NOT have moved to recycle bin
        assert (project_path / "sequences" / "seq-1.md").exists()

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

        # Act file should NOT have moved to recycle bin
        assert (project_path / "acts" / "act-1.md").exists()

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

        import frontmatter
        post_b = frontmatter.load(project_path / "scenes" / "scene-b.md")
        assert post_b.metadata["order"] == 2

    def test_create_scene_validates_parent(self, tmp_path):
        """Create scene with non-existent sequence_id → error."""
        from tools.story_create import handler as create_handler

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

    def test_update_structure_index_scene(self, tmp_path):
        """After edit, structure-index.yaml updated without full rebuild."""
        from tools.story_create import handler as create_handler
        from tools.story_edit import handler as edit_handler
        from core.index import update_structure_index_scene, refresh_index

        project_path = _make_project_with_structure(tmp_path)

        # Create entities with explicit id fields (story_create doesn't auto-fill id)
        create_handler({
            "entity_type": "act", "slug": "act-1", "project": str(project_path),
            "frontmatter": {"id": "act-1", "title": "Act 1"}
        })
        create_handler({
            "entity_type": "sequence", "slug": "seq-1", "project": str(project_path),
            "frontmatter": {"id": "seq-1", "title": "Seq 1", "act_id": "act-1"}
        })
        create_handler({
            "entity_type": "scene", "slug": "dramatic-scene", "project": str(project_path),
            "frontmatter": {
                "id": "dramatic-scene", "title": "Dramatic Scene",
                "sequence_id": "seq-1", "act_id": "act-1",
                "value": "Trust", "dramatic_role": "setup"
            }
        })

        # Refresh index to pick up all created entities (structure-index includes dramatic-scene)
        refresh_index(project_path)

        # Verify initial state
        import frontmatter, yaml
        structure_path = project_path / ".story" / "structure-index.yaml"
        with open(structure_path) as f:
            si = yaml.safe_load(f)
        scene_entry = next(s for s in si["scenes"] if s["id"] == "dramatic-scene")
        assert scene_entry["dramatic_role"] == "setup"

        # Edit scene frontmatter
        edit_handler({
            "action": "edit_note",
            "target": {"entity_type": "scene", "slug": "dramatic-scene", "project": str(project_path)},
            "data": {"dramatic_role": "crisis", "value_close": "negative"},
            "summary": "Change dramatic role"
        })

        # Verify structure-index.yaml was updated (lightweight, no full rebuild)
        with open(structure_path) as f:
            si = yaml.safe_load(f)
        scene_entry = next(s for s in si["scenes"] if s["id"] == "dramatic-scene")
        assert scene_entry["dramatic_role"] == "crisis"
        assert scene_entry["value_close"] == "negative"

        # Also verify update_structure_index_scene directly (the underlying mechanism)
        # Edit frontmatter directly, then call update
        scene_path = project_path / "scenes" / "dramatic-scene.md"
        post = frontmatter.load(scene_path)
        post.metadata["value_open"] = "mixed"
        with open(scene_path, "w") as f:
            frontmatter.dump(post, f)
        update_structure_index_scene(project_path, "dramatic-scene")

        with open(structure_path) as f:
            si = yaml.safe_load(f)
        scene_entry = next(s for s in si["scenes"] if s["id"] == "dramatic-scene")
        assert scene_entry["value_open"] == "mixed"


# ---- Phase 4: assemble_scene_content() Tests (Task 17) ----

def _make_project_with_scenes(tmp, scenes_data, sequences_data=None, acts_data=None):
    """Create a project with scene files for assemble_scene_content tests."""
    project_path = Path(tmp) / "test-project"
    project_path.mkdir()
    (project_path / "characters").mkdir(parents=True)
    (project_path / "locations").mkdir(parents=True)
    (project_path / "worlds").mkdir(parents=True)
    (project_path / "plots").mkdir(parents=True)
    (project_path / "scenes").mkdir(parents=True)
    (project_path / "sequences").mkdir(parents=True)
    (project_path / "acts").mkdir(parents=True)
    (project_path / ".story").mkdir(parents=True)
    (project_path / "project.md").write_text("---\nname: Test\n---\n")

    for seq in (sequences_data or []):
        slug = seq["id"]
        frontmatter = {"id": seq["id"], "title": seq.get("title", slug), "order": seq.get("order", 0)}
        if "act_id" in seq:
            frontmatter["act_id"] = seq["act_id"]
        (project_path / "sequences" / f"{slug}.md").write_text(
            f"---\n" + "\n".join(f"{k}: {v}" for k, v in frontmatter.items()) + "\n---\n"
        )

    for act in (acts_data or []):
        slug = act["id"]
        frontmatter = {"id": act["id"], "title": act.get("title", slug), "order": act.get("order", 0)}
        (project_path / "acts" / f"{slug}.md").write_text(
            f"---\n" + "\n".join(f"{k}: {v}" for k, v in frontmatter.items()) + "\n---\n"
        )

    for scene in scenes_data:
        slug = scene["id"]
        content_text = scene.get("content", "")
        frontmatter = {
            "id": scene["id"],
            "title": scene.get("title", slug),
            "order": scene.get("order", 0),
            "sequence_id": scene.get("sequence_id", ""),
            "act_id": scene.get("act_id", ""),
        }
        (project_path / "scenes" / f"{slug}.md").write_text(
            f"---\n" + "\n".join(f"{k}: {v}" for k, v in frontmatter.items()) + f"\n---\n\n## Content\n\n{content_text}\n"
        )

    return project_path


class TestAssembleSceneContent:
    """Tests for assemble_scene_content() (Phase 4, Task 17)."""

    def test_empty_scenes(self, tmp_path):
        """No scenes → empty string."""
        from core.index import assemble_scene_content

        project_path = _make_project_with_scenes(tmp_path, [])
        index = {
            "scenes": [],
            "sequences": [],
            "acts": [],
        }
        result = assemble_scene_content(index, project_path)
        assert result == ""

    def test_scene_with_content(self, tmp_path):
        """Scene with ## Content → concatenated text in order."""
        from core.index import assemble_scene_content

        project_path = _make_project_with_scenes(
            tmp_path,
            scenes_data=[
                {"id": "scene-1", "title": "Scene 1", "order": 1, "sequence_id": "seq-1", "act_id": "act-1", "content": "First scene content."},
            ],
            sequences_data=[{"id": "seq-1", "title": "Seq 1", "order": 1, "act_id": "act-1"}],
            acts_data=[{"id": "act-1", "title": "Act 1", "order": 1}],
        )
        index = {
            "scenes": [
                {"id": "scene-1", "title": "Scene 1", "order": 1, "sequence_id": "seq-1", "act_id": "act-1"},
            ],
            "sequences": [{"id": "seq-1", "title": "Seq 1", "order": 1, "act_id": "act-1"}],
            "acts": [{"id": "act-1", "title": "Act 1", "order": 1}],
        }
        result = assemble_scene_content(index, project_path)
        assert "First scene content." in result

    def test_respects_act_sequence_order(self, tmp_path):
        """Scenes in different sequences appear in act→sequence→order."""
        from core.index import assemble_scene_content

        project_path = _make_project_with_scenes(
            tmp_path,
            scenes_data=[
                {"id": "scene-b", "title": "Scene B", "order": 1, "sequence_id": "seq-2", "act_id": "act-1", "content": "SECOND"},
                {"id": "scene-a", "title": "Scene A", "order": 1, "sequence_id": "seq-1", "act_id": "act-1", "content": "FIRST"},
            ],
            sequences_data=[
                {"id": "seq-1", "title": "Seq 1", "order": 1, "act_id": "act-1"},
                {"id": "seq-2", "title": "Seq 2", "order": 2, "act_id": "act-1"},
            ],
            acts_data=[{"id": "act-1", "title": "Act 1", "order": 1}],
        )
        index = {
            "scenes": [
                {"id": "scene-b", "title": "Scene B", "order": 1, "sequence_id": "seq-2", "act_id": "act-1"},
                {"id": "scene-a", "title": "Scene A", "order": 1, "sequence_id": "seq-1", "act_id": "act-1"},
            ],
            "sequences": [
                {"id": "seq-1", "title": "Seq 1", "order": 1, "act_id": "act-1"},
                {"id": "seq-2", "title": "Seq 2", "order": 2, "act_id": "act-1"},
            ],
            "acts": [{"id": "act-1", "title": "Act 1", "order": 1}],
        }
        result = assemble_scene_content(index, project_path)
        # seq-1 (order=1) comes before seq-2 (order=2)
        assert result.index("FIRST") < result.index("SECOND")

    def test_missing_scene_file_skipped(self, tmp_path):
        """Scene file that doesn't exist on disk is skipped."""
        from core.index import assemble_scene_content

        project_path = _make_project_with_scenes(
            tmp_path,
            scenes_data=[
                {"id": "exists", "title": "Exists", "order": 1, "sequence_id": "seq-1", "act_id": "act-1", "content": "Present."},
            ],
            sequences_data=[{"id": "seq-1", "title": "Seq 1", "order": 1, "act_id": "act-1"}],
            acts_data=[{"id": "act-1", "title": "Act 1", "order": 1}],
        )
        index = {
            "scenes": [
                {"id": "exists", "title": "Exists", "order": 1, "sequence_id": "seq-1", "act_id": "act-1"},
                {"id": "missing", "title": "Missing", "order": 2, "sequence_id": "seq-1", "act_id": "act-1"},
            ],
            "sequences": [{"id": "seq-1", "title": "Seq 1", "order": 1, "act_id": "act-1"}],
            "acts": [{"id": "act-1", "title": "Act 1", "order": 1}],
        }
        result = assemble_scene_content(index, project_path)
        assert "Present." in result
        # No crash, no "missing" content

    def test_scene_without_content_section_skipped(self, tmp_path):
        """Scene file without ## Content section is skipped."""
        from core.index import assemble_scene_content

        project_path = _make_project_with_scenes(
            tmp_path,
            scenes_data=[
                {"id": "with-content", "title": "With Content", "order": 1, "sequence_id": "seq-1", "act_id": "act-1", "content": "Has content."},
            ],
            sequences_data=[{"id": "seq-1", "title": "Seq 1", "order": 1, "act_id": "act-1"}],
            acts_data=[{"id": "act-1", "title": "Act 1", "order": 1}],
        )
        # Create a scene file without ## Content
        (project_path / "scenes" / "no-content.md").write_text(
            "---\nid: no-content\ntitle: No Content\norder: 2\nsequence_id: seq-1\nact_id: act-1\n---\n\n## Description\n\nJust a description.\n"
        )
        index = {
            "scenes": [
                {"id": "with-content", "title": "With Content", "order": 1, "sequence_id": "seq-1", "act_id": "act-1"},
                {"id": "no-content", "title": "No Content", "order": 2, "sequence_id": "seq-1", "act_id": "act-1"},
            ],
            "sequences": [{"id": "seq-1", "title": "Seq 1", "order": 1, "act_id": "act-1"}],
            "acts": [{"id": "act-1", "title": "Act 1", "order": 1}],
        }
        result = assemble_scene_content(index, project_path)
        assert "Has content." in result
        assert "Just a description." not in result

    def test_content_heading_prefix_stripped(self, tmp_path):
        """The '## Content' heading prefix is stripped from output."""
        from core.index import assemble_scene_content

        project_path = _make_project_with_scenes(
            tmp_path,
            scenes_data=[
                {"id": "scene-1", "title": "Scene 1", "order": 1, "sequence_id": "seq-1", "act_id": "act-1", "content": "Body text here."},
            ],
            sequences_data=[{"id": "seq-1", "title": "Seq 1", "order": 1, "act_id": "act-1"}],
            acts_data=[{"id": "act-1", "title": "Act 1", "order": 1}],
        )
        index = {
            "scenes": [
                {"id": "scene-1", "title": "Scene 1", "order": 1, "sequence_id": "seq-1", "act_id": "act-1"},
            ],
            "sequences": [{"id": "seq-1", "title": "Seq 1", "order": 1, "act_id": "act-1"}],
            "acts": [{"id": "act-1", "title": "Act 1", "order": 1}],
        }
        result = assemble_scene_content(index, project_path)
        assert "## Content" not in result
        assert "Body text here." in result

    def test_multiple_scenes_concatenated(self, tmp_path):
        """Multiple scenes concatenated with double newline."""
        from core.index import assemble_scene_content

        project_path = _make_project_with_scenes(
            tmp_path,
            scenes_data=[
                {"id": "s1", "title": "S1", "order": 1, "sequence_id": "seq-1", "act_id": "act-1", "content": "Alpha."},
                {"id": "s2", "title": "S2", "order": 2, "sequence_id": "seq-1", "act_id": "act-1", "content": "Beta."},
            ],
            sequences_data=[{"id": "seq-1", "title": "Seq 1", "order": 1, "act_id": "act-1"}],
            acts_data=[{"id": "act-1", "title": "Act 1", "order": 1}],
        )
        index = {
            "scenes": [
                {"id": "s1", "title": "S1", "order": 1, "sequence_id": "seq-1", "act_id": "act-1"},
                {"id": "s2", "title": "S2", "order": 2, "sequence_id": "seq-1", "act_id": "act-1"},
            ],
            "sequences": [{"id": "seq-1", "title": "Seq 1", "order": 1, "act_id": "act-1"}],
            "acts": [{"id": "act-1", "title": "Act 1", "order": 1}],
        }
        result = assemble_scene_content(index, project_path)
        assert "Alpha." in result
        assert "Beta." in result
        assert result.index("Alpha.") < result.index("Beta.")
        # Double newline separator
        assert "Alpha.\n\nBeta." in result


# ---- Phase 4: compute_structural_stats() Tests (Task 18) ----

class TestComputeStructuralStats:
    """Tests for compute_structural_stats() (Phase 4, Task 18)."""

    def test_empty_index(self):
        """Empty index → zero counts, empty collections."""
        from core.index import compute_structural_stats

        result = compute_structural_stats({"scenes": [], "sequences": [], "acts": []})
        assert result["sceneCount"] == 0
        assert result["sequenceCount"] == 0
        assert result["actCount"] == 0
        assert result["sceneStatus"] == {}
        assert result["sceneRoles"] == {}
        assert result["acts"] == []

    def test_status_and_role_counts(self):
        """Status and role counts match scene frontmatter."""
        from core.index import compute_structural_stats

        index = {
            "scenes": [
                {"id": "s1", "status": "planned", "dramatic_role": "setup"},
                {"id": "s2", "status": "written", "dramatic_role": "crisis"},
                {"id": "s3", "status": "planned", "dramatic_role": "setup"},
            ],
            "sequences": [{"id": "seq-1"}],
            "acts": [{"id": "act-1", "title": "Act 1"}],
        }
        result = compute_structural_stats(index)
        assert result["sceneCount"] == 3
        assert result["sequenceCount"] == 1
        assert result["actCount"] == 1
        assert result["sceneStatus"] == {"planned": 2, "written": 1}
        assert result["sceneRoles"] == {"setup": 2, "crisis": 1}

    def test_missing_role_defaults_to_unset(self):
        """Scene with empty/missing dramatic_role → 'unset' bucket."""
        from core.index import compute_structural_stats

        index = {
            "scenes": [
                {"id": "s1", "status": "planned", "dramatic_role": ""},
                {"id": "s2", "status": "planned"},  # no dramatic_role key
            ],
            "sequences": [],
            "acts": [],
        }
        result = compute_structural_stats(index)
        assert result["sceneRoles"] == {"unset": 2}

    def test_acts_list_with_counts(self):
        """Act stats include scene/sequence counts from index."""
        from core.index import compute_structural_stats

        index = {
            "scenes": [
                {"id": "s1", "status": "planned", "dramatic_role": "setup"},
                {"id": "s2", "status": "written", "dramatic_role": "crisis"},
            ],
            "sequences": [{"id": "seq-1"}, {"id": "seq-2"}],
            "acts": [
                {"id": "act-1", "title": "Act One", "scene_count": 2, "sequence_count": 2},
            ],
        }
        result = compute_structural_stats(index)
        assert len(result["acts"]) == 1
        assert result["acts"][0] == {
            "id": "act-1",
            "title": "Act One",
            "sceneCount": 2,
            "sequenceCount": 2,
        }

    def test_multiple_acts(self):
        """Multiple acts → all listed with individual counts."""
        from core.index import compute_structural_stats

        index = {
            "scenes": [
                {"id": "s1", "status": "planned", "dramatic_role": "setup"},
                {"id": "s2", "status": "written", "dramatic_role": "resolution"},
            ],
            "sequences": [{"id": "seq-1"}, {"id": "seq-2"}],
            "acts": [
                {"id": "act-1", "title": "Act One", "scene_count": 1, "sequence_count": 1},
                {"id": "act-2", "title": "Act Two", "scene_count": 1, "sequence_count": 1},
            ],
        }
        result = compute_structural_stats(index)
        assert result["actCount"] == 2
        assert len(result["acts"]) == 2
        assert result["acts"][0]["id"] == "act-1"
        assert result["acts"][1]["id"] == "act-2"


# ---- Phase 4: screenplay stats from assembled scene content (Task 19) ----

class TestScreenplayStatsFromSceneContent:
    """Tests for assemble_scene_content → _compute_screenplay_stats pipeline."""

    def test_pipeline_produces_stats_with_scriptHtml(self, tmp_path):
        """_compute_screenplay_stats(assemble_scene_content(...)) returns valid stats incl scriptHtml."""
        from core.index import assemble_scene_content
        import importlib.util

        project_path = _make_project_with_scenes(
            tmp_path,
            scenes_data=[
                {
                    "id": "scene-1",
                    "title": "The Institute",
                    "order": 1,
                    "sequence_id": "seq-1",
                    "act_id": "act-1",
                    "content": "EXT. THE INSTITUTE - DAY\n\nA vast decaying building.\n\nKAEL (15, intense) stares at a wall of pale light.\n\nKAEL\nSomething's wrong. Everything arrives too perfectly.",
                },
            ],
            sequences_data=[{"id": "seq-1", "title": "Seq 1", "order": 1, "act_id": "act-1"}],
            acts_data=[{"id": "act-1", "title": "Act 1", "order": 1}],
        )
        index = {
            "scenes": [{"id": "scene-1", "title": "The Institute", "order": 1, "sequence_id": "seq-1", "act_id": "act-1"}],
            "sequences": [{"id": "seq-1", "title": "Seq 1", "order": 1, "act_id": "act-1"}],
            "acts": [{"id": "act-1", "title": "Act 1", "order": 1}],
        }

        scene_text = assemble_scene_content(index, project_path)
        assert scene_text, "assemble_scene_content returned empty string"

        spec = importlib.util.spec_from_file_location("story_dashboard", Path("tools/story_dashboard.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        stats = mod._compute_screenplay_stats(scene_text)
        assert stats is not None
        assert "scriptHtml" in stats
        assert stats["scriptHtml"], "scriptHtml should not be empty for valid scene content"
        assert "lengthStats" in stats
        assert stats["lengthStats"]["scenes"] >= 1


# ---- Phase 4: _enrich_entity_scenes() title preservation (Task 20) ----

class TestEnrichEntityScenesTitle:
    """Tests for _enrich_entity_scenes() storing title in character/location scenes."""

    def test_character_scenes_have_title(self, tmp_path):
        """Character scenes[] entries have title field."""
        from core.index import generate_index

        project_path = _make_minimal_project(tmp_path)
        (project_path / "characters").mkdir(parents=True, exist_ok=True)
        (project_path / "locations").mkdir(parents=True, exist_ok=True)
        (project_path / "scenes").mkdir(parents=True, exist_ok=True)

        (project_path / "characters" / "kael.md").write_text(
            "---\nid: kael\nname: Kael\nstory_role: Protagonist\n---\n"
        )
        (project_path / "scenes" / "discovery.md").write_text(
            "---\nid: discovery\ntitle: The Discovery\nsequence_id: seq-1\nact_id: act-1\ncharacters:\n  - kael\n---\n"
        )

        index = generate_index(project_path)
        kael = next(c for c in index["characters"] if c["id"] == "kael")
        assert "scenes" in kael
        assert len(kael["scenes"]) == 1
        assert kael["scenes"][0]["title"] == "The Discovery"
        assert kael["scenes"][0]["id"] == "discovery"

    def test_location_scenes_have_title(self, tmp_path):
        """Location scenes[] entries have title field."""
        from core.index import generate_index

        project_path = _make_minimal_project(tmp_path)
        (project_path / "locations").mkdir(parents=True, exist_ok=True)
        (project_path / "scenes").mkdir(parents=True, exist_ok=True)

        (project_path / "locations" / "institute.md").write_text(
            "---\nid: institute\nname: The Institute\n---\n"
        )
        (project_path / "scenes" / "escape.md").write_text(
            "---\nid: escape\ntitle: The Escape\nsequence_id: seq-1\nact_id: act-1\nlocation: institute\n---\n"
        )

        index = generate_index(project_path)
        institute = next(l for l in index["locations"] if l["id"] == "institute")
        assert "scenes" in institute
        assert len(institute["scenes"]) == 1
        assert institute["scenes"][0]["title"] == "The Escape"
        assert institute["scenes"][0]["id"] == "escape"

    def test_character_without_scenes_has_no_scenes_key(self, tmp_path):
        """Character with no scenes doesn't get scenes key added."""
        from core.index import generate_index

        project_path = _make_minimal_project(tmp_path)
        (project_path / "characters").mkdir(parents=True, exist_ok=True)

        (project_path / "characters" / "lone.md").write_text(
            "---\nid: lone\nname: Lone\nstory_role: Minor\n---\n"
        )

        index = generate_index(project_path)
        lone = next(c for c in index["characters"] if c["id"] == "lone")
        assert "scenes" not in lone