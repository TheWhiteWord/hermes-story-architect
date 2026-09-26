"""A gap hidden by the cap must not look like a gap that was fixed.

Regression: `characters` fell past UNFILLED_LIMIT at count 2 and vanished from
the view, so setting no_cast on one of two castless scenes dropped the count to
1 and pushed it further off. The view then showed no `characters` gap at all
while the DB still had one — fixing a scene looked like resolving the field.
"""
import json
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

FIXTURE = Path(__file__).parent / "fixtures" / "save-the-children"


@pytest.fixture
def project(tmp_path, monkeypatch):
    root = tmp_path / "root"
    shutil.copytree(FIXTURE, root / "projects" / "save-the-children")
    import core.config
    monkeypatch.setattr(core.config, "load_plugin_config", lambda: {"root_path": str(root)})
    from tools.story_import import handler as import_handler
    import_handler({"project": "save-the-children", "confirm": True}, root_path=str(root))
    return root / "projects" / "save-the-children"


def unfilled(project):
    from tools.story_load import handler
    return json.loads(
        handler({"project": "save-the-children", "view": "unfilled"},
                root_path=str(project.parent.parent)))


def test_omitted_fields_are_named(project):
    """When the view truncates, it must say which fields it dropped."""
    data = unfilled(project)
    assert data["truncated"] is True
    assert data["other_fields"], "truncated view must name the fields it omitted"
    shown = {i["field"] for i in data["unfilled"]}
    dropped = set(data["other_fields"])
    assert shown and dropped
    assert not (shown & dropped), "a field cannot be both shown and omitted"
    assert len(data["unfilled"]) + len(data["other_fields"]) == data["gap_types"]


def test_a_gap_is_never_silently_absent(project):
    """Every field the DB knows about is either shown or named as omitted."""
    from core.db import get_unfilled_map
    data = unfilled(project)
    known = set(get_unfilled_map(project))
    accounted = {i["field"] for i in data["unfilled"]} | set(data.get("other_fields", []))
    assert known == accounted


def test_untruncated_view_has_no_other_fields(project, monkeypatch):
    """Below the cap there is nothing omitted, so the key must be absent."""
    import tools.story_load as sl
    monkeypatch.setattr(sl, "UNFILLED_LIMIT", 1000)
    data = unfilled(project)
    assert "truncated" not in data
    assert "other_fields" not in data
