"""story_load tool — load a project's nested index into context."""
import json
from pathlib import Path

from core.db import milestone_label


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
            "enum": ["arc", "dramatic_elements", "relationship", "unfilled"],
            "description": "Optional focused view. Omit for the base structural map. "
                           "'arc' = one character's arc beats, pass character. "
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
            "description": "For view='dramatic_elements': limit to one act id. "
                           "Defaults to all."
        },
        "field": {
            "type": "string",
            "description": "For view='unfilled': one field name (e.g. 'character_value_at_close'). "
                           "Answers 'who else is missing this?' — the unfiltered list is grouped by "
                           "field, so asking for one is a lookup, not a filter over the output."
        },
        "entity": {
            "type": "string",
            "description": "For view='unfilled': one entity id. Answers 'what did I skip on this?'. "
                           "Pair with `field` to ask both ways at once."
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
    if view == "dramatic_elements":
        return _view_dramatic_elements(conn, args)
    if view == "relationship":
        return _view_relationship(conn)
    if view == "unfilled":
        return _view_unfilled(project_path, args)
    return {"error": f"Unknown view: {view}. Valid: arc, "
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


def _view_dramatic_elements(conn, args: dict) -> dict:
    """Every dramatic fact in one view, so two kinds can be checked against
    each other: the STRUCTURAL milestones (inciting incident, the three
    climaxes) and the PLOT dramatic roles.

    Milestones are the main plot's roles. A scene's plot roles are relations
    reaching at it from each plot — the role comes from the relation kind
    ("plot_setup" -> "setup") — and the main plot's inciting_incident, crisis
    and climax roles are the story-level milestones.
    """
    act_filter = args.get("act")

    # Which plots point at which scene, in which role. Built unconditionally:
    # the view exists to cross-check the plot roles against the structural
    # ones, so withholding half of them defeats it. The role comes from the
    # relation kind ("plot_setup" -> "setup") so this needs no hardcoded list
    # to drift out of sync with the schemas.
    plot_refs = {}
    for plot_id, in conn.execute(
            "SELECT id FROM entities WHERE type='plot' AND is_deleted=0 ORDER BY id"):
        for to_id, kind in conn.execute(
                "SELECT to_id, kind FROM relations "
                "WHERE from_id=:f AND kind LIKE 'plot\\_%' ESCAPE '\\'",
                {"f": plot_id}):
            plot_refs.setdefault(to_id, []).append(
                {"plot": plot_id, "role": kind[len("plot_"):]})

    # Plot scopes, so milestone_label knows which plot is the main one.
    plot_scopes = {}
    for plot_id, extra_json in conn.execute(
            "SELECT id, extra FROM entities WHERE type='plot' AND is_deleted=0"):
        pe = json.loads(extra_json or "{}")
        plot_scopes[plot_id] = pe.get("plot_scope", "")

    acts_out = []
    for act_id, act_title, act_order, act_extra_json in conn.execute(
            "SELECT id, name, order_key, extra FROM entities "
            "WHERE type='act' AND is_deleted=0 ORDER BY order_key, id").fetchall():
        if act_filter and act_id != act_filter:
            continue
        act_extra = json.loads(act_extra_json or "{}")
        act = {"id": act_id, "title": act_title}
        seqs_out = []
        for seq_id, seq_title, seq_order, seq_extra_json in conn.execute(
                "SELECT id, name, order_key, extra FROM entities "
                "WHERE type='sequence' AND parent_id=:p ORDER BY order_key, id",
                {"p": act_id}).fetchall():
            seq_extra = json.loads(seq_extra_json or "{}")
            seq = {"id": seq_id, "title": seq_title}
            if seq_extra.get("primary_plot"):
                seq["primary_plot"] = seq_extra["primary_plot"]
            scenes_out = []
            for scene_id, scene_title, one_sentence, order_key, status, extra_json in conn.execute(
                    "SELECT id, name, one_sentence, order_key, status, extra FROM entities "
                    "WHERE type='scene' AND parent_id=:p AND is_deleted=0 "
                    "ORDER BY order_key, id",
                    {"p": seq_id}).fetchall():
                extra = json.loads(extra_json or "{}")
                scene = {
                    "id": scene_id,
                    "title": scene_title,
                    "status": status,
                }
                if one_sentence:
                    scene["one_sentence"] = one_sentence
                # `dramatic_role` is emitted whenever it is set, INCLUDING
                # "plot_role". That is the point of the view: "plot_role"
                # beside a `plots[]` entry is the agreement, and a reader
                # checking the two halves can see when the scene says it
                # serves a plot and no plot agrees. An empty value is omitted
                # — it asserts nothing, and this view is not the unfilled map.
                if extra.get("dramatic_role"):
                    scene["dramatic_role"] = extra["dramatic_role"]
                # Milestones are the main plot's roles, derived from the
                # scene's plot_roles. A scene can hold multiple (e.g. both
                # the inciting incident and a complication).
                milestones = milestone_label(plot_refs.get(scene_id, []), plot_scopes)
                if milestones:
                    scene["milestone"] = milestones
                if scene_id in plot_refs:
                    scene["plots"] = plot_refs[scene_id]
                scenes_out.append(scene)
            seq["scenes"] = scenes_out
            seqs_out.append(seq)
        act["sequences"] = seqs_out
        acts_out.append(act)

    # The project is the top container even when `act` narrows to one act: the
    # story's climax and inciting incident are global facts, and a reader who
    # filtered down to a single act still needs them to judge what the act is
    # part of. Emitted unconditionally, whether or not it is set, so the shape
    # does not change with the data.
    proj_row = conn.execute(
        "SELECT extra FROM entities WHERE type='project' AND is_deleted=0 LIMIT 1"
    ).fetchone()
    pro = json.loads(proj_row[0]) if proj_row and proj_row[0] else {}
    # The plot index, at the top, under the project. This view's scenes carry
    # plot SLUGS, and a slug is meaningless without knowing which plot it is
    # and how it sits against the others — main or sub, and which of the four
    # types. Listing them once here is what makes a scene's `plots[]` entries
    # readable, and it is the only place the two sets can be compared: a plot
    # in this index with no scene below it is a plot serving nothing.
    #
    # Each entry carries its own milestones — the scenes holding each role in
    # THAT plot. The main plot's are the story's; every sub-plot's are its own.
    scene_order = {sid: ok for sid, ok in conn.execute(
        "SELECT id, order_key FROM entities WHERE type='scene' AND is_deleted=0")}
    plot_milestones = {}
    for scene_id, roles in plot_refs.items():
        for entry in roles:
            plot_milestones.setdefault(entry["plot"], {}).setdefault(
                entry["role"], []).append(scene_id)
    for roles in plot_milestones.values():
        for scene_ids in roles.values():
            # Story order, so a plot with several scenes in one role lists
            # them as they happen rather than in relation-insertion order.
            scene_ids.sort(key=lambda sid: (scene_order.get(sid, 0), sid))

    plot_index = []
    for plot_id, plot_name, plot_extra_json in conn.execute(
            "SELECT id, name, extra FROM entities "
            "WHERE type='plot' AND is_deleted=0 ORDER BY id").fetchall():
        pe = json.loads(plot_extra_json or "{}")
        plot_index.append({
            "id": plot_id,
            "name": plot_name,
            "plot_scope": pe.get("plot_scope", ""),
            "plot_type": pe.get("plot_type", ""),
            "milestones": plot_milestones.get(plot_id, {}),
        })
    # Story-level milestones are the main plot's roles. Find the main plot's
    # inciting_incident and climax scenes from the plot role relations.
    main_milestones = {"inciting_incident": [], "climax": []}
    main_plot_ids = [pid for pid, scope in plot_scopes.items() if scope == "main"]
    if main_plot_ids:
        for scene_id, roles in plot_refs.items():
            for entry in roles:
                if entry["plot"] in main_plot_ids and entry["role"] in main_milestones:
                    main_milestones[entry["role"]].append(scene_id)

    out = {
        "view": "dramatic_elements",
        "act": act_filter or "all",
        "project": {
            "structure_type": pro.get("structure_type", ""),
            "story_climax_scene_id": main_milestones["climax"] or "unfilled",
            "inciting_incident_scene_id": main_milestones["inciting_incident"] or "unfilled",
            "plots": plot_index,
        },
        "acts": acts_out,
    }
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
    """What is still at its default, and — with a filter — one answer at a time.

    The two questions worth asking are both lookups against the same inverted
    map:

      field=X   "who else is missing X?" — the other entities that skipped it
      entity=Y  "what did I skip on Y?"  — the fields that entity is missing

    Unfiltered, the list is grouped by field and sorted by how many entities
    share each gap. That ordering is not a priority ranking: `goals_long` is
    high because nothing writes it, not because it matters more. To ask about
    a specific one, filter — a filtered answer is never truncated.
    """
    from core.db import get_unfilled_map

    unfilled = get_unfilled_map(project_path)
    field = args.get("field")
    entity = args.get("entity")

    if field or entity:
        return _unfilled_focused(unfilled, field, entity)

    items = [{"field": f, "entities": ids, "count": len(ids)}
             for f, ids in unfilled.items()]
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
                       f"other_fields lists the rest — still gaps. "
                       f"Pass field=<name> for one, or entity=<id> for one entity.")
    if not items:
        out["message"] = "Nothing is at default — every optional field is filled."
    return out


def _unfilled_focused(unfilled: dict, field: str | None, entity: str | None) -> dict:
    """One field's entities, or one entity's fields. Never truncated.

    A filtered answer is complete by construction: you asked about one field or
    one entity, so there is nothing to cut off and no `other_fields` to warn
    about. That is the whole reason to filter rather than read the long list.

    No counts. The lists are the answer, and a count beside a list is a second
    thing to keep in step with it. No "is this entity in that list" flag
    either — the caller is holding both.
    """
    out: dict = {"view": "unfilled"}
    if field:
        out["field"] = field
        out["entities"] = unfilled.get(field, [])
        if not out["entities"]:
            out["message"] = (
                f"'{field}' is missing on no entity — either it is filled "
                f"everywhere, or it is not a field. story_describe lists the "
                f"fields that exist.")
    if entity:
        out["entity"] = entity
        out["fields"] = sorted(f for f, ids in unfilled.items() if entity in ids)
        if not out["fields"]:
            out["message"] = f"'{entity}' has every optional field filled."
    return out


def project_path_of(conn) -> Path:
    """Recover the project folder from the database file the connection is on."""
    # ponytail: sqlite exposes the file path; the plugin always uses .story/story.db.
    return Path(conn.execute("PRAGMA database_list").fetchone()[2]).parent.parent
