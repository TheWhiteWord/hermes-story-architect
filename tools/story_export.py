"""story_export tool — reads story.db → writes markdown vault."""
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
    """Export SQLite to markdown vault."""
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

    from core.db import get_db

    conn = get_db(project_path)
    try:
        _export_all(conn, project_path)
    except Exception as e:
        conn.close()
        return json.dumps({"error": str(e)})

    conn.close()
    return json.dumps({"success": True, "message": f"Exported {project_path.name}"})


def _export_all(conn, project_path: Path) -> None:
    """Export all entities to markdown files."""
    rows = conn.execute(
        "SELECT id, type, name, one_sentence, order_key, status, parent_id, location_id, extra, is_deleted "
        "FROM entities ORDER BY type, id"
    ).fetchall()

    for row in rows:
        entity_id, entity_type, name, one_sentence, order_key, status, parent_id, location_id, extra_json, is_deleted = row
        extra = json.loads(extra_json) if extra_json else {}

        # Denormalize from relations back to frontmatter
        if entity_type == "scene":
            chars = conn.execute(
                "SELECT from_id FROM relations WHERE to_id=? AND kind='character_scene'",
                (entity_id,)
            ).fetchall()
            if chars:
                extra["characters"] = [r[0] for r in chars]

        if entity_type == "plot":
            setups = conn.execute(
                "SELECT to_id, note FROM relations WHERE from_id=? AND kind='plot_setup'",
                (entity_id,)
            ).fetchall()
            if setups:
                extra["setups"] = [{"scene_id": s[0], "description": s[1]} for s in setups]
            payoffs = conn.execute(
                "SELECT to_id, note FROM relations WHERE from_id=? AND kind='plot_payoff'",
                (entity_id,)
            ).fetchall()
            if payoffs:
                extra["payoffs"] = [{"scene_id": p[0], "description": p[1]} for p in payoffs]

        fm = _frontmatter_for(entity_type, entity_id, name, one_sentence, order_key, status, parent_id, location_id, extra)
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
        elif entity_type == "arc":
            # Derive beat_id from composite entity_id + parent_id
            beat_id = entity_id[len(parent_id)+1:] if parent_id else entity_id
            char_dir = project_path / "arcs" / parent_id
            char_dir.mkdir(parents=True, exist_ok=True)
            _write_note(char_dir / f"{beat_id}.md", fm, body)
        elif is_deleted:
            recycle_dir = project_path / "_recycle-bin" / entity_type
            _write_note(recycle_dir / f"{entity_id}.md", fm, body)
        else:
            folder = _folder_for(entity_type)
            _write_note(project_path / folder / f"{entity_id}.md", fm, body)


def _frontmatter_for(entity_type: str, entity_id: str, name: str, one_sentence: str,
                     order_key: float, status: str, parent_id: str, location_id: str,
                     extra: dict) -> dict:
    """Build frontmatter dict for export."""
    if entity_type == "project":
        fm = {"name": name, "logline": one_sentence}
        fm.update(extra)
        return fm

    fm = {}

    if entity_type == "character":
        fm["name"] = name
        fm["one_sentence"] = one_sentence
        fm.update(extra)
        return fm

    if entity_type == "location":
        fm["name"] = name
        fm["one_sentence"] = one_sentence
        return fm

    if entity_type == "world":
        fm["name"] = name
        fm["one_sentence"] = one_sentence
        if "rules" in extra:
            fm["rules"] = extra["rules"]
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

    if entity_type == "arc":
        # Derive beat_id from composite entity_id + parent_id (no extra storage needed)
        beat_id = entity_id[len(parent_id)+1:] if parent_id else entity_id
        fm["id"] = beat_id
        fm["character"] = parent_id
        fm["label"] = name
        fm["order"] = int(order_key) if order_key == int(order_key) else order_key
        # Remove 'id' from extra since we already set it
        arc_extra = {k: v for k, v in extra.items() if k != "id"}
        fm.update(arc_extra)
        return fm

    fm.update(extra)
    return fm


def _folder_for(entity_type: str) -> str:
    return {
        "character": "characters",
        "location": "locations",
        "world": "worlds",
        "plot": "plots",
        "scene": "scenes",
        "sequence": "sequences",
        "act": "acts",
    }.get(entity_type, entity_type)


def _write_note(path: Path, fm: dict, body: str) -> None:
    """Write a note file with frontmatter and body."""
    import frontmatter
    path.parent.mkdir(parents=True, exist_ok=True)
    post = frontmatter.Post(body, **fm)
    with open(path, "w") as f:
        frontmatter.dump(post, f)
