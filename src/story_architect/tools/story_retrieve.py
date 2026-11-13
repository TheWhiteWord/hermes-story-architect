"""story_retrieve tool — read one entity: its fields and section prose.

The counterpart to story_load ("what exists and where" vs "what does this say").

* A typo'd or mistyped id reports the project, not the import tool.
* Relation-backed fields (plot beats, scene characters) are reachable, so a
  plot's crisis scene can be read as empty.
* Any number of entities per call, held to a response budget: whole entities
  up to the budget, then `truncated` + `deferred_ids` + a hint. An entity is
  never cut in half — it is returned complete or not at all (see core.budget).
"""
import json
from pathlib import Path

from story_architect.core.constants import ENTITY_SCHEMAS
from story_architect.core.entity import (ENTITY_COLUMN_MAP, REVERSED_RELATION_KINDS as REVERSED_KINDS,
                          _RELATION_FIELDS)
from story_architect.core.value_focus import for_act, for_plot, for_project, for_sequence

# The computed `value_focus` read-back per unit type, with the project beside
# it: the project row is a singleton, so `_resolve` ignores its id and its
# scope function takes none.
VALUE_FOCUS_SCOPES = {
    "plot": for_plot,
    "sequence": for_sequence,
    "act": for_act,
    "project": for_project,
}

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
                           "project name from story_load. Responses are kept within a size "
                           "budget: entities come back whole, in the order given, and if "
                           "they would not all fit the response is marked `truncated` and "
                           "`deferred_ids` lists the ones to ask for next.",
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


def _scene_beats_id(conn, scene_id: str) -> str:
    """The id of a scene's `scene_beats` record, or "" when it has none.

    One record per scene (the write path refuses a second), so this is a lookup
    rather than a list. It returns the ID, not the record: the id cannot be
    derived from the scene id (it is caller-supplied — the skill teaches
    `{scene_id}-beats`), so the pointer is what tells the reader where to look.
    The record itself is read with `story_retrieve` on `scene_beats` and this id.
    """
    row = conn.execute(
        "SELECT id FROM entities "
        "WHERE type='scene_beats' AND parent_id=? AND is_deleted=0",
        (scene_id,)).fetchone()
    return row[0] if row else ""


def _scene_beats(conn, scene_id: str) -> dict | None:
    """A scene's `scene_beats` record, or None when it has none.

    Read whole: it is the same data the scene's `turning_point` computed field
    is derived from.
    """
    row = conn.execute(
        "SELECT id, parent_id, extra FROM entities "
        "WHERE type='scene_beats' AND parent_id=? AND is_deleted=0",
        (scene_id,)).fetchone()
    if not row:
        return None
    return {"id": row[0], "scene": row[1], **json.loads(row[2] or "{}")}


def _location_places(conn, location_id: str) -> list[str]:
    """The distinct non-empty `place` of a location's scenes, sorted.

    Derived at read time, so a scene written with a new place appears here on
    the next read without maintenance. Same derivation as the dashboard's
    location payload.
    """
    rows = conn.execute(
        "SELECT e.extra FROM relations r JOIN entities e ON e.id=r.to_id "
        "WHERE r.from_id=? AND r.kind='location_scene' "
        "AND e.type='scene' AND e.is_deleted=0",
        (location_id,)).fetchall()
    places = set()
    for (extra_json,) in rows:
        place = (json.loads(extra_json or "{}").get("place") or "").strip()
        if place:
            places.add(place)
    return sorted(places)


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
    # A computed field is derived, not stored: `value_focus` is the major and
    # minor values counted from the scenes' value_turns. Nothing to read from
    # `extra`, so it is built here — the first loop above already reserved the
    # key in schema position. The project row is a singleton, so `_resolve`
    # ignores its id and its scope function takes none.
    if "value_focus" in wanted and entity_type in VALUE_FOCUS_SCOPES:
        values["value_focus"] = (
            for_project(_project_path(conn)) if entity_type == "project"
            else VALUE_FOCUS_SCOPES[entity_type](_project_path(conn), data["id"]))
    # The same for a scene's `turning_point`: the record is another entity, so
    # there is nothing in this row's `extra` to read, and a scene with no record
    # returns "" — the distinction the design keeps ("or empty"). `scene_beats`
    # is NOT here: it is the record's id, so `_scene_beats_id` answers it and
    # the record itself is a second `story_retrieve` call.
    if entity_type == "scene" and "turning_point" in wanted:
        sb = _scene_beats(conn, data["id"])
        values["turning_point"] = sb.get("turning_point", "") if sb else ""
    if entity_type == "scene" and "scene_beats" in wanted:
        values["scene_beats"] = _scene_beats_id(conn, data["id"])
    # A location's `places` is the same computed list the dashboard derives:
    # the distinct non-empty `place` of its scenes.
    if entity_type == "location" and "places" in wanted:
        values["places"] = _location_places(conn, data["id"])

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
    from story_architect.core.entity import unfilled_fields
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


