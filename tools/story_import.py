"""story_import tool — reads markdown vault → populates story.db."""
import json
from pathlib import Path

SCHEMA = {
    "description": "DESTRUCTIVE. Rebuilds the database from the Markdown vault: deletes every row "
                   "and re-imports, discarding all work done since the last story_export. The "
                   "database is the source of truth, not Markdown. Only for an intentional re-sync "
                   "from Markdown files. Never use this to repair a problem — take a "
                   "story_backup first, and prefer story_edit or story_create to change things.",
    "type": "object",
    "properties": {
        "project": {"type": "string", "description": "Project slug or path"},
        "dry_run": {"type": "boolean",
                    "description": "Report what would be deleted and re-imported without "
                                   "changing anything. Use this first."},
        "confirm": {"type": "boolean",
                    "description": "Required to actually import when the database holds work that "
                                   "exists only in the database. Set after reading the dry_run report."},
    },
    "required": ["project"],
}


def _backup(project_path: Path) -> str:
    """Timestamped copy of story.db, so a destructive import is always recoverable.

    Delegates to core.db.backup_database — the WAL-safe, collision-free copy that
    story_backup also uses.
    """
    from core.db import backup_database
    return backup_database(project_path)


def _diff(project_path: Path) -> dict:
    """Which database entities have no Markdown note behind them.

    Those are the ones an import destroys. An entity created at runtime with
    story_create has no .md file — that is exactly the set the wipe deletes.

    Deliberately one-directional: an entity with a note file is never reported as
    at risk, even when the importer keys it differently (the project row uses the
    folder name, arc beats a `{char}-{beat}` composite). A missed warning only
    means the guard stays quiet; a false "you will lose data" would block every
    legitimate re-import.
    """
    from core.db import get_db

    conn = get_db(project_path)
    try:
        rows = conn.execute("SELECT id, type FROM entities").fetchall()
    finally:
        conn.close()

    markdown_ids = set()
    for folder in ("characters", "locations", "worlds", "plots", "scenes",
                   "sequences", "acts", "relationships"):
        d = project_path / folder
        if d.exists():
            markdown_ids |= {f.stem for f in d.glob("*.md") if not f.name.startswith("_")}

    # Arc beats live in arcs/{character}/{beat}.md and are keyed `{char}-{beat}`.
    # They do not appear in the flat folders above, and a database may hold them
    # typed as 'character', so match them by the note tree as well.
    arc_beat_ids = set()
    arcs = project_path / "arcs"
    if arcs.exists():
        for char_dir in arcs.iterdir():
            if char_dir.is_dir() and not char_dir.name.startswith(("_", ".")):
                arc_beat_ids |= {f"{char_dir.name}-{f.stem}" for f in char_dir.glob("*.md")}

    at_risk = sorted(
        entity_id for entity_id, entity_type in rows
        if entity_type not in ("project", "arc_beat")
        and entity_id not in markdown_ids
        and entity_id not in arc_beat_ids
    )
    return {"entities_in_db": len(rows), "would_be_destroyed": at_risk}


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

    from core.db import (
        get_db, create_schema, has_schema, get_project_memory,
        empty_memory, validate_memory,
    )

    db_file = project_path / ".story" / "story.db"

    # ── Safety gate ────────────────────────────────────────────────────────────
    # An import DELETEs every row and rebuilds from Markdown. The database is the
    # source of truth, so anything that exists only in the database is lost — the
    # character a user created five minutes ago, every story_edit since the last
    # export. This is the one tool that can silently destroy work, so it reports
    # first and refuses without explicit consent.
    if db_file.exists() and args.get("dry_run"):
        report = _diff(project_path)
        report["dry_run"] = True
        report["message"] = (
            f"Nothing was changed. An import would rebuild {project_path.name} from Markdown: "
            f"{report['entities_in_db']} entities are in the database. The database is the "
            f"source of truth, so anything without a Markdown note behind it would be lost."
        )
        if report["would_be_destroyed"]:
            report["warning"] = (
                f"{len(report['would_be_destroyed'])} entities exist ONLY in the database and "
                f"would be DESTROYED: {', '.join(report['would_be_destroyed'][:10])}"
                + ("..." if len(report["would_be_destroyed"]) > 10 else "")
            )
            report["next_step"] = (
                "Run story_export first to keep them, or story_backup to save a restorable copy. "
                "Then re-run with confirm=true to import anyway."
            )
        else:
            report["next_step"] = "Nothing would be lost. Re-run with confirm=true to import."
        return json.dumps(report)

    if db_file.exists() and not args.get("confirm"):
        report = _diff(project_path)
        if report["would_be_destroyed"]:
            backup = _backup(project_path)
            return json.dumps({
                "success": False,
                "error": f"Refusing to import: {len(report['would_be_destroyed'])} entities exist "
                         f"only in the database and would be destroyed.",
                "would_be_destroyed": report["would_be_destroyed"],
                "backup_created": backup,
                "action_required": "A backup was saved. Run story_export to keep these entities in "
                                   "Markdown, then re-run with confirm=true to import anyway.",
                "hint": "Run with dry_run=true first to see this report before doing anything.",
            })
        # Nothing would be lost — a clean re-sync. Allow it, but still back up.

    existing_memory = get_project_memory(project_path) if db_file.exists() else None
    memory_path = project_path / ".story" / "memory.md"
    imported_memory = None
    if memory_path.exists():
        import frontmatter
        try:
            memory_fm = dict(frontmatter.load(memory_path).metadata)
            imported_memory = validate_memory(memory_fm)
        except Exception as e:
            return json.dumps({"error": f"Invalid story memory: {e}"})
    conn = get_db(project_path)
    try:
        if not has_schema(conn):
            create_schema(conn)

        project_exists = conn.execute(
            "SELECT id, extra FROM entities WHERE type='project' LIMIT 1"
        ).fetchone()
        if not (project_path / "project.md").exists():
            if not project_exists:
                conn.close()
                return json.dumps({"error": "Project markdown not found and no project DB exists"})
            if imported_memory is not None:
                extra = json.loads(project_exists[1]) if project_exists[1] else {}
                extra["memory"] = imported_memory
                conn.execute(
                    "UPDATE entities SET extra=? WHERE id=?",
                    (json.dumps(extra, ensure_ascii=False), project_exists[0]),
                )
            conn.close()
            return json.dumps({"success": True, "message": f"Imported memory for {project_path.name}"})

        # Last line of defence: the wipe below is irreversible from here.
        backup_path = _backup(project_path)

        conn.execute("BEGIN")
        _clear_all(conn)
        _import_all(conn, project_path)
        if imported_memory is not None:
            row = conn.execute("SELECT id, extra FROM entities WHERE type='project' LIMIT 1").fetchone()
            if row:
                extra = json.loads(row[1]) if row[1] else {}
                extra["memory"] = imported_memory
                conn.execute("UPDATE entities SET extra=? WHERE id=?", (json.dumps(extra, ensure_ascii=False), row[0]))
        elif existing_memory is not None:
            row = conn.execute("SELECT id, extra FROM entities WHERE type='project' LIMIT 1").fetchone()
            if row:
                extra = json.loads(row[1]) if row[1] else {}
                extra["memory"] = existing_memory
                conn.execute("UPDATE entities SET extra=? WHERE id=?", (json.dumps(extra, ensure_ascii=False), row[0]))
        conn.execute("COMMIT")
    except Exception as e:
        conn.execute("ROLLBACK")
        conn.close()
        return json.dumps({"error": str(e)})

    conn.close()
    return json.dumps({
        "success": True,
        "message": f"Imported {project_path.name}",
        "backup_created": backup_path,
    })


