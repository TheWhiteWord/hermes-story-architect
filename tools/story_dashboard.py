"""story_dashboard tool — open project dashboard in preview pane."""
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
    """Open project dashboard in the preview pane."""
    from .. import load_plugin_config
    from .story_resolve import resolve_project

    config = load_plugin_config()
    vault_path = Path(config.get("vault_path", "~/story-vault")).expanduser()
    project = args["project"]

    try:
        project_path = resolve_project(project, vault_path)
    except ValueError as e:
        return json.dumps({"error": str(e)})

    # Dashboard is auto-created by story_index
    dashboard_dest = project_path / "story-dashboard.html"
    if not dashboard_dest.exists():
        return json.dumps({"error": "Dashboard not found. Run story_index first."})

    return json.dumps({
        "success": True,
        "message": f"Dashboard opened for {project}",
        "dashboard_url": f"file://{dashboard_dest}",
        "project": project
    })
