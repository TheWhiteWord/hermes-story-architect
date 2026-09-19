"""story_load tool — load a project's index and memory into context."""
import json
from pathlib import Path


SCHEMA = {
    "type": "object",
    "properties": {
        "project": {
            "type": "string",
            "description": "Project slug or name"
        }
    },
    "required": ["project"]
}


def handler(args: dict, **kwargs) -> str:
    """Load project index and memory into context."""
    from .story_resolve import resolve_project

    _vault = kwargs.get("vault_path")
    if _vault:
        vault_path = Path(_vault)
    else:
        from core.config import load_plugin_config
        config = load_plugin_config()
        vault_path = Path(config.get("vault_path", "~/story-vault")).expanduser()
    project = args["project"]

    # Resolve project
    try:
        project_path = resolve_project(project, vault_path)
    except ValueError as e:
        return json.dumps({"error": str(e)})

    # DB is source of truth
    db_path = project_path / ".story" / "story.db"
    if not db_path.exists():
        return json.dumps({"error": "Database not found. Run story_import first."})

    from core.db import has_schema
    from core.db import get_project_summary
    import sqlite3
    conn = None
    try:
        conn = sqlite3.connect(str(db_path))
        if not has_schema(conn):
            return json.dumps({"error": "Database schema not found. Run story_import first."})
        summary = get_project_summary(project_path)
        if summary:
            return json.dumps(summary)
    except Exception as e:
        return json.dumps({"error": str(e)})
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass

    return json.dumps({"error": "Failed to load project summary."})
