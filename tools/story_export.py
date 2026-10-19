"""story_export tool — reads story.db → writes markdown vault."""
import json
import re
from pathlib import Path

from core.constants import ENTITY_SCHEMAS
from core.entity import PLOT_BEAT_FIELDS

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
    "scene_beats": "scene_beats",
    "sequence": "sequences",
    "act": "acts",
    "relationship": "relationships",
}


# A value is not a folder note: every value lives in one file at the project
# root, one frontmatter block per value, so a writer reads the whole set at
# once instead of opening one note per value. Everything else is per-note.
VALUE_FILE = "values.md"


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

    # A scene_beats note has no title of its own — the design names it by the
    # SCENE's title — so the map has to exist before the records are written.
    scene_titles = dict(conn.execute(
        "SELECT id, name FROM entities WHERE type='scene' AND is_deleted=0"))
    written = set()
    value_blocks = []
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
            # `plot_roles` is a RELATION field, so it never lands in `extra` and
            # `fm.update(extra)` below would silently drop every plot role from
            # the scene note — and re-import would then lose them with nothing
            # to complain about. Rebuilt from the rows, which is the same fact
            # the plot note used to carry.
            role_rows = conn.execute(
                "SELECT from_id, kind, note FROM relations "
                "WHERE to_id=? AND kind LIKE 'plot_%' ORDER BY \"order\"",
                (entity_id,)
            ).fetchall()
            if role_rows:
                extra["plot_roles"] = [
                    {"plot": f, "role": k[len("plot_"):], "description": n or ""}
                    for f, k, n in role_rows
                ]

        if entity_type == "location" or entity_type == "world":
            kind = "location_variant" if entity_type == "location" else "world_variant"
            var = conn.execute(
                f"SELECT to_id FROM relations WHERE from_id=? AND kind='{kind}'",
                (entity_id,)
            ).fetchone()
            if var:
                extra["variant_of"] = var[0]

        if entity_type == "plot":
            # The five role fields are computed and are NOT emitted: they are the
            # scene's `plot_roles` read back from this side, so writing them here
            # would put the same fact on both notes and let the two disagree.
            for field in list(PLOT_BEAT_FIELDS):
                extra.pop(field, None)

        # Nested value data is stored as JSON, so its key order is whatever the
        # writer happened to produce — and the note is what a writer reads.
        # Reorder it against the schema's declared `sub_fields`, recursively,
        # so `value_turns` reads plot/value/from/to before its effects and the
        # ladder reads p/c/cd/nn rather than alphabetically.
        for field, meta in ENTITY_SCHEMAS.get(entity_type, {}).items():
            if meta.get("sub_fields") and field in extra:
                extra[field] = _ordered(extra[field], meta)

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

        if entity_type == "value":
            value_blocks.append(_value_block(entity_id, name, extra, body))
            continue

        if entity_type == "project":
            _write_note(project_path / "project.md", fm, body)
            written.add(project_path / "project.md")
            from core.db import get_project_memory
            _write_note(project_path / ".story" / "memory.md", get_project_memory(project_path), "")
            written.add(project_path / ".story" / "memory.md")
            continue

        folder = project_path / _folder_for(entity_type)

        # A scene_beats note is named by the scene's title: the record has no
        # title of its own, and two records for scenes of the same name would
        # otherwise both fall to the "untitled" fallback and collide.
        note_title = name
        if entity_type == "scene_beats" and parent_id:
            note_title = scene_titles.get(parent_id, name)

        # The filename is the title, so the id has to live in the frontmatter —
        # it is the only thing that survives the name change. `used` is per
        # folder, so two characters may each own a "The Choice" note.
        used = used_names.setdefault(folder, set())
        note = folder / f"{_filename(note_title, folder, used)}.md"
        _write_note(note, fm, body)
        written.add(note)

    # One file for every value, always written — an empty `values.md` is a
    # stable, present file rather than a file that appears and disappears.
    # `entity_rows` is `ORDER BY type, id`, so the blocks come out in id order.
    # Written directly rather than through `_write_note`: the file is a
    # concatenation of blocks that already carry their own `---` fences, so a
    # wrapper frontmatter block would be a leading `--- {} ---` the parser has
    # to skip.
    values_path = project_path / VALUE_FILE
    values_path.write_text("\n\n".join(value_blocks) + ("\n" if value_blocks else ""))
    written.add(values_path)

    return written


def _ordered(value, meta: dict):
    """Reorder a field's entries and their nested entries to the schema's order.

    Declared `sub_fields` come first, in declaration order, at every depth;
    any key the declaration does not name is kept after them rather than
    dropped, so an unrecognised key still reaches the note and is still refused
    on the next import instead of vanishing silently.
    """
    subs = meta.get("sub_fields") or {}
    if meta.get("type") == "list" and isinstance(value, list):
        return [_ordered(v, meta) for v in value]
    if isinstance(value, dict):
        out = {}
        if meta.get("type") == "object" and meta.get("keyed"):
            # A map keyed by entity: the keys are data, only the values reorder.
            return {k: _ordered(v, meta) for k, v in value.items()}
        for key, sub_meta in subs.items():
            if key in value:
                out[key] = _ordered(value[key], sub_meta) if sub_meta.get(
                    "sub_fields") else value[key]
        for key, v in value.items():
            if key not in out:
                out[key] = v
        return out
    return value


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

    if entity_type == "scene_beats":
        fm["id"] = entity_id
        fm["scene"] = parent_id
        fm.update({k: v for k, v in extra.items() if k != "id"})
        return fm

    if entity_type == "relationship":
        fm["name"] = name
        if status:
            fm["status"] = status
        fm.update(extra)
        return fm

    fm.update(extra)
    return fm


def _value_block(entity_id: str, name: str, extra: dict, body: str) -> str:
    """One value as a frontmatter block for the concatenated `values.md`.

    Field order is `id, name, p, c, cd, nn, note` — the schema order, so the
    ladder reads p/c/cd/nn rather than alphabetically. `note` is skipped when
    empty. The block carries no wrapper frontmatter of its own: the file is a
    concatenation of these, and the importer splits on the `---` fences.
    """
    import frontmatter
    fm = {"id": entity_id, "name": name}
    for rung in ("p", "c", "cd", "nn"):
        fm[rung] = str(extra.get(rung) or "")
    if extra.get("note"):
        fm["note"] = extra["note"]
    return frontmatter.dumps(frontmatter.Post(body, **fm), sort_keys=False).rstrip("\n")


def _folder_for(entity_type: str) -> str:
    return _FOLDERS.get(entity_type, entity_type)


def _write_note(path: Path, fm: dict, body: str) -> None:
    """Write a note file with frontmatter and body.

    `sort_keys=False` keeps the declared order, top level and nested: PyYAML
    sorts by default, so a `value_turns` entry came out alphabetised — effects
    before plot, and the ladder as c/cd/nn/note/p/value — which reads as noise
    in the one file a writer actually edits. The schema's `sub_fields` order is
    the intended reading order.
    """
    import frontmatter
    path.parent.mkdir(parents=True, exist_ok=True)
    post = frontmatter.Post(body, **fm)
    with open(path, "w") as f:
        frontmatter.dump(post, f, sort_keys=False)
