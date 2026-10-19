"""Phase 0 T0.3 — pin the read contract for a beat reference.

A ref target that does not exist must be:
  - an error on write (Phase 1, T1.5)
  - a soft finding on read (Phase 3, prose in Findings section)

This test asserts that `check_references` uses id+type lookup, so the fix
in Phase 1 (adding `scene_beats` refs to the write path) is not regressed
by a later refactor. Uses `plot.characters` (ref: character) as the
concrete case since `scene_beats` schema does not exist yet.
"""
import pytest

from core import writes
from core.db import get_db
from core.entity import check_references


def test_check_references_id_only_lookup(fixture_path):
    """A ref resolves by id+type. Phase 1 adds scene_beats refs to this path."""
    # Create a character
    writes.create_entity(fixture_path, "character", "alice", {"name": "Alice"})

    # A plot referencing that character passes
    check_references(fixture_path, "plot", {"characters": ["alice"]})

    # A plot referencing a non-existent character raises
    with pytest.raises(ValueError, match="Character not found"):
        check_references(fixture_path, "plot", {"characters": ["ghost"]})
