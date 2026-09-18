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
            return _db_response(summary, project_path)
    except Exception as e:
        return json.dumps({"error": str(e)})
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass

    return json.dumps({"error": "Failed to load project summary."})


def _db_response(summary: dict, project_path: Path) -> str:
    """Build JSON response from DB summary."""
    project = summary.get("project", {})
    entities = summary.get("entities", {"cols": [], "rows": []})
    relations = summary.get("relations", {"cols": [], "rows": []})

    # Count by entity type for confirmation message
    type_counts = {}
    for row in entities.get("rows", []):
        # cols: id, type, name, one_sentence, status, order_key, parent_id, location_id, extra
        if len(row) > 1:
            t = row[1]
            type_counts[t] = type_counts.get(t, 0) + 1

    confirmation = (
        f"Loaded {project.get('name', 'Unknown')} — "
        f"{type_counts.get('arc', 0)} arc beats, "
        f"{type_counts.get('scene', 0)} scenes, "
        f"{type_counts.get('sequence', 0)} sequences, "
        f"{type_counts.get('act', 0)} acts, "
        f"{type_counts.get('character', 0)} characters, "
        f"{type_counts.get('location', 0)} locations, "
        f"{type_counts.get('plot', 0)} plots."
    )

    # Read memory
    memory_path = project_path / ".story" / "memory.md"
    memory = ""
    if memory_path.exists():
        memory = memory_path.read_text()

    return json.dumps({
        "loaded": True,
        "confirmation": confirmation,
        "project": project,
        "entities": entities,
        "relations": relations,
        "memory": memory,
    })
