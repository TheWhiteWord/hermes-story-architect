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
