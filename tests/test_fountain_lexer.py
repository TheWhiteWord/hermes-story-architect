"""Test suite for Fountain lexer — port of Better Fountain."""
import pytest
from pathlib import Path
from core.fountain_lexer import (
    tokenize,
    tokens_to_html,
    classify_line,
    trim_character_extension,
    trim_character_force_symbol,
    parse_location,
    extract_scene_content,
    fountain_to_html,
    CHARACTER_RE,
    SCENE_HEADING_RE,
    TRANSITION_RE,
    SECTION_RE,
    SYNOPSIS_RE,
    PARENTHETICAL_RE,
    CENTERED_RE,
    PAGE_BREAK_RE,
    LYRIC_RE,
    NOTE_INLINE_RE,
    BONEYARD_START_RE,
    BONEYARD_END_RE,
)


# ---- Fixtures ----

@pytest.fixture
def save_the_children_fountain():
    """Load the Save the Children screenplay."""
    path = Path(__file__).parent / "fixtures" / "save-the-children" / "screenplay.fountain"
    return path.read_text()


@pytest.fixture
def the_water_audit_fountain():
    """Load the Save the Children screenplay."""
    path = Path(__file__).parent / "fixtures" / "save-the-children" / "screenplay.fountain"
    return path.read_text()


# ---- Character Extension Tests ----

class TestCharacterExtension:
    def test_simple_name(self):
        assert trim_character_extension("KAEL") == "KAEL"

    def test_contd(self):
        assert trim_character_extension("KAEL (CONT'D)") == "KAEL"

    def test_vo(self):
        assert trim_character_extension("ADMINISTRATOR (V.O.)") == "ADMINISTRATOR"

    def test_os(self):
        assert trim_character_extension("VOICE (O.S.)") == "VOICE"

    def test_on_radio(self):
        assert trim_character_extension("KAEL (on the radio)") == "KAEL"

    def test_with_caret(self):
        assert trim_character_extension("STEEL ^") == "STEEL"

    def test_with_extension_and_caret(self):
        assert trim_character_extension("STEEL (CONT'D) ^") == "STEEL"

    def test_force_symbol(self):
        assert trim_character_force_symbol("@McCONNOR") == "McCONNOR"

    def test_no_force_symbol(self):
        assert trim_character_force_symbol("KAEL") == "KAEL"


# ---- Location Parsing Tests ----

class TestLocationParsing:
    def test_int(self):
        loc = parse_location("INT. KITCHEN - NIGHT")
        assert loc["name"] == "KITCHEN"
        assert loc["time_of_day"] == "NIGHT"
        assert loc["interior"] is True
        assert loc["exterior"] is False

    def test_ext(self):
        loc = parse_location("EXT. PARK - DAY")
        assert loc["name"] == "PARK"
        assert loc["time_of_day"] == "DAY"
        assert loc["interior"] is False
        assert loc["exterior"] is True

    def test_int_ext(self):
        loc = parse_location("INT./EXT. CAR - NIGHT")
        assert loc["name"] == "CAR"
        assert loc["interior"] is True
        assert loc["exterior"] is True

    def test_ie(self):
        loc = parse_location("I/E. CAR - NIGHT")
        assert loc["name"] == "CAR"
        assert loc["interior"] is True
        assert loc["exterior"] is True

    def test_est(self):
        loc = parse_location("EST. CITY - NIGHT")
        assert loc["name"] == "CITY"

    def test_no_time(self):
        loc = parse_location("INT. KITCHEN")
        assert loc["name"] == "KITCHEN"
        assert loc["time_of_day"] == ""

    def test_not_heading(self):
        assert parse_location("NOT A HEADING") is None


# ---- Regex Tests ----

class TestRegexPatterns:
    def test_scene_heading_int(self):
        assert SCENE_HEADING_RE.match("INT. ROOM - DAY")

    def test_scene_heading_ext(self):
        assert SCENE_HEADING_RE.match("EXT. PARK - NIGHT")

    def test_scene_heading_est(self):
        assert SCENE_HEADING_RE.match("EST. CITY - DAY")

    def test_scene_heading_int_ext(self):
        assert SCENE_HEADING_RE.match("INT./EXT. CAR - NIGHT")

    def test_scene_heading_ie(self):
        assert SCENE_HEADING_RE.match("I/E. CAR - NIGHT")

    def test_scene_heading_with_number(self):
        assert SCENE_HEADING_RE.match("INT. ROOM - DAY #1#")

    def test_transition_cut_to(self):
        assert TRANSITION_RE.match("CUT TO:")

    def test_transition_fade_to_black(self):
        assert TRANSITION_RE.match("FADE TO BLACK.")

    def test_transition_smash_cut(self):
        assert TRANSITION_RE.match("SMASH CUT TO:")

    def test_section_single(self):
        assert SECTION_RE.match("# Act I")

    def test_section_double(self):
        assert SECTION_RE.match("## Sequence")

    def test_section_triple(self):
        assert SECTION_RE.match("### Scene")

    def test_synopsis(self):
        assert SYNOPSIS_RE.match("= Summary text")

    def test_parenthetical(self):
        assert PARENTHETICAL_RE.match("(direction)")

    def test_centered(self):
        assert CENTERED_RE.match("> THE END <")

    def test_page_break(self):
        assert PAGE_BREAK_RE.match("===")

    def test_lyric(self):
        assert LYRIC_RE.match("~Singing~")

    def test_note_inline(self):
        assert NOTE_INLINE_RE.search("text [[note]] more")

    def test_boneyard_start(self):
        assert BONEYARD_START_RE.match("/* comment")

    def test_boneyard_end(self):
        assert BONEYARD_END_RE.search("comment */")


