"""Write path — create, edit, delete, reorder, project lifecycle.

Plain functions taking a resolved `project_path`, returning a dict and raising
on failure. The `json.dumps` / `{"error": ...}` string convention belongs to
the tool boundary, not here: `core/drafts.py` calls these in-process and reads
the dict directly.

**Errors raise; previews return.** A preview or a refusal whose payload is the
point — the delete consent gate, the structural-children refusal — returns a
dict, because the caller needs the thing it is being refused *with*. A fault
raises `ValueError`, with the actionable detail in the message: nothing that
used to travel in an `error` key is lost, because the key only ever named what
the sentence now says.
"""
import json
import sqlite3
from pathlib import Path

from .constants import ENTITY_SCHEMAS

_FIELDS_TO_SKIP = {"id", "type"}


# ─── project lifecycle ───

def create_project(slug: str, frontmatter_data: dict, root_path: Path) -> dict:
    """Create a new project with DB-only initialization."""
    _check_slug(slug)
    project_path = root_path / "projects" / slug

    schema = ENTITY_SCHEMAS.get("project", {})
    required = [f for f, meta in schema.items() if not meta.get("optional", True)]
    missing = [f for f in required if not frontmatter_data.get(f)]
    if missing:
        raise ValueError(
            f"Missing required fields for project: {', '.join(missing)}")

    # Merge frontmatter over schema defaults
    merged = {field: frontmatter_data.get(field, meta["default"])
              for field, meta in schema.items()}
    from .db import create_schema, empty_memory, get_db
    from .entity import columns_for_insert, standard_sections

    conn = get_db(project_path)
    try:
        create_schema(conn)
        conn.execute("BEGIN")
        if conn.execute("SELECT id FROM entities WHERE type='project' LIMIT 1").fetchone():
            conn.execute("ROLLBACK")
            raise ValueError(f"Project already exists: {slug}")

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
    except Exception:
        # Autocommit is off for this block (explicit BEGIN), so a real ROLLBACK
        # is the right cleanup — but never let it replace the cause.
        try:
            conn.execute("ROLLBACK")
        except Exception:
            pass
        raise
    finally:
        conn.close()

    return {
        "success": True,
        "message": f"Created project: {slug}",
        "file": str(project_path / ".story" / "story.db"),
    }


# ─── create ───

