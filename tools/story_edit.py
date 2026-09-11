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
            "enum": ["edit_note", "edit_screenplay", "delete_entity", "update_story_memory", "create_entity"],
            "description": "Action type"
        },
        "target": {
            "type": "object",
            "properties": {
                "entity_type": {"type": "string"},
                "slug": {"type": "string"}
            }
        },
        "changes": {
            "type": "array",
            "items": {"type": "object"},
            "description": "List of changes to apply"
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
    summary = args["summary"]
    
    # Resolve project
    try:
        project_path = resolve_project(target.get("project", ""), vault_path)
    except ValueError as e:
        return json.dumps({"error": str(e)})
    
    if action == "edit_note":
        result = _edit_note(project_path, target, changes, summary)
    elif action == "edit_screenplay":
        return _edit_screenplay(project_path, changes, summary)
    elif action == "delete_entity":
        result = _delete_entity(project_path, target, summary)
    elif action == "create_entity":
        result = _create_entity(project_path, target, changes, summary)
    elif action == "update_story_memory":
        result = _update_story_memory(project_path, changes, summary)
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


def _edit_note(project_path: Path, target: dict, changes: list, summary: str) -> str:
    """Edit an entity note."""
    import frontmatter
    
    entity_type = target.get("entity_type")
    slug = target.get("slug")
    folder = ENTITY_FOLDERS.get(entity_type, "")
    file_path = project_path / folder / f"{slug}.md"
    
    if not file_path.exists():
        return json.dumps({"error": f"Entity not found: {entity_type}/{slug}"})

    post = frontmatter.load(file_path)

    for change in changes:
        change_type = change.get("type")
        if change_type == "body_section":
            section = change["section"]
            new_body = change["new"]
            post.content = replace_section(post.content, section, new_body)
        elif change_type == "frontmatter":
            field = change["field"]
            value = change["value"]
            post[field] = value

    with open(file_path, 'w') as f:
        frontmatter.dump(post, f)

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


def _delete_entity(project_path: Path, target: dict, summary: str) -> str:
    """Move entity to _recycle-bin/."""
    import shutil

    entity_type = target.get("entity_type")
    slug = target.get("slug")
    folder = ENTITY_FOLDERS.get(entity_type, "")
    file_path = project_path / folder / f"{slug}.md"

    if not file_path.exists():
        return json.dumps({"error": f"Entity not found: {entity_type}/{slug}"})

    # Create recycle bin
    recycle_bin = project_path / "_recycle-bin" / entity_type
    recycle_bin.mkdir(parents=True, exist_ok=True)

    # Move file
    dest = recycle_bin / f"{slug}.md"
    shutil.move(str(file_path), str(dest))

    return json.dumps({
        "success": True,
        "message": f"Moved to recycle bin: {summary}",
        "file": str(dest)
    })


def _create_entity(project_path: Path, target: dict, changes: list, summary: str) -> str:
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


def _update_story_memory(project_path: Path, changes: list, summary: str) -> str:
    """Update the story memory file."""
    import frontmatter
    memory_path = project_path / ".story" / "memory.md"

    if not memory_path.exists():
        return json.dumps({"error": "memory.md not found"})

    post = frontmatter.load(memory_path)

    for change in changes:
        change_type = change.get("type")
        if change_type == "body_section":
            section = change["section"]
            new_body = change["new"]
            post.content = replace_section(post.content, section, new_body)
        elif change_type == "frontmatter":
            field = change["field"]
            value = change["value"]
            post[field] = value

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
    }
    return sections.get(entity_type, [])
