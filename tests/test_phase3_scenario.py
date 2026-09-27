"""3-edit scenario test: sequential edits → each visible in next load."""
import json
import shutil
import tempfile
from pathlib import Path

import pytest

from core.writes import (create_entity, delete_entity, edit_entity,
                          reorder)
from tools.story_import import handler as import_handler
from tools.story_load import handler as load_handler
from tools.story_retrieve import handler as retrieve_handler


@pytest.fixture
def db_project(fixture_path):
    """Create a temp project with DB imported from fixture."""
    tmp = tempfile.mkdtemp()
    proj = Path(tmp) / "projects" / "save-the-children"
    proj.parent.mkdir(parents=True)
    shutil.copytree(str(fixture_path), str(proj))
    import_handler({"project": str(proj), "root_path": Path(tmp)})
    yield proj, Path(tmp)
    shutil.rmtree(tmp, ignore_errors=True)


def _find_entity_in_nested(result, entity_type, slug):
    """Find an entity in the nested load result by type and slug."""
    if entity_type == "character":
        return next((e for e in result["characters"] if e["id"] == slug), None)
    elif entity_type == "plot":
        return next((e for e in result["plots"] if e["id"] == slug), None)
    elif entity_type == "location":
        for world in result["worlds"]:
            found = next((loc for loc in world.get("locations", []) if loc["id"] == slug), None)
            if found:
                return found
        return None
    elif entity_type == "world":
        return next((e for e in result["worlds"] if e["id"] == slug), None)
    elif entity_type == "act":
        for act in result["acts"]:
            if act.get("id") == slug:
                return act
    elif entity_type == "sequence":
        for act in result["acts"]:
            for seq in act.get("sequences", []):
                if seq.get("id") == slug:
                    return seq
    elif entity_type == "scene":
        for act in result["acts"]:
            for seq in act.get("sequences", []):
                for scene in seq.get("scenes", []):
                    if isinstance(scene, dict) and scene.get("id") == slug:
                        return scene
    return None


def _all_entity_ids(result):
    """Collect all entity IDs from nested structure."""
    ids = set()
    for char in result["characters"]:
        ids.add(char["id"])
    for loc in result.get("orphaned_locations", []):
        ids.add(loc["id"])
    for plot in result["plots"]:
        ids.add(plot["id"])
    for world in result["worlds"]:
        ids.add(world["id"])
        for loc in world.get("locations", []):
            ids.add(loc["id"])
    for act in result["acts"]:
        ids.add(act["id"])
        for seq in act.get("sequences", []):
            ids.add(seq["id"])
            for scene in seq.get("scenes", []):
                if isinstance(scene, dict):
                    ids.add(scene["id"])
                else:
                    ids.add(scene)
    return ids


