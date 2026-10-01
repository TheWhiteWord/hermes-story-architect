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
                  {"name": "The Resistance", "one_sentence": "x",
                   "setups": "the first scene"})
    rows = _relations(vault)
    assert len(rows) == before, f"a string wrote relation rows: {rows}"
    assert all(len(to_id) > 1 for _, to_id, _ in rows), \
        f"single-character relation targets: {rows}"


# ─── One dict→row rule, on all three write paths ─────────────────────────────
#
# relations_for_insert used to unwrap {scene_id, description} for plot_setup and
# plot_payoff only; every other kind got str(dict) as to_id. So a plot CREATE
# wrote corrupt rows for crisis and climax — the row pointed at a scene slug
# that did not exist and the prose was dropped. Edit and import were already
# correct, which is why it went unnoticed: the only coverage was through edit.

PLOT_BEATS = {
    "setups": ("plot_setup", "s1", "setup prose"),
    "crisis": ("plot_crisis", "s2", "crisis prose"),
    "climax": ("plot_climax", "s3", "climax prose"),
    "payoffs": ("plot_payoff", "s4", "payoff prose"),
}


def _notes(project):
    conn = sqlite3.connect(str(Path(project) / ".story" / "story.db"))
    rows = conn.execute(
        "SELECT kind, to_id, note FROM relations ORDER BY kind, to_id").fetchall()
    conn.close()
    return rows


@pytest.mark.parametrize("field,kind,scene_id,note", [
    pytest.param(f, k, s, n, id=f) for f, (k, s, n) in PLOT_BEATS.items()])
def test_create_writes_the_scene_slug_and_the_description(vault, field, kind,
                                                          scene_id, note):
    """The regression test. Every role, on the path that used to corrupt two."""
    from core.writes import create_entity as _create
    _create(vault, "plot", "the-resistance",
            {"name": "The Resistance", "one_sentence": "x",
             field: [{"scene_id": scene_id, "description": note}]})
    assert (kind, scene_id, note) in _notes(vault)


def test_create_does_not_stringify_a_dict_into_to_id(vault):
    """The symptom, stated directly: no to_id may contain a `{`."""
    create_entity(vault, "plot", "the-resistance", {
        "name": "The Resistance", "one_sentence": "x",
        "setups": [{"scene_id": "s1", "description": "d"}],
        "crisis": [{"scene_id": "s2", "description": "d"}],
        "climax": [{"scene_id": "s3", "description": "d"}],
        "payoffs": [{"scene_id": "s4", "description": "d"}]})
    bad = [r for r in _notes(vault) if "{" in r[1] or "'scene_id'" in r[1]]
    assert not bad, f"dict repr written into to_id: {bad}"


MALFORMED = {"setups": [{"description": "no scene named"}]}


def test_malformed_entry_is_skipped_on_create(vault):
    create_entity(vault, "plot", "the-resistance",
                  {"name": "The Resistance", "one_sentence": "x", **MALFORMED})
    assert _notes(vault) == [], _notes(vault)


def test_malformed_entry_is_skipped_on_edit(vault):
    from core.writes import edit_entity
    create_entity(vault, "plot", "the-resistance",
                  {"name": "The Resistance", "one_sentence": "x"})
    edit_entity(vault, "plot", "the-resistance", MALFORMED, "set a bad beat")
    assert _notes(vault) == [], _notes(vault)


def test_malformed_entry_is_skipped_on_import(tmp_path):
    """Three paths, three copies of the unwrap, and they disagreed on the
    missing-key default — two skipped the row, one wrote the dict repr as
    to_id. One function, one behaviour."""
    from tools.story_import import handler as import_handler
    root = tmp_path / "v"
    proj = root / "projects" / "stc"
    (proj / "plots").mkdir(parents=True)
    (proj / "project.md").write_text("---\nname: STC\nlogline: L\n---\n")
    (proj / "plots" / "P.md").write_text(
        "---\nid: the-resistance\nname: The Resistance\n"
        "one_sentence: x\n"
        "setups: [{'description': 'no scene named'}]\n---\n")
    import_handler({"project": str(proj), "root_path": root})
    assert _notes(proj) == [], _notes(proj)


def test_a_bare_slug_still_writes_as_is(vault):
    """The other shape the same loop serves: `characters` holds plain slugs."""
    create_entity(vault, "scene", "s1", {"title": "S1", "characters": ["kael"]})
    assert ("character_scene", "s1") in [(k, t) for k, t, _ in _notes(vault)]
