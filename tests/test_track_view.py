"""Track view: one entity's journey across the scenes that record it.

Built on a small project with known facts, so every assertion is a fact laid
in by the test rather than a snapshot. The fixture's `scene_beats` records
carry no prose, so the interesting cases are written here — the reader's job
is to order and group, and this pins what it orders.

A character's row is driven by the scene's cast, its record and its turns; a
location, world or relationship reduces to the scenes whose state changed.
"""
import json

from story_architect.core.writes import create_entity, create_project
from story_architect.tools.story_load import handler as load_handler

WORDS = {"p": "p1", "c": "c1", "cd": "cd1", "nn": "nn1"}


def _project(tmp_path):
    root = tmp_path / "v"
    (root / "projects").mkdir(parents=True)
    assert create_project("stc", {"name": "STC"}, root)["success"]
    return root / "projects" / "stc"


def _track(project, entity, **args):
    return json.loads(load_handler(
        {"project": str(project), "view": "track", "entity": entity, **args},
        root_path=str(project.parent.parent)))


def _plot(project, plot_id, chars):
    create_entity(project, "plot", plot_id,
                  {"name": plot_id.title(), "characters": chars})


def _value(project, name):
    create_entity(project, "value", name, {"name": name, **WORDS})


def _scene(project, slug, seq, act, **fields):
    create_entity(project, "scene", slug,
                  {"title": slug.title(), "sequence_id": seq, "act_id": act,
                   **fields})


def _turn(plot, value, from_, to, character, effect):
    return {"plot": plot, "value": value, "from": from_, "to": to,
            "effects": [{"character": character,
                         "levels": [{"conflict_level": "inner",
                                     "effect": effect}]}]}


def _story(project):
    """One plot, one protagonist, one value, two acts of one sequence each.

    The character comes first: `plot.characters` is a `ref: character`, so a
    plot naming a character that does not exist yet is refused on write.
    """
    create_entity(project, "character", "kael", {"name": "Kael"})
    _plot(project, "main-plot", ["kael"])
    _value(project, "trust")
    create_entity(project, "act", "act-1", {"title": "Act One"})
    create_entity(project, "act", "act-2", {"title": "Act Two"})
    create_entity(project, "sequence", "seq-a",
                  {"title": "Seq A", "act_id": "act-1"})
    create_entity(project, "sequence", "seq-b",
                  {"title": "Seq B", "act_id": "act-2"})