def _section_sizes(conn, entity_id: str) -> dict:
    """Heading -> characters, for an entity too big to return whole, so the
    agent can ask for its sections one at a time instead of guessing."""
    return {h: len(b or "") for h, b in conn.execute(
        "SELECT heading, body FROM sections WHERE entity_id=? ORDER BY rowid",
        (entity_id,))}


def handler(args: dict, **kwargs) -> str:
    """Return the requested fields and sections for one or more entities."""
    from story_architect.core.config import resolve_root
    from story_architect.core.db import get_db, has_schema
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
        # `["all"]` means EVERY field, computed ones included. The five role
        # fields are the whole content of a plot entity: without them a full
        # retrieve returns the plot's name, type and scope and nothing about its
        # story.
        #
        # They are still refused on the WRITE paths (drafts, create, edit) and
        # by the importer, which is where "computed" earns its keep: nobody
        # types them, they are derived. Excluding them from a READ is a
        # different claim, and the wrong one.
        wanted = set(schema) if want_fields == ["all"] else set(want_fields or [])

        from story_architect.core.budget import json_size, max_response_chars
        budget = max_response_chars()
        # What the envelope costs beside the entities: the type, the keys, and
        # room for `truncated`, `deferred_ids` and the hint.
        used = json_size({"entity_type": entity_type, "entities": []}) + 400
        entities, not_found, deferred = [], [], []
        oversize = None
        for position, entity_id in enumerate(ids):
            if deferred:
                deferred.append(entity_id)   # once one is deferred, the tail is
                continue
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
            # Whole entities only. The FIRST is always returned, however big:
            # refusing it would leave the agent with nothing to act on. Every
            # later one must fit alongside what is already there, plus the ids
            # that would be deferred if it does not.
            cost = json_size(entry) + 2
            if entities:
                tail = sum(len(i) + 4 for i in ids[position:])
                if used + cost + tail > budget:
                    deferred.append(entity_id)
                    continue
            elif used + cost > budget:
                oversize = {"id": data["id"],
                            "section_sizes": _section_sizes(conn, data["id"])}
            entities.append(entry)
            used += cost
    finally:
        conn.close()

    def assemble() -> dict:
        response = {"entity_type": entity_type, "entities": entities}
        hints = []
        if not_found:
            response["not_found"] = not_found
            hints.append("Call story_load to list valid ids for this project.")
        if deferred:
            response["truncated"] = True
            response["deferred_ids"] = deferred
            hints.append(
                f"{len(entities)} of {len(ids)} requested entities are returned, "
                f"each complete; the size budget stopped the rest. Call again with "
                f"deferred_ids (same sections/fields) to read them.")
        if oversize:
            response["over_budget"] = oversize
            hints.append(
                f"'{oversize['id']}' alone is larger than the size budget. To read it "
                f"in parts, request one section at a time — section_sizes lists them.")
        if hints:
            response["hint"] = " ".join(hints)
        return response

    # The estimate in the loop above is a shortcut; this is the guarantee, taken
    # on the real output. Hand back the last entity until it fits (never the
    # first), so the response is within budget unless one entity alone is not.
    response = assemble()
    while json_size(response) > budget and len(entities) > 1:
        deferred.insert(0, entities.pop()["id"])
        response = assemble()
    return json.dumps(response)
