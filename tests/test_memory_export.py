"""Export and import tests for the DB-backed memory projection."""
import json

import pytest

from tools.story_export import handler as export_handler
from tools.story_import import handler as import_handler
from tools.story_memory import handler as memory_handler


@pytest.fixture
def project(tmp_path):
    from tools.story_create import handler as create_handler
    create_handler({
        "entity_type": "project",
        "slug": "memory-export",
        "project": "",
        "frontmatter": {"name": "Memory Export"},
    }, vault_path=tmp_path)
    return tmp_path / "projects" / "memory-export", tmp_path


def test_export_writes_frontmatter_only_and_preserves_order(project):
    path, vault = project
    memory_handler({
        "project": str(path), "action": "add", "category": "decisions", "entry": "First",
    }, vault_path=vault)
    memory_handler({
        "project": str(path), "action": "add", "category": "decisions", "entry": "Second",
    }, vault_path=vault)
    assert json.loads(export_handler({"project": str(path)}, vault_path=vault))["success"] is True
    text = (path / ".story" / "memory.md").read_text()
    assert text.startswith("---")
    assert text.rstrip().endswith("---")
    assert "decisions:" in text
    assert text.index("First") < text.index("Second")
    assert "##" not in text


def test_memory_file_is_projection_not_source(project):
    path, vault = project
    memory_handler({
        "project": str(path), "action": "add", "category": "directions", "entry": "DB value",
    }, vault_path=vault)
    (path / ".story" / "memory.md").write_text("---\ndirections:\n  - File value\n---\n")
    memory_handler({
        "project": str(path), "action": "add", "category": "open_questions", "entry": "Question?",
    }, vault_path=vault)
    export_handler({"project": str(path)}, vault_path=vault)
    text = (path / ".story" / "memory.md").read_text()
    assert "DB value" in text
    assert "File value" not in text
    assert "Question?" in text
