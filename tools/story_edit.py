"""story_edit tool — propose and apply edits (action protocol)."""
import json
from pathlib import Path
from core.constants import ENTITY_SCHEMAS

SCHEMA = {
    "description": "Change an existing entity: fields, section prose and relations. Also deletes "
                   "and restores entities, and reorders scenes/sequences. Deleting is "
                   "REVERSIBLE — it flags the entity rather than erasing it, so "
                   "action=\"restore\" brings it back exactly, prose included. To create "
                   "something new, use story_create instead.",
    "type": "object",
    "properties": {
        "action": {
            "type": "string",
            "enum": ["edit_note", "delete_entity", "restore", "purge", "reorder"],
            "description": "Action type: edit_note (edit entity fields/prose), "
                           "delete_entity (soft delete — reversible via restore, blocked if it "
                           "has structural children), restore (bring a deleted entity back), "
                           "reorder (batch renumber order fields for scenes/sequences)"
        },
        "target": {
            "type": "object",
            "description": "Target entity",
            "properties": {
                "entity_type": {"type": "string", "enum": list(ENTITY_SCHEMAS),
                                "description": "Type of entity to edit. 'project' targets the "
                                               "project entity itself (slug is ignored)."},
                "slug": {"type": "string", "description": "Entity id, as returned by story_load. "
                                                          "Ignore for entity_type='project'."}
            }
        },
        "data": {
            "type": "object",
            "description": "Key-value edits, FLAT: {\"<field_name>\": value} and/or "
                           "{\"<Section Name>\": prose body}. Do NOT nest under "
                           "'frontmatter' or 'sections' — a nested call is rejected "
                           "with an error rather than silently ignored. The response "
                           "lists what was actually applied. Use dry_run first to "
                           "check a shape you are unsure about."
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
        },
        "dry_run": {
            "type": "boolean",
            "description": "Report what would change and change nothing. Use before any "
                           "edit you want to confirm. Not needed for delete_entity: "
                           "a delete without confirm is already refused with the full "
                           "preview of what it would affect."
        },
        "confirm": {
            "type": "boolean",
            "description": "Required to delete."
        },
        "purge_confirm": {
            "type": "string",
            "description": "Required for action=\"purge\". Must contain the literal text "
                           "DELETE <project slug>, e.g. \"DELETE my-film\". This is the user's "
                           "call to make — do not supply it unless the user has asked for the "
                           "deleted entities to be removed permanently."
        },
        "older_than_days": {
            "type": "integer",
            "description": "For action=\"purge\": only purge entities deleted longer ago than "
                           "this many days. Default 30. Anything newer stays restorable."
        }
    },
    "required": ["action", "target", "summary"]
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

    dry_run = bool(args.get("dry_run"))

    if action == "edit_note":
        if dry_run:
            return _preview_edit(project_path, target, data)
        result = _edit_note_db(project_path, target, data, summary)
    elif action == "delete_entity":
        result = _delete_entity(project_path, target, summary, args.get("confirm"))
    elif action == "purge":
        result = _purge_deleted(project_path, target, args)
    elif action == "restore":
        result = _restore_entity(project_path, target, summary)
    elif action == "reorder":
        order_context = args.get("order_context", {})
        if dry_run:
            return _preview_reorder(project_path, target, order_context)
        result = _reorder(project_path, target, order_context, summary)
    else:
        return json.dumps({"error": f"Unknown action: {action}"})

    return result


def _preview_edit(project_path: Path, target: dict, data: dict) -> str:
    """What an edit_note would change. Reads only; touches nothing."""
    from core.db import get_db
    from core.entity import ENTITY_COLUMN_MAP, standard_sections

    entity_type = target.get("entity_type") or ""
    slug = target.get("slug") or ""
    conn = get_db(project_path)
    try:
        entity_id = _find_entity_id_db(conn, entity_type, slug)
        if not entity_id:
            return json.dumps({"error": f"Entity not found: {entity_type}/{slug}"})
        row = conn.execute("SELECT extra FROM entities WHERE id=?", (entity_id,)).fetchone()
        extra = json.loads(row[0]) if row and row[0] else {}
        standard = set(standard_sections(entity_type))
        column_map = ENTITY_COLUMN_MAP.get(entity_type, {})

        changes = []
        for key, value in data.items():
            if key in _FIELDS_TO_SKIP:
                continue
            if key in standard:
                current = conn.execute(
                    "SELECT body FROM sections WHERE entity_id=? AND heading=?",
                    (entity_id, key)).fetchone()
                before = current[0] if current else None
                where = "section"
            elif key in column_map:
                col = column_map[key]
                current = conn.execute(
                    f"SELECT {col} FROM entities WHERE id=?", (entity_id,)).fetchone()
                before = current[0] if current else None
                where = "column"
            else:
                before = extra.get(key)
                where = "extra"
            if before != value:
                changes.append({"field": key, "stored_in": where,
                                "from": before, "to": value})
        return json.dumps({
            "dry_run": True, "entity_id": entity_id, "changes": changes,
            "message": f"Nothing was changed. {len(changes)} field(s) would change.",
        })
    finally:
        conn.close()


def _default_for(entity_type: str, field: str):
    """The schema default for a field — "" or [] when it has none.

    Resetting a reference to this rather than a bare "" means a field whose
    default is a visible placeholder ("Location not set") keeps the placeholder,
    so the UI still shows that the field needs filling.
    """
    return ENTITY_SCHEMAS.get(entity_type, {}).get(field, {}).get("default", "")


def _purge_references(conn, deleted_ids: set) -> tuple:
    """Strip references to deleted entities out of the JSON `extra` of survivors.

    The cascade above only handles relation *rows* and `parent_id`. But several
    reference sites live in `extra` instead, and deleting a character left
    relationship entities still naming them — with their perspectives intact:

        kael-mira  {"characters": ["kael", ...], "perspectives": {"kael": {...}}}

    A relationship is a first-class entity, not a relation row, so nothing else
    was touching it. This walks every surviving entity once and removes the dead
    ids from the known reference fields.
    """
    if not deleted_ids:
        return [], []

    # Only live entities: the delete flags its targets before calling this, so
    # without the filter it would re-scrub the entity it is deleting.
    rows = conn.execute(
        "SELECT id, type, extra FROM entities WHERE is_deleted=0").fetchall()
    touched = []
    # Fields emptied that the schema marks required. unfilled_fields skips those
    # by design, so this is the only place the agent learns about them.
    detached = []
    for entity_id, entity_type, extra_json in rows:
        if entity_id in deleted_ids:
            continue
        extra = json.loads(extra_json) if extra_json else {}
        changed = False

        # Reference *columns*, not extra: a scene's location_id points at a
        # location, and nothing else would ever clear it. parent_id is checked
        # too — a child whose parent was deleted as a non-structural cascade
        # member should not be left pointing at nothing.
        #
        # Columns are emptied to "" rather than NULL: unfilled_fields treats a
        # missing key and an empty value the same way, and "" round-trips to
        # Markdown as a visible blank instead of a silent null.
        for column in ("parent_id", "location_id"):
            row = conn.execute(
                f"SELECT {column} FROM entities WHERE id=?", (entity_id,)).fetchone()
            if row and row[0] in deleted_ids:
                conn.execute(f"UPDATE entities SET {column}='' WHERE id=?", (entity_id,))
                changed = True
                # location is optional, so unfilled_fields picks it up on its own.
                if column == "location_id":
                    detached.append({"entity_id": entity_id, "entity_type": entity_type,
                                     "field": "location", "was_pointing_at": row[0]})

        # List-valued references: characters, scenes. The key is kept and the
        # dead ids dropped, so the field reads as empty rather than absent.
        for field in ("characters", "scenes"):
            value = extra.get(field)
            if isinstance(value, list) and deleted_ids & set(map(str, value)):
                extra[field] = [v for v in value if str(v) not in deleted_ids]
                changed = True

        # Single-valued reference: an arc beat's scene. Reset to the schema
        # default rather than a bare "", so a field that has a visible placeholder
        # ("Location not set") keeps it — the UI shows the gap instead of a blank.
        if str(extra.get("scene", "")) in deleted_ids:
            was = extra["scene"]
            extra["scene"] = _default_for(entity_type, "scene")
            changed = True
            detached.append({"entity_id": entity_id, "entity_type": entity_type,
                             "field": "scene", "was_pointing_at": was})

        # Per-character sub-objects: a relationship's perspectives. This one
        # really is a removal — the surviving half of the relationship is what
        # the entity is for, so dropping the dead key keeps the other one.
        perspectives = extra.get("perspectives")
        if isinstance(perspectives, dict):
            gone = [k for k in perspectives if k in deleted_ids]
            for key in gone:
                del perspectives[key]
                changed = True

        if changed:
            conn.execute("UPDATE entities SET extra=? WHERE id=?",
                         (json.dumps(extra), entity_id))
            touched.append(entity_id)
    return touched, detached


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
            "SELECT id FROM entities WHERE type='arc_beat' AND id=? AND is_deleted=0",
            (slug,)
        ).fetchone()
        if row:
            return row[0]
        row = conn.execute(
            "SELECT id FROM entities WHERE type='arc_beat' AND id LIKE ? AND is_deleted=0",
            (f"%-{slug}",)
        ).fetchone()
        return row[0] if row else None
    else:
        # is_deleted=0: a deleted entity must not be an editable/restoreable
        # target. `_restore_entity` looks the row up without this filter.
        row = conn.execute(
            "SELECT id FROM entities WHERE type=? AND id=? AND is_deleted=0",
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

        from core.entity import standard_sections as get_std_sections
        standard_sections = set(get_std_sections(entity_type))
        # The one column map, owned by core.entity. This file used to keep its own
        # copy that was missing `project`, so editing a logline wrote it into
        # `extra` and reported success while the column stayed unchanged.
        from core.entity import ENTITY_COLUMN_MAP
        column_map = ENTITY_COLUMN_MAP.get(entity_type, {})
        schema = ENTITY_SCHEMAS.get(entity_type, {})

        column_updates = {}
        extra_updates = {}
        section_updates = {}
        computed_skipped = []

        for key, value in data.items():
            if key in _FIELDS_TO_SKIP:
                continue
            if schema.get(key, {}).get("computed"):
                computed_skipped.append(key)  # Read-only, derived elsewhere
                continue
            if key in standard_sections:
                section_updates[key] = value
            elif key in column_map:
                column_updates[column_map[key]] = value
            else:
                extra_updates[key] = value

        from core.entity import _RELATION_FIELDS
        rel_fields = _RELATION_FIELDS.get(entity_type, {})

        # ── Reject what cannot be applied, BEFORE writing anything ──
        # `data` is flat: {"<field>": value} or {"<Section name>": body}. A
        # nested call like {"frontmatter": {...}} used to be dumped verbatim into
        # `extra` — the write "succeeded", nothing changed, and the edit was
        # silently lost. An unrecognised key is now a hard error naming the
        # valid ones, so the caller can correct itself.
        valid = (set(schema) | standard_sections | set(rel_fields)
                 | set(column_map) | _FIELDS_TO_SKIP)
        unknown = [k for k in data if k not in valid]
        if unknown:
            return json.dumps({
                "error": (
                    f"Unrecognised {entity_type} edit key(s): "
                    f"{', '.join(sorted(unknown))}. "
                    "`data` must be flat — pass field names and section names "
                    "directly, not nested under frontmatter/sections."
                ),
                "unrecognised_keys": sorted(unknown),
                "valid_field_examples": sorted(
                    f for f in schema if not schema[f].get("computed"))[:8],
                "valid_section_examples": sorted(standard_sections)[:5],
                "hint": "Use story_describe(entity_type=...) for the full list.",
            })

        applied_fields = []
        applied_sections = []
        applied_relations = []
        skipped_computed = []

        conn.execute("BEGIN")

        # Update entity columns
        if column_updates:
            set_clause = ", ".join(f"{col}=?" for col in column_updates)
            values = list(column_updates.values()) + [entity_id]
            conn.execute(f"UPDATE entities SET {set_clause} WHERE id=?", values)
            applied_fields.extend(column_updates)

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
            applied_fields.extend(extra_updates)

        # Create/update relation rows for all _RELATION_FIELDS of this entity type
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
            applied_relations.append(field)

        # Upsert sections
        for heading, body in section_updates.items():
            conn.execute(
                "INSERT INTO sections (entity_id, heading, body) VALUES (?, ?, ?) "
                "ON CONFLICT(entity_id, heading) DO UPDATE SET body=excluded.body",
                (entity_id, heading, body)
            )
            applied_sections.append(heading)

        conn.execute("COMMIT")
    except Exception as e:
        try:
            conn.execute("ROLLBACK")
        except Exception:
            pass
        return json.dumps({"error": str(e)})
    finally:
        conn.close()

    response = {
        "success": True,
        "message": f"Applied: {summary}",
        "entity_id": entity_id,
        # Name what actually landed, so "success" cannot mean "silently did
        # nothing" the way an unrecognised key used to.
        "applied": {
            "fields": sorted(set(applied_fields)),
            "sections": sorted(set(applied_sections)),
            "relations": sorted(set(applied_relations)),
        },
    }
    if computed_skipped:
        response["skipped_read_only"] = sorted(set(computed_skipped))
    if not (applied_fields or applied_sections or applied_relations):
        response["warning"] = (
            "Nothing was written" +
            (": every key was a read-only computed field. "
             if computed_skipped else ". ")
            + "Use story_describe to see which fields are editable."
        )
    return json.dumps(response)


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


def _preview_reorder(project_path: Path, target: dict, order_context: dict) -> str:
    """What a reorder would change. Reads only; touches nothing."""
    from core.db import get_db

    entity_type = target.get("entity_type")
    if entity_type not in ("scene", "sequence"):
        return json.dumps({"error": f"Reorder not supported for {entity_type}"})
    ordered_ids = order_context.get("ordered_ids", [])
    if not ordered_ids:
        return json.dumps({"error": "order_context.ordered_ids required"})

    conn = get_db(project_path)
    try:
        changes = []
        for new_order, item_id in enumerate(ordered_ids, 1):
            row = conn.execute(
                "SELECT order_key FROM entities WHERE type=? AND id=?",
                (entity_type, item_id)).fetchone()
            if not row:
                return json.dumps({"error": f"{entity_type} not found: {item_id}"})
            if row[0] != new_order:
                changes.append({"id": item_id, "from": row[0], "to": new_order})
        return json.dumps({
            "dry_run": True, "changes": changes,
            "message": f"Nothing was changed. {len(changes)} of {len(ordered_ids)} would move.",
        })
    finally:
        conn.close()


def _purge_deleted(project_path: Path, target: dict, args: dict) -> str:
    """Permanently remove soft-deleted rows. Two deliberate guards.

    1. `purge_confirm` must contain the literal "DELETE <project slug>". The
       agent cannot guess that string, so it can only ever purge if the user
       handed it over — which puts a human in the loop by construction.
    2. An age floor: only rows deleted more than `older_than_days` ago (default
       30) are eligible. Anything deleted in this session stays restorable, so
       tidying up can never destroy a fresh mistake.

    A backup is taken first, so even this is recoverable by hand.
    """
    from datetime import datetime, timedelta

    from core.db import backup_database, get_db

    required = f"DELETE {project_path.name}"
    given = args.get("purge_confirm", "")
    if required not in given:
        return json.dumps({
            "error": "Purge refused. It is irreversible and must be the user's call.",
            "action_required": 'Re-run with purge_confirm="%s" if you are sure.' % required,
            "hint": 'To undo a delete instead, use action="restore" — that is exact.',
        })

    days = args.get("older_than_days", 30)
    cutoff = (datetime.now() - timedelta(days=days)).isoformat(timespec="seconds")

    conn = get_db(project_path)
    try:
        rows = conn.execute(
            "SELECT id, type, deleted_at FROM entities "
            "WHERE is_deleted=1 AND deleted_at IS NOT NULL AND deleted_at <= ? "
            "ORDER BY type, id", (cutoff,)).fetchall()
        if not rows:
            younger = conn.execute(
                "SELECT count(*) FROM entities WHERE is_deleted=1").fetchone()[0]
            return json.dumps({
                "success": True,
                "purged": [],
                "message": (
                    f"Nothing is old enough to purge ({younger} deleted entities are "
                    f"younger than {days} days). They stay restorable."),
            })

        ids = [r[0] for r in rows]
        marks = ",".join("?" * len(ids))
        backup = backup_database(project_path)
        conn.execute(f"DELETE FROM sections WHERE entity_id IN ({marks})", ids)
        conn.execute(f"DELETE FROM relations WHERE from_id IN ({marks}) "
                     f"OR to_id IN ({marks})", ids + ids)
        conn.execute(f"DELETE FROM entities WHERE id IN ({marks})", ids)
    finally:
        conn.close()

    return json.dumps({
        "success": True,
        "message": f"Purged {len(ids)} entities permanently.",
        "purged": [{"id": r[0], "type": r[1], "deleted_at": r[2]} for r in rows],
        "backup": backup,
        "note": ("Markdown files for these entities are removed by the next "
                 "story_export."),
    })


def _restore_entity(project_path: Path, target: dict, summary: str) -> str:
    """Undelete an entity by clearing is_deleted. Exact inverse of the delete.

    Sections and relations were never removed, so there is nothing to rebuild —
    which is the whole reason the delete is a flag and not a DELETE.
    """
    from core.db import get_db

    entity_type = target.get("entity_type") or ""
    slug = target.get("slug") or ""
    conn = get_db(project_path)
    try:
        # Deliberately NOT filtered on is_deleted — that is the point.
        row = conn.execute(
            "SELECT id, is_deleted, deleted_at FROM entities WHERE id=? OR id=?",
            (slug, slug),
        ).fetchone()
        if not row:
            return json.dumps({"error": f"Entity not found: {entity_type}/{slug}"})
        entity_id, is_deleted, deleted_at = row
        if not is_deleted:
            return json.dumps({
                "error": f"{entity_id} is not deleted — nothing to restore.",
                "entity_id": entity_id,
            })
        conn.execute(
            "UPDATE entities SET is_deleted=0, deleted_at=NULL WHERE id=?", (entity_id,))
        # Beats cascaded with the character come back too — a restore that left
        # them deleted would silently halve the arc.
        restored_children = [r[0] for r in conn.execute(
            "SELECT id FROM entities WHERE type='arc_beat' AND parent_id=? "
            "AND is_deleted=1 ORDER BY id", (entity_id,)).fetchall()]
        if restored_children:
            conn.execute(
                "UPDATE entities SET is_deleted=0, deleted_at=NULL "
                "WHERE type='arc_beat' AND parent_id=? AND is_deleted=1", (entity_id,))
    finally:
        conn.close()

    return json.dumps({
        "success": True,
        "message": f"Restored: {summary}",
        "entity_id": entity_id,
        "was_deleted_at": deleted_at,
        "restored_cascade_children": restored_children,
    })


def _delete_entity(project_path: Path, target: dict, summary: str,
                   confirm=None) -> str:
    """Soft-delete entity and its dependencies. Requires explicit consent.

    Rows are flagged `is_deleted=1` rather than removed, so `action="restore"`
    is an exact inverse and no prose can be lost. Refused without `confirm: true`
    so the agent can show the user what is about to go.
    """
    from datetime import datetime

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
        structural = [c for c in children if c[1] in ("scene", "sequence")]

        if not confirm:
            # What goes, and why it is being held back.
            sections = conn.execute(
                "SELECT COUNT(*) FROM sections WHERE entity_id=?", (entity_id,)
            ).fetchone()[0]
            relations = conn.execute(
                "SELECT COUNT(*) FROM relations WHERE from_id=? OR to_id=?",
                (entity_id, entity_id)).fetchone()[0]
            report = {
                "entity_id": entity_id,
                "entity_type": entity_type,
                "would_delete": [entity_id] + [c[0] for c in children],
                "cascade_children": [{"id": c[0], "type": c[1]} for c in children],
                "sections_deleted": sections,
                "relations_deleted": relations,
            }
            if not confirm:
                # The report above IS the preview, so dry_run has nothing left
                # to add here: it would return this same payload. See the
                # test that asserts dry_run == the refusal.
                report["error"] = "Delete refused without confirm. Nothing has changed yet."
                report["action_required"] = (
                    "Review would_delete / cascade_children / sections_deleted above, "
                    "then re-run with confirm=true to flag them deleted. This is "
                    "reversible: action=\"restore\" undoes it."
                )
                return json.dumps(report)

        # Checked after the consent gate and never gated by it: a structural child
        # means the delete is refused outright, confirm or not.
        if structural:
            return json.dumps({
                "error": (
                    f"Cannot delete: {len(structural)} structural child(ren) reference this: "
                    f"{', '.join(c[0] for c in structural[:5])}. Delete or move them first."
                ),
                "entity_id": entity_id,
                "blocking_children": [{"id": c[0], "type": c[1]} for c in structural],
                "hint": "Reorder or re-parent them instead, or delete them first.",
            })

        # Soft delete (task_18 spec): flag the row instead of removing it.
        # Sections and relations are left intact, so `restore` is an exact
        # inverse — a hard delete would have to reconstruct all of it, and
        # could not do it faithfully.
        stamp = datetime.now().isoformat(timespec="seconds")
        for child_id, child_type in children:
            conn.execute(
                "UPDATE entities SET is_deleted=1, deleted_at=? WHERE id=?",
                (stamp, child_id))
        conn.execute(
            "UPDATE entities SET is_deleted=1, deleted_at=? WHERE id=?",
            (stamp, entity_id))

        deleted_ids = {entity_id} | {c[0] for c in children}

        # Relations *owned by* a deleted entity survive, so restore can put
        # them back. Relations *pointing at* one must go: a live character
        # pointing at a dead scene is the dangling state this whole function
        # exists to prevent.
        for dead_id in deleted_ids:
            conn.execute(
                "DELETE FROM relations WHERE from_id NOT IN "
                "(SELECT id FROM entities WHERE is_deleted=1) AND to_id=?",
                (dead_id,))

        # References held in other entities' extra must still be scrubbed, or a
        # deleted id would be handed out as a valid target by story_load.
        depurged, detached = _purge_references(conn, deleted_ids)
    except ValueError as e:
        return json.dumps({"error": str(e)})
    except Exception as e:
        return json.dumps({"error": str(e)})
    finally:
        conn.close()

    return json.dumps({
        "success": True,
        "message": f"Deleted: {summary}",
        "entity_id": entity_id,
        "cascade_deleted": [c[0] for c in children],
        "references_purged": depurged,
        "detached": detached,
        "reversible": True,
        "how_to_undo": (
            f'story_edit action="restore" with the same target. Deleted at {stamp}.'
        ),
    })



