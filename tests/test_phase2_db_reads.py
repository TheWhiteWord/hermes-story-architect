"""Tests for Phase 2: DB-backed read paths (shadow reads)."""
import json
import shutil
import tempfile
from pathlib import Path

import pytest

from tools.story_import import handler as import_handler
from tools.story_load import handler as load_handler
from tools.story_retrieve import handler as retrieve_handler
from tools.story_search import handler as search_handler
from tools.story_dashboard import handler as dashboard_handler
from tools.story_create import handler as create_handler
from tools.story_edit import handler as edit_handler


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


class TestStoryLoadDB:
    """story_load reads from DB when story.db exists."""

    def test_load_returns_column_format(self, db_project):
        proj, vault = db_project
        result = json.loads(load_handler({"project": str(proj), "vault_path": vault}))
        assert result["loaded"] is True
        assert "project" in result
        assert "entities" in result
        assert "relations" in result
        assert "cols" in result["entities"]
        assert "rows" in result["entities"]
        assert "cols" in result["relations"]
        assert "rows" in result["relations"]

    def test_load_no_derived_arrays(self, db_project):
        proj, vault = db_project
        result = json.loads(load_handler({"project": str(proj), "vault_path": vault}))
        data = json.dumps(result)
        # No enriched arrays in the response
        assert '"scenes"' not in data or '"scenes": []' in data
        assert '"plots"' not in data or '"plots": []' in data
        assert "sequences_list" not in data
        assert "arc_beats_list" not in data

    def test_load_no_sections_list(self, db_project):
        proj, vault = db_project
        result = json.loads(load_handler({"project": str(proj), "vault_path": vault}))
        # entities rows should not have a "sections" field
        for row in result["entities"]["rows"]:
            assert "sections" not in row

    def test_load_relations_completeness(self, db_project):
        proj, vault = db_project
        result = json.loads(load_handler({"project": str(proj), "vault_path": vault}))
        relations = result["relations"]["rows"]
        # Check key relation types present
        kinds = {r[2] for r in relations}
        assert "character_scene" in kinds
        assert "plot_setup" in kinds
        # arc_beat relations no longer exist — beats are derived from arc entities
        assert "location_scene" in kinds

    def test_load_memory_included(self, db_project):
        proj, vault = db_project
        result = json.loads(load_handler({"project": str(proj), "vault_path": vault}))
        assert "memory" in result

    def test_load_project_metadata(self, db_project):
        proj, vault = db_project
        result = json.loads(load_handler({"project": str(proj), "vault_path": vault}))
        assert result["project"]["name"] == "Save the Children"


class TestStoryRetrieveDB:
    """story_retrieve reads from DB when story.db exists."""

    def test_retrieve_character_sections(self, db_project):
        proj, vault = db_project
        result = json.loads(retrieve_handler({
            "project": str(proj),
            "entity_type": "character",
            "slug": "kael",
            "sections": ["Personality", "Background"],
            "vault_path": vault
        }))
        assert result["entity_type"] == "character"
        assert result["slug"] == "kael"
        assert "Personality" in result["sections"]
        assert "Background" in result["sections"]

    def test_retrieve_all_sections(self, db_project):
        proj, vault = db_project
        result = json.loads(retrieve_handler({
            "project": str(proj),
            "entity_type": "character",
            "slug": "kael",
            "sections": ["all"],
            "vault_path": vault
        }))
        assert "content" in result
        assert "sections" in result
        assert "Personality" in result["sections"]

    def test_retrieve_arc_beat(self, db_project):
        proj, vault = db_project
        result = json.loads(retrieve_handler({
            "project": str(proj),
            "entity_type": "arc",
            "slug": "kael-1",
            "sections": ["Action"],
            "vault_path": vault
        }))
        assert result["slug"] == "kael-1"
        assert "Action" in result["sections"]


class TestStorySearchDB:
    """story_search uses FTS5 when story.db exists."""

    def test_search_arc_beat_content(self, db_project):
        """Conflict 3: FTS5 finds content in arc beats (old glob missed them)."""
        proj, vault = db_project
        result = json.loads(search_handler({
            "project": str(proj),
            "query": "First Doubt",
            "vault_path": vault
        }))
        assert result["total"] > 0
        # Found in an arc beat entity
        entity_ids = [r["entity_id"] for r in result["results"]]
        assert any("kael" in eid for eid in entity_ids)

    def test_search_scene_content(self, db_project):
        proj, vault = db_project
        result = json.loads(search_handler({
            "project": str(proj),
            "query": "KAEL",
            "vault_path": vault
        }))
        assert result["total"] > 0

    def test_search_no_match(self, db_project):
        proj, vault = db_project
        result = json.loads(search_handler({
            "project": str(proj),
            "query": "xyznonexistent123",
            "vault_path": vault
        }))
        assert result["total"] == 0


