"""A plot role is written on the SCENE, and read back on the plot.

The whole point of the phase: the agent records which plot a scene runs
through where it is already writing the scene, so a plot is never reopened to
add a scene to it. The plot's five role fields became `computed` — the same
rows, seen from the other side.

Two of these tests fail without the fix and are marked as such below: the
export round-trip (silent loss — the markdown loses every role and re-import
has nothing to complain about) and the delete sweep (a dead plot's rows
outlive the plot they name).

One correction to the plan, measured while implementing: the sweep was
specified to stop a deleted plot's rows *reattaching* when a plot is recreated
with the same slug. That is not reachable — `delete_entity` soft-deletes, so
the slug stays taken and `create_entity` refuses it ("Entity already exists").
The rows are still unreachable while the plot is dead (every reader filters on
`to_id`, and db.py filters `from_id` on `is_deleted`), so the sweep is right —
but its real cost lands on `restore`, not on reattachment. That cost is pinned
in `test_restore_brings_the_plot_back_without_its_roles`.
"""
import json
import shutil
import sqlite3
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from core.constants import PLOT_ROLES  # noqa: E402
from core.writes import create_entity, create_project, delete_entity, edit_entity  # noqa: E402


@pytest.fixture
def vault(tmp_path):
    """A project with two plots and three scenes, no roles written yet."""
    v = tmp_path / "v"
    (v / "projects").mkdir(parents=True)
    assert create_project("stc", {"name": "STC", "logline": "L"}, v)["success"] is True
    project = v / "projects" / "stc"
    for slug, name in (("the-resistance", "The Resistance"),
                       ("the-betrayal", "The Betrayal")):
        create_entity(project, "plot", slug, {"name": name, "one_sentence": "x"})
    for i in range(1, 4):
        create_entity(project, "scene", f"s{i}", {"title": f"S{i}", "order": i})
    return project


def rows(project, kind=None):
    conn = sqlite3.connect(str(Path(project) / ".story" / "story.db"))
    sql = "SELECT from_id, to_id, kind, note, \"order\" FROM relations"
    if kind:
        sql += f" WHERE kind='{kind}'"
    out = conn.execute(sql + " ORDER BY \"order\"").fetchall()
    conn.close()
    return out


def write_roles(project, scene, entries):
    return edit_entity(project, "scene", scene, {"plot_roles": entries}, "roles")


class TestWriting:
    def test_create_writes_one_row_per_entry(self, vault):
        """`from_id` is the PLOT and `to_id` the scene: the direction every
        existing reader keys off, unchanged. Only the writer moved."""
        create_entity(vault, "scene", "s4", {
            "title": "S4", "order": 4,
            "plot_roles": [{"plot": "the-resistance", "role": "setup",
                            "description": "the door was never locked"}]})
        assert ("the-resistance", "s4", "plot_setup",
                "the door was never locked", 1) in rows(vault, "plot_setup")

    def test_edit_writes_one_row_per_entry(self, vault):
        write_roles(vault, "s1", [{"plot": "the-resistance", "role": "crisis",
                                   "description": "d"}])
        assert ("the-resistance", "s1", "plot_crisis", "d", 1) in rows(vault, "plot_crisis")

    def test_every_role_reaches_its_own_kind(self, vault):
        """All five, not the two the old dict→row unwrap happened to handle."""
        for i, role in enumerate(PLOT_ROLES, 4):
            create_entity(vault, "scene", f"s{i}", {"title": f"S{i}", "order": i})
            write_roles(vault, f"s{i}",
                        [{"plot": "the-resistance", "role": role,
                          "description": role}])
        assert sorted(r[2] for r in rows(vault) if r[2].startswith("plot_")) == \
            sorted(f"plot_{r}" for r in PLOT_ROLES)

    def test_one_scene_two_plots_different_roles(self, vault):
        """The shape that is the reason `plot_roles` is a list of entries
        naming their own plot: a scene can be a climax for one plot and a
        complication for another."""
        write_roles(vault, "s1", [
            {"plot": "the-resistance", "role": "climax", "description": "a"},
            {"plot": "the-betrayal", "role": "complication", "description": "b"},
        ])
        got = {(r[0], r[2]) for r in rows(vault) if r[2].startswith("plot_")}
        assert got == {("the-resistance", "plot_climax"),
                       ("the-betrayal", "plot_complication")}

    def test_editing_replaces_the_rows_wholesale(self, vault):
        """Delete-then-reinsert, not merge: a removed entry leaves no row."""
        write_roles(vault, "s1", [
            {"plot": "the-resistance", "role": "setup", "description": "keep"},
            {"plot": "the-betrayal", "role": "climax", "description": "drop"},
        ])
        write_roles(vault, "s1", [{"plot": "the-resistance", "role": "setup",
                                   "description": "keep"}])
        got = rows(vault)
        assert [r for r in got if r[1] == "s1"] == [
            ("the-resistance", "s1", "plot_setup", "keep", 1)]

    def test_clearing_plot_roles_removes_every_row(self, vault):
        write_roles(vault, "s1", [{"plot": "the-resistance", "role": "setup",
                                   "description": "d"}])
        write_roles(vault, "s1", [])
        assert [r for r in rows(vault) if r[2].startswith("plot_")] == []


