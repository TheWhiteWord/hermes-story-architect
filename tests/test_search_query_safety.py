"""story_search must never report a broken query as a missing database.

Regression: FTS5 syntax errors were swallowed and returned as
"Database not found. Run story_import first." — which sends the agent to
story_import, and that wipes the DB.
"""
import json
import shutil
import tempfile
from pathlib import Path

import pytest

from tools.story_import import handler as import_handler
from tools.story_search import handler as search_handler


@pytest.fixture
def db_project(fixture_path):
    """Temp project with DB imported from the fixture."""
    tmp = tempfile.mkdtemp()
    proj = Path(tmp) / "projects" / "save-the-children"
    proj.parent.mkdir(parents=True)
    shutil.copytree(str(fixture_path), str(proj))
    import_handler({"project": str(proj), "root_path": Path(tmp)})
    yield proj, Path(tmp)
    shutil.rmtree(tmp, ignore_errors=True)


class TestSearchQuerySafety:
    def test_punctuation_does_not_error(self, db_project):
        proj, vault = db_project
        for query in ["garden (part 2)", 'the "garden', "Kael & Mira", "garden ^ 2"]:
            result = json.loads(search_handler({
                "project": str(proj), "query": query, "root_path": vault,
            }))
            assert "error" not in result, f"{query!r} -> {result}"

    def test_reports_total_when_truncated(self, db_project):
        proj, vault = db_project
        result = json.loads(search_handler({
            "project": str(proj), "query": "the", "root_path": vault, "limit": 2,
        }))
        assert result["total"] == 2
        assert result["total_matches"] >= result["total"]
        if result["total_matches"] > 2:
            assert "note" in result

    def test_snippet_is_bounded(self, db_project):
        proj, vault = db_project
        result = json.loads(search_handler({
            "project": str(proj), "query": "the", "root_path": vault,
        }))
        assert all(len(r["snippet"]) <= 205 for r in result["results"])
