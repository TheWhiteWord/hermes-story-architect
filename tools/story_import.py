"""story_import tool — reads markdown vault → populates story.db."""
import json
from pathlib import Path

from core.entity import plot_role_relations

SCHEMA = {
    "description": "DESTRUCTIVE. Rebuilds the database from the Markdown vault: deletes every row "
                   "and re-imports, discarding all work done since the last story_export. The "
                   "database is the source of truth, not Markdown. Only for an intentional re-sync "
                   "from Markdown files. Never use this to repair a problem — take a "
                   "story_backup first, and prefer story_draft to change things.",
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

    Those are the ones an import destroys. An entity created at runtime
    has no .md file — that is exactly the set the wipe deletes.

    Deliberately one-directional: an entity with a note file is never reported as
    at risk, even when the importer keys it differently (the project row uses the
    folder name). A missed warning only means the guard stays quiet; a false
    "you will lose data" would block every legitimate re-import.
    """
    from core.db import get_db

    conn = get_db(project_path)
    try:
        rows = conn.execute("SELECT id, type FROM entities").fetchall()
    finally:
        conn.close()

    # The filename is the title, so the id is only in the frontmatter. This has
    # to read every note — the same pass the import already makes.
    import frontmatter

    def _ids_in(folder: Path) -> set:
        found = set()
        if not folder.exists():
            return found
        for f in folder.glob("*.md"):
            if f.name.startswith("_"):
                continue
            found.add(str(frontmatter.load(f).metadata.get("id") or f.stem))
        return found

    markdown_ids = set()
    for folder in ("characters", "locations", "worlds", "plots", "scenes",
                   "scene_beats", "sequences", "acts", "relationships"):
        markdown_ids |= _ids_in(project_path / folder)

    # Values live in one root file, not a folder, so they would otherwise be
    # reported as database-only and destroyed on every import. Parse their ids
    # from that file with the same block parser the import uses.
    values_file = project_path / "values.md"
    if values_file.exists():
        for fm, _ in _iter_value_blocks(values_file.read_text()):
            if fm.get("id"):
                markdown_ids.add(str(fm["id"]))

    at_risk = sorted(
        entity_id for entity_id, entity_type in rows
        if entity_type != "project"
        and entity_id not in markdown_ids
    )
    return {"entities_in_db": len(rows), "would_be_destroyed": at_risk}


def handler(args, **kwargs) -> str:
    """Import markdown vault into SQLite."""
    from .story_resolve import resolve_project
    from core.config import resolve_root

    root_path = resolve_root(kwargs)

    try:
        project_path = resolve_project(args["project"], root_path)
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
    # character a user created five minutes ago, every commit since the last
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
    # Values first: a scene's value turn names a value, and that value must
    # exist before the scene naming it is imported.
    _import_values(conn, project_path)
    _import_folder(conn, project_path, "characters", "character")
    _import_folder(conn, project_path, "locations", "location")
    _import_folder(conn, project_path, "worlds", "world")
    _import_folder(conn, project_path, "plots", "plot")
    _import_folder(conn, project_path, "scenes", "scene")
    # Immediately after the scenes: a record names its scene, so the scene must
    # exist before the record is inserted.
    _import_folder(conn, project_path, "scene_beats", "scene_beats")
    _import_folder(conn, project_path, "sequences", "sequence")
    _import_folder(conn, project_path, "acts", "act")
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


def _iter_value_blocks(text: str):
    """Yield `(frontmatter, body)` per value from the concatenated `values.md`.

    The one non-reused piece: `values.md` is a concatenation of per-value
    frontmatter blocks separated by `---`, not a single note, so `frontmatter`
    parses only the first block. Split on the fences and parse each block's
    YAML. An empty or absent file yields nothing — "no values", not an error.
    A trailing fence with no closing one ends the walk rather than yielding a
    half block.
    """
    import yaml
    lines = text.split("\n")
    i, n = 0, len(lines)
    while i < n:
        if lines[i].strip() != "---":
            i += 1
            continue
        j = i + 1
        fm_lines = []
        while j < n and lines[j].strip() != "---":
            fm_lines.append(lines[j])
            j += 1
        if j >= n:
            break  # an unterminated block; ignore it
        fm = yaml.safe_load("\n".join(fm_lines)) or {}
        k = j + 1
        body_lines = []
        while k < n and lines[k].strip() != "---":
            body_lines.append(lines[k])
            k += 1
        yield fm, "\n".join(body_lines).strip("\n")
        i = k


def _import_values(conn, project_path: Path) -> None:
    """Import every value from the single `values.md` at the project root."""
    values_file = project_path / "values.md"
    if not values_file.exists():
        return
    text = values_file.read_text()
    if not text.strip():
        return
    from core.writes import validate_value
    for fm, body in _iter_value_blocks(text):
        entity_id = str(fm.get("id") or "").strip()
        name = str(fm.get("name") or "").strip()
        if not entity_id or not name:
            raise ValueError(
                f"A value block in {values_file.name} is missing an id or name "
                f"(got id={entity_id!r}, name={name!r}). Every value needs both.")
        # Same checks the write path runs, so a hand-edited values.md is
        # refused exactly as story_draft would refuse it. validate_value opens
        # its own read connection, so it sees the values already inserted in
        # this pass — the name-uniqueness rule holds across the file.
        validate_value(project_path, entity_id, fm)
        _insert_entity(conn, "value", entity_id, fm, body)


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
        # The filename is the title, so the id comes from the frontmatter. The
        # stem is only the fallback, for a note written before ids were written
        # out — or by hand.
        entity_id = str(fm.get("id") or note.stem)
        _insert_entity(conn, entity_type, entity_id, fm, body)
        _insert_relations(conn, entity_type, entity_id, fm)





def _insert_entity(conn, entity_type: str, slug: str, fm: dict, body: str) -> None:
    """Insert entity row + sections + relations."""
    columns = _columns_for(entity_type, slug, fm)
    conn.execute(
        "INSERT INTO entities (id, type, name, one_sentence, order_key, status, parent_id, location_id, extra) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (columns["id"], columns["type"], columns["name"], columns["one_sentence"],
         columns["order_key"], columns["status"], columns["parent_id"],
         columns["location_id"], json.dumps(columns["extra"])),
    )
    _insert_sections(conn, columns["id"], body, entity_type)


def _insert_sections(conn, entity_id: str, body: str, entity_type: str) -> None:
    """Insert every standard section for the type, empty where the note is silent.

    A heading in the note that is not standard is refused, exactly as on the
    create and edit paths. It used to be inserted as written, which meant the
    same section name was valid or an error depending on which path carried
    it — and it is how a note written against an older vocabulary ended up
    holding prose under a name nothing would ever read back.
    """
    from core.section_parser import list_sections, get_section
    from core.entity import standard_sections

    headings = list_sections(body)
    standard = standard_sections(entity_type)
    unknown = [h for h in headings if h not in standard]
    if unknown:
        raise ValueError(
            f"{entity_id}: unrecognised {entity_type} section name(s): "
            f"{', '.join(sorted(unknown))}. The section set is closed — use one "
            f"of: {', '.join(standard)}.")

    for h in headings:
        text = get_section(body, h)
        lines = text.split("\n", 1)
        body_text = lines[1].strip() if len(lines) > 1 else ""
        conn.execute(
            "INSERT INTO sections (entity_id, heading, body) VALUES (?, ?, ?)",
            (entity_id, h, body_text),
        )
    # Ensure all standard sections exist (e.g. scene Content is a structural invariant)
    for section in standard:
        if section not in headings:
            conn.execute(
                "INSERT INTO sections (entity_id, heading, body) VALUES (?, ?, ?)",
                (entity_id, section, ""),
            )


def _columns_for(entity_type: str, slug: str, fm: dict) -> dict:
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
    elif entity_type == "scene_beats":
        return {
            "id": slug, "type": "scene_beats",
            "name": "", "one_sentence": "",
            "order_key": 0, "status": "",
            "parent_id": fm.get("scene"), "location_id": None,
            "extra": _extra_for("scene_beats", fm),
        }
    elif entity_type == "relationship":
        return {
            "id": slug, "type": "relationship",
            "name": fm.get("name", ""), "one_sentence": "",
            "order_key": 0, "status": fm.get("status", ""),
            "parent_id": None, "location_id": None,
            "extra": _extra_for("relationship", fm),
        }
    elif entity_type == "value":
        return {
            "id": slug, "type": "value",
            "name": fm.get("name", ""), "one_sentence": "",
            "order_key": 0, "status": "", "parent_id": None, "location_id": None,
            "extra": _extra_for("value", fm),
        }
    return {"id": slug, "type": entity_type, "name": "", "one_sentence": "",
            "order_key": 0, "status": "", "parent_id": None, "location_id": None, "extra": {}}


def _extra_for(entity_type: str, fm: dict) -> dict:
    """The entity's extra JSON, from the fields that are not columns or relations.

    A key that belongs to no field of this type is refused, as it is on the
    create and edit paths. It used to be kept verbatim, which is how a nested
    `goals: {short, long}` survived an import while every reader looked for
    the flat `goals_short` — the character showed its goals in the dashboard
    and as unfilled in story_retrieve at the same time.
    """
    from core.constants import ENTITY_SCHEMAS

    # The VALUE checks, which `_extra_for` was missing and the write paths both
    # have. A hand-edited note carrying a retired value used to import clean:
    # `dramatic_role: climax` was accepted after the enum narrowed to
    # plot_role/transition/non-event, stored, and read back as a value no
    # reader expects — the silent version of the unknown-key refusal below.
    #
    # Only the value checks, NOT the structural ones. `value_problems` is the
    # split, and it lives beside the checks so the two kinds cannot drift.
    from core.entity import value_problems
    problems = value_problems(entity_type, fm)
    if problems:
        raise ValueError(
            f"Invalid {entity_type} frontmatter in the note: "
            f"{'; '.join(problems)}. story_describe lists the valid fields "
            f"for this type.")

    # Fields that go to columns or relations (not extra)
    skip = {
        "character": {"name", "one_sentence", "id"},
        "location": {"name", "one_sentence", "id", "world", "variant_of"},
        "world": {"name", "one_sentence", "id", "variant_of"},
        "plot": {"name", "one_sentence", "status", "id"},
        # `plot_roles` is relation-stored, so it must not land in extra.
        "scene": {"title", "order", "status", "sequence_id", "location", "id", "characters",
                  "plot_roles"},
        "scene_beats": {"scene", "id"},
        "sequence": {"title", "order", "status", "act_id", "id"},
        "act": {"title", "order", "status", "id"},
        "relationship": {"name", "status", "id"},
        "value": {"name", "id"},
    }
    s = skip.get(entity_type, set())
    valid = set(s) | set(ENTITY_SCHEMAS.get(entity_type, {})) | {"id", "type"}
    unknown = [k for k in fm if k not in valid]
    if unknown:
        raise ValueError(
            f"Unrecognised {entity_type} field(s) in frontmatter: "
            f"{', '.join(sorted(unknown))}. story_describe lists the valid "
            f"fields for this type.")

    extra = {}
    for k, v in fm.items():
        # A computed field is derived at read time and has no row to write. It
        # is refused rather than kept: an old note carrying `plot.setups` would
        # otherwise import as a plot with a dead `setups` key in extra that no
        # reader looks at, and the roles it described would be silently gone.
        # The write paths already refuse these (drafts, create, edit).
        if ENTITY_SCHEMAS.get(entity_type, {}).get(k, {}).get("computed"):
            raise ValueError(
                f"Unrecognised {entity_type} field(s) in frontmatter: {k}. "
                f"It is read-only (computed) — set it on the scene as "
                f"plot_roles, or on the relationship that derives it.")
        if k not in s and v not in (None, "", [], {}):
            extra[k] = v
    # The one cross-field rule a scene has. The importer is a write path like
    # any other, so it enforces the same invariant — otherwise a hand-edited
    # note could import a contradiction the write tools would have refused.
    if entity_type == "scene":
        from core.entity import validate_scene_dramatic_role
        validate_scene_dramatic_role(extra.get("dramatic_role", ""),
                                     fm.get("plot_roles", []))
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
        # A plot role is written on the scene. The rows are the plot's to own
        # (from_id=plot), which is the direction every reader expects.
        for row in plot_role_relations(slug, fm.get("plot_roles")):
            conn.execute(
                "INSERT OR IGNORE INTO relations (from_id, to_id, kind, note, \"order\") "
                "VALUES (?, ?, ?, ?, ?)",
                (row["from_id"], row["to_id"], row["kind"], row["note"], row["order"]),
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



