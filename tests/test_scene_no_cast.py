"""A drafted scene with no cast is flagged; no_cast records that it's deliberate.

Two halves, both load-bearing:
- without a cast → `view='unfilled'` must flag `characters` (an LLM that forgot
  to attach the cast is a real failure mode, silently invisible otherwise)
- with `no_cast` set → it must stop flagging, or a deliberate decision is
  reported as a gap forever and the author learns to ignore the field
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


def gaps(project, field):
    from tools.story_load import handler
    data = json.loads(
        handler({"project": "save-the-children", "view": "unfilled"},
                root_path=str(project.parent.parent)))
    for item in data["unfilled"]:
        if item["field"] == field:
            return set(item["entities"])
    return set()


def _scene_with_no_cast(project, scene_id):
    """Force the fixture scene into the state we care about: drafted, no relations."""
    import sqlite3
    db = project / ".story" / "story.db"
    conn = sqlite3.connect(str(db))
    conn.execute("DELETE FROM relations WHERE to_id=? AND kind='character_scene'", (scene_id,))
    conn.commit()
    conn.close()


def _set_no_cast(project, scene_id, value=True):
    import json as _json
    import sqlite3
    db = project / ".story" / "story.db"
    conn = sqlite3.connect(str(db))
    row = conn.execute("SELECT extra FROM entities WHERE id=?", (scene_id,)).fetchone()
    extra = _json.loads(row[0] or "{}")
    extra["no_cast"] = value
    conn.execute("UPDATE entities SET extra=? WHERE id=?", (_json.dumps(extra), scene_id))
    conn.commit()
    conn.close()


def test_a_castless_drafted_scene_is_flagged(project):
    _scene_with_no_cast(project, "central-room-day")
    assert "central-room-day" in gaps(project, "characters")


def test_no_cast_clears_the_gap(project):
    _scene_with_no_cast(project, "central-room-day")
    assert "central-room-day" in gaps(project, "characters")
    _set_no_cast(project, "central-room-day", True)
    assert "central-room-day" not in gaps(project, "characters")


def test_clearing_no_cast_restores_the_gap(project):
    _scene_with_no_cast(project, "central-room-day")
    _set_no_cast(project, "central-room-day", True)
    assert "central-room-day" not in gaps(project, "characters")
    _set_no_cast(project, "central-room-day", False)
    assert "central-room-day" in gaps(project, "characters")


def test_no_cast_does_not_hide_a_real_cast(project):
    """no_cast is a statement about an empty cast, not a way to suppress the check."""
    import sqlite3
    db = project / ".story" / "story.db"
    conn = sqlite3.connect(str(db))
    n = conn.execute(
        "SELECT COUNT(*) FROM relations WHERE to_id='central-room-day' "
        "AND kind='character_scene'").fetchone()[0]
    conn.close()
    assert n, "fixture scene should have a cast"
    _set_no_cast(project, "central-room-day", True)
    assert "central-room-day" not in gaps(project, "characters")
