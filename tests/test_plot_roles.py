"""One source for the plot role vocabulary.

The same role list used to be hand-written in eight places, so adding a role
meant editing all eight and missing one was a silent dashboard bug rather than
an error. `PLOT_ROLES` (constants) and `_RELATION_FIELDS["plot"]` (entity) are
the only two places the vocabulary now lives; everything else derives from
them. The first test is what keeps those two from drifting — a comment would
not, which is why it is a test.
"""
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from core.constants import PLOT_ROLES  # noqa: E402
from core.entity import PLOT_BEAT_FIELDS  # noqa: E402


class TestVocabulary:
    def test_plot_roles_matches_the_relation_field_map(self):
        """The drift guard. Both sides are written by hand; only a test links them."""
        roles_from_map = {kind.replace("plot_", "") for kind in PLOT_BEAT_FIELDS.values()}
        assert set(PLOT_ROLES) == roles_from_map

    def test_the_five_dramatic_roles(self):
        """The dramatic roles. `transition`/`non-event` are scene beats, not plot roles."""
        assert PLOT_ROLES == ["setup", "complication", "crisis", "climax", "resolution"]

    def test_the_dashboard_role_list_is_the_same_list(self):
        """The JS copy is hand-written like PLOT_ROLES was — so pin it.

        The dashboard's role badges and role sections iterate this list; a role
        added in Python and forgotten here renders a plot with a silent gap,
        not an error.
        """
        from pathlib import Path
        js = (REPO / "src/dashboard/js/colors.js").read_text()
        found = re.search(r"DASH\.PLOT_ROLES = \[([^\]]*)\]", js)
        assert found, "colors.js no longer declares DASH.PLOT_ROLES"
        assert [r.strip().strip("'\"") for r in found.group(1).split(",") if r.strip()] == PLOT_ROLES

    def test_field_names_are_not_role_names_pluralised(self):
        """`crisis` and `climax` stay singular — so the map cannot be derived
        from the role names, only iterated. Stated so the constraint survives."""
        assert "crisis" in PLOT_BEAT_FIELDS and "climax" in PLOT_BEAT_FIELDS
        assert "crisiss" not in PLOT_BEAT_FIELDS and "climaxs" not in PLOT_BEAT_FIELDS


@pytest.fixture
def full_role_project(tmp_path):
    """A project where one plot fills every role, in one sequence inside one act."""
    from core.writes import create_entity, create_project, edit_entity

    root = tmp_path / "v"
    (root / "projects").mkdir(parents=True)
    assert create_project("stc", {"name": "STC", "logline": "L"}, root)["success"] is True
    project = root / "projects" / "stc"

    create_entity(project, "act", "act-1", {"title": "Act One", "order": 1, "status": "drafted"})
    create_entity(project, "sequence", "seq-1", {"title": "Seq", "order": 1,
                                                 "status": "drafted", "act_id": "act-1"})
    # One scene per role. The role is written on the SCENE as `plot_roles` —
    # the plot's own fields are computed, so this is the only write path.
    for i, role in enumerate(PLOT_ROLES):
        create_entity(project, "scene", f"scene-{i}", {
            "title": f"Scene {i}", "order": i, "status": "written",
            "dramatic_role": role, "sequence_id": "seq-1", "act_id": "act-1",
        })

    create_entity(project, "plot", "the-plot", {
        "name": "The Plot", "one_sentence": "x", "plot_scope": "main",
    })
    for i, role in enumerate(PLOT_ROLES):
        edit_entity(project, "scene", f"scene-{i}", {
            "plot_roles": [{"plot": "the-plot", "role": role, "description": "d"}],
        }, f"record the {role}")
    return project


class TestHasRoleFlags:
    """Every role's flag, on both the sequence row and the act row. Written before
    the refactor, it fails on the hardcoded four-flag version — a new role
    would have needed four more edits in two places to show up here."""

    @pytest.mark.parametrize("owner", ["sequence", "act"])
    def test_every_role_raises_its_flag(self, full_role_project, owner):
        from core.db import get_dashboard_data

        data = get_dashboard_data(full_role_project)["story_data"]
        rows = (data["sequences"] if owner == "sequence" else data["acts"])
        plots = [p for row in rows for p in row.get("plots", [])]
        assert plots, f"no plot row on the {owner}"
        for plot in plots:
            for role in PLOT_ROLES:
                assert plot.get(f"has_{role}") is True, \
                    f"{owner} row missing has_{role}: {sorted(plot)}"

    def test_flag_set_is_exactly_the_roles(self, full_role_project):
        """No stale hardcoded flag survives, and none is missing."""
        from core.db import get_dashboard_data

        data = get_dashboard_data(full_role_project)["story_data"]
        plot = next(p for p in data["sequences"][0]["plots"])
        flags = {k for k in plot if k.startswith("has_")}
        assert flags == {f"has_{role}" for role in PLOT_ROLES}