class TestCharacterTrack:
    def test_coverage_counts_appearances_records_and_changes(self, tmp_path):
        p = _project(tmp_path)
        _story(p)
        _scene(p, "s1", "seq-a", "act-1", characters=["kael"])
        _scene(p, "s2", "seq-a", "act-1", characters=["kael"],
               value_turns=[_turn("main-plot", "trust", "p1", "c1",
                                  "kael", "He doubts.")])
        _scene(p, "s3", "seq-b", "act-2", characters=["kael"])
        create_entity(p, "scene_beats", "s2-beats",
                      {"scene": "s2",
                       "changes": [{"entity": "kael", "change": "now wary"}]})
        create_entity(p, "scene_beats", "s3-beats", {"scene": "s3"})
        out = _track(p, "kael")
        assert out["coverage"] == {"appears": 3, "with_scene_beats": 2,
                                   "with_change": 1}

    def test_an_appearance_with_nothing_recorded_is_counted_not_listed(self, tmp_path):
        """The whole point of `coverage`: a silent appearance is a gap the
        reader is told about, not a row it has to infer."""
        p = _project(tmp_path)
        _story(p)
        _scene(p, "s1", "seq-a", "act-1", characters=["kael"])
        _scene(p, "s2", "seq-a", "act-1", characters=["kael"])
        out = _track(p, "kael")
        assert out["coverage"]["appears"] == 2
        assert [r["scene"] for a in out["acts"] for q in a["sequences"]
                for r in q["scenes"]] == []

    def test_rows_are_grouped_by_act_then_sequence(self, tmp_path):
        p = _project(tmp_path)
        _story(p)
        for slug, seq, act in (("s1", "seq-a", "act-1"), ("s2", "seq-a", "act-1"),
                               ("s3", "seq-b", "act-2")):
            _scene(p, slug, seq, act, characters=["kael"])
            create_entity(p, "scene_beats", f"{slug}-beats",
                          {"scene": slug,
                           "changes": [{"entity": "kael", "change": f"{slug} changed"}]})
        out = _track(p, "kael")
        assert [a["act"] for a in out["acts"]] == ["act-1", "act-2"]
        assert [q["sequence"] for q in out["acts"][0]["sequences"]] == ["seq-a"]
        assert [r["scene"] for q in out["acts"][0]["sequences"]
                for r in q["scenes"]] == ["s1", "s2"]

    def test_a_change_joins_every_entry_into_one_sentence(self, tmp_path):
        p = _project(tmp_path)
        _story(p)
        _scene(p, "s1", "seq-a", "act-1", characters=["kael"])
        create_entity(p, "scene_beats", "s1-beats", {
            "scene": "s1",
            "changes": [{"entity": "kael", "change": "now wary"},
                        {"entity": "kael", "change": "and unwilling to ask"}]})
        row = _track(p, "kael")["acts"][0]["sequences"][0]["scenes"][0]
        assert row["change"] == "now wary; and unwilling to ask"

    def test_driver_and_objective_come_from_the_record(self, tmp_path):
        p = _project(tmp_path)
        _story(p)
        _scene(p, "s1", "seq-a", "act-1", characters=["kael"])
        create_entity(p, "scene_beats", "s1-beats", {
            "scene": "s1", "driver": "kael",
            "scene_objective": "to get the door open without being seen",
            "changes": [{"entity": "kael", "change": "now suspects"}]})
        row = _track(p, "kael")["acts"][0]["sequences"][0]["scenes"][0]
        assert row["driver"] is True
        assert row["scene_objective"] == "to get the door open without being seen"

    def test_a_driver_outside_the_cast_does_not_drive(self, tmp_path):
        """The write path allows a driver who is not in the scene; the row
        must not claim a presence the scene does not have."""
        p = _project(tmp_path)
        _story(p)
        _scene(p, "s1", "seq-a", "act-1", characters=[])
        create_entity(p, "scene_beats", "s1-beats", {
            "scene": "s1", "driver": "kael",
            "changes": [{"entity": "kael", "change": "now suspects"}]})
        row = _track(p, "kael")["acts"][0]["sequences"][0]["scenes"][0]
        assert "driver" not in row

    def test_an_objective_is_omitted_when_unfilled(self, tmp_path):
        p = _project(tmp_path)
        _story(p)
        _scene(p, "s1", "seq-a", "act-1", characters=["kael"])
        create_entity(p, "scene_beats", "s1-beats", {
            "scene": "s1", "driver": "kael",
            "changes": [{"entity": "kael", "change": "now suspects"}]})
        row = _track(p, "kael")["acts"][0]["sequences"][0]["scenes"][0]
        assert row["driver"] is True
        assert "scene_objective" not in row

    def test_true_character_reports_the_two_prose_fields(self, tmp_path):
        p = _project(tmp_path)
        _story(p)
        _scene(p, "s1", "seq-a", "act-1", characters=["kael"])
        create_entity(p, "scene_beats", "s1-beats", {
            "scene": "s1", "driver": "kael",
            "true_character": [{"character": "kael",
                                "dilemma": "Trust vs. safety",
                                "choice_reveals": "She chooses trust"}],
            "changes": [{"entity": "kael", "change": "now willing to refuse"}]})
        row = _track(p, "kael")["acts"][0]["sequences"][0]["scenes"][0]
        assert row["true_character"] == {"dilemma": "Trust vs. safety",
                                         "choice_reveals": "She chooses trust"}

    def test_effects_are_value_then_level_then_sentence(self, tmp_path):
        """The keys are the value and level names, so `conflict_level` and
        `effect` are not repeated on every entry."""
        p = _project(tmp_path)
        _story(p)
        _scene(p, "s1", "seq-a", "act-1", characters=["kael"],
               value_turns=[_turn("main-plot", "trust", "p1", "c1",
                                  "kael", "He doubts the story.")])
        out = _track(p, "kael")
        row = out["acts"][0]["sequences"][0]["scenes"][0]
        assert row["effects"] == {"trust": {"inner": "He doubts the story."}}
        assert "conflict_level" not in json.dumps(row)

    def test_a_second_plot_turning_the_same_value_is_keyed_by_plot(self, tmp_path):
        """One value can turn under two plots in one scene; the two are
        distinct evidence, so neither is dropped."""
        p = _project(tmp_path)
        _story(p)
        _plot(p, "sub-plot", ["kael"])
        _scene(p, "s1", "seq-a", "act-1", characters=["kael"], value_turns=[
            _turn("main-plot", "trust", "p1", "c1", "kael", "Main turn."),
            _turn("sub-plot", "trust", "c1", "cd1", "kael", "Sub turn."),
        ])
        effects = _track(p, "kael")["acts"][0]["sequences"][0]["scenes"][0]["effects"]
        assert effects == {"trust": {"inner": "Main turn."},
                           "trust (sub-plot)": {"inner": "Sub turn."}}

    def test_the_header_values_give_the_path_of_a_protagonist(self, tmp_path):
        """`deepest` is the deepest rung visited, which is what makes a P
        earned rather than naive."""
        p = _project(tmp_path)
        _story(p)
        _scene(p, "s1", "seq-a", "act-1", characters=["kael"],
               value_turns=[_turn("main-plot", "trust", "p1", "cd1",
                                  "kael", "First.")])
        _scene(p, "s2", "seq-b", "act-2", characters=["kael"],
               value_turns=[_turn("main-plot", "trust", "cd1", "nn1",
                                  "kael", "Deepest.")])
        out = _track(p, "kael")
        assert out["values"] == [{"value": "trust", "from": "p1",
                                  "deepest": "nn1", "to": "nn1"}]

    def test_the_header_lists_the_plots_the_character_is_protagonist_of(self, tmp_path):
        p = _project(tmp_path)
        _story(p)
        _plot(p, "sub-plot", ["kael"])
        _scene(p, "s1", "seq-a", "act-1", characters=["kael"],
               value_turns=[_turn("main-plot", "trust", "p1", "c1",
                                  "kael", "He doubts.")])
        out = _track(p, "kael")
        assert out["plots"] == ["main-plot", "sub-plot"]


