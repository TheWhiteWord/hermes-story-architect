"""story_index tool — regenerate project index."""
import json
from pathlib import Path
from ..core.index import generate_index, write_index

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
    """Regenerate project index."""
    from .. import load_plugin_config
    from .story_resolve import resolve_project
    
    config = load_plugin_config()
    vault_path = Path(config.get("vault_path", "~/story-vault")).expanduser()
    project = args["project"]
    
    try:
        project_path = resolve_project(project, vault_path)
    except ValueError as e:
        return json.dumps({"error": str(e)})

    # Initialize project.md if missing (marker file)
    project_md = project_path / "project.md"
    if not project_md.exists():
        project_md.write_text(
            f"---\n"
            f"name: {project_path.name}\n"
            f"---\n"
            f"\n"
            f"# {project_path.name}\n"
            f"\n"
        )

    # Initialize memory.md if missing
    memory_dir = project_path / ".story"
    if not memory_dir.exists():
        memory_dir.mkdir(parents=True, exist_ok=True)
    memory_path = memory_dir / "memory.md"
    if not memory_path.exists():
        memory_path.write_text("# Story Memory\n\n")

    # Copy dashboard HTML to project folder
    dashboard_src = Path(__file__).parent.parent / "src" / "dashboard" / "story-dashboard.html"
    dashboard_dest = project_path / "story-dashboard.html"
    if dashboard_src.exists() and not dashboard_dest.exists():
        import shutil
        shutil.copy2(dashboard_src, dashboard_dest)

    # Generate index
    index = generate_index(project_path)

    # Write index
    index_path = project_path / ".story" / "index.yaml"
    index_path.parent.mkdir(exist_ok=True)
    write_index(index, index_path)
    
    return json.dumps({
        "success": True,
        "message": f"Index regenerated for {index['project']['name']}",
        "index": index
    })
