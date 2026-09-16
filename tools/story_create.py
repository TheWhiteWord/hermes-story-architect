"""story_create tool — create new entities."""
import json
from pathlib import Path
from core.constants import ENTITY_SCHEMAS
from core.paths import build_entity_path, find_entity_path


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
                "enum": ["project", "character", "location", "world", "plot", "scene", "sequence", "act", "arc"],
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
    
    _vault = kwargs.get("vault_path")
    if _vault:
        vault_path = Path(_vault)
    else:
        config = load_plugin_config()
        vault_path = Path(config.get("vault_path", "~/story-vault")).expanduser()
    
    entity_type = args["entity_type"]
    slug = args["slug"]
    frontmatter_data = args["frontmatter"]
    
    # Project creation is special — initializes the full project structure
    if entity_type == "project":
        return _create_project(slug, frontmatter_data, vault_path)
    
    # Validate slug
    if not slug.replace("-", "").replace("_", "").isalnum():
        return json.dumps({"error": "Slug must be alphanumeric with hyphens/underscores only"})
    
    # Resolve project
    try:
        project_path = resolve_project(args.get("project", ""), vault_path)
    except ValueError as e:
        return json.dumps({"error": str(e)})
    
    # Build path (handles flat + nested via core/paths.py)
    file_path = build_entity_path(project_path, entity_type, slug, frontmatter_data)
    if file_path.exists():
        return json.dumps({"error": f"Entity already exists: {entity_type}/{slug}"})
    
    # Generate frontmatter — merge over schema defaults so all fields are present
    import frontmatter
    schema = ENTITY_SCHEMAS.get(entity_type, {})
    merged = {field: frontmatter_data.get(field, meta["default"]) for field, meta in schema.items()}

    # Parent validation for arc type
    if entity_type == "arc":
        if frontmatter_data.get("character") and not _entity_exists(project_path, "character", frontmatter_data["character"]):
            return json.dumps({"error": f"Character not found: {frontmatter_data['character']}"})
        if frontmatter_data.get("scene") and not _entity_exists(project_path, "scene", frontmatter_data["scene"]):
            return json.dumps({"error": f"Scene not found: {frontmatter_data['scene']}"})

    # Parent validation + auto-order for structural types
    if entity_type in ("scene", "sequence"):
        try:
            _validate_parents(project_path, entity_type, merged)
        except ValueError as e:
            return json.dumps({"error": str(e)})
        if merged.get("order", 0) == 0:
            parent = "sequence" if entity_type == "scene" else "act"
            parent_id = merged.get("sequence_id") or merged.get("act_id")
            if parent_id:
                merged["order"] = _get_next_order(project_path, parent, parent_id)

    post = frontmatter.Post("", **merged)
    
    # Add standard sections based on entity type
    sections = _get_standard_sections(entity_type)
    if sections:
        post.content = "\n\n".join(f"## {s}\n" for s in sections)
    
    # Ensure folder exists (parents=True for nested entities like arcs/{character}/)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Write file
    with open(file_path, 'w') as f:
        frontmatter.dump(post, f)

    # Refresh index so story_load reflects changes immediately
    try:
        from core.index import refresh_index
        refresh_index(project_path)
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


def _create_project(slug, frontmatter_data, vault_path):
    """Create a new project with full scaffolding."""
    import frontmatter
    
    project_path = vault_path / "projects" / slug
    
    # Check if project already exists
    if (project_path / "project.md").exists():
        return json.dumps({"error": f"Project already exists: {slug}"})
    
    # Validate required fields
    schema = ENTITY_SCHEMAS.get("project", {})
    required = [f for f, meta in schema.items() if not meta.get("optional", True)]
    missing = [f for f in required if not frontmatter_data.get(f)]
    if missing:
        return json.dumps({
            "error": f"Missing required fields for project: {', '.join(missing)}"
        })
    
    # Merge frontmatter over schema defaults
    merged = {field: frontmatter_data.get(field, meta["default"]) for field, meta in schema.items()}
    
    # Create project.md with standard sections
    project_path.mkdir(parents=True, exist_ok=True)
    post = frontmatter.Post("", **merged)
    sections = _get_standard_sections("project")
    post.content = "\n".join(f"## {s}\n" for s in sections)
    with open(project_path / "project.md", 'w') as f:
        frontmatter.dump(post, f)
    
    # Create .story/memory.md with standard sections
    memory_dir = project_path / ".story"
    memory_dir.mkdir(parents=True, exist_ok=True)
    memory_content = "\n\n".join([
        "# Story Memory",
        "## Continuity notes\n",
        "## Character knowledge\n",
        "## World events\n",
        "## Open questions\n",
    ])
    (memory_dir / "memory.md").write_text(memory_content)
    
    # Create entity folders
    for folder in ["characters", "locations", "worlds", "plots", "scenes", "sequences", "acts", "arcs"]:
        (project_path / folder).mkdir(exist_ok=True)
    
    # Generate initial index
    from core.index import generate_index, write_index
    index = generate_index(project_path)
    write_index(index, memory_dir / "index.yaml")
    
    return json.dumps({
        "success": True,
        "message": f"Created project: {slug}",
        "file": str(project_path / "project.md")
    })


def _validate_parents(project_path: Path, entity_type: str, frontmatter: dict) -> None:
    """Raise ValueError if referenced parents don't exist."""
    if entity_type == "scene":
        if frontmatter.get("sequence_id") and not _entity_exists(project_path, "sequence", frontmatter["sequence_id"]):
            raise ValueError(f"Sequence not found: {frontmatter['sequence_id']}")
        if frontmatter.get("act_id") and not _entity_exists(project_path, "act", frontmatter["act_id"]):
            raise ValueError(f"Act not found: {frontmatter['act_id']}")
    elif entity_type == "sequence":
        if frontmatter.get("act_id") and not _entity_exists(project_path, "act", frontmatter["act_id"]):
            raise ValueError(f"Act not found: {frontmatter['act_id']}")


def _get_next_order(project_path: Path, parent_type: str, parent_id: str) -> int:
    """Compute the next order value for a new child within its parent."""
    folder = "scenes" if parent_type == "sequence" else "sequences"
    field = "sequence_id" if parent_type == "sequence" else "act_id"
    child_dir = project_path / folder
    if not child_dir.exists():
        return 1
    import frontmatter
    max_order = 0
    for note in child_dir.glob("*.md"):
        if note.name.startswith("_"):
            continue
        post = frontmatter.load(note)
        if post.get(field) == parent_id:
            order = post.get("order", 0)
            if isinstance(order, (int, float)) and order > max_order:
                max_order = order
    return int(max_order) + 1


def _entity_exists(project_path: Path, entity_type: str, slug: str) -> bool:
    """Check if an entity file exists."""
    if not slug:
        return False
    return find_entity_path(project_path, entity_type, slug) is not None


def _get_standard_sections(entity_type: str) -> list[str]:
    """Get standard sections for an entity type."""
    sections = {
        "project": ["Synopsis", "Themes", "Structure", "Notes"],
        "character": ["Personality", "Background", "Voice", "Greatest Fear", "Secrets", "Arc", "Relationships", "Goals"],
        "location": ["Description", "History", "Scenes"],
        "world": ["Description", "History", "Conflict"],
        "plot": ["Summary", "Obstacles", "Stakes"],
        "scene": ["Description", "Dramatic Function", "Notes", "Content"],
        "sequence": ["Summary", "Scene Order", "Notes"],
        "act": ["Summary", "Thematic Function", "Notes"],
        "arc": ["Action", "Gap", "Choice", "Shift", "Development Log"],
    }
    return sections.get(entity_type, [])
