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
from core.entity import (ENTITY_COLUMN_MAP, REVERSED_RELATION_KINDS as REVERSED_KINDS,
                          _RELATION_FIELDS)

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
            "description": "Field names to return. ['all'] for every field, including the "
                           "computed ones a plot's five role fields are. Omit for none. Call "
                           "story_describe to see what fields a type has.",
        },
    },
    "required": ["project", "entity_type", "id"],
}

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


def _project_path(conn) -> Path:
    """Recover the project folder from the database file the connection is on."""
    # ponytail: sqlite exposes the file path; the plugin always uses .story/story.db.
    return Path(conn.execute("PRAGMA database_list").fetchone()[2]).parent.parent


def _entity_fields(conn, data: dict, entity_type: str, wanted: set) -> dict:
    """Field values: columns, extra JSON, and relation-backed fields merged in."""
    extra = json.loads(data.get("extra") or "{}")
    schema = ENTITY_SCHEMAS.get(entity_type, {})
    column_map = ENTITY_COLUMN_MAP.get(entity_type, {})

    # Emit in SCHEMA order, not in `wanted` order. `wanted` is a set, so
    # iterating it gave whatever order the hash table happened to produce —
    # which put one_sentence between two role fields and shuffled the five
    # roles against each other. The schema is the one ordered declaration of a
    # type's fields, so it is what the output order follows: a reader gets the
    # fields as the type declares them, on every call, and reordering the
    # schema reorders every reader at once.
    values = {}
    for field, meta in schema.items():
        if field not in wanted:
            continue
        if field in column_map:
            values[field] = data.get(column_map[field], "")
        else:
            values[field] = extra.get(field, meta["default"])
    # A computed field is derived, not stored: `value_lines` is the plot's
    # schemas with their turns, which live on the scenes. Nothing to read from
    # `extra`, so it is built here — the first loop already reserved the key in
    # schema position.
    if entity_type == "plot" and "value_lines" in wanted:
        from core.db import compute_value_lines
        values["value_lines"] = compute_value_lines(
            _project_path(conn), data["id"])

    # Relation-backed fields: plot beats are rows linking to scenes, not
    # columns. Their position in the output is wherever the schema puts them,
    # so the first loop above reserves the key and this one fills it.
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
    # A scene's plot_roles are the same rows read from the other side, and the
    # only place they are WRITTEN. Not in `_RELATION_FIELDS` because it is one
    # field to five kinds — see entity.plot_role_relations.
    if entity_type == "scene" and "plot_roles" in wanted:
        values["plot_roles"] = [
            {"plot": plot, "role": kind[len("plot_"):], "description": note or ""}
            for plot, kind, note in conn.execute(
                'SELECT from_id, kind, note FROM relations '
                "WHERE to_id=? AND kind LIKE 'plot_%' ORDER BY \"order\"",
                (data["id"],),
            ).fetchall()
        ]
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
    # The same for a scene's plot_roles — filled means a row exists, not an
    # extra key, and plot_roles is never in extra.
    if entity_type == "scene" and conn.execute(
            "SELECT 1 FROM relations WHERE to_id=? AND kind LIKE 'plot_%' LIMIT 1",
            (data["id"],)).fetchone():
        extra["plot_roles"] = [1]
    # `data` IS the row (see _row_data), so the column-backed fields —
    # scene.location, plot.one_sentence, project.logline, location.world —
    # are visible here instead of being reported as gaps.
    return unfilled_fields(entity_type, extra, data)


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
    from core.config import resolve_root
    from core.db import get_db, has_schema
    from .story_resolve import resolve_project

    root_path = resolve_root(kwargs)

    try:
        project_path = resolve_project(args["project"], root_path)
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
        # `["all"]` means EVERY field, computed ones included. It used to filter
        # them out, on the reasoning that a computed field is derived and so is
        # not "the entity's own" — which reads right until you retrieve a plot
        # in full and find no scenes anywhere in it. The five role fields are
        # the whole content of a plot entity: without them a full retrieve
        # returns the plot's name, type and scope and nothing about its story.
        #
        # They are still refused on the WRITE paths (drafts, create, edit) and
        # by the importer, which is where "computed" earns its keep: nobody
        # types them, they are derived. Excluding them from a READ is a
        # different claim, and the wrong one.
        wanted = set(schema) if want_fields == ["all"] else set(want_fields or [])

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
            if want_sections:
                found = _sections(conn, data["id"], want_sections)
                entry["sections"] = found
                missing = [k for k, v in found.items() if v is None]
                if missing:
                    entry["sections_not_found"] = missing
                    entry["available_sections"] = list(_sections(conn, data["id"], ["all"]))
            # `unfilled_fields` LAST: it is the verdict on everything above, and
            # it reads as a summary of the fields and the prose rather than as
            # one more section among them.
            if wanted:
                entry["unfilled_fields"] = _unfilled(conn, data, entity_type)
            entities.append(entry)
    finally:
        conn.close()

    response = {"entity_type": entity_type, "entities": entities}
    if not_found:
        response["not_found"] = not_found
        response["hint"] = "Call story_load to list valid ids for this project."
    return json.dumps(response)
