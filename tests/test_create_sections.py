"""core.writes.create_entity — the entry point for every write.

Two defects worth pinning:

1. Prose passed at create time was silently dropped. The write created every
   standard section empty and ignored the argument entirely, so the natural
   "create this character and write who they are" call lost the prose and
   reported success.
2. An unknown entity_type was accepted. The schema enum is advisory — an LLM
   can pass anything — and an unknown type was inserted as a row, surfacing much
   later as a mystery.

The second point is also why a rejected call must leave nothing behind: a
half-made entity is worse than no entity, because the next call finds it there.
"""
import json
import sqlite3

import pytest

from core.writes import create_entity, create_project
from tools.story_retrieve import handler as retrieve_handler


@pytest.fixture
def vault(tmp_path):
    v = tmp_path / "v"
    (v / "projects").mkdir(parents=True)
    assert create_project("stc", {"name": "STC", "logline": "L"}, v)["success"] is True
    return v


def _project(vault):
    return vault / "projects" / "stc"


def _create(vault, entity_type, slug, frontmatter=None, sections=None):
    return create_entity(_project(vault), entity_type, slug,
                         frontmatter if frontmatter is not None else {}, sections)


def _sections(vault, entity_type, entity_id):
    r = json.loads(retrieve_handler(
        {"project": "stc", "entity_type": entity_type, "id": [entity_id],
         "sections": ["all"]}, root_path=str(vault)))
    return r["entities"][0]["sections"]


def _exists(vault, entity_id):
    conn = sqlite3.connect(str(_project(vault) / ".story" / "story.db"))
    try:
        return bool(conn.execute("SELECT 1 FROM entities WHERE id=?", (entity_id,)).fetchone())
    finally:
        conn.close()


class TestSectionsAtCreate:
    def test_prose_is_written(self, vault):
        _create(vault, "character", "nova",
                {"name": "Nova", "one_sentence": "X"},
                {"Identity": "A courier who talks too much.", "Notes": "Loves rain."})
        got = _sections(vault, "character", "nova")
        assert got["Identity"] == "A courier who talks too much."
        assert got["Notes"] == "Loves rain."

    def test_standard_sections_still_created_empty(self, vault):
        """The template is not replaced by what was supplied — it is filled."""
        _create(vault, "character", "nova", {"name": "Nova"}, {"Identity": "Wry."})
        got = _sections(vault, "character", "nova")
        assert got["Desires"] == ""
        assert got["Background"] == ""

    def test_nonstandard_heading_is_rejected(self, vault):
        """The section set is closed on the create path as well as the edit
        path. It was not: a create accepted a heading the edit then refused, so
        the same name was valid or invalid depending on which call carried it."""
        _create(vault, "act", "act-1", {"title": "Act One"})
        _create(vault, "sequence", "seq-1", {"title": "Seq One", "act_id": "act-1"})
        with pytest.raises(ValueError, match="closed"):
            _create(vault, "scene", "s1", {"title": "S1", "sequence_id": "seq-1"},
                    {"Cold Open": "Went straight to it."})
        assert not _exists(vault, "s1"), "a rejected call must not leave a half-made entity"

    def test_no_sections_argument_still_works(self, vault):
        assert _create(vault, "character", "nova", {"name": "Nova"})["success"] is True
        assert _sections(vault, "character", "nova")["Identity"] == ""

    def test_non_dict_sections_is_rejected(self, vault):
        with pytest.raises(ValueError, match="must be an object"):
            _create(vault, "character", "nova", {"name": "Nova"}, ["Personality"])
        assert not _exists(vault, "nova"), "a rejected call must not leave a half-made entity"


class TestUnknownType:
    def test_rejected_and_names_the_valid_types(self, vault):
        """The caller has to be able to correct itself, so the valid set travels
        with the failure rather than the model retrying blind."""
        with pytest.raises(ValueError) as exc:
            _create(vault, "dragon", "smaug", {"name": "S"})
        assert "Unknown entity_type: dragon" in str(exc.value)
        assert "character" in str(exc.value)

    def test_nothing_was_inserted(self, vault):
        with pytest.raises(ValueError):
            _create(vault, "dragon", "smaug", {"name": "S"})
        assert not _exists(vault, "smaug")

    def test_valid_types_still_pass(self, vault):
        for entity_type in ("character", "world", "location", "plot", "relationship"):
            assert _create(vault, entity_type, f"e-{entity_type}",
                           {"name": "N"})["success"] is True


