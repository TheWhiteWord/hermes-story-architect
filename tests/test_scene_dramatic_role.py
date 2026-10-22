"""A scene's `dramatic_role` no longer carries a role — the role is per plot.

`plot_roles` says what the scene does for each plot. `dramatic_role` is left
with only the two values that mean "this scene serves NO plot": transition and
non-event. Those are mutually exclusive with carrying roles, and the write
paths refuse the contradiction instead of storing it.

The stub rule is covered here too, because narrowing the field would
otherwise have collapsed every ordinary scene to a bare id: `_is_scene_stub`
used to read `not dramatic_role`, which was true of nearly every scene the
moment the roles moved to `plot_roles`.
"""
import json
import sqlite3
from pathlib import Path

import pytest

from core.constants import SCENE_DRAMATIC_ROLES
from core.db import get_dashboard_data, get_project_summary
from core.entity import validate_scene_dramatic_role
from core.writes import create_entity, create_project, edit_entity


@pytest.fixture
def vault(tmp_path):
    v = tmp_path / "projects"
    v.mkdir(parents=True)
    assert create_project("stc", {"name": "STC", "logline": "L"}, v)["success"]
    project = v / "projects" / "stc"
    create_entity(project, "plot", "the-resistance", {"name": "The Resistance"})
    # The act/sequence walk is how a scene reaches the base map at all, so the
    # fixture needs the parent chain or every scene is invisible there.
    create_entity(project, "act", "act-1", {"title": "Act One"})
    create_entity(project, "sequence", "seq-1", {"title": "Seq One",
                                                 "act_id": "act-1"})
    for i in range(1, 5):
        # status drafted, because a scene defaults to `planned` and a planned
        # scene is a stub in the base map — a real scene, not a test artefact.
        create_entity(project, "scene", f"s{i}", {"title": f"S{i}", "order": i,
                                                 "sequence_id": "seq-1",
                                                 "status": "drafted"})
    return project


def rows(project):
    conn = sqlite3.connect(str(Path(project) / ".story" / "story.db"))
    out = conn.execute(
        'SELECT from_id, to_id, kind, note FROM relations '
        "WHERE kind LIKE 'plot\\_%' ESCAPE '\\' ORDER BY to_id, kind"
    ).fetchall()
    conn.close()
    return out


class TestTheVocabulary:
    def test_the_five_plot_roles_are_gone(self):
        """A role here is the confusion this change exists to remove: the same
        word on the scene and on the plot, meaning different things."""
        for role in ("setup", "complication", "crisis", "climax", "resolution"):
            assert role not in SCENE_DRAMATIC_ROLES

    def test_what_remains(self):
        assert SCENE_DRAMATIC_ROLES == ["plot_role", "transition", "non-event"]


class TestMutualExclusion:
    def test_transition_with_roles_is_refused(self):
        with pytest.raises(ValueError, match="serves no plot"):
            validate_scene_dramatic_role("transition", [
                {"plot": "p", "role": "climax", "description": "d"}])

    def test_non_event_with_roles_is_refused(self):
        with pytest.raises(ValueError, match="serves no plot"):
            validate_scene_dramatic_role("non-event", [
                {"plot": "p", "role": "setup", "description": "d"}])

    def test_the_error_names_the_fix(self):
        """The agent hitting this holds both halves and must be told which to
        drop — not merely that the rule exists."""
        try:
            validate_scene_dramatic_role("non-event", [
                {"plot": "p", "role": "climax", "description": "d"}])
        except ValueError as exc:
            assert "clear plot_roles" in str(exc)
            assert "'plot_role'" in str(exc)
        else:
            pytest.fail("expected a refusal")

    @pytest.mark.parametrize("role", ["transition", "non-event", "", "plot_role"])
    def test_the_legal_combinations_pass(self, role):
        roles = ([{"plot": "p", "role": "climax", "description": "d"}]
                 if role in ("", "plot_role") else [])
        validate_scene_dramatic_role(role, roles)

    def test_plot_role_with_no_roles_is_allowed(self):
        """A scene may not be placed against a plot yet. Refusing here would
        make the ordinary case fail on first write."""
        validate_scene_dramatic_role("plot_role", [])


