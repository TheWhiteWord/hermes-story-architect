"""story_retrieve tool — read one entity: its fields and section prose.

The counterpart to story_load ("what exists and where" vs "what does this say").

Three defects this replaces:
  * a typo'd or mistyped id reported "Database not found. Run story_import first."
    — pointing the agent at the one tool that destroys work;
  * relation-backed fields (plot beats, scene characters) were unreachable, so an
    agent could not see that a plot's crisis scene was empty;
  * one entity per call, forcing a round trip per id.
"""
import json
from pathlib import Path

from core.constants import ENTITY_SCHEMAS
from core.entity import ENTITY_COLUMN_MAP, _RELATION_FIELDS

SCHEMA = {
    "description": "Read one or more entities: their field values and section prose, plus which "
                   "fields are still unfilled. Use after story_load or story_search has identified "
                   "the entity. Request only the sections or fields you need — this is how content "
                   "is read.",
    "type": "object",
    "properties": {
        "project": {"type": "string", "description": "Project slug or name"},
        "entity_type": {"type": "string", "enum": list(ENTITY_SCHEMAS),
                        "description": "Type of entity to read"},
        "id": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Entity id(s), exactly as returned by story_load. Several at once is "
                           "cheaper than one call per id. For entity_type='project' use the "
                           "project name from story_load.",
        },
        "sections": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Section names to return. ['all'] for every section. Omit for none.",
        },
        "fields": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Field names to return. ['all'] for every non-computed field. Omit for "
                           "none. Call story_describe to see what fields a type has.",
        },
    },
    "required": ["project", "entity_type", "id"],
}

# Relations stored from the opposite side: a scene's characters are the
# character_scene rows pointing AT it, not rows it owns.
REVERSED_KINDS = {"character_scene"}

def _columns(conn) -> list:
    # Never cached across calls: tests and the dashboard use different databases
    # in one process, and a cached column list silently misaligns row values.
    return [c[1] for c in conn.execute("PRAGMA table_info(entities)").fetchall()]


def _resolve(conn, entity_type: str, entity_id: str):
    """Find the entity. Returns (row, error) — exactly one is set."""
    if entity_type == "project":
        sql, params = "SELECT * FROM entities WHERE type='project' LIMIT 1", ()
    elif entity_type == "arc_beat":
        sql, params = "SELECT * FROM entities WHERE type='arc_beat' AND id=? AND is_deleted=0", (entity_id,)
        row = conn.execute(sql, params).fetchone()
        if row:
            return row, None
        # A beat is keyed `{character}-{beat}`; the caller may only know the beat part.
        row = conn.execute(
            "SELECT * FROM entities WHERE type='arc_beat' AND id LIKE ? AND is_deleted=0", (f"%-{entity_id}",)
        ).fetchone()
        if row:
            return row, None
    else:
        sql, params = ("SELECT * FROM entities WHERE type=? AND id=? AND is_deleted=0",
                      (entity_type, entity_id))
    row = conn.execute(sql, params).fetchone()
    if row:
        return row, None
    return None, (
        f"No {entity_type} with id '{entity_id}'. Ids are exactly as returned by story_load."
    )


def _row_data(conn, row) -> dict:
    return dict(zip(_columns(conn), row))


def _entity_fields(conn, data: dict, entity_type: str, wanted: set) -> dict:
    """Field values: columns, extra JSON, and relation-backed fields merged in."""
    extra = json.loads(data.get("extra") or "{}")
    schema = ENTITY_SCHEMAS.get(entity_type, {})
    column_map = ENTITY_COLUMN_MAP.get(entity_type, {})

    values = {}
    for field in wanted:
        if field not in schema:
            continue
        if field in column_map:
            values[field] = data.get(column_map[field], "")
        else:
            values[field] = extra.get(field, schema[field]["default"])

    # Relation-backed fields: plot beats are rows linking to scenes, not columns.
    for field, (kind, is_list) in _RELATION_FIELDS.get(entity_type, {}).items():
        if field not in wanted:
            continue
        # character_scene is stored from the character side, so a scene's characters
        # are the rows pointing AT it. Every other kind points away from the owner.
        if kind in REVERSED_KINDS:
            rows = conn.execute(
                'SELECT from_id, note FROM relations WHERE to_id=? AND kind=? ORDER BY "order"',
                (data["id"], kind),
            ).fetchall()
        else:
            rows = conn.execute(
                'SELECT to_id, note FROM relations WHERE from_id=? AND kind=? ORDER BY "order"',
                (data["id"], kind),
            ).fetchall()
        if not is_list:
            values[field] = rows[0][0] if rows else ""
        elif kind.startswith("plot_"):
            values[field] = [{"scene_id": to_id, "description": note} for to_id, note in rows]
        else:
            values[field] = [to_id for to_id, _ in rows]
    return values