class TestUnknownField:
    """An unrecognised key was dropped by create and refused by edit.

    The visible symptom: `{"goals": {"short": ..., "long": ...}}` created a
    character and reported success, with the goal simply not there — and the
    schema's own description used to advertise that shape. Fields are flat.
    """

    def test_nested_goals_is_rejected(self, vault):
        with pytest.raises(ValueError, match="flat"):
            _create(vault, "character", "nested",
                    {"name": "N", "one_sentence": "X",
                     "goals": {"short": "Stay.", "long": "Survive."}})
        assert not _exists(vault, "nested"), "a rejected call must not leave a half-made entity"

    def test_error_names_the_offending_key_and_the_flat_ones(self, vault):
        with pytest.raises(ValueError) as exc:
            _create(vault, "character", "n2", {"name": "N", "goals": {"short": "a"}})
        message = str(exc.value)
        assert "goals" in message
        assert "goals_short" in message and "goals_long" in message

    def test_flat_goals_are_stored(self, vault):
        _create(vault, "character", "flat",
                {"name": "F", "one_sentence": "X",
                 "goals_short": "Stay.", "goals_long": "Survive."})
        sections = _sections(vault, "character", "flat")
        assert sections  # the entity exists and reads back
        r = json.loads(retrieve_handler(
            {"project": "stc", "entity_type": "character", "id": ["flat"],
             "fields": ["goals_short", "goals_long"]}, root_path=str(vault)))
        fields = r["entities"][0]["fields"]
        assert fields["goals_short"] == "Stay."
        assert fields["goals_long"] == "Survive."

    def test_the_schema_does_not_advertise_a_nested_form(self, vault):
        """The description is what an agent reads before writing. It once said
        "nested goals.short also accepted", which nothing implemented."""
        from core.constants import ENTITY_SCHEMAS
        for field in ("goals_short", "goals_long"):
            assert "nested" not in ENTITY_SCHEMAS["character"][field]["description"]

    def test_every_valid_field_of_every_type_is_accepted(self, vault):
        """A guard that rejects real fields is worse than no guard."""
        from core.constants import ENTITY_SCHEMAS
        from core.entity import ENTITY_COLUMN_MAP, relation_fields
        rejected = []
        for entity_type, schema in ENTITY_SCHEMAS.items():
            if entity_type == "project":
                continue
            keys = [k for k, m in schema.items() if not m.get("computed")]
            keys += list(relation_fields(entity_type))
            keys += list(ENTITY_COLUMN_MAP.get(entity_type, {}))
            for key in keys:
                slug = f"probe-{entity_type}-{key}"
                try:
                    _create(vault, entity_type, slug, {key: "PROBE"})
                except ValueError as e:
                    if "Unrecognised" in str(e):
                        rejected.append(f"{entity_type}.{key}: {e}")
        assert not rejected, f"valid fields wrongly rejected: {rejected}"


class TestIdUniqueness:
    """Ids are global across types, so the two failure cases need different advice."""

    def test_same_type_says_to_edit_instead(self, vault):
        _create(vault, "character", "kael", {"name": "K"})
        with pytest.raises(ValueError, match="Entity already exists: character/kael"):
            _create(vault, "character", "kael", {"name": "K"})

    def test_cross_type_names_the_occupant(self, vault):
        """A retrying caller must be told WHO holds the name, or they will just
        pick a different slug and create a duplicate of the same thing."""
        _create(vault, "character", "kael", {"name": "K"})
        with pytest.raises(ValueError) as exc:
            _create(vault, "world", "kael", {"name": "K"})
        assert "already used by a character" in str(exc.value)
        assert "unique across all types" in str(exc.value)

    def test_a_lost_race_says_the_same_thing_as_a_caught_duplicate(self, vault):
        """A lost check-then-insert race must not leak a raw database error.

        `create_entity` checks for a duplicate with a SELECT and inserts with a
        separate statement, so a second writer can land the same id in between.
        The primary key still refuses it — what matters is that the refusal reads
        as "already exists" rather than as
        "IntegrityError: UNIQUE constraint failed: entities.id", which tells the
        user nothing about what to do next.

        Driven by two real threads, because that is the only way to produce the
        interleaving; a mock would be asserting the mock.
        """
        import threading

        results = []
        barrier = threading.Barrier(2)

        def create():
            barrier.wait()          # both past the start line together
            try:
                _create(vault, "character", "kael", {"name": "K"})
                results.append("ok")
            except Exception as e:
                results.append(f"{type(e).__name__}: {e}")

        threads = [threading.Thread(target=create) for _ in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        losers = [r for r in results if r != "ok"]
        assert len(losers) == 1, f"expected one create to lose, got {results}"
        assert "Entity already exists: character/kael" in losers[0]
        assert "IntegrityError" not in losers[0]


class TestValidationBeforeInsert:
    def test_bad_parent_creates_nothing(self, vault):
        with pytest.raises(ValueError, match="Sequence not found: ghost-seq"):
            _create(vault, "scene", "s1", {"title": "S1", "sequence_id": "ghost-seq"})
        assert not _exists(vault, "s1")

    @pytest.mark.parametrize("slug", ["", "   ", "a/b", "../escape", "with space"])
    def test_bad_slug_rejected(self, vault, slug):
        with pytest.raises(ValueError, match="alphanumeric"):
            _create(vault, "character", slug, {"name": "N"})
        assert not _exists(vault, slug.strip())
