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

    def test_load_project_metadata(self, db_project):
        proj, vault = db_project
        result = json.loads(load_handler({"project": str(proj), "vault_path": vault}))
        assert result["project"]["name"] == "Save the Children"


class TestNestedStructure:
    """story_load returns nested acts/characters/plots/locations/worlds dicts."""

    def test_load_returns_nested_acts(self, db_project):
        """acts[] contains sequences[] contains scenes[]."""
        proj, vault = db_project
        result = json.loads(load_handler({"project": str(proj), "vault_path": vault}))
        assert "acts" in result
        assert isinstance(result["acts"], list)
        assert len(result["acts"]) > 0
        act = result["acts"][0]
        assert "sequences" in act
        assert isinstance(act["sequences"], list)
        if act["sequences"]:
            seq = act["sequences"][0]
            assert "scenes" in seq
            assert isinstance(seq["scenes"], list)

    def test_load_characters_keyed_by_slug(self, db_project):
        """characters is a list with explicit id field."""
        proj, vault = db_project
        result = json.loads(load_handler({"project": str(proj), "vault_path": vault}))
        assert "characters" in result
        assert isinstance(result["characters"], list)
        assert any(e["id"] == "kael" for e in result["characters"])

    def test_load_plots_keyed_by_slug(self, db_project):
        """plots is a list with explicit id field."""
        proj, vault = db_project
        result = json.loads(load_handler({"project": str(proj), "vault_path": vault}))
        assert "plots" in result
        assert isinstance(result["plots"], list)

    def test_load_locations_keyed_by_slug(self, db_project):
        """locations nested inside worlds, each with explicit id field."""
        proj, vault = db_project
        result = json.loads(load_handler({"project": str(proj), "vault_path": vault}))
        assert "worlds" in result
        assert isinstance(result["worlds"], list)
        # Locations are nested inside worlds
        all_locs = []
        for w in result["worlds"]:
            all_locs.extend(w.get("locations", []))
        assert len(all_locs) > 0
        assert all("id" in loc for loc in all_locs)

    def test_load_worlds_keyed_by_slug(self, db_project):
        """worlds is a list with explicit id field, contains locations."""
        proj, vault = db_project
        result = json.loads(load_handler({"project": str(proj), "vault_path": vault}))
        assert "worlds" in result
        assert isinstance(result["worlds"], list)
        assert all("id" in w for w in result["worlds"])
        # Each world has a locations array
        for w in result["worlds"]:
            assert "locations" in w

    def test_no_entities_key(self, db_project):
        """Old flat entities key is gone."""
        proj, vault = db_project
        result = json.loads(load_handler({"project": str(proj), "vault_path": vault}))
        assert "entities" not in result

    def test_no_relations_key(self, db_project):
        """Old flat relations key is gone."""
        proj, vault = db_project
        result = json.loads(load_handler({"project": str(proj), "vault_path": vault}))
        assert "relations" not in result

    def test_no_memory_key(self, db_project):
        """Old full-memory key is gone (replaced by memory_outline)."""
        proj, vault = db_project
        result = json.loads(load_handler({"project": str(proj), "vault_path": vault}))
        assert "memory" not in result
        assert "memory_outline" in result


class TestStubClassification:
    """Scene and arc beat stubs are correctly classified."""

    def test_scene_stub_has_only_id(self, db_project):
        """A planned scene with no dramatic_role is a stub: {id} only."""
        proj, vault = db_project
        result = json.loads(load_handler({"project": str(proj), "vault_path": vault}))
        # Verify stub mechanism: if a stub exists, it should be a compact object
        for act in result["acts"]:
            for seq in act.get("sequences", []):
                for scene in seq.get("scenes", []):
                    if isinstance(scene, dict) and "dramatic_role" not in scene:
                        assert "id" in scene
                        assert "status" not in scene or scene.get("status") == "planned"
        # Note: fixture has no stub scenes (all have dramatic_role + status),
        # so this test is vacuous here.

    def test_scene_full_has_dramatic_role(self, db_project):
        """A non-stub scene has dramatic_role."""
        proj, vault = db_project
        result = json.loads(load_handler({"project": str(proj), "vault_path": vault}))
        found_full = False
        for act in result["acts"]:
            for seq in act.get("sequences", []):
                for scene in seq.get("scenes", []):
                    if isinstance(scene, dict) and scene.get("dramatic_role"):
                        found_full = True
        assert found_full, "No full scenes found in fixture"

    def test_character_has_no_arc_array(self, db_project):
        """Character in load output has no arc array (retrieved via story_retrieve)."""
        proj, vault = db_project
        result = json.loads(load_handler({"project": str(proj), "vault_path": vault}))
        for char in result["characters"]:
            assert "arc" not in char


