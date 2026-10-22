"""Value turns: the value a turn names must be a defined value entity.

A turn is one shift of a value plus how it lands on each protagonist. Every
part of it is checked at write time: the plot exists, the value names an
existing `value` entity, `from`/`to` are words of that value's four rungs,
and each effect names a protagonist through one level per conflict circle.
A value has one schema wherever it is used, so nothing is defined on the
scene — a turn names a value, and the words are that entity's.

The validator refuses with the value's words in the message, because the
agent holding a refused turn needs the vocabulary, not the rule.

The validator (unit level) and the two write paths that call it (create and
edit, each with its own transaction) are both covered, including a draft
that creates a value and edits a scene naming it in one batch.
"""
import json
import sqlite3
from pathlib import Path

import pytest

from core import drafts
from core.entity import validate_scene_value_turns
from core.writes import create_entity, create_project, edit_entity

SCHEMA = {"p": "loyalty", "c": "complicity", "cd": "betrayal",
          "nn": "fanatic love"}
JUSTICE = {"p": "just", "c": "lenient", "cd": "unjust", "nn": "tyranny"}


@pytest.fixture
def project(tmp_path):
    """A project with two protagonists, one plot, one value entity (trust)."""
    root = tmp_path / "v"
    (root / "projects").mkdir(parents=True)
    assert create_project("stc", {"name": "STC"}, root)["success"]
    proj = root / "projects" / "stc"
    for slug, name in (("kael", "Kael"), ("mira", "Mira"), ("dana", "Dana")):
        create_entity(proj, "character", slug, {"name": name})
    create_entity(proj, "plot", "main-plot", {
        "name": "Main", "characters": ["kael", "mira"]})
    _value(proj, "trust", **SCHEMA)
    return proj


def _value(project, slug, **words):
    """A value entity: id is the slug of its name, four rung words in extra."""
    fm = {"name": slug.replace("-", " ").title(), **words}
    return create_entity(project, "value", slug, fm)


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


def _extra(project, eid):
    conn = sqlite3.connect(str(Path(project) / ".story" / "story.db"))
    row = conn.execute(
        "SELECT extra FROM entities WHERE id=?", (eid,)).fetchone()
    conn.close()
    return json.loads(row[0]) if row and row[0] else {}


class TestTheValueEntity:
    """The value a turn names must be a defined value entity."""

    def test_a_turn_naming_a_defined_value_passes(self, project):
        validate_scene_value_turns(project, [_turn()])

    def test_from_equal_to_to_is_allowed(self, project):
        """A scene that deepens rather than turns: the shift is in how it
        lands, which `effects` already carries."""
        validate_scene_value_turns(project, [_turn(to="loyalty")])

    def test_an_unknown_value_is_refused_with_the_defined_values(self, project):
        msg = _refuse(project, [_turn(value="justice")])
        assert "justice is not a defined value" in msg
        assert "trust" in msg and "loyalty" in msg  # the defined vocabulary
        assert "Create the value first" in msg  # and the fix

    def test_the_name_matches_case_insensitively_and_trimmed(self, project):
        validate_scene_value_turns(project, [_turn(value="  Trust  ")])

    def test_a_value_defined_in_the_same_draft_commits(self, project):
        """The plan §7 verification item: a value create followed by a scene
        edit naming it commits, since a draft applies creates before edits."""
        create_entity(project, "scene", "s1", {"title": "S1"})
        staged = drafts.stage(project, [
            {"op": "create", "type": "value", "id": "justice",
             "frontmatter": {"name": "Justice", **JUSTICE},
             "summary": "New value: Justice"},
            {"op": "edit", "entity_type": "scene", "entity_id": "s1",
             "data": {"value_turns": [_turn(
                 value="justice", **{"from": "just", "to": "unjust"})]},
             "summary": "Justice shifts"},
        ], "define justice and record its first shift")
        result = drafts.commit(project, staged["draft_id"])
        assert result["success"] is True
        turns = _extra(project, "s1")["value_turns"]
        assert turns[0]["value"] == "justice"

    def test_a_refused_create_of_a_scene_naming_an_unknown_value_writes_nothing(
            self, project):
        """The refusal lands before BEGIN, so neither the scene nor anything
        else is written."""
        with pytest.raises(ValueError):
            create_entity(project, "scene", "s1", {"title": "S1",
                                                   "value_turns": [_turn(
                                                       value="justice")]})
        assert not _extra(project, "s1")

    def test_an_unrelated_edit_re_checks_the_stored_turns(self, project):
        """The merged-state rule: a later edit of the scene validates what is
        already stored, not just what this edit passes."""
        create_entity(project, "scene", "s1", {"title": "S1",
                                               "value_turns": [_turn()]})
        edit_entity(project, "scene", "s1", {"title": "Renamed"}, "rename")
        assert _extra(project, "s1")["value_turns"][0]["value"] == "trust"

    def test_an_edit_to_an_orphaned_turn_is_refused(self, project):
        """A value deleted from the project orphans every turn naming it, and
        the next edit of such a scene is refused — the value no longer
        exists, so the turn cannot resolve."""
        create_entity(project, "scene", "s1", {"title": "S1",
                                               "value_turns": [_turn()]})
        # Simulate the orphan: strip the value entity, keep the turn.
        conn = sqlite3.connect(str(Path(project) / ".story" / "story.db"))
        conn.execute("UPDATE entities SET is_deleted=1 WHERE id='trust'")
        conn.commit()
        conn.close()
        with pytest.raises(ValueError):
            edit_entity(project, "scene", "s1", {"title": "Renamed"}, "rename")


class TestTheWords:
    """`from`/`to` must be words of the resolved value's four rungs."""

    def test_a_from_outside_the_value_is_refused(self, project):
        msg = _refuse(project, [_turn(**{"from": "warmth"})])
        assert "not a word of the trust schema" in msg
        assert "loyalty" in msg

    def test_a_to_outside_the_value_is_refused(self, project):
        assert "not a word of the trust schema" in _refuse(
            project, [_turn(to="warmth")])

    def test_a_missing_plot_is_refused_by_name(self, project):
        assert "Plot not found: no-such-plot" in _refuse(
            project, [_turn(plot="no-such-plot")])


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
