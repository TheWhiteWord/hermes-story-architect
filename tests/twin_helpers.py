"""Shared machinery for the "twin project" tests.

A delete used to PHYSICALLY remove what pointed at the deleted entity (relation
rows, names in other entities' `extra`, `location_id`). It now keeps all of it
and every reader hides it. The twin tests hold the new behaviour to the old: build two
identical projects, delete in both, physically remove the references in one of
them as the old delete did, and require every reader to give the same answer on
both. A reader that forgets to hide something shows it in one twin only.

`everything_a_reader_can_say` is the list of readers. A reader that is not in it
is not covered; add new ones here.
"""
import json
import shutil
import sqlite3

SLUG = "save-the-children"


def build(fixture_path, tmp_path, name):
    from story_architect.tools.story_import import handler as import_handler
    vault = tmp_path / name
    p = vault / "projects" / SLUG
    p.parent.mkdir(parents=True)
    shutil.copytree(str(fixture_path), str(p))
    import_handler({"project": SLUG, "confirm": True}, root_path=str(vault))
    return p, vault


def sql(p, statement, *args):
    conn = sqlite3.connect(str(p / ".story" / "story.db"))
    try:
        rows = conn.execute(statement, args).fetchall()
        conn.commit()
        return rows
    finally:
        conn.close()


def dead_set(p):
    return {r[0] for r in sql(p, "SELECT id FROM entities WHERE is_deleted=1")}


# ─── what the old delete did, kept here as the reference ───

def remove_relation_rows(p):
    """Physically remove every relation row that touches a deleted entity."""
    sql(p, "DELETE FROM relations WHERE from_id IN (SELECT id FROM entities WHERE is_deleted=1) "
           "OR to_id IN (SELECT id FROM entities WHERE is_deleted=1)")


def scrub_references(p):
    """The old `_purge_references`: take every deleted id out of the `extra` of
    every live entity (lists `characters`/`scenes`, the keys of `perspectives`)
    and empty `location_id` / `parent_id` columns that pointed at one."""
    dead = dead_set(p)
    conn = sqlite3.connect(str(p / ".story" / "story.db"))
    try:
        for eid, extra_json, loc, parent in conn.execute(
                "SELECT id, extra, location_id, parent_id FROM entities "
                "WHERE is_deleted=0").fetchall():
            extra = json.loads(extra_json) if extra_json else {}
            for field in ("characters", "scenes"):
                if isinstance(extra.get(field), list):
                    extra[field] = [v for v in extra[field] if str(v) not in dead]
            if isinstance(extra.get("perspectives"), dict):
                extra["perspectives"] = {k: v for k, v in extra["perspectives"].items()
                                         if k not in dead}
            conn.execute("UPDATE entities SET extra=?, location_id=CASE WHEN location_id IN "
                         "(SELECT id FROM entities WHERE is_deleted=1) THEN '' ELSE location_id END, "
                         "parent_id=CASE WHEN parent_id IN (SELECT id FROM entities "
                         "WHERE is_deleted=1) THEN '' ELSE parent_id END WHERE id=?",
                         (json.dumps(extra), eid))
        conn.commit()
    finally:
        conn.close()


# ─── every reader ───

def everything_a_reader_can_say(p, vault):
    """The output of every reader, per live entity, as comparable text."""
    from story_architect.app import services
    from story_architect.core import db, manual_edits, manual_entities, manual_structure, track
    from story_architect.tools import (story_export, story_load, story_retrieve,
                                       story_search)
    out = {}

    def rec(name, fn):
        try:
            r = fn()
            out[name] = r if isinstance(r, str) else json.dumps(r, default=str, sort_keys=True)
        except Exception as e:  # an error is output too; both twins must agree
            out[name] = f"{type(e).__name__}: {e}"

    for eid, etype in sql(p, "SELECT id, type FROM entities WHERE is_deleted=0 "
                             "AND type != 'project'"):
        rec(f"retrieve:{eid}", lambda: story_retrieve.handler(
            {"project": SLUG, "entity_type": etype, "id": eid,
             "fields": ["all"], "sections": ["all"]}, root_path=str(vault)))
        rec(f"form:{eid}", lambda: manual_entities.load_entity(p, etype, eid))
        rec(f"delete_preview:{eid}", lambda: manual_entities.delete_preview(p, etype, eid))
        if etype == "scene":
            rec(f"script:{eid}", lambda: manual_edits.load_scene_script(p, eid))
            rec(f"values:{eid}", lambda: story_load.handler(
                {"project": SLUG, "view": "values", "scene": eid}, root_path=str(vault)))
        if etype in ("character", "location", "world", "relationship"):
            rec(f"track:{eid}", lambda: track.for_entity(p, eid))
    rec("summary", lambda: db.get_project_summary(p))
    rec("unfilled_map", lambda: db.get_unfilled_map(p))
    rec("dashboard", lambda: db.get_dashboard_data(p))
    rec("app_dashboard", lambda: services.get_project_dashboard(vault, SLUG))
    rec("tree", lambda: manual_structure.load_tree(p))
    for view in (None, "dramatic_elements", "relationship", "unfilled"):
        rec(f"load:{view}", lambda: story_load.handler(
            {"project": SLUG, **({"view": view} if view else {})}, root_path=str(vault)))
    for character in ("kael", "mira"):
        rec(f"load:relationship:{character}", lambda: story_load.handler(
            {"project": SLUG, "view": "relationship", "character": character},
            root_path=str(vault)))
    for query in ("the", "door", "kael"):
        rec(f"search:{query}", lambda: story_search.handler(
            {"project": SLUG, "query": query}, root_path=str(vault)))
    rec("export", lambda: story_export.handler({"project": SLUG}, root_path=str(vault)))
    out["export_files"] = "\n".join(
        f"## {f.relative_to(p)}\n{f.read_text()}" for f in sorted(p.rglob("*.md"))
        if ".story" not in f.parts)
    return out


def differing(a, b):
    assert a.keys() == b.keys()
    return sorted(k for k in a if a[k] != b[k])


# ─── the whole stored state, for exact round trips ───

def snapshot(p):
    """Every table that holds project data, row for row."""
    return {t: sorted(map(repr, sql(p, f"SELECT * FROM {t}")))
            for t in ("entities", "relations", "sections", "revisions")}


# ─── the integrity oracle ───

def assert_no_orphans(project_path):
    """No row points at something that is not there (core.integrity)."""
    from story_architect.core.integrity import find_orphans
    conn = sqlite3.connect(str(project_path / ".story" / "story.db"))
    try:
        assert find_orphans(conn) == {}
    finally:
        conn.close()
