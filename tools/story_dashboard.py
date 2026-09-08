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
    "required": ["project"],
    "description": "Open the story dashboard in the preview pane. After calling this tool, pass the returned dashboard_url to desktop_preview(action=open, url=...) so the user can see it."
}


def handler(args: dict, **kwargs) -> str:
    """Open project dashboard in the preview pane."""
    import tempfile
    import yaml

    from .. import load_plugin_config
    from .story_resolve import resolve_project

    config = load_plugin_config()
    vault_path = Path(config.get("vault_path", "~/story-vault")).expanduser()
    project = args["project"]

    try:
        project_path = resolve_project(project, vault_path)
    except ValueError as e:
        return json.dumps({"error": str(e)})

    index_path = project_path / ".story" / "index.yaml"
    if not index_path.exists():
        return json.dumps({"error": "Index not found. Run story_index first."})

    dashboard_src = Path(__file__).parent.parent / "src" / "dashboard" / "story-dashboard.html"
    if not dashboard_src.exists():
        return json.dumps({"error": "Dashboard file not found in plugin"})

    # Read index.yaml, convert to JSON, inject inline — avoids fetch('file://') which Electron blocks
    yaml_data = yaml.safe_load(index_path.read_text(encoding="utf-8"))
    html = dashboard_src.read_text(encoding="utf-8")

    injection = f"window.__STORY_DATA__ = {json.dumps(yaml_data)};"
    html = html.replace(
        "// ─── Boot ─────────────────────────────────────────────────────────────────────",
        injection + "\n// ─── Boot ─────────────────────────────────────────────────────────────────────",
    )

    # Name temp file after the story title
    project_name = (yaml_data.get("project", {}).get("name") or project).strip()
    safe_name = "".join(c if c.isalnum() or c in " -_" else "_" for c in project_name).strip().replace(" ", "_")
    tmp_dir = Path(tempfile.gettempdir())
    tmp_path = tmp_dir / f"{safe_name}.html"
    tmp_path.write_text(html, encoding="utf-8")

    return json.dumps({
        "success": True,
        "message": f"Dashboard opened for {project}",
        "dashboard_url": f"file://{tmp_path}",
        "project": project,
    })
