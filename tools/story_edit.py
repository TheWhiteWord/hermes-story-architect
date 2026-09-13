"""story_edit tool — propose and apply edits (action protocol)."""
import json
from pathlib import Path
from core.constants import ENTITY_FOLDERS, ENTITY_SCHEMAS
from core.section_parser import replace_section

SCHEMA = {
    "type": "object",
    "properties": {
        "action": {
            "type": "string",
            "enum": ["edit_note", "edit_screenplay", "delete_entity", "update_story_memory", "create_entity", "reorder"],
            "description": "Action type"
        },
        "target": {
            "type": "object",
            "properties": {
                "entity_type": {"type": "string"},
                "slug": {"type": "string"}
            }
        },
        "data": {
            "type": "object",
            "description": "Key-value edits: frontmatter fields and/or section names"
        },
        "order_context": {
            "type": "object",
            "description": "For reorder: ordered list of slugs defining new order",
            "properties": {
                "ordered_ids": {
                    "type": "array",
                    "items": {"type": "string"}
                }
            }
        },
        "summary": {
            "type": "string",
            "description": "Human-readable summary of the edit"
        }
    },
    "required": ["action", "target", "summary"]
}


def handler(args: dict, **kwargs) -> str:
    """Apply edit to project note."""
    from core.config import load_plugin_config
    from .story_resolve import resolve_project
    
    config = load_plugin_config()
    vault_path = Path(config.get("vault_path", "~/story-vault")).expanduser()
    
    action = args["action"]
    target = args["target"]
    changes = args.get("changes", [])
    data = args.get("data", {})
    summary = args["summary"]
    
    # Resolve project
    try:
        project_path = resolve_project(target.get("project", ""), vault_path)
    except ValueError as e:
        return json.dumps({"error": str(e)})
    
    if action == "edit_note":
        result = _edit_note(project_path, target, data, summary)
    elif action == "edit_screenplay":
        return _edit_screenplay(project_path, changes, summary)
    elif action == "delete_entity":
        result = _delete_entity(project_path, target, summary)
    elif action == "create_entity":
        result = _create_entity(project_path, target, data, summary)
    elif action == "update_story_memory":
        result = _update_story_memory(project_path, data, summary)
    elif action == "reorder":
        order_context = args.get("order_context", {})
        result = _reorder(project_path, target, order_context, summary)
    else:
        return json.dumps({"error": f"Unknown action: {action}"})

    # Refresh index so story_load reflects changes
    try:
        _refresh_index(project_path)
    except Exception as e:
        # Report failure but don't override the original result
        if '"success": true' in result:
            result = result.replace('"success": true', f'"success": true, "index_warning": "{e}"')

    return result


def _refresh_index(project_path: Path) -> None:
    """Refresh the index file to reflect changes.
    Ensures .story/ directory exists before writing.
    Raises exceptions on failure."""
    from core.index import refresh_index
    refresh_index(project_path)


def _edit_note(project_path: Path, target: dict, data: dict, summary: str) -> str:
    """Edit an entity note using data bag. Key ∈ schema fields → frontmatter update. Key ∈ standard sections → body section update."""
    import frontmatter
    
    entity_type = target.get("entity_type") or ""
    slug = target.get("slug") or ""
    folder = ENTITY_FOLDERS.get(entity_type, "")
    file_path = project_path / folder / f"{slug}.md"
    
    if not file_path.exists():
        return json.dumps({"error": f"Entity not found: {entity_type}/{slug}"})

    post = frontmatter.load(file_path)
    schema_fields = set(ENTITY_SCHEMAS.get(entity_type, {}).keys())
    standard_sections = set(_get_standard_sections(entity_type))
    
    for key, value in data.items():
        if key in schema_fields:
            post[key] = value
        elif key in standard_sections:
            post.content = replace_section(post.content, key, value)

    with open(file_path, 'w') as f:
        frontmatter.dump(post, f)

    # Lightweight structure-index update for scenes (O(1) vs O(N) rebuild)
    if entity_type == "scene":
        from core.index import update_structure_index_scene
        update_structure_index_scene(project_path, slug)

    return json.dumps({
        "success": True,
        "message": f"Applied: {summary}",
        "file": str(file_path)
    })


def _edit_screenplay(project_path: Path, changes: list, summary: str) -> str:
    """Edit screenplay.fountain."""
    from core.screenplay import extract_scenes
    from core.fountain_lexer import tokenize
    
    screenplay_path = project_path / "screenplay.fountain"
    if not screenplay_path.exists():
        return json.dumps({"error": "screenplay.fountain not found"})
    
    content = screenplay_path.read_text()
    tokens = tokenize(content)
    
    # Apply changes (simplified — full implementation would modify tokens)
    for change in changes:
        # TODO: implement screenplay editing logic
        pass
    
    # Reconstruct fountain text from tokens
    lines = []
    for token in tokens:
        if token['type'] not in ('separator', 'dialogue_begin', 'dialogue_end', 'dual_dialogue_begin', 'dual_dialogue_end'):
            lines.append(token['text'])
    
    new_content = '\n'.join(lines)
    screenplay_path.write_text(new_content)
    
    return json.dumps({
        "success": True,
        "message": f"Applied: {summary}",
        "file": str(screenplay_path)
    })


