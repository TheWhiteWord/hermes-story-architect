"""3-edit scenario test: sequential edits → each visible in next load."""
import json
import shutil
import tempfile
from pathlib import Path

import pytest

from tools.story_import import handler as import_handler
from tools.story_load import handler as load_handler
from tools.story_retrieve import handler as retrieve_handler
from tools.story_create import handler as create_handler
from tools.story_edit import handler as edit_handler
from tools.story_search import handler as search_handler


@pytest.fixture
def fixture_path():
    return Path(__file__).parent / "fixtures" / "save-the-children"


@pytest.fixture
def db_project(fixture_path):
    """Create a temp project with DB imported from fixture."""
    tmp = tempfile.mkdtemp()
    proj = Path(tmp) / "projects" / "save-the-children"
    proj.parent.mkdir(parents=True)
    shutil.copytree(str(fixture_path), str(proj))
    import_handler({"project": str(proj), "vault_path": Path(tmp)})
    yield proj, Path(tmp)
    shutil.rmtree(tmp, ignore_errors=True)


class Test3EditScenario:
    """3-edit scenario: each edit → next load shows change immediately."""

    def test_edit_note_visible_in_load(self, db_project):
        """Edit kael's one_sentence → story_load shows new value."""
        proj, vault = db_project

        # Edit
        result = edit_handler({
            "action": "edit_note",
            "target": {"entity_type": "character", "slug": "kael", "project": str(proj)},
            "data": {"one_sentence": "Updated description for kael."},
            "summary": "Update kael one_sentence",
            "vault_path": vault
        })
        assert json.loads(result)["success"] is True

        # Load shows change
        result = json.loads(load_handler({"project": str(proj), "vault_path": vault}))
        assert result["loaded"] is True
        entities = result["entities"]["rows"]
        kael_row = next(r for r in entities if r[0] == "kael")
        # cols: id, type, name, one_sentence, status, order_key, parent_id, location_id, extra
        assert kael_row[3] == "Updated description for kael."

    def test_delete_entity_excluded_from_load(self, db_project):
        """Delete a character → story_load excludes it. Arcs cascade-delete."""
        proj, vault = db_project

        # Create a character with arc beats
        create_handler({
            "entity_type": "character", "slug": "temp-char", "project": str(proj),
            "frontmatter": {"name": "Temp", "story_role": "Minor", "one_sentence": "Temp"},
            "vault_path": vault
        })
        create_handler({
            "entity_type": "arc", "slug": "1", "project": str(proj),
            "frontmatter": {
                "id": "1", "character": "temp-char",
                "label": "Beat", "action": "a", "gap": "g",
                "choice": "c", "shift": "s", "y": 0.0, "order": 1,
            },
            "vault_path": vault
        })

        # Delete character
        result = edit_handler({
            "action": "delete_entity",
            "target": {"entity_type": "character", "slug": "temp-char", "project": str(proj)},
            "summary": "Delete temp-char",
            "vault_path": vault
        })
        assert json.loads(result)["success"] is True

        # Load excludes deleted entity AND its arcs
        result = json.loads(load_handler({"project": str(proj), "vault_path": vault}))
        entities = result["entities"]["rows"]
        ids = [r[0] for r in entities]
        assert "temp-char" not in ids
        assert "temp-char-1" not in ids, f"Arc beat not cascade-deleted: {ids}"

    def test_delete_sequence_with_scenes_blocked(self, db_project):
        """Deleting a sequence that has scenes is blocked."""
        proj, vault = db_project

        create_handler({
            "entity_type": "sequence", "slug": "seq-with-scenes", "project": str(proj),
            "frontmatter": {"title": "Seq", "act_id": "act-1"},  # act-1 from fixture import
            "vault_path": vault
        })
        # Create a scene in this sequence
        create_handler({
            "entity_type": "scene", "slug": "scene-in-seq", "project": str(proj),
            "frontmatter": {"title": "Scene", "sequence_id": "seq-with-scenes", "act_id": "act-1"},
            "vault_path": vault
        })

        result = edit_handler({
            "action": "delete_entity",
            "target": {"entity_type": "sequence", "slug": "seq-with-scenes", "project": str(proj)},
            "summary": "Delete seq",
            "vault_path": vault
        })
        data = json.loads(result)
        assert "error" in data
        assert "structural" in data["error"].lower() or "scene" in data["error"].lower()

    def test_delete_character_cascades_arcs(self, db_project):
        """Deleting a character cascade-deletes all their arc beats."""
        proj, vault = db_project

        create_handler({
            "entity_type": "character", "slug": "cascade-char", "project": str(proj),
            "frontmatter": {"name": "Cascade", "story_role": "Minor", "one_sentence": "Test"},
            "vault_path": vault
        })
        for i in range(1, 4):
            create_handler({
                "entity_type": "arc", "slug": str(i), "project": str(proj),
                "frontmatter": {
                    "id": str(i), "character": "cascade-char",
                    "label": f"Beat {i}", "action": "a", "gap": "g",
                    "choice": "c", "shift": "s", "y": 0.0, "order": i,
                },
                "vault_path": vault
            })

        # Delete character
        result = edit_handler({
            "action": "delete_entity",
            "target": {"entity_type": "character", "slug": "cascade-char", "project": str(proj)},
            "summary": "Delete cascade-char",
            "vault_path": vault
        })
        assert json.loads(result)["success"] is True

        # All arcs gone
        result = json.loads(load_handler({"project": str(proj), "vault_path": vault}))
        ids = [r[0] for r in result["entities"]["rows"]]
        assert "cascade-char" not in ids
        for i in range(1, 4):
            assert f"cascade-char-{i}" not in ids, f"Arc {i} not cascade-deleted: {ids}"

    def test_reorder_visible_in_load(self, db_project):
        """Reorder scenes → story_load shows new order_key sequence."""
        proj, vault = db_project

        # Create a sequence with scenes
        create_handler({
            "entity_type": "act", "slug": "act-test", "project": str(proj),
            "frontmatter": {"title": "Test Act"}, "vault_path": vault
        })
        create_handler({
            "entity_type": "sequence", "slug": "seq-test", "project": str(proj),
            "frontmatter": {"title": "Test Seq", "act_id": "act-test"}, "vault_path": vault
        })
        for slug in ["scene-x", "scene-y", "scene-z"]:
            create_handler({
                "entity_type": "scene", "slug": slug, "project": str(proj),
                "frontmatter": {"title": f"Scene {slug[-1]}", "sequence_id": "seq-test", "act_id": "act-test"},
                "vault_path": vault
            })

        # Reorder: scene-z first
        result = edit_handler({
            "action": "reorder",
            "target": {"entity_type": "scene", "project": str(proj)},
            "order_context": {"ordered_ids": ["scene-z", "scene-x", "scene-y"]},
            "summary": "Reorder scenes",
            "vault_path": vault
        })
        assert json.loads(result)["success"] is True

        # Load shows new order
        result = json.loads(load_handler({"project": str(proj), "vault_path": vault}))
        entities = result["entities"]["rows"]
        scenes = [r for r in entities if r[1] == "scene" and r[0] in ("scene-x", "scene-y", "scene-z")]
        scenes_sorted = sorted(scenes, key=lambda r: r[5])  # order_key col
        assert [r[0] for r in scenes_sorted] == ["scene-z", "scene-x", "scene-y"]
        assert [r[5] for r in scenes_sorted] == [1, 2, 3]


