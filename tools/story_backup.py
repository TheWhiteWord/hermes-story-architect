"""story_backup tool — create timestamped .db backup."""
import json
from pathlib import Path

SCHEMA = {
    "description": "Copy the project database to a timestamped file. The database holds every "
                   "write — story_draft commits and story_memory all persist there, and the "
                   "Markdown files are only a stale export. Take one before a delete, and "
                   "before finishing a working session. Note: a backup can be copied but NOT "
                   "restored by any tool yet.",
    "type": "object",
    "properties": {
        "project": {"type": "string", "description": "Project slug or path"},
    },
    "required": ["project"],
}


def handler(args, **kwargs) -> str:
    """Backup story.db to a timestamped copy."""
    from .story_resolve import resolve_project
    from core.config import resolve_root

    root_path = resolve_root(kwargs)

    try:
        project_path = resolve_project(args["project"], root_path)
    except ValueError as e:
        return json.dumps({"error": str(e)})

    db_path = project_path / ".story" / "story.db"
    if not db_path.exists():
        return json.dumps({"error": "No story.db found. Run story_import first."})

    from core.db import backup_database
    backup_path = backup_database(project_path)

    return json.dumps({
        "success": True,
        "message": f"Backed up to {Path(backup_path).name}",
        "backup": backup_path,
    })