# ---- Token Classification Tests ----

class TestTokenClassification:
    def test_scene_heading(self):
        assert classify_line("INT. ROOM - DAY") == "scene_heading"

    def test_forced_scene_heading(self):
        assert classify_line(".OPENING TITLES") == "scene_heading"

    def test_action(self):
        assert classify_line("Dave stands there.") == "action"

    def test_character(self):
        assert classify_line("KAEL") == "character"

    def test_character_with_extension(self):
        assert classify_line("ADMINISTRATOR (V.O.)") == "character"

    def test_character_force_symbol(self):
        # @ prefix forces character names with lowercase
        assert classify_line("@McCONNOR") == "character"

    def test_dialogue_after_character(self):
        assert classify_line("Hello world", prev_type="character") == "dialogue"

    def test_parenthetical_in_dialogue(self):
        assert classify_line("(chosen)", prev_type="character") == "parenthetical"

    def test_transition(self):
        assert classify_line("CUT TO:") == "transition"

    def test_section(self):
        assert classify_line("# Act I") == "section"

    def test_synopsis(self):
        assert classify_line("= Summary") == "synopsis"

    def test_centered(self):
        assert classify_line("> THE END <") == "centered"

    def test_page_break(self):
        assert classify_line("===") == "page_break"

    def test_lyric(self):
        assert classify_line("~Singing~") == "lyric"

    def test_separator(self):
        assert classify_line("") == "separator"

    def test_separator_spaces(self):
        assert classify_line("   ") == "separator"


# ---- Full Tokenization Tests ----

class TestTokenization:
    def test_save_the_children_scenes(self, save_the_children_fountain):
        tokens = tokenize(save_the_children_fountain)
        scenes = [t for t in tokens if t["type"] == "scene_heading"]
        # EXT. THE INSTITUTE, INT. CENTRAL ROOM, EXT. THE GARDEN, INT. THE CORE,
        # EXT. THE INSTITUTE (400 YEARS), INT. CENTRAL ROOM - NIGHT, .OPENING TITLES,
        # INT. THE CORE (Act II), EXT. THE INSTITUTE (Act II)
        assert len(scenes) == 9

    def test_save_the_children_title_page(self, save_the_children_fountain):
        tokens = tokenize(save_the_children_fountain)
        title_page = [t for t in tokens if t["type"] in ("title", "credit", "author", "source")]
        assert len(title_page) == 4

    def test_save_the_children_sections(self, save_the_children_fountain):
        tokens = tokenize(save_the_children_fountain)
        sections = [t for t in tokens if t["type"] == "section"]
        assert len(sections) == 2

    def test_save_the_children_synopses(self, save_the_children_fountain):
        tokens = tokenize(save_the_children_fountain)
        synopses = [t for t in tokens if t["type"] == "synopsis"]
        assert len(synopses) == 2

    def test_save_the_children_boneyard_stripped(self, save_the_children_fountain):
        tokens = tokenize(save_the_children_fountain)
        # Lines 82-95 are boneyard — should be stripped (become separators)
        boneyard_content = [t for t in tokens if 82 <= t["line"] <= 95 and t["type"] not in ("separator",)]
        assert len(boneyard_content) == 0

    def test_save_the_children_note(self, save_the_children_fountain):
        tokens = tokenize(save_the_children_fountain)
        notes = [t for t in tokens if t["type"] == "note"]
        assert len(notes) == 1
        assert "writer's note" in notes[0]["text"]

    def test_save_the_children_lyrics(self, save_the_children_fountain):
        tokens = tokenize(save_the_children_fountain)
        lyrics = [t for t in tokens if t["type"] == "lyric"]
        assert len(lyrics) == 2

    def test_save_the_children_transitions(self, save_the_children_fountain):
        tokens = tokenize(save_the_children_fountain)
        transitions = [t for t in tokens if t["type"] == "transition"]
        assert len(transitions) == 3  # CUT TO:, SMASH CUT TO:, FADE OUT.

    def test_save_the_children_centered(self, save_the_children_fountain):
        tokens = tokenize(save_the_children_fountain)
        centered = [t for t in tokens if t["type"] == "centered"]
        assert len(centered) == 1

    def test_save_the_children_page_break(self, save_the_children_fountain):
        tokens = tokenize(save_the_children_fountain)
        page_breaks = [t for t in tokens if t["type"] == "page_break"]
        assert len(page_breaks) == 1

    def test_the_water_audit_scenes(self, the_water_audit_fountain):
        tokens = tokenize(the_water_audit_fountain)
        scenes = [t for t in tokens if t["type"] == "scene_heading"]
        assert len(scenes) == 9

    def test_the_water_audit_characters(self, the_water_audit_fountain):
        tokens = tokenize(the_water_audit_fountain)
        characters = [t for t in tokens if t["type"] == "character"]
        names = [t["character_name"] for t in characters]
        assert "KAEL" in names
        assert "MIRA" in names
        assert "MARCUS" in names

    def test_character_extension_stripped(self, the_water_audit_fountain):
        tokens = tokenize(the_water_audit_fountain)
        characters = [t for t in tokens if t["type"] == "character"]
        for char in characters:
            assert "(" not in char["character_name"]
            assert "^" not in char["character_name"]


