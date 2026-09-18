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
    is_deleted INTEGER NOT NULL DEFAULT 0,
    deleted_at TEXT,
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
    """Open a short-lived connection with WAL mode and busy_timeout."""
    db_path = project_path / ".story" / "story.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
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
            "FROM entities WHERE is_deleted=0 ORDER BY type, id"
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
        # 1. story_data — column-oriented entities (active only)
        ent_rows = conn.execute(
            "SELECT id, type, name, one_sentence, order_key, status, parent_id, location_id "
            "FROM entities WHERE is_deleted=0 ORDER BY type, id"
        ).fetchall()
        story_data = [
            {
                "id": r[0], "type": r[1], "name": r[2], "one_sentence": r[3],
                "order": r[4], "status": r[5], "parent_id": r[6], "location_id": r[7],
            }
            for r in ent_rows
        ]

        # 2. sections — {entity_id: {heading: body}}
        sec_rows = conn.execute(
            "SELECT entity_id, heading, body FROM sections ORDER BY entity_id, rowid"
        ).fetchall()
        sections = {}
        for entity_id, heading, body in sec_rows:
            if entity_id not in sections:
                sections[entity_id] = {}
            sections[entity_id][heading] = body

        # 3. screenplay_text — scene ## Content concatenated in order
        scene_content_rows = conn.execute(
            """SELECT s.body, e.order_key, p.order_key as parent_order
               FROM sections s
               JOIN entities e ON s.entity_id = e.id
               LEFT JOIN entities p ON e.parent_id = p.id
               WHERE e.type='scene' AND s.heading='Content' AND e.is_deleted=0
               ORDER BY COALESCE(p.order_key, 0), e.order_key"""
        ).fetchall()
        screenplay_text = "\n\n".join(r[0] for r in scene_content_rows)

        # 4. structural_stats
        status_rows = conn.execute(
            "SELECT status, COUNT(*) FROM entities WHERE type='scene' AND is_deleted=0 GROUP BY status"
        ).fetchall()
        scene_status = dict(status_rows)

        role_rows = conn.execute(
            "SELECT json_extract(extra, '$.dramatic_role'), COUNT(*) "
            "FROM entities WHERE type='scene' AND is_deleted=0 "
            "GROUP BY json_extract(extra, '$.dramatic_role')"
        ).fetchall()
        scene_roles = {r[0] or "unset": r[1] for r in role_rows}

        seq_count = conn.execute(
            "SELECT COUNT(*) FROM entities WHERE type='sequence' AND is_deleted=0"
        ).fetchone()[0]
        act_count = conn.execute(
            "SELECT COUNT(*) FROM entities WHERE type='act' AND is_deleted=0"
        ).fetchone()[0]
        scene_count = sum(scene_status.values())

        # Act stats — count scenes/sequences per act
        act_rows = conn.execute(
            "SELECT id, name, order_key FROM entities WHERE type='act' AND is_deleted=0 ORDER BY order_key"
        ).fetchall()
        acts_stats = []
        for act_id, act_name, act_order in act_rows:
            seq_c = conn.execute(
                "SELECT COUNT(*) FROM entities WHERE type='sequence' AND parent_id=? AND is_deleted=0",
                (act_id,)
            ).fetchone()[0]
            scene_c = conn.execute(
                """SELECT COUNT(*) FROM entities WHERE type='scene' AND is_deleted=0
                   AND parent_id IN (SELECT id FROM entities WHERE type='sequence' AND parent_id=? AND is_deleted=0)""",
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
               WHERE e.type='scene' AND s.heading='Content' AND e.is_deleted=0
               ORDER BY COALESCE(pp.order_key, 0), COALESCE(p.order_key, 0), e.order_key"""
        ).fetchall()
        return "\n\n".join(r[0] for r in rows)
    finally:
        conn.close()
