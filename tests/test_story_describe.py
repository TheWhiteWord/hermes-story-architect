"""story_describe: what fields does an entity type expect?

Its purpose is helping the LLM prepare good questions for the user before creating
or completing an entity. It must NOT describe the other tools: tool schemas are
already in the model's context at all times, so echoing them here would spend
tokens repeating what the model already knows.
"""
import importlib
import json

import pytest

from tools import story_describe

ALL_TOOLS = [
    "story_admin", "story_backup", "story_dashboard", "story_describe",
    "story_draft", "story_export", "story_import", "story_load",
    "story_memory", "story_retrieve", "story_search",
]


def _handler(args):
    return json.loads(story_describe.handler(args))


class TestDescribeScope:
    def test_does_not_duplicate_tool_schemas(self):
        assert "tools" not in story_describe.SCHEMA["properties"]
        assert "tools" not in _handler({})

    def test_every_tool_carries_its_own_description(self):
        """What story_describe gave up, each tool now carries itself."""
        for name in ALL_TOOLS:
            schema = importlib.import_module(f"tools.{name}").SCHEMA
            assert len(schema.get("description", "")) > 20, f"{name} has no description"

    def test_destructive_tool_says_so(self):
        desc = importlib.import_module("tools.story_import").SCHEMA["description"]
        assert "DESTRUCTIVE" in desc

    def test_no_description_promises_a_missing_parameter(self):
        """A description must never tell the model to pass something the schema lacks."""
        for name in ALL_TOOLS:
            schema = importlib.import_module(f"tools.{name}").SCHEMA
            props = set(schema.get("properties", {}))
            description = schema.get("description", "")
            for claim in ("dry_run", "view=", "fields=[", "id="):
                assert claim not in description, \
                    f"{name} advertises '{claim}' but does not accept it"


class TestEntityFields:
    def test_single_entity_type(self):
        assert list(_handler({"entity_type": "character"})["entity_schemas"]) == ["character"]

    def test_all_entity_types_by_default(self):
        assert len(_handler({})["entity_schemas"]) == 10

    def test_relation_backed_fields_are_flagged(self):
        fields = _handler({"entity_type": "plot"})["entity_schemas"]["plot"]
        for name in ("setups", "crisis", "climax", "payoffs"):
            assert fields[name]["stored_as"] == "relation"

    def test_computed_fields_say_do_not_set(self):
        fields = _handler({"entity_type": "character"})["entity_schemas"]["character"]
        computed = [f for f, m in fields.items() if m.get("computed")]
        assert computed, "character should have computed fields"
        for name in computed:
            assert "do not set" in fields[name]["description"]

    @pytest.mark.parametrize("field", ["name", "one_sentence", "goals_short"])
    def test_ordinary_fields_carry_what_a_question_needs(self, field):
        """Enough to decide whether it is worth asking the user about this field."""
        entry = _handler({"entity_type": "character"})["entity_schemas"]["character"][field]
        assert entry["type"] and "default" in entry and "optional" in entry
        assert entry["description"]

    def test_unknown_entity_type_errors(self):
        assert "Unknown entity_type" in _handler({"entity_type": "nope"})["error"]


class TestStructuredFieldShapesAreVisible:
    """D1: the schema knows the shape, so story_describe must say it.

    The output builder used to copy four keys by hand and drop `sub_fields`.
    A `relationship.perspectives` object was then written as a bare string
    (crashing story_load) and a plot's `setups` descriptions were silently
    discarded on write — the schema carried the shape and the tool did not
    show it.
    """

    def test_sub_fields_present_on_every_field_that_has_them(self):
        from core.constants import ENTITY_SCHEMAS

        out = _handler({})["entity_schemas"]
        expected = {
            f"{et}.{f}"
            for et, fields in ENTITY_SCHEMAS.items()
            for f, meta in fields.items()
            if "sub_fields" in meta
        }
        assert expected, "no field has sub_fields — the premise of this test is gone"
        got = {
            f"{et}.{f}"
            for et, fields in out.items()
            for f, meta in fields.items()
            if "sub_fields" in meta
        }
        assert got == expected

    def test_an_object_sub_field_says_which_keys_it_takes(self):
        perspectives = _handler({"entity_type": "relationship"})["entity_schemas"]["relationship"]["perspectives"]
        assert perspectives["type"] == "object"
        assert set(perspectives["sub_fields"]) == {
            "label", "feeling", "type", "strength", "secret"}
        assert perspectives["sub_fields"]["strength"]["type"] == "number"

    def test_a_list_sub_field_says_what_each_item_holds(self):
        setups = _handler({"entity_type": "plot"})["entity_schemas"]["plot"]["setups"]
        assert setups["type"] == "list"
        assert set(setups["sub_fields"]) == {"scene_id", "description"}

    def test_no_schema_key_is_dropped(self):
        """The invariant, not a spot check: a new annotation must not vanish.

        This is the assertion that would have caught the original bug, and it
        keeps catching it if someone adds a key to ENTITY_SCHEMAS later.
        """
        from core.constants import ENTITY_SCHEMAS

        out = _handler({})["entity_schemas"]
        missing = set()
        for et, fields in ENTITY_SCHEMAS.items():
            for field, meta in fields.items():
                missing |= set(meta) - set(out[et][field])
        assert not missing, f"schema keys dropped by story_describe: {sorted(missing)}"


class TestEntityTypeEnumsStayInSync:
    """Every tool that takes an entity_type must accept every one ENTITY_SCHEMAS defines.

    A hand-written enum once dropped 'project', so the model could not act on the
    project entity even though the handler supported it. story_draft and
    story_admin route entity_type through core.writes and have no enum of their own.
    """

    @pytest.mark.parametrize("tool,path", [
        ("story_retrieve", ["entity_type"]),
        ("story_describe", ["entity_type"]),
    ])
    def test_enum_matches_entity_schemas(self, tool, path):
        from core.constants import ENTITY_SCHEMAS

        node = importlib.import_module(f"tools.{tool}").SCHEMA["properties"]
        for key in path:
            node = node[key]
        assert set(node["enum"]) == set(ENTITY_SCHEMAS), (
            f"{tool} enum is out of sync: "
            f"missing={sorted(set(ENTITY_SCHEMAS) - set(node['enum']))} "
            f"extra={sorted(set(node['enum']) - set(ENTITY_SCHEMAS))}"
        )
