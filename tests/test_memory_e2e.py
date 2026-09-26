"""End-to-end checks for the DB-authoritative story-memory loop."""
import json

import pytest

from tools.story_create import handler as create_handler
from tools.story_dashboard import handler as dashboard_handler
from tools.story_export import handler as export_handler
from tools.story_load import handler as load_handler
from tools.story_memory import handler as memory_handler


def test_memory_loop_is_db_authoritative(tmp_path):
    project = tmp_path / "projects" / "memory-e2e"
    vault = tmp_path
    assert json.loads(create_handler({
        "entity_type": "project", "slug": "memory-e2e", "project": "",
        "frontmatter": {"name": "Memory E2E"},
    }, root_path=vault))["success"] is True

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

    dashboard = json.loads(dashboard_handler({"project": str(project)}, root_path=vault))
    assert dashboard["success"] is True
    html_path = dashboard["dashboard_url"].replace("file://", "").split("?")[0]
    html = open(html_path, encoding="utf-8").read()
    assert "Story Memory" in html
    assert "memory-dialog" in html
    assert "Decision" in html

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
