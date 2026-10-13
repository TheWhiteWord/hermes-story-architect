"""Value turns: the vocabulary a turn speaks has to resolve on its plot.

A turn is one shift of a value plus how it lands on each protagonist. Every
part of it is checked at write time against the plot it names — the value has
a schema there, `from`/`to` are words of that schema, each effect names a
protagonist through one level per conflict circle — and a turn that defines a
value the plot had none for registers its schema on the plot in the same
write.

The validator refuses with the plot's words in the message, because the agent
holding a refused turn needs the vocabulary, not the rule.

The validator itself (unit level) and the two write paths that call it
(create and edit, each with its own transaction) are both covered: the
registration test asserts the plot's `value_schemas` landed, and the refusal
tests assert nothing landed — scene or plot.
"""
import json
import sqlite3
from pathlib import Path

import pytest

from core.db import compute_value_lines
from core.entity import validate_scene_value_turns
from core.writes import create_entity, create_project, edit_entity

SCHEMA = {"p": "loyalty", "c": "complicity", "cd": "betrayal",
          "nn": "fanatic love"}
JUSTICE = {"p": "just", "c": "lenient", "cd": "unjust", "nn": "tyranny"}


@pytest.fixture
def project(tmp_path):
    """A project with two protagonists and one plot defining `trust`."""
    root = tmp_path / "v"
    (root / "projects").mkdir(parents=True)
    assert create_project("stc", {"name": "STC"}, root)["success"]
    proj = root / "projects" / "stc"
    for slug, name in (("kael", "Kael"), ("mira", "Mira"), ("dana", "Dana")):
        create_entity(proj, "character", slug, {"name": name})
    create_entity(proj, "plot", "main-plot", {
        "name": "Main", "characters": ["kael", "mira"],
        "value_schemas": [{"value": "trust", **SCHEMA}]})
    return proj


def _turn(**over):
    """A valid trust turn, overridden per case."""
    turn = {"plot": "main-plot", "value": "trust", "from": "loyalty",
            "to": "betrayal",
            "effects": [{"character": "kael",
                         "levels": [{"conflict_level": "personal",
                                     "effect": "Kael feels betrayed."}]}]}
    turn.update(over)
    return turn


def _refuse(project, turns):
    with pytest.raises(ValueError) as exc:
        validate_scene_value_turns(project, turns)
    return str(exc.value)


def _schemas(project):
    conn = sqlite3.connect(str(Path(project) / ".story" / "story.db"))
    row = conn.execute(
        "SELECT extra FROM entities WHERE id='main-plot'").fetchone()
    conn.close()
    extra = json.loads(row[0]) if row and row[0] else {}
    return extra.get("value_schemas") or []


def _extra(project, eid):
    conn = sqlite3.connect(str(Path(project) / ".story" / "story.db"))
    row = conn.execute(
        "SELECT extra FROM entities WHERE id=?", (eid,)).fetchone()
    conn.close()
    return json.loads(row[0]) if row and row[0] else {}


class TestTheSchema:
    def test_a_valid_turn_passes(self, project):
        validate_scene_value_turns(project, [_turn()])

    def test_from_equal_to_to_is_allowed(self, project):
        """A scene that deepens rather than turns: the shift is in how it
        lands, which `effects` already carries."""
        validate_scene_value_turns(project, [_turn(to="loyalty")])

    def test_no_schema_anywhere_is_refused_with_the_plots_values(self, project):
        msg = _refuse(project, [_turn(value="justice")])
        assert "no schema on main-plot" in msg
        assert "trust" in msg and "loyalty" in msg  # the plot's vocabulary
        assert "schema" in msg  # and the fix

    def test_an_inline_schema_for_a_registered_value_is_refused(self, project):
        msg = _refuse(project, [_turn(schema=SCHEMA)])
        assert "already has a schema" in msg
        assert "loyalty" in msg  # the existing words, not just the rule
        assert "Remove schema" in msg

    def test_a_missing_plot_is_refused_by_name(self, project):
        assert "Plot not found: no-such-plot" in _refuse(
            project, [_turn(plot="no-such-plot")])

    def test_a_from_outside_the_schema_is_refused(self, project):
        msg = _refuse(project, [_turn(**{"from": "warmth"})])
        assert "not a word of the trust schema" in msg
        assert "loyalty" in msg

    def test_a_to_outside_the_schema_is_refused(self, project):
        assert "not a word of the trust schema" in _refuse(
            project, [_turn(to="warmth")])