class TestScopeAndErrors:
    def test_the_scope_is_story_by_default(self, tmp_path):
        p = _project(tmp_path)
        _story(p)
        assert _track(p, "kael")["scope"] == "story"

    def test_act_narrows_the_tree_and_reports_the_scope(self, tmp_path):
        p = _project(tmp_path)
        _story(p)
        for slug, seq, act in (("s1", "seq-a", "act-1"), ("s2", "seq-b", "act-2")):
            _scene(p, slug, seq, act, characters=["kael"])
            create_entity(p, "scene_beats", f"{slug}-beats",
                          {"scene": slug,
                           "changes": [{"entity": "kael", "change": f"{slug} changed"}]})
        out = _track(p, "kael", act="act-2")
        assert out["scope"] == {"act": "act-2", "sequence": None}
        assert [a["act"] for a in out["acts"]] == ["act-2"]
        assert out["coverage"]["appears"] == 1

    def test_sequence_narrows_to_one_sequence(self, tmp_path):
        p = _project(tmp_path)
        _story(p)
        _scene(p, "s1", "seq-a", "act-1", characters=["kael"],
               value_turns=[_turn("main-plot", "trust", "p1", "c1",
                                  "kael", "He doubts.")])
        _scene(p, "s2", "seq-b", "act-2", characters=["kael"],
               value_turns=[_turn("main-plot", "trust", "c1", "cd1",
                                  "kael", "He doubts more.")])
        out = _track(p, "kael", sequence="seq-a")
        assert out["scope"] == {"act": None, "sequence": "seq-a"}
        assert [r["scene"] for a in out["acts"] for q in a["sequences"]
                for r in q["scenes"]] == ["s1"]
        # The scope narrows the header too: s1 alone visits p1 and c1, so the
        # deepest rung in the scope is c1, not the cd1 s2 reaches.
        assert out["values"] == [{"value": "trust", "from": "p1",
                                  "deepest": "c1", "to": "c1"}]

    def test_value_narrows_the_effects_and_the_header(self, tmp_path):
        p = _project(tmp_path)
        _story(p)
        _value(p, "freedom")
        _scene(p, "s1", "seq-a", "act-1", characters=["kael"], value_turns=[
            _turn("main-plot", "trust", "p1", "c1", "kael", "He doubts."),
            _turn("main-plot", "freedom", "p1", "c1", "kael", "He is free."),
        ])
        out = _track(p, "kael", value="freedom")
        assert out["value"] == "freedom"
        row = out["acts"][0]["sequences"][0]["scenes"][0]
        assert list(row["effects"]) == ["freedom"]
        assert [v["value"] for v in out["values"]] == ["freedom"]

    def test_an_unknown_entity_is_an_error_not_an_empty_track(self, tmp_path):
        p = _project(tmp_path)
        _story(p)
        out = _track(p, "ghost")
        assert "error" in out
        assert "ghost" in out["error"]

    def test_track_without_an_entity_is_an_error(self, tmp_path):
        p = _project(tmp_path)
        out = json.loads(load_handler(
            {"project": str(p), "view": "track"},
            root_path=str(p.parent.parent)))
        assert "error" in out
        assert "entity" in out["error"]


