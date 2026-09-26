"""A project slug is a directory name, so it gets the same validation as any id.

Regression: story_create returned to _create_project() before the slug check
ran, so slug='../escape' became a literal path under projects/.
"""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from tools.story_create import handler  # noqa: E402


def _create(slug, root, **extra):
    args = {
        "entity_type": "project",
        "slug": slug,
        "project": str(root),
        "frontmatter": {"name": "T", "logline": "L", "genre": "G", "status": "draft"},
    }
    args.update(extra)
    return json.loads(handler(args, root_path=str(root)))


def test_project_slug_rejects_path_traversal(tmp_path):
    r = _create("../escape", tmp_path)
    assert r.get("error")
    assert not (tmp_path.parent / "escape").exists()


def test_project_slug_rejects_spaces_and_slashes(tmp_path):
    for bad in ("My Story", "a/b", "", ".."):
        r = _create(bad, tmp_path)
        assert r.get("error"), f"expected rejection for {bad!r}, got {r}"


def test_valid_project_slug_still_works(tmp_path):
    r = _create("my-story_2", tmp_path)
    assert r.get("success"), r
    assert (tmp_path / "projects" / "my-story_2" / ".story" / "story.db").exists()
