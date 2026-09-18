"""story_search tool — search within a project."""
import json
from pathlib import Path

SCHEMA = {
    "type": "object",
    "properties": {
        "project": {
            "type": "string",
            "description": "Project slug or name"
        },
        "query": {
            "type": "string",
            "description": "Search query"
        }
    },
    "required": ["project", "query"]
}


def handler(args: dict, **kwargs) -> str:
    """Search across project notes."""
    from core.config import load_plugin_config
    from .story_resolve import resolve_project

    config = load_plugin_config()
    vault_path = Path(config.get("vault_path", "~/story-vault")).expanduser()
    project = args["project"]
    query = args["query"]

    try:
        project_path = resolve_project(project, vault_path)
    except ValueError as e:
        return json.dumps({"error": str(e)})

    # Phase 2: Try FTS5 first
    db_path = project_path / ".story" / "story.db"
    if db_path.exists():
        from core.db import has_schema, search_sections
        import sqlite3
        conn = None
        try:
            conn = sqlite3.connect(str(db_path))
            if has_schema(conn):
                results = search_sections(project_path, query)
                conn.close()
                return json.dumps({
                    "query": query,
                    "results": results,
                    "total": len(results)
                })
        except Exception:
            pass
        finally:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass

    # No DB or no schema — error
    return json.dumps({"error": "Database not found. Run story_import first."})
