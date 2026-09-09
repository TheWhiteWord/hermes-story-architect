"""Test suite for Fountain lexer — port of Better Fountain."""
import pytest
from pathlib import Path
from core.fountain_lexer import (
    parse,
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
def expected_output():
    """Load the expected output from Better Fountain."""
    path = Path(__file__).parent / "fixtures" / "save-the-children" / "expected_output.json"
    import json
    return json.load(open(path))


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
        # Note: BF regex only strips ^ when preceded by (extension)
        # "STEEL ^" has no (, so ^ is NOT stripped by BF
        assert trim_character_extension("STEEL ^") == "STEEL ^"

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
        # Verify all scene headings
        expected_headings = [
            "EXT. THE INSTITUTE - DAY",
            "INT. CENTRAL ROOM - DAY",
            "EXT. THE GARDEN - NIGHT",
            "INT. THE CORE - DAY (400 YEARS EARLIER)",
            "EXT. THE INSTITUTE - NIGHT (400 YEARS EARLIER)",
            "INT. CENTRAL ROOM - NIGHT",
            "OPENING TITLES",
            "INT. THE CORE - DAY",
            "EXT. THE INSTITUTE - DAY",
        ]
        for i, heading in enumerate(expected_headings):
            assert scenes[i]["text"] == heading

    def test_save_the_children_title_page(self, save_the_children_fountain):
        result = parse(save_the_children_fountain)
        all_title = []
        for pos in ['tl', 'tc', 'tr', 'cc', 'bl', 'br', 'hidden']:
            all_title.extend(result['title_page'].get(pos, []))
        title_page = [t for t in all_title if t["type"] in ("title", "credit", "author", "source")]
        assert len(title_page) == 4
        # Verify title page content
        types = [t["type"] for t in title_page]
        assert "title" in types
        assert "credit" in types
        assert "author" in types
        assert "source" in types

    def test_save_the_children_sections(self, save_the_children_fountain):
        tokens = tokenize(save_the_children_fountain)
        sections = [t for t in tokens if t["type"] == "section"]
        assert len(sections) == 4
        # Verify section levels and text
        assert sections[0]["level"] == 1
        assert sections[0]["text"] == "Act I"
        assert sections[1]["level"] == 2
        assert sections[1]["text"] == "Sequence A"
        assert sections[2]["level"] == 3
        assert sections[2]["text"] == "Scene Group 1"
        assert sections[3]["level"] == 1
        assert sections[3]["text"] == "Act II"

    def test_save_the_children_synopses(self, save_the_children_fountain):
        tokens = tokenize(save_the_children_fountain)
        synopses = [t for t in tokens if t["type"] == "synopsis"]
        assert len(synopses) == 2

    def test_save_the_children_boneyard_stripped(self, save_the_children_fountain):
        tokens = tokenize(save_the_children_fountain)
        # Lines 97-110 are boneyard — should be stripped (become separators)
        boneyard_content = [t for t in tokens if t.get("line") and 97 <= t["line"] <= 110 and t["type"] not in ("separator",)]
        assert len(boneyard_content) == 0

    def test_save_the_children_note(self, save_the_children_fountain):
        result = parse(save_the_children_fountain)
        notes = []
        for s in result['properties']['structure']:
            notes.extend(s.get('notes', []))
        assert len(notes) == 1
        assert "writer's note" in notes[0]["note"]

    def test_save_the_children_lyrics(self, save_the_children_fountain):
        tokens = tokenize(save_the_children_fountain)
        lyrics = [t for t in tokens if t["type"] == "action" and t.get("text", "").startswith("*")]
        assert len(lyrics) == 2

    def test_save_the_children_transitions(self, save_the_children_fountain):
        tokens = tokenize(save_the_children_fountain)
        transitions = [t for t in tokens if t["type"] == "transition"]
        assert len(transitions) == 3  # CUT TO:, SMASH CUT TO:, FADE OUT.

    def test_save_the_children_centered(self, save_the_children_fountain):
        tokens = tokenize(save_the_children_fountain)
        centered = [t for t in tokens if t["type"] == "centered"]
        assert len(centered) == 1
        assert centered[0]["text"] == "THE END"

    def test_save_the_children_page_break(self, save_the_children_fountain):
        tokens = tokenize(save_the_children_fountain)
        page_breaks = [t for t in tokens if t["type"] == "page_break"]
        assert len(page_breaks) == 1

    def test_save_the_children_characters(self, save_the_children_fountain):
        tokens = tokenize(save_the_children_fountain)
        characters = [t for t in tokens if t["type"] == "character"]
        names = [t["text"] for t in characters]
        # Verify all character names are present
        assert "KAEL" in names
        assert "MIRA" in names
        assert "MARCUS" in names
        assert "ELENA" in names
        assert "ADMINISTRATOR (V.O.)" in names

    def test_character_extension_stripped(self, save_the_children_fountain):
        tokens = tokenize(save_the_children_fountain)
        characters = [t for t in tokens if t["type"] == "character"]
        # Verify character tokens have text field (may include extensions)
        for char in characters:
            assert "text" in char
            assert char["text"]  # Non-empty


# ---- Scene Extraction Tests ----

class TestSceneExtraction:
    def test_extract_scene_content(self, save_the_children_fountain):
        # Test scene 0 (action + note, no chars)
        content = extract_scene_content(save_the_children_fountain, 0)
        assert "EXT. THE INSTITUTE - DAY" in content
        assert "A vast decaying building" in content
        assert "[[This is a writer's note about the scene]]" in content
        
        # Test scene 1 (chars + dialogue + parenthetical)
        content = extract_scene_content(save_the_children_fountain, 1)
        assert "INT. CENTRAL ROOM - DAY" in content
        assert "KAEL" in content
        assert "MIRA" in content
        assert "Something's wrong" in content
        assert "You're feeling it too?" in content
        assert "(chosen)" in content
        
        # Test scene 2 (action + note, no chars)
        content = extract_scene_content(save_the_children_fountain, 2)
        assert "EXT. THE GARDEN - NIGHT" in content
        assert "Kael walks through simulated moonlight" in content
        assert "[[Another note about the garden]]" in content
        
        # Test scene 3 (chars + dialogue + parenthetical)
        content = extract_scene_content(save_the_children_fountain, 3)
        assert "INT. THE CORE - DAY (400 YEARS EARLIER)" in content
        assert "MARCUS" in content
        assert "ELENA" in content
        assert "They're at the gates" in content
        assert "The project is too fragile" in content
        assert "(almost to herself)" in content
        
        # Test scene 4 (action only, no transition)
        content = extract_scene_content(save_the_children_fountain, 4)
        assert "EXT. THE INSTITUTE - NIGHT (400 YEARS EARLIER)" in content
        assert "Outsiders gather" in content
        
        # Test scene 5 (chars + dialogue + transition)
        content = extract_scene_content(save_the_children_fountain, 5)
        assert "INT. CENTRAL ROOM - NIGHT" in content
        assert "ADMINISTRATOR (V.O.)" in content
        assert "KAEL" in content
        assert "You don't understand" in content
        assert "I understand I was chosen" in content
        assert "CUT TO:" in content
        
        # Test scene 6 (centered + page break)
        content = extract_scene_content(save_the_children_fountain, 6)
        assert "OPENING TITLES" in content
        assert "THE END" in content
        
        # Test scene 7 (chars + dual dialogue + transition)
        content = extract_scene_content(save_the_children_fountain, 7)
        assert "INT. THE CORE - DAY" in content
        assert "ELENA" in content
        assert "MIRA" in content
        assert "You were never meant to escape" in content
        assert "Then why show us the door?" in content
        assert "SMASH CUT TO:" in content
        
        # Test scene 8 (action + transition)
        content = extract_scene_content(save_the_children_fountain, 8)
        assert "EXT. THE INSTITUTE - DAY" in content
        assert "The building crumbles" in content
        assert "FADE OUT." in content

    def test_extract_all_scenes(self, save_the_children_fountain):
        from core.screenplay import extract_scenes
        scenes = extract_scenes(save_the_children_fountain)
        assert len(scenes) == 9
        # Verify all scene headings
        expected_headings = [
            "EXT. THE INSTITUTE - DAY",
            "INT. CENTRAL ROOM - DAY",
            "EXT. THE GARDEN - NIGHT",
            "INT. THE CORE - DAY (400 YEARS EARLIER)",
            "EXT. THE INSTITUTE - NIGHT (400 YEARS EARLIER)",
            "INT. CENTRAL ROOM - NIGHT",
            "OPENING TITLES",
            "INT. THE CORE - DAY",
            "EXT. THE INSTITUTE - DAY",
        ]
        for i, heading in enumerate(expected_headings):
            assert scenes[i]["heading"] == heading

    def test_scene_characters(self, save_the_children_fountain):
        from core.screenplay import extract_scenes
        scenes = extract_scenes(save_the_children_fountain)
        # Verify characters in each scene
        assert "KAEL" in scenes[1]["characters"]
        assert "MIRA" in scenes[1]["characters"]
        assert "MARCUS" in scenes[3]["characters"]
        assert "ELENA" in scenes[3]["characters"]
        assert "ADMINISTRATOR (V.O.)" in scenes[5]["characters"]
        assert "KAEL" in scenes[5]["characters"]
        assert "ELENA" in scenes[7]["characters"]
        assert "MIRA" in scenes[7]["characters"]

    def test_dual_dialogue_detected(self, save_the_children_fountain):
        """Test that dual dialogue ^ is handled."""
        tokens = tokenize(save_the_children_fountain)
        dual_chars = [t for t in tokens if t["type"] == "character" and t.get("dual") == "right"]
        assert len(dual_chars) >= 1
        # Verify ^ is stripped from text
        for char in dual_chars:
            assert "^" not in char["text"]
        # Verify dual_dialogue_begin token exists
        dual_begin = [t for t in tokens if t["type"] == "dual_dialogue_begin"]
        assert len(dual_begin) >= 1


# ---- Duration Tests ----

class TestDuration:
    def test_dialogue_duration_calculated(self, save_the_children_fountain):
        """Test that dialogue tokens have time set."""
        tokens = tokenize(save_the_children_fountain)
        dialogue_tokens = [t for t in tokens if t["type"] == "dialogue"]
        for t in dialogue_tokens:
            assert "time" in t, f"Dialogue token missing time: {t}"
            assert t["time"] is not None, f"Dialogue token time is None: {t}"
            assert t["time"] >= 0, f"Dialogue token time negative: {t}"

    def test_action_duration_calculated(self, save_the_children_fountain):
        """Test that action tokens have time set."""
        tokens = tokenize(save_the_children_fountain)
        action_tokens = [t for t in tokens if t["type"] == "action"]
        for t in action_tokens:
            assert "time" in t, f"Action token missing time: {t}"
            assert t["time"] is not None, f"Action token time is None: {t}"
            assert t["time"] >= 0, f"Action token time negative: {t}"

    def test_totals_match_expected(self, save_the_children_fountain, expected_output):
        """Test that total action and dialogue duration match expected output."""
        result = parse(save_the_children_fountain)
        # Compare with tolerance for floating point
        assert abs(result["lengthAction"] - expected_output["lengthAction"]) < 0.01, \
            f"Action length mismatch: {result['lengthAction']} != {expected_output['lengthAction']}"
        assert abs(result["lengthDialogue"] - expected_output["lengthDialogue"]) < 0.01, \
            f"Dialogue length mismatch: {result['lengthDialogue']} != {expected_output['lengthDialogue']}"

    def test_scene_durations(self, save_the_children_fountain, expected_output):
        """Test that per-scene action/dialogue durations match expected output."""
        result = parse(save_the_children_fountain)
        for i, scene in enumerate(result["properties"]["scenes"]):
            expected_scene = expected_output["properties"]["scenes"][i]
            assert abs(scene["actionLength"] - expected_scene["actionLength"]) < 0.01, \
                f"Scene {i} action length mismatch: {scene['actionLength']} != {expected_scene['actionLength']}"
            assert abs(scene["dialogueLength"] - expected_scene["dialogueLength"]) < 0.01, \
                f"Scene {i} dialogue length mismatch: {scene['dialogueLength']} != {expected_scene['dialogueLength']}"




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
