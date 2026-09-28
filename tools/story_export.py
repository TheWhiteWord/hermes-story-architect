"""story_export tool — reads story.db → writes markdown vault."""
import json
import re
from pathlib import Path

from core.constants import ENTITY_SCHEMAS

SCHEMA = {
    "description": "Write the whole database back out to Markdown files. Use to publish the "
                   "project as readable notes, or to snapshot it before a story_import. Note this "
                   "does not create a restorable database copy — use story_backup for that.",
    "type": "object",
    "properties": {
        "project": {"type": "string", "description": "Project slug or path"}
    },
    "required": ["project"],
}


def handler(args, **kwargs) -> str:
    """Export SQLite to markdown vault."""
    from .story_resolve import resolve_project
    from core.config import resolve_root

    root_path = resolve_root(kwargs)

    try:
        project_path = resolve_project(args["project"], root_path)
    except ValueError as e:
        return json.dumps({"error": str(e)})

    from core.db import get_db

    conn = get_db(project_path)
    try:
        written = _export_all(conn, project_path)
        removed = _sweep_stale(project_path, written)
    except Exception as e:
        conn.close()
        return json.dumps({"error": str(e)})

    conn.close()
    return json.dumps({
        "success": True,
        "message": f"Exported {project_path.name}",
        "files_written": len(written),
        "files_removed": removed,
    })


# Where notes live, by entity type. Used by the sweep to know what it may touch.
_FOLDERS = {
    "character": "characters",
    "location": "locations",
    "world": "worlds",
    "plot": "plots",
    "scene": "scenes",
    "sequence": "sequences",
    "act": "acts",
    "relationship": "relationships",
}


def _filename(title: str, folder: Path, used: set) -> str:
    """A readable, unique `.md` stem for one entity, for a folder being written.

    Titles are what a person reads, so the filename is the title — with the
    characters a filesystem cannot take removed. Two entities can share a title
    ("The Choice" is one beat per character in `save-the-children`), and they
    land in different folders, but nothing stops one folder holding two, so a
    counter settles it: `The Choice.md`, then `The Choice 2.md`.

    Nothing references a filename, so a collision is cosmetic — an id collision
    would be silent, and `id` is the primary key for that reason. A title that
    sanitises to nothing falls back to the entity's id, which is never empty.
    """
    stem = "".join(c for c in (title or "") if c.isalnum() or c in " -_").strip()
    stem = re.sub(r"\s+", " ", stem).strip(" .")
    candidate = stem or "untitled"
    n = 2
    while f"{candidate}.md" in used:
        candidate = f"{stem} {n}"
        n += 1
    used.add(f"{candidate}.md")
    return candidate


def _sweep_stale(project_path: Path, written: set) -> list:
    """Delete notes a previous export wrote that the database no longer has.

    Export only ever writes, so without this a deleted entity leaves its .md
    behind and the next story_import resurrects it. A delete has to survive a
    round trip.

    Only files in the manifest — the paths the last export wrote — are eligible.
    A hand-authored note the database has never seen is never touched, and a
    project exported for the first time sweeps nothing.
    """
    manifest_path = project_path / ".story" / "exported.json"
    previous = set()
    if manifest_path.exists():
        try:
            previous = set(json.loads(manifest_path.read_text()))
        except (json.JSONDecodeError, TypeError):
            previous = set()

    # The manifest holds project-relative paths; `written` holds absolute ones.
    now = {str(p.relative_to(project_path)) for p in written}
    removed = []
    for rel in sorted(previous - now):
        stale = project_path / rel
        if stale.is_file():
            stale.unlink()
            removed.append(rel)
            # An arc beat was the last note in its character folder.
            for parent in stale.parents:
                if parent == project_path or not parent.is_dir():
                    break
                if parent.parent == project_path / "arcs" and not any(parent.iterdir()):
                    parent.rmdir()
                break

    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(sorted(now), indent=2))
    return removed


