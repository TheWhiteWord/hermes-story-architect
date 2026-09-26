"""The five extended views of story_load.

The base view is the once-per-session map and is deliberately slim — it must
stay that way, since its whole job is to be cheap enough to always load. These
tests exist to keep it slim (it is pinned by exact shape) and to keep each view
answering exactly one question.

The design rule they all share: a view is a *budget*, not a feature. Loading
more is a deliberate act, which is what keeps the default affordable at 90+
scenes.
"""

import json
import shutil
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

FIXTURE = Path(__file__).parent / "fixtures" / "save-the-children"


@pytest.fixture
def project(tmp_path, monkeypatch):
    vault = tmp_path / "v"
    shutil.copytree(FIXTURE, vault / "projects" / "save-the-children")
    import core.config
    monkeypatch.setattr(core.config, "load_plugin_config",
                        lambda: {"root_path": str(vault)})
    from tools.story_import import handler as import_handler
    import_handler({"project": "save-the-children", "confirm": True}, root_path=str(vault))
    return vault / "projects" / "save-the-children"


def load(project, **args):
    from tools.story_load import handler
    vault = str(project.parent.parent)
    return json.loads(handler({"project": "save-the-children", **args}, root_path=vault))


class TestPlotBeatsLiveInTheirOwnView:
    """The base map names plots; it does not enumerate their beats.

    setups/crisis/climax/payoffs are per-scene in
    view='dramatic_elements' with add_plot, and story_retrieve returns the plot
    whole. Repeating bare scene ids in the map cost tokens and told you nothing
    the other two surfaces don't say better.
    """

    def test_base_map_has_no_plot_beats(self, project):
        result = load(project)
        assert result["plots"], "fixture should have plots"
        for plot in result["plots"]:
            assert not {"setups", "crisis", "climax", "payoffs"} & plot.keys()

    def test_dramatic_elements_with_add_plot_still_has_every_beat_kind(self, project):
        result = load(project, view="dramatic_elements", add_plot=True)
        roles = {p["role"]
                 for act in result["acts"] for seq in act.get("sequences", [])
                 for scene in seq.get("scenes", []) for p in scene.get("plots", [])}
        assert roles, "add_plot returned no plot references at all"
        assert roles <= {"setup", "crisis", "climax", "payoff"}

    def test_retrieve_returns_the_plot_beats(self, project):
        from tools.story_retrieve import handler as retrieve_handler
        import json as _json
        plot_id = load(project)["plots"][0]["id"]
        got = _json.loads(retrieve_handler({
            "project": "save-the-children", "entity_type": "plot",
            "id": [plot_id], "fields": ["all"], "root_path": str(project.parent.parent),
        }))["entities"][0]["fields"]
        beats = got.get("setups", []) + got.get("crisis", []) \
            + got.get("climax", []) + got.get("payoffs", [])
        assert beats, f"{plot_id} lost its beats — they are readable nowhere"


class TestBaseViewIsUnchanged:
    """The default view must not grow. It is pinned by shape, not by content."""

    def test_base_view_has_no_view_key(self, project):
        assert "view" not in load(project)

    def test_base_view_keeps_its_slim_key_set(self, project):
        assert set(load(project)) == {
            "loaded", "confirmation", "project", "acts",
            "characters", "plots", "worlds", "memory"}

    def test_base_view_carries_no_domain_depth(self, project):
        """The base map deliberately omits the domains the views own."""
        base = load(project)
        assert "relationships" not in base
        assert "unfilled" not in base
        # No arc beats, and no per-character perspective data — the two heaviest
        # domains, which is exactly what the views are for. A single
        # dramatic_role per scene *is* kept: at one short string it earns its
        # place in the map.
        dumped = json.dumps(base)
        assert "is_crisis" not in dumped
        assert "perspectives" not in dumped
        assert "arc_beat" not in dumped

    def test_base_view_stays_small_as_the_project_grows(self, project):
        """The cost that justifies the views: a scene must be near-free."""
        from tools.story_load import handler
        vault = str(project.parent.parent)
        small = len(json.dumps(load(project)))
        from tools.story_create import handler as create_handler
        for i in range(40):
            create_handler({"entity_type": "scene", "slug": f"extra-{i:02d}",
                            "project": "save-the-children",
                            "frontmatter": {"title": f"Extra {i}",
                                            "sequence_id": "seq-discovery"}},
                           root_path=vault)
        grown = len(json.dumps(load(project)))
        # 40 scenes must not cost more than a trivial slice of the budget.
        assert (grown - small) / 40 < 40, f"{grown - small} chars for 40 scenes"


