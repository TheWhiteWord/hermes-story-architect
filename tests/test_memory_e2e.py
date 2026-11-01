"""End-to-end checks for the DB-authoritative story-memory loop."""
import json

import pytest

from story_architect.core.writes import create_project
from story_architect.tools.story_export import handler as export_handler
from story_architect.tools.story_load import handler as load_handler
from story_architect.tools.story_memory import handler as memory_handler


def test_memory_loop_is_db_authoritative(tmp_path):
    project = tmp_path / "projects" / "memory-e2e"
    vault = tmp_path
    assert create_project("memory-e2e", {"name": "Memory E2E"}, vault)["success"] is True

    entries = {
        "decisions": "Decision",
        "directions": "Direction",
        "open_questions": "Question?",
        "continuity_warnings": "Warning",
    }
    for category, entry in entries.items():
        result = json.loads(memory_handler({
            "project": str(project), "action": "add", "category": category, "entry": entry,
        }, root_path=vault))
        assert result["success"] is True

    loaded = json.loads(load_handler({"project": str(project)}, root_path=vault))
    assert loaded["memory"]["categories"] == {category: [entry] for category, entry in entries.items()}
    assert loaded["memory"]["usage"].endswith("/3000")

    assert json.loads(export_handler({"project": str(project)}, root_path=vault))["success"] is True
    memory_file = project / ".story" / "memory.md"
    assert memory_file.read_text().count("---") == 2
    (project / ".story" / "memory.md").write_text("stale file")
    reloaded = json.loads(load_handler({"project": str(project)}, root_path=vault))
    assert reloaded["memory"]["categories"] == {category: [entry] for category, entry in entries.items()}

    duplicate = json.loads(memory_handler({
        "project": str(project), "action": "add", "category": "decisions", "entry": "Decision",
    }, root_path=vault))
    assert duplicate["success"] is True
    overlong = json.loads(memory_handler({
        "project": str(project), "action": "add", "category": "decisions", "entry": "x" * 301,
    }, root_path=vault))
    assert overlong["success"] is False
