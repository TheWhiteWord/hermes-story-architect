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

    # Check that index exists
    index_path = project_path / ".story" / "index.yaml"
    if not index_path.exists():
        return json.dumps({"error": "Index not found. Run story_index first."})

    # Dashboard is in the plugin src/ directory
    dashboard_src = Path(__file__).parent.parent / "src" / "dashboard" / "story-dashboard.html"
    if not dashboard_src.exists():
        return json.dumps({"error": "Dashboard file not found in plugin"})

    # Return URL with project path as query param
    dashboard_url = f"file://{dashboard_src}?project={project_path}"

    return json.dumps({
        "success": True,
        "message": f"Dashboard opened for {project}",
        "dashboard_url": dashboard_url,
        "project": project
    })
