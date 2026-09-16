"""Tests for arc coherence checks (Phase 1), graph decoupling (Phase 2), and coherence visualization (Phase 3)."""
import pytest
from pathlib import Path
from core.coherence import (
    compute_coherence,
    _act_direction,
    _y_sign,
    _charge_to_sign,
    _charge_delta,
    _beats_for_character,
    _scenes_in_act,
    CHARGE_SIGN,
    DIRECTIONAL_ALIGNMENT_MIN_DELTA,
    ESCALATION_IMBALANCE_RATIO,
)
from core.constants import ENTITY_SCHEMAS


# ─── Helpers ───────────────────────────────────────────────────────────────


def _make_index(
    characters=None,
    arcs=None,
    acts=None,
    scenes=None,
    project=None,
):
    """Build a minimal index dict for testing."""
    return {
        "characters": characters or [],
        "arcs": arcs or [],
        "acts": acts or [],
        "scenes": scenes or [],
        "project": project or {},
    }


def _act(act_id="act-1", order=1, value_open="positive", value_close="negative", climax_scene_id=""):
    return {
        "id": act_id, "title": f"Act {act_id}", "order": order,
        "value_open": value_open, "value_close": value_close,
        "climax_scene_id": climax_scene_id,
    }


def _scene(scene_id, act_id, order=1):
    return {"id": scene_id, "act_id": act_id, "order": order}


def _beat(beat_id, character, scene, y, order, is_crisis=False, is_climax=False):
    return {
        "id": beat_id, "character": character, "scene": scene,
        "y": y, "order": order, "is_crisis": is_crisis, "is_climax": is_climax,
    }


def _char(char_id, role):
    return {"id": char_id, "story_role": role}


# ─── Test helper functions ─────────────────────────────────────────────────


class TestHelperFunctions:
    def test_act_direction_positive_to_negative(self):
        assert _act_direction(_act(value_open="positive", value_close="negative")) == -1

    def test_act_direction_negative_to_positive(self):
        assert _act_direction(_act(value_open="negative", value_close="positive")) == 1

    def test_act_direction_no_change(self):
        assert _act_direction(_act(value_open="positive", value_close="positive")) == 0

    def test_act_direction_mixed_charges(self):
        assert _act_direction(_act(value_open="mixed", value_close="positive")) == 1

    def test_y_sign_positive(self):
        assert _y_sign(0.5) == 1

    def test_y_sign_negative(self):
        assert _y_sign(-0.3) == -1

    def test_y_sign_zero(self):
        assert _y_sign(0) == 0

    def test_y_sign_non_numeric(self):
        assert _y_sign("abc") == 0

    def test_charge_sign_mapping(self):
        assert CHARGE_SIGN["positive"] == 1
        assert CHARGE_SIGN["negative"] == -1
        assert CHARGE_SIGN["mixed"] == 0
        assert CHARGE_SIGN["ironic"] == 0

    def test_charge_to_sign_known(self):
        assert _charge_to_sign("positive") == 1
        assert _charge_to_sign("negative") == -1

    def test_charge_to_sign_unknown(self):
        assert _charge_to_sign("unknown") == 0

    def test_charge_delta_positive_shift(self):
        assert _charge_delta("negative", "positive") == 1

    def test_charge_delta_negative_shift(self):
        assert _charge_delta("positive", "negative") == -1

    def test_charge_delta_no_shift(self):
        assert _charge_delta("positive", "positive") == 0

    def test_beats_for_character_filters_and_sorts(self):
        index = _make_index(arcs=[
            _beat("2", "kael", "s1", 0.0, 2),
            _beat("1", "kael", "s2", 0.0, 1),
            _beat("1", "elena", "s1", 0.0, 1),
        ])
        result = _beats_for_character(index, "kael")
        assert [b["id"] for b in result] == ["1", "2"]

    def test_scenes_in_act(self):
        index = _make_index(scenes=[
            _scene("s1", "act-1"), _scene("s2", "act-1"), _scene("s3", "act-2"),
        ])
        assert set(_scenes_in_act(index, "act-1")) == {"s1", "s2"}
        assert _scenes_in_act(index, "act-2") == ["s3"]
        assert _scenes_in_act(index, "act-3") == []


# ─── Test Directional Alignment ─────────────────────────────────────────────