def create_entity(project_path: Path, entity_type: str, slug: str,
                  frontmatter_data: dict, sections: dict | None = None) -> dict:
    """Insert an entity, its standard sections, and its relation rows.

    `sections` fills the standard section bodies. The section set is closed: a
    heading that is not standard for this entity type is an error, the same as
    on the edit path.
    """
    _check_slug(slug)

    # The schema enum is advisory — a caller can still pass anything. Reject it
    # here, or an unknown type lands in the database and surfaces much later as
    # a mystery.
    if entity_type not in ENTITY_SCHEMAS:
        raise ValueError(
            f"Unknown entity_type: {entity_type}. "
            f"Valid types: {', '.join(sorted(ENTITY_SCHEMAS))}")

    # Checked here, not mid-insert, so a bad value cannot leave a half-made entity.
    if sections is None:
        sections = {}
    if not isinstance(sections, dict):
        raise ValueError("'sections' must be an object of {heading: text}")
    sections = {str(k): str(v) for k, v in sections.items()}

    from .db import create_schema, get_db, has_schema
    from .entity import (columns_for_insert, relations_for_insert,
                         standard_sections)

    # The section set is closed, and this is where it is enforced. edit_entity
    # already refused an unrecognised heading; create accepted one, so the same
    # key was valid on one path and an error on the other, and story_describe
    # documented only the stricter half. A heading outside the set is prose
    # nothing will ever read back as a section of this type.
    #
    # Same rule, same place, on all three write paths: story_import, create
    # and edit all refuse a name outside the set, so a section means one thing.
    standard = standard_sections(entity_type)
    unknown = [h for h in sections if h not in standard]
    if unknown:
        raise ValueError(
            f"Unrecognised {entity_type} section name(s): "
            f"{', '.join(sorted(unknown))}. The section set is closed — use one "
            f"of: {', '.join(standard)}. story_describe lists them per type."
        )

    # Same for field names, and for the same reason: edit_entity refused an
    # unrecognised key and create silently dropped it. The visible symptom was
    # `{"goals": {"short": ..., "long": ...}}` — a shape the schema's own
    # description used to advertise — reporting a character created with no
    # goals at all. A field is flat, always; there is no nested form. The
    # import path refuses the same key, so a note carrying one fails to import
    # rather than importing as something no reader will ever show.
    from .entity import ENTITY_COLUMN_MAP, _RELATION_FIELDS
    valid = (set(ENTITY_SCHEMAS[entity_type])
             | set(standard) | set(_RELATION_FIELDS.get(entity_type, {}))
             | set(ENTITY_COLUMN_MAP.get(entity_type, {})) | _FIELDS_TO_SKIP)
    unknown_fields = [k for k in frontmatter_data if k not in valid]
    if unknown_fields:
        raise ValueError(
            f"Unrecognised {entity_type} field(s): "
            f"{', '.join(sorted(unknown_fields))}. Fields are flat — pass each "
            f"by its own name (e.g. goals_short, goals_long), never nested "
            f"inside another key. story_describe lists the valid fields."
        )

    conn = get_db(project_path)
    try:
        if not has_schema(conn):
            create_schema(conn)

        # Merge frontmatter over schema defaults
        schema = ENTITY_SCHEMAS.get(entity_type, {})
        merged = {field: frontmatter_data.get(field, meta["default"])
                  for field, meta in schema.items() if not meta.get("computed")}

        columns = columns_for_insert(entity_type, slug, merged)
        entity_id = columns["id"]

        # Ids are global across types, so the name the caller gave may belong to
        # something else entirely — say which, or they will retry with a
        # different slug. (The PK would enforce it either way; this is friendlier.)
        existing = conn.execute(
            "SELECT type FROM entities WHERE id=?", (entity_id,)
        ).fetchone()
        if existing:
            if existing[0] == entity_type:
                raise ValueError(
                    f"Entity already exists: {entity_type}/{slug}. "
                    f"Edit it instead of creating it.")
            raise ValueError(
                f"Id '{slug}' is already used by a {existing[0]}. "
                f"Entity ids are unique across all types — "
                f"choose a different slug for this {entity_type}.")

        # Parent validation for arc type
        if entity_type == "arc_beat":
            from .entity import validate_arc_parents
            validate_arc_parents(
                project_path, merged.get("character", ""), merged.get("scene", ""))

        # Parent validation for scene (act_id consistency, location exists)
        if entity_type == "scene":
            from .entity import validate_scene_act_id, validate_scene_location
            sequence_id = merged.get("sequence_id", "")
            act_id = merged.get("act_id", "")
            if sequence_id:
                _validate_sequence_exists(conn, sequence_id)
                if act_id:
                    validate_scene_act_id(project_path, sequence_id, act_id)
            validate_scene_location(project_path, merged.get("location", ""))

        # Validate plot characters reference existing entities
        if entity_type == "plot":
            from .entity import validate_plot_characters
            validate_plot_characters(project_path, merged.get("characters", []))

        # Auto-order if not provided
        if entity_type in ("scene", "sequence") and merged.get("order", 0) == 0 and columns["parent_id"]:
            next_order = _get_next_order_db(conn, entity_type, columns["parent_id"])
            columns["order_key"] = next_order
            merged["order"] = next_order

        # Using autocommit mode (get_db sets isolation_level=None) — no explicit
        # transaction needed
        standard = standard_sections(entity_type)
        relations = relations_for_insert(entity_type, slug, merged)

        try:
            conn.execute(
                "INSERT INTO entities (id, type, name, one_sentence, order_key, status, parent_id, location_id, extra) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (columns["id"], columns["type"], columns["name"], columns["one_sentence"],
                 columns["order_key"], columns["status"], columns["parent_id"],
                 columns["location_id"], columns["extra"]),
            )
        except sqlite3.IntegrityError:
            # The duplicate check above is a SELECT and this INSERT is a separate
            # statement, so a second writer can land the same id in between. The
            # primary key is the real guarantee — this only translates its error
            # into the message the check would have produced, so a lost race
            # reads the same as a caught duplicate instead of leaking
            # "UNIQUE constraint failed: entities.id" to the user.
            raise ValueError(
                f"Entity already exists: {entity_type}/{slug}. "
                f"Edit it instead of creating it.") from None

        # Every standard section is created; the caller's prose fills the ones
        # given. Headings outside the set were rejected above, so these rows
        # and `sections` are the same closed set.
        section_rows = [(entity_id, heading, str(sections.get(heading, "")))
                        for heading in standard]
        if section_rows:
            conn.executemany(
                "INSERT INTO sections (entity_id, heading, body) VALUES (?, ?, ?)",
                section_rows,
            )

        for rel in relations:
            conn.execute(
                "INSERT INTO relations (from_id, to_id, kind, note, \"order\") VALUES (?, ?, ?, ?, ?)",
                (rel["from_id"], rel["to_id"], rel["kind"], rel["note"], rel["order"]),
            )
    except Exception:
        # Autocommit mode: there is no open transaction, so ROLLBACK itself
        # raises and would replace the real error with "cannot rollback - no
        # transaction is active". Never let cleanup hide the cause.
        try:
            conn.execute("ROLLBACK")
        except Exception:
            pass
        raise
    finally:
        conn.close()

    return {
        "success": True,
        "message": f"Created {entity_type}: {slug}",
        "entity_id": entity_id,
    }