class TestNonCharacterTrack:
    def test_a_location_reduces_to_scene_and_change(self, tmp_path):
        p = _project(tmp_path)
        _story(p)
        create_entity(p, "location", "the-core", {"name": "The Core"})
        _scene(p, "s1", "seq-a", "act-1", location="the-core",
               characters=["kael"])
        _scene(p, "s2", "seq-b", "act-2", location="the-core",
               characters=["kael"])
        create_entity(p, "scene_beats", "s2-beats", {
            "scene": "s2",
            "changes": [{"entity": "the-core",
                         "change": "now flooded to the second level"}]})
        out = _track(p, "the-core")
        assert out["coverage"] == {"appears": 2, "with_scene_beats": 1,
                                   "with_change": 1}
        rows = [r for a in out["acts"] for q in a["sequences"]
                for r in q["scenes"]]
        assert rows == [{"scene": "s2",
                         "change": "now flooded to the second level"}]

    def test_a_relationship_is_tracked_by_its_changes(self, tmp_path):
        p = _project(tmp_path)
        _story(p)
        create_entity(p, "relationship", "kael-mira",
                      {"name": "Kael & Mira", "type": "relationship",
                       "characters": ["kael", "mira"]})
        create_entity(p, "character", "mira", {"name": "Mira"})
        _scene(p, "s1", "seq-a", "act-1", characters=["kael", "mira"])
        create_entity(p, "scene_beats", "s1-beats", {
            "scene": "s1",
            "changes": [{"entity": "kael-mira",
                         "change": "now open to each other"}]})
        out = _track(p, "kael-mira")
        assert out["coverage"] == {"appears": 1, "with_scene_beats": 1,
                                   "with_change": 1}
        row = out["acts"][0]["sequences"][0]["scenes"][0]
        assert row == {"scene": "s1",
                       "change": "now open to each other"}

    def test_a_non_character_carries_no_plots_or_values(self, tmp_path):
        """`plots` and `values` are protagonist facts; a location has neither,
        so they are absent rather than empty."""
        p = _project(tmp_path)
        _story(p)
        create_entity(p, "location", "the-core", {"name": "The Core"})
        _scene(p, "s1", "seq-a", "act-1", location="the-core", characters=["kael"])
        create_entity(p, "scene_beats", "s1-beats", {
            "scene": "s1",
            "changes": [{"entity": "the-core", "change": "now flooded"}]})
        out = _track(p, "the-core")
        assert "plots" not in out
        assert "values" not in out