class TestDirectionalAlignment:
    def test_aligned_no_flag(self):
        """Protagonist net Δy matches structural direction — no flag."""
        index = _make_index(
            characters=[_char("kael", "Protagonist")],
            arcs=[
                _beat("1", "kael", "s1", 0.0, 1),
                _beat("2", "kael", "s2", -0.8, 2),
            ],
            acts=[_act(value_open="positive", value_close="negative")],
            scenes=[_scene("s1", "act-1"), _scene("s2", "act-1")],
        )
        flags = compute_coherence(index)
        assert not any(f["check"] == "directional_alignment" for f in flags)

    def test_misaligned_flags(self):
        """Protagonist net Δy opposes structural direction — flag."""
        index = _make_index(
            characters=[_char("kael", "Protagonist")],
            arcs=[
                _beat("1", "kael", "s1", 0.0, 1),
                _beat("2", "kael", "s2", 0.8, 2),
            ],
            acts=[_act(value_open="positive", value_close="negative")],
            scenes=[_scene("s1", "act-1"), _scene("s2", "act-1")],
        )
        flags = compute_coherence(index)
        assert any(f["check"] == "directional_alignment" for f in flags)

    def test_small_movement_no_flag(self):
        """Net Δy below threshold — no flag even if opposing."""
        index = _make_index(
            characters=[_char("kael", "Protagonist")],
            arcs=[
                _beat("1", "kael", "s1", 0.0, 1),
                _beat("2", "kael", "s2", -0.1, 2),
            ],
            acts=[_act(value_open="positive", value_close="negative")],
            scenes=[_scene("s1", "act-1"), _scene("s2", "act-1")],
        )
        flags = compute_coherence(index)
        assert not any(f["check"] == "directional_alignment" for f in flags)

    def test_multiple_acts_independent(self):
        """Each act checked independently — one misalignment doesn't flag others."""
        index = _make_index(
            characters=[_char("kael", "Protagonist")],
            arcs=[
                _beat("1", "kael", "s1", 0.0, 1),
                _beat("2", "kael", "s2", 0.8, 2),  # Act 1: positive net, struct negative → flag
                _beat("3", "kael", "s3", 0.0, 3),
                _beat("4", "kael", "s4", -0.8, 4),  # Act 2: negative net, struct positive → flag
            ],
            acts=[
                _act("act-1", 1, "positive", "negative"),
                _act("act-2", 2, "negative", "positive"),
            ],
            scenes=[_scene("s1", "act-1"), _scene("s2", "act-1"),
                    _scene("s3", "act-2"), _scene("s4", "act-2")],
        )
        flags = compute_coherence(index)
        dir_flags = [f for f in flags if f["check"] == "directional_alignment"]
        assert len(dir_flags) == 2


# ─── Test Escalation ────────────────────────────────────────────────────────


class TestEscalation:
    def test_escalates_no_flag(self):
        """Peak |Δy| increases act over act — no flag."""
        index = _make_index(
            characters=[_char("kael", "Protagonist")],
            arcs=[
                _beat("1", "kael", "s1", 0.0, 1),
                _beat("2", "kael", "s2", 0.3, 2),
                _beat("3", "kael", "s3", 0.0, 3),
                _beat("4", "kael", "s4", 0.9, 4),
            ],
            acts=[_act("act-1", 1), _act("act-2", 2)],
            scenes=[_scene("s1", "act-1"), _scene("s2", "act-1"),
                    _scene("s3", "act-2"), _scene("s4", "act-2")],
        )
        flags = compute_coherence(index)
        assert not any(f["check"] == "escalation" for f in flags)

    def test_peaks_early_flags(self):
        """Act 1 peak > 1.5× Act 2 peak — flag."""
        index = _make_index(
            characters=[_char("kael", "Protagonist")],
            arcs=[
                _beat("1", "kael", "s1", 0.0, 1),
                _beat("2", "kael", "s2", 0.9, 2),  # Act 1 peak = 0.9
                _beat("3", "kael", "s3", 0.0, 3),
                _beat("4", "kael", "s4", 0.3, 4),  # Act 2 peak = 0.3
            ],
            acts=[_act("act-1", 1), _act("act-2", 2)],
            scenes=[_scene("s1", "act-1"), _scene("s2", "act-1"),
                    _scene("s3", "act-2"), _scene("s4", "act-2")],
        )
        flags = compute_coherence(index)
        esc_flags = [f for f in flags if f["check"] == "escalation"]
        assert len(esc_flags) >= 1

    def test_single_act_skipped(self):
        """Only 1 act — escalation check skipped."""
        index = _make_index(
            characters=[_char("kael", "Protagonist")],
            arcs=[
                _beat("1", "kael", "s1", 0.0, 1),
                _beat("2", "kael", "s2", 0.9, 2),
            ],
            acts=[_act("act-1", 1)],
            scenes=[_scene("s1", "act-1"), _scene("s2", "act-1")],
        )
        flags = compute_coherence(index)
        assert not any(f["check"] == "escalation" for f in flags)