class TestTheInlineSchema:
    def test_an_inline_schema_defines_a_new_value(self, project):
        validate_scene_value_turns(project, [_turn(
            value="justice", **{"from": "just", "to": "unjust"},
            schema=JUSTICE)])

    def test_non_distinct_words_are_refused(self, project):
        """The four rungs are four different states; p = c is not a ladder."""
        assert "four distinct words" in _refuse(project, [_turn(
            value="honor", **{"from": "a", "to": "b"},
            schema={"p": "a", "c": "a", "cd": "c", "nn": "d"})])

    def test_several_inline_schemas_for_one_value_must_agree(self, project):
        """Two turns of the same value in one scene: the words are the
        vocabulary, so two definitions of it is a contradiction."""
        turns = [
            _turn(value="justice", **{"from": "just", "to": "unjust"},
                  schema=JUSTICE),
            _turn(value="justice", **{"from": "unjust", "to": "just"}),
        ]
        validate_scene_value_turns(project, turns)

    def test_several_inline_schemas_that_disagree_are_refused(self, project):
        turns = [
            _turn(value="justice", **{"from": "just", "to": "unjust"},
                  schema=JUSTICE),
            _turn(value="justice", **{"from": "fair", "to": "unfair"},
                  schema={"p": "fair", "c": "lenient", "cd": "unfair",
                          "nn": "tyranny"}),
        ]
        assert "differently" in _refuse(project, turns)


class TestTheEffects:
    def test_a_character_outside_the_plot_is_refused(self, project):
        assert "not a protagonist of main-plot" in _refuse(project, [_turn(
            effects=[{"character": "dana",
                      "levels": [{"conflict_level": "inner",
                                  "effect": "Dana notices."}]}])])

    def test_a_duplicated_character_is_refused(self, project):
        """One entry per protagonist: a character reached through two
        circles lists one level per circle, not two entries."""
        assert "appears twice" in _refuse(project, [_turn(effects=[
            {"character": "kael",
             "levels": [{"conflict_level": "inner", "effect": "a"}]},
            {"character": "kael",
             "levels": [{"conflict_level": "inner", "effect": "b"}]}])])

    def test_empty_effects_are_refused(self, project):
        assert "effects is required" in _refuse(project, [_turn(effects=[])])

    def test_empty_levels_are_refused(self, project):
        assert "levels is required" in _refuse(project, [_turn(
            effects=[{"character": "kael", "levels": []}])])

    def test_an_invalid_conflict_level_is_refused(self, project):
        msg = _refuse(project, [_turn(effects=[{"character": "kael", "levels": [
            {"conflict_level": "spiritual", "effect": "x"}]}])])
        assert "inner, personal, extra-personal" in msg

    def test_a_duplicated_conflict_level_is_refused(self, project):
        """One level per circle: a character cannot be reached twice
        through the same one."""
        assert "two 'inner' levels" in _refuse(project, [_turn(
            effects=[{"character": "kael", "levels": [
                {"conflict_level": "inner", "effect": "a"},
                {"conflict_level": "inner", "effect": "b"}]}])])

    def test_an_empty_effect_sentence_is_refused(self, project):
        """The sentence is the record of what the shift does at that level —
        the one part no reader can reconstruct."""
        assert "effect is required" in _refuse(project, [_turn(
            effects=[{"character": "kael", "levels": [
                {"conflict_level": "inner", "effect": "  "}]}])])


