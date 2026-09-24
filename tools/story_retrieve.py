"""story_retrieve tool — get specific sections from project notes."""
import json
from pathlib import Path

SCHEMA = {
    "type": "object",
    "properties": {
        "project": {
            "type": "string",
            "description": "Project slug or name"
        },
        "entity_type": {
            "type": "string",
            "enum": ["character", "location", "world", "plot", "project", "scene", "sequence", "act", "arc_beat", "relationship"],
            "description": "Type of entity"
        },
        "slug": {
            "type": "string",
            "description": "Entity slug"
        },
        "sections": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Section names to retrieve. Use ['all'] for all sections."
        }
    },
    "required": ["project", "entity_type", "slug", "sections"]
}


def handler(args: dict, **kwargs) -> str:
    """Retrieve specific sections from a story note."""
    from core.config import load_plugin_config
    from .story_resolve import resolve_project

    config = load_plugin_config()
    vault_path = Path(config.get("vault_path", "~/story-vault")).expanduser()
    project = args["project"]
    entity_type = args["entity_type"]
    slug = args["slug"]
    sections = args["sections"]

    # Resolve project path
    try:
        project_path = resolve_project(project, vault_path)
    except ValueError as e:
        return json.dumps({"error": str(e)})

    # Phase 2: Try DB first
    db_path = project_path / ".story" / "story.db"
    if db_path.exists():
        from core.db import has_schema, get_entity_sections
        import sqlite3
        conn = None
        try:
            conn = sqlite3.connect(str(db_path))
            if has_schema(conn):
                entity_id = _entity_id_for(conn, entity_type, slug)
                if entity_id:
                    db_sections = get_entity_sections(project_path, entity_id)
                    if db_sections:
                        unfilled = _unfilled_for_entity(conn, entity_id)
                        conn.close()
                        return _format_sections(entity_type, slug, sections, db_sections, project_path, unfilled)
        except Exception:
            pass
        finally:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass

    # No DB or no schema — error
    return json.dumps({"error": "Database not found. Run story_import first."})


def _unfilled_for_entity(conn, entity_id: str) -> list[str]:
    """Return unfilled fields for an entity from its extra JSON."""
    from core.entity import unfilled_fields
    row = conn.execute(
        "SELECT type, extra FROM entities WHERE id=?", (entity_id,)
    ).fetchone()
    if not row:
        return []
    etype, extra_json = row
    extra = json.loads(extra_json) if extra_json else {}
    if etype == "plot":
        # Plot beats live in relations, not extra — merge for unfilled check
        for kind, field in (("plot_setup", "setups"), ("plot_crisis", "crisis"),
                            ("plot_climax", "climax"), ("plot_payoff", "payoffs")):
            ids = [to_id for (to_id,) in conn.execute(
                "SELECT to_id FROM relations WHERE from_id=? AND kind=?", (entity_id, kind)
            ).fetchall()]
            if ids:
                extra = {**extra, field: ids}
    return unfilled_fields(etype, extra)


def _entity_id_for(conn, entity_type: str, slug: str) -> str | None:
    """Map entity_type + slug to DB entity id."""
    if entity_type == "arc_beat":
        # arc PK is "{char_slug}-{beat_id}"
        # Try direct match first
        row = conn.execute(
            "SELECT id FROM entities WHERE type='arc_beat' AND id=?", (slug,)
        ).fetchone()
        if row:
            return row[0]
        # Try pattern match for {char}-{beat} — slug is the beat_id, entity_id is {char_slug}-{beat_id}
        row = conn.execute(
            "SELECT id FROM entities WHERE type='arc_beat' AND id LIKE ?", (f"%-{slug}",)
        ).fetchone()
        return row[0] if row else None
    else:
        row = conn.execute(
            "SELECT id FROM entities WHERE type=? AND id=?", (entity_type, slug)
        ).fetchone()
        return row[0] if row else None


def _format_sections(entity_type: str, slug: str, sections: list, db_sections: dict, project_path: Path, unfilled: list | None = None) -> str:
    """Format DB sections to match the old file-based response."""
    from core.section_parser import list_sections

    if sections == ["all"]:
        # All sections: return headings + content
        all_content = "\n\n".join(
            f"## {heading}\n{body}" for heading, body in db_sections.items()
        )
        result = {
            "entity_type": entity_type,
            "slug": slug,
            "sections": list(db_sections.keys()),
            "content": all_content
        }
        if unfilled is not None:
            result["unfilled_fields"] = unfilled
        return json.dumps(result)

    results = {}
    for section in sections:
        if section in db_sections:
            results[section] = f"## {section}\n{db_sections[section]}"
        else:
            available = list(db_sections.keys())
            results[section] = f"Section '{section}' not found. Available: {available}"

    result = {
        "entity_type": entity_type,
        "slug": slug,
        "sections": results
    }
    if unfilled is not None:
        result["unfilled_fields"] = unfilled
    return json.dumps(result)