# ─── edit ───

def edit_entity(project_path: Path, entity_type: str, slug: str,
                data: dict, summary: str) -> dict:
    """Edit entity fields, section prose and relations. Single transaction.

    Schema fields route to entity columns or `extra`, section names to the
    sections table, and a relation field rewrites that kind's relation rows.
    """
    from .db import get_db

    conn = get_db(project_path)
    try:
        entity_id = _find_entity_id_db(conn, entity_type, slug)
        if not entity_id:
            raise ValueError(f"Entity not found: {entity_type}/{slug}")

        from .entity import (ENTITY_COLUMN_MAP, coerce_number,
                             standard_sections as get_std_sections)
        standard_sections = set(get_std_sections(entity_type))
        # The one column map, owned by core.entity. An out-of-tree copy that
        # was missing `project` made editing a logline write it into `extra` and
        # report success while the column stayed unchanged.
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
                # `extra` is a JSON blob and does not enforce types, so a
                # `number` field arriving as '3' is stored as '3' and later
                # breaks any reader that compares it — the dashboard's max()
                # on act_count raised and took the whole view down. This path
                # UPDATEs rather than inserting, so it does not go through
                # columns_for_insert where the same coercion lives; both call
                # the one helper, because two copies of these four lines is
                # how create_project came to disagree with edit_entity.
                extra_updates[key] = coerce_number(value) if (
                    schema.get(key, {}).get("type") == "number"
                ) else value

        from .entity import (REVERSED_RELATION_KINDS, _RELATION_FIELDS,
                             relation_endpoints, relation_entry)
        rel_fields = _RELATION_FIELDS.get(entity_type, {})

        # ── Reject what cannot be applied, BEFORE writing anything ──
        # `data` is flat: {"<field>": value} or {"<Section name>": body}. A
        # nested call like {"frontmatter": {...}} would be dumped verbatim into
        # `extra` — the write "succeeded", nothing changed, and the edit was
        # silently lost. An unrecognised key is a hard error naming the valid
        # ones, so the caller can correct itself.
        valid = (set(schema) | standard_sections | set(rel_fields)
                 | set(column_map) | _FIELDS_TO_SKIP)
        unknown = [k for k in data if k not in valid]
        if unknown:
            examples = sorted(f for f in schema if not schema[f].get("computed"))[:8]
            raise ValueError(
                f"Unrecognised {entity_type} edit key(s): {', '.join(sorted(unknown))}. "
                f"`data` must be flat — pass field names and section names "
                f"directly, not nested under frontmatter/sections. "
                f"Valid field examples: {', '.join(examples)}. "
                f"Valid section examples: {', '.join(sorted(standard_sections)[:5])}."
            )

        applied_fields = []
        applied_sections = []
        applied_relations = []

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
            # Delete old relations of this kind for this entity. The key column
            # follows the stored direction — a reversed kind (a scene's cast) is
            # keyed on to_id, not from_id. See entity.relation_endpoints.
            own_col = "to_id" if kind in REVERSED_RELATION_KINDS else "from_id"
            conn.execute(
                f"DELETE FROM relations WHERE {own_col}=? AND kind=?", (entity_id, kind)
            )
            value = data[field]
            if is_list:
                if not isinstance(value, list):
                    continue
                for i, beat in enumerate(value):
                    target, note = relation_entry(beat)
                    if target:
                        from_id, to_id = relation_endpoints(entity_id, kind, target)
                        conn.execute(
                            "INSERT INTO relations (from_id, to_id, kind, note, \"order\") VALUES (?, ?, ?, ?, ?)",
                            (from_id, to_id, kind, note, i + 1)
                        )
            else:
                # Non-list: single string value
                if value:
                    from_id, to_id = relation_endpoints(entity_id, kind, str(value))
                    conn.execute(
                        "INSERT INTO relations (from_id, to_id, kind) VALUES (?, ?, ?)",
                        (from_id, to_id, kind)
                    )
            applied_relations.append(field)

        # A scene's location lives in the column AND in a reverse-index
        # relation. Re-derive the relation whenever the column is touched, and
        # delete the old one first — a scene that moved must not keep claiming
        # its previous location, which is what makes a location look used when
        # no scene is there any more. See entity.location_scene_relations.
        # Keyed by COLUMN name, because column_updates is.
        if entity_type == "scene" and "location_id" in column_updates:
            conn.execute(
                "DELETE FROM relations WHERE to_id=? AND kind='location_scene'",
                (entity_id,),
            )
            new_location = column_updates["location_id"]
            if new_location:
                conn.execute(
                    "INSERT INTO relations (from_id, to_id, kind, note, \"order\") "
                    "VALUES (?, ?, 'location_scene', '', 1)",
                    (str(new_location), entity_id),
                )
            applied_relations.append("location")

        # Upsert sections
        for heading, body in section_updates.items():
            conn.execute(
                "INSERT INTO sections (entity_id, heading, body) VALUES (?, ?, ?) "
                "ON CONFLICT(entity_id, heading) DO UPDATE SET body=excluded.body",
                (entity_id, heading, body)
            )
            applied_sections.append(heading)

        conn.execute("COMMIT")
    except Exception:
        try:
            conn.execute("ROLLBACK")
        except Exception:
            pass
        raise
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
    return response