# ─── Test Crisis Placement ─────────────────────────────────────────────────


class TestCrisisPlacement:
    def test_climax_in_final_act_no_flag(self):
        """is_climax beat in final act — no flag."""
        index = _make_index(
            characters=[_char("kael", "Protagonist")],
            arcs=[
                _beat("1", "kael", "s1", 0.0, 1),
                _beat("2", "kael", "s2", -0.5, 2, is_climax=True),
            ],
            acts=[_act("act-1", 1)],
            scenes=[_scene("s1", "act-1"), _scene("s2", "act-1")],
        )
        flags = compute_coherence(index)
        assert not any(f["check"] == "crisis_placement" for f in flags)

    def test_climax_not_in_final_act_flags(self):
        """is_climax beat in Act 1 (not final) — flag."""
        index = _make_index(
            characters=[_char("kael", "Protagonist")],
            arcs=[
                _beat("1", "kael", "s1", 0.0, 1, is_climax=True),
                _beat("2", "kael", "s2", -0.5, 2),
            ],
            acts=[_act("act-1", 1), _act("act-2", 2)],
            scenes=[_scene("s1", "act-1"), _scene("s2", "act-2")],
        )
        flags = compute_coherence(index)
        assert any(f["check"] == "crisis_placement" for f in flags)

    def test_crisis_in_final_act_flags(self):
        """is_crisis beat in final act — flag."""
        index = _make_index(
            characters=[_char("kael", "Protagonist")],
            arcs=[
                _beat("1", "kael", "s1", 0.0, 1),
                _beat("2", "kael", "s2", -0.5, 2, is_crisis=True),
            ],
            acts=[_act("act-1", 1)],
            scenes=[_scene("s1", "act-1"), _scene("s2", "act-1")],
        )
        flags = compute_coherence(index)
        assert any(f["check"] == "crisis_placement" for f in flags)


# ─── Test Controlling Idea ─────────────────────────────────────────────────


class TestControllingIdea:
    def test_aligned_no_flag(self):
        """Protagonist y_final matches project value_at_close — no flag."""
        index = _make_index(
            characters=[_char("kael", "Protagonist")],
            arcs=[
                _beat("1", "kael", "s1", 0.0, 1),
                _beat("2", "kael", "s2", -0.8, 2),
            ],
            acts=[_act("act-1", 1)],
            scenes=[_scene("s1", "act-1"), _scene("s2", "act-1")],
            project={"value_at_close": "negative"},
        )
        flags = compute_coherence(index)
        assert not any(f["check"] == "controlling_idea" for f in flags)

    def test_contradicts_flags(self):
        """Protagonist y_final opposite to value_at_close — flag."""
        index = _make_index(
            characters=[_char("kael", "Protagonist")],
            arcs=[
                _beat("1", "kael", "s1", 0.0, 1),
                _beat("2", "kael", "s2", 0.8, 2),
            ],
            acts=[_act("act-1", 1)],
            scenes=[_scene("s1", "act-1"), _scene("s2", "act-1")],
            project={"value_at_close": "negative"},
        )
        flags = compute_coherence(index)
        assert any(f["check"] == "controlling_idea" for f in flags)


# ─── Test Antagonist Divergence ─────────────────────────────────────────────


class TestAntagonistDivergence:
    def test_diverge_at_climax_no_flag(self):
        """P and A move opposite at climax — no flag."""
        index = _make_index(
            characters=[_char("kael", "Protagonist"), _char("admin", "Antagonist")],
            arcs=[
                _beat("p1", "kael", "s1", 0.0, 1),
                _beat("p2", "kael", "s2", -0.8, 2),
                _beat("a1", "admin", "s1", 0.0, 1),
                _beat("a2", "admin", "s2", 0.8, 2),
            ],
            acts=[_act("act-1", 1, climax_scene_id="s2")],
            scenes=[_scene("s1", "act-1"), _scene("s2", "act-1")],
        )
        flags = compute_coherence(index)
        assert not any(f["check"] == "antagonist_divergence" for f in flags)

    def test_converge_at_climax_flags(self):
        """P and A move same direction at climax — flag."""
        index = _make_index(
            characters=[_char("kael", "Protagonist"), _char("admin", "Antagonist")],
            arcs=[
                _beat("p1", "kael", "s1", 0.0, 1),
                _beat("p2", "kael", "s2", 0.8, 2),
                _beat("a1", "admin", "s1", 0.0, 1),
                _beat("a2", "admin", "s2", 0.8, 2),
            ],
            acts=[_act("act-1", 1, climax_scene_id="s2")],
            scenes=[_scene("s1", "act-1"), _scene("s2", "act-1")],
        )
        flags = compute_coherence(index)
        assert any(f["check"] == "antagonist_divergence" for f in flags)

    def test_no_antagonist_skipped(self):
        """No antagonist — check skipped."""
        index = _make_index(
            characters=[_char("kael", "Protagonist")],
            arcs=[
                _beat("p1", "kael", "s1", 0.0, 1),
                _beat("p2", "kael", "s2", 0.8, 2),
            ],
            acts=[_act("act-1", 1, climax_scene_id="s2")],
            scenes=[_scene("s1", "act-1"), _scene("s2", "act-1")],
        )
        flags = compute_coherence(index)
        assert not any(f["check"] == "antagonist_divergence" for f in flags)


