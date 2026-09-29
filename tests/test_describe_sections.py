"""story_describe must report the section vocabulary, and it must be the real one.

The section names are a closed set on the write path — `core/writes.py` rejects
an edit key that is not a field, a relation, or a standard section — so an agent
that has to guess a name loses the whole write. Nothing else in the tool surface
reports them: `story_retrieve` only reveals `available_sections` as a side effect
of a miss. These tests fail if that regresses, or if the reported list drifts
from what the write path actually accepts.
"""
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from core.entity import standard_sections  # noqa: E402
from tools.story_describe import handler  # noqa: E402


def _describe(entity_type=None):
    args = {"entity_type": entity_type} if entity_type else {}
    return json.loads(handler(args))["entity_schemas"]


def test_every_type_reports_its_sections():
    out = _describe()
    assert out, "no entity types described"
    for entity_type, entry in out.items():
        assert "sections" in entry, f"{entity_type} reports no sections"


def test_reported_sections_are_the_ones_the_write_path_accepts():
    """The whole point: the list is read from standard_sections, not restated."""
    for entity_type, entry in _describe().items():
        assert entry["sections"]["standard_sections"] == standard_sections(entity_type), \
            entity_type


def test_the_character_vocabulary_is_present_and_named():
    sections = _describe("character")["character"]["sections"]["standard_sections"]
    for name in ("Identity", "Desires", "Background", "Contradictions",
                 "Psychology", "Arc", "Relationships", "Voice", "Notes"):
        assert name in sections, name


def test_sections_say_they_are_a_closed_set():
    """The model has to know a wrong guess is rejected, not merely unusual."""
    description = _describe("scene")["scene"]["sections"]["description"]
    assert "CLOSED SET" in description
    assert "story_draft" in description


def test_sections_do_not_shadow_a_field():
    """Merged flat, so the synthetic key must not collide with a real field."""
    from core.constants import ENTITY_SCHEMAS

    for entity_type, entry in _describe().items():
        assert entity_type in ENTITY_SCHEMAS
        assert "sections" not in ENTITY_SCHEMAS[entity_type], \
            f"{entity_type} has a real field named 'sections' — the merged key collides"


def test_every_type_has_at_least_one_section():
    for entity_type, entry in _describe().items():
        assert entry["sections"]["standard_sections"], f"{entity_type} has no sections"
