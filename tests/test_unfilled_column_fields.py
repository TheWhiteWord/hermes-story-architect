"""A field with a value is not a gap.

`unfilled_fields` was handed the `extra` blob alone, so the four fields that
live in DB columns were invisible to it: `project.logline`,
`plot.one_sentence`, `location.world` and `scene.location`. Every one of them
was reported unfilled on live data that had it filled — and in the same
payload, one key away, returned with its real value. An author reading the
unfilled view was told to write something they had already written, which is
the fastest way to make a gap list stop being read.

The fix layers the columns on at the shared helper rather than in each caller,
because the callers were merging them by hand, one type at a time, and that is
how four of them got missed in the first place.

The fifth case in here is a TRUE positive and is pinned as one:
`project.screenplay_title` sits on its schema default ("Default"), which the
"empty" rule counts as unset because the user never chose it. It is the
reason the survivor of the sweep is correct rather than a leftover.
"""
import json
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from core.constants import ENTITY_SCHEMAS
from core.db import get_db, get_unfilled_map
from core.entity import ENTITY_COLUMN_MAP, unfilled_fields


@pytest.fixture
def project(tmp_path):
    root = tmp_path / "projects"
    root.mkdir(exist_ok=True)
    proj = root / "stc"
    shutil.copytree(str(REPO / "tests" / "fixtures" / "save-the-children"),
                    str(proj))
    from conftest import build_fixture_db
    build_fixture_db(proj, tmp_path)
    return proj


def reported(project, entity_type, entity_id):
    """What story_retrieve reports as unfilled, through its own path."""
    from tools.story_retrieve import _resolve, _row_data, _unfilled
    conn = get_db(project)
    try:
        row, err = _resolve(conn, entity_type, entity_id)
        assert not err, err
        return _unfilled(conn, _row_data(conn, row), entity_type)
    finally:
        conn.close()


def field_value(project, entity_type, entity_id, field):
    from tools.story_retrieve import _resolve, _row_data, _entity_fields
    conn = get_db(project)
    try:
        row, err = _resolve(conn, entity_type, entity_id)
        assert not err, err
        data = _row_data(conn, row)
        return _entity_fields(conn, data, entity_type, set(ENTITY_SCHEMAS[entity_type])).get(field)
    finally:
        conn.close()


# The four fields that live in a column, with a fixture entity that has one.
COLUMN_CASES = [
    ("project", "stc", "logline"),
    ("plot", "the-resistance", "one_sentence"),
    ("location", "the-central-room", "world"),
    ("scene", "central-room-day", "location"),
]


class TestColumnBackedFieldsAreNotGaps:
    @pytest.mark.parametrize("entity_type,entity_id,field", COLUMN_CASES)
    def test_a_filled_column_is_not_reported(self, project, entity_type,
                                             entity_id, field):
        assert field_value(project, entity_type, entity_id, field), \
            "fixture no longer has this value; the test is vacuous"
        assert field not in reported(project, entity_type, entity_id)

    @pytest.mark.parametrize("entity_type,entity_id,field", COLUMN_CASES)
    def test_the_field_is_still_returned_with_its_value(self, project,
                                                       entity_type, entity_id,
                                                       field):
        """The two halves have to agree: a field cannot be both returned and
        missing. This is the shape of the original bug."""
        assert field_value(project, entity_type, entity_id, field)
        assert field not in reported(project, entity_type, entity_id)

    @pytest.mark.parametrize("entity_type,entity_id,field", COLUMN_CASES)
    def test_clearing_the_column_is_reported_again(self, project, entity_type,
                                                   entity_id, field):
        """The fix must not have made the gap undetectable — an unfilled field
        that never reports is as useless as one that always does."""
        conn = get_db(project)
        col = ENTITY_COLUMN_MAP[entity_type][field]
        row = conn.execute(
            f"SELECT {col} FROM entities WHERE id=?", (entity_id,)).fetchone()
        conn.execute(f"UPDATE entities SET {col}='' WHERE id=?", (entity_id,))
        conn.commit()
        conn.close()
        try:
            assert field in reported(project, entity_type, entity_id)
        finally:
            conn = get_db(project)
            conn.execute(f"UPDATE entities SET {col}=? WHERE id=?",
                         (row[0], entity_id))
            conn.commit()
            conn.close()


class TestTheUnfilledMap:
    """The second caller. It had its own hand-rolled column merge, one type at
    a time, which is where `location.world` was missed entirely."""

    def test_no_filled_column_appears_in_the_map(self, project):
        """Per ENTITY, not per field: `one_sentence` is a column for plots and
        for scenes, and the fixture's scenes mostly have an empty one. Asserting
        the field is absent would be asserting that a real gap is silenced."""
        unfilled = get_unfilled_map(project)
        for entity_type, entity_id, field in COLUMN_CASES:
            if entity_type == "project":
                continue  # this view excludes the project row by design
            assert entity_id not in unfilled.get(field, []), \
                f"{field} reported for {entity_id} despite having a value"

    def test_a_genuine_gap_in_the_same_field_is_still_reported(self, project):
        """The other half. `one_sentence` on the-resistance is filled and on
        central-room-day is empty, and the map has to say exactly that — a fix
        that dropped the column merge entirely would pass the test above."""
        unfilled = get_unfilled_map(project)
        assert "the-resistance" not in unfilled.get("one_sentence", [])
        assert "central-room-day" in unfilled.get("one_sentence", [])

    def test_genuine_gaps_still_appear(self, project):
        """Not a silencing fix: an unfilled field must still be reported."""
        unfilled = get_unfilled_map(project)
        # The scientists plot has no complications — a real, deliberate gap.
        assert "the-scientists-last-stand" in unfilled.get("complications", [])
        # Both fixture plots have plot_scope set (main and sub).
        assert "plot_scope" not in unfilled


class TestScreenplayTitleIsARealGap:
    """The one survivor of the sweep, pinned so it cannot be 'fixed' by
    accident. It sits on its schema default, which counts as unset because the
    user never chose it — the opposite of a column the user filled."""

    def test_the_default_counts_as_unfilled(self):
        assert "screenplay_title" in unfilled_fields("project", {})

    def test_a_chosen_title_is_not_a_gap(self):
        assert "screenplay_title" not in unfilled_fields(
            "project", {"screenplay_title": "Save the Children"})


class TestTheHelperItself:
    def test_without_a_row_the_old_behaviour_is_unchanged(self):
        """The signature change must be backward compatible: a caller with only
        the blob gets the answer it got before, not a crash and not a different
        verdict."""
        assert "one_sentence" in unfilled_fields("plot", {})

    def test_the_row_is_not_mutated(self):
        """`extra` is the caller's dict and is reused after the call in
        get_unfilled_map; writing columns into it would corrupt the next
        iteration's view of the entity."""
        extra = {"name": "X"}
        unfilled_fields("plot", extra, {"one_sentence": "real", "name": "X"})
        assert extra == {"name": "X"}

    def test_extra_wins_over_a_stale_column(self):
        """If a field ever moves out of a column, the blob is the newer value
        and a stale column must not shadow it."""
        gaps = unfilled_fields("plot", {"one_sentence": "written"},
                               {"one_sentence": ""})
        assert "one_sentence" not in gaps
