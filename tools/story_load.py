"""story_load tool — load a project's nested index into context."""
import json
from pathlib import Path


SCHEMA = {
    "description": "Structural map of a project: what exists and where — acts, sequences, scenes, "
                   "characters, plots, worlds. Call once per session before other story tools. "
                   "Not for reading an entity's content; use story_retrieve for that. Pass `view` "
                   "when you need one domain in depth — the default view stays small on purpose.",
    "type": "object",
    "properties": {
        "project": {
            "type": "string",
            "description": "Project slug or name"
        },
        "view": {
            "type": "string",
            "enum": ["arc", "story_value", "dramatic_elements", "relationship", "unfilled"],
            "description": "Optional focused view. Omit for the base structural map. "
                           "'arc' = one character's beats, pass character. "
                           "'story_value' = value arc across the structure. "
                           "'dramatic_elements' = per-scene dramatic roles and milestones. "
                           "'relationship' = the full relationship graph with perspectives. "
                           "'unfilled' = what is still incomplete, to answer 'what next?'."
        },
        "character": {
            "type": "string",
            "description": "For view='arc': the character id. Defaults to every character."
        },
        "act": {
            "type": "string",
            "description": "For view='dramatic_elements' and 'story_value': limit to one act id. "
                           "Defaults to all."
        },
        "add_plot": {
            "type": "boolean",
            "description": "For view='dramatic_elements': include which plots reference each "
                           "scene, and in which role. Off by default — it roughly doubles the view."
        }
    },
    "required": ["project"]
}


def handler(args: dict, **kwargs) -> str:
    """Load project nested index into context."""
    from core.config import resolve_root
    from .story_resolve import resolve_project

    root_path = resolve_root(kwargs)
    project = args["project"]

    # Resolve project
    try:
        project_path = resolve_project(project, root_path)
    except ValueError as e:
        return json.dumps({"error": str(e)})

    # DB is source of truth
    db_path = project_path / ".story" / "story.db"
    if not db_path.exists():
        return json.dumps({"error": "Database not found. Run story_import first."})

    from core.db import has_schema
    from core.db import get_project_summary
    import sqlite3

    view = args.get("view")
    conn = None
    try:
        conn = sqlite3.connect(str(db_path))
        if not has_schema(conn):
            return json.dumps({"error": "Database schema not found. Run story_import first."})

        # The base view is the default and stays deliberately slim: it is the
        # once-per-session map, and its cost per scene is ~16 characters. Any
        # depth beyond that is opt-in, so nothing here is conditional on `view`.
        if view is None:
            summary = get_project_summary(project_path)
            if summary:
                return json.dumps(summary)
        else:
            result = _extended_view(conn, project_path, view, args)
            if result is not None:
                return json.dumps(result)
    except Exception as e:
        return json.dumps({"error": str(e)})
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass

    return json.dumps({"error": "Failed to load project summary."})


def _extended_view(conn, project_path, view: str, args: dict):
    """One focused domain. Returns None for an unknown view name."""
    if view == "arc":
        return _view_arc(conn, args)
    if view == "story_value":
        return _view_story_value(conn, args)
    if view == "dramatic_elements":
        return _view_dramatic_elements(conn, args)
    if view == "relationship":
        return _view_relationship(conn)
    if view == "unfilled":
        return _view_unfilled(project_path, args)
    return {"error": f"Unknown view: {view}. Valid: arc, story_value, "
                     f"dramatic_elements, relationship, unfilled."}


def _view_arc(conn, args: dict) -> dict:
    """A character's beats, in order, with the value shift at each step."""
    from core.db import get_character_arcs

    character = args.get("character")
    if character:
        beats = get_character_arcs(project_path_of(conn), character)
        if not beats:
            return {"view": "arc", "character": character, "beats": [],
                    "note": f"No arc beats for '{character}'."}
        return {"view": "arc", "character": character, "beats": beats}

    rows = conn.execute(
        "SELECT id FROM entities WHERE type='character' AND is_deleted=0 ORDER BY id").fetchall()
    project_path = project_path_of(conn)
    arcs = []
    for (char_id,) in rows:
        beats = get_character_arcs(project_path, char_id)
        if beats:
            arcs.append({"character": char_id, "beat_count": len(beats),
                         "beats": beats})
    return {"view": "arc", "arcs": arcs,
            "hint": "Pass character=<id> for one arc in full."}


