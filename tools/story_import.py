"""story_import tool — reads markdown vault → populates story.db."""
import json
from pathlib import Path

SCHEMA = {
    "type": "object",
    "properties": {
        "project": {"type": "string", "description": "Project slug or path"},
    },
    "required": ["project"],
}


def handler(args, **kwargs) -> str:
    """Import markdown vault into SQLite."""
    from .story_resolve import resolve_project
    from core.config import load_plugin_config

    vault = kwargs.get("vault_path")
    if vault:
        vault_path = Path(vault)
    else:
        config = load_plugin_config()
        vault_path = Path(config.get("vault_path", "~/story-vault")).expanduser()

    try:
        project_path = resolve_project(args["project"], vault_path)
    except ValueError as e:
        return json.dumps({"error": str(e)})

    from core.db import get_db, create_schema, has_schema
    from core.section_parser import list_sections, get_section

    conn = get_db(project_path)
    try:
        if not has_schema(conn):
            create_schema(conn)

        conn.execute("BEGIN")
        _clear_all(conn)
        _import_all(conn, project_path)
        conn.execute("COMMIT")
    except Exception as e:
        conn.execute("ROLLBACK")
        conn.close()
        return json.dumps({"error": str(e)})

    conn.close()
    return json.dumps({"success": True, "message": f"Imported {project_path.name}"})


def _clear_all(conn) -> None:
    """Clear all tables for re-import."""
    conn.execute("DELETE FROM relations")
    conn.execute("DELETE FROM sections")
    conn.execute("DELETE FROM entities")


def _import_all(conn, project_path: Path) -> None:
    """Walk all entity folders and import."""
    import frontmatter

    _import_project(conn, project_path)
    _import_folder(conn, project_path, "characters", "character")
    _import_folder(conn, project_path, "locations", "location")
    _import_folder(conn, project_path, "worlds", "world")
    _import_folder(conn, project_path, "plots", "plot")
    _import_folder(conn, project_path, "scenes", "scene")
    _import_folder(conn, project_path, "sequences", "sequence")
    _import_folder(conn, project_path, "acts", "act")
    _import_arcs(conn, project_path)


def _import_project(conn, project_path: Path) -> None:
    """Import project.md."""
    import frontmatter
    from core.section_parser import list_sections, get_section

    fm_file = project_path / "project.md"
    if not fm_file.exists():
        return
    post = frontmatter.load(fm_file)
    fm = dict(post.metadata)
    body = post.content

    extra = {}
    skip = {"name", "logline"}
    for k, v in fm.items():
        if k not in skip:
            extra[k] = v

    conn.execute(
        "INSERT INTO entities (id, type, name, one_sentence, extra) VALUES (?, ?, ?, ?, ?)",
        (project_path.name, "project", fm.get("name", ""), fm.get("logline", ""), json.dumps(extra)),
    )

    headings = list_sections(body)
    for h in headings:
        text = get_section(body, h)
        lines = text.split("\n", 1)
        body_text = lines[1].strip() if len(lines) > 1 else ""
        conn.execute(
            "INSERT INTO sections (entity_id, heading, body) VALUES (?, ?, ?)",
            (project_path.name, h, body_text),
        )


def _import_folder(conn, project_path: Path, folder_name: str, entity_type: str) -> None:
    """Import all entities from a flat folder."""
    import frontmatter
    from core.section_parser import list_sections, get_section

    folder = project_path / folder_name
    if not folder.exists():
        return

    for note in sorted(folder.glob("*.md")):
        if note.name.startswith("_"):
            continue
        post = frontmatter.load(note)
        fm = dict(post.metadata)
        body = post.content
        slug = note.stem
        _insert_entity(conn, entity_type, slug, fm, body)
        _insert_relations(conn, entity_type, slug, fm)


def _import_arcs(conn, project_path: Path) -> None:
    """Import arc beats from nested arcs/{character}/{beat}.md structure."""
    import frontmatter
    from core.section_parser import list_sections, get_section

    arcs_folder = project_path / "arcs"
    if not arcs_folder.exists():
        return

    for char_folder in sorted(arcs_folder.iterdir()):
        if not char_folder.is_dir() or char_folder.name.startswith("_") or char_folder.name.startswith("."):
            continue
        for note in sorted(char_folder.glob("*.md")):
            if note.name.startswith("_"):
                continue
            post = frontmatter.load(note)
            fm = dict(post.metadata)
            body = post.content
            char_slug = char_folder.name
            beat_id = fm.get("id", note.stem)
            slug = f"{char_slug}-{beat_id}"
            _insert_entity(conn, "arc", slug, fm, body, char_slug=char_slug)




def _insert_entity(conn, entity_type: str, slug: str, fm: dict, body: str,
                   char_slug: str = None) -> None:
    """Insert entity row + sections + relations."""
    columns = _columns_for(entity_type, slug, fm, char_slug)
    conn.execute(
        "INSERT INTO entities (id, type, name, one_sentence, order_key, status, parent_id, location_id, extra) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (columns["id"], columns["type"], columns["name"], columns["one_sentence"],
         columns["order_key"], columns["status"], columns["parent_id"],
         columns["location_id"], json.dumps(columns["extra"])),
    )
    _insert_sections(conn, columns["id"], body)


def _insert_sections(conn, entity_id: str, body: str) -> None:
    """Parse and insert body sections."""
    from core.section_parser import list_sections, get_section

    headings = list_sections(body)
    for h in headings:
        text = get_section(body, h)
        lines = text.split("\n", 1)
        body_text = lines[1].strip() if len(lines) > 1 else ""
        conn.execute(
            "INSERT INTO sections (entity_id, heading, body) VALUES (?, ?, ?)",
            (entity_id, h, body_text),
        )