def _unfilled(conn, data: dict, entity_type: str) -> list:
    from core.entity import unfilled_fields
    extra = json.loads(data.get("extra") or "{}")
    # A plot beat is filled only when its relation row exists, not when extra has a key.
    for field, (kind, _) in _RELATION_FIELDS.get(entity_type, {}).items():
        sql = ("SELECT 1 FROM relations WHERE to_id=? AND kind=? LIMIT 1"
               if kind in REVERSED_KINDS
               else "SELECT 1 FROM relations WHERE from_id=? AND kind=? LIMIT 1")
        if conn.execute(sql, (data["id"], kind)).fetchone():
            extra[field] = [1]
    return unfilled_fields(entity_type, extra)


def _sections(conn, entity_id: str, wanted) -> dict:
    """Requested sections; a name with no section comes back as null."""
    rows = conn.execute(
        "SELECT heading, body FROM sections WHERE entity_id=? ORDER BY rowid", (entity_id,)
    ).fetchall()
    if wanted == ["all"]:
        return {h: b for h, b in rows}
    bodies = dict(rows)
    return {name: bodies.get(name) for name in wanted}


def handler(args: dict, **kwargs) -> str:
    """Return the requested fields and sections for one or more entities."""
    from core.config import load_plugin_config
    from core.db import get_db, has_schema
    from .story_resolve import resolve_project

    _vault = kwargs.get("vault_path")
    if _vault:
        vault_path = Path(_vault)
    else:
        vault_path = Path(load_plugin_config().get("vault_path", "~/story-vault")).expanduser()

    try:
        project_path = resolve_project(args["project"], vault_path)
    except ValueError as e:
        return json.dumps({"error": str(e)})

    if not (project_path / ".story" / "story.db").exists():
        return json.dumps({"error": "Database not found. Run story_import first."})

    entity_type = args["entity_type"]
    ids = args["id"]
    if isinstance(ids, str):          # tolerate a bare string
        ids = [ids]
    want_sections = args.get("sections")
    want_fields = args.get("fields")

    if not want_sections and not want_fields:
        return json.dumps({
            "error": "Nothing requested. Pass sections (['all'] or names) and/or fields "
                     "(['all'] or names).",
        })

    conn = get_db(project_path)
    try:
        if not has_schema(conn):
            return json.dumps({"error": "Database schema incomplete. Run story_import first."})

        schema = ENTITY_SCHEMAS.get(entity_type, {})
        wanted = set(f for f, m in schema.items() if not m.get("computed")) \
            if want_fields == ["all"] else set(want_fields or [])

        entities, not_found = [], []
        for entity_id in ids:
            row, error = _resolve(conn, entity_type, entity_id)
            if error:
                not_found.append({"id": entity_id, "error": error})
                continue
            data = _row_data(conn, row)
            entry = {"id": data["id"]}
            if wanted:
                entry["fields"] = _entity_fields(conn, data, entity_type, wanted)
                entry["unfilled_fields"] = _unfilled(conn, data, entity_type)
            if want_sections:
                found = _sections(conn, data["id"], want_sections)
                entry["sections"] = found
                missing = [k for k, v in found.items() if v is None]
                if missing:
                    entry["sections_not_found"] = missing
                    entry["available_sections"] = list(_sections(conn, data["id"], ["all"]))
            entities.append(entry)
    finally:
        conn.close()

    response = {"entity_type": entity_type, "entities": entities}
    if not_found:
        response["not_found"] = not_found
        response["hint"] = "Call story_load to list valid ids for this project."
    return json.dumps(response)
