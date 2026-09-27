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


def unfilled_by(project, **kw):
    from tools.story_load import handler
    return json.loads(
        handler({"project": "save-the-children", "view": "unfilled", **kw},
                root_path=str(project.parent.parent)))


def test_a_filtered_answer_is_complete_and_points_both_ways(project):
    """Asking about one field or entity is what makes the long list readable.

    The cap exists because ~20 field types do not fit. A filtered answer has
    no such problem, so it must not inherit the truncation machinery — no
    `other_fields`, no `truncated`, and no list that could have been cut.

    The two filters are the two directions of one question and compose:
    `entities` is who has the gap, `fields` is what one entity lacks.
    """
    from core.db import get_unfilled_map
    known = get_unfilled_map(project)
    dropped = unfilled(project)["other_fields"][0]
    assert dropped in known, "the omitted field must still be a real gap"

    by_field = unfilled_by(project, field=dropped)
    assert "truncated" not in by_field and "other_fields" not in by_field
    assert by_field["entities"] == known[dropped], "field= must be a lookup, not a sample"

    entity = by_field["entities"][0]
    by_entity = unfilled_by(project, entity=entity)
    assert "truncated" not in by_entity and "other_fields" not in by_entity
    assert by_entity["fields"] == sorted(
        f for f, ids in known.items() if entity in ids)

    both = unfilled_by(project, field=dropped, entity=entity)
    assert both["entities"] == known[dropped]
    assert dropped in both["fields"], "the two filters answer opposite questions"


def test_a_filter_that_matches_nothing_says_so(project):
    """An empty list with no explanation reads as "complete", not "you typo'd"."""
    for kw in ({"field": "no_cast"}, {"field": "not_a_real_field"}):
        empty = unfilled_by(project, **kw)
        key = "entities" if "field" in kw else "fields"
        assert empty[key] == [], empty
        assert "message" in empty, f"{kw} returned an empty list with no explanation"

    complete = unfilled_by(project, entity="no-such-entity")
    assert complete["fields"] == [] and "message" in complete


def test_a_field_that_is_empty_by_design_is_not_a_gap():
    """`variant_of` is empty ON a base location or world — that is what a base
    one is. Reported as unfilled, every project carries the gap forever and
    "fixing" it means inventing a parent that does not exist.
    """
    from core.constants import ENTITY_SCHEMAS
    from core.entity import unfilled_fields
    for entity_type in ("location", "world"):
        assert "variant_of" in ENTITY_SCHEMAS[entity_type], \
            f"{entity_type} lost variant_of — this guard is about the field, not the type"
        assert "variant_of" not in unfilled_fields(entity_type, {}), \
            f"{entity_type}.variant_of is reported as a gap on a base entity"


def test_a_field_that_is_filled_by_hand_is_still_not_a_gap():
    """The skip is unconditional — a real variant relationship is not a gap
    either, and neither state should reach the view."""
    from core.entity import unfilled_fields
    assert "variant_of" not in unfilled_fields("location", {"variant_of": "the-i"})


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
    # The hint must point at how to ask about one, or the caller is left with a
    # list it cannot act on and no way to get past the cap.
    assert "field=" in data["hint"] and "entity=" in data["hint"], data["hint"]


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
    from core.writes import create_entity, edit_entity

    def create(entity_type, slug, frontmatter):
        create_entity(project, entity_type, slug, frontmatter)

    def edit(entity_type, slug, **fields):
        edit_entity(project, entity_type, slug, fields, "test")

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
