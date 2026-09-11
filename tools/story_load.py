"""story_load tool — load a project's index and memory into context."""
from pathlib import Path
from core.index import generate_index

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
    import json
    from core.config import load_plugin_config
    from rapidfuzz import fuzz, process
    from .story_resolve import resolve_project
    
    config = load_plugin_config()
    vault_path = Path(config.get("vault_path", "~/story-vault")).expanduser()
    project = args["project"]
    
    # Resolve project
    try:
        project_path = resolve_project(project, vault_path)
    except ValueError as e:
        return json.dumps({"error": str(e)})
    
    # Read index
    index_path = project_path / ".story" / "index.yaml"
    if not index_path.exists():
        return json.dumps({"error": "No index found. Run story_index first."})
    
    import yaml
    with open(index_path) as f:
        index = yaml.safe_load(f)
    
    # Read memory
    memory_path = project_path / ".story" / "memory.md"
    memory = ""
    if memory_path.exists():
        memory = memory_path.read_text()
    
    # Build confirmation
    confirmation = (
        f"Loaded {index['project']['name']} — "
        f"{len(index.get('scenes', []))} scenes, "
        f"{len(index.get('characters', []))} characters, "
        f"{len(index.get('locations', []))} locations, "
        f"{len(index.get('plots', []))} plots."
    )
    
    return json.dumps({
        "loaded": True,
        "project": index["project"],
        "confirmation": confirmation,
        "index": index,
        "memory": memory
    })
