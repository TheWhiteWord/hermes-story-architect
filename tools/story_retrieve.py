"""story_retrieve tool — get specific sections from project notes."""
import json
import frontmatter
from pathlib import Path
from core.constants import ENTITY_FOLDERS
from core.section_parser import get_section, list_sections

SCHEMA = {
    "type": "object",
    "properties": {
        "project": {
            "type": "string",
            "description": "Project slug or name"
        },
        "entity_type": {
            "type": "string",
            "enum": ["character", "location", "world", "plot", "project"],
            "description": "Type of entity"
        },
        "slug": {
            "type": "string",
            "description": "Entity slug"
        },
        "sections": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Section names to retrieve. Use ['all'] for all sections."
        }
    },
    "required": ["project", "entity_type", "slug", "sections"]
}


def handler(args: dict, **kwargs) -> str:
    """Retrieve specific sections from a story note."""
    from core.config import load_plugin_config
    from .story_resolve import resolve_project
    
    config = load_plugin_config()
    vault_path = Path(config.get("vault_path", "~/story-vault")).expanduser()
    project = args["project"]
    entity_type = args["entity_type"]
    slug = args["slug"]
    sections = args["sections"]
    
    # Resolve project path
    try:
        project_path = resolve_project(project, vault_path)
    except ValueError as e:
        return json.dumps({"error": str(e)})
    
    # Resolve file path
    folder = ENTITY_FOLDERS[entity_type]
    if entity_type == "project":
        file_path = project_path / "project.md"
    else:
        file_path = project_path / folder / f"{slug}.md"
    
    if not file_path.exists():
        return json.dumps({"error": f"Entity not found: {entity_type}/{slug}"})
    
    # Read file
    post = frontmatter.load(file_path)
    body = post.content
    
    # Retrieve sections
    if sections == ["all"]:
        return json.dumps({
            "entity_type": entity_type,
            "slug": slug,
            "sections": list_sections(body),
            "content": body
        })
    
    results = {}
    for section in sections:
        content = get_section(body, section)
        if content:
            results[section] = content
        else:
            available = list_sections(body)
            results[section] = f"Section '{section}' not found. Available: {available}"
    
    return json.dumps({
        "entity_type": entity_type,
        "slug": slug,
        "sections": results
    })