def _columns_for(entity_type: str, slug: str, fm: dict, char_slug: str = None) -> dict:
    """Map frontmatter fields to entity columns."""
    if entity_type == "character":
        return {
            "id": slug, "type": "character",
            "name": fm.get("name", ""), "one_sentence": fm.get("one_sentence", ""),
            "order_key": 0, "status": "", "parent_id": None, "location_id": None,
            "extra": _extra_for("character", fm),
        }
    elif entity_type == "location":
        return {
            "id": slug, "type": "location",
            "name": fm.get("name", ""), "one_sentence": fm.get("one_sentence", ""),
            "order_key": 0, "status": "", "parent_id": None, "location_id": None,
            "extra": _extra_for("location", fm),
        }
    elif entity_type == "world":
        return {
            "id": slug, "type": "world",
            "name": fm.get("name", ""), "one_sentence": fm.get("one_sentence", ""),
            "order_key": 0, "status": "", "parent_id": None, "location_id": None,
            "extra": _extra_for("world", fm),
        }
    elif entity_type == "plot":
        return {
            "id": slug, "type": "plot",
            "name": fm.get("name", ""), "one_sentence": fm.get("one_sentence", ""),
            "order_key": 0, "status": fm.get("status", "active"), "parent_id": None, "location_id": None,
            "extra": _extra_for("plot", fm),
        }
    elif entity_type == "scene":
        return {
            "id": slug, "type": "scene",
            "name": fm.get("title", ""), "one_sentence": "",
            "order_key": fm.get("order", 0), "status": fm.get("status", "planned"),
            "parent_id": fm.get("sequence_id"), "location_id": fm.get("location"),
            "extra": _extra_for("scene", fm),
        }
    elif entity_type == "sequence":
        return {
            "id": slug, "type": "sequence",
            "name": fm.get("title", ""), "one_sentence": "",
            "order_key": fm.get("order", 0), "status": fm.get("status", "planned"),
            "parent_id": fm.get("act_id"), "location_id": None,
            "extra": _extra_for("sequence", fm),
        }
    elif entity_type == "act":
        return {
            "id": slug, "type": "act",
            "name": fm.get("title", ""), "one_sentence": "",
            "order_key": fm.get("order", 0), "status": fm.get("status", "planned"),
            "parent_id": None, "location_id": None,
            "extra": _extra_for("act", fm),
        }
    elif entity_type == "arc":
        return {
            "id": slug, "type": "arc",
            "name": fm.get("label", ""), "one_sentence": "",
            "order_key": fm.get("order", 0), "status": "",
            "parent_id": char_slug, "location_id": None,
            "extra": _extra_for("arc", fm),
        }
    return {"id": slug, "type": entity_type, "name": "", "one_sentence": "",
            "order_key": 0, "status": "", "parent_id": None, "location_id": None, "extra": {}}


def _extra_for(entity_type: str, fm: dict) -> dict:
    """Extract extra JSON fields for an entity type."""
    # Fields that go to columns or relations (not extra)
    skip = {
        "character": {"name", "one_sentence", "id", "relationships"},
        "location": {"name", "one_sentence", "id"},
        "world": {"name", "one_sentence", "id"},
        "plot": {"name", "one_sentence", "status", "id", "setups", "payoffs", "crisis", "climax"},
        "scene": {"title", "order", "status", "sequence_id", "location", "id", "characters"},
        "sequence": {"title", "order", "status", "act_id", "id"},
        "act": {"title", "order", "status", "id"},
        "arc": {"id", "label", "order", "character"},
    }
    s = skip.get(entity_type, set())
    extra = {}
    for k, v in fm.items():
        if k not in s and v not in (None, "", [], {}):
            extra[k] = v
    return extra


def _insert_relations(conn, entity_type: str, slug: str, fm: dict) -> None:
    """Insert relations for an entity."""
    if entity_type == "scene":
        for char_id in fm.get("characters", []):
            conn.execute(
                "INSERT OR IGNORE INTO relations (from_id, to_id, kind) VALUES (?, ?, ?)",
                (char_id, slug, "character_scene"),
            )
        loc_id = fm.get("location")
        if loc_id:
            conn.execute(
                "INSERT OR IGNORE INTO relations (from_id, to_id, kind) VALUES (?, ?, ?)",
                (loc_id, slug, "location_scene"),
            )
    elif entity_type == "plot":
        # All 4 plot beat types — setups, crisis, climax, payoffs
        for field, kind in (("setups", "plot_setup"), ("crisis", "plot_crisis"), ("climax", "plot_climax"), ("payoffs", "plot_payoff")):
            for beat in fm.get(field, []):
                sid = beat.get("scene_id", "") if isinstance(beat, dict) else beat
                desc = beat.get("description", "") if isinstance(beat, dict) else ""
                if sid:
                    conn.execute(
                        "INSERT OR IGNORE INTO relations (from_id, to_id, kind, note) VALUES (?, ?, ?, ?)",
                        (slug, sid, kind, desc),
                    )
    elif entity_type == "character":
        # Structured relationships from frontmatter
        for rel in fm.get("relationships", []):
            if isinstance(rel, dict):
                target = rel.get("id", "")
                if target:
                    note = json.dumps({
                        "label": rel.get("label", ""),
                        "feeling": rel.get("feeling", ""),
                    })
                    conn.execute(
                        "INSERT OR IGNORE INTO relations (from_id, to_id, kind, note) VALUES (?, ?, ?, ?)",
                        (slug, target, "character_relationship", note),
                    )



