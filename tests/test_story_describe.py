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
        for name in ("setups", "complications", "crisis", "climax", "resolutions"):
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


class TestStorageLabelsAreTrue:
    """B4/B5: the label says where a field lives, and it is never a guess.

    The label used to come from a flattened set of field NAMES across all
    entity types, so `plot.characters` and `relationship.characters` were
    called relations because `scene.characters` is one. Both are stored in
    `extra`. An agent reading that has no way to know the tool was guessing.
    """

    def test_no_field_is_labelled_with_storage_it_does_not_have(self):
        from core.entity import ENTITY_COLUMN_MAP, relation_fields

        out = _handler({})["entity_schemas"]
        wrong = []
        for et, fields in out.items():
            cols = ENTITY_COLUMN_MAP.get(et, {})
            rels = relation_fields(et)
            for field, entry in fields.items():
                claim = entry.get("stored_as")
                if not claim:
                    continue
                truth = ("relation" if field in rels
                         else "column" if field in cols else None)
                if claim != truth:
                    wrong.append(f"{et}.{field}: says {claim}, is {truth}")
        assert not wrong, wrong

    def test_every_declared_reference_is_labelled(self):
        from core.constants import ENTITY_SCHEMAS
        from core.entity import ENTITY_COLUMN_MAP, relation_fields

        out = _handler({})["entity_schemas"]
        declared = set()
        for et, cols in ENTITY_COLUMN_MAP.items():
            declared |= {(et, f) for f, c in cols.items() if c.endswith("_id")}
        for et in ENTITY_SCHEMAS:
            declared |= {(et, f) for f in relation_fields(et)}
        unlabelled = [f"{et}.{f}" for et, f in declared
                      if not out[et][f].get("stored_as")]
        assert not unlabelled, unlabelled

    def test_a_link_in_extra_is_still_marked_as_a_reference(self):
        """The nine `extra` links have no special storage, but the agent still
        needs to know the value is another entity's slug, not a display name."""
        out = _handler({})["entity_schemas"]
        for et, field in [("scene", "act_id"), ("arc_beat", "scene"),
                          ("plot", "characters"),
                          ("project", "story_climax_scene_id")]:
            assert out[et][field]["is_reference"] is True, f"{et}.{field}"

    def test_an_id_is_not_a_reference(self):
        """`id` says "slug" because it IS one. Calling it a reference to
        another entity would be wrong in the other direction.

        No schema declares `id` any more — the row key is the id, so a declared
        field could only ever render blank. The guard below therefore has nothing
        left to act on today, and stays only as a backstop should one reappear.
        """
        from core.constants import ENTITY_SCHEMAS
        for et in ("scene", "act", "arc_beat"):
            assert "id" not in ENTITY_SCHEMAS[et], (
                f"{et} declares an id field, which the write path discards "
                f"and the read path can only render empty")

    def test_a_plain_value_is_not_labelled(self):
        """`name`, `order`, `status` are columns like everything else; saying so
        for 25 fields is noise that buries the 12 that matter."""
        out = _handler({})["entity_schemas"]
        for et, field in [("act", "title"), ("act", "order"),
                          ("character", "one_sentence"), ("project", "logline")]:
            assert "stored_as" not in out[et][field], f"{et}.{field}"
            assert not out[et][field].get("is_reference"), f"{et}.{field}"


class TestOneVocabularyAcrossReadAndWrite:
    """story_load and story_describe use the SAME field names.

    `story_load` used to abbreviate to `chars`/`loc`, saving 12 tokens (0.7% of
    the payload) and costing a second vocabulary every agent had to learn. The
    abbreviations are gone; these tests fail if they come back, because their
    return is what caused the confusion in the first place.
    """

    def _load_payload(self):
        import shutil
        import tempfile
        from pathlib import Path

        from core.db import get_project_summary

        src = Path(__file__).parent / "fixtures" / "save-the-children"
        tmp = Path(tempfile.mkdtemp()) / "p"
        shutil.copytree(src, tmp)
        try:
            return get_project_summary(tmp)
        finally:
            shutil.rmtree(tmp.parent)

    def test_story_load_does_not_emit_the_old_abbreviations(self):
        blob = json.dumps(self._load_payload())
        assert '"chars"' not in blob, "story_load abbreviates again"
        assert '"loc":' not in blob, "story_load abbreviates again"

    def test_story_load_uses_the_write_side_names(self):
        blob = json.dumps(self._load_payload())
        assert '"characters"' in blob
        assert '"location"' in blob

    def test_every_link_key_story_load_emits_is_a_real_field_name(self):
        """The stronger form: no link key is a name story_describe cannot accept.

        A made-up abbreviation fails here even if nobody remembered its name.
        Scoped to entity nodes (dicts carrying an `id`); the `memory` subtree
        has its own vocabulary and is not entity fields.
        """
        from core.constants import ENTITY_SCHEMAS

        out = _handler({})["entity_schemas"]
        known = {f for fields in out.values() for f in fields}
        # Declared sub_field names are real vocabulary too. `with` lives here and
        # nowhere else — `character.relationships.sub_fields` — so a top-level-only
        # set rejects a name story_describe in fact reports, and this test failed on
        # a correct payload for three phases before anyone read what it was asserting.
        known |= {sub for fields in out.values() for f in fields.values()
                  for sub in (f.get("sub_fields") or {})}
        # Entity containers, not fields: they hold other entities.
        known |= {"acts", "sequences", "scenes", "worlds", "locations",
                  "plots", "characters"}
        # `milestone` is the load payload's own climax marker, deliberately not
        # a stored field — the spec derives it from four scene booleans.
        known |= {"milestone"}
        # `id` is the entity's own key, not a field: it identifies the node
        # rather than describing it, and no schema declares it.
        known |= {"id"}

        def walk(node, is_entity=False):
            if isinstance(node, dict):
                entity = is_entity or "id" in node
                for k, v in node.items():
                    if entity and isinstance(v, (str, list)) and k not in known:
                        pytest.fail(f"story_load emits unknown entity field {k!r}")
                    walk(v, entity)
            elif isinstance(node, list):
                for x in node:
                    walk(x, is_entity)

        walk(self._load_payload())

    def test_story_describe_uses_one_name_for_the_entity_id(self):
        """The op argument is `id` and the field is `id`, so no bridging note.

        This description once ended "an entity's `id` is the `slug` argument of its
        op" — a sentence that exists only because the two names disagreed.
        """
        from tools.story_describe import SCHEMA

        assert "slug" not in SCHEMA["description"]


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