def _view_story_value(conn, args: dict) -> dict:
    """The value's journey: project, then act → sequence → scene.

    This view owns the value at every level — the base structural map carries
    only the project's own value, so nothing is lost by not repeating it there.
    Each container develops the value independently, so a scene's shift is not
    derivable from its sequence's and must be read here. Scenes matter most:
    they are where the value actually turns, and in a real project they carry
    values the containers do not (a subplot's Hope against the mainline Trust).
    """
    act_filter = args.get("act")

    scene_sql = ("SELECT id, parent_id, order_key, name, extra FROM entities "
                 "WHERE type='scene' AND is_deleted=0 ORDER BY order_key, id")
    scenes_by_seq: dict[str, list] = {}
    for scene_id, parent_id, _ok, name, extra_json in conn.execute(scene_sql).fetchall():
        extra = json.loads(extra_json or "{}")
        scenes_by_seq.setdefault(parent_id, []).append({
            "id": scene_id,
            "title": name,
            "value": extra.get("value", ""),
            "value_at_open": extra.get("value_at_open", ""),
            "value_at_close": extra.get("value_at_close", ""),
        })

    seq_sql = ("SELECT id, parent_id, name, order_key, extra FROM entities "
               "WHERE type='sequence' AND is_deleted=0 ORDER BY order_key, id")
    seq_by_act: dict[str, list] = {}
    for seq_id, parent_id, name, _ok, extra_json in conn.execute(seq_sql).fetchall():
        extra = json.loads(extra_json or "{}")
        seq_by_act.setdefault(parent_id, []).append({
            "id": seq_id,
            "title": name,
            "value": extra.get("value", ""),
            "value_at_open": extra.get("value_at_open", ""),
            "value_at_close": extra.get("value_at_close", ""),
            "scenes": scenes_by_seq.get(seq_id, []),
        })

    sql = ("SELECT id, name, order_key, extra FROM entities "
           "WHERE type='act' AND is_deleted=0 "
           "ORDER BY order_key, id")
    acts = []
    for act_id, title, _order_key, extra_json in conn.execute(sql).fetchall():
        if act_filter and act_id != act_filter:
            continue
        extra = json.loads(extra_json or "{}")
        acts.append({
            "id": act_id,
            "title": title,
            "value": extra.get("value", ""),
            "value_at_open": extra.get("value_at_open", ""),
            "value_at_close": extra.get("value_at_close", ""),
            "sequences": seq_by_act.get(act_id, []),
        })

    project = conn.execute(
        "SELECT extra FROM entities WHERE type='project' AND is_deleted=0 LIMIT 1").fetchone()
    pro = json.loads(project[0]) if project and project[0] else {}
    return {
        "view": "story_value",
        "act": act_filter or "all",
        "story_value": pro.get("value", ""),
        "value_at_open": pro.get("value_at_open", ""),
        "value_at_close": pro.get("value_at_close", ""),
        "acts": acts,
    }


