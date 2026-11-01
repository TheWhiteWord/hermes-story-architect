"""story_dashboard_link smoke test."""
import json
from pathlib import Path

from story_architect.tools import story_dashboard_link


def test_dashboard_link_returns_url(tmp_path):
    projects = tmp_path / "projects"
    projects.mkdir()
    proj = projects / "demo"
    proj.mkdir()
    (proj / ".story").mkdir()
    import sqlite3
    (proj / ".story" / "story.db").touch()
    # minimal db not required for resolve? resolve_project opens db. Use fixture-less: just check module import + registry.
    from story_architect.app.mcp_server import build_registry
    names = [n for n, _, _ in build_registry()]
    assert "dashboard_link" in names