# ─── Test compute_coherence integration ─────────────────────────────────────


class TestComputeCoherence:
    def test_empty_index_no_flags(self):
        """Empty/minimal index — no flags."""
        index = _make_index()
        assert compute_coherence(index) == []

    def test_no_protagonist_no_flags(self):
        """No protagonist — no flags."""
        index = _make_index(
            characters=[_char("elena", "Supporting")],
            arcs=[_beat("1", "elena", "s1", 0.5, 1)],
            acts=[_act("act-1", 1)],
            scenes=[_scene("s1", "act-1")],
        )
        assert compute_coherence(index) == []

    def test_full_fixture_all_checks_run(self):
        """Full index — all applicable checks run."""
        from pathlib import Path
        from core.index import generate_index

        index = generate_index(Path("tests/fixtures/save-the-children"))
        flags = compute_coherence(index)
        # Kael ends at +0.5 (positive) but project value_at_close is negative → controlling_idea flag
        assert len(flags) >= 1
        assert any(f["check"] == "controlling_idea" for f in flags)

    def test_flag_format_consistent(self):
        """All flags have required keys."""
        index = _make_index(
            characters=[_char("kael", "Protagonist")],
            arcs=[
                _beat("1", "kael", "s1", 0.0, 1),
                _beat("2", "kael", "s2", 0.8, 2),
            ],
            acts=[_act(value_open="positive", value_close="negative")],
            scenes=[_scene("s1", "act-1"), _scene("s2", "act-1")],
        )
        flags = compute_coherence(index)
        for f in flags:
            assert "check" in f
            assert "severity" in f
            assert "act" in f
            assert "message" in f
            assert "data" in f





# ─── Phase 4: Fixture Integration ────────────────────────────────────────


class TestCoherenceFixtureIntegration:
    FIXTURE_PATH = Path(__file__).parent / "fixtures" / "save-the-children"

    def test_controlling_idea_flag(self):
        """Protagonist ends at +0.5 but project closes negative — should flag."""
        from core.coherence import compute_coherence
        from core.index import generate_index
        index = generate_index(self.FIXTURE_PATH)
        flags = compute_coherence(index)
        controlling = [f for f in flags if f["check"] == "controlling_idea"]
        assert len(controlling) == 1
        assert "opposite" in controlling[0]["message"].lower() or "contradiction" in controlling[0]["message"].lower()

    def test_antagonist_divergence_no_flag(self):
        """P and A diverge at climax — no flag expected."""
        from core.coherence import compute_coherence
        from core.index import generate_index
        index = generate_index(self.FIXTURE_PATH)
        flags = compute_coherence(index)
        divergence = [f for f in flags if f["check"] == "antagonist_divergence"]
        assert len(divergence) == 0

    def test_protagonist_beats_all_in_act1(self):
        """All protagonist beats are in act-1 — escalation skipped (single act)."""
        from core.coherence import compute_coherence
        from core.index import generate_index
        index = generate_index(self.FIXTURE_PATH)
        flags = compute_coherence(index)
        escalation = [f for f in flags if f["check"] == "escalation"]
        assert len(escalation) == 0

    def test_full_coherence_report_structure(self):
        """All flags have required fields."""
        from core.coherence import compute_coherence
        from core.index import generate_index
        index = generate_index(self.FIXTURE_PATH)
        flags = compute_coherence(index)
        for f in flags:
            assert "check" in f
            assert "severity" in f
            assert "act" in f
            assert "message" in f
            assert "data" in f


