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


def get_project_summary(project_path: Path) -> dict:
    """Return column-oriented project summary for story_load.

    Shape: {project: {...}, entities: {cols, rows}, relations: {cols, rows}}
    Relations exclude the `note` field to save tokens.
    """
    conn = get_db(project_path)
    try:
        # Project metadata
        row = conn.execute(
            "SELECT id, name, one_sentence, extra FROM entities WHERE type='project'"
        ).fetchone()
        if row:
            proj_id, proj_name, proj_one_sentence, proj_extra_json = row
            proj_extra = json.loads(proj_extra_json) if proj_extra_json else {}
            project = {"name": proj_name, "logline": proj_one_sentence}
            project.update(proj_extra)
        else:
            project = {"name": "Unknown", "logline": ""}

        # Entities table (flat, no derived arrays)
        ent_cols = ["id", "type", "name", "one_sentence", "status", "order_key", "parent_id", "location_id", "extra"]
        ent_rows = conn.execute(
            "SELECT id, type, name, one_sentence, status, order_key, parent_id, location_id, extra "
            "FROM entities ORDER BY type, id"
        ).fetchall()
        entities = {
            "cols": ent_cols,
            "rows": [
                list(r[:8]) + [json.loads(r[8]) if r[8] else {}]
                for r in ent_rows
            ],
        }

        # Relations table (no note field)
        rel_cols = ["from_id", "to_id", "kind"]
        rel_rows = conn.execute(
            "SELECT from_id, to_id, kind FROM relations ORDER BY kind, from_id, to_id"
        ).fetchall()
        relations = {
            "cols": rel_cols,
            "rows": [list(r) for r in rel_rows],
        }

        # Unfilled fields per entity
        from .entity import unfilled_fields
        unfilled_map = {}
        for row in entities["rows"]:
            unfilled_map[row[0]] = unfilled_fields(row[1], row[8])

        return {"project": project, "entities": entities, "relations": relations, "unfilled": unfilled_map}
    finally:
        conn.close()


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

        # Build entity lookup for cross-references
        entity_by_id = {}
        for r in ent_rows:
            entity_by_id[r[0]] = {
                "id": r[0], "type": r[1], "name": r[2], "one_sentence": r[3],
                "order": r[4], "status": r[5], "parent_id": r[6], "location_id": r[7],
                "extra": json.loads(r[8]) if r[8] else {},
            }

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

        for e in ent_rows:
            etype = e[1]
            eid = e[0]
            extra = json.loads(e[8]) if e[8] else {}

            if etype == "character":
                d = _entity_dict({
                    "id": eid, "name": e[2], "one_sentence": e[3], "order": e[4],
                    "status": e[5], "parent_id": e[6], "extra": extra,
                })
                # scenes: string[] of scene IDs (from character_scene relations)
                d["scenes"] = rel_map.get(eid, {}).get("character_scene", [])
                # relationships: denormalized from character_relationship
                rels = []
                for rel in rel_map.get(eid, {}).get("character_relationship", []):
                    target_id = rel.get("to_id", "") if isinstance(rel, dict) else rel
                    if target_id in entity_by_id:
                        t = entity_by_id[target_id]
                        rels.append({
                            "id": t["id"],
                            "label": t["name"],
                            "feeling": rel.get("note", "") if isinstance(rel, dict) else "",
                        })
                d["relationships"] = rels
                characters.append(d)

            elif etype == "scene":
                d = _entity_dict({
                    "id": eid, "name": e[2], "one_sentence": e[3], "order": e[4],
                    "status": e[5], "parent_id": e[6], "extra": extra,
                })
                # characters from character_scene relations (reverse lookup)
                char_ids = []
                for cid, kinds in rel_map.items():
                    if "character_scene" in kinds:
                        for rel in kinds["character_scene"]:
                            if isinstance(rel, dict):
                                if rel.get("to_id") == eid:
                                    char_ids.append(cid)
                            elif rel == eid:
                                char_ids.append(cid)
                d["characters"] = char_ids
                # locations from location_scene relations (reverse lookup)
                loc_ids = []
                for lid, kinds in rel_map.items():
                    if "location_scene" in kinds:
                        for rel in kinds["location_scene"]:
                            if isinstance(rel, dict):
                                if rel.get("to_id") == eid:
                                    loc_ids.append(lid)
                            elif rel == eid:
                                loc_ids.append(lid)
                d["locations"] = loc_ids
                # plots from plot_setup/plot_payoff relations (reverse lookup)
                plot_ids = []
                for pid, kinds in rel_map.items():
                    for kind in ("plot_setup", "plot_payoff"):
                        if kind in kinds:
                            for rel in kinds[kind]:
                                if isinstance(rel, dict):
                                    if rel.get("to_id") == eid:
                                        plot_ids.append(pid)
                                elif rel == eid:
                                    plot_ids.append(pid)
                d["plots"] = plot_ids
                scenes.append(d)

            elif etype == "location":
                d = _entity_dict({
                    "id": eid, "name": e[2], "one_sentence": e[3], "order": e[4],
                    "status": e[5], "parent_id": e[6], "extra": extra,
                })
                # scenes from location_scene relations
                scene_ids = []
                for sid, kinds in rel_map.items():
                    if "location_scene" in kinds and eid in kinds["location_scene"]:
                        scene_ids.append(sid)
                d["scenes"] = scene_ids
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
                worlds.append(d)

            elif etype == "act":
                d = _entity_dict({
                    "id": eid, "name": e[2], "one_sentence": e[3], "order": e[4],
                    "status": e[5], "parent_id": e[6], "extra": extra,
                })
                acts.append(d)

            elif etype == "sequence":
                d = _entity_dict({
                    "id": eid, "name": e[2], "one_sentence": e[3], "order": e[4],
                    "status": e[5], "parent_id": e[6], "extra": extra,
                })
                sequences.append(d)

            elif etype == "arc":
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
                    c["arc_beats_list"].append(a)
                    break

        # Sort each character's beats by order, set arc_beat_count
        for c in characters:
            if "arc_beats_list" in c:
                c["arc_beats_list"].sort(key=lambda b: b.get("order", 0))
                c["arc_beat_count"] = len(c["arc_beats_list"])

        # Rename arcs to story.arcs for dashboard compatibility
        story_arcs = arcs

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

        structural_stats = {
            "sceneCount": scene_count,
            "sequenceCount": seq_count,
            "actCount": act_count,
            "sceneStatus": scene_status,
            "sceneRoles": scene_roles,
            "plotCoverage": [],
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