class TestThePlotSideIsReadOnly:
    def test_a_plot_edit_cannot_write_a_role(self, vault):
        """The field is computed, so the edit is reported and dropped — not
        written. Before this, the same call wrote a row."""
        res = edit_entity(vault, "plot", "the-resistance",
                          {"setups": [{"scene_id": "s1", "description": "d"}]},
                          "set up")
        assert "setups" in res["skipped_read_only"]
        assert [r for r in rows(vault) if r[2].startswith("plot_")] == []

    def test_a_plot_create_cannot_write_a_role(self, vault):
        create_entity(vault, "plot", "the-betrayal-2",
                      {"name": "B2", "one_sentence": "x",
                       "crisis": [{"scene_id": "s1", "description": "d"}]})
        assert [r for r in rows(vault) if r[2].startswith("plot_")] == []

    def test_the_plot_reads_back_what_the_scene_wrote(self, vault):
        """Same rows, other direction — so nothing downstream had to change."""
        write_roles(vault, "s1", [{"plot": "the-resistance", "role": "setup",
                                   "description": "the door"}])
        from core.db import get_dashboard_data
        plot = next(p for p in get_dashboard_data(vault)["story_data"]["plots"]
                    if p["id"] == "the-resistance")
        assert plot["setups"] == [{"scene_id": "s1", "description": "the door"}]


class TestValidation:
    def test_a_missing_plot_is_refused_by_name(self, vault):
        with pytest.raises(ValueError, match="Plot not found: no-such-plot"):
            write_roles(vault, "s1", [{"plot": "no-such-plot", "role": "setup",
                                       "description": "d"}])

    def test_a_missing_plot_on_create_is_refused(self, vault):
        with pytest.raises(ValueError, match="Plot not found: no-such-plot"):
            create_entity(vault, "scene", "s9", {
                "title": "S9", "order": 9,
                "plot_roles": [{"plot": "no-such-plot", "role": "setup",
                                "description": "d"}]})

    def test_a_role_outside_the_dramatic_five_is_refused(self, vault):
        """`transition` and `non-event` are scene beats, not plot roles."""
        with pytest.raises(ValueError, match="Invalid plot role: transition"):
            write_roles(vault, "s1", [{"plot": "the-resistance",
                                       "role": "transition", "description": "d"}])

    def test_the_message_lists_the_valid_roles(self, vault):
        with pytest.raises(ValueError) as e:
            write_roles(vault, "s1", [{"plot": "the-resistance", "role": "nope",
                                       "description": "d"}])
        for role in PLOT_ROLES:
            assert role in str(e.value)

    def test_a_refused_edit_writes_nothing(self, vault):
        write_roles(vault, "s1", [{"plot": "the-resistance", "role": "setup",
                                   "description": "original"}])
        with pytest.raises(ValueError):
            write_roles(vault, "s1", [{"plot": "the-resistance", "role": "setup",
                                       "description": "changed"},
                                      {"plot": "ghost", "role": "climax",
                                       "description": "d"}])
        # The delete runs inside the transaction, and the refusal aborts it —
        # so the original row is still there, not gone.
        assert [r for r in rows(vault) if r[1] == "s1"] == [
            ("the-resistance", "s1", "plot_setup", "original", 1)]


