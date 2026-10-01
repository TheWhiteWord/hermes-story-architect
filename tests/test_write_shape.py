"""D4: a field that declares a shape must hold it at write time.

Six fields declare `sub_fields`, and before this nothing checked the value
against that declaration. Two measured consequences, both silent until
something downstream tripped:

* `plot.setups: "the first scene"` was iterated one **character** at a time into
  relation rows — eight rows pointing at `' '`, `'e'`, `'f'` — and the commit
  that created them reported failure with `0 committed`.
* `relationship.perspectives: "just a string"` made `story_draft` raise
  `AttributeError`, so the tool returned a traceback rather than a finding.

The read side (B7/B9/D1) shows the shape; this is the other half — catching the
mistake when the display is not consulted.
"""
import json
import sqlite3
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from core.entity import validate_entity  # noqa: E402
from core.writes import create_entity, create_project  # noqa: E402


@pytest.fixture
def vault(tmp_path):
    v = tmp_path / "v"
    (v / "projects").mkdir(parents=True)
    assert create_project("stc", {"name": "STC", "logline": "L"}, v)["success"] is True
    return v / "projects" / "stc"


def _relations(project):
    conn = sqlite3.connect(str(Path(project) / ".story" / "story.db"))
    rows = conn.execute("SELECT from_id, to_id, kind FROM relations").fetchall()
    conn.close()
    return rows


def test_a_string_where_a_list_is_declared_is_reported():
    warnings = validate_entity("plot", {"setups": "the first scene"})
    assert any("setups must be a list" in w for w in warnings), warnings
    # The finding names the keys, so the agent can fix it without a lookup.
    assert any("scene_id" in w and "description" in w for w in warnings)


def test_a_string_where_an_object_is_declared_is_reported():
    warnings = validate_entity("relationship", {"perspectives": "just a string"})
    assert any("perspectives must be an object" in w for w in warnings), warnings


def test_a_list_containing_a_non_object_is_reported():
    warnings = validate_entity("plot", {"setups": ["the first scene"]})
    assert any("non-object" in w for w in warnings), warnings


def test_a_wrong_shape_does_not_crash_the_validator():
    """The crash this fixes: `.items()` on the very value just complained about."""
    for fm in ({"perspectives": "a string"}, {"perspectives": ["a", "b"]},
               {"perspectives": 42}):
        warnings = validate_entity("relationship", {"characters": ["kael", "mira"], **fm})
        assert isinstance(warnings, list)
    assert any("perspectives must be" in w
               for w in validate_entity("relationship", {"perspectives": 42}))


def test_a_correct_shape_is_not_reported():
    good_list = {"setups": [{"scene_id": "s1", "description": "d"}]}
    assert not [w for w in validate_entity("plot", good_list) if "setups" in w]
    good_obj = {"characters": ["kael", "mira"],
                "perspectives": {"kael": {"label": "K", "feeling": "wary",
                                          "type": "ally", "strength": 0.5,
                                          "secret": False}}}
    assert not [w for w in validate_entity("relationship", good_obj) if "perspectives" in w]


def test_a_string_writes_no_relation_rows(vault):
    """The data-integrity half, on the path that skips stage-time validation.

    `create_entity` is called directly by the importer and by tests, so the
    stage-time finding is not the only guard — the database must not receive
    one relation row per character of a string.
    """
    before = len(_relations(vault))
    create_entity(vault, "plot", "the-resistance",
                  {"name": "The Resistance", "one_sentence": "x"})
    create_entity(vault, "scene", "s1", {
        "title": "S1", "plot_roles": "the first scene"})
    rows = _relations(vault)
    assert len(rows) == before, f"a string wrote relation rows: {rows}"
    assert all(len(to_id) > 1 for _, to_id, _ in rows), \
        f"single-character relation targets: {rows}"


# ─── One dict→row rule, on all three write paths ─────────────────────────────
#
# relations_for_insert used to unwrap {scene_id, description} for plot_setup and
# plot_resolution only; every other kind got str(dict) as to_id. So a plot CREATE
# wrote corrupt rows for crisis and climax — the row pointed at a scene slug
# that did not exist and the prose was dropped. Edit and import were already
# correct, which is why it went unnoticed: the only coverage was through edit.
#
# These ran through the plot's five fields. Those are computed now — a role is
# written on the SCENE as `plot_roles` — so the coverage moved with the write
# path rather than being deleted. See test_scene_plot_roles.py for the
# scene-side contract.

PLOT_ROLES = ["setup", "complication", "crisis", "climax", "resolution"]


def _with_plot(vault):
    """A project holding one plot, so `plot_roles` has something to name."""
    create_entity(vault, "plot", "the-resistance",
                  {"name": "The Resistance", "one_sentence": "x"})
    return vault


def _notes(project):
    conn = sqlite3.connect(str(Path(project) / ".story" / "story.db"))
    rows = conn.execute(
        "SELECT kind, to_id, note FROM relations ORDER BY kind, to_id").fetchall()
    conn.close()
    return rows


@pytest.mark.parametrize("role", PLOT_ROLES)
def test_create_writes_the_scene_slug_and_the_description(vault, role):
    """The regression test, on the field a role is written on now. Every role,
    including the two the old unwrap used to corrupt."""
    _with_plot(vault)
    from core.writes import create_entity as _create
    _create(vault, "scene", "s1", {
        "title": "S1",
        "plot_roles": [{"plot": "the-resistance", "role": role,
                        "description": f"{role} prose"}]})
    assert (f"plot_{role}", "s1", f"{role} prose") in _notes(vault)


