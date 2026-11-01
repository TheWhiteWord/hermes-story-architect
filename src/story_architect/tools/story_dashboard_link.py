"""story_dashboard_link — return the app URL for a project's dashboard."""
import json

SCHEMA = {
    "description": "Return the URL of the app's dashboard for a project, so the owner can open it in a browser. Does not open a browser or render anything.",
    "type": "object",
    "properties": {
        "project": {
            "type": "string",
            "description": "Project slug or name (same resolution as other tools).",
        },
        "view": {
            "type": "string",
            "description": "Optional view/tab to append.",
        },
    },
    "required": ["project"],
}


def handler(args: dict, **kwargs) -> str:
    from story_architect.core.config import resolve_root
    from .story_resolve import resolve_project

    root_path = resolve_root(kwargs)
    project_path = resolve_project(args.get("project", ""), root_path)
    slug = project_path.name

    try:
        from story_architect.app.config import load_config
        port = load_config().port
    except Exception:
        port = 8731

    url = f"http://127.0.0.1:{port}/#/p/{slug}"
    if args.get("view"):
        url += f"/{args['view']}"
    return json.dumps({"success": True, "url": url, "slug": slug})
