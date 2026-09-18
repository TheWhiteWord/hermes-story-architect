"""story_backup tool — create timestamped .db backup."""
import json
import shutil
from datetime import datetime
from pathlib import Path

SCHEMA = {
    "type": "object",
    "properties": {
        "project": {"type": "string", "description": "Project slug or path"},
    },
    "required": ["project"],
}


def handler(args, **kwargs) -> str:
    """Backup story.db to a timestamped copy."""
    from .story_resolve import resolve_project
    from core.config import load_plugin_config

    vault = kwargs.get("vault_path")
    if vault:
        vault_path = Path(vault)
    else:
        config = load_plugin_config()
        vault_path = Path(config.get("vault_path", "~/story-vault")).expanduser()

    try:
        project_path = resolve_project(args["project"], vault_path)
    except ValueError as e:
        return json.dumps({"error": str(e)})

    db_path = project_path / ".story" / "story.db"
    if not db_path.exists():
        return json.dumps({"error": "No story.db found. Run story_import first."})

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = project_path / ".story" / f"story_{timestamp}.db"
    shutil.copy2(str(db_path), str(backup_path))

    return json.dumps({
        "success": True,
        "message": f"Backed up to {backup_path.name}",
        "backup": str(backup_path),
    })