def test_create_does_not_stringify_a_dict_into_to_id(vault):
    """The symptom, stated directly: no to_id may contain a `{`."""
    _with_plot(vault)
    create_entity(vault, "scene", "s1", {
        "title": "S1",
        "plot_roles": [{"plot": "the-resistance", "role": role,
                        "description": "d"} for role in PLOT_ROLES]})
    bad = [r for r in _notes(vault) if "{" in r[1] or "'plot'" in r[1]]
    assert not bad, f"dict repr written into to_id: {bad}"


MALFORMED = [{"role": "setup", "description": "no plot named"}]


def test_malformed_entry_is_refused_on_create(vault):
    """An entry naming no plot is not a row — it is a reference that resolves
    to nothing, refused by name."""
    _with_plot(vault)
    with pytest.raises(ValueError, match="plot_roles entry needs a plot slug"):
        create_entity(vault, "scene", "s1", {"title": "S1", "plot_roles": MALFORMED})
    assert [r for r in _notes(vault) if r[0].startswith("plot_")] == []


def test_malformed_entry_is_refused_on_edit(vault):
    from core.writes import edit_entity
    _with_plot(vault)
    create_entity(vault, "scene", "s1", {"title": "S1"})
    with pytest.raises(ValueError, match="plot_roles entry needs a plot slug"):
        edit_entity(vault, "scene", "s1", {"plot_roles": MALFORMED}, "set a bad role")
    assert [r for r in _notes(vault) if r[0].startswith("plot_")] == []


def test_a_bare_slug_still_writes_as_is(vault):
    """The other shape the same loop serves: `characters` holds plain slugs."""
    create_entity(vault, "scene", "s1", {"title": "S1", "characters": ["kael"]})
    assert ("character_scene", "s1") in [(k, t) for k, t, _ in _notes(vault)]


# ─── Create-path coverage for EVERY writable relation field ──────────────────
#
# The corruption above survived because the create path had no coverage at all —
# only the edit path, which was already correct. So this is the audit the bug
# asked for: derived from the schema rather than hand-listed, because a hand list
# is the same thing that let the hole exist.
#
# `CREATE_PATH_CASES` is the only hand-written part: a relation field needs a
# *target that exists*, and only the test knows what a valid slug looks like for
# each entity. The list is asserted against the schema, so a relation field added
# without a case here fails rather than passing untested.

CREATE_PATH_CASES = [
    # (entity_type, field, value, expected kind, the row's `to_id`, child slug)
    # `character_scene` is stored from the CHARACTER side, so the row points at
    # the scene; every other kind points away from its owner. The case says which
    # end, rather than assuming one shape for all rows.
    ("location", "variant_of", "the-room", "location_variant", "the-room", "the-room-night"),
    ("world", "variant_of", "the-real-world", "world_variant", "the-real-world", "the-mirror-world"),
    ("scene", "characters", ["kael"], "character_scene", "s1", "s1"),
]


def _writable_relation_fields():
    """Every relation field a create may write — computed ones are read-only."""
    from core.constants import ENTITY_SCHEMAS
    from core.entity import relation_fields
    # `computed` only, and via .get: writes.py accepts a relation field that has no
    # schema entry (valid = schema | sections | rel_fields), so filtering on schema
    # membership here would exempt exactly the fields create still writes.
    return {(et, f) for et, schema in ENTITY_SCHEMAS.items() for f in relation_fields(et)
            if not schema.get(f, {}).get("computed")}


def test_every_writable_relation_field_has_a_create_path_case():
    """The audit's own guard. Add a relation field and this names what is missing."""
    covered = {(et, f) for et, f, _v, _kind, _to, _slug in CREATE_PATH_CASES} | {("scene", "plot_roles")}
    missing = _writable_relation_fields() - covered
    assert not missing, f"relation fields with no create-path test: {sorted(missing)}"


def _create_with_relation(vault, entity_type, field, value, child):
    """A base target that exists, then the entity carrying the relation field."""
    if entity_type == "scene":
        create_entity(vault, "character", value[0], {"name": "Kael"})
        return create_entity(vault, entity_type, child, {"title": "S", field: value})
    base = {"name": "Base", "one_sentence": "x"} if entity_type == "world" else {"name": "Base"}
    create_entity(vault, entity_type, value, base)
    return create_entity(vault, entity_type, child, {**base, field: value})


@pytest.mark.parametrize("entity_type, field, value, kind, to_id, child", CREATE_PATH_CASES)
def test_create_writes_the_relation_row_and_it_reads_back(
        vault, entity_type, field, value, kind, to_id, child):
    """The audit's assertion, per field: create writes the row, and it means something.

    Both halves in one test because the row alone is the name-only assertion this
    phase is removing — a row that exists but resolves to nothing passes it.
    """
    import json

    from tools.story_retrieve import handler as retrieve_handler

    _create_with_relation(vault, entity_type, field, value, child)
    rows = [(k, t) for k, t, _ in _notes(vault) if k == kind]
    assert rows == [(kind, to_id)], f"{entity_type}.{field} wrote {rows}"
    assert not [r for r in rows if "{" in r[1]], "a dict repr reached the row"

    out = json.loads(retrieve_handler({
        "action": "retrieve", "project": str(vault), "root_path": str(vault),
        "entity_type": entity_type, "id": [child], "fields": [field],
    }))
    # `fields` nests the values; `unfilled_fields` sits beside it.
    got = out["entities"][0]["fields"][field]
    assert got == value, f"{entity_type}.{field} read back as {got!r}"