class TestDelete:
    def test_deleting_a_plot_removes_its_rows(self, vault):
        """FAILS WITHOUT THE FIX. The plot owns the row (`from_id`), so the
        `to_id` sweep in delete_entity never sees it: the row survives, every
        reader filters on `to_id` so it is unreachable while dead, and it
        reattaches silently if a plot takes the same slug again."""
        write_roles(vault, "s1", [{"plot": "the-resistance", "role": "setup",
                                   "description": "d"}])
        delete_entity(vault, "plot", "the-resistance", "cut it", confirm=True)
        assert [r for r in rows(vault) if r[2].startswith("plot_")] == []

    def test_a_deleted_plot_role_is_unreachable_while_the_plot_is_dead(self, vault):
        """The row is gone AND the plot is gone, so nothing dangles.

        Checked on the delete side because that is the sweep's whole purpose.
        See the module docstring for why a *recreated* plot was the original
        worry and why it is not reachable.
        """
        write_roles(vault, "s1", [{"plot": "the-resistance", "role": "setup",
                                   "description": "d"}])
        delete_entity(vault, "plot", "the-resistance", "cut it", confirm=True)
        assert [r for r in rows(vault) if r[2].startswith("plot_")] == []

    def test_restore_brings_the_plot_back_without_its_roles(self, vault):
        """The accepted cost, pinned so it cannot change unnoticed.

        `restore` is documented as exact — prose and relations included. That
        is now false for a plot's role rows: the delete sweep took them, and
        putting them back would mean resurrecting rows nobody can vouch for.
        A test is the only thing that makes a documented exception real.
        """
        from tools.story_admin import _restore_entity
        write_roles(vault, "s1", [{"plot": "the-resistance", "role": "setup",
                                   "description": "d"}])
        delete_entity(vault, "plot", "the-resistance", "cut it", confirm=True)
        _restore_entity({"target": {"entity_type": "plot", "id": "the-resistance"},
                         "summary": "put it back"},
                        vault)
        from core.db import get_dashboard_data
        plot = next(p for p in get_dashboard_data(vault)["story_data"]["plots"]
                    if p["id"] == "the-resistance")
        assert plot["setups"] == [], \
            "if this passes, restore is exact again — drop the exception note"

    def test_deleting_a_scene_still_removes_its_rows(self, vault):
        """The other direction, which already worked via the `to_id` sweep."""
        write_roles(vault, "s1", [{"plot": "the-resistance", "role": "setup",
                                   "description": "d"}])
        delete_entity(vault, "scene", "s1", "cut it", confirm=True)
        assert [r for r in rows(vault) if r[2].startswith("plot_")] == []