class TestRegistrationOnWrite:
    """The write paths: a turn that defines a value registers its schema on
    the plot, in the same transaction as the scene."""

    def _create_scene(self, project, turns, slug="s1"):
        return create_entity(project, "scene", slug,
                             {"title": "S1", "value_turns": turns})

    def test_a_create_registers_the_inline_schema_on_the_plot(self, project):
        self._create_scene(project, [_turn(
            value="justice", **{"from": "just", "to": "unjust"},
            schema=JUSTICE)])
        schemas = _schemas(project)
        assert schemas and schemas[-1]["value"] == "justice"
        assert schemas[-1]["nn"] == "tyranny"

    def test_a_registered_value_needs_no_schema_on_a_later_scene(
            self, project):
        """The registration is durable: the next scene just names the value."""
        self._create_scene(project, [_turn(
            value="justice", **{"from": "just", "to": "unjust"},
            schema=JUSTICE)], "s1")
        self._create_scene(project, [_turn(
            value="justice", **{"from": "unjust", "to": "just"})], "s2")
        assert len(_schemas(project)) == 2  # trust + justice, registered once

    def test_a_refused_create_registers_nothing(self, project):
        with pytest.raises(ValueError):
            self._create_scene(project, [_turn(
                value="honor", **{"from": "a", "to": "b"},
                effects=[])])
        assert len(_schemas(project)) == 1  # trust only — honor never landed
        assert not _extra(project, "s1")

    def test_an_edit_registers_the_inline_schema(self, project):
        create_entity(project, "scene", "s1", {"title": "S1"})
        edit_entity(project, "scene", "s1", {"value_turns": [_turn(
            value="courage", **{"from": "bold", "to": "afraid"},
            schema={"p": "bold", "c": "reckless", "cd": "afraid",
                    "nn": "martyr"})]}, "add courage")
        schemas = _schemas(project)
        assert schemas[-1]["value"] == "courage"

    def test_a_refused_edit_registers_nothing_and_writes_nothing(
            self, project):
        """Both halves of the transaction: the scene keeps its turns and the
        plot keeps its schemas — a refusal is all-or-nothing."""
        create_entity(project, "scene", "s1", {"title": "S1"})
        with pytest.raises(ValueError):
            edit_entity(project, "scene", "s1", {"value_turns": [_turn(
                value="mercy", **{"from": "kind", "to": "cruel"},
                effects=[{"character": "kael", "levels": []}])]}, "bad mercy")
        assert len(_schemas(project)) == 1
        assert not _extra(project, "s1").get("value_turns")

    def test_an_unrelated_edit_re_checks_the_stored_turns(self, project):
        """The merged-state rule: a later edit of the scene validates what is
        already stored, not just what this edit passes. A stored turn that
        registered its value must still pass — its schema key is consumed."""
        self._create_scene(project, [_turn(
            value="justice", **{"from": "just", "to": "unjust"},
            schema=JUSTICE)])
        edit_entity(project, "scene", "s1", {"title": "Renamed"}, "rename")
        assert self._title(project, "s1") == "Renamed"
        assert _extra(project, "s1")["value_turns"][0]["value"] == "justice"

    @staticmethod
    def _title(project, eid):
        conn = sqlite3.connect(str(Path(project) / ".story" / "story.db"))
        row = conn.execute("SELECT name FROM entities WHERE id=?",
                           (eid,)).fetchone()
        conn.close()
        return row[0] if row else None


def _project(root, *plots):
    """A project with the given plots and two protagonists (shared chars)."""
    (root / "projects").mkdir(parents=True)
    assert create_project("stc", {"name": "STC"}, root)["success"]
    proj = root / "projects" / "stc"
    create_entity(proj, "character", "kael", {"name": "Kael"})
    create_entity(proj, "character", "mira", {"name": "Mira"})
    for pid, schemas in plots:
        create_entity(proj, "plot", pid, {
            "name": pid, "characters": ["kael", "mira"],
            "value_schemas": schemas})
    return proj


def _scene(project, slug, turns, **kw):
    return create_entity(project, "scene", slug,
                         {"title": slug, "value_turns": turns, **kw})


def _scene_ids(lines, value="trust"):
    line = next(l for l in lines if l["value"] == value)
    return [t["scene_id"] for t in line["turns"]]


class TestSharedValueAcrossPlots:
    """Defect 1: a value two plots both define must not mix their turns."""

    def test_each_plot_reads_only_its_own_turns(self, tmp_path):
        project = _project(tmp_path / "v",
                           ("main-plot", [{"value": "trust", **SCHEMA}]),
                           ("sub-plot", [{"value": "trust", **SCHEMA}]))
        _scene(project, "s-main", [_turn(plot="main-plot")])
        _scene(project, "s-sub", [_turn(plot="sub-plot")])
        assert _scene_ids(compute_value_lines(project, "main-plot")) == ["s-main"]
        assert _scene_ids(compute_value_lines(project, "sub-plot")) == ["s-sub"]


class TestTurnsReadAcrossActs:
    """Defect 2: sequence order keys restart in each act, so the act leads."""

    def _in_two_acts(self, tmp_path):
        """Act 2's sequence gets a lower order_key than act 1's scene."""
        project = _project(tmp_path / "v",
                           ("main-plot", [{"value": "trust", **SCHEMA}]))
        create_entity(project, "act", "act-1", {"title": "A1", "order": 1})
        create_entity(project, "act", "act-2", {"title": "A2", "order": 2})
        create_entity(project, "sequence", "seq-1", {"title": "S1", "order": 5,
                                                     "act_id": "act-1"})
        create_entity(project, "sequence", "seq-2", {"title": "S2", "order": 1,
                                                     "act_id": "act-2"})
        # The act-1 scene happens later inside its sequence than the act-2
        # scene does, so scene order alone would put it second — the act must
        # lead the key, or act 2 reads before act 1.
        _scene(project, "s-early", [_turn()], order=1,
               sequence_id="seq-2", act_id="act-2")
        _scene(project, "s-late", [_turn()], order=2,
               sequence_id="seq-1", act_id="act-1")
        return project

    def test_act_one_scene_reads_before_act_two(self, tmp_path):
        project = self._in_two_acts(tmp_path)
        assert _scene_ids(compute_value_lines(project, "main-plot")) == [
            "s-late", "s-early"]

    def test_turns_carry_their_placement(self, tmp_path):
        from core.db import get_scene_value_turns
        project = self._in_two_acts(tmp_path)
        rows = get_scene_value_turns(project)
        by_scene = {r["scene_id"]: r for r in rows}
        assert set(by_scene) == {"s-late", "s-early"}
        for scene_id, act, seq in (("s-late", "act-1", "seq-1"),
                                   ("s-early", "act-2", "seq-2")):
            row = by_scene[scene_id]
            assert row["plot"] == "main-plot"
            assert row["act_id"] == act
            assert row["sequence_id"] == seq
            assert row["order"] == (
                {"s-late": (1, 5, 2), "s-early": (2, 1, 1)}[scene_id]
                + (scene_id,))
            assert row["value"] == "trust"

    def test_two_plots_are_distinguishable_in_the_helper(self, tmp_path):
        from core.db import get_scene_value_turns
        project = _project(tmp_path / "v",
                           ("main-plot", [{"value": "trust", **SCHEMA}]),
                           ("sub-plot", [{"value": "trust", **SCHEMA}]))
        _scene(project, "s-main", [_turn(plot="main-plot")])
        _scene(project, "s-sub", [_turn(plot="sub-plot")])
        rows = get_scene_value_turns(project)
        assert {r["plot"] for r in rows} == {"main-plot", "sub-plot"}


