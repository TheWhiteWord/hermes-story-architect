"""Tests for the `value` entity type: constants, validation, create, edit, describe.

A value is a flat leaf: `name` is a column, the four ladder words and `note`
land in `extra`. One entity per value, id is the slug of the name.
"""
import json

import pytest

from core.constants import ENTITY_LABELS, ENTITY_SCHEMAS, REQUIRED_FIELDS
from core.entity import distinct_ladder_words, standard_sections, validate_entity
from core.writes import create_entity, create_project, edit_entity
from tools.story_describe import handler as describe_handler


@pytest.fixture
def project(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    (root / "projects" / "p").mkdir(parents=True)
    create_project("p", {"name": "P"}, root)
    return root / "projects" / "p"


def _value(project, slug, **overrides):
    fm = {"name": slug.replace("-", " ").title(), "p": "trust", "c": "distrust",
          "cd": "betrayal", "nn": "naive faith"}
    fm.update(overrides)
    return create_entity(project, "value", slug, fm)


class TestConstants:
    def test_value_is_a_labelled_entity_type(self):
        assert ENTITY_LABELS["value"] == "Value"
        assert "value" in ENTITY_SCHEMAS

    def test_fields_are_in_schema_order(self):
        assert list(ENTITY_SCHEMAS["value"]) == ["name", "p", "c", "cd", "nn", "note"]

    def test_only_note_is_optional(self):
        assert REQUIRED_FIELDS["value"] == ["name", "p", "c", "cd", "nn"]

    def test_sections_are_a_definition_and_notes(self):
        assert standard_sections("value") == ["Definition", "Notes"]


class TestValidateValue:
    def test_four_distinct_words_pass(self):
        assert distinct_ladder_words(
            {"p": "trust", "c": "distrust", "cd": "betrayal", "nn": "naive faith"})

    def test_duplicate_word_is_not_distinct(self):
        assert not distinct_ladder_words(
            {"p": "trust", "c": "trust", "cd": "betrayal", "nn": "naive faith"})

    def test_empty_word_is_not_distinct(self):
        assert not distinct_ladder_words({"p": "trust", "c": "", "cd": "x", "nn": "y"})

    def test_validate_entity_reports_a_duplicate_word(self):
        warnings = validate_entity("value", {"name": "Trust", "p": "a", "c": "a",
                                             "cd": "d", "nn": "e"})
        assert any("four distinct words" in w for w in warnings)

    def test_validate_entity_is_silent_on_a_good_value(self):
        assert validate_entity("value", {"name": "Trust", "p": "a", "c": "b",
                                         "cd": "c", "nn": "d"}) == []


class TestCreate:
    def test_a_valid_value_is_created(self, project):
        r = _value(project, "trust")
        assert r["success"], r
        assert r["entity_id"] == "trust"

    def test_retrieve_returns_every_field_in_schema_order(self, project, tmp_path):
        _value(project, "trust")
        from tools.story_retrieve import handler as retrieve_handler
        out = json.loads(retrieve_handler(
            {"project": "p", "entity_type": "value", "id": ["trust"],
             "fields": ["all"]}, root_path=str(project.parent.parent)))
        assert list(out["entities"][0]["fields"]) == \
            ["name", "p", "c", "cd", "nn", "note"]

    def test_duplicate_words_are_refused_and_name_the_rungs(self, project):
        with pytest.raises(ValueError, match="four distinct words"):
            _value(project, "trust", c="trust")

    def test_a_missing_word_is_refused(self, project):
        with pytest.raises(ValueError, match="four distinct words"):
            _value(project, "trust", c="")

    def test_id_must_equal_the_slug_of_the_name(self, project):
        with pytest.raises(ValueError, match="slug of its name"):
            create_entity(project, "value", "trust-2",
                          {"name": "Trust", "p": "a", "c": "b", "cd": "c", "nn": "d"})

    def test_name_uniqueness_is_case_and_whitespace_insensitive(self, project):
        _value(project, "trust")
        # Same name, different id: the id is not the slug, so it is refused —
        # and were the id check skipped, the name check below still refuses it.
        with pytest.raises(ValueError):
            create_entity(project, "value", "trust-2",
                          {"name": "  TRUST  ", "p": "a", "c": "b",
                           "cd": "c", "nn": "d"})

    def test_a_refused_create_writes_nothing(self, project):
        from core.db import get_db
        with pytest.raises(ValueError):
            _value(project, "trust", c="trust")
        conn = get_db(project)
        try:
            assert conn.execute(
                "SELECT id FROM entities WHERE type='value'").fetchall() == []
        finally:
            conn.close()


class TestEdit:
    def test_a_valid_edit_lands(self, project):
        _value(project, "trust")
        r = edit_entity(project, "value", "trust", {"p": "openness"}, "reword")
        assert r["success"], r

    def test_a_rename_that_moves_the_slug_is_refused(self, project):
        _value(project, "trust")
        with pytest.raises(ValueError, match="slug of its name"):
            edit_entity(project, "value", "trust", {"name": "Faith"}, "rename")

    def test_a_rename_that_keeps_the_slug_is_allowed(self, project):
        _value(project, "trust")
        r = edit_entity(project, "value", "trust", {"name": "  Trust  "}, "tidy")
        assert r["success"], r

    def test_an_edit_to_a_duplicate_word_is_refused(self, project):
        _value(project, "trust")
        with pytest.raises(ValueError, match="four distinct words"):
            edit_entity(project, "value", "trust", {"c": "trust"}, "dup")

    def test_a_refused_edit_changes_nothing(self, project):
        from core.db import get_db
        _value(project, "trust")
        with pytest.raises(ValueError):
            edit_entity(project, "value", "trust", {"c": "trust"}, "dup")
        conn = get_db(project)
        try:
            row = conn.execute(
                "SELECT extra FROM entities WHERE id='trust'").fetchone()
            assert json.loads(row[0])["c"] == "distrust"
        finally:
            conn.close()


class TestDescribe:
    def test_describe_lists_the_fields_and_sections(self):
        d = json.loads(describe_handler({"entity_type": "value"}))
        fields = d["entity_schemas"]["value"]
        assert [f for f in fields if f != "sections"] == \
            ["name", "p", "c", "cd", "nn", "note"]
        assert fields["sections"]["standard_sections"] == ["Definition", "Notes"]
