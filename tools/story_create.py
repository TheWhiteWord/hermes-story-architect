"""story_create tool — create new entities."""
import json
from pathlib import Path
from core.constants import ENTITY_FOLDERS, REQUIRED_FIELDS, ENTITY_SCHEMAS


def _build_schema() -> dict:
    """Build JSON schema with field-level descriptions from ENTITY_SCHEMAS."""
    # Collect all unique fields across all entity types
    all_fields: dict[str, dict] = {}
    for entity_type, fields in ENTITY_SCHEMAS.items():
        for field, meta in fields.items():
            if field not in all_fields:
                all_fields[field] = {
                    "type": meta["type"],
                    "description": meta["description"],
                    "default": meta["default"],
                    "optional": meta.get("optional", True),
                    "_entity_types": [entity_type],
                }
                # Carry over sub_fields if present
                if "sub_fields" in meta:
                    all_fields[field]["sub_fields"] = meta["sub_fields"]
            else:
                all_fields[field]["_entity_types"].append(entity_type)

    # Build frontmatter properties
    frontmatter_props = {}
    for field, info in all_fields.items():
        field_schema = {
            "type": info["type"],
            "description": f"{info['description']} (used by: {', '.join(info['_entity_types'])})",
        }
        if info.get("default") != "":
            field_schema["default"] = info["default"]
        if not info.get("optional", True):
            field_schema["required"] = True
        # For list types with sub-fields, document items structure
        if info["type"] == "list" and "sub_fields" in info:
            field_schema["items"] = {
                "type": "object",
                "description": info["description"] + ". Sub-fields: " + ", ".join(info["sub_fields"].keys()),
                "properties": {
                    k: {"type": "number" if k == "number" else "string", "description": v}
                    for k, v in info["sub_fields"].items()
                },
            }
        frontmatter_props[field] = field_schema

    return {
        "type": "object",
        "properties": {
            "entity_type": {
                "type": "string",
                "enum": ["character", "location", "world", "plot"],
                "description": "Type of entity to create",
            },
            "slug": {
                "type": "string",
                "description": "Entity slug (unique identifier, used as filename)",
            },
            "project": {
                "type": "string",
                "description": "Project slug or path",
            },
            "frontmatter": {
                "type": "object",
                "description": "Frontmatter fields. Only include fields relevant to your entity type.",
                "properties": frontmatter_props,
            },
        },
        "required": ["entity_type", "slug", "project", "frontmatter"],
    }


SCHEMA = _build_schema()


def handler(args: dict, **kwargs) -> str:
    """Create new entity note."""
    from core.config import load_plugin_config
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
    
    # Generate frontmatter — merge over schema defaults so all fields are present
    import frontmatter
    schema = ENTITY_SCHEMAS.get(entity_type, {})
    merged = {field: frontmatter_data.get(field, meta["default"]) for field, meta in schema.items()}
    post = frontmatter.Post("", **merged)
    
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
        from core.index import generate_index, write_index
        index_path = project_path / ".story" / "index.yaml"
        index_path.parent.mkdir(exist_ok=True)
        index = generate_index(project_path)
        write_index(index, index_path)
    except Exception as e:
        return json.dumps({
            "success": True,
            "message": f"Created {entity_type}: {slug} (index refresh failed: {e})",
            "file": str(file_path)
        })

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