class TestGraphDecoupling:
    def test_project_has_act_count(self):
        """act_count defaults to 3 at project creation."""
        schema = ENTITY_SCHEMAS["project"]
        assert "act_count" in schema
        assert schema["act_count"]["type"] == "number"
        assert schema["act_count"]["default"] == 3

    def test_act_count_auto_adjusts(self):
        """act_count auto-adjusts upward if more act files exist."""
        from core.index import _parse_project
        from pathlib import Path

        result = _parse_project(
            Path("."), [], [], [], [],
            scenes_count=0, sequences_count=0, acts_count=4, arcs_count=0,
        )
        assert result["act_count"] == 4

    def test_act_count_manual_override(self):
        """act_count can be set manually and persists if higher than file count."""
        from core.index import _parse_project
        from pathlib import Path

        # Without a real project.md, declared defaults to 3, acts_count=2 → max=3
        result = _parse_project(
            Path("."), [], [], [], [],
            scenes_count=0, sequences_count=0, acts_count=2, arcs_count=0,
        )
        assert result["act_count"] == 3

    def test_graph_renders_empty_bands(self):
        """Graph renders act_count bands even with no act files."""
        with open("src/dashboard/story-dashboard.html") as f:
            js = f.read()
        assert "arc-act-band" in js
        assert "actCount" in js
        assert "actBandwidth" in js


# ─── Phase 3: Coherence Visualization ───────────────────────────────────


class TestDashboardVisualization:
    """Test that dashboard HTML/JS includes coherence visualization elements."""

    @pytest.fixture
    def dashboard_html(self):
        return Path("src/dashboard/story-dashboard.html").read_text()

    @pytest.fixture
    def dashboard_py(self):
        return Path("tools/story_dashboard.py").read_text()

    def test_delta_bar_css_exists(self, dashboard_html):
        """Delta bar CSS classes are defined."""
        assert ".arc-delta-bar" in dashboard_html
        assert ".arc-delta-bar-bar" in dashboard_html
        assert ".arc-delta-bar-bar.positive" in dashboard_html
        assert ".arc-delta-bar-bar.negative" in dashboard_html

    def test_structural_avenue_css_exists(self, dashboard_html):
        """Structural avenue CSS class is defined."""
        assert ".arc-structural-avenue" in dashboard_html

    def test_line_style_css_exists(self, dashboard_html):
        """Multi-character line style CSS classes are defined."""
        assert ".arc-line.antagonist" in dashboard_html
        assert ".arc-line.supporting" in dashboard_html

    def test_coherence_flag_css_exists(self, dashboard_html):
        """Coherence flag CSS class is defined."""
        assert ".arc-warning.coherence" in dashboard_html

    def test_delta_bar_html_container_exists(self, dashboard_html):
        """Delta bar HTML container is present."""
        assert 'id="arc-delta-bar"' in dashboard_html

    def test_charge_sign_mapping_exists(self, dashboard_html):
        """CHARGE_SIGN mapping is defined in buildArcGraph."""
        assert "CHARGE_SIGN" in dashboard_html
        assert "positive: 1" in dashboard_html

    def test_structural_avenue_rendered_in_svg(self, dashboard_html):
        """Structural avenue rect is rendered in SVG output."""
        assert "arc-structural-avenue" in dashboard_html

    def test_act_band_has_data_attribute(self, dashboard_html):
        """Act band rects have data-act attribute."""
        assert 'data-act=' in dashboard_html

    def test_antagonist_line_class_applied(self, dashboard_html):
        """Antagonist character lines use dashed style class."""
        assert "'antagonist'" in dashboard_html or '"antagonist"' in dashboard_html

    def test_supporting_line_class_applied(self, dashboard_html):
        """Supporting character lines use thin style class."""
        assert "'supporting'" in dashboard_html or '"supporting"' in dashboard_html

    def test_buildDeltaBar_function_exists(self, dashboard_html):
        """buildDeltaBar function is defined."""
        assert "function buildDeltaBar(" in dashboard_html

    def test_buildDeltaBar_called_in_buildArcGraph(self, dashboard_html):
        """buildDeltaBar is called at the end of buildArcGraph."""
        idx = dashboard_html.find("function buildArcGraph(")
        assert idx > 0
        end_idx = dashboard_html.find("\nfunction ", idx + 1)
        func_body = dashboard_html[idx:end_idx]
        assert "buildDeltaBar" in func_body

    def test_coherence_flags_rendered_in_warnings(self, dashboard_html):
        """Coherence flags are rendered in the warnings area with special class."""
        assert "coherenceFlags" in dashboard_html
        assert "arc-warning" in dashboard_html

    def test_coherence_flags_injected_by_backend(self, dashboard_py):
        """story_dashboard.py injects __COHERENCE_FLAGS__."""
        assert "__COHERENCE_FLAGS__" in dashboard_py
        assert "from core.coherence import compute_coherence" in dashboard_py
