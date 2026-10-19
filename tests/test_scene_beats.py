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
from core.db import get_db, get_unfilled_map
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


# ── T2.1: unfilled reporting for the scene's computed scene_beats field ──

def _make_project(tmp_path):
    """Create a minimal project with acts/sequences/scenes folders."""
    from pathlib import Path
    project_path = Path(tmp_path) / "test-project"
    project_path.mkdir()
    (project_path / "characters").mkdir(parents=True)
    (project_path / "locations").mkdir(parents=True)
    (project_path / "worlds").mkdir(parents=True)
    (project_path / "plots").mkdir(parents=True)
    (project_path / "scenes").mkdir(parents=True)
    (project_path / "sequences").mkdir(parents=True)
    (project_path / "acts").mkdir(parents=True)
    (project_path / ".story").mkdir(parents=True)
    (project_path / "project.md").write_text("---\nname: Test\n---\n")
    return project_path


def _make_scene(project_path, scene_id, status, dramatic_role):
    """Create a scene with the given status and dramatic_role."""
    writes.create_entity(project_path, "act", f"act-{scene_id}", {"title": f"Act {scene_id}"})
    writes.create_entity(project_path, "sequence", f"seq-{scene_id}",
                        {"title": f"Seq {scene_id}", "act_id": f"act-{scene_id}"})
    writes.create_entity(project_path, "scene", scene_id, {
        "title": f"Scene {scene_id}",
        "status": status,
        "dramatic_role": dramatic_role,
        "sequence_id": f"seq-{scene_id}",
        "act_id": f"act-{scene_id}",
    })


def test_unfilled_reports_scene_beats_for_drafted_plot_role_scene(tmp_path):
    """A drafted plot-role scene with no scene_beats is reported unfilled."""
    p = _make_project(tmp_path)
    _make_scene(p, "drafted-plot", "drafted", "plot_role")
    unfilled = get_unfilled_map(p)
    assert "drafted-plot" in unfilled.get("scene_beats", [])


def test_unfilled_reports_scene_beats_for_drafted_empty_role_scene(tmp_path):
    """A drafted scene with empty dramatic_role is reported unfilled."""
    p = _make_project(tmp_path)
    _make_scene(p, "drafted-empty", "drafted", "")
    unfilled = get_unfilled_map(p)
    assert "drafted-empty" in unfilled.get("scene_beats", [])


def test_unfilled_skips_planned_scene(tmp_path):
    """A planned scene is a stub and is skipped."""
    p = _make_project(tmp_path)
    _make_scene(p, "planned-scene", "planned", "plot_role")
    unfilled = get_unfilled_map(p)
    assert "planned-scene" not in unfilled.get("scene_beats", [])


def test_unfilled_skips_transition_scene(tmp_path):
    """A transition scene is never reported."""
    p = _make_project(tmp_path)
    _make_scene(p, "transition-scene", "drafted", "transition")
    unfilled = get_unfilled_map(p)
    assert "transition-scene" not in unfilled.get("scene_beats", [])


def test_unfilled_skips_non_event_scene(tmp_path):
    """A non-event scene is never reported."""
    p = _make_project(tmp_path)
    _make_scene(p, "non-event-scene", "drafted", "non-event")
    unfilled = get_unfilled_map(p)
    assert "non-event-scene" not in unfilled.get("scene_beats", [])


def test_unfilled_not_reported_when_scene_beats_exists(tmp_path):
    """A scene with a scene_beats record is not reported."""
    p = _make_project(tmp_path)
    _make_scene(p, "has-beats", "drafted", "plot_role")
    writes.create_entity(p, "scene_beats", "has-beats-beats", {
        "scene": "has-beats",
        "beats": [{"action": {"surface": "test"}, "reaction": {"surface": "test"}}],
    })
    unfilled = get_unfilled_map(p)
    assert "has-beats" not in unfilled.get("scene_beats", [])
