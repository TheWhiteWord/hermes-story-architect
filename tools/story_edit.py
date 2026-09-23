"""story_edit tool — propose and apply edits (action protocol)."""
import json
from pathlib import Path
from core.constants import ENTITY_SCHEMAS
from core.section_parser import replace_section

SCHEMA = {
    "type": "object",
    "properties": {
        "action": {
            "type": "string",
            "enum": ["edit_note", "delete_entity", "update_story_memory", "reorder"],
            "description": "Action type: edit_note (edit entity frontmatter/body sections), delete_entity (hard delete, blocked if has children), update_story_memory, reorder (batch renumber order fields for scenes/sequences)"
        },
        "target": {
            "type": "object",
            "description": "Target entity (omit for update_story_memory)",
            "properties": {
                "entity_type": {"type": "string", "enum": ["character", "location", "world", "plot", "scene", "sequence", "act", "arc_beat"]},
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

# FM field name → DB column name, per entity type
_ENTITY_COLUMN_MAP = {
    "character": {"name": "name", "one_sentence": "one_sentence"},
    "location": {"name": "name", "one_sentence": "one_sentence", "world": "parent_id"},
    "world": {"name": "name", "one_sentence": "one_sentence"},
    "plot": {"name": "name", "one_sentence": "one_sentence", "status": "status"},
    "scene": {"title": "name", "order": "order_key", "status": "status", "sequence_id": "parent_id", "location": "location_id"},
    "sequence": {"title": "name", "order": "order_key", "status": "status", "act_id": "parent_id"},
    "act": {"title": "name", "order": "order_key", "status": "status"},
    "arc_beat": {"label": "name", "order": "order_key", "character": "parent_id"},
    "relationship": {"name": "name", "status": "status"},
}

_FIELDS_TO_SKIP = {"id", "type"}


def handler(args: dict, **kwargs) -> str:
    """Apply edit to project note."""
    from core.config import load_plugin_config
    from .story_resolve import resolve_project

    _vault = kwargs.get("vault_path")
    if _vault:
        vault_path = Path(_vault)
    else:
        config = load_plugin_config()
        vault_path = Path(config.get("vault_path", "~/story-vault")).expanduser()

    action = args["action"]
    target = args["target"]
    data = args.get("data", {})
    summary = args["summary"]

    # Resolve project
    try:
        project_path = resolve_project(target.get("project", ""), vault_path)
    except ValueError as e:
        return json.dumps({"error": str(e)})

    if action == "edit_note":
        result = _edit_note_db(project_path, target, data, summary)
    elif action == "delete_entity":
        result = _delete_entity(project_path, target, summary)
    elif action == "update_story_memory":
        result = _update_story_memory(project_path, data, summary)
    elif action == "reorder":
        order_context = args.get("order_context", {})
        result = _reorder(project_path, target, order_context, summary)
    else:
        return json.dumps({"error": f"Unknown action: {action}"})

    return result


def _find_entity_id_db(conn, entity_type: str, slug: str) -> str | None:
    """Map (entity_type, slug) to DB entity_id.

    For arcs, entity_id = '{char_slug}-{beat_id}' and slug is the beat_id.
    Tries exact match first (slug may already be full entity_id), then pattern.
    """
    if entity_type == "project":
        row = conn.execute("SELECT id FROM entities WHERE type='project'").fetchone()
        return row[0] if row else None
    elif entity_type == "arc_beat":
        row = conn.execute(
            "SELECT id FROM entities WHERE type='arc_beat' AND id=?", (slug,)
        ).fetchone()
        if row:
            return row[0]
        row = conn.execute(
            "SELECT id FROM entities WHERE type='arc_beat' AND id LIKE ?",
            (f"%-{slug}",)
        ).fetchone()
        return row[0] if row else None
    else:
        row = conn.execute(
            "SELECT id FROM entities WHERE type=? AND id=?",
            (entity_type, slug)
        ).fetchone()
        return row[0] if row else None


def _edit_note_db(project_path: Path, target: dict, data: dict, summary: str) -> str:
    """Edit entity in DB: schema fields → entity columns/extra, sections → sections table.

    Single transaction: BEGIN → updates → COMMIT, rollback on any error.
    """
    from core.db import get_db

    entity_type = target.get("entity_type") or ""
    slug = target.get("slug") or ""

    conn = get_db(project_path)
    try:
        entity_id = _find_entity_id_db(conn, entity_type, slug)
        if not entity_id:
            return json.dumps({"error": f"Entity not found: {entity_type}/{slug}"})

        standard_sections = set(_get_standard_sections(entity_type))
        column_map = _ENTITY_COLUMN_MAP.get(entity_type, {})
        schema = ENTITY_SCHEMAS.get(entity_type, {})

        column_updates = {}
        extra_updates = {}
        section_updates = {}

        for key, value in data.items():
            if key in _FIELDS_TO_SKIP:
                continue
            if schema.get(key, {}).get("computed"):
                continue  # Read-only field — derived from other entities
            if key in standard_sections:
                section_updates[key] = value
            elif key in column_map:
                column_updates[column_map[key]] = value
            else:
                extra_updates[key] = value

        conn.execute("BEGIN")

        # Update entity columns
        if column_updates:
            set_clause = ", ".join(f"{col}=?" for col in column_updates)
            values = list(column_updates.values()) + [entity_id]
            conn.execute(f"UPDATE entities SET {set_clause} WHERE id=?", values)

        # Update extra JSON
        if extra_updates:
            row = conn.execute(
                "SELECT extra FROM entities WHERE id=?", (entity_id,)
            ).fetchone()
            extra = json.loads(row[0]) if row and row[0] else {}
            extra.update(extra_updates)
            conn.execute(
                "UPDATE entities SET extra=? WHERE id=?",
                (json.dumps(extra), entity_id)
            )

        # Create/update relation rows for all _RELATION_FIELDS of this entity type
        from core.entity import _RELATION_FIELDS
        rel_fields = _RELATION_FIELDS.get(entity_type, {})
        for field, (kind, is_list) in rel_fields.items():
            if field not in data:
                continue
            # Delete old relations of this kind for this entity
            conn.execute(
                "DELETE FROM relations WHERE from_id=? AND kind=?", (entity_id, kind)
            )
            value = data[field]
            if is_list:
                if not isinstance(value, list):
                    continue
                for i, beat in enumerate(value):
                    if isinstance(beat, dict):
                        to_id = beat.get("scene_id", str(beat))
                        note = beat.get("description", "")
                    else:
                        to_id = str(beat)
                        note = ""
                    if to_id:
                        conn.execute(
                            "INSERT INTO relations (from_id, to_id, kind, note, \"order\") VALUES (?, ?, ?, ?, ?)",
                            (entity_id, to_id, kind, note, i + 1)
                        )
            else:
                # Non-list: single string value
                if value:
                    conn.execute(
                        "INSERT INTO relations (from_id, to_id, kind) VALUES (?, ?, ?)",
                        (entity_id, str(value), kind)
                    )

        # Upsert sections
        for heading, body in section_updates.items():
            conn.execute(
                "INSERT INTO sections (entity_id, heading, body) VALUES (?, ?, ?) "
                "ON CONFLICT(entity_id, heading) DO UPDATE SET body=excluded.body",
                (entity_id, heading, body)
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
        "message": f"Applied: {summary}",
        "entity_id": entity_id
    })


def _reorder(project_path: Path, target: dict, order_context: dict, summary: str) -> str:
    """Reorder scenes/sequences within their parent by renumbering order_key.

    The LLM provides the complete new ordering. All items must exist and
    belong to the same parent; order is renumbered 1, 2, 3, ... from the list.
    Single DB transaction: BEGIN → UPDATE order_key for each item → COMMIT.
    """
    from core.db import get_db

    entity_type = target.get("entity_type")
    if entity_type not in ("scene", "sequence"):
        return json.dumps({"error": f"Reorder not supported for {entity_type}"})

    ordered_ids = order_context.get("ordered_ids", [])
    if not ordered_ids:
        return json.dumps({"error": "order_context.ordered_ids required"})

    conn = get_db(project_path)
    try:
        # Verify all entities exist and belong to the same parent
        parent_id = None
        for item_id in ordered_ids:
            row = conn.execute(
                "SELECT parent_id FROM entities WHERE type=? AND id=?",
                (entity_type, item_id),
            ).fetchone()
            if not row:
                return json.dumps({"error": f"{entity_type} not found: {item_id}"})
            if parent_id is None:
                parent_id = row[0]
            elif row[0] != parent_id:
                return json.dumps({"error": f"{item_id} does not belong to {parent_id}"})

        if not parent_id:
            return json.dumps({"error": f"{entity_type} {ordered_ids[0]} has no parent"})

        # Renumber: 1, 2, 3, ... in a single transaction
        conn.execute("BEGIN")
        for i, item_id in enumerate(ordered_ids, 1):
            conn.execute(
                "UPDATE entities SET order_key=? WHERE id=?",
                (i, item_id),
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
        "message": f"Reordered {len(ordered_ids)} {entity_type}(s) in {parent_id}: {summary}"
    })


def _delete_entity(project_path: Path, target: dict, summary: str) -> str:
    """Hard-delete entity and its dependencies."""
    from core.db import get_db

    entity_type = target.get("entity_type") or ""
    slug = target.get("slug") or ""

    conn = get_db(project_path)
    try:
        entity_id = _find_entity_id_db(conn, entity_type, slug)
        if not entity_id:
            return json.dumps({"error": f"Entity not found: {entity_type}/{slug}"})

        # Cascade block: structural types (containment hierarchy)
        # Derived from DB: any entity whose parent_id points to this one is a child
        children = conn.execute(
            "SELECT id, type FROM entities WHERE parent_id=?", (entity_id,)
        ).fetchall()
        if children:
            # If any child is a structural type (act/sequence/scene), block deletion
            structural = [c for c in children if c[1] in ("scene", "sequence")]
            if structural:
                ids = [c[0] for c in structural[:5]]
                raise ValueError(
                    f"Cannot delete: {len(structural)} structural child(ren) reference this: {', '.join(ids)}"
                )
            # Non-structural children (arcs) are cascade-deleted with parent
            for child_id, child_type in children:
                conn.execute("DELETE FROM sections WHERE entity_id=?", (child_id,))
                conn.execute("DELETE FROM relations WHERE from_id=? OR to_id=?", (child_id, child_id))
                conn.execute("DELETE FROM entities WHERE id=?", (child_id,))

        # Hard delete: entity + its sections + its relations
        conn.execute("DELETE FROM sections WHERE entity_id=?", (entity_id,))
        conn.execute("DELETE FROM relations WHERE from_id=? OR to_id=?", (entity_id, entity_id))
        conn.execute("DELETE FROM entities WHERE id=?", (entity_id,))
    except ValueError as e:
        return json.dumps({"error": str(e)})
    except Exception as e:
        return json.dumps({"error": str(e)})
    finally:
        conn.close()

    return json.dumps({
        "success": True,
        "message": f"Deleted: {summary}",
        "entity_id": entity_id
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