class TestExportRoundTrip:
    """FAILS WITHOUT THE FIX, and SILENTLY.

    `plot_roles` is a relation field, so it never lands in `extra`, and the
    scene branch's `fm.update(extra)` would emit no `plot_roles` at all. The
    markdown would simply lose every role, and re-import would find nothing to
    complain about — the worst failure shape there is.
    """

    @pytest.fixture
    def round_tripped(self, tmp_path, monkeypatch):
        """Export the fixture-shaped project, then import it back."""
        root = tmp_path / "root"
        project = root / "projects" / "stc"
        shutil.copytree(REPO / "tests" / "fixtures" / "save-the-children", project)
        import core.config
        monkeypatch.setattr(core.config, "load_plugin_config",
                            lambda: {"root_path": str(root)})
        from tools.story_import import handler as import_handler
        from tools.story_export import handler as export_handler
        import_handler({"project": "stc", "confirm": True}, root_path=str(root))
        export_handler({"project": "stc", "root_path": str(root)})
        return project

    def _plot_roles(self, project, scene):
        conn = sqlite3.connect(str(Path(project) / ".story" / "story.db"))
        out = conn.execute(
            'SELECT from_id, kind, note FROM relations '
            "WHERE to_id=? AND kind LIKE 'plot_%' ORDER BY \"order\"", (scene,)
        ).fetchall()
        conn.close()
        return out

    def test_the_scene_note_carries_its_plot_roles(self, round_tripped):
        scene = round_tripped / "scenes" / "Central Room - Day.md"
        text = scene.read_text()
        assert "plot_roles:" in text, "the scene note lost every plot role"
        assert "the-resistance" in text and "setup" in text

    def test_the_plot_note_no_longer_carries_the_five_fields(self, round_tripped):
        text = (round_tripped / "plots" / "The Resistance.md").read_text()
        for field in ("setups", "crisis", "climax", "complications", "resolutions"):
            assert f"\n{field}:" not in text, \
                f"the plot note still emits the computed field {field}"

    def test_reimport_keeps_every_role(self, round_tripped, tmp_path, monkeypatch):
        """Export → import: the rows have to be identical, or the fact is being
        carried by something other than the relations."""
        before = self._plot_roles(round_tripped, "central-room-day")
        assert before, "the fixture's scene has no role to begin with"

        import core.config
        root2 = tmp_path / "root2"
        project2 = root2 / "projects" / "stc"
        shutil.copytree(round_tripped, project2)
        monkeypatch.setattr(core.config, "load_plugin_config",
                            lambda: {"root_path": str(root2)})
        from tools.story_import import handler as import_handler
        import_handler({"project": "stc", "confirm": True}, root_path=str(root2))
        assert self._plot_roles(project2, "central-room-day") == before

    def test_the_surviving_role_is_on_the_plot_side_too(self, round_tripped,
                                                        tmp_path, monkeypatch):
        """The round trip has to be invisible from the plot's side as well —
        that is what makes it a round trip rather than a relocation."""
        from core.db import get_dashboard_data
        plot = next(p for p in get_dashboard_data(round_tripped)["story_data"]["plots"]
                    if p["id"] == "the-resistance")
        assert plot["setups"], "the plot reads empty after export → import"


class TestSchema:
    def test_the_plot_role_fields_are_computed(self):
        from core.constants import ENTITY_SCHEMAS
        for field in ("setups", "complications", "crisis", "climax", "resolutions"):
            assert ENTITY_SCHEMAS["plot"][field]["computed"] is True, \
                f"plot.{field} is still writable"

    def test_plot_roles_is_a_scene_field_with_the_right_shape(self):
        from core.constants import ENTITY_SCHEMAS
        field = ENTITY_SCHEMAS["scene"]["plot_roles"]
        assert field["type"] == "list"
        assert not field.get("computed"), "the write side cannot be computed"
        assert set(field["sub_fields"]) == {"plot", "role", "description"}

    def test_a_malformed_plot_roles_shape_is_reported(self):
        """The read side shows the shape; this is the write side catching it
        when the display is not consulted. See test_write_shape.py."""
        from core.entity import validate_entity
        warnings = validate_entity("scene", {"plot_roles": "the first scene"})
        assert any("plot_roles must be a list" in w for w in warnings), warnings
        assert any("plot, role, description" in w for w in warnings), warnings

    def test_a_role_outside_the_five_is_not_caught_by_the_shape_check(self):
        """The shape is fine; only `validate_scene_plot_roles` can judge the
        role, because the same call also resolves the plot. Stated so the
        division of labour is not mistaken for a gap."""
        from core.entity import validate_entity
        warnings = validate_entity("scene", {
            "plot_roles": [{"plot": "p", "role": "transition", "description": "d"}]})
        assert not [w for w in warnings if "plot_roles" in w]