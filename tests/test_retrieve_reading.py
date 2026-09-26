"""story_retrieve — the three defects fixed, pinned.

1. A bad id said "Database not found. Run story_import first." — pointing the
   agent at the one tool that destroys work. Wrong slug and wrong type both
   produced it.
2. Relation-backed fields (plot beats, scene characters) were unreachable, so an
   agent could not see that a plot's crisis was empty.
3. One entity per call.
"""
import json
import shutil

import pytest

from tools.story_create import handler as create_handler
from tools.story_import import handler as import_handler
from tools.story_retrieve import handler as retrieve_handler


def _get(project, vault, **args):
    args["project"] = str(project)
    args["vault_path"] = str(vault)
    return json.loads(retrieve_handler(args))


@pytest.fixture
def db(fixture_path, tmp_path):
    """Imported fixture — read-only operations only."""
    vault = tmp_path / "v"
    proj = vault / "save-the-children"
    proj.parent.mkdir(parents=True)
    shutil.copytree(str(fixture_path), str(proj))
    import_handler({"project": str(proj), "confirm": True, "vault_path": str(vault)})
    return proj, vault


class TestBadIdIsNotAnImportProblem:
    """The old error sent the agent to a destructive tool to fix a typo."""

    def test_typo_in_slug(self, db):
        proj, vault = db
        r = _get(proj, vault, entity_type="character", id=["kael-vale"], sections=["all"])
        assert "No character with id 'kael-vale'" in r["not_found"][0]["error"]
        assert "story_load" in r["not_found"][0]["error"]
        assert "import" not in r["not_found"][0]["error"].lower()

    def test_wrong_entity_type(self, db):
        """A valid id, the wrong type — the old code reported a missing database."""
        proj, vault = db
        r = _get(proj, vault, entity_type="plot", id=["kael"], sections=["all"])
        assert "No plot with id 'kael'" in r["not_found"][0]["error"]
        assert r["entities"] == []

    def test_holds_no_such_database(self, db):
        proj, vault = db
        r = _get(proj, vault, entity_type="character", id=["nope"], sections=["all"])
        assert "Database not found" not in json.dumps(r)

    def test_good_id_still_works_alongside_a_bad_one(self, db):
        proj, vault = db
        r = _get(proj, vault, entity_type="character", id=["kael", "nope"], sections=["all"])
        assert [e["id"] for e in r["entities"]] == ["kael"]
        assert r["not_found"][0]["id"] == "nope"

    def test_missing_database_still_says_so(self, fixture_path, tmp_path):
        """The real 'no database' case keeps its message."""
        vault = tmp_path / "v"
        proj = vault / "p"
        proj.parent.mkdir(parents=True)
        shutil.copytree(str(fixture_path), str(proj))
        (proj / ".story" / "story.db").unlink()
        r = _get(proj, vault, entity_type="character", id=["kael"], sections=["all"])
        assert r["error"] == "Database not found. Run story_import first."


class TestRelationBackedFields:
    def test_plot_beats_are_readable(self, db):
        proj, vault = db
        r = _get(proj, vault, entity_type="plot", id=["the-resistance"],
                  fields=["setups", "crisis", "climax", "payoffs"])
        f = r["entities"][0]["fields"]
        assert f["setups"], "plot setups are stored as relations and were unreachable"
        assert f["setups"][0]["scene_id"]
        assert "description" in f["setups"][0]

    def test_scene_characters_are_readable(self, db):
        proj, vault = db
        r = _get(proj, vault, entity_type="scene", id=["central-room-day"],
                  fields=["characters"])
        assert r["entities"][0]["fields"]["characters"]

    def test_empty_beats_show_as_empty_not_missing(self, db):
        """The point of the fix: an unset crisis must read as empty."""
        proj, vault = db
        r = _get(proj, vault, entity_type="plot", id=["the-resistance"],
                  fields=["crisis"], sections=[])
        assert r["entities"][0]["fields"]["crisis"] == []
        assert "crisis" in r["entities"][0]["unfilled_fields"]


class TestSelection:
    def test_sections_subset(self, db):
        proj, vault = db
        r = _get(proj, vault, entity_type="character", id=["kael"], sections=["Personality"])
        assert list(r["entities"][0]["sections"]) == ["Personality"]

    def test_missing_section_is_reported_not_silent(self, db):
        proj, vault = db
        r = _get(proj, vault, entity_type="character", id=["kael"], sections=["Nowhere"])
        entity = r["entities"][0]
        assert entity["sections"]["Nowhere"] is None
        assert entity["sections_not_found"] == ["Nowhere"]
        assert "Personality" in entity["available_sections"]

    def test_fields_only(self, db):
        proj, vault = db
        r = _get(proj, vault, entity_type="character", id=["kael"], fields=["one_sentence"])
        assert "one_sentence" in r["entities"][0]["fields"]
        assert "sections" not in r["entities"][0]

    def test_sections_and_fields_together(self, db):
        proj, vault = db
        r = _get(proj, vault, entity_type="character", id=["kael"],
                  fields=["story_role"], sections=["Personality"])
        entity = r["entities"][0]
        assert entity["fields"]["story_role"]
        assert entity["sections"]["Personality"] is not None

    def test_asking_for_nothing_is_an_error(self, db):
        """Otherwise a call returns an empty entity and the agent assumes it is empty."""
        proj, vault = db
        r = _get(proj, vault, entity_type="character", id=["kael"])
        assert "Nothing requested" in r["error"]

    def test_computed_fields_excluded_from_all(self, db):
        proj, vault = db
        r = _get(proj, vault, entity_type="character", id=["kael"], fields=["all"], sections=["all"])
        assert "entity_type" not in r["entities"][0]["fields"]


class TestBatchAndIds:
    def test_several_ids_in_one_call(self, db):
        proj, vault = db
        r = _get(proj, vault, entity_type="character", id=["kael", "mira"],
                  sections=["Personality"])
        assert [e["id"] for e in r["entities"]] == ["kael", "mira"]

    def test_bare_string_is_tolerated(self, db):
        proj, vault = db
        r = _get(proj, vault, entity_type="character", id="kael", sections=["Personality"])
        assert r["entities"][0]["id"] == "kael"

    def test_arc_beat_suffix_resolves(self, db):
        """Beats are keyed `{character}-{beat}`; the beat part alone is enough."""
        proj, vault = db
        r = _get(proj, vault, entity_type="arc_beat", id=["1"], sections=["Action"])
        assert r["entities"][0]["id"].endswith("-1")

    def test_arc_beat_full_key_resolves(self, db):
        proj, vault = db
        r = _get(proj, vault, entity_type="arc_beat", id=["kael-1"], sections=["Action"])
        assert r["entities"][0]["id"] == "kael-1"