class TestEmbeddedCrossReferences:
    """Cross-references are embedded directly, not in a relations table."""

    def test_scene_has_chars(self, db_project):
        """scene.chars populated from character_scene relations."""
        proj, vault = db_project
        result = json.loads(load_handler({"project": str(proj), "vault_path": vault}))
        for act in result["acts"]:
            for seq in act.get("sequences", []):
                for scene in seq.get("scenes", []):
                    if isinstance(scene, dict) and scene.get("dramatic_role"):
                        # chars may be omitted when empty, but must be present for
                        # scenes that have characters assigned
                        if scene.get("chars"):
                            assert isinstance(scene["chars"], list)

    def test_scene_has_loc(self, db_project):
        """scene.loc populated from location_scene relation."""
        proj, vault = db_project
        result = json.loads(load_handler({"project": str(proj), "vault_path": vault}))
        for act in result["acts"]:
            for seq in act.get("sequences", []):
                for scene in seq.get("scenes", []):
                    if isinstance(scene, dict) and scene.get("dramatic_role"):
                        # loc may be omitted when unassigned
                        if scene.get("loc"):
                            assert isinstance(scene["loc"], str)

    def test_character_has_rel(self, db_project):
        """character.relationships populated from relationship entities."""
        proj, vault = db_project
        result = json.loads(load_handler({"project": str(proj), "vault_path": vault}))
        for char in result["characters"]:
            if "relationships" in char:
                for rel in char["relationships"]:
                    assert "with" in rel
                    assert "label" in rel
                    assert "type" in rel

    def test_plot_has_setups(self, db_project):
        """plot.setups populated from plot_setup relations."""
        proj, vault = db_project
        result = json.loads(load_handler({"project": str(proj), "vault_path": vault}))
        for plot in result["plots"]:
            if "setups" in plot:
                assert isinstance(plot["setups"], list)


class TestSectionsPerEntity:
    """Sections are not included in load output (token budget)."""

    def test_character_has_no_sections_key(self, db_project):
        """Character in load output has no sections key."""
        proj, vault = db_project
        result = json.loads(load_handler({"project": str(proj), "vault_path": vault}))
        kael = next(e for e in result["characters"] if e["id"] == "kael")
        assert "sections" not in kael

    def test_all_entities_have_no_sections_key(self, db_project):
        """No entity type in load output has a sections key."""
        proj, vault = db_project
        result = json.loads(load_handler({"project": str(proj), "vault_path": vault}))
        for char in result["characters"]:
            assert "sections" not in char
        for plot in result["plots"]:
            assert "sections" not in plot
        for w in result["worlds"]:
            assert "sections" not in w
            for loc in w.get("locations", []):
                assert "sections" not in loc
        for act in result["acts"]:
            assert "sections" not in act
            for seq in act.get("sequences", []):
                assert "sections" not in seq
                for scene in seq.get("scenes", []):
                    if isinstance(scene, dict):
                        assert "sections" not in scene


class TestUnfilledInverted:
    """Unfilled is inverted: {field: [entity_ids]}, stubs excluded."""

    def test_unfilled_inverted_shape(self, db_project):
        """unfilled maps field names to lists of entity slugs."""
        proj, vault = db_project
        result = json.loads(load_handler({"project": str(proj), "vault_path": vault}))
        unfilled = result["unfilled"]
        assert isinstance(unfilled, dict)
        # Each value should be a list
        for field, entities in unfilled.items():
            assert isinstance(entities, list), f"unfilled[{field}] is not a list"

    def test_unfilled_excludes_stubs(self, db_project):
        """Stub entities do not appear in unfilled lists."""
        proj, vault = db_project
        result = json.loads(load_handler({"project": str(proj), "vault_path": vault}))
        unfilled = result["unfilled"]
        # Collect all entity slugs mentioned in unfilled
        all_unfilled = set()
        for entities in unfilled.values():
            all_unfilled.update(entities)
        # No stub scene slug should appear
        for act in result["acts"]:
            for seq in act.get("sequences", []):
                for scene in seq.get("scenes", []):
                    if isinstance(scene, dict) and "dramatic_role" not in scene:
                        assert scene["id"] not in all_unfilled, f"Stub scene {scene['id']} in unfilled"

    def test_character_goals_unfilled(self, db_project):
        """New character has goals_short/goals_long unfilled."""
        proj, vault = db_project
        # Create a new character
        create_handler({
            "entity_type": "character", "slug": "unfilled-test",
            "project": str(proj),
            "frontmatter": {"name": "Unfilled", "story_role": "Minor"},
            "vault_path": vault
        })
        result = json.loads(load_handler({"project": str(proj), "vault_path": vault}))
        unfilled = result["unfilled"]
        # goals_short should list the new character
        assert "goals_short" in unfilled
        assert "unfilled-test" in unfilled["goals_short"]

    def test_unfilled_excludes_status_booleans_numbers(self, db_project):
        """unfilled must not contain status, booleans, or numbers — only string/placeholder fields."""
        proj, vault = db_project
        result = json.loads(load_handler({"project": str(proj), "vault_path": vault}))
        unfilled = result["unfilled"]
        # No boolean fields
        assert "is_crisis" not in unfilled
        assert "is_climax" not in unfilled
        assert "arc_complete" not in unfilled
        # No numeric fields
        assert "y" not in unfilled
        assert "act_count" not in unfilled
        # No status fields
        assert "status" not in unfilled
        # String placeholder fields should still be there
        assert "goals_short" in unfilled


