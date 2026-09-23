"""Database connection, schema creation, and table existence checks."""
import json
import sqlite3
from pathlib import Path

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS entities (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,
    name TEXT NOT NULL DEFAULT '',
    one_sentence TEXT NOT NULL DEFAULT '',
    order_key REAL NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT '',
    parent_id TEXT,
    location_id TEXT,
    extra JSON NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS relations (
    from_id TEXT NOT NULL,
    to_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    note TEXT NOT NULL DEFAULT '',
    "order" INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (from_id, to_id, kind)
);

CREATE TABLE IF NOT EXISTS sections (
    entity_id TEXT NOT NULL,
    heading TEXT NOT NULL,
    body TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (entity_id, heading)
);

CREATE VIRTUAL TABLE IF NOT EXISTS sections_fts USING fts5(
    body,
    content='sections',
    content_rowid='rowid'
);

CREATE TRIGGER IF NOT EXISTS sections_ai AFTER INSERT ON sections BEGIN
    INSERT INTO sections_fts(rowid, body) VALUES (new.rowid, new.body);
END;
CREATE TRIGGER IF NOT EXISTS sections_ad AFTER DELETE ON sections BEGIN
    INSERT INTO sections_fts(sections_fts, rowid, body) VALUES ('delete', old.rowid, old.body);
END;
CREATE TRIGGER IF NOT EXISTS sections_au AFTER UPDATE ON sections BEGIN
    INSERT INTO sections_fts(sections_fts, rowid, body) VALUES ('delete', old.rowid, old.body);
    INSERT INTO sections_fts(rowid, body) VALUES (new.rowid, new.body);
END;
"""


def get_db(project_path: Path) -> sqlite3.Connection:
    """Open a short-lived connection with WAL mode and busy_timeout.

    Uses autocommit mode (isolation_level=None) — callers explicitly
    BEGIN/COMMIT/ROLLBACK for transactions. Avoids nested-transaction errors
    from SQLite's implicit transaction behavior.
    """
    db_path = project_path / ".story" / "story.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), isolation_level=None)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=3000")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def create_schema(conn: sqlite3.Connection) -> None:
    """Create all tables, indexes, triggers."""
    conn.executescript(SCHEMA_SQL)


def has_schema(conn: sqlite3.Connection) -> bool:
    """Check if all required tables exist."""
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name IN ('entities', 'relations', 'sections', 'sections_fts')"
    )
    tables = {row[0] for row in cursor.fetchall()}
    return {"entities", "relations", "sections", "sections_fts"}.issubset(tables)


_PROJECT_DEFAULTS = {
    "logline": "logline not set",
    "genre": "genre not set",
    "setting": "not set",
    "spine": "Spine not set",
    "controlling_idea": "Controlling Idea not set",
    "value": "Value not set",
    "value_at_open": "Opening Value not set",
    "value_at_close": "Closing Value not set",
    "structure_type": "Structure Type not set",
    "act_count": 3,
    "inciting_incident_scene_id": "Inciting Incident Scene not set",
    "story_climax_scene_id": "Story Climax Scene not set",
}


def get_memory_outline(project_path: Path) -> dict:
    """Parse ## headings from .story/memory.md, return outline with preview lines."""
    memory_path = project_path / ".story" / "memory.md"
    if not memory_path.exists():
        return {"status": "placeholder — design deferred, see §5", "sections": []}

    content = memory_path.read_text()
    sections = []
    lines = content.split("\n")
    current_heading = None
    preview = ""

    for line in lines:
        if line.startswith("## "):
            if current_heading is not None:
                sections.append({"heading": current_heading, "preview": preview})
            current_heading = line[3:].strip()
            preview = ""
        elif current_heading is not None and not preview and line.strip():
            preview = line.strip()[:120]

    if current_heading is not None:
        sections.append({"heading": current_heading, "preview": preview})

    return {"status": "placeholder — design deferred, see §5", "sections": sections}


def get_project_summary(project_path: Path) -> dict:
    """Return nested project summary for story_load (spec §2).

    Shape: {loaded, confirmation, project, acts, characters, plots,
            locations, worlds, unfilled, memory_outline}
    """
    conn = get_db(project_path)
    try:
        # ── Project metadata ──
        row = conn.execute(
            "SELECT name, one_sentence, extra FROM entities WHERE type='project'"
        ).fetchone()
        if row:
            proj_name, proj_one_sentence, proj_extra_json = row
            proj_extra = json.loads(proj_extra_json) if proj_extra_json else {}
            project = {
                "name": proj_name,
                "logline": proj_one_sentence,
                "status": proj_extra.get("status", ""),
                "genre": proj_extra.get("genre", ""),
                "setting": proj_extra.get("setting", ""),
                "spine": proj_extra.get("spine", ""),
                "controlling_idea": proj_extra.get("controlling_idea", ""),
                "value": proj_extra.get("value", ""),
                "value_at_open": proj_extra.get("value_at_open", ""),
                "value_at_close": proj_extra.get("value_at_close", ""),
                "structure_type": proj_extra.get("structure_type", ""),
                "act_count": proj_extra.get("act_count", 3),
                "inciting_incident_scene_id": proj_extra.get("inciting_incident_scene_id", ""),
                "story_climax_scene_id": proj_extra.get("story_climax_scene_id", ""),
            }
            project = {k: v for k, v in project.items()
                       if k in ("status", "act_count") or (v and v != _PROJECT_DEFAULTS.get(k))}
        else:
            project = {"name": "Unknown", "logline": "", "status": ""}

        # ── All entities (excluding project) ──
        ent_rows = conn.execute(
            "SELECT id, type, name, one_sentence, status, order_key, parent_id, extra "
            "FROM entities WHERE type != 'project'"
        ).fetchall()

        # ── All relations ──
        rel_rows = conn.execute(
            "SELECT from_id, to_id, kind, note FROM relations"
        ).fetchall()

        # ── Build cross-reference maps ──
        scene_chars = {}  # scene_id -> [char_slug, ...]
        scene_loc = {}    # scene_id -> loc_slug
        char_rels = {}    # char_slug -> [{id, label, feeling}, ...]
        plot_scenes = {}  # plot_slug -> {"setups": [], "crisis": [], "climax": [], "payoffs": []}
        variant_of = {}   # entity_id -> base_slug (location_variant / world_variant)

        for from_id, to_id, kind, note in rel_rows:
            if kind == "character_scene":
                scene_chars.setdefault(to_id, []).append(from_id)
            elif kind == "location_scene":
                scene_loc[to_id] = from_id
            elif kind == "character_relationship":
                try:
                    parsed = json.loads(note) if note else {}
                except (json.JSONDecodeError, TypeError):
                    parsed = {}
                char_rels.setdefault(from_id, []).append({
                    "id": to_id,
                    "label": parsed.get("label", ""),
                    "feeling": parsed.get("feeling", ""),
                })
            elif kind == "plot_setup":
                plot_scenes.setdefault(from_id, {}).setdefault("setups", []).append(to_id)
            elif kind == "plot_crisis":
                plot_scenes.setdefault(from_id, {}).setdefault("crisis", []).append(to_id)
            elif kind == "plot_climax":
                plot_scenes.setdefault(from_id, {}).setdefault("climax", []).append(to_id)
            elif kind == "plot_payoff":
                plot_scenes.setdefault(from_id, {}).setdefault("payoffs", []).append(to_id)
            elif kind in ("location_variant", "world_variant"):
                variant_of[from_id] = to_id

        # ── Organize entities by type ──
        acts = {}
        sequences = {}
        scenes = {}
        characters = {}
        plots = {}
        locations = {}
        worlds = {}
        relationships = {}
        for eid, etype, name, one_sentence, status, order_key, parent_id, extra_json in ent_rows:
            extra = json.loads(extra_json) if extra_json else {}

            if etype == "act":
                acts[eid] = {
                    "id": eid, "title": name, "status": status,
                    "value": extra.get("value", "Value not set"),
                    "value_open": extra.get("value_open", ""),
                    "value_close": extra.get("value_close", ""),
                    "_order_key": order_key, "_parent_id": parent_id,
                }
            elif etype == "sequence":
                sequences[eid] = {
                    "id": eid, "title": name, "status": status,
                    "value": extra.get("value", "Value not set"),
                    "value_open": extra.get("value_open", ""),
                    "value_close": extra.get("value_close", ""),
                    "_order_key": order_key, "_parent_id": parent_id,
                }
            elif etype == "scene":
                scenes[eid] = {
                    "id": eid, "title": name, "status": status,
                    "one_sentence": one_sentence,
                    "dramatic_role": extra.get("dramatic_role", ""),
                    "_order_key": order_key, "_parent_id": parent_id,
                    "_extra": extra,
                }
            elif etype == "character":
                characters[eid] = {
                    "id": eid, "name": name, "one_sentence": one_sentence,
                    "story_role": extra.get("story_role", ""),
                    "arc_type": extra.get("arc_type", "Arc type not set"),
                    "arc_value": extra.get("arc_value", "Arc value not set"),
                    "arc_value_at_open": extra.get("arc_value_at_open", "Not set"),
                    "arc_value_at_close": extra.get("arc_value_at_close", "Not set"),
                }
            elif etype == "plot":
                plots[eid] = {
                    "id": eid, "name": name, "one_sentence": one_sentence,
                    "status": status,
                    "plot_type": extra.get("plot_type", ""),
                    "plot_scope": extra.get("plot_scope", ""),
                    "value_arc": extra.get("value_arc", ""),
                    "characters": extra.get("characters", []),
                }
            elif etype == "location":
                locations[eid] = {
                    "id": eid, "name": name, "one_sentence": one_sentence,
                    "mood": extra.get("mood", ""),
                    "dramatic_function": extra.get("dramatic_function", ""),
                    "_order_key": order_key, "_parent_id": parent_id,
                }
            elif etype == "world":
                worlds[eid] = {
                    "id": eid, "name": name, "one_sentence": one_sentence,
                    "rules": extra.get("rules", []),
                    "period": extra.get("period", ""),
                    "values": extra.get("values", []),
                    "power": extra.get("power", []),
                    "_order_key": order_key, "_parent_id": parent_id,
                }
            elif etype == "relationship":
                relationships[eid] = {
                    "id": eid, "name": name, "status": status,
                    "characters": extra.get("characters", []),
                    "perspectives": extra.get("perspectives", {}),
                    "scenes": extra.get("scenes", []),
                    "history": extra.get("history", ""),
                }


        # ── Helpers ──
        def _is_scene_stub(s):
            return s["status"] == "planned" or not s["dramatic_role"]

        def _milestone_marker(extra):
            if extra.get("is_inciting_incident"):
                return "inciting incident"
            if extra.get("is_story_climax"):
                return "story climax"
            if extra.get("is_act_climax"):
                return "act climax"
            if extra.get("is_sequence_climax"):
                return "sequence climax"
            return None

        def _omit(d, defaults, always_keep=None):
            always_keep = always_keep or set()
            return {k: v for k, v in d.items()
                    if k in always_keep or (v and v != defaults.get(k))}

        # ── Build scene output ──
        def _build_scene(sid):
            s = scenes[sid]
            stub = _is_scene_stub(s)
            chars = scene_chars.get(sid, [])
            if stub:
                result = {"id": sid}
                if chars:
                    result["chars"] = chars
                return result
            result = {
                "id": sid,
                "title": s["title"],
                "status": s["status"],
                "one_sentence": s["one_sentence"],
                "dramatic_role": s["dramatic_role"],
                "chars": chars,
                "loc": scene_loc.get(sid),
                "milestone": _milestone_marker(s["_extra"]),
            }
            return _omit(result, {"one_sentence": "", "dramatic_role": "", "chars": [], "loc": None, "milestone": None},
                         always_keep={"status"})

        # ── Build sequence output ──
        def _build_sequence(seq_id):
            seq = sequences[seq_id]
            child_scene_ids = sorted(
                [sid for sid, s in scenes.items() if s["_parent_id"] == seq_id],
                key=lambda sid: (scenes[sid]["_order_key"], sid)
            )
            result = {
                "id": seq["id"],
                "title": seq["title"],
                "status": seq["status"],
                "value": seq["value"],
                "value_open": seq["value_open"],
                "value_close": seq["value_close"],
                "scenes": [_build_scene(sid) for sid in child_scene_ids],
            }
            return _omit(result, {"value": "Value not set", "value_open": "", "value_close": ""},
                         always_keep={"status"})

        # ── Build act output ──
        def _build_act(act_id):
            act = acts[act_id]
            child_seq_ids = sorted(
                [sid for sid, s in sequences.items() if s["_parent_id"] == act_id],
                key=lambda sid: (sequences[sid]["_order_key"], sid)
            )
            result = {
                "id": act["id"],
                "title": act["title"],
                "status": act["status"],
                "value": act["value"],
                "value_open": act["value_open"],
                "value_close": act["value_close"],
                "sequences": [_build_sequence(sid) for sid in child_seq_ids],
            }
            return _omit(result, {"value": "Value not set", "value_open": "", "value_close": ""},
                         always_keep={"status"})

        # Build top-level acts (those without parent_id or parent not in acts)
        top_act_ids = sorted(
            [aid for aid, a in acts.items() if not a["_parent_id"] or a["_parent_id"] not in acts],
            key=lambda aid: (acts[aid]["_order_key"], aid)
        )
        acts_list = [_build_act(aid) for aid in top_act_ids]

        # ── Computed character relationship summary (CONVENTION_computed_fields) ──
        char_rel_summary = {}
        for rel in relationships.values():
            for char_id in rel["characters"]:
                others = [c for c in rel["characters"] if c != char_id]
                if not others:
                    continue
                p = rel["perspectives"].get(char_id, {})
                char_rel_summary.setdefault(char_id, []).append({
                    "with": others[0],
                    "label": p.get("label", ""),
                    "type": p.get("type", ""),
                })

        # ── Build character output ──
        def _build_character(char_id):
            char = characters[char_id]
            result = {
                "id": char_id,
                "name": char["name"],
                "one_sentence": char["one_sentence"],
                "story_role": char["story_role"],
                "arc_type": char["arc_type"],
                "arc_value": char["arc_value"],
                "arc_value_at_open": char["arc_value_at_open"],
                "arc_value_at_close": char["arc_value_at_close"],
                "rel": char_rels.get(char_id, []),
                "relationships": char_rel_summary.get(char_id, []),
            }
            return _omit(result, {"arc_type": "Arc type not set", "arc_value": "Arc value not set",
                                  "arc_value_at_open": "Not set", "arc_value_at_close": "Not set", "rel": [], "relationships": []})

        # ── Build plot output ──
        def _build_plot(plot_id):
            plot = plots[plot_id]
            ps = plot_scenes.get(plot_id, {})
            result = {
                "id": plot_id,
                "name": plot["name"],
                "one_sentence": plot["one_sentence"],
                "status": plot["status"],
                "plot_type": plot["plot_type"],
                "plot_scope": plot["plot_scope"],
                "value_arc": plot["value_arc"],
                "characters": plot["characters"],
                "setups": ps.get("setups", []),
                "crisis": ps.get("crisis", []),
                "climax": ps.get("climax", []),
                "payoffs": ps.get("payoffs", []),
            }
            return _omit(result, {"plot_type": "", "plot_scope": "", "value_arc": "Value arc not set",
                                  "characters": [], "setups": [], "crisis": [], "climax": [], "payoffs": []},
                         always_keep={"status"})

        # ── Build location/world output ──
        def _build_location(loc_id):
            loc = locations[loc_id]
            result = {"id": loc_id, "name": loc["name"], "one_sentence": loc["one_sentence"]}
            if loc_id in variant_of:
                result["variant_of"] = variant_of[loc_id]
            return result

        def _build_world(world_id):
            w = worlds[world_id]
            child_loc_ids = sorted(
                [lid for lid, loc in locations.items() if loc.get("_parent_id") == world_id],
                key=lambda lid: (locations[lid]["_order_key"], lid),
            )
            locations_list = [_build_location(lid) for lid in child_loc_ids]
            result = {"id": world_id, "name": w["name"], "one_sentence": w["one_sentence"], "locations": locations_list}
            if w.get("period"):
                result["period"] = w["period"]
            if world_id in variant_of:
                result["variant_of"] = variant_of[world_id]
            return result

        characters_list = [_build_character(cid) for cid in characters]
        plots_list = [_build_plot(pid) for pid in plots]
        worlds_list = [_build_world(wid) for wid in worlds]

        # Orphaned locations (no world, or world doesn't exist) — top-level array
        orphaned_loc_ids = sorted(
            [lid for lid, loc in locations.items()
             if not loc.get("_parent_id") or loc["_parent_id"] not in worlds],
            key=lambda lid: (locations[lid]["_order_key"], lid),
        )
        orphaned_locations = [_build_location(lid) for lid in orphaned_loc_ids]

        # ── Unfilled (inverted) ──
        from .entity import unfilled_fields
        unfilled_inv = {}
        for eid, etype, name, one_sentence, status, order_key, parent_id, extra_json in ent_rows:
            extra = json.loads(extra_json) if extra_json else {}

            # Determine if stub (skip stubs — maximally unfilled by definition)
            is_stub = False
            if etype == "scene":
                dramatic_role = extra.get("dramatic_role", "")
                is_stub = status == "planned" or not dramatic_role
            elif etype == "arc_beat":
                is_stub = not name  # label stored in name column

            if is_stub:
                continue

            # Merge column-stored fields into extra for unfilled check
            if etype in ("scene", "sequence", "plot", "act") and status:
                extra = {**extra, "status": status}
            if etype in ("scene", "plot") and one_sentence:
                extra = {**extra, "one_sentence": one_sentence}
            # Merge relation-sourced fields for accurate unfilled detection
            if etype == "scene":
                chars = scene_chars.get(eid, [])
                if chars:
                    extra = {**extra, "characters": chars}
                loc = scene_loc.get(eid)
                if loc:
                    extra = {**extra, "location": loc}

            fields = unfilled_fields(etype, extra)
            for field in fields:
                unfilled_inv.setdefault(field, []).append(eid)

        # ── Confirmation string ──
        total_locations = len(locations)
        total_scenes = len(scenes)
        developed_scenes = sum(1 for s in scenes.values() if not _is_scene_stub(s))
        confirmation = (
            f"Loaded {project.get('name', 'Unknown')} — "
            f"{total_scenes} scenes ({developed_scenes} developed), "
            f"{len(sequences)} sequences, "
            f"{len(acts)} acts, "
            f"{len(characters)} characters, "
            f"{total_locations} locations, "
            f"{len(plots)} plots, "
            f"{len(worlds)} worlds."
        )

        # ── Memory outline ──
        memory_outline = get_memory_outline(project_path)

        result = {
            "loaded": True,
            "confirmation": confirmation,
            "project": project,
            "acts": acts_list,
            "characters": characters_list,
            "plots": plots_list,
            "worlds": worlds_list,
            "relationships": relationships,
            "unfilled": unfilled_inv,
            "memory_outline": memory_outline,
        }
        if orphaned_locations:
            result["orphaned_locations"] = orphaned_locations
        return result
    finally:
        conn.close()


def get_character_arcs(project_path: Path, char_id: str) -> list[dict]:
    """Return arc beats for a character, ordered by order_key then id.

    Used by story_retrieve to fetch arc details on demand.
    """
    import sqlite3
    db_path = project_path / ".story" / "story.db"
    if not db_path.exists():
        return []
    conn = None
    try:
        conn = sqlite3.connect(str(db_path))
        rows = conn.execute(
            "SELECT id, name, extra, order_key FROM entities WHERE type='arc_beat' AND parent_id=? ORDER BY order_key, id",
            (char_id,),
        ).fetchall()
        return [
            {
                "id": row[0],
                "label": row[1],
                "scene": json.loads(row[2]).get("scene", "") if row[2] else "",
                "shift": json.loads(row[2]).get("shift", "") if row[2] else "",
                "y": json.loads(row[2]).get("y", 0.0) if row[2] else 0.0,
                "is_crisis": json.loads(row[2]).get("is_crisis", False) if row[2] else False,
                "is_climax": json.loads(row[2]).get("is_climax", False) if row[2] else False,
            }
            for row in rows
        ]
    except Exception:
        return []
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass


def get_entity_sections(project_path: Path, entity_id: str) -> dict:
    """Return {heading: body} for an entity's sections. story_retrieve uses this."""
    conn = get_db(project_path)
    try:
        rows = conn.execute(
            "SELECT heading, body FROM sections WHERE entity_id=? ORDER BY rowid",
            (entity_id,)
        ).fetchall()
        return {heading: body for heading, body in rows}
    finally:
        conn.close()


def search_sections(project_path: Path, query: str) -> list[dict]:
    """FTS5 search across all sections. Returns list of {entity_id, heading, snippet}."""
    conn = get_db(project_path)
    try:
        # FTS5 query — join back to sections for entity_id + heading
        cursor = conn.execute(
            """SELECT s.entity_id, s.heading, s.body
               FROM sections_fts f
               JOIN sections s ON f.rowid = s.rowid
               WHERE f.body MATCH ?
               ORDER BY rank""",
            (query,)
        )
        return [
            {"entity_id": row[0], "heading": row[1], "snippet": row[2]}
            for row in cursor.fetchall()
        ]
    finally:
        conn.close()


def get_dashboard_data(project_path: Path) -> dict:
    """Return all 6 injection shapes for story_dashboard.

    Returns dict with keys:
      story_data: column-oriented entities (for __STORY_DATA__)
      sections: {entity_id: {heading: body}} (for __SECTIONS__)
      screenplay_text: concatenated scene ## Content (for __SCREENPLAY_STATS__)
      structural_stats: status/role counts (for __STRUCTURAL_STATS__)
      title_page: project frontmatter fields (for title page)
    """
    conn = get_db(project_path)
    try:
        # 1. story_data — denormalized projection per entity type
        ent_rows = conn.execute(
            "SELECT id, type, name, one_sentence, order_key, status, parent_id, location_id, extra "
            "FROM entities ORDER BY type, id"
        ).fetchall()

        # Build entity lookup for cross-references (must precede rel lookups)
        entity_by_id = {}
        for r in ent_rows:
            entity_by_id[r[0]] = {
                "id": r[0], "type": r[1], "name": r[2], "one_sentence": r[3],
                "order": r[4], "status": r[5], "parent_id": r[6], "location_id": r[7],
                "extra": json.loads(r[8]) if r[8] else {},
            }

        # Load all relations for denormalization (include note for plot beat descriptions)
        rel_rows = conn.execute(
            "SELECT from_id, to_id, kind, note FROM relations"
        ).fetchall()
        # Build lookup: entity_id -> {kind -> [{to_id, note}]}
        rel_map = {}
        for from_id, to_id, kind, note in rel_rows:
            if from_id not in rel_map:
                rel_map[from_id] = {}
            if kind not in rel_map[from_id]:
                rel_map[from_id][kind] = []
            rel_map[from_id][kind].append({"to_id": to_id, "note": note or ""})

        # Build reverse lookups from rel_rows (single pass, O(M) total)
        scene_chars = {}
        scene_locs = {}
        scene_plots = {}
        char_scenes = {}  # character_id → [scene_id, ...]
        variant_map = {}  # entity_id → variant_of (location_variant / world_variant)
        for from_id, to_id, kind, note in rel_rows:
            if kind == "character_scene":
                # Relation may be stored character→scene OR scene→character
                # (import vs story_create conventions). Detect by checking
                # which side is a character vs scene entity.
                if from_id in entity_by_id and entity_by_id[from_id]["type"] == "character":
                    scene_chars.setdefault(to_id, []).append(from_id)
                    char_scenes.setdefault(from_id, []).append(to_id)
                elif to_id in entity_by_id and entity_by_id[to_id]["type"] == "character":
                    scene_chars.setdefault(from_id, []).append(to_id)
                    char_scenes.setdefault(to_id, []).append(from_id)
            elif kind == "location_scene":
                scene_locs.setdefault(to_id, []).append(from_id)
            elif kind in ("plot_setup", "plot_crisis", "plot_climax", "plot_payoff"):
                beat = kind.replace("plot_", "")
                scene_plots.setdefault(to_id, []).append({"id": from_id, "beat": beat})
            elif kind in ("location_variant", "world_variant"):
                variant_map[from_id] = to_id

        # Denormalize: build per-type arrays with cross-references
        def _entity_dict(e):
            d = {
                "id": e["id"],
                "name": e["name"],
                "one_sentence": e["one_sentence"],
                "status": e["status"],
                "order": e["order"],
                "parent_id": e["parent_id"],
            }
            # Merge extra fields at top level
            for k, v in e["extra"].items():
                if k not in d:
                    d[k] = v
            return d

        characters = []
        scenes = []
        locations = []
        plots = []
        worlds = []
        acts = []
        sequences = []
        arcs = []
        relationships = []

        for e in ent_rows:
            etype = e[1]
            eid = e[0]
            extra = json.loads(e[8]) if e[8] else {}

            if etype == "character":
                d = _entity_dict({
                    "id": eid, "name": e[2], "one_sentence": e[3], "order": e[4],
                    "status": e[5], "parent_id": e[6], "extra": extra,
                })
                # scenes: [{id, title, heading}] (from character_scene relations)
                scene_objs = []
                for sid in char_scenes.get(eid, []):
                    if sid in entity_by_id:
                        s = entity_by_id[sid]
                        s_extra = s.get("extra", {})
                        scene_objs.append({
                            "id": sid,
                            "title": s.get("name", ""),
                            "heading": s_extra.get("heading", ""),
                        })
                d["scenes"] = scene_objs
                # relationships: denormalized from character_relationship
                rels = []
                for rel in rel_map.get(eid, {}).get("character_relationship", []):
                    target_id = rel.get("to_id", "") if isinstance(rel, dict) else rel
                    if target_id in entity_by_id:
                        t = entity_by_id[target_id]
                        note = rel.get("note", "") if isinstance(rel, dict) else ""
                        try:
                            parsed = json.loads(note) if note else {}
                        except (json.JSONDecodeError, TypeError):
                            parsed = {}
                        rels.append({
                            "id": t["id"],
                            "label": parsed.get("label", ""),
                            "feeling": parsed.get("feeling", ""),
                        })
                d["relationships"] = rels
                characters.append(d)

            elif etype == "scene":
                d = _entity_dict({
                    "id": eid, "name": e[2], "one_sentence": e[3], "order": e[4],
                    "status": e[5], "parent_id": e[6], "extra": extra,
                })
                d["title"] = e[2]  # alias for dashboard (reads s.title)
                d["sequence_id"] = e[6]  # alias for dashboard (reads s.sequence_id)
                d["act_id"] = extra.get("act_id", "")
                # characters, locations, plots — O(1) reverse lookups
                d["characters"] = scene_chars.get(eid, [])
                d["locations"] = scene_locs.get(eid, [])
                if e[7] and e[7] not in d["locations"]:
                    d["locations"].append(e[7])
                d["plots"] = scene_plots.get(eid, [])
                scenes.append(d)

            elif etype == "location":
                d = _entity_dict({
                    "id": eid, "name": e[2], "one_sentence": e[3], "order": e[4],
                    "status": e[5], "parent_id": e[6], "extra": extra,
                })
                if eid in variant_map:
                    d["variant_of"] = variant_map[eid]
                # scenes: [{id, title, heading}] (from location_scene relations)
                scene_objs = []
                for rel in rel_map.get(eid, {}).get("location_scene", []):
                    sid = rel.get("to_id", "") if isinstance(rel, dict) else rel
                    if sid in entity_by_id:
                        s = entity_by_id[sid]
                        s_extra = s.get("extra", {})
                        scene_objs.append({
                            "id": sid,
                            "title": s.get("name", ""),
                            "heading": s_extra.get("heading", ""),
                        })
                d["scenes"] = scene_objs
                locations.append(d)

            elif etype == "plot":
                d = _entity_dict({
                    "id": eid, "name": e[2], "one_sentence": e[3], "order": e[4],
                    "status": e[5], "parent_id": e[6], "extra": extra,
                })
                # Normalize all plot beat fields to [{scene_id, description}] objects
                def _normalize_beats(beats):
                    result = []
                    for b in beats:
                        if isinstance(b, dict):
                            if "to_id" in b:
                                # New format: {to_id, note}
                                result.append({"scene_id": b["to_id"], "description": b.get("note", "")})
                            else:
                                # Already normalized: {scene_id, description}
                                result.append(b)
                        else:
                            result.append({"scene_id": str(b), "description": ""})
                    return result
                d["setups"] = _normalize_beats(rel_map.get(eid, {}).get("plot_setup", []))
                d["crisis"] = _normalize_beats(rel_map.get(eid, {}).get("plot_crisis", []))
                d["climax"] = _normalize_beats(rel_map.get(eid, {}).get("plot_climax", []))
                d["payoffs"] = _normalize_beats(rel_map.get(eid, {}).get("plot_payoff", []))
                # characters from character list (stored in extra.characters)
                d["characters"] = extra.get("characters", [])
                plots.append(d)

            elif etype == "world":
                d = _entity_dict({
                    "id": eid, "name": e[2], "one_sentence": e[3], "order": e[4],
                    "status": e[5], "parent_id": e[6], "extra": extra,
                })
                if eid in variant_map:
                    d["variant_of"] = variant_map[eid]
                worlds.append(d)

            elif etype == "act":
                d = _entity_dict({
                    "id": eid, "name": e[2], "one_sentence": e[3], "order": e[4],
                    "status": e[5], "parent_id": e[6], "extra": extra,
                })
                d["title"] = e[2]  # alias for dashboard (reads act.title)
                acts.append(d)

            elif etype == "sequence":
                d = _entity_dict({
                    "id": eid, "name": e[2], "one_sentence": e[3], "order": e[4],
                    "status": e[5], "parent_id": e[6], "extra": extra,
                })
                d["title"] = e[2]  # alias for dashboard (reads seq.title)
                d["act_id"] = e[6]  # alias for dashboard (reads seq.act_id)
                sequences.append(d)

            elif etype == "arc_beat":
                d = _entity_dict({
                    "id": eid, "name": e[2], "one_sentence": e[3], "order": e[4],
                    "status": e[5], "parent_id": e[6], "extra": extra,
                })
                # Denormalize all arc fields for dashboard (reads d.action, d.choice, etc.)
                d["action"] = extra.get("action", "")
                d["choice"] = extra.get("choice", "")
                d["gap"] = extra.get("gap", "")
                d["shift"] = extra.get("shift", "")
                d["y"] = extra.get("y", 0.0)
                d["is_crisis"] = extra.get("is_crisis", False)
                d["is_climax"] = extra.get("is_climax", False)
                d["character"] = extra.get("character", e[6] or "")
                d["scene"] = extra.get("scene", "")
                d["label"] = extra.get("label", e[2])  # label is stored in name column
                arcs.append(d)

            elif etype == "relationship":
                d = _entity_dict({
                    "id": eid, "name": e[2], "one_sentence": e[3], "order": e[4],
                    "status": e[5], "parent_id": e[6], "extra": extra,
                })
                d["characters"] = extra.get("characters", [])
                d["perspectives"] = extra.get("perspectives", {})
                d["scenes"] = extra.get("scenes", [])
                d["history"] = extra.get("history", "")
                relationships.append(d)

        # Group arcs by character and attach as arc_beats_list (dashboard reads c.arc_beats_list)
        # Derived from arc entities directly — no separate arc_beat relations needed
        for a in arcs:
            char_id = a.get("character") or a.get("parent_id")
            if not char_id:
                continue
            for c in characters:
                if c["id"] == char_id:
                    if "arc_beats_list" not in c:
                        c["arc_beats_list"] = []
                    c["arc_beats_list"].append({
                        "id": a.get("id", ""),
                        "label": a.get("label", ""),
                        "scene": a.get("scene", ""),
                        "shift": a.get("shift", ""),
                        "y": a.get("y", 0.0),
                        "order": a.get("order", 0),
                        "is_crisis": a.get("is_crisis", False),
                        "is_climax": a.get("is_climax", False),
                    })
                    break

        # Sort each character's beats by order, set arc_beat_count
        for c in characters:
            if "arc_beats_list" in c:
                c["arc_beats_list"].sort(key=lambda b: b.get("order", 0))
                c["arc_beat_count"] = len(c["arc_beats_list"])

        # Computed character relationship summary for dashboard (richer than load — includes strength)
        char_rel_summary = {}
        for rel in relationships:
            for char_id in rel["characters"]:
                others = [c for c in rel["characters"] if c != char_id]
                if not others:
                    continue
                p = rel["perspectives"].get(char_id, {})
                char_rel_summary.setdefault(char_id, []).append({
                    "with": others[0],
                    "label": p.get("label", ""),
                    "type": p.get("type", ""),
                    "strength": p.get("strength", 0),
                })
        for c in characters:
            c["relationships"] = char_rel_summary.get(c["id"], [])

        # Rename arcs to story.arcs for dashboard compatibility
        story_arcs = arcs

        # Build scene.arc_beats from arc entities (reverse lookup)
        scene_beats = {}
        for a in arcs:
            sid = a.get("scene", "")
            if not sid:
                continue
            if sid not in scene_beats:
                scene_beats[sid] = []
            scene_beats[sid].append({
                "character": a.get("character", ""),
                "beat_id": a.get("id", ""),
                "label": a.get("label", ""),
                "y": a.get("y", 0.0),
                "is_crisis": a.get("is_crisis", False),
                "is_climax": a.get("is_climax", False),
            })
        for s in scenes:
            s["arc_beats"] = scene_beats.get(s["id"], [])

        # Build sequence.scenes_list, scene_count, and plots
        plot_lookup = {p["id"]: p for p in plots}
        for seq in sequences:
            scenes_in_seq = sorted(
                [s for s in scenes if s.get("parent_id") == seq["id"]],
                key=lambda s: s.get("order", 0)
            )
            seq["scenes_list"] = [s["id"] for s in scenes_in_seq]
            seq["scene_count"] = len(seq["scenes_list"])
            # Aggregate plots from scenes (beat info populated by Task 7)
            seq_plots = {}
            for scene in scenes_in_seq:
                for p in scene.get("plots", []):
                    pid = p.get("id") if isinstance(p, dict) else p
                    if pid not in seq_plots:
                        meta = plot_lookup.get(pid, {})
                        seq_plots[pid] = {
                            "id": pid,
                            "has_setup": False, "has_crisis": False,
                            "has_climax": False, "has_payoff": False,
                            "plot_scope": meta.get("plot_scope", ""),
                            "plot_type": meta.get("plot_type", ""),
                            "value_arc": meta.get("value_arc", ""),
                        }
                    beat = p.get("beat", "") if isinstance(p, dict) else ""
                    if beat == "setup": seq_plots[pid]["has_setup"] = True
                    elif beat == "crisis": seq_plots[pid]["has_crisis"] = True
                    elif beat == "climax": seq_plots[pid]["has_climax"] = True
                    elif beat == "payoff": seq_plots[pid]["has_payoff"] = True
            seq["plots"] = sorted(seq_plots.values(), key=lambda x: (0 if x["plot_scope"] == "main" else 1, x["id"]))

        # Act enrichment: sequences_list, scenes_list (via sequences), counts, plots
        # In the new DB, scenes point to sequences (parent_id), not acts directly.
        # Act scenes must be derived by traversing act → sequences → scenes.
        for act in acts:
            seqs_in_act = sorted(
                [s for s in sequences if s.get("parent_id") == act["id"]],
                key=lambda s: s.get("order", 0)
            )
            act["sequences_list"] = [s["id"] for s in seqs_in_act]
            # Gather all scene IDs from child sequences, preserving sort order
            seq_order = {s["id"]: s.get("order", 0) for s in scenes}
            act_scene_ids = []
            for seq in seqs_in_act:
                act_scene_ids.extend(seq.get("scenes_list", []))
            act["scenes_list"] = sorted(act_scene_ids, key=lambda sid: seq_order.get(sid, 0))
            act["sequence_count"] = len(act["sequences_list"])
            act["scene_count"] = len(act["scenes_list"])
            # Aggregate plots from all scenes in child sequences
            act_plots = {}
            for scene in [s for s in scenes if s.get("id") in act_scene_ids]:
                for p in scene.get("plots", []):
                    pid = p.get("id") if isinstance(p, dict) else p
                    if pid not in act_plots:
                        meta = plot_lookup.get(pid, {})
                        act_plots[pid] = {
                            "id": pid,
                            "has_setup": False, "has_crisis": False,
                            "has_climax": False, "has_payoff": False,
                            "plot_scope": meta.get("plot_scope", ""),
                            "plot_type": meta.get("plot_type", ""),
                            "value_arc": meta.get("value_arc", ""),
                        }
                    beat = p.get("beat", "") if isinstance(p, dict) else ""
                    if beat == "setup": act_plots[pid]["has_setup"] = True
                    elif beat == "crisis": act_plots[pid]["has_crisis"] = True
                    elif beat == "climax": act_plots[pid]["has_climax"] = True
                    elif beat == "payoff": act_plots[pid]["has_payoff"] = True
            act["plots"] = sorted(act_plots.values(), key=lambda x: (0 if x["plot_scope"] == "main" else 1, x["id"]))

        # Project entity (for story_memory)
        proj_row = conn.execute(
            "SELECT name, one_sentence, extra FROM entities WHERE type='project'"
        ).fetchone()
        story_memory = {}
        if proj_row:
            story_memory = {
                "name": proj_row[0],
                "logline": proj_row[1],
                "title_page": {
                    "name": proj_row[0],
                    "logline": proj_row[1],
                    "screenplay_title": json.loads(proj_row[2]).get("screenplay_title", "") if proj_row[2] else "",
                    "credit": json.loads(proj_row[2]).get("credit", "") if proj_row[2] else "",
                    "author": json.loads(proj_row[2]).get("author", "") if proj_row[2] else "",
                    "contact": json.loads(proj_row[2]).get("contact", "") if proj_row[2] else "",
                    "draft_date": json.loads(proj_row[2]).get("draft_date", "") if proj_row[2] else "",
                    "draft": json.loads(proj_row[2]).get("draft", "") if proj_row[2] else "",
                },
            }

        # Project: dashboard reads p.logline (not one_sentence) and top-level extra fields
        proj_dict = entity_by_id.get(conn.execute("SELECT id FROM entities WHERE type='project' LIMIT 1").fetchone()[0], {})
        if proj_dict:
            if not proj_dict.get("logline") and proj_dict.get("one_sentence"):
                proj_dict["logline"] = proj_dict["one_sentence"]
            # Flatten extra fields to top level for dashboard
            for k, v in proj_dict.get("extra", {}).items():
                if k not in proj_dict:
                    proj_dict[k] = v
            # Project counts (dashboard stats row reads these directly)
            proj_dict["scene_count"] = len(scenes)
            proj_dict["character_count"] = len(characters)
            proj_dict["location_count"] = len(locations)
            proj_dict["world_count"] = len(worlds)
            proj_dict["plot_count"] = len(plots)
            proj_dict["sequence_count"] = len(sequences)
            proj_dict["act_count"] = max(proj_dict.get("act_count", 3), len(acts))
            proj_dict["arc_count"] = len(story_arcs)

        story_data = {
            "project": proj_dict,
            "characters": characters,
            "scenes": scenes,
            "locations": locations,
            "plots": plots,
            "worlds": worlds,
            "acts": acts,
            "sequences": sequences,
            "arcs": story_arcs,
            "relationships": relationships,
            "story_memory": story_memory,
        }

        # 2. sections — {entity_type: {slug: {heading: body}}}
        sec_rows = conn.execute(
            "SELECT s.entity_id, s.heading, s.body, e.type "
            "FROM sections s JOIN entities e ON s.entity_id = e.id "
            "ORDER BY s.entity_id, s.rowid"
        ).fetchall()
        sections = {}
        for entity_id, heading, body, entity_type in sec_rows:
            if entity_type not in sections:
                sections[entity_type] = {}
            if entity_id not in sections[entity_type]:
                sections[entity_type][entity_id] = {}
            sections[entity_type][entity_id][heading] = body

        # 3. screenplay_text — scene ## Content concatenated in order
        scene_content_rows = conn.execute(
            """SELECT s.body, e.order_key, p.order_key as parent_order
               FROM sections s
               JOIN entities e ON s.entity_id = e.id
               LEFT JOIN entities p ON e.parent_id = p.id
               WHERE e.type='scene' AND s.heading='Content'
               ORDER BY COALESCE(p.order_key, 0), e.order_key"""
        ).fetchall()
        screenplay_text = "\n\n".join(r[0] for r in scene_content_rows)

        # 4. structural_stats
        status_rows = conn.execute(
            "SELECT status, COUNT(*) FROM entities WHERE type='scene' GROUP BY status"
        ).fetchall()
        scene_status = dict(status_rows)

        role_rows = conn.execute(
            "SELECT json_extract(extra, '$.dramatic_role'), COUNT(*) "
            "FROM entities WHERE type='scene' "
            "GROUP BY json_extract(extra, '$.dramatic_role')"
        ).fetchall()
        scene_roles = {r[0] or "unset": r[1] for r in role_rows}

        seq_count = conn.execute(
            "SELECT COUNT(*) FROM entities WHERE type='sequence' "
        ).fetchone()[0]
        act_count = conn.execute(
            "SELECT COUNT(*) FROM entities WHERE type='act' "
        ).fetchone()[0]
        scene_count = sum(scene_status.values())

        # Act stats — count scenes/sequences per act
        act_rows = conn.execute(
            "SELECT id, name, order_key FROM entities WHERE type='act'  ORDER BY order_key"
        ).fetchall()
        acts_stats = []
        for act_id, act_name, act_order in act_rows:
            seq_c = conn.execute(
                "SELECT COUNT(*) FROM entities WHERE type='sequence' AND parent_id=? ",
                (act_id,)
            ).fetchone()[0]
            scene_c = conn.execute(
                """SELECT COUNT(*) FROM entities WHERE type='scene' 
                   AND parent_id IN (SELECT id FROM entities WHERE type='sequence' AND parent_id=? )""",
                (act_id,)
            ).fetchone()[0]
            acts_stats.append({
                "id": act_id, "title": act_name,
                "sceneCount": scene_c, "sequenceCount": seq_c,
            })

        # Plot coverage: count unique scenes per plot
        plot_scene_sets = {}
        for scene in scenes:
            for p in scene.get("plots", []):
                pid = p.get("id") if isinstance(p, dict) else p
                if pid not in plot_scene_sets:
                    plot_scene_sets[pid] = set()
                plot_scene_sets[pid].add(scene["id"])
        plot_coverage = []
        for pid, scene_set in sorted(plot_scene_sets.items(), key=lambda x: len(x[1]), reverse=True):
            pl = plot_lookup.get(pid, {})
            plot_coverage.append({
                "id": pid,
                "name": pl.get("name", pid),
                "plot_scope": pl.get("plot_scope", ""),
                "plot_type": pl.get("plot_type", ""),
                "value_arc": pl.get("value_arc", ""),
                "sceneCount": len(scene_set),
                "coveragePct": round((len(scene_set) / len(scenes)) * 100) if scenes else 0,
            })

        structural_stats = {
            "sceneCount": scene_count,
            "sequenceCount": seq_count,
            "actCount": act_count,
            "sceneStatus": scene_status,
            "sceneRoles": scene_roles,
            "plotCoverage": plot_coverage,
            "acts": acts_stats,
        }

        # 5. title_page — project frontmatter
        proj_row = conn.execute(
            "SELECT name, one_sentence, extra FROM entities WHERE type='project'"
        ).fetchone()
        title_page_data = {}
        if proj_row:
            name, one_sentence, extra_json = proj_row
            extra = json.loads(extra_json) if extra_json else {}
            title_page_data = {
                "name": name,
                "logline": one_sentence,
                "screenplay_title": extra.get("screenplay_title", ""),
                "credit": extra.get("credit", ""),
                "author": extra.get("author", ""),
                "contact": extra.get("contact", ""),
                "draft_date": extra.get("draft_date", ""),
                "draft": extra.get("draft", ""),
            }

        return {
            "story_data": story_data,
            "sections": sections,
            "screenplay_text": screenplay_text,
            "structural_stats": structural_stats,
            "title_page": title_page_data,
        }
    finally:
        conn.close()


def get_screenplay_text(project_path: Path) -> str:
    """Concatenate scene ## Content sections from DB, ordered by act→sequence→scene."""
    conn = get_db(project_path)
    try:
        rows = conn.execute(
            """SELECT s.body FROM sections s
               JOIN entities e ON s.entity_id = e.id
               LEFT JOIN entities p ON e.parent_id = p.id
               LEFT JOIN entities pp ON p.parent_id = pp.id
               WHERE e.type='scene' AND s.heading='Content'
               ORDER BY COALESCE(pp.order_key, 0), COALESCE(p.order_key, 0), e.order_key"""
        ).fetchall()
        return "\n\n".join(r[0] for r in rows)
    finally:
        conn.close()