def _view_dramatic_elements(conn, args: dict) -> dict:
    """Per-scene dramatic role and milestone, nested by act and sequence."""
    act_filter = args.get("act")
    add_plot = bool(args.get("add_plot"))

    # Which plots point at which scene, in which role. Built once, only if asked.
    # The role comes from the relation kind ("plot_setup" -> "setup") so this
    # needs no hardcoded list to drift out of sync with the schemas.
    plot_refs = {}
    if add_plot:
        for plot_id, in conn.execute(
                "SELECT id FROM entities WHERE type='plot' AND is_deleted=0 ORDER BY id"):
            for to_id, note, kind in conn.execute(
                    "SELECT to_id, note, kind FROM relations "
                    "WHERE from_id=:f AND kind LIKE 'plot_%'",
                    {"f": plot_id}):
                plot_refs.setdefault(to_id, []).append(
                    {"plot": plot_id,
                     "role": kind[len("plot_"):],
                     "description": note})

    acts_out = []
    for act_id, act_title, act_order in conn.execute(
            "SELECT id, name, order_key FROM entities WHERE type='act' AND is_deleted=0 "
            "ORDER BY order_key, id").fetchall():
        if act_filter and act_id != act_filter:
            continue
        seqs_out = []
        for seq_id, seq_title, seq_order in conn.execute(
                "SELECT id, name, order_key FROM entities "
                "WHERE type='sequence' AND parent_id=:p ORDER BY order_key, id",
                {"p": act_id}).fetchall():
            scenes_out = []
            for scene_id, scene_title, order_key, status, extra_json in conn.execute(
                    "SELECT id, name, order_key, status, extra FROM entities "
                    "WHERE type='scene' AND parent_id=:p AND is_deleted=0 "
                    "ORDER BY order_key, id",
                    {"p": seq_id}).fetchall():
                extra = json.loads(extra_json or "{}")
                scene = {
                    "id": scene_id,
                    "title": scene_title,
                    "status": status,
                    "dramatic_role": extra.get("dramatic_role", ""),
                }
                for marker in ("is_setup", "is_turning_point", "is_crisis",
                               "is_climax", "is_resolution"):
                    if extra.get(marker):
                        scene[marker] = True
                if extra.get("milestone"):
                    scene["milestone"] = extra["milestone"]
                if add_plot and scene_id in plot_refs:
                    scene["plots"] = plot_refs[scene_id]
                scenes_out.append(scene)
            seqs_out.append({"id": seq_id, "title": seq_title, "scenes": scenes_out})
        acts_out.append({"id": act_id, "title": act_title, "sequences": seqs_out})

    out = {"view": "dramatic_elements", "act": act_filter or "all", "acts": acts_out}
    if add_plot:
        out["add_plot"] = True
    return out


def _view_relationship(conn) -> dict:
    """Every relationship with its per-character perspectives."""
    out = []
    for rel_id, name, status, extra_json in conn.execute(
            "SELECT id, name, status, extra FROM entities "
            "WHERE type='relationship' AND is_deleted=0 "
            "ORDER BY id").fetchall():
        extra = json.loads(extra_json or "{}")
        perspectives = extra.get("perspectives", {})
        out.append({
            "id": rel_id,
            "name": name,
            "status": status,
            "characters": extra.get("characters", []),
            "scenes": extra.get("scenes", []),
            "perspectives": [
                {"character": char_id,
                 "type": p.get("type", ""),
                 "label": p.get("label", ""),
                 "feeling": p.get("feeling", ""),
                 "strength": p.get("strength"),
                 "secret": p.get("secret", False)}
                for char_id, p in sorted(perspectives.items())
            ],
        })
    return {"view": "relationship", "relationships": out}


# The unfilled view is a suggestion list, not an inventory: a project with 90
# scenes produces hundreds of entries, and an unbounded list is a wall the LLM
# cannot act on. Ranked structurally (by field, then entity type) and capped.
UNFILLED_LIMIT = 15


def _view_unfilled(project_path, args: dict) -> dict:
    from core.db import get_unfilled_map

    items = [{"field": field, "entities": ids, "count": len(ids)}
             for field, ids in get_unfilled_map(project_path).items()]
    items.sort(key=lambda i: (-i["count"], i["field"]))

    total = sum(i["count"] for i in items)
    shown = items[:UNFILLED_LIMIT]
    out = {
        "view": "unfilled",
        "total_gaps": total,
        "gap_types": len(items),
        "unfilled": shown,
    }
    if len(items) > UNFILLED_LIMIT:
        out["truncated"] = True
        out["shown_types"] = UNFILLED_LIMIT
        # Name the fields that did not fit. Without this an omitted field is
        # indistinguishable from a resolved one: `characters` fell off the end
        # at count 2, and dropping one entity pushed it further off, so fixing
        # a scene made the remaining gap look like it had been handled.
        out["other_fields"] = [i["field"] for i in items[UNFILLED_LIMIT:]]
        out["hint"] = (f"{len(items)} field types are incomplete; the "
                       f"{UNFILLED_LIMIT} most common are shown. "
                       f"other_fields lists the rest — still gaps.")
    if not items:
        out["message"] = "Nothing is at default — every optional field is filled."
    return out


def project_path_of(conn) -> Path:
    """Recover the project folder from the database file the connection is on."""
    # ponytail: sqlite exposes the file path; the plugin always uses .story/story.db.
    return Path(conn.execute("PRAGMA database_list").fetchone()[2]).parent.parent