class Test3EditScenario:
    """3-edit scenario: each edit → next load shows change immediately."""

    def test_edit_note_visible_in_load(self, db_project):
        """Edit kael's one_sentence → story_load shows new value."""
        proj, vault = db_project

        # Edit
        result = edit_entity(proj, "character", "kael",
                              {"one_sentence": "Updated description for kael."},
                              "Update kael one_sentence")
        assert result["success"] is True

        # Load shows change
        result = json.loads(load_handler({"project": str(proj), "root_path": vault}))
        assert result["loaded"] is True
        kael = next(e for e in result["characters"] if e["id"] == "kael")
        assert kael["one_sentence"] == "Updated description for kael."

    def test_delete_entity_excluded_from_load(self, db_project):
        """Delete a character → story_load excludes it. Arcs cascade-delete."""
        proj, vault = db_project

        # Create a character with arc beats
        create_entity(proj, "character", "temp-char",
            {"name": "Temp", "story_role": "Minor", "one_sentence": "Temp"})
        create_entity(proj, "arc_beat", "1", {
            "id": "1", "character": "temp-char",
            "label": "Beat", "action": "a", "gap": "g",
            "choice": "c", "shift": "s", "y": 0.0, "order": 1,
        })

        # Delete character
        result = delete_entity(proj, "character", "temp-char",
                               "Delete temp-char", True)
        assert result["success"] is True

        # Load excludes deleted entity AND its arcs
        result = json.loads(load_handler({"project": str(proj), "root_path": vault}))
        ids = _all_entity_ids(result)
        assert "temp-char" not in ids
        assert "temp-char-1" not in ids, f"Arc beat not cascade-deleted: {ids}"

    def test_delete_sequence_with_scenes_blocked(self, db_project):
        """Deleting a sequence that has scenes is blocked."""
        proj, vault = db_project

        create_entity(proj, "sequence", "seq-with-scenes",
            {"title": "Seq", "act_id": "act-1"})  # act-1 from fixture import
        # Create a scene in this sequence
        create_entity(proj, "scene", "scene-in-seq",
            {"title": "Scene", "sequence_id": "seq-with-scenes", "act_id": "act-1"})

        result = delete_entity(proj, "sequence", "seq-with-scenes",
                               "Delete seq", True)
        assert "Cannot delete" in result["error"]
        assert [c["id"] for c in result["blocking_children"]] == ["scene-in-seq"]

    def test_delete_character_cascades_arcs(self, db_project):
        """Deleting a character cascade-deletes all their arc beats."""
        proj, vault = db_project

        create_entity(proj, "character", "cascade-char",
            {"name": "Cascade", "story_role": "Minor", "one_sentence": "Test"})
        for i in range(1, 4):
            create_entity(proj, "arc_beat", str(i), {
                "id": str(i), "character": "cascade-char",
                "label": f"Beat {i}", "action": "a", "gap": "g",
                "choice": "c", "shift": "s", "y": 0.0, "order": i,
            })

        # Delete character
        result = delete_entity(proj, "character", "cascade-char",
                               "Delete cascade-char", True)
        assert result["success"] is True

        # All arcs gone
        result = json.loads(load_handler({"project": str(proj), "root_path": vault}))
        ids = _all_entity_ids(result)
        assert "cascade-char" not in ids
        for i in range(1, 4):
            assert f"cascade-char-{i}" not in ids, f"Arc {i} not cascade-deleted: {ids}"

    def test_reorder_visible_in_load(self, db_project):
        """Reorder scenes → story_load shows new order_key sequence."""
        proj, vault = db_project

        # Create a sequence with scenes
        create_entity(proj, "act", "act-test", {"title": "Test Act"})
        create_entity(proj, "sequence", "seq-test",
            {"title": "Test Seq", "act_id": "act-test"})
        for slug in ["scene-x", "scene-y", "scene-z"]:
            create_entity(proj, "scene", slug,
                {"title": f"Scene {slug[-1]}", "sequence_id": "seq-test", "act_id": "act-test"})

        # Reorder: scene-z first
        result = reorder(proj, "scene", ["scene-z", "scene-x", "scene-y"],
                         "Reorder scenes")
        assert result["success"] is True

        # Load shows new order
        result = json.loads(load_handler({"project": str(proj), "root_path": vault}))
        # Find scenes in nested structure
        scenes_found = {}
        for act in result["acts"]:
            for seq in act.get("sequences", []):
                for scene in seq.get("scenes", []):
                    if isinstance(scene, dict) and scene.get("id") in ("scene-x", "scene-y", "scene-z"):
                        scenes_found[scene["id"]] = scene
        assert len(scenes_found) == 3
        # Order is implied by array position — find the sequence containing them
        for act in result["acts"]:
            for seq in act.get("sequences", []):
                scene_ids = [s["id"] if isinstance(s, dict) else s for s in seq.get("scenes", [])]
                if "scene-z" in scene_ids:
                    # Verify order-z is first among the three
                    ordered = [sid for sid in scene_ids if sid in ("scene-x", "scene-y", "scene-z")]
                    assert ordered == ["scene-z", "scene-x", "scene-y"], f"Order wrong: {ordered}"


class TestAppValidation:
    """App-level validation: scene act_id consistency, plot/arc refs."""

    def test_scene_mismatched_act_id_rejected(self, tmp_path):
        """Create scene with mismatched sequence.act_id vs scene.act_id → error."""
        create_entity(tmp_path, "act", "act-a",
            {"title": "Act A"})
        create_entity(tmp_path, "act", "act-b",
            {"title": "Act B"})
        create_entity(tmp_path, "sequence", "seq-1",
            {"title": "Seq 1", "act_id": "act-a"})

        with pytest.raises(ValueError, match="act"):
            create_entity(tmp_path, "scene", "bad-scene",
                {"title": "Bad Scene", "sequence_id": "seq-1", "act_id": "act-b"})

    def test_plot_unknown_character_rejected(self, tmp_path):
        """Create plot with non-existent character → error."""
        with pytest.raises(ValueError, match="Character not found|nonexistent-char"):
            create_entity(tmp_path, "plot", "test-plot",
                {"name": "Test Plot", "characters": ["nonexistent-char"]})

    def test_arc_unknown_character_rejected(self, tmp_path):
        """Create arc with non-existent character → error."""
        with pytest.raises(ValueError, match="Character not found"):
            create_entity(tmp_path, "arc_beat", "1", {
                "id": "1", "character": "nonexistent",
                "label": "Test", "action": "a", "gap": "g",
                "choice": "c", "shift": "s", "y": 0.0, "order": 1,
            })

    def test_arc_unknown_scene_rejected(self, tmp_path):
        """Create arc with non-existent scene → error."""
        create_entity(tmp_path, "character", "kael",
            {"name": "Kael", "story_role": "Protagonist", "one_sentence": "Test"})
        with pytest.raises(ValueError, match="Scene not found"):
            create_entity(tmp_path, "arc_beat", "1", {
                "id": "1", "character": "kael", "scene": "nonexistent-scene",
                "label": "Test", "action": "a", "gap": "g",
                "choice": "c", "shift": "s", "y": 0.0, "order": 1,
            })