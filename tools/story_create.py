"""story_create tool — create new entities."""
import json
from pathlib import Path
from ..core.constants import ENTITY_FOLDERS, REQUIRED_FIELDS

SCHEMA = {
    "type": "object",
    "properties": {
        "entity_type": {
            "type": "string",
            "enum": ["character", "location", "world", "plot"],
            "description": "Type of entity to create"
        },
        "slug": {
            "type": "string",
            "description": "Entity slug (unique identifier)"
        },
        "frontmatter": {
            "type": "object",
            "description": "Frontmatter fields"
        }
    },
    "required": ["entity_type", "slug", "project", "frontmatter"]
}


def handler(args: dict, **kwargs) -> str:
    """Create new entity note."""
    from .. import load_plugin_config
    from .story_resolve import resolve_project
    
    config = load_plugin_config()
    vault_path = Path(config.get("vault_path", "~/story-vault")).expanduser()
    
    entity_type = args["entity_type"]
    slug = args["slug"]
    frontmatter_data = args["frontmatter"]
    
    # Validate slug
    if not slug.replace("-", "").replace("_", "").isalnum():
        return json.dumps({"error": "Slug must be alphanumeric with hyphens/underscores only"})
    
    # Resolve project
    try:
        project_path = resolve_project(args.get("project", ""), vault_path)
    except ValueError as e:
        return json.dumps({"error": str(e)})
    
    # Check if entity already exists
    folder = ENTITY_FOLDERS[entity_type]
    file_path = project_path / folder / f"{slug}.md"
    if file_path.exists():
        return json.dumps({"error": f"Entity already exists: {entity_type}/{slug}"})
    
    # Generate frontmatter
    import frontmatter
    post = frontmatter.Post("", **frontmatter_data)
    
    # Add standard sections based on entity type
    sections = _get_standard_sections(entity_type)
    if sections:
        post.content = "\n\n".join(f"## {s}\n" for s in sections)
    
    # Ensure folder exists
    file_path.parent.mkdir(exist_ok=True)
    
    # Write file
    with open(file_path, 'w') as f:
        frontmatter.dump(post, f)

    # Refresh index so story_load reflects changes immediately
    try:
        from ..core.index import generate_index, write_index
        index_path = project_path / ".story" / "index.yaml"
        index = generate_index(project_path)
        write_index(index, index_path)
    except Exception:
        pass

    return json.dumps({
        "success": True,
        "message": f"Created {entity_type}: {slug}",
        "file": str(file_path)
    })


def _get_standard_sections(entity_type: str) -> list[str]:
    """Get standard sections for an entity type."""
    sections = {
        "character": ["Personality", "Background", "Voice", "Greatest Fear", "Secrets", "Arc", "Relationships", "Goals"],
        "location": ["Description", "History", "Scenes"],
        "world": ["Description", "History", "Conflict"],
        "plot": ["Summary", "Obstacles", "Stakes"],
    }
    return sections.get(entity_type, [])
