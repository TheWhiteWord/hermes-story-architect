"""B10: a `number` field must not be able to hold a string.

The first live test stored `act_count` as the string `'3'` — the schema says
`"type": "number"`, and `extra` is a JSON blob that does not enforce it. The
dashboard then died on `max('3', 3)`.

The fix coerces on write *and* on read. Both halves are needed: a write-side
fix alone leaves every database written before it still broken, while looking
complete.
"""
import json
import shutil
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

FIXTURE = Path(__file__).parent / "fixtures" / "save-the-children"


@pytest.fixture
def project_with_string_act_count(tmp_path):
    """A real fixture project whose act_count has been corrupted to '3'."""
    dest = tmp_path / "corrupt"
    shutil.copytree(str(FIXTURE), str(dest))
    db = sqlite3.connect(str(dest / ".story" / "story.db"))
    row = db.execute("SELECT id, extra FROM entities WHERE type='project'").fetchone()
    extra = json.loads(row[1] or "{}")
    extra["act_count"] = "3"
    db.execute("UPDATE entities SET extra=? WHERE id=?", (json.dumps(extra), row[0]))
    db.commit()
    db.close()
    return dest, row[0]


class TestNumericFieldsCoerceOnRead:
    def test_dashboard_survives_a_string_act_count(self, project_with_string_act_count):
        """This raised TypeError: '>' not supported between 'int' and 'str'."""
        from core.db import get_dashboard_data

        path, _ = project_with_string_act_count
        data = get_dashboard_data(path)          # used to raise
        act_count = data["story_data"]["project"]["act_count"]
        assert isinstance(act_count, int)
        assert act_count >= 3

    def test_summary_survives_a_string_act_count(self, project_with_string_act_count):
        from core.db import get_project_summary

        path, _ = project_with_string_act_count
        assert isinstance(get_project_summary(path)["project"]["act_count"], int)


class TestNumericFieldsCoerceOnWrite:
    def test_a_string_written_to_a_number_field_stores_a_number(
            self, project_with_string_act_count):
        from core.writes import edit_entity

        path, project_id = project_with_string_act_count
        edit_entity(path, "project", project_id, {"act_count": "5"}, "set five")
        raw = json.loads(sqlite3.connect(
            str(path / ".story" / "story.db")
        ).execute("SELECT extra FROM entities WHERE type='project'").fetchone()[0])
        assert raw["act_count"] == 5
        assert isinstance(raw["act_count"], int)


class TestCoerceNumber:
    @pytest.mark.parametrize("value,expected", [
        ("3", 3), ("-2", -2), ("2.5", 2.5),   # the string cases that broke the dashboard
        (7, 7), (2.5, 2.5),                   # already correct — untouched
        (None, 3), ("", 3), ("  ", 3),        # "not set" → the default
        ("abc", "abc"),                       # not a number: returned, not silently defaulted
    ])
    def test_edges(self, value, expected):
        from core.db import _coerce_number

        assert _coerce_number(value, 3) == expected

    def test_a_non_numeric_value_is_visible_not_replaced(self):
        """A wrong value the reader can see beats a plausible one it cannot."""
        from core.db import _coerce_number

        assert _coerce_number("three acts", 3) == "three acts"
