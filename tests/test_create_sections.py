"""story_create — the entry point for every write.

Two defects worth pinning:

1. Prose passed at create time was silently dropped. The tool created every
   standard section empty and ignored the argument entirely, so the natural
   "create this character and write who they are" call lost the prose and
   reported success.
2. An unknown entity_type was accepted. The schema enum is advisory — an LLM
   can pass anything — and an unknown type was inserted as a row, surfacing much
   later as a mystery.
"""
import json
import sqlite3

import pytest

from tools.story_create import handler as create_handler
from tools.story_retrieve import handler as retrieve_handler


@pytest.fixture
def vault(tmp_path):
    v = tmp_path / "v"
    (v / "projects").mkdir(parents=True)
    r = json.loads(create_handler(
        {"entity_type": "project", "slug": "stc", "frontmatter": {"name": "STC", "logline": "L"}},
        vault_path=str(v)))
    assert r["success"] is True
    return v


def _create(vault, **args):
    args.setdefault("project", "stc")
    return json.loads(create_handler(args, vault_path=str(vault)))


def _sections(vault, entity_type, entity_id):
    r = json.loads(retrieve_handler(
        {"project": "stc", "entity_type": entity_type, "id": [entity_id],
         "sections": ["all"]}, vault_path=str(vault)))
    return r["entities"][0]["sections"]


def _exists(vault, entity_id):
    conn = sqlite3.connect(str(vault / "projects" / "stc" / ".story" / "story.db"))
    try:
        return bool(conn.execute("SELECT 1 FROM entities WHERE id=?", (entity_id,)).fetchone())
    finally:
        conn.close()


class TestSectionsAtCreate:
    def test_prose_is_written(self, vault):
        _create(vault, entity_type="character", slug="nova",
                frontmatter={"name": "Nova", "one_sentence": "X"},
                sections={"Identity": "A courier who talks too much.", "Notes": "Loves rain."})
        got = _sections(vault, "character", "nova")
        assert got["Identity"] == "A courier who talks too much."
        assert got["Notes"] == "Loves rain."

    def test_standard_sections_still_created_empty(self, vault):
        """The template is not replaced by what was supplied — it is filled."""
        _create(vault, entity_type="character", slug="nova",
                frontmatter={"name": "Nova"}, sections={"Identity": "Wry."})
        got = _sections(vault, "character", "nova")
        assert got["Desires"] == ""
        assert got["Background"] == ""

    def test_nonstandard_heading_is_added(self, vault):
        _create(vault, entity_type="act", slug="act-1", frontmatter={"title": "Act One"})
        _create(vault, entity_type="sequence", slug="seq-1",
                frontmatter={"title": "Seq One", "act_id": "act-1"})
        _create(vault, entity_type="scene", slug="s1",
                frontmatter={"title": "S1", "sequence_id": "seq-1"},
                sections={"Cold Open": "Went straight to it."})
        assert _sections(vault, "scene", "s1")["Cold Open"] == "Went straight to it."

    def test_no_sections_argument_still_works(self, vault):
        assert _create(vault, entity_type="character", slug="nova",
                       frontmatter={"name": "Nova"})["success"] is True
        assert _sections(vault, "character", "nova")["Identity"] == ""

    def test_non_dict_sections_is_rejected(self, vault):
        r = _create(vault, entity_type="character", slug="nova",
                    frontmatter={"name": "Nova"}, sections=["Personality"])
        assert "must be an object" in r["error"]
        assert not _exists(vault, "nova"), "a rejected call must not leave a half-made entity"


class TestUnknownType:
    def test_rejected(self, vault):
        r = _create(vault, entity_type="dragon", slug="smaug", frontmatter={"name": "S"})
        assert r["error"] == "Unknown entity_type: dragon"
        assert "character" in r["valid_types"]

    def test_nothing_was_inserted(self, vault):
        _create(vault, entity_type="dragon", slug="smaug", frontmatter={"name": "S"})
        assert not _exists(vault, "smaug")

    def test_ten_valid_types_still_pass(self, vault):
        for entity_type in ("character", "world", "location", "plot", "relationship"):
            assert _create(vault, entity_type=entity_type, slug=f"e-{entity_type}",
                           frontmatter={"name": "N"})["success"] is True


class TestIdUniqueness:
    """Ids are global across types, so the two failure cases need different advice."""

    def test_same_type_points_at_story_edit(self, vault):
        _create(vault, entity_type="character", slug="kael", frontmatter={"name": "K"})
        r = _create(vault, entity_type="character", slug="kael", frontmatter={"name": "K"})
        assert r["error"] == "Entity already exists: character/kael"
        assert "story_edit" in r["hint"]

    def test_cross_type_names_the_occupant(self, vault):
        _create(vault, entity_type="character", slug="kael", frontmatter={"name": "K"})
        r = _create(vault, entity_type="world", slug="kael", frontmatter={"name": "K"})
        assert "already used by a character" in r["error"]
        assert "unique across all types" in r["hint"]


class TestValidationBeforeInsert:
    def test_bad_parent_creates_nothing(self, vault):
        r = _create(vault, entity_type="scene", slug="s1",
                    frontmatter={"title": "S1", "sequence_id": "ghost-seq"})
        assert r["error"] == "Sequence not found: ghost-seq"
        assert not _exists(vault, "s1")

    @pytest.mark.parametrize("slug", ["", "   ", "a/b", "../escape", "with space"])
    def test_bad_slug_rejected(self, vault, slug):
        r = _create(vault, entity_type="character", slug=slug, frontmatter={"name": "N"})
        assert "alphanumeric" in r["error"]
        assert not _exists(vault, slug.strip())