class TestConfirmationFormat:
    """Confirmation string matches new format."""

    def test_confirmation_format(self, db_project):
        """Confirmation: 'Loaded <name> — N scenes (M developed), ...'"""
        proj, vault = db_project
        result = json.loads(load_handler({"project": str(proj), "vault_path": vault}))
        conf = result["confirmation"]
        assert conf.startswith("Loaded Save the Children — ")
        assert "scenes" in conf
        assert "developed" in conf
        assert "sequences" in conf
        assert "acts" in conf
        assert "characters" in conf
        assert "locations" in conf
        assert "plots" in conf
        assert "worlds" in conf


class TestTokenBudget:
    def test_load_under_8_5k_tokens(self, db_project):
        proj, vault = db_project
        result = json.loads(load_handler({"project": str(proj), "vault_path": vault}))
        data = json.dumps(result)
        est_tokens = len(data) // 4
        assert est_tokens < 8500, f"Estimated tokens: {est_tokens}"


class TestNavigationalQueries:
    """5 navigational queries answerable from nested structure alone."""

    def test_plot_to_scenes(self, db_project):
        """Which scenes does 'the-resistance' plot touch?"""
        proj, vault = db_project
        result = json.loads(load_handler({"project": str(proj), "vault_path": vault}))
        plot = next(p for p in result["plots"] if p["id"] == "the-resistance")
        scenes = (
            plot.get("setups", [])
            + plot.get("crisis", [])
            + plot.get("climax", [])
            + plot.get("payoffs", [])
        )
        assert len(scenes) > 0

    def test_character_to_scenes(self, db_project):
        """What scenes has Kael been in?"""
        proj, vault = db_project
        result = json.loads(load_handler({"project": str(proj), "vault_path": vault}))
        kael = next(e for e in result["characters"] if e["id"] == "kael")
        # Navigate: find scenes where kael is in chars
        kael_scenes = []
        for act in result["acts"]:
            for seq in act.get("sequences", []):
                for scene in seq.get("scenes", []):
                    if isinstance(scene, dict) and "kael" in scene.get("chars", []):
                        kael_scenes.append(scene["id"])
        assert "central-room-day" in kael_scenes

    def test_scene_to_plots(self, db_project):
        """Which plots touch central-room-day?"""
        proj, vault = db_project
        result = json.loads(load_handler({"project": str(proj), "vault_path": vault}))
        touching = []
        for plot in result["plots"]:
            all_scenes = (
                plot.get("setups", [])
                + plot.get("crisis", [])
                + plot.get("climax", [])
                + plot.get("payoffs", [])
            )
            if "central-room-day" in all_scenes:
                touching.append(plot["id"])
        assert len(touching) > 0

    def test_structure_hierarchy(self, db_project):
        """act→sequence→scene hierarchy is directly visible in nesting."""
        proj, vault = db_project
        result = json.loads(load_handler({"project": str(proj), "vault_path": vault}))
        acts = result["acts"]
        assert len(acts) > 0
        for act in acts:
            assert "sequences" in act
            for seq in act["sequences"]:
                assert "scenes" in seq
                assert len(seq["scenes"]) > 0


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
            "entity_type": "arc_beat",
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

    def test_dashboard_has_relationships(self, db_project):
        """Dashboard includes relationship entities."""
        proj, vault = db_project
        result = json.loads(dashboard_handler({
            "project": str(proj),
            "vault_path": vault
        }))
        assert result["success"] is True
        html = Path(result["dashboard_url"].replace("file://", "")).read_text()
        assert "relationships" in html


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