# ---- Scene Extraction Tests ----

class TestSceneExtraction:
    def test_extract_scene_content(self, the_water_audit_fountain):
        content = extract_scene_content(the_water_audit_fountain, 0)
        assert "EXT. THE INSTITUTE - DAY" in content
        assert "KAEL" in content

    def test_extract_all_scenes(self, the_water_audit_fountain):
        from core.screenplay import extract_scenes
        scenes = extract_scenes(the_water_audit_fountain)
        assert len(scenes) == 9
        assert scenes[0]["heading"] == "EXT. THE INSTITUTE - DAY"
        assert scenes[1]["heading"] == "INT. CENTRAL ROOM - DAY"
        assert scenes[2]["heading"] == "EXT. THE GARDEN - NIGHT"

    def test_scene_characters(self, the_water_audit_fountain):
        from core.screenplay import extract_scenes
        scenes = extract_scenes(the_water_audit_fountain)
        assert "KAEL" in scenes[0]["characters"]
        assert "MIRA" in scenes[1]["characters"]
        assert "MARCUS" in scenes[1]["characters"]

    def test_scene_one_sentence(self, the_water_audit_fountain):
        from core.screenplay import extract_scenes
        scenes = extract_scenes(the_water_audit_fountain)
        assert scenes[0]["one_sentence"] == "A vast decaying building. Nature reclaims the walls."


# ---- HTML Rendering Tests ----

class TestHtmlRendering:
    def test_tokens_to_html_scene_heading(self):
        tokens = [{"type": "scene_heading", "text": "INT. ROOM - DAY", "line": 0}]
        html = tokens_to_html(tokens)
        assert "fountain-scene_heading" in html
        assert "INT. ROOM - DAY" in html

    def test_tokens_to_html_character(self):
        tokens = [{"type": "character", "text": "KAEL", "line": 0}]
        html = tokens_to_html(tokens)
        assert "fountain-character" in html

    def test_tokens_to_html_dialogue(self):
        tokens = [{"type": "dialogue", "text": "Hello", "line": 0}]
        html = tokens_to_html(tokens)
        assert "fountain-dialogue" in html

    def test_tokens_to_html_action(self):
        tokens = [{"type": "action", "text": "Dave stands.", "line": 0}]
        html = tokens_to_html(tokens)
        assert "fountain-action" in html

    def test_fountain_to_html(self):
        fountain = "INT. ROOM - DAY\n\nDave stands."
        html = fountain_to_html(fountain)
        assert "fountain-scene_heading" in html
        assert "fountain-action" in html


# ---- Integration with Index ----

class TestIndexIntegration:
    def test_generate_index_with_new_lexer(self, tmp_path):
        """Test that index generation works with the new lexer."""
        # Create a minimal project
        project = tmp_path / "test-project"
        project.mkdir()
        
        # Create characters folder
        chars = project / "characters"
        chars.mkdir()
        (chars / "kael.md").write_text("""---
name: Kael
story_role: Protagonist
one_sentence: A young person who questions the system.
---

## Personality
Intense, curious, determined.
""")
        
        # Create screenplay
        (project / "screenplay.fountain").write_text("""INT. ROOM - DAY

KAEL
Something's wrong.

INT. HALLWAY - DAY

KAEL
I was meant to find this.
""")
        
        from core.index import generate_index
        index = generate_index(project)
        
        assert index["project"]["scene_count"] == 2
        assert len(index["scenes"]) == 2
        # Character names are matched to slugs by the index generator
        assert "kael" in index["scenes"][0]["characters"]