def current_values(project_path: Path, entity_type: str, slug: str,
                   data: dict) -> dict:
    """What an edit would change, per field: where it lives, from, to.

    Reads only; touches nothing. Draft previews render from this.
    """
    from .db import get_db
    from .entity import ENTITY_COLUMN_MAP, standard_sections

    conn = get_db(project_path)
    try:
        entity_id = _find_entity_id_db(conn, entity_type, slug)
        if not entity_id:
            raise ValueError(f"Entity not found: {entity_type}/{slug}")
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
                    f"SELECT {col} FROM entities WHERE id=?", (entity_id,)
                ).fetchone()
                before = current[0] if current else None
                where = "column"
            else:
                before = extra.get(key)
                where = "extra"
            if before != value:
                changes.append({"field": key, "stored_in": where,
                                "from": before, "to": value})
        return {
            "dry_run": True, "entity_id": entity_id, "changes": changes,
            "message": f"Nothing was changed. {len(changes)} field(s) would change.",
        }
    finally:
        conn.close()


# ─── delete ───

def delete_entity(project_path: Path, entity_type: str, slug: str,
                  summary: str, confirm=None) -> dict:
    """Soft-delete an entity and its dependencies. Requires explicit consent.

    Rows are flagged `is_deleted=1` rather than removed, so restore is an exact
    inverse and no prose can be lost. **Returns** rather than raises in two
    cases, because the payload is the point of the refusal:

    * without `confirm` — a report of what would go, and nothing has changed;
    * with structural children — the blockers, which the caller must act on.
    """
    from datetime import datetime

    from .db import get_db

    conn = get_db(project_path)
    try:
        entity_id = _find_entity_id_db(conn, entity_type, slug)
        if not entity_id:
            raise ValueError(f"Entity not found: {entity_type}/{slug}")

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
            return {
                "error": "Delete refused without confirm. Nothing has changed yet.",
                "entity_id": entity_id,
                "entity_type": entity_type,
                "would_delete": [entity_id] + [c[0] for c in children],
                "cascade_children": [{"id": c[0], "type": c[1]} for c in children],
                "sections_deleted": sections,
                "relations_deleted": relations,
                # The report above IS the preview, so dry_run has nothing left
                # to add here: it would return this same payload. See the test
                # that asserts dry_run == the refusal.
                "action_required": (
                    "Review would_delete / cascade_children / sections_deleted above, "
                    "then re-run with confirm=true to flag them deleted. This is "
                    "reversible: restore undoes it."
                ),
            }

        # Checked after the consent gate and never gated by it: a structural child
        # means the delete is refused outright, confirm or not.
        if structural:
            return {
                "error": (
                    f"Cannot delete: {len(structural)} structural child(ren) reference this: "
                    f"{', '.join(c[0] for c in structural[:5])}. Delete or move them first."
                ),
                "entity_id": entity_id,
                "blocking_children": [{"id": c[0], "type": c[1]} for c in structural],
                "hint": "Reorder or re-parent them instead, or delete them first.",
            }

        # Soft delete: flag the row instead of removing it. Sections and
        # relations are left intact, so `restore` is an exact inverse — a hard
        # delete would have to reconstruct all of it, and could not do it
        # faithfully.
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
    finally:
        conn.close()

    return {
        "success": True,
        "message": f"Deleted: {summary}",
        "entity_id": entity_id,
        "cascade_deleted": [c[0] for c in children],
        "references_purged": depurged,
        "detached": detached,
        "reversible": True,
        "how_to_undo": f"restore with the same target. Deleted at {stamp}.",
    }


