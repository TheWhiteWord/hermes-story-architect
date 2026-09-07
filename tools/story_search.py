"""story_search tool — search within a project."""
import json
from pathlib import Path
from ..core.constants import ENTITY_FOLDERS

SCHEMA = {
    "type": "object",
    "properties": {
        "project": {
            "type": "string",
            "description": "Project slug or name"
        },
        "query": {
            "type": "string",
            "description": "Search query"
        }
    },
    "required": ["project", "query"]
}


def handler(args: dict, **kwargs) -> str:
    """Search across project notes."""
    from .. import load_plugin_config
    from .story_resolve import resolve_project
    
    config = load_plugin_config()
    vault_path = Path(config.get("vault_path", "~/story-vault")).expanduser()
    project = args["project"]
    query = args["query"].lower()
    
    try:
        project_path = resolve_project(project, vault_path)
    except ValueError as e:
        return json.dumps({"error": str(e)})
    
    results = []
    
    # Search all entity folders
    for entity_type, folder in ENTITY_FOLDERS.items():
        folder_path = project_path / folder
        if not folder_path.exists():
            continue
        for note in folder_path.glob("*.md"):
            if note.name.startswith("_"):
                continue
            content = note.read_text()
            if query in content.lower():
                # Find matching lines
                lines = content.split('\n')
                matches = [
                    f"{i+1}: {line}"
                    for i, line in enumerate(lines)
                    if query in line.lower()
                ]
                results.append({
                    "entity_type": entity_type,
                    "slug": note.stem,
                    "matches": matches[:5]  # Cap at 5 matches per file
                })
    
    return json.dumps({
        "query": args["query"],
        "results": results,
        "total": len(results)
    })
