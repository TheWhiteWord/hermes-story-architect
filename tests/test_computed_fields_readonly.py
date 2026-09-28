"""A computed field cannot be written, and the agent is told at preview time.

`character.relationships` is derived from relationship entities. The write path
(`edit_entity`) already drops such a field and reports `skipped_read_only` — but
that happens *after* the agent has read a preview promising the change, so the
preview is the only place it can still be told. It was silent: the draft
validator skipped every op that was not a `create`.
"""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from tools.story_draft import handler  # noqa: E402


def _stage(project, ops):
    return json.loads(handler({"project": str(project), "action": "stage",
                               "ops": ops, "summary": "probe"}))


def test_editing_a_computed_field_is_reported_at_preview(fixture_path):
    r = _stage(fixture_path, [{
        "op": "edit", "entity_type": "character", "entity_id": "kael",
        "data": {"relationships": [{"with": "marcus-chen",
                                    "label": "Rival", "type": "enemy"}]},
        "summary": "probe: write a read-only field",
    }])
    assert r["validation"], "no warning about a read-only field"
    assert any("relationships" in f and "read-only" in f for f in r["validation"])


def test_creating_with_a_computed_field_is_reported(fixture_path):
    """A create cannot actually write one — the schema merge drops it — so the
    finding is the only place that says so."""
    r = _stage(fixture_path, [{
        "op": "create", "type": "character", "slug": "someone-new",
        "frontmatter": {"name": "Someone", "relationships": []},
        "summary": "probe",
    }])
    assert any("relationships" in f and "read-only" in f for f in r["validation"])


def test_editing_an_ordinary_field_reports_nothing(fixture_path):
    r = _stage(fixture_path, [{
        "op": "edit", "entity_type": "character", "entity_id": "kael",
        "data": {"story_role": "Protagonist"},
        "summary": "probe: an editable field",
    }])
    assert r["validation"] == []


def test_the_write_path_also_refuses_it(fixture_path):
    """The preview is not the only guard; `edit_entity` drops it and says so."""
    from core.writes import edit_entity

    r = edit_entity(fixture_path, "character", "kael",
                    data={"relationships": [{"with": "marcus-chen"}]},
                    summary="probe")
    assert r["skipped_read_only"] == ["relationships"]
    assert r["applied"]["fields"] == []
    assert "read-only" in r["warning"]
