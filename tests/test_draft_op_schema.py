"""The published `ops` schema must state the grammar `validate_ops` enforces.

The model is handed `story_draft`'s JSON Schema, never this code. When the two
disagreed, the model was told an op was "an object" and guessed — arriving with
keys stripped, which read as a bridge bug and wasn't one. The schema is built
from the validator's tables precisely so it cannot drift; these tests are what
keeps that true, and they fail if someone hand-edits one side.

Deliberately stdlib-only: the repo has no jsonschema dependency and adding one to
check four dicts is not worth it. The check is that both sides agree, not that a
third-party validator agrees.
"""
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from core import drafts  # noqa: E402
from core.constants import ENTITY_SCHEMAS  # noqa: E402
from core.writes import REORDERABLE_TYPES  # noqa: E402
from tools.story_draft import _op_schemas  # noqa: E402


def _branches():
    return {b["properties"]["op"]["enum"][0]: b for b in _op_schemas()}


def test_every_op_kind_has_a_branch():
    assert set(_branches()) == set(drafts.OP_ORDER)


def test_branch_required_matches_the_validator():
    """The whole point: the model is told exactly what stage will demand."""
    branches = _branches()
    for kind, required in drafts.REQUIRED_OP_KEYS.items():
        assert branches[kind]["required"] == ["op", *required], kind


def test_entity_types_enumerated_not_left_open():
    """A bare string lets the model invent an entity type that cannot commit."""
    branches = _branches()
    for kind in ("create", "edit", "delete"):
        assert branches[kind]["properties"]["entity_type" if kind != "create" else "type"]["enum"] \
            == list(ENTITY_SCHEMAS), kind


def test_reorder_is_restricted_to_reorderable_types():
    """`reorder` is refused at stage for anything else, so say so up front."""
    assert _branches()["reorder"]["properties"]["entity_type"]["enum"] == list(REORDERABLE_TYPES)


def test_ordered_ids_declares_its_item_type():
    """Untyped list items are how a list of strings comes back double-nested."""
    assert _branches()["reorder"]["properties"]["ordered_ids"]["items"] == {"type": "string"}


def test_frontmatter_and_data_stay_free_form():
    """Their keys are the entity's fields — story_describe's job, not the schema's.

    A closed object here would be wrong twice over: it would have to be
    restated for ten entity types, and it would go stale on the first schema
    change. Open is correct.
    """
    branches = _branches()
    assert branches["create"]["properties"]["frontmatter"]["type"] == "object"
    assert branches["edit"]["properties"]["data"]["type"] == "object"


@pytest.mark.parametrize("kind", sorted(drafts.OP_ORDER))
def test_a_well_formed_op_satisfies_its_own_branch(kind):
    """Each published branch accepts the op shape its own required list implies."""
    branch = _branches()[kind]
    op = {"op": kind}
    for key in branch["required"]:
        if key == "op":
            continue
        op[key] = {
            "type": "character",
            "entity_type": "scene",
            "id": "mara-venn",
            "entity_id": "the-lamp",
            "frontmatter": {"name": "Mara"},
            "data": {"status": "written"},
            "ordered_ids": ["a", "b"],
            "summary": "one line",
        }[key]
    missing = [k for k in branch["required"] if k not in op]
    assert not missing
    assert set(op) >= set(branch["required"])