class TestAppValidation:
    """App-level validation: scene act_id consistency, plot/arc refs."""

    def test_scene_mismatched_act_id_rejected(self, tmp_path):
        """Create scene with mismatched sequence.act_id vs scene.act_id → error."""
        create_handler({
            "entity_type": "act", "slug": "act-a", "project": str(tmp_path),
            "frontmatter": {"title": "Act A"}
        })
        create_handler({
            "entity_type": "act", "slug": "act-b", "project": str(tmp_path),
            "frontmatter": {"title": "Act B"}
        })
        create_handler({
            "entity_type": "sequence", "slug": "seq-1", "project": str(tmp_path),
            "frontmatter": {"title": "Seq 1", "act_id": "act-a"}
        })

        result = create_handler({
            "entity_type": "scene", "slug": "bad-scene", "project": str(tmp_path),
            "frontmatter": {"title": "Bad Scene", "sequence_id": "seq-1", "act_id": "act-b"}
        })
        data = json.loads(result)
        assert "error" in data
        assert "act" in data["error"].lower()

    def test_plot_unknown_character_rejected(self, tmp_path):
        """Create plot with non-existent character → error."""
        result = create_handler({
            "entity_type": "plot", "slug": "test-plot", "project": str(tmp_path),
            "frontmatter": {"name": "Test Plot", "characters": ["nonexistent-char"]}
        })
        data = json.loads(result)
        assert "error" in data
        assert "Character not found" in data["error"] or "nonexistent-char" in data["error"]

    def test_arc_unknown_character_rejected(self, tmp_path):
        """Create arc with non-existent character → error."""
        result = create_handler({
            "entity_type": "arc", "slug": "1", "project": str(tmp_path),
            "frontmatter": {
                "id": "1", "character": "nonexistent",
                "label": "Test", "action": "a", "gap": "g",
                "choice": "c", "shift": "s", "y": 0.0, "order": 1,
            }
        })
        data = json.loads(result)
        assert "error" in data
        assert "Character not found" in data["error"]

    def test_arc_unknown_scene_rejected(self, tmp_path):
        """Create arc with non-existent scene → error."""
        create_handler({
            "entity_type": "character", "slug": "kael", "project": str(tmp_path),
            "frontmatter": {"name": "Kael", "story_role": "Protagonist", "one_sentence": "Test"}
        })
        result = create_handler({
            "entity_type": "arc", "slug": "1", "project": str(tmp_path),
            "frontmatter": {
                "id": "1", "character": "kael", "scene": "nonexistent-scene",
                "label": "Test", "action": "a", "gap": "g",
                "choice": "c", "shift": "s", "y": 0.0, "order": 1,
            }
        })
        data = json.loads(result)
        assert "error" in data
        assert "Scene not found" in data["error"]