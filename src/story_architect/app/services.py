"""Read services for the standalone app (framework-free)."""
from __future__ import annotations

from pathlib import Path

from story_architect.core.config import resolve_root
from story_architect.core.db import get_dashboard_data, has_schema
from story_architect.tools.story_resolve import resolve_project


class ProjectNotFound(Exception):
    pass


def list_projects(root) -> list[dict]:
    root = Path(root)
    projects_dir = root / "projects"
    if not projects_dir.exists():
        return []
    out = []
    for d in sorted(projects_dir.iterdir()):
        if not d.is_dir():
            continue
        db = d / ".story" / "story.db"
        meta = {"slug": d.name, "has_db": db.exists()}
        if db.exists():
            import sqlite3
            try:
                conn = sqlite3.connect(str(db))
                row = conn.execute("SELECT name FROM entities WHERE type='project' LIMIT 1").fetchone()
                conn.close()
                if row and row[0]:
                    meta["name"] = row[0]
            except Exception:
                pass
        out.append(meta)
    return out


def get_project_dashboard(root, slug) -> dict:
    root = Path(root)
    try:
        project_path = resolve_project(slug, root)
    except ValueError as e:
        raise ProjectNotFound(str(e))
    db_path = project_path / ".story" / "story.db"
    if not db_path.exists():
        raise ProjectNotFound(f"Database not found for {slug}")
    import sqlite3
    conn = sqlite3.connect(str(db_path))
    try:
        if not has_schema(conn):
            raise ProjectNotFound(f"Database schema not found for {slug}")
    finally:
        conn.close()
    data = get_dashboard_data(project_path)
    # screenplay stats previously computed in story_dashboard tool; recompute here
    scene_text = data.get("screenplay_text", "")
    scene_ids = data.get("screenplay_scene_ids", [])
    screenplay_stats = None
    if scene_text:
        try:
            from story_architect.app.stats import _compute_screenplay_stats
            screenplay_stats = _compute_screenplay_stats(scene_text, scene_ids=scene_ids)
        except Exception:
            screenplay_stats = None
    data["screenplay_stats"] = screenplay_stats
    return data
