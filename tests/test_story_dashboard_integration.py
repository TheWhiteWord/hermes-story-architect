"""Integration tests for Script View + Statistics Panel."""
import pytest
from pathlib import Path
from unittest.mock import patch, mock_open

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "save-the-children"


class TestDashboardIntegration:
    """Test that dashboard HTML includes all required elements."""

    @pytest.fixture
    def dashboard_html(self):
        return Path("src/dashboard/story-dashboard.html").read_text()

    def test_script_view_exists(self, dashboard_html):
        """Script view div is present."""
        assert 'id="script-view"' in dashboard_html

    def test_stats_panel_exists(self, dashboard_html):
        """Stats panel aside is present."""
        assert 'id="stats-panel"' in dashboard_html

    def test_stats_panel_width_defined(self, dashboard_html):
        """Stats panel width CSS variable defined."""
        assert '--stats-panel-w' in dashboard_html

    def test_script_nav_button_exists(self, dashboard_html):
        """Script nav button with data-view='script'."""
        assert "data-view=\"script\"" in dashboard_html

    def test_stats_element_ids_present(self, dashboard_html):
        """All required stat element IDs are in HTML."""
        required_ids = [
            'lengthStats-pagesWhole', 'lengthStats-scenes', 'lengthStats-words',
            'durationStats-total', 'durationStats-action', 'durationStats-dialogue',
            'characterStats-count', 'characterStats-monologues',
            'sceneStats-count', 'locationStats-count',
            'sceneprop-type_int', 'sceneprop-type_ext', 'sceneprop-type_mixed',
            'sceneprop-time_day', 'sceneprop-time_night',
        ]
        for eid in required_ids:
            assert f'id="{eid}"' in dashboard_html, f"Missing ID: {eid}"

    def test_build_script_view_function(self, dashboard_html):
        """buildScriptView function is defined."""
        assert 'function buildScriptView()' in dashboard_html

    def test_open_stats_panel_function(self, dashboard_html):
        """openStatsPanel function is defined."""
        assert 'function openStatsPanel()' in dashboard_html

    def test_d3_charts_functions(self, dashboard_html):
        """D3 chart rendering functions are defined."""
        assert 'function renderDurationChart(' in dashboard_html
        assert 'function renderCharacterChart(' in dashboard_html
        assert 'function renderBarcodeChart(' in dashboard_html

    def test_sort_table_function(self, dashboard_html):
        """sortTable function is defined."""
        assert 'function sortTable(' in dashboard_html

    def test_switch_view_wrapper(self, dashboard_html):
        """switchView is wrapped (not replaced)."""
        assert 'const _origSwitchView = switchView;' in dashboard_html

    def test_scene_click_matching(self, dashboard_html):
        """Scene heading click matching logic present."""
        assert 'showScenePanel(matched.id)' in dashboard_html

    def test_no_new_inline_fountain_css(self, dashboard_html):
        """New CSS (after narrow layout) does not redefine standalone .fountain-* classes."""
        narrow_idx = dashboard_html.find('/* Narrow layout */')
        assert narrow_idx > 0, "Narrow layout anchor not found"
        new_css = dashboard_html[narrow_idx:]
        # The new CSS should not redefine standalone .fountain-scene_heading etc.
        # (those are in screenplay.css which gets inlined by story_dashboard.py)
        # Check for standalone definitions (not compound selectors like .screenplay-doc .fountain-scene_heading)
        import re
        standalone = re.search(r'(?<![.\w-])fountain-scene_heading\s*\{', new_css)
        assert standalone is None, "New CSS should not define standalone .fountain-scene_heading"

    def test_d3_cdn_loaded(self, dashboard_html):
        """D3.js CDN is loaded."""
        assert 'd3.min.js' in dashboard_html

    def test_stats_computation_in_backend(self):
        """story_dashboard.py computes stats."""
        src = Path("tools/story_dashboard.py").read_text()
        assert '_compute_screenplay_stats' in src
        assert '__SCREENPLAY_STATS__' in src

    def test_stats_injected_before_boot(self):
        """Stats injected before Boot comment."""
        src = Path("tools/story_dashboard.py").read_text()
        stats_pos = src.find('__SCREENPLAY_STATS__')
        boot_pos = src.find('// ─── Boot')
        assert stats_pos > 0 and boot_pos > 0
        assert stats_pos < boot_pos

    def test_fountain_parse_imported(self):
        """fountain_parse is imported in story_dashboard.py."""
        src = Path("tools/story_dashboard.py").read_text()
        assert 'from core.fountain_lexer import parse as fountain_parse' in src

    def test_screenplay_stats_computation(self):
        """Stats computation produces expected structure."""
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "story_dashboard",
            Path("tools/story_dashboard.py"),
        )
        assert spec is not None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        fountain_text = (FIXTURE_PATH / "screenplay.fountain").read_text()
        stats = mod._compute_screenplay_stats(fountain_text)

        assert stats is not None
        assert 'lengthStats' in stats
        assert 'durationStats' in stats
        assert 'characterStats' in stats
        assert 'locationStats' in stats
        assert 'sceneStats' in stats
        assert 'titlePage' in stats
        assert 'scriptHtml' in stats

        # Verify length stats
        ls = stats['lengthStats']
        assert ls['scenes'] > 0
        assert ls['words'] > 0
        assert ls['pagesWhole'] >= 1

        # Verify duration stats
        ds = stats['durationStats']
        assert len(ds['lengthchart_action']) == 20
        assert len(ds['lengthchart_dialogue']) == 20

        # Verify character stats
        cs = stats['characterStats']
        assert cs['characterCount'] > 0
        assert len(cs['characters']) > 0
        for c in cs['characters']:
            assert 'name' in c
            assert 'color' in c
            assert 'speakingParts' in c
            assert 'secondsSpoken' in c

        # Verify scene stats
        ss = stats['sceneStats']
        assert len(ss['scenes']) > 0
        assert 'typeCounts' in ss
        assert 'timeCounts' in ss

    def test_hsl_from_name_deterministic(self):
        """_hsl_from_name produces deterministic colors."""
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "story_dashboard",
            Path("tools/story_dashboard.py"),
        )
        assert spec is not None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        c1 = mod._hsl_from_name("Kael")
        c2 = mod._hsl_from_name("Kael")
        c3 = mod._hsl_from_name("Mira")
        assert c1 == c2
        assert c1 != c3
        assert c1.startswith('hsl(')
