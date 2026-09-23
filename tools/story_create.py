"""story_create tool — create new entities."""
import json
from pathlib import Path
from core.constants import ENTITY_SCHEMAS


def _build_schema() -> dict:
    """Build JSON schema with field-level descriptions from ENTITY_SCHEMAS."""
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
                if "sub_fields" in meta:
                    all_fields[field]["sub_fields"] = meta["sub_fields"]
            else:
                all_fields[field]["_entity_types"].append(entity_type)

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
                "enum": ["project", "character", "location", "world", "plot", "scene", "sequence", "act", "arc_beat"],
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
    """Create new entity in DB."""
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

    # Check uniqueness — auto-create schema if missing
    from core.db import get_db, has_schema, create_schema
    conn = get_db(project_path)
    try:
        if not has_schema(conn):
            create_schema(conn)

        # Merge frontmatter over schema defaults
        schema = ENTITY_SCHEMAS.get(entity_type, {})
        merged = {field: frontmatter_data.get(field, meta["default"]) for field, meta in schema.items() if not meta.get("computed")}

        # Map to columns
        from core.entity import columns_for_insert, relations_for_insert
        columns = columns_for_insert(entity_type, slug, merged)
        entity_id = columns["id"]

        # Check uniqueness (PK will enforce, but give friendly error)
        existing = conn.execute(
            "SELECT id FROM entities WHERE id=?", (entity_id,)
        ).fetchone()
        if existing:
            return json.dumps({"error": f"Entity already exists: {entity_type}/{slug}"})

        # Parent validation for arc type
        if entity_type == "arc_beat":
            from core.entity import validate_arc_parents
            try:
                validate_arc_parents(
                    project_path,
                    merged.get("character", ""),
                    merged.get("scene", ""),
                )
            except ValueError as e:
                return json.dumps({"error": str(e)})

        # Parent validation for scene (act_id consistency)
        if entity_type == "scene":
            from core.entity import validate_scene_act_id
            sequence_id = merged.get("sequence_id", "")
            act_id = merged.get("act_id", "")
            if sequence_id:
                try:
                    _validate_sequence_exists(conn, sequence_id)
                    if act_id:
                        validate_scene_act_id(project_path, sequence_id, act_id)
                except ValueError as e:
                    return json.dumps({"error": str(e)})

        # Validate plot characters reference existing entities
        if entity_type == "plot":
            from core.entity import validate_plot_characters
            try:
                validate_plot_characters(project_path, merged.get("characters", []))
            except ValueError as e:
                return json.dumps({"error": str(e)})

        # Auto-order if not provided
        if entity_type in ("scene", "sequence") and merged.get("order", 0) == 0 and columns["parent_id"]:
            next_order = _get_next_order_db(conn, entity_type, columns["parent_id"])
            columns["order_key"] = next_order
            merged["order"] = next_order

        # Insert entity + sections + relations
        # Using autocommit mode (get_db sets isolation_level=None) — no explicit transaction needed
        sections = _get_standard_sections(entity_type)
        relations = relations_for_insert(entity_type, slug, merged)

        conn.execute(
            "INSERT INTO entities (id, type, name, one_sentence, order_key, status, parent_id, location_id, extra) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (columns["id"], columns["type"], columns["name"], columns["one_sentence"],
             columns["order_key"], columns["status"], columns["parent_id"],
             columns["location_id"], columns["extra"]),
        )

        # Insert standard sections
        if sections:
            section_rows = [(entity_id, heading, "") for heading in sections]
            conn.executemany(
                "INSERT INTO sections (entity_id, heading, body) VALUES (?, ?, ?)",
                section_rows,
            )

        # Insert relations
        for rel in relations:
            conn.execute(
                "INSERT INTO relations (from_id, to_id, kind, note, \"order\") VALUES (?, ?, ?, ?, ?)",
                (rel["from_id"], rel["to_id"], rel["kind"], rel["note"], rel["order"]),
            )
    except Exception as e:
        conn.execute("ROLLBACK")
        return json.dumps({"error": str(e)})
    finally:
        conn.close()

    return json.dumps({
        "success": True,
        "message": f"Created {entity_type}: {slug}",
        "entity_id": entity_id,
    })


def _validate_sequence_exists(conn, sequence_id: str) -> None:
    """Raise ValueError if sequence doesn't exist in DB."""
    row = conn.execute(
        "SELECT id FROM entities WHERE id=? AND type='sequence'", (sequence_id,)
    ).fetchone()
    if not row:
        raise ValueError(f"Sequence not found: {sequence_id}")


def _get_next_order_db(conn, entity_type: str, parent_id: str) -> int:
    """Compute next order value for a new child within its parent."""
    row = conn.execute(
        "SELECT COALESCE(MAX(order_key), 0) + 1 FROM entities WHERE type=? AND parent_id=?",
        (entity_type, parent_id),
    ).fetchone()
    return int(row[0]) if row else 1


def _create_project(slug, frontmatter_data, vault_path):
    """Create a new project with full scaffolding in DB."""
    import frontmatter

    project_path = vault_path / "projects" / slug

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

    # Create project.md + memory.md (project.md still needed for story_resolve)
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

    # Create entity folders (for import/export round-trip)
    for folder in ["characters", "locations", "worlds", "plots", "scenes", "sequences", "acts", "arcs"]:
        (project_path / folder).mkdir(exist_ok=True)

    # Create story.db with schema
    from core.db import get_db, create_schema
    conn = get_db(project_path)
    try:
        create_schema(conn)

        # Insert project entity
        from core.entity import columns_for_insert
        columns = columns_for_insert("project", slug, merged)
        conn.execute(
            "INSERT INTO entities (id, type, name, one_sentence, order_key, status, parent_id, location_id, extra) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (columns["id"], columns["type"], columns["name"], columns["one_sentence"],
             columns["order_key"], columns["status"], columns["parent_id"],
             columns["location_id"], columns["extra"]),
        )

        # Insert standard sections
        if sections:
            section_rows = [(slug, heading, "") for heading in sections]
            conn.executemany(
                "INSERT INTO sections (entity_id, heading, body) VALUES (?, ?, ?)",
                section_rows,
            )

        conn.commit()
    finally:
        conn.close()

    return json.dumps({
        "success": True,
        "message": f"Created project: {slug}",
        "file": str(project_path / "project.md"),
    })


def _get_standard_sections(entity_type: str) -> list[str]:
    """Get standard sections for an entity type."""
    sections = {
        "project": ["Synopsis", "Themes", "Structure", "Notes"],
        "character": ["Personality", "Background", "Voice", "Greatest Fear", "Secrets", "Arc", "Relationships", "Goals"],
        "location": ["Description", "Atmosphere", "Image System", "History", "Dramatic Function"],
        "world": ["Description", "History", "Livelihood", "Power", "Rituals", "Values", "Conflict"],
        "plot": ["Summary", "Obstacles", "Stakes"],
        "scene": ["Description", "Dramatic Function", "Notes", "Content"],
        "sequence": ["Summary", "Scene Order", "Notes"],
        "act": ["Summary", "Thematic Function", "Notes"],
        "arc_beat": ["Action", "Gap", "Choice", "Shift", "Development Log"],
        "relationship": ["Description", "History", "Dynamics", "Scenes", "Notes"],
    }
    return sections.get(entity_type, [])
