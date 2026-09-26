"""unfilled_fields: what counts as "not set".

The rule is "empty OR still the schema default". Both halves are load-bearing,
because some defaults are UI placeholders ("Summary not set") rather than "" —
they exist so the UI can show the user that a field needs filling.

The bug this pins: the old rule was `value == default` alone, so a field the
user *cleared* back to "" was reported as filled. The UI showed a populated field
with nothing in it and the agent got no signal that anything was missing.
"""
import pytest

from core.constants import ENTITY_SCHEMAS
from core.entity import unfilled_fields


def _unfilled(entity_type, **extra):
    return unfilled_fields(entity_type, extra)


class TestClearedFields:
    """The regression: clearing a field must make it unfilled again."""

    def test_cleared_string_is_unfilled(self):
        assert "goals_short" in _unfilled("character", goals_short="")

    def test_cleared_list_is_unfilled(self):
        assert "characters" in _unfilled("plot", characters=[])

    def test_cleared_object_is_unfilled(self):
        assert "perspectives" in _unfilled("relationship", perspectives={})

    def test_none_is_unfilled(self):
        assert "goals_short" in _unfilled("character", goals_short=None)

    def test_clearing_one_field_leaves_the_others(self):
        unfilled = _unfilled("character", goals_short="", goals_long="A quiet ambition")
        assert "goals_short" in unfilled
        assert "goals_long" not in unfilled


class TestRealContent:
    def test_content_is_filled(self):
        assert "one_sentence" not in _unfilled("plot", one_sentence="A courier who questions it.")

    def test_placeholder_default_is_unfilled(self):
        assert "one_sentence" in _unfilled("plot", one_sentence="Summary not set")

    def test_empty_default_still_unfilled(self):
        """Fields whose default is '' were already correct; keep them so."""
        assert "plot_scope" in _unfilled("plot", plot_scope="")

    def test_absent_field_uses_the_default(self):
        assert "one_sentence" in _unfilled("plot")


class TestNeverUnfilled:
    @pytest.mark.parametrize("field", ["status"])
    def test_status_is_workflow_state_not_content(self, field):
        assert field not in _unfilled("character", **{field: ""})

    def test_booleans_and_numbers_are_not_unfilled(self):
        """False and 0 are real values, not absences."""
        for entity_type, fields in ENTITY_SCHEMAS.items():
            for field, meta in fields.items():
                if meta["type"] in ("boolean", "number"):
                    assert field not in unfilled_fields(
                        entity_type, {field: False if meta["type"] == "boolean" else 0})

    def test_computed_fields_are_skipped(self):
        for entity_type, fields in ENTITY_SCHEMAS.items():
            computed = [f for f, m in fields.items() if m.get("computed")]
            for field in computed:
                assert field not in unfilled_fields(entity_type, {field: ""})


class TestSubFields:
    """The parent/child rule, whose guard this change also touched."""

    def test_empty_parent_reports_the_parent(self):
        assert "perspectives" in _unfilled("relationship", perspectives={}, characters=["kael"])

    def test_partially_filled_parent_reports_the_gap(self):
        unfilled = _unfilled("relationship",
                             perspectives={"kael": "sees everything"},
                             characters=["kael", "mira"])
        assert "perspectives.mira" in unfilled
        assert "perspectives.kael" not in unfilled

    def test_fully_filled_parent_reports_nothing(self):
        unfilled = _unfilled("relationship",
                             perspectives={"kael": "a", "mira": "b"},
                             characters=["kael", "mira"])
        assert not [u for u in unfilled if u.startswith("perspectives")]

    def test_list_parent_present_counts_as_filled(self):
        """An entry existing = filled; its notes are optional prose."""
        assert "setups" not in _unfilled("plot", setups=[{"scene_id": "s1", "description": ""}])

    def test_cleared_list_parent_is_unfilled(self):
        assert "setups" in _unfilled("plot", setups=[])
