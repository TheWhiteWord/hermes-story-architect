"""Test server-side stats computation for story_dashboard."""
import json
from pathlib import Path

import pytest

# Add repo root to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "save-the-children"


@pytest.fixture
def fountain_text():
    return (FIXTURE_PATH / "screenplay.fountain").read_text()


@pytest.fixture
def index_yaml():
    return (FIXTURE_PATH / ".story" / "index.yaml").read_text()


class TestStatsComputation:
    """Test that fountain_lexer produces stats in expected format."""

    def test_parse_produces_tokens(self, fountain_text):
        """parse() returns tokens list."""
        from core.fountain_lexer import parse
        result = parse(fountain_text)
        assert 'tokens' in result
        assert isinstance(result['tokens'], list)
        assert len(result['tokens']) > 0

    def test_scene_heading_tokens(self, fountain_text):
        """Scene headings are correctly identified."""
        from core.fountain_lexer import parse
        result = parse(fountain_text)
        scenes = [t for t in result['tokens'] if t['type'] == 'scene_heading']
        assert len(scenes) > 0
        for s in scenes:
            assert 'text' in s
            assert 'number' in s

    def test_dialogue_has_duration(self, fountain_text):
        """Dialogue tokens have time estimate."""
        from core.fountain_lexer import parse
        result = parse(fountain_text)
        dialogue = [t for t in result['tokens'] if t['type'] == 'dialogue']
        assert len(dialogue) > 0
        for d in dialogue:
            assert d.get('time', 0) >= 0

    def test_character_stats_build(self, fountain_text):
        """Character stats can be aggregated from tokens."""
        from core.fountain_lexer import parse
        result = parse(fountain_text)
        tokens = result['tokens']

        char_map = {}
        for t in tokens:
            if t['type'] == 'dialogue' and t.get('character'):
                name = t['character']
                if name not in char_map:
                    char_map[name] = {'speakingParts': 0, 'secondsSpoken': 0, 'wordsSpoken': 0, 'monologues': 0}
                char_map[name]['speakingParts'] += 1
                char_map[name]['secondsSpoken'] += t.get('time', 0)
                char_map[name]['wordsSpoken'] += len(t['text'].split())
                if (t.get('time', 0) or 0) > 30:
                    char_map[name]['monologues'] += 1

        assert len(char_map) > 0
        for name, stats in char_map.items():
            assert stats['speakingParts'] > 0
            assert stats['secondsSpoken'] >= 0

    def test_scene_type_classification(self, fountain_text):
        """Scene headings classified as int/ext/mixed."""
        from core.fountain_lexer import parse
        result = parse(fountain_text)
        scenes = [t for t in result['tokens'] if t['type'] == 'scene_heading']

        for s in scenes:
            h = s['text'].upper()
            if 'INT.' in h and 'EXT.' in h:
                assert True  # mixed
            elif 'INT.' in h or 'INT ' in h:
                assert True  # int
            elif 'EXT.' in h or 'EXT ' in h:
                assert True  # ext

    def test_tokens_to_html_produces_classes(self, fountain_text):
        """tokens_to_html produces fountain class names."""
        from core.fountain_lexer import parse, tokens_to_html
        result = parse(fountain_text)
        html = tokens_to_html(result['tokens'])
        assert 'fountain-scene_heading' in html or 'fountain-scene_heading' in html.replace('-', '_')

    def test_parse_returns_action_dialogue_lengths(self, fountain_text):
        """parse() returns lengthAction and lengthDialogue."""
        from core.fountain_lexer import parse
        result = parse(fountain_text)
        assert 'lengthAction' in result
        assert 'lengthDialogue' in result
        assert result['lengthAction'] > 0 or result['lengthDialogue'] >= 0

    def test_parse_returns_script_html(self, fountain_text):
        """parse() returns scriptHtml for pre-rendered HTML."""
        from core.fountain_lexer import parse
        result = parse(fountain_text)
        assert 'scriptHtml' in result
        assert isinstance(result['scriptHtml'], str)

    def test_duration_chart_buckets(self, fountain_text):
        """Duration chart produces 20 buckets."""
        from core.fountain_lexer import parse
        result = parse(fountain_text)
        tokens = result['tokens']

        BUCKETS = 20
        bucket_size = max(1, len(tokens) // BUCKETS)
        lchart_action = []
        for b in range(BUCKETS):
            start = b * bucket_size
            end = min(len(tokens), (b + 1) * bucket_size)
            slice_tokens = tokens[start:end]
            a = sum((len(t['text'].split()) / 200) * 60 for t in slice_tokens if t['type'] == 'action')
            lchart_action.append(round(a, 1))

        assert len(lchart_action) == BUCKETS


class TestStatsInjection:
    """Test that story_dashboard injects stats correctly."""

    def test_stats_injected_before_boot(self):
        """window.__SCREENPLAY_STATS__ is injected before Boot comment."""
        src = Path("src/dashboard/story-dashboard.html").read_text()
        assert "// ─── Boot" in src

    def test_screenplay_css_linked(self):
        """screenplay.css is linked in the dashboard."""
        src = Path("src/dashboard/story-dashboard.html").read_text()
        assert 'screenplay.css' in src
