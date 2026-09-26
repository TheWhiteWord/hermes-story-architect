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
        "description": "Create a new entity, or a new project. Validates parent references and "
                       "auto-orders new scenes and sequences. Fails if the entity already exists "
                       "— use story_edit to change something that is already there. Call "
                       "story_describe first to see which fields this entity type expects.",
        "type": "object",
        "properties": {
            "entity_type": {
                "type": "string",
                "enum": list(ENTITY_SCHEMAS),
                "description": "Type of entity to create",
            },
            "slug": {
                "type": "string",
                "description": "Unique id for the entity, as it will appear in story_load "
                               "output. Lowercase, hyphen-separated. For entity_type='project' "
                               "this is the new project's folder name.",
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
            "sections": {
                "type": "object",
                "description": "Prose to write into the entity's body sections, keyed by heading "
                               "({heading: text}). Every standard section is created regardless; "
                               "this fills the ones you supply. A heading that is not standard for "
                               "this entity type is added as written. Use story_describe to see the "
                               "standard sections.",
                "additionalProperties": {"type": "string"},
            },
        },
        "required": ["entity_type", "slug", "project", "frontmatter"],
    }


SCHEMA = _build_schema()


def handler(args: dict, **kwargs) -> str:
    """Create new entity in DB."""
    from core.config import resolve_root
    from .story_resolve import resolve_project

    root_path = resolve_root(kwargs)

    entity_type = args["entity_type"]
    slug = args["slug"]
    frontmatter_data = args["frontmatter"]

    # Validate slug. Checked before the project branch too: a project slug IS a
    # directory name (projects/<slug>), so an unvalidated one is a path
    # traversal, not just a malformed id.
    if not slug or not slug.replace("-", "").replace("_", "").isalnum():
        return json.dumps({"error": "Slug must be alphanumeric with hyphens/underscores only"})

    # Project creation is special — initializes the full project structure
    if entity_type == "project":
        return _create_project(slug, frontmatter_data, root_path)

    # The schema enum is advisory — an LLM can still pass anything. Reject it here,
    # or an unknown type lands in the database and surfaces much later as a mystery.
    if entity_type not in ENTITY_SCHEMAS:
        return json.dumps({
            "error": f"Unknown entity_type: {entity_type}",
            "valid_types": sorted(ENTITY_SCHEMAS),
        })

    # Validated here, not mid-insert, so a bad value cannot leave a half-made entity.
    supplied_sections = args.get("sections") or {}
    if not isinstance(supplied_sections, dict):
        return json.dumps({"error": "'sections' must be an object of {heading: text}"})
    supplied_sections = {str(k): str(v) for k, v in supplied_sections.items()}

    # Resolve project
    try:
        project_path = resolve_project(args.get("project", ""), root_path)
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
        from core.entity import columns_for_insert, relations_for_insert, standard_sections
        columns = columns_for_insert(entity_type, slug, merged)
        entity_id = columns["id"]

        # Check uniqueness (PK will enforce, but give friendly error). Ids are
        # global across types, so the name the caller gave may belong to something
        # else entirely — say which, or they will retry with a different slug.
        existing = conn.execute(
            "SELECT type FROM entities WHERE id=?", (entity_id,)
        ).fetchone()
        if existing:
            if existing[0] == entity_type:
                return json.dumps({
                    "error": f"Entity already exists: {entity_type}/{slug}",
                    "hint": "Use story_edit to change something that is already there.",
                })
            return json.dumps({
                "error": f"Id '{slug}' is already used by a {existing[0]}.",
                "hint": f"Entity ids are unique across all types. "
                        f"Choose a different slug for this {entity_type}.",
            })

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
        sections = standard_sections(entity_type)
        relations = relations_for_insert(entity_type, slug, merged)

        conn.execute(
            "INSERT INTO entities (id, type, name, one_sentence, order_key, status, parent_id, location_id, extra) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (columns["id"], columns["type"], columns["name"], columns["one_sentence"],
             columns["order_key"], columns["status"], columns["parent_id"],
             columns["location_id"], columns["extra"]),
        )

        # Every standard section is created; the caller's prose fills the ones given.
        # A heading that is not standard is added as written — a scene may need a
        # heading this schema has never heard of.
        supplied = supplied_sections
        section_rows = [(entity_id, heading, str(supplied.get(heading, "")))
                        for heading in sections]
        section_rows += [(entity_id, heading, str(body))
                         for heading, body in supplied.items() if heading not in sections]
        if section_rows:
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
        # Autocommit mode: there is no open transaction, so ROLLBACK itself raises
        # and would replace the real error with "cannot rollback - no transaction
        # is active". Never let cleanup hide the cause.
        try:
            conn.execute("ROLLBACK")
        except Exception:
            pass
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


def _create_project(slug, frontmatter_data, root_path):
    """Create a new project with DB-only initialization."""
    project_path = root_path / "projects" / slug

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
    from core.db import empty_memory, get_db, create_schema
    from core.entity import columns_for_insert, standard_sections

    conn = get_db(project_path)
    try:
        create_schema(conn)
        conn.execute("BEGIN")
        if conn.execute("SELECT id FROM entities WHERE type='project' LIMIT 1").fetchone():
            conn.execute("ROLLBACK")
            return json.dumps({"error": f"Project already exists: {slug}"})

        memory = empty_memory()
        sections = standard_sections("project")
        columns = columns_for_insert("project", slug, {**merged, "memory": memory})
        conn.execute(
            "INSERT INTO entities (id, type, name, one_sentence, order_key, status, parent_id, location_id, extra) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (columns["id"], columns["type"], columns["name"], columns["one_sentence"],
             columns["order_key"], columns["status"], columns["parent_id"],
             columns["location_id"], columns["extra"]),
        )
        if sections:
            conn.executemany(
                "INSERT INTO sections (entity_id, heading, body) VALUES (?, ?, ?)",
                [(slug, heading, "") for heading in sections],
            )
        conn.execute("COMMIT")
    except Exception as e:
        try:
            conn.execute("ROLLBACK")
        except Exception:
            pass
        return json.dumps({"error": str(e)})
    finally:
        conn.close()

    return json.dumps({
        "success": True,
        "message": f"Created project: {slug}",
        "file": str(project_path / ".story" / "story.db"),
    })



