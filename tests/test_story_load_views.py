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
from pathlib import Path

import pytest


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

    setups/complications/crisis/climax/resolutions are per-scene in
    view='dramatic_elements', and story_retrieve returns the plot
    whole. Repeating bare scene ids in the map cost tokens and told you nothing
    the other two surfaces don't say better.
    """

    def test_base_map_has_no_plot_beats(self, project):
        result = load(project)
        assert result["plots"], "fixture should have plots"
        for plot in result["plots"]:
            assert not {"setups", "complications", "crisis", "climax",
                        "resolutions"} & plot.keys()

    def test_dramatic_elements_carries_every_beat_kind(self, project):
        """No flag: the view's job is cross-checking plot roles against the
        structural milestones, and half of that was withheld behind add_plot."""
        result = load(project, view="dramatic_elements")
        roles = {p["role"]
                 for act in result["acts"] for seq in act.get("sequences", [])
                 for scene in seq.get("scenes", []) for p in scene.get("plots", [])}
        assert roles, "dramatic_elements returned no plot references at all"
        from core.constants import PLOT_ROLES
        assert roles <= set(PLOT_ROLES)

    def test_the_plot_index_sits_under_the_project(self, project):
        """A scene's `plots[]` entry is a bare slug; the index is what says
        which plot it is, how it sits against the others, and — by omission —
        which plots exist but touch no scene at all."""
        plots = load(project, view="dramatic_elements")["project"]["plots"]
        by_id = {p["id"]: p for p in plots}
        assert set(by_id) == {"the-resistance", "the-scientists-last-stand"}
        entry = by_id["the-resistance"]
        assert entry["name"] == "The Resistance"
        assert entry["plot_type"] == "Setup"
        # The fixture marks the-resistance as the main plot.
        assert entry["plot_scope"] == "main"

    def test_plot_index_carries_per_plot_milestones(self, project):
        """Each plot's index entry reports its own role scenes — the main
        plot's are the story's milestones, every sub-plot's are its own.
        The fixture gives the-resistance an inciting_incident, a climax, and
        a resolution."""
        plots = load(project, view="dramatic_elements")["project"]["plots"]
        by_id = {p["id"]: p for p in plots}
        assert by_id["the-resistance"]["milestones"] == {
            "inciting_incident": ["central-room-day"],
            "climax": ["central-room-night"],
            "resolution": ["the-core-day"],
        }
        # The sub-plot's own milestones are its own roles.
        assert by_id["the-scientists-last-stand"]["milestones"] == {
            "setup": ["central-room-day"],
        }

    def test_every_scene_plot_slug_resolves_against_the_index(self, project):
        """The cross-check the index exists for: a role naming a plot absent
        from the index has nothing to be checked against."""
        out = load(project, view="dramatic_elements")
        known = {p["id"] for p in out["project"]["plots"]}
        named = {p["plot"]
                 for act in out["acts"] for seq in act.get("sequences", [])
                 for scene in seq.get("scenes", []) for p in scene.get("plots", [])}
        assert named <= known, f"unresolvable plot slugs: {named - known}"

    def test_scene_plot_entries_carry_no_description(self, project):
        """Dropped on purpose — it is the plot note's prose and it roughly
        doubles the payload. `story_retrieve` is where a description is read."""
        out = load(project, view="dramatic_elements")
        entries = [p
                   for act in out["acts"] for seq in act.get("sequences", [])
                   for scene in seq.get("scenes", []) for p in scene.get("plots", [])]
        assert entries
        assert all(set(p) == {"plot", "role"} for p in entries)

    def test_retrieve_returns_the_plot_beats(self, project):
        """The six fields are computed, so `["all"]` skips them — name them.

        The write side moved to the scene, and `plot_roles` is in `["all"]`; this
        asserts the plot side is still readable by name, which is the cost of
        `computed` and the thing worth pinning.
        """
        from tools.story_retrieve import handler as retrieve_handler
        import json as _json
        plot_id = load(project)["plots"][0]["id"]
        got = _json.loads(retrieve_handler({
            "project": "save-the-children", "entity_type": "plot",
            "id": [plot_id],
            "fields": ["setups", "inciting_incident", "complications",
                       "crisis", "climax", "resolutions"],
            "root_path": str(project.parent.parent),
        }))["entities"][0]["fields"]
        beats = got.get("setups", []) + got.get("inciting_incident", []) \
            + got.get("complications", []) + got.get("crisis", []) \
            + got.get("climax", []) + got.get("resolutions", [])
        assert beats, f"{plot_id} lost its beats — they are readable nowhere"

    def test_the_scenes_plot_roles_are_the_write_side(self, project):
        """Same rows, reachable from the scene, which is where they are written."""
        from tools.story_retrieve import handler as retrieve_handler
        import json as _json
        got = _json.loads(retrieve_handler({
            "project": "save-the-children", "entity_type": "scene",
            "id": ["central-room-day"], "fields": ["all"],
            "root_path": str(project.parent.parent),
        }))["entities"][0]["fields"]
        assert got["plot_roles"], "the scene's own plot roles are unreadable"
        assert got["plot_roles"][0] == {
            "plot": "the-resistance", "role": "inciting_incident",
            "description": got["plot_roles"][0]["description"]}
        assert got["plot_roles"][0]["description"]


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
        small = len(json.dumps(load(project)))
        from core.writes import create_entity
        for i in range(40):
            create_entity(project, "scene", f"extra-{i:02d}",
                          {"title": f"Extra {i}", "sequence_id": "seq-discovery"})
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


class TestDramaticElementsView:
    def test_nests_scenes_under_sequence_under_act(self, project):
        scenes = (load(project, view="dramatic_elements")["acts"][0]
                  ["sequences"][0]["scenes"])
        assert [s["id"] for s in scenes] == [
            "central-room-day", "central-room-night", "the-core-day"]

    def test_carries_dramatic_role_and_the_plot_roles(self, project):
        """Both halves, because the view exists to check them against each
        other. `dramatic_role` says the scene serves a plot; `plots[]` says
        which and in what role. "plot_role" with no `plots[]` is exactly the
        disagreement worth spotting, so it must be reported, not hidden."""
        scenes = {s["id"]: s for s in
                  (load(project, view="dramatic_elements")["acts"][0]
                   ["sequences"][0]["scenes"])}
        day = scenes["central-room-day"]
        assert day["dramatic_role"] == "plot_role"
        assert day["plots"], "the plot roles must be visible alongside it"

    def test_plots_are_always_present_not_behind_a_flag(self, project):
        scenes = (load(project, view="dramatic_elements")["acts"][0]
                  ["sequences"][0]["scenes"])
        assert any("plots" in s for s in scenes), \
            "plot roles must be in the view unconditionally"

    def test_project_is_the_top_container(self, project):
        """The story's climax and inciting incident are global facts, so they
        are reported whether or not `act` narrows the tree to one act."""
        out = load(project, view="dramatic_elements")
        project = out["project"]
        assert project["structure_type"] == "Classical"
        # The fixture's main plot (the-resistance) holds central-room-day as
        # its inciting incident and central-room-night as its climax.
        assert project["story_climax_scene_id"] == ["central-room-night"]
        assert project["inciting_incident_scene_id"] == ["central-room-day"]
        # The plot index lives here too, so the scene slugs below resolve.
        assert {p["id"] for p in project["plots"]}

    def test_project_survives_the_act_filter(self, project):
        """The whole reason it is in this view: filtering to one act must not
        remove the context that says what the act is part of."""
        out = load(project, view="dramatic_elements", act="act-1")
        assert out["project"]["story_climax_scene_id"] == ["central-room-night"]
        assert [a["id"] for a in out["acts"]] == ["act-1"]

    def test_sequence_carries_its_primary_plot(self, project):
        seq = (load(project, view="dramatic_elements")["acts"][0]
               ["sequences"][0])
        assert seq["primary_plot"] == "the-resistance"

    def test_scene_reports_milestones_from_main_plot_roles(self, project):
        """Milestones are the main plot's roles. The fixture's main plot
        (the-resistance) holds central-room-night as its climax."""
        scenes = (load(project, view="dramatic_elements")["acts"][0]
                  ["sequences"][0]["scenes"])
        night = scenes[1]
        assert "milestone" in night
        assert "climax" in night["milestone"]

    def test_scene_reports_the_derived_milestone_label(self, project):
        """The milestone label is derived from the scene's plot_roles. A scene
        with a main-plot role carries the label."""
        scenes = (load(project, view="dramatic_elements")["acts"][0]
                  ["sequences"][0]["scenes"])
        assert "milestone" in scenes[1]
        assert "climax" in scenes[1]["milestone"]
        assert "milestone" in scenes[0]
        assert "inciting_incident" in scenes[0]["milestone"]

    def test_no_dead_markers_are_emitted(self, project):
        """The loop this replaced read is_setup / is_turning_point /
        is_crisis / is_climax / is_resolution — none a scene field, and two of
        them arc_beat's. If any reappear, the view is reading a key that
        belongs to another entity type."""
        scenes = (load(project, view="dramatic_elements")["acts"][0]
                  ["sequences"][0]["scenes"])
        dead = {"is_setup", "is_turning_point", "is_crisis", "is_climax",
                "is_resolution"}
        assert not [k for s in scenes for k in s if k in dead]

    def test_both_halbes_are_reported_so_they_can_be_cross_checked(self, project):
        """The reason the view carries plot roles unconditionally: a scene that
        says it serves a plot, beside the plots that agree.

        The fixture stores no `dramatic_role` on any scene, so the two states
        this test compares cannot both be produced from it — the agreement case
        has to be written. That is the fixture's gap, not a defect in the view.
        """
        from core.writes import edit_entity

        # 1. the scene says plot_role and a plot agrees -> both reported.
        edit_entity(project, "scene", "central-room-day",
                    {"dramatic_role": "plot_role"}, "r")
        scenes = {s["id"]: s for s in
                  (load(project, view="dramatic_elements")["acts"][0]
                   ["sequences"][0]["scenes"])}
        day = scenes["central-room-day"]
        assert day["dramatic_role"] == "plot_role"
        assert day["plots"], "the plot roles must be visible alongside it"

        # 2. the scene says non-event -> reported, and it serves no plot.
        edit_entity(project, "scene", "central-room-day",
                    {"dramatic_role": "non-event", "plot_roles": []}, "r")
        day = {s["id"]: s for s in
               (load(project, view="dramatic_elements")["acts"][0]
                ["sequences"][0]["scenes"])}["central-room-day"]
        assert day["dramatic_role"] == "non-event"
        assert "plots" not in day

    def test_the_role_is_derived_from_the_relation_kind(self, project):
        """Not guessed from the plot's fields — read off the `plot_<role>` row."""
        scenes = (load(project, view="dramatic_elements")
                  ["acts"][0]["sequences"][0]["scenes"])
        assert scenes[0]["plots"][0] == {"plot": "the-resistance",
                                         "role": "inciting_incident"}
        assert scenes[2]["plots"][0]["role"] == "resolution"


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
        """The top gap must be the field most entities share.

        Not a fixed field name: 16 of the fixture's 17 characters have no arc
        designed, so `character_value_at_close` legitimately outranks everything
        else. Pinning a name here would make the test fail every time the
        fixture's data changes, and pass for the wrong reason if it did not.
        """
        r = load(project, view="unfilled")
        assert r["total_gaps"] > 0
        top = r["unfilled"][0]
        assert top["count"] == max(i["count"] for i in r["unfilled"])
        assert top["count"] > 1, "a top gap shared by one entity is not 'what next?'"

    def test_ranks_by_how_many_entities_share_the_gap(self, project):
        counts = [i["count"] for i in load(project, view="unfilled")["unfilled"]]
        assert counts == sorted(counts, reverse=True)

    def test_is_capped_so_it_stays_a_suggestion_not_an_inventory(self, project,
                                                                 monkeypatch):
        # The cap is set here rather than left to the fixture's gap count: the
        # plot's six role fields stopped being gaps when they became computed,
        # so the fixture sits exactly on the cap and truncation stopped firing
        # for a reason unrelated to truncation.
        import tools.story_load as sl
        monkeypatch.setattr(sl, "UNFILLED_LIMIT", 3)
        r = load(project, view="unfilled")
        assert len(r["unfilled"]) <= 3
        assert r["truncated"] is True

    def test_truncation_is_honest_about_what_is_hidden(self, project, monkeypatch):
        import tools.story_load as sl
        monkeypatch.setattr(sl, "UNFILLED_LIMIT", 3)
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
        for v in ("arc", "dramatic_elements", "relationship", "values"):
            assert v in r["error"]

    def test_every_view_is_documented_in_the_schema(self, project):
        from tools.story_load import SCHEMA
        assert set(SCHEMA["properties"]["view"]["enum"]) == {
            "arc", "dramatic_elements", "relationship", "unfilled", "values"}