def _export_all(conn, project_path: Path) -> set:
    """Export all entities to markdown files. Returns the set of paths written."""
    # Per folder, the names claimed so far *in this pass*. Deliberately not
    # seeded from disk: re-exporting overwrites Kael.md with Kael.md, so a
    # second export is idempotent. The counter only fires when two entities in
    # one folder want the same title.
    used_names = {}
    # A beat's folder is its character's title, so the id -> title map is needed
    # before the beats are written.
    char_titles = dict(conn.execute(
        "SELECT id, name FROM entities WHERE type='character' AND is_deleted=0"))
    # character id -> the folder name their beats are filed under
    arc_dirs = {}
    written = set()
    entity_rows = conn.execute(
        "SELECT id, type, name, one_sentence, order_key, status, parent_id, location_id, extra "
        "FROM entities WHERE is_deleted=0 ORDER BY type, id"
    ).fetchall()

    for row in entity_rows:
        entity_id, entity_type, name, one_sentence, order_key, status, parent_id, location_id, extra_json = row
        extra = json.loads(extra_json) if extra_json else {}

        # Denormalize from relations back to frontmatter
        if entity_type == "scene":
            chars = conn.execute(
                "SELECT from_id FROM relations WHERE to_id=? AND kind='character_scene'",
                (entity_id,)
            ).fetchall()
            if chars:
                extra["characters"] = [r[0] for r in chars]

        if entity_type == "location" or entity_type == "world":
            kind = "location_variant" if entity_type == "location" else "world_variant"
            var = conn.execute(
                f"SELECT to_id FROM relations WHERE from_id=? AND kind='{kind}'",
                (entity_id,)
            ).fetchone()
            if var:
                extra["variant_of"] = var[0]

        if entity_type == "plot":
            for field, kind in (("setups", "plot_setup"), ("crisis", "plot_crisis"),
                                ("climax", "plot_climax"), ("payoffs", "plot_payoff")):
                beat_rows = conn.execute(
                    f"SELECT to_id, note FROM relations WHERE from_id=? AND kind='{kind}' "
                    f'ORDER BY "order"', (entity_id,)
                ).fetchall()
                if beat_rows:
                    extra[field] = [{"scene_id": r[0], "description": r[1]} for r in beat_rows]

        fm = _frontmatter_for(entity_type, entity_id, name, one_sentence, order_key, status, parent_id, location_id, extra)
        # The filename is the title, so `id` is the only thing that survives a
        # rename — it has to be in the note for every type, not just the four
        # that happened to declare it. Set here rather than in each branch.
        fm["id"] = entity_id
        sections = conn.execute(
            "SELECT heading, body FROM sections WHERE entity_id = ? ORDER BY rowid",
            (entity_id,)
        ).fetchall()

        body = ""
        if sections:
            parts = []
            for heading, body_text in sections:
                parts.append(f"## {heading}\n\n{body_text.rstrip()}")
            body = "\n\n".join(parts)

        if entity_type == "project":
            _write_note(project_path / "project.md", fm, body)
            written.add(project_path / "project.md")
            from core.db import get_project_memory
            _write_note(project_path / ".story" / "memory.md", get_project_memory(project_path), "")
            written.add(project_path / ".story" / "memory.md")
            continue

        if entity_type == "arc_beat":
            # The character is the folder, named by their title like every other
            # note. The character link itself rides in the frontmatter, so this
            # is grouping, not identity. Cached per character: the counter in
            # _filename is for siblings, and every beat of one character has to
            # land in the *same* folder.
            arcs = project_path / "arcs"
            if parent_id not in arc_dirs:
                arc_dirs[parent_id] = _filename(
                    char_titles.get(parent_id, parent_id or "unknown"),
                    arcs, used_names.setdefault(arcs, set()))
            folder = arcs / arc_dirs[parent_id]
            folder.mkdir(parents=True, exist_ok=True)
        else:
            folder = project_path / _folder_for(entity_type)

        # The filename is the title, so the id has to live in the frontmatter —
        # it is the only thing that survives the name change. `used` is per
        # folder, so two characters may each own a "The Choice" note.
        used = used_names.setdefault(folder, set())
        note = folder / f"{_filename(name, folder, used)}.md"
        _write_note(note, fm, body)
        written.add(note)

    return written


def _frontmatter_for(entity_type: str, entity_id: str, name: str, one_sentence: str,
                     order_key: float, status: str, parent_id: str, location_id: str,
                     extra: dict) -> dict:
    """Build frontmatter dict for export."""
    if entity_type == "project":
        fm = {"name": name, "logline": one_sentence}
        fm.update({k: v for k, v in extra.items() if k != "memory"})
        return fm

    fm = {}

    if entity_type == "character":
        fm["name"] = name
        fm["one_sentence"] = one_sentence
        char_schema = ENTITY_SCHEMAS.get("character", {})
        extra = {k: v for k, v in extra.items() if not char_schema.get(k, {}).get("computed")}
        fm.update(extra)
        return fm

    if entity_type == "location":
        fm["name"] = name
        fm["one_sentence"] = one_sentence
        # Merge extra fields (mood, dramatic_function, variant_of)
        for k, v in extra.items():
            if k not in fm:
                fm[k] = v
        # World from parent_id
        if parent_id:
            fm["world"] = parent_id
        return fm

    if entity_type == "world":
        fm["name"] = name
        fm["one_sentence"] = one_sentence
        # Merge extra fields (rules, period, values, power, variant_of)
        for k, v in extra.items():
            if k not in fm:
                fm[k] = v
        return fm

    if entity_type == "plot":
        fm["name"] = name
        if one_sentence:
            fm["one_sentence"] = one_sentence
        if status:
            fm["status"] = status
        fm.update(extra)
        return fm

    if entity_type == "scene":
        fm["id"] = entity_id
        fm["title"] = name
        fm["order"] = int(order_key) if order_key == int(order_key) else order_key
        fm["status"] = status
        fm["sequence_id"] = parent_id
        if location_id:
            fm["location"] = location_id
        fm.update(extra)
        return fm

    if entity_type == "sequence":
        fm["id"] = entity_id
        fm["title"] = name
        fm["order"] = int(order_key) if order_key == int(order_key) else order_key
        fm["status"] = status
        fm["act_id"] = parent_id
        fm.update(extra)
        return fm

    if entity_type == "act":
        fm["id"] = entity_id
        fm["title"] = name
        fm["order"] = int(order_key) if order_key == int(order_key) else order_key
        fm["status"] = status
        fm.update(extra)
        return fm

    if entity_type == "arc_beat":
        fm["id"] = entity_id
        fm["character"] = parent_id
        fm["label"] = name
        fm["order"] = int(order_key) if order_key == int(order_key) else order_key
        # Remove 'id' from extra since we already set it
        arc_extra = {k: v for k, v in extra.items() if k != "id"}
        fm.update(arc_extra)
        return fm

    if entity_type == "relationship":
        fm["name"] = name
        if status:
            fm["status"] = status
        fm.update(extra)
        return fm

    fm.update(extra)
    return fm


def _folder_for(entity_type: str) -> str:
    return _FOLDERS.get(entity_type, entity_type)


def _write_note(path: Path, fm: dict, body: str) -> None:
    """Write a note file with frontmatter and body."""
    import frontmatter
    path.parent.mkdir(parents=True, exist_ok=True)
    post = frontmatter.Post(body, **fm)
    with open(path, "w") as f:
        frontmatter.dump(post, f)