# ─── reorder ───

# Entity types reorder can renumber. Declared here, next to the function that
# enforces it, and imported by the draft validator so a type that stages is a
# type that commits — the two checks used to disagree, and the disagreement
# only surfaced as a raw ValueError after the user had approved the preview.
REORDERABLE_TYPES = ("scene", "sequence")


def reorder(project_path: Path, entity_type: str, ordered_ids: list,
            summary: str) -> dict:
    """Renumber scenes/sequences within their parent.

    The caller provides the complete new ordering. All items must exist and
    belong to the same parent; order is renumbered 1, 2, 3, ... from the list.
    Single DB transaction: BEGIN → UPDATE order_key for each item → COMMIT.
    """
    from .db import get_db

    if entity_type not in REORDERABLE_TYPES:
        raise ValueError(f"Reorder not supported for {entity_type}")
    if not ordered_ids:
        raise ValueError("ordered_ids required for reorder")

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
                raise ValueError(f"{entity_type} not found: {item_id}")
            if parent_id is None:
                parent_id = row[0]
            elif row[0] != parent_id:
                raise ValueError(f"{item_id} does not belong to {parent_id}")

        if not parent_id:
            raise ValueError(f"{entity_type} {ordered_ids[0]} has no parent")

        # Renumber: 1, 2, 3, ... in a single transaction
        conn.execute("BEGIN")
        for i, item_id in enumerate(ordered_ids, 1):
            conn.execute(
                "UPDATE entities SET order_key=? WHERE id=?",
                (i, item_id),
            )
        conn.execute("COMMIT")
    except Exception:
        try:
            conn.execute("ROLLBACK")
        except Exception:
            pass
        raise
    finally:
        conn.close()

    return {
        "success": True,
        "message": f"Reordered {len(ordered_ids)} {entity_type}(s) in {parent_id}: {summary}"
    }


# ─── shared helpers ───

def _check_slug(slug: str) -> None:
    """Reject anything that is not a plain id.

    Checked for a project slug too, which is not merely hygiene: a project slug
    IS a directory name (projects/<slug>), so an unvalidated one is a path
    traversal.
    """
    if not slug or not slug.replace("-", "").replace("_", "").isalnum():
        raise ValueError("Slug must be alphanumeric with hyphens/underscores only")


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


def _find_entity_id_db(conn, entity_type: str, slug: str) -> str | None:
    """Map (entity_type, id) to the DB entity_id.

    An exact match on the primary key, for every type. Arc beats used to be
    stored as '{character}-{beat}' and looked up by a bare beat number through
    `id LIKE '%-{slug}'` — which matched every character owning a beat of that
    name and took the first, so an edit could silently rewrite the wrong beat.
    A beat's id is now its own slug and its character link is `parent_id`, so
    there is nothing left to match loosely.
    """
    if entity_type == "project":
        row = conn.execute("SELECT id FROM entities WHERE type='project'").fetchone()
        return row[0] if row else None
    # is_deleted=0: a deleted entity must not be an editable/restoreable
    # target. `restore` looks the row up without this filter.
    row = conn.execute(
        "SELECT id FROM entities WHERE type=? AND id=? AND is_deleted=0",
        (entity_type, slug)
    ).fetchone()
    return row[0] if row else None


def _default_for(entity_type: str, field: str):
    """The schema default for a field — "" or [] when it has none.

    Resetting a reference to this rather than a bare "" keeps the two apart: a
    field whose default is a real value (project.screenplay_title is "Default")
    resets to that, while an unfilled field resets to empty (B12 — these
    defaults were once visible placeholders like "Location not set").
    """
    return ENTITY_SCHEMAS.get(entity_type, {}).get(field, {}).get("default", "")


def _purge_references(conn, deleted_ids: set) -> tuple:
    """Strip references to deleted entities out of the JSON `extra` of survivors.

    The cascade in `delete_entity` only handles relation *rows* and `parent_id`.
    But several reference sites live in `extra` instead, and deleting a
    character left relationship entities still naming them — with their
    perspectives intact:

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
        # default rather than a bare "", so a field whose default is a real
        # value resets to that value and not to nothing.
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
