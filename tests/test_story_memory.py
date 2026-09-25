"""Focused tests for the dedicated story-memory mutation tool."""
import json

import pytest

from tools.story_memory import handler


@pytest.fixture
def project(tmp_path):
    from tools.story_create import handler as create_handler
    create_handler({
        "entity_type": "project",
        "slug": "memory-tool",
        "project": "",
        "frontmatter": {"name": "Memory Tool"},
    }, vault_path=tmp_path)
    return tmp_path / "projects" / "memory-tool", tmp_path


def call(project, vault, **args):
    return json.loads(handler({"project": str(project), **args}, vault_path=vault))


def test_add_remove_and_replace_round_trip(project):
    path, vault = project
    added = call(path, vault, action="add", category="decisions", entry="Keep the mystery unresolved.")
    assert added["success"] is True
    assert added["usage"].endswith("/3000")
    removed = call(path, vault, action="remove", category="decisions", old_entry="Keep the mystery unresolved.")
    assert removed["success"] is True
    call(path, vault, action="add", category="decisions", entry="Old rule")
    replaced = call(path, vault, action="replace", category="decisions", old_entry="Old rule", new_entry="New rule")
    assert replaced["entry"] == "New rule"
    from core.db import get_project_memory
    assert get_project_memory(path)["decisions"] == ["New rule"]


def test_duplicate_add_is_noop(project):
    path, vault = project
    call(path, vault, action="add", category="directions", entry="Keep it ambiguous.")
    result = call(path, vault, action="add", category="directions", entry="Keep it ambiguous.")
    assert result["success"] is True


def test_invalid_operation_does_not_mutate(project):
    path, vault = project
    result = call(path, vault, action="add", category="decisions", entry="x" * 301)
    assert result["success"] is False
    assert result["current_entries"] == []


def test_replace_missing_entry_does_not_mutate(project):
    path, vault = project
    result = call(path, vault, action="replace", category="decisions", old_entry="missing", new_entry="new")
    assert result["success"] is False
    assert result["current_entries"] == []