class TestStoryDashboardDB:
    """story_dashboard uses DB path when story.db exists."""

    def test_dashboard_all_injections(self, db_project):
        proj, vault = db_project
        result = json.loads(dashboard_handler({
            "project": str(proj),
            "vault_path": vault
        }))
        assert result["success"] is True
        html = Path(result["dashboard_url"].replace("file://", "")).read_text()
        assert "__STORY_DATA__" in html
        assert "__SECTIONS__" in html
        assert "__SCREENPLAY_STATS__" in html
        assert "__STRUCTURAL_STATS__" in html


class TestAutoReimport:
    """story_edit/story_create auto-reimport to DB in Phase 2."""

    def test_create_entity_syncs_to_db(self, db_project):
        proj, vault = db_project
        # Create a new character
        result = json.loads(create_handler({
            "entity_type": "character",
            "slug": "test-new-char",
            "project": str(proj),
            "frontmatter": {"name": "Test New Char", "story_role": "Supporting"},
            "vault_path": vault
        }))
        assert result["success"] is True

        # DB should now have the new entity
        from core.db import get_db
        import sqlite3
        conn = sqlite3.connect(str(proj / ".story" / "story.db"))
        row = conn.execute(
            "SELECT id FROM entities WHERE id='test-new-char'"
        ).fetchone()
        conn.close()
        assert row is not None

    def test_edit_entity_syncs_to_db(self, db_project):
        proj, vault = db_project
        # Edit kael's one_sentence
        result = json.loads(edit_handler({
            "action": "edit_note",
            "target": {"entity_type": "character", "slug": "kael", "project": str(proj)},
            "data": {"one_sentence": "Updated description."},
            "summary": "Update one_sentence",
            "vault_path": vault
        }))
        assert result["success"] is True

        # DB should reflect the change
        from core.db import get_db
        import sqlite3
        conn = sqlite3.connect(str(proj / ".story" / "story.db"))
        row = conn.execute(
            "SELECT one_sentence FROM entities WHERE id='kael'"
        ).fetchone()
        conn.close()
        assert row[0] == "Updated description."


class TestTokenBudget:
    """story_load response token budget."""

    def test_load_under_5k_tokens(self, db_project):
        proj, vault = db_project
        result = json.loads(load_handler({"project": str(proj), "vault_path": vault}))
        data = json.dumps(result)
        # Rough token estimate: ~4 chars per token for JSON
        est_tokens = len(data) // 4
        assert est_tokens < 5000, f"Estimated tokens: {est_tokens}"


class TestNavigationalQueries:
    """5 navigational queries answerable from story_load summary alone."""

    def test_plot_to_scenes(self, db_project):
        """Which scenes does 'the-resistance' plot touch?"""
        proj, vault = db_project
        result = json.loads(load_handler({"project": str(proj), "vault_path": vault}))
        relations = result["relations"]["rows"]
        scenes = [r[1] for r in relations if r[0] == "the-resistance" and r[2].startswith("plot_")]
        assert len(scenes) > 0

    def test_character_to_scenes(self, db_project):
        """What scenes has Kael been in?"""
        proj, vault = db_project
        result = json.loads(load_handler({"project": str(proj), "vault_path": vault}))
        relations = result["relations"]["rows"]
        scenes = [r[1] for r in relations if r[0] == "kael" and r[2] == "character_scene"]
        assert "central-room-day" in scenes

    def test_scene_to_plots(self, db_project):
        """Which plot moments occur in central-room-day?"""
        proj, vault = db_project
        result = json.loads(load_handler({"project": str(proj), "vault_path": vault}))
        relations = result["relations"]["rows"]
        plots = [r[0] for r in relations if r[1] == "central-room-day" and r[2].startswith("plot_")]
        assert len(plots) > 0

    def test_scene_to_arc_beats(self, db_project):
        """What arc beats does central-room-day host?"""
        proj, vault = db_project
        result = json.loads(load_handler({"project": str(proj), "vault_path": vault}))
        entities = result["entities"]["rows"]
        # Arc beats are derived from arc entities, not relations
        beats = [r[0] for r in entities if r[1] == "arc" and r[8].get("scene") == "central-room-day"]
        assert len(beats) > 0

    def test_structure_hierarchy(self, db_project):
        """act→sequence→scene hierarchy reconstructable from parent_id + order_key."""
        proj, vault = db_project
        result = json.loads(load_handler({"project": str(proj), "vault_path": vault}))
        entities = result["entities"]["rows"]
        # Build lookup
        by_id = {r[0]: r for r in entities}
        # Find act → sequence → scene
        acts = [r for r in entities if r[1] == "act"]
        assert len(acts) > 0
        for act in acts:
            seqs = [r for r in entities if r[1] == "sequence" and r[6] == act[0]]
            for seq in seqs:
                scenes = [r for r in entities if r[1] == "scene" and r[6] == seq[0]]
                assert len(scenes) > 0
