"""A project slug is a directory name, so it gets the same validation as any id.

Regression: the create path returned to project creation before the slug check
ran, so slug='../escape' became a literal path under projects/.
"""

import pytest


from core.writes import create_project


def _create(slug, root, **extra):
    frontmatter = {"name": "T", "logline": "L", "genre": "G", "status": "draft"}
    frontmatter.update(extra)
    return create_project(slug, frontmatter, root)


def test_project_slug_rejects_path_traversal(tmp_path):
    with pytest.raises(ValueError, match="alphanumeric"):
        _create("../escape", tmp_path)
    assert not (tmp_path.parent / "escape").exists()


@pytest.mark.parametrize("bad", ["My Story", "a/b", "", ".."])
def test_project_slug_rejects_spaces_and_slashes(tmp_path, bad):
    with pytest.raises(ValueError, match="alphanumeric"):
        _create(bad, tmp_path)


def test_valid_project_slug_still_works(tmp_path):
    assert _create("my-story_2", tmp_path)["success"] is True
    assert (tmp_path / "projects" / "my-story_2" / ".story" / "story.db").exists()