class TestArcView:
    def test_one_character_returns_beats_in_order(self, project):
        r = load(project, view="arc", character="kael")
        assert r["character"] == "kael"
        assert [b["id"] for b in r["beats"]] == ["kael-1", "kael-2", "kael-3"]

    def test_beats_carry_the_value_shift(self, project):
        beat = load(project, view="arc", character="kael")["beats"][0]
        assert beat["shift"] == "positive → mixed"
        assert beat["y"] == 0.8

    def test_no_character_returns_every_arc(self, project):
        r = load(project, view="arc")
        got = {a["character"] for a in r["arcs"]}
        assert "kael" in got and "marcus-chen" in got

    def test_unknown_character_is_empty_not_an_error(self, project):
        r = load(project, view="arc", character="nobody")
        assert r["beats"] == []
        assert "note" in r


class TestStoryValueView:
    def test_returns_value_at_project_and_act_level(self, project):
        r = load(project, view="story_value")
        assert r["story_value"] == "Trust"
        assert r["value_at_open"] and r["value_at_close"]
        assert [a["id"] for a in r["acts"]] == ["act-1"]

    def test_act_filter_narrows(self, project):
        assert load(project, view="story_value", act="act-1")["acts"]
        assert load(project, view="story_value", act="act-99")["acts"] == []


class TestDramaticElementsView:
    def test_nests_scenes_under_sequence_under_act(self, project):
        scenes = (load(project, view="dramatic_elements")["acts"][0]
                  ["sequences"][0]["scenes"])
        assert [s["id"] for s in scenes] == [
            "central-room-day", "central-room-night", "the-core-day"]

    def test_carries_the_dramatic_role(self, project):
        scenes = (load(project, view="dramatic_elements")["acts"][0]
                  ["sequences"][0]["scenes"])
        assert scenes[0]["dramatic_role"] == "setup"
        assert scenes[1]["dramatic_role"] == "climax"

    def test_plots_are_absent_unless_asked_for(self, project):
        scenes = (load(project, view="dramatic_elements")["acts"][0]
                  ["sequences"][0]["scenes"])
        assert all("plots" not in s for s in scenes)

    def test_add_plot_attaches_the_role_and_description(self, project):
        """The role must be derived from the relation kind, not guessed."""
        scenes = (load(project, view="dramatic_elements", add_plot=True)
                  ["acts"][0]["sequences"][0]["scenes"])
        setup = scenes[0]["plots"][0]
        assert setup == {"plot": "the-resistance", "role": "setup",
                         "description": "Kael discovers the door isn't locked "
                                        "— it was never locked."}
        assert scenes[2]["plots"][0]["role"] == "payoff"

    def test_add_plot_is_echoed_so_the_agent_knows(self, project):
        assert load(project, view="dramatic_elements",
                    add_plot=True)["add_plot"] is True


class TestRelationshipView:
    def test_returns_every_relationship(self, project):
        r = load(project, view="relationship")
        assert {x["id"] for x in r["relationships"]} >= {
            "kael-mira", "kael-the-administrator"}

    def test_perspectives_are_flat_and_name_the_character(self, project):
        """Keyed-by-character dicts would be fine in storage but unreadable here."""
        rel = load(project, view="relationship")["relationships"][0]
        first = rel["perspectives"][0]
        assert set(first) == {"character", "type", "label", "feeling",
                              "strength", "secret"}
        assert first["character"] in rel["characters"]


class TestUnfilledView:
    def test_answers_what_next(self, project):
        r = load(project, view="unfilled")
        assert r["total_gaps"] > 0
        assert r["unfilled"][0]["field"] == "goals_long"

    def test_ranks_by_how_many_entities_share_the_gap(self, project):
        counts = [i["count"] for i in load(project, view="unfilled")["unfilled"]]
        assert counts == sorted(counts, reverse=True)

    def test_is_capped_so_it_stays_a_suggestion_not_an_inventory(self, project):
        r = load(project, view="unfilled")
        assert len(r["unfilled"]) <= 15
        assert r["truncated"] is True

    def test_truncation_is_honest_about_what_is_hidden(self, project):
        r = load(project, view="unfilled")
        assert r["shown_types"] == len(r["unfilled"])
        assert str(r["gap_types"]) in r["hint"]

    def test_every_entry_names_its_entities_and_count(self, project):
        for item in load(project, view="unfilled")["unfilled"]:
            assert item["count"] == len(item["entities"])


class TestDispatch:
    def test_unknown_view_lists_the_valid_ones(self, project):
        r = load(project, view="nonsense")
        assert "unfilled" in r["error"]
        for v in ("arc", "story_value", "dramatic_elements", "relationship"):
            assert v in r["error"]

    def test_every_view_is_documented_in_the_schema(self, project):
        from tools.story_load import SCHEMA
        assert set(SCHEMA["properties"]["view"]["enum"]) == {
            "arc", "story_value", "dramatic_elements", "relationship", "unfilled"}