class TestWritePaths:
    def test_edit_creating_the_contradiction_is_refused(self, vault):
        """The MERGED state is what matters: `data` here names only
        dramatic_role, and the roles already sit in the DB. Validating `data`
        alone would pass this and store the contradiction."""
        edit_entity(vault, "scene", "s1", {"plot_roles": [
            {"plot": "the-resistance", "role": "climax", "description": "d"}]}, "r")
        with pytest.raises(ValueError, match="serves no plot"):
            edit_entity(vault, "scene", "s1", {"dramatic_role": "transition"}, "r")

    def test_the_contradiction_leaves_nothing_behind(self, vault):
        """A refused edit must not have half-applied: the roles stay, the
        dramatic_role is not set."""
        edit_entity(vault, "scene", "s1", {"plot_roles": [
            {"plot": "the-resistance", "role": "climax", "description": "d"}]}, "r")
        with pytest.raises(ValueError):
            edit_entity(vault, "scene", "s1", {"dramatic_role": "non-event"}, "r")
        conn = sqlite3.connect(str(Path(vault) / ".story" / "story.db"))
        extra = json.loads(conn.execute(
            "SELECT extra FROM entities WHERE id='s1'").fetchone()[0])
        conn.close()
        assert extra.get("dramatic_role", "") not in ("non-event", "transition")
        assert rows(vault) == [("the-resistance", "s1", "plot_climax", "d")]

    def test_clearing_the_roles_makes_transition_legal(self, vault):
        """The other direction: the fix is to drop one half, and that must work."""
        edit_entity(vault, "scene", "s1", {"plot_roles": [
            {"plot": "the-resistance", "role": "climax", "description": "d"}]}, "r")
        edit_entity(vault, "scene", "s1", {"plot_roles": []}, "r")
        assert edit_entity(vault, "scene", "s1",
                           {"dramatic_role": "transition"}, "r")["success"]

    def test_a_plot_less_scene_stores_no_role_row(self, vault):
        edit_entity(vault, "scene", "s2", {"dramatic_role": "non-event"}, "r")
        assert rows(vault) == []


class TestStubRule:
    """`status == planned` is the only stub test now.

    The old rule also treated "no dramatic_role" as a stub, which was correct
    when an empty role meant "not shaped yet" and is catastrophic now that an
    ordinary scene carries no dramatic_role at all: every scene would collapse
    to a bare id in the base map and vanish from the unfilled map.
    """

    def test_an_ordinary_scene_is_not_a_stub(self, vault):
        """No dramatic_role, no plot_roles, status drafted — still a full row.
        This is the regression the narrowing would have caused."""
        edit_entity(vault, "scene", "s1", {"plot_roles": [
            {"plot": "the-resistance", "role": "setup", "description": "d"}]}, "r")
        summary = get_project_summary(vault)
        scene = next(s for a in summary["acts"] for sq in a["sequences"]
                     for s in sq["scenes"] if s["id"] == "s1")
        assert scene.get("title") == "S1"
        assert "status" in scene

    def test_a_planned_scene_is_still_a_stub(self, vault):
        edit_entity(vault, "scene", "s2", {"status": "planned"}, "r")
        summary = get_project_summary(vault)
        scene = next(s for a in summary["acts"] for sq in a["sequences"]
                     for s in sq["scenes"] if s["id"] == "s2")
        assert scene == {"id": "s2"} or set(scene) <= {"id", "characters"}


class TestRoleStats:
    """The dashboard's role chart counted `dramatic_role`, which would now
    report "plot_role: 4" — the storage decision, not the shape of the story.
    It counts the `plot_<role>` relations instead."""

    def test_stats_count_plot_roles(self, vault):
        for scene, role in (("s1", "setup"), ("s2", "climax"), ("s3", "resolution")):
            edit_entity(vault, "scene", scene, {"plot_roles": [
                {"plot": "the-resistance", "role": role, "description": "d"}]}, "r")
        stats = get_dashboard_data(vault)["structural_stats"]
        assert stats["sceneRoles"]["setup"] == 1
        assert stats["sceneRoles"]["climax"] == 1
        assert stats["sceneRoles"]["resolution"] == 1

    def test_plot_role_itself_is_not_a_bar(self, vault):
        edit_entity(vault, "scene", "s1", {"dramatic_role": "plot_role",
                                          "plot_roles": [
                                              {"plot": "the-resistance",
                                               "role": "setup",
                                               "description": "d"}]}, "r")
        stats = get_dashboard_data(vault)["structural_stats"]
        assert "plot_role" not in stats["sceneRoles"]

    def test_a_plot_less_scene_is_still_counted(self, vault):
        """Otherwise the chart omits exactly the scenes a reader is looking for
        when a role looks thin."""
        edit_entity(vault, "scene", "s1", {"dramatic_role": "non-event"}, "r")
        stats = get_dashboard_data(vault)["structural_stats"]
        assert stats["sceneRoles"]["non-event"] == 1
