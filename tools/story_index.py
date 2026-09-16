"""story_index tool — regenerate project index."""
import json
from pathlib import Path
from core.index import generate_index, write_index

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
    from .story_resolve import resolve_project
    
    _vault = kwargs.get("vault_path")
    if _vault:
        vault_path = Path(_vault)
    else:
        from core.config import load_plugin_config
        config = load_plugin_config()
        vault_path = Path(config.get("vault_path", "~/story-vault")).expanduser()
    project = args["project"]
    
    try:
        project_path = resolve_project(project, vault_path)
    except ValueError as e:
        return json.dumps({"error": str(e)})

    # Check required files exist (don't auto-create)
    project_md = project_path / "project.md"
    if not project_md.exists():
        return json.dumps({"error": f"project.md not found at {project_path}. Create with story_create(entity_type='project', slug='{project_path.name}')"})
    
    memory_path = project_path / ".story" / "memory.md"
    if not memory_path.exists():
        return json.dumps({"error": f".story/memory.md not found. Create with story_create(entity_type='project', slug='{project_path.name}')"})
    
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
