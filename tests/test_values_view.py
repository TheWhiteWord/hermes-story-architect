"""The `values` view of story_load — schemas and their turns, three shapes.

Built on the save-the-children fixture, whose ground truth is known by
construction: freedom and trust both live on the main plot (the-resistance),
turn in three scenes, and the three scenes sit in one sequence. Every
assertion is arithmetic against that, not a snapshot.

The three calls the view answers (design §5):
  no args          → every value with its schema, sorted by name
  scene=<id>       → the sequence and act's major/minor, and for each plot the
                     scene serves, where each value was last left and next
  plot/sequence/act → the unit's major/minor, and each value's turns in order

Edge cases the design names are tested too: a scene serving no plot, and an
empty project — both must come back empty without error.
"""

import json
import shutil
import sqlite3
from pathlib import Path

import pytest


FIXTURE = Path(__file__).parent / "fixtures" / "save-the-children"


@pytest.fixture
def project(tmp_path):
    vault = tmp_path / "v"
    shutil.copytree(FIXTURE, vault / "projects" / "save-the-children")
    import core.config
    from tools.story_import import handler as import_handler
    import_handler({"project": "save-the-children", "confirm": True},
                   root_path=str(vault))
    return vault / "projects" / "save-the-children"


def load(project, **args):
    from tools.story_load import handler
    return json.loads(handler({"project": "save-the-children", "view": "values",
                               **args}, root_path=str(project.parent.parent)))


def _db(project):
    return sqlite3.connect(str(project / ".story" / "story.db"))


class TestNoArgs:
    """The one command to see what values exist, with their schemas."""

    def test_every_value_with_its_schema_sorted_by_name(self, project):
        out = load(project)
        names = [v["value"] for v in out["values"]]
        assert names == sorted(names) == ["freedom", "trust"]
        freedom = out["values"][0]
        assert freedom["id"] == "freedom"
        assert freedom["p"] == "free"
        assert freedom["cd"] == "imprisoned"
        assert freedom["nn"] == "gilded cage"
        assert freedom["note"]  # the fixture fills it


class TestScene:
    """Read before evaluating a scene: sequence/act major/minor, and per plot
    the scene serves, where each value was last left and turns next."""

    def test_first_scene_carries_focus_but_no_last_left(self, project):
        out = load(project, scene="central-room-day")
        assert out["scene"] == "central-room-day"
        assert out["sequence"] == "seq-discovery"
        assert out["act"] == "act-1"
        assert out["sequence_focus"]["major"]  # freedom + trust both shift here
        assert out["act_focus"]["major"]

    def test_the_scene_serves_both_plots(self, project):
        # central-room-day has a plot_roles row from each plot.
        plots = load(project, scene="central-room-day")["plots"]
        assert set(plots) == {"the-resistance", "the-scientists-last-stand"}
        # Only the-resistance carries value turns; the subplot has none.
        assert plots["the-resistance"]["values"]
        assert plots["the-scientists-last-stand"]["values"] == []

    def test_first_turn_of_a_value_has_no_last_left(self, project):
        # central-room-day is the earliest scene, so nothing precedes it.
        entry = {v["value"]: v
                 for v in load(project, scene="central-room-day")
                 ["plots"]["the-resistance"]["values"]}
        assert "last_left" not in entry["freedom"]
        assert "last_left" not in entry["trust"]

    def test_a_middle_scene_reports_last_left_and_next(self, project):
        # central-room-night sits between central-room-day and the-core-day.
        entry = {v["value"]: v
                 for v in load(project, scene="central-room-night")
                 ["plots"]["the-resistance"]["values"]}
        freedom = entry["freedom"]
        assert freedom["last_left"] == {"scene": "central-room-day", "to": "free"}
        assert freedom["next"] == {"scene": "the-core-day", "from": "free"}

    def test_last_turn_of_a_value_has_no_next(self, project):
        # the-core-day is the final scene: it was left, nothing follows.
        entry = {v["value"]: v
                 for v in load(project, scene="the-core-day")
                 ["plots"]["the-resistance"]["values"]}
        assert entry["freedom"]["last_left"]["scene"] == "central-room-night"
        assert "next" not in entry["freedom"]


