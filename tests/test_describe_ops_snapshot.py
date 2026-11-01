"""describe_ops snapshot tests."""
import json
from pathlib import Path

from story_architect.core import drafts


def test_describe_ops_create(fixture_path):
    ops = [{"op": "create", "type": "character", "id": "kael",
            "frontmatter": {"name": "Kael"}, "sections": {"Arc": "x"},
            "summary": "s"}]
    out = drafts.describe_ops(fixture_path, ops)
    assert out[0]["kind"] == "create"
    assert out[0]["fields"][0]["field"] == "name"
    assert out[0]["sections"][0]["name"] == "Arc"
    assert "unfilled" in out[0]
    json.dumps(out)


def test_describe_ops_edit(fixture_path):
    # ensure entity exists? use fixture entity
    ops = [{"op": "edit", "entity_type": "location", "entity_id": "the-central-room",
            "data": {"mood": "dark"}, "summary": "s"}]
    out = drafts.describe_ops(fixture_path, ops)
    assert out[0]["kind"] == "edit"
    assert "fields" in out[0] or "sections" in out[0]


def test_describe_ops_delete(fixture_path):
    ops = [{"op": "delete", "entity_type": "location", "entity_id": "the-central-room",
            "summary": "s"}]
    out = drafts.describe_ops(fixture_path, ops)
    assert out[0]["kind"] == "delete"
    assert out[0]["reversible"] is True


def test_describe_ops_reorder(fixture_path):
    ops = [{"op": "reorder", "entity_type": "scene", "entity_id": "x",
            "ordered_ids": ["a", "b"], "summary": "s"}]
    out = drafts.describe_ops(fixture_path, ops)
    assert out[0]["kind"] == "reorder"
    assert out[0]["count"] == 2
    assert len(out[0]["order"]) == 2