class TestTheReadBack:
    """`plot.value_lines`: the turns of one plot, read back in story order.

    Registration in Phase 3 guarantees every turn's value has a schema on its
    plot, so the line can render `from`/`to` and the vocabulary with no
    lookup of its own. What it adds is ORDER — the scene's position in the
    story, which is the whole reason to read the line back rather than the
    turns one scene at a time.
    """

    def _scenes(self, project, *titles):
        for title, turns in titles:
            create_entity(project, "scene", title,
                          {"title": title, "value_turns": turns})

    def test_the_line_carries_the_schema_and_the_turns(self, project):
        self._scenes(project, ("s1", [_turn()]))
        lines = compute_value_lines(project, "main-plot")
        assert len(lines) == 1
        line = lines[0]
        assert line["value"] == "trust"
        assert line["schema"]["nn"] == "fanatic love"
        assert line["turns"] == [{
            "scene_id": "s1", "from": "loyalty", "to": "betrayal",
            "effects": [{"character": "kael", "levels": [
                {"conflict_level": "personal",
                 "effect": "Kael feels betrayed."}]}]}]

    def test_turns_read_in_story_order_not_write_order(self, project):
        """A scene written later still reads where it happens."""
        # Written in reverse: the scene that happens FIRST is created LAST.
        self._scenes(project, ("s3", [_turn(**{"from": "complicity",
                                               "to": "betrayal"})]),
                     ("s2", [_turn(**{"from": "loyalty",
                                      "to": "complicity"})]))
        lines = compute_value_lines(project, "main-plot")
        assert [t["scene_id"] for t in lines[0]["turns"]] == ["s2", "s3"]

    def test_a_value_with_no_turns_yet_is_not_a_line(self, project):
        """The read-back lists what exists: a registered value with no scene
        turn has no line, not an empty one."""
        create_entity(project, "scene", "s1", {"title": "S1"})
        assert compute_value_lines(project, "main-plot") == []

    def test_retrieve_returns_the_computed_field(self, project):
        """The exposure contract: `value_lines` is computed, not stored, so a
        retrieve asking for it must still answer."""
        from tools.story_retrieve import handler as retrieve_handler
        self._scenes(project, ("s1", [_turn()]))
        out = json.loads(retrieve_handler({
            "project": str(project), "entity_type": "plot", "id": ["main-plot"],
            "fields": ["value_lines"]}, root_path=str(project.parent.parent)))
        line = out["entities"][0]["fields"]["value_lines"]
        assert line[0]["value"] == "trust"
        assert line[0]["turns"][0]["scene_id"] == "s1"

    def test_retrieve_returns_the_stored_field(self, project):
        from tools.story_retrieve import handler as retrieve_handler
        out = json.loads(retrieve_handler({
            "project": str(project), "entity_type": "plot", "id": ["main-plot"],
            "fields": ["value_schemas"]}, root_path=str(project.parent.parent)))
        assert out["entities"][0]["fields"]["value_schemas"][0]["p"] == "loyalty"

    def test_a_value_the_plot_no_longer_defines_is_dropped(self, project):
        """A plot edited to remove a value leaves the scene's turn behind, and
        the line reads the plot's vocabulary — an orphan turn is not a line."""
        self._scenes(project, ("s1", [_turn()]))
        edit_entity(project, "plot", "main-plot",
                    {"value_schemas": []}, "drop the value")
        assert compute_value_lines(project, "main-plot") == []