def _clear_all(conn) -> None:
    """Clear all tables for re-import."""
    conn.execute("DELETE FROM relations")
    conn.execute("DELETE FROM sections")
    conn.execute("DELETE FROM entities")


def _import_all(conn, project_path: Path) -> None:
    """Walk all entity folders and import."""
    _import_project(conn, project_path)
    _import_folder(conn, project_path, "characters", "character")
    _import_folder(conn, project_path, "locations", "location")
    _import_folder(conn, project_path, "worlds", "world")
    _import_folder(conn, project_path, "plots", "plot")
    _import_folder(conn, project_path, "scenes", "scene")
    _import_folder(conn, project_path, "sequences", "sequence")
    _import_folder(conn, project_path, "acts", "act")
    _import_arcs(conn, project_path)
    _import_folder(conn, project_path, "relationships", "relationship")


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

    from core.db import empty_memory
    extra = {"memory": empty_memory()}
    skip = {"name", "logline", "memory"}
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
            _insert_entity(conn, "arc_beat", slug, fm, body, char_slug=char_slug)




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
    _insert_sections(conn, columns["id"], body, entity_type)


def _insert_sections(conn, entity_id: str, body: str, entity_type: str) -> None:
    """Insert all standard sections for entity type, empty body if missing from note."""
    from core.section_parser import list_sections, get_section
    from core.entity import standard_sections

    headings = list_sections(body)
    for h in headings:
        text = get_section(body, h)
        lines = text.split("\n", 1)
        body_text = lines[1].strip() if len(lines) > 1 else ""
        conn.execute(
            "INSERT INTO sections (entity_id, heading, body) VALUES (?, ?, ?)",
            (entity_id, h, body_text),
        )
    # Ensure all standard sections exist (e.g. scene Content is a structural invariant)
    for section in standard_sections(entity_type):
        if section not in headings:
            conn.execute(
                "INSERT INTO sections (entity_id, heading, body) VALUES (?, ?, ?)",
                (entity_id, section, ""),
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
            "order_key": 0, "status": "", "parent_id": fm.get("world"), "location_id": None,
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
    elif entity_type == "arc_beat":
        return {
            "id": slug, "type": "arc_beat",
            "name": fm.get("label", ""), "one_sentence": "",
            "order_key": fm.get("order", 0), "status": "",
            "parent_id": char_slug, "location_id": None,
            "extra": _extra_for("arc_beat", fm),
        }
    elif entity_type == "relationship":
        return {
            "id": slug, "type": "relationship",
            "name": fm.get("name", ""), "one_sentence": "",
            "order_key": 0, "status": fm.get("status", ""),
            "parent_id": None, "location_id": None,
            "extra": _extra_for("relationship", fm),
        }
    return {"id": slug, "type": entity_type, "name": "", "one_sentence": "",
            "order_key": 0, "status": "", "parent_id": None, "location_id": None, "extra": {}}


def _extra_for(entity_type: str, fm: dict) -> dict:
    """Extract extra JSON fields for an entity type."""
    # Fields that go to columns or relations (not extra)
    skip = {
        "character": {"name", "one_sentence", "id"},
        "location": {"name", "one_sentence", "id", "world", "variant_of"},
        "world": {"name", "one_sentence", "id", "variant_of"},
        "plot": {"name", "one_sentence", "status", "id", "setups", "payoffs", "crisis", "climax"},
        "scene": {"title", "order", "status", "sequence_id", "location", "id", "characters"},
        "sequence": {"title", "order", "status", "act_id", "id"},
        "act": {"title", "order", "status", "id"},
        "arc_beat": {"id", "label", "order", "character"},
        "relationship": {"name", "status", "id"},
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
    elif entity_type == "location":
        target = fm.get("variant_of")
        if target:
            conn.execute(
                "INSERT OR IGNORE INTO relations (from_id, to_id, kind) VALUES (?, ?, ?)",
                (slug, target, "location_variant"),
            )
    elif entity_type == "world":
        target = fm.get("variant_of")
        if target:
            conn.execute(
                "INSERT OR IGNORE INTO relations (from_id, to_id, kind) VALUES (?, ?, ?)",
                (slug, target, "world_variant"),
            )



