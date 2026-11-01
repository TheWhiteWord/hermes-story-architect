"""Value focus: major/minor values per plot, sequence, act and story.

A value's frequency in a unit is the number of distinct scenes in which it
shifts there — a scene with two turns of the same value counts it once. Major
is the most frequent values with ties at the cut all major; minor is the
rest. Story scope follows the plot scopes: the main plot's majors are the
story's majors, the subplots' majors not already major are its minors.

Built on a small project with known counts, so every assertion is arithmetic
rather than a snapshot. The values are named words, never a/b/c — a single
letter is a column on the scene, and a turn naming one would read as that
column instead of a value.
"""
import json

import pytest

from story_architect.core.value_focus import for_act, for_plot, for_project, for_sequence
from story_architect.core.writes import create_entity, create_project
from story_architect.tools.story_retrieve import handler as retrieve_handler

WORDS = {"p": "p1", "c": "c1", "cd": "cd1", "nn": "nn1"}


@pytest.fixture
def project(tmp_path):
    """An empty project: the counts are laid in per test."""
    root = tmp_path / "v"
    (root / "projects").mkdir(parents=True)
    assert create_project("stc", {"name": "STC"}, root)["success"]
    return root / "projects" / "stc"


def _value(project, name):
    create_entity(project, "value", name, {"name": name, **WORDS})


def _turn(value, plot):
    return {"plot": plot, "value": value, "from": "p1", "to": "c1",
            "effects": [{"character": "kael",
                         "levels": [{"conflict_level": "inner",
                                     "effect": "He notices."}]}]}


def _scenes_with_turns(project, seq_id, act_id, plan):
    """Create scenes under `seq_id`, each carrying the turns in its plan.

    `plan` is a list of lists: one scene per entry, each entry the turns it
    carries.
    """
    for i, turns in enumerate(plan, 1):
        create_entity(project, "scene", f"{seq_id}-s{i}",
                      {"title": f"S{i}", "sequence_id": seq_id,
                       "act_id": act_id, "value_turns": turns})


def _cast(project):
    """One protagonist — a turn's effect must name one of the plot's."""
    create_entity(project, "character", "kael", {"name": "Kael"})


def _plot(project, scope, plot_id):
    create_entity(project, "plot", plot_id,
                  {"name": plot_id.title(), "characters": ["kael"],
                   "plot_scope": scope})


def _retrieve(project, entity_type, entity_id, fields=("value_focus",)):
    return json.loads(retrieve_handler({
        "project": str(project), "entity_type": entity_type,
        "id": [entity_id], "fields": list(fields),
    }))["entities"][0]["fields"]["value_focus"]


def _names(focus):
    return ([i["value"] for i in focus["major"]],
            [i["value"] for i in focus["minor"]])


def _structure(project, *sequences):
    _cast(project)
    create_entity(project, "act", "act-1", {"title": "Act I"})
    for seq_id in (sequences or ("seq-1",)):
        create_entity(project, "sequence", seq_id,
                      {"title": seq_id, "act_id": "act-1"})


class TestTheCount:
    """A scene counts once per value however many turns it carries."""

    def test_known_counts_major_at_the_cut(self, project):
        """trust×4, loyalty×3, justice×2, freedom×1 → major
        [trust,loyalty,justice], minor [freedom]."""
        _structure(project)
        _plot(project, "main", "main")
        for v in ("trust", "loyalty", "justice", "freedom"):
            _value(project, v)
        _scenes_with_turns(project, "seq-1", "act-1",
                           [[_turn("trust", "main")]] * 4
                           + [[_turn("loyalty", "main")]] * 3
                           + [[_turn("justice", "main")]] * 2
                           + [[_turn("freedom", "main")]] * 1)
        focus = for_plot(project, "main")
        assert _names(focus) == (["trust", "loyalty", "justice"], ["freedom"])
        assert [i["scenes"] for i in focus["major"]] == [4, 3, 2]
        assert focus["minor"][0]["scenes"] == 1

    def test_two_turns_of_a_value_in_one_scene_count_it_once(self, project):
        """The scene is the unit, not the turn."""
        _structure(project)
        _plot(project, "main", "main")
        _value(project, "trust")
        _value(project, "loyalty")
        _scenes_with_turns(project, "seq-1", "act-1",
                           [[_turn("trust", "main"), _turn("trust", "main")],
                            [_turn("loyalty", "main")]])
        focus = for_plot(project, "main")
        assert [(i["value"], i["scenes"]) for i in focus["major"]] == [
            ("loyalty", 1), ("trust", 1)]  # a tie: name breaks it


class TestTheCut:
    """Ties at the cut are all major (design §4)."""

    def test_tie_at_the_third_place_is_major(self, project):
        """trust×4, loyalty×3, justice×2, freedom×2 → major [all four],
        minor []."""
        _structure(project)
        _plot(project, "main", "main")
        for v in ("trust", "loyalty", "justice", "freedom"):
            _value(project, v)
        _scenes_with_turns(project, "seq-1", "act-1",
                           [[_turn("trust", "main")]] * 4
                           + [[_turn("loyalty", "main")]] * 3
                           + [[_turn("justice", "main")]] * 2
                           + [[_turn("freedom", "main")]] * 2)
        assert _names(for_plot(project, "main")) == (
            ["trust", "loyalty", "freedom", "justice"], [])  # justice and freedom tie at 2

    def test_fewer_values_than_the_cut_are_all_major(self, project):
        _structure(project)
        _plot(project, "main", "main")
        _value(project, "trust")
        _value(project, "loyalty")
        _scenes_with_turns(project, "seq-1", "act-1",
                           [[_turn("trust", "main")], [_turn("loyalty", "main")]])
        assert _names(for_plot(project, "main")) == (["loyalty", "trust"], [])


