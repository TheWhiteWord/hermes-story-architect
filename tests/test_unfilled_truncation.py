"""A gap hidden by the cap must not look like a gap that was fixed.

Regression: `characters` fell past UNFILLED_LIMIT at count 2 and vanished from
the view, so setting no_cast on one of two castless scenes dropped the count to
1 and pushed it further off. The view then showed no `characters` gap at all
while the DB still had one — fixing a scene looked like resolving the field.
"""
import json
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

FIXTURE = Path(__file__).parent / "fixtures" / "save-the-children"


@pytest.fixture
def project(tmp_path, monkeypatch):
    root = tmp_path / "root"
    shutil.copytree(FIXTURE, root / "projects" / "save-the-children")
    import core.config
    monkeypatch.setattr(core.config, "load_plugin_config", lambda: {"root_path": str(root)})
    from tools.story_import import handler as import_handler
    import_handler({"project": "save-the-children", "confirm": True}, root_path=str(root))
    return root / "projects" / "save-the-children"


def unfilled(project):
    from tools.story_load import handler
    return json.loads(
        handler({"project": "save-the-children", "view": "unfilled"},
                root_path=str(project.parent.parent)))


def test_omitted_fields_are_named(project):
    """When the view truncates, it must say which fields it dropped."""
    data = unfilled(project)
    assert data["truncated"] is True
    assert data["other_fields"], "truncated view must name the fields it omitted"
    shown = {i["field"] for i in data["unfilled"]}
    dropped = set(data["other_fields"])
    assert shown and dropped
    assert not (shown & dropped), "a field cannot be both shown and omitted"
    assert len(data["unfilled"]) + len(data["other_fields"]) == data["gap_types"]


def test_a_gap_is_never_silently_absent(project):
    """Every field the DB knows about is either shown or named as omitted."""
    from core.db import get_unfilled_map
    data = unfilled(project)
    known = set(get_unfilled_map(project))
    accounted = {i["field"] for i in data["unfilled"]} | set(data.get("other_fields", []))
    assert known == accounted


def test_untruncated_view_has_no_other_fields(project, monkeypatch):
    """Below the cap there is nothing omitted, so the key must be absent."""
    import tools.story_load as sl
    monkeypatch.setattr(sl, "UNFILLED_LIMIT", 1000)
    data = unfilled(project)
    assert "truncated" not in data
    assert "other_fields" not in data


def test_no_drift_row_when_every_container_carries_a_charge(project):
    """The fixture is consistent, so there is nothing to report. Absent, not empty."""
    assert "value_drift" not in unfilled(project)


def test_drift_row_names_a_container_whose_children_carry_charges(project):
    """The gap row says the act is empty; only this says its scenes are not.

    Symptom 2 of the original issue: `act-2` and its sequence held no value
    while all three of their scenes ran charges. Every one of those was
    invisible — the container was a gap, the scenes were filled, and nothing
    connected the two facts.
    """
    from tools.story_create import handler as create_handler
    from tools.story_edit import handler as edit_handler

    vault = project.parent.parent

    def create(entity_type, slug, frontmatter):
        create_handler({"entity_type": entity_type, "slug": slug,
                        "project": "save-the-children", "frontmatter": frontmatter},
                       root_path=str(vault))

    def edit(entity_type, slug, **fields):
        edit_handler({"action": "edit_note", "summary": "test",
                      "target": {"entity_type": entity_type, "slug": slug,
                                 "project": "save-the-children"},
                      "data": fields}, root_path=str(vault))

    # A charged act holding a charged sequence holding charged scenes, then
    # strip the act's own charge: exactly the drift, built in the open.
    create("act", "act-2", {"title": "Act Two", "order": 2})
    create("sequence", "seq-confrontation",
           {"title": "The Confrontation", "order": 1, "act_id": "act-2",
            "value_at_open": "negative", "value_at_close": "positive"})
    drift = unfilled(project).get("value_drift", [])
    assert "act-2" in {d["id"] for d in drift}

    # Give the act a charge of its own and it stops being drift — the row
    # reports a missing field, so filling the field retires it.
    edit("act", "act-2", value_at_open="negative", value_at_close="positive")
    drift = unfilled(project).get("value_drift", [])
    assert "act-2" not in {d["id"] for d in drift}


def test_drift_row_reports_presence_not_a_suggested_value(project):
    """It must not invent a charge. The correspondence is a writing decision."""
    from core.db import get_value_drift
    for row in get_value_drift(project):
        assert set(row) == {"id", "type", "descendants_with_charges"}
        assert "value_at_open" not in row and "value_at_close" not in row