class TestUnit:
    """A plot, sequence or act: its major/minor and per-value turns in order."""

    def test_plot_lists_turns_in_story_order(self, project):
        out = load(project, plot="the-resistance")
        assert out["unit"] == "plot" and out["plot"] == "the-resistance"
        freedom = {v["value"]: v for v in out["values"]}["freedom"]
        scenes = [t["scene"] for t in freedom["turns"]]
        assert scenes == ["central-room-day", "central-room-night", "the-core-day"]
        # plan §5: each turn carries scene, plot, from, to.
        assert set(freedom["turns"][0]) == {"scene", "plot", "from", "to"}
        assert freedom["turns"][0]["from"] == "imprisoned"

    def test_value_narrows_to_one(self, project):
        out = load(project, plot="the-resistance", value="trust")
        assert [v["value"] for v in out["values"]] == ["trust"]

    def test_sequence_aggregates_all_plots(self, project):
        out = load(project, sequence="seq-discovery")
        assert out["unit"] == "sequence"
        # the-resistance's two values both shift in this sequence's scenes.
        names = {v["value"] for v in out["values"]}
        assert names == {"freedom", "trust"}

    def test_act_reports_the_same_shape(self, project):
        out = load(project, act="act-1")
        assert out["unit"] == "act"
        assert out["value_focus"]["major"]
        assert {v["value"] for v in out["values"]} == {"freedom", "trust"}


class TestEdges:
    """Absent and empty cases come back empty, never an error."""

    def test_unknown_scene_is_not_found(self, project):
        out = load(project, scene="no-such-scene")
        assert "error" in out and "no-such-scene" in out["error"]

    def test_unit_with_no_turns_is_empty(self, project):
        # the subplot carries no value turns.
        out = load(project, plot="the-scientists-last-stand")
        assert out["value_focus"] == {"major": [], "minor": []}
        assert out["values"] == []

    def test_scene_with_no_plot_roles_and_no_primary_plot(self, tmp_path):
        # A scene whose sequence names no primary_plot and which has no
        # plot_roles relations serves no plot: `plots` is empty, no crash.
        from core.writes import create_project, create_entity
        root = tmp_path / "v"
        (root / "projects").mkdir(parents=True)
        assert create_project("solo", {"name": "Solo"}, root)["success"]
        proj = root / "projects" / "solo"
        create_entity(proj, "act", "act-1", {"title": "Act I"})
        create_entity(proj, "sequence", "seq-1", {"title": "Seq", "act_id": "act-1"})
        create_entity(proj, "character", "kael", {"name": "Kael"})
        create_entity(proj, "plot", "main",
                      {"name": "Main", "characters": ["kael"], "plot_scope": "main"})
        create_entity(proj, "value", "trust",
                      {"name": "trust", "p": "open", "c": "wary",
                       "cd": "deceived", "nn": "exploited"})
        create_entity(proj, "scene", "s1",
                      {"title": "S1", "sequence_id": "seq-1", "act_id": "act-1",
                       "value_turns": [{"plot": "main", "value": "trust",
                                        "from": "open", "to": "wary",
                                        "effects": [{"character": "kael",
                                                     "levels": [{"conflict_level": "inner",
                                                                 "effect": "He notices."}]}]}]})
        from tools.story_load import handler
        out = json.loads(handler(
            {"project": "solo", "view": "values", "scene": "s1"},
            root_path=str(proj.parent.parent)))
        assert out["plots"] == {}


class TestEmptyProject:
    """A project with no values at all must not crash the view."""

    @pytest.fixture
    def empty(self, tmp_path):
        from core.writes import create_project
        root = tmp_path / "v"
        (root / "projects").mkdir(parents=True)
        assert create_project("empty", {"name": "Empty"}, root)["success"]
        return root / "projects" / "empty"

    def test_no_args_on_empty_project(self, empty):
        from tools.story_load import handler
        out = json.loads(handler(
            {"project": "empty", "view": "values"},
            root_path=str(empty.parent.parent)))
        assert out["values"] == []
        assert out.get("message")

    def test_unit_on_empty_project(self, empty):
        from tools.story_load import handler
        out = json.loads(handler(
            {"project": "empty", "view": "values", "plot": "none"},
            root_path=str(empty.parent.parent)))
        assert out["value_focus"] == {"major": [], "minor": []}
        assert out["values"] == []