class TestTheScopes:
    """Each unit counts its own scenes; a plot never sees another's turns."""

    def test_sequence_counts_all_plots_together(self, project):
        """A value shifting in two plots' scenes within one sequence counts
        both scenes, with no main/sub split."""
        _structure(project)
        _plot(project, "main", "main")
        _plot(project, "sub", "sub")
        _value(project, "trust")
        _value(project, "loyalty")
        _scenes_with_turns(project, "seq-1", "act-1",
                           [[_turn("trust", "main")],
                            [_turn("trust", "sub")],
                            [_turn("loyalty", "sub")]])
        focus = for_sequence(project, "seq-1")
        assert [(i["value"], i["scenes"]) for i in focus["major"]] == [
            ("trust", 2), ("loyalty", 1)]

    def test_act_counts_all_its_sequences(self, project):
        _structure(project, "seq-1", "seq-2")
        _plot(project, "main", "main")
        _value(project, "trust")
        _scenes_with_turns(project, "seq-1", "act-1", [[_turn("trust", "main")]])
        _scenes_with_turns(project, "seq-2", "act-1", [[_turn("trust", "main")]])
        assert _names(for_act(project, "act-1")) == (["trust"], [])
        assert for_act(project, "act-1")["major"][0]["scenes"] == 2

    def test_a_plot_never_sees_another_plots_turns(self, project):
        """The defect the ranking fixed: a value shared by two plots counted
        the other plot's scenes."""
        _structure(project)
        _plot(project, "main", "main")
        _plot(project, "sub", "sub")
        _value(project, "trust")
        _scenes_with_turns(project, "seq-1", "act-1",
                           [[_turn("trust", "main")]] * 2
                           + [[_turn("trust", "sub")]] * 3)
        assert for_plot(project, "main")["major"][0]["scenes"] == 2
        assert for_plot(project, "sub")["major"][0]["scenes"] == 3


class TestTheStory:
    """Story: the main plot's majors are the story's majors; the subplots'
    major values not already major are the minors (design §4)."""

    def test_subplot_major_not_in_main_is_minor(self, project):
        _structure(project)
        _plot(project, "main", "main")
        _plot(project, "sub", "sub")
        for v in ("trust", "loyalty", "justice", "courage"):
            _value(project, v)
        # Main: trust×3, loyalty×2, justice×1 → major [trust,loyalty,justice].
        # Sub: courage×2 → major [courage].
        _scenes_with_turns(project, "seq-1", "act-1",
                           [[_turn("trust", "main")]] * 3
                           + [[_turn("loyalty", "main")]] * 2
                           + [[_turn("justice", "main")]]
                           + [[_turn("courage", "sub")]] * 2)
        focus = for_project(project)
        assert _names(focus) == (["trust", "loyalty", "justice"], ["courage"])
        assert focus["minor"][0]["scenes"] == 2

    def test_a_subplot_value_already_major_is_not_duplicated(self, project):
        _structure(project)
        _plot(project, "main", "main")
        _plot(project, "sub", "sub")
        for v in ("trust", "loyalty"):
            _value(project, v)
        # trust is major in both plots; loyalty is major in neither — in
        # main it is below the cut, in sub it ties trust for the cut.
        _scenes_with_turns(project, "seq-1", "act-1",
                           [[_turn("trust", "main")]] * 3
                           + [[_turn("loyalty", "main")]]
                           + [[_turn("trust", "sub")]] * 2
                           + [[_turn("loyalty", "sub")]] * 2)
        assert _names(for_project(project)) == (["trust", "loyalty"], [])


class TestEmpty:
    def test_no_turns_anywhere_is_empty(self, project):
        _structure(project)
        create_entity(project, "scene", "s1", {"title": "S1", "sequence_id": "seq-1",
                                                "act_id": "act-1"})
        assert for_plot(project, "nope") == {"major": [], "minor": []}
        assert for_sequence(project, "seq-1") == {"major": [], "minor": []}
        assert for_act(project, "act-1") == {"major": [], "minor": []}
        assert for_project(project) == {"major": [], "minor": []}


class TestRetrieveReadBack:
    """Plan §7: a computed field requested by name, for all four types."""

    def test_by_name_and_via_all(self, project):
        _structure(project)
        _plot(project, "main", "main")
        _value(project, "trust")
        _value(project, "loyalty")
        _scenes_with_turns(project, "seq-1", "act-1",
                           [[_turn("trust", "main")]] * 3
                           + [[_turn("loyalty", "main")]])
        assert _names(_retrieve(project, "plot", "main")) == (["trust", "loyalty"], [])
        assert _names(_retrieve(project, "sequence", "seq-1")) == (["trust", "loyalty"], [])
        assert _names(_retrieve(project, "act", "act-1")) == (["trust", "loyalty"], [])
        assert _names(_retrieve(project, "project", "stc")) == (["trust", "loyalty"], [])
        # fields=['all'] carries it too, in schema position.
        assert _names(_retrieve(project, "plot", "main", fields=("all",))) == (
            ["trust", "loyalty"], [])