def _reorder(project_path: Path, target: dict, order_context: dict, summary: str) -> str:
    """Reorder scenes/sequences within their parent by renumbering order fields.

    The LLM provides the complete new ordering. All items must exist and
    belong to the same parent; order is renumbered 1, 2, 3, ... from the list.
    """
    import frontmatter

    entity_type = target.get("entity_type")
    if entity_type not in ("scene", "sequence"):
        return json.dumps({"error": f"Reorder not supported for {entity_type}"})

    ordered_ids = order_context.get("ordered_ids", [])
    if not ordered_ids:
        return json.dumps({"error": "order_context.ordered_ids required"})

    folder = ENTITY_FOLDERS[entity_type]
    parent_field = "sequence_id" if entity_type == "scene" else "act_id"

    # Determine parent from first item
    first_path = project_path / folder / f"{ordered_ids[0]}.md"
    if not first_path.exists():
        return json.dumps({"error": f"{entity_type} not found: {ordered_ids[0]}"})

    first_post = frontmatter.load(first_path)
    parent_id = first_post.get(parent_field, "")

    if not parent_id:
        return json.dumps({"error": f"{entity_type} {ordered_ids[0]} has no parent"})

    # Verify all items exist and belong to same parent
    for item_id in ordered_ids:
        note_path = project_path / folder / f"{item_id}.md"
        if not note_path.exists():
            return json.dumps({"error": f"{entity_type} not found: {item_id}"})
        post = frontmatter.load(note_path)
        if post.get(parent_field) != parent_id:
            return json.dumps({"error": f"{item_id} does not belong to {parent_id}"})

    # Renumber: 1, 2, 3, ...
    for i, item_id in enumerate(ordered_ids, 1):
        note_path = project_path / folder / f"{item_id}.md"
        post = frontmatter.load(note_path)
        post["order"] = i
        with open(note_path, "w") as f:
            frontmatter.dump(post, f)

    return json.dumps({
        "success": True,
        "message": f"Reordered {len(ordered_ids)} {entity_type}(s) in {parent_id}: {summary}"
    })


def _delete_entity(project_path: Path, target: dict, summary: str) -> str:
    """Move entity to _recycle-bin/. Blocks if structural types have children."""
    import shutil
    import frontmatter

    entity_type = target.get("entity_type") or ""
    slug = target.get("slug") or ""
    folder = ENTITY_FOLDERS.get(entity_type, "")
    file_path = project_path / folder / f"{slug}.md"

    if not file_path.exists():
        return json.dumps({"error": f"Entity not found: {entity_type}/{slug}"})

    # Cascade blocking for structural types (containment hierarchy)
    try:
        if entity_type == "sequence":
            _check_no_children(project_path, "scenes", "sequence_id", slug, "scene")
        elif entity_type == "act":
            _check_no_children(project_path, "sequences", "act_id", slug, "sequence")
    except ValueError as e:
        return json.dumps({"error": str(e)})
    # Non-structural types (character, location, world, plot): no cascade check

    # Move to recycle bin
    recycle_bin = project_path / "_recycle-bin" / entity_type
    recycle_bin.mkdir(parents=True, exist_ok=True)

    dest = recycle_bin / f"{slug}.md"
    shutil.move(str(file_path), str(dest))

    return json.dumps({
        "success": True,
        "message": f"Moved to recycle bin: {summary}",
        "file": str(dest)
    })


def _check_no_children(project_path: Path, child_folder: str, parent_field: str, parent_id: str, child_name: str) -> None:
    """Raise ValueError if any children reference this parent."""
    import frontmatter

    child_dir = project_path / child_folder
    if not child_dir.exists():
        return
    children = []
    for note in child_dir.glob("*.md"):
        if note.name.startswith("_"):
            continue
        post = frontmatter.load(note)
        if post.get(parent_field) == parent_id:
            children.append(post.get("id", note.stem))
    if children:
        raise ValueError(
            f"Cannot delete: {len(children)} {child_name}(s) reference this: {', '.join(children[:5])}"
        )


def _create_entity(project_path: Path, target: dict, data: dict, summary: str) -> str:
    """Create a new entity note."""
    import frontmatter

    entity_type = target.get("entity_type", "")
    slug = target.get("slug", "")
    frontmatter_data = target.get("frontmatter", {})
    folder = ENTITY_FOLDERS.get(entity_type, "")
    file_path = project_path / folder / f"{slug}.md"

    if file_path.exists():
        return json.dumps({"error": f"Entity already exists: {entity_type}/{slug}"})

    # Generate frontmatter — merge over schema defaults so all fields are present
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
    _refresh_index(project_path)

    return json.dumps({
        "success": True,
        "message": f"Applied: {summary}",
        "file": str(file_path)
    })


def _update_story_memory(project_path: Path, data: dict, summary: str) -> str:
    """Update the story memory file using data bag. All keys are body sections (memory.md has no frontmatter schema)."""
    import frontmatter
    memory_path = project_path / ".story" / "memory.md"

    if not memory_path.exists():
        return json.dumps({"error": "memory.md not found"})

    post = frontmatter.load(memory_path)

    for key, value in data.items():
        post.content = replace_section(post.content, key, value)

    with open(memory_path, 'w') as f:
        frontmatter.dump(post, f)

    return json.dumps({
        "success": True,
        "message": f"Updated story memory: {summary}",
        "file": str(memory_path)
    })


def _get_standard_sections(entity_type: str) -> list[str]:
    """Get standard sections for an entity type."""
    sections = {
        "character": ["Personality", "Background", "Voice", "Greatest Fear", "Secrets", "Arc", "Relationships", "Goals"],
        "location": ["Description", "History", "Scenes"],
        "world": ["Description", "History", "Conflict"],
        "plot": ["Summary", "Obstacles", "Stakes"],
        "scene": ["Description", "Dramatic Function", "Notes", "Content"],
        "sequence": ["Summary", "Scene Order", "Notes"],
        "act": ["Summary", "Thematic Function", "Notes"],
    }
    return sections.get(entity_type, [])
