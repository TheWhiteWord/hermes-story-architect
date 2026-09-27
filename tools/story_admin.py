"""story_admin tool — project lifecycle and the admin-only entity operations.

Five actions, none of them proposals. Entity *authoring* goes through
story_draft, which shows the user what will change and writes nothing until they
say so. What is here cannot be drafted at all: a project has no database to hold
a draft before it exists, and purge/restore/delete-project are the operations
that must never be a side effect of committing a batch.

`purge` and `restore` are the undo pair. `create_project`, `list_projects` and
`delete_project` are the project lifecycle; nothing drafts, because a draft
exists to exist before it is written.
"""
import json
import shutil
from pathlib import Path

SCHEMA = {
    "description": "Project lifecycle and admin operations: create_project (a new project), "
                   "list_projects, delete_project, restore (bring a soft-deleted entity back), "
                   "purge (permanently remove entities deleted over 30 days ago). Entity content "
                   "itself is NOT here — create and edit through story_draft, which shows the "
                   "user the change before it is written. Deleting an entity is a soft delete and "
                   "is exactly reversible via restore; purge is the only irreversible one, and "
                   "delete_project removes an entire project.",
    "type": "object",
    "properties": {
        "action": {
            "type": "string",
            "enum": ["create_project", "list_projects", "delete_project", "restore", "purge"],
            "description": "create_project (initialise a new project folder + database), "
                           "list_projects (every project under the root, no database opened), "
                           "delete_project (remove a project folder and everything in it), "
                           "restore (undelete one entity, bringing back its prose and relations "
                           "exactly as they were), purge (permanently remove soft-deleted "
                           "entities older than the age floor — irreversible)"
        },
        "project": {
            "type": "string",
            "description": "Project slug or path. For create_project this is the new project's "
                           "folder name and the project does not exist yet.",
        },
        "frontmatter": {
            "type": "object",
            "description": "For create_project: the project entity's field values, e.g. "
                           "{name, logline}. Missing fields fall back to schema defaults; "
                           "required fields must be present and non-empty.",
        },
        "target": {
            "type": "object",
            "description": "For restore: the entity to bring back.",
            "properties": {
                "entity_type": {"type": "string",
                                "description": "Type of entity to restore"},
                "slug": {"type": "string", "description": "Entity id, as returned by story_load"},
            },
        },
        "summary": {
            "type": "string",
            "description": "For restore: one line naming what was restored",
        },
        "delete_confirm": {
            "type": "string",
            "description": "Required for action=\"delete_project\". Must contain the literal text "
                           "\"DELETE <project slug>\", e.g. \"DELETE my-film\". This is the "
                           "user's call to make — do not supply it unless the user has asked for "
                           "the project to be removed entirely. A string, not a boolean, on "
                           "purpose: a flag is something the agent can set by itself, and this "
                           "destroys every entity in the project."
        },
        "purge_confirm": {
            "type": "string",
            "description": "Required for action=\"purge\". Must contain the literal text "
                           "\"DELETE <project slug>\", e.g. \"DELETE my-film\". This is the "
                           "user's call to make — do not supply it unless the user has asked for "
                           "the deleted entities to be removed permanently."
        },
        "older_than_days": {
            "type": "integer",
            "description": "For action=\"purge\": only purge entities deleted longer ago than "
                           "this many days. Default 30. Anything newer stays restorable."
        },
    },
    "required": ["action"],
}


def handler(args: dict, **kwargs) -> str:
    from core.config import resolve_root

    root_path = resolve_root(kwargs)
    action = args["action"]

    try:
        if action == "create_project":
            return json.dumps(_create_project(args, root_path))
        if action == "list_projects":
            return json.dumps(_list_projects(root_path))
        if action == "delete_project":
            return json.dumps(_delete_project(args, root_path))
        if action == "purge":
            return json.dumps(_purge_deleted(args, _resolve(args, root_path)))
        if action == "restore":
            return json.dumps(_restore_entity(args, _resolve(args, root_path)))
        return json.dumps({"error": f"Unknown action: {action}"})
    except ValueError as e:
        return json.dumps({"error": str(e)})


def _resolve(args: dict, root_path: Path) -> Path:
    """Resolve the `project` argument, which every project-scoped action takes."""
    from .story_resolve import resolve_project
    return resolve_project(args.get("project", ""), root_path)


# ─── the five actions ───

def _create_project(args: dict, root_path: Path) -> dict:
    from core.writes import create_project
    return create_project(
        args.get("project", ""), args.get("frontmatter") or {}, root_path)


def _list_projects(root_path: Path) -> dict:
    """Every project folder under the root. Directory listing only.

    A project is a directory holding `.story/story.db` — so this reads the
    listing and nothing else. Opening a database per project to recover its
    display name would be a connection per candidate on every call, on a root
    that may hold hundreds; `resolve_project` already does that once, when
    there is a specific project to resolve.
    """
    projects_dir = root_path / "projects"
    if not projects_dir.is_dir():
        return {"success": True, "projects": [], "count": 0,
                "note": f"No projects directory at {projects_dir}"}

    projects = []
    for folder in sorted(projects_dir.iterdir()):
        if not folder.is_dir():
            continue
        db = folder / ".story" / "story.db"
        projects.append({
            "slug": folder.name,
            "path": str(folder),
            "has_database": db.exists(),
        })
    return {"success": True, "projects": projects, "count": len(projects)}


def _delete_project(args: dict, root_path: Path) -> dict:
    """Remove a project folder entirely. Backs up first, refuses without a typed string.

    Two deliberate guards, both because this is the one operation in the plugin
    that destroys work no flag in the database can bring back:

    1. `delete_confirm` must contain "DELETE <project slug>". The agent cannot
       arrive at that string on its own, so it can only happen if the user
       handed it over — a human in the loop by construction, not by prompt.
    2. A backup is taken and written *outside* the folder being removed, so the
       project is still recoverable by hand afterwards. `backup_database` puts
       its snapshot inside `project_path/.story/`, which `rmtree` would take
       with it — so it is relocated to `<root>/backups/` before the delete.
    """
    project_path = _resolve(args, root_path)
    slug = project_path.name

    required = f"DELETE {slug}"
    given = args.get("delete_confirm", "")
    if required not in given:
        return {
            "error": "Delete refused. It removes every entity in the project and "
                     "no flag in the database can undo it.",
            "action_required": f'Re-run with delete_confirm="{required}" if the user has '
                               f"asked for this project to be removed entirely.",
            "project": str(project_path),
            "hint": "To keep the project but tidy it up, use action=\"purge\" "
                    "instead — that only touches entities already soft-deleted.",
        }

    if not (project_path / ".story" / "story.db").exists():
        return {
            "error": f"Not a story project — no .story/story.db in {project_path}. "
                     f"Nothing was deleted.",
            "project": str(project_path),
        }

    backup = _backup_outside(project_path, root_path)
    shutil.rmtree(project_path)

    return {
        "success": True,
        "message": f"Deleted project: {slug}",
        "project": str(project_path),
        "backup": backup,
        "note": "The backup is the full database as it was immediately before the "
                "delete. To recover, copy it back to <project>/.story/story.db.",
    }


def _backup_outside(project_path: Path, root_path: Path) -> str:
    """Snapshot a project's database into <root>/backups/, not into the project.

    `backup_database` writes beside the database it copies, which for
    `delete_project` means the snapshot is destroyed by the very delete it was
    taken for. Same WAL-safe copy, different destination.
    """
    from datetime import datetime

    from core.db import backup_database

    snapshot = Path(backup_database(project_path))
    backups = root_path / "backups"
    backups.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = backups / f"{project_path.name}_{stamp}.db"
    n = 1
    while dest.exists():
        dest = backups / f"{project_path.name}_{stamp}_{n}.db"
        n += 1
    shutil.move(str(snapshot), str(dest))
    return str(dest)


def _purge_deleted(args: dict, project_path: Path) -> dict:
    """Permanently remove soft-deleted rows. Two deliberate guards.

    1. `purge_confirm` must contain the literal "DELETE <project slug>". The
       agent cannot guess that string, so it can only ever purge if the user
       handed it over — which puts a human in the loop by construction.
    2. An age floor: only rows deleted more than `older_than_days` ago (default
       30) are eligible. Anything deleted in this session stays restorable, so
       tidying up can never destroy a fresh mistake.

    A backup is taken first, so even this is recoverable by hand.
    """
    from datetime import datetime, timedelta

    from core.db import backup_database, get_db

    required = f"DELETE {project_path.name}"
    given = args.get("purge_confirm", "")
    if required not in given:
        return {
            "error": "Purge refused. It is irreversible and must be the user's call.",
            "action_required": f'Re-run with purge_confirm="{required}" if you are sure.',
            "hint": 'To undo a delete instead, use action="restore" — that is exact.',
        }

    days = args.get("older_than_days", 30)
    cutoff = (datetime.now() - timedelta(days=days)).isoformat(timespec="seconds")

    conn = get_db(project_path)
    try:
        rows = conn.execute(
            "SELECT id, type, deleted_at FROM entities "
            "WHERE is_deleted=1 AND deleted_at IS NOT NULL AND deleted_at <= ? "
            "ORDER BY type, id", (cutoff,)).fetchall()
        if not rows:
            younger = conn.execute(
                "SELECT count(*) FROM entities WHERE is_deleted=1").fetchone()[0]
            return {
                "success": True,
                "purged": [],
                "message": (
                    f"Nothing is old enough to purge ({younger} deleted entities are "
                    f"younger than {days} days). They stay restorable."),
            }

        ids = [r[0] for r in rows]
        marks = ",".join("?" * len(ids))
        backup = backup_database(project_path)
        conn.execute(f"DELETE FROM sections WHERE entity_id IN ({marks})", ids)
        conn.execute(f"DELETE FROM relations WHERE from_id IN ({marks}) "
                     f"OR to_id IN ({marks})", ids + ids)
        conn.execute(f"DELETE FROM entities WHERE id IN ({marks})", ids)
    finally:
        conn.close()

    return {
        "success": True,
        "message": f"Purged {len(ids)} entities permanently.",
        "purged": [{"id": r[0], "type": r[1], "deleted_at": r[2]} for r in rows],
        "backup": backup,
        "note": ("Markdown files for these entities are removed by the next "
                 "story_export."),
    }


def _restore_entity(args: dict, project_path: Path) -> dict:
    """Undelete an entity by clearing is_deleted. Exact inverse of the delete.

    Sections and relations were never removed, so there is nothing to rebuild —
    which is the whole reason the delete is a flag and not a DELETE.
    """
    from core.db import get_db

    target = args.get("target") or {}
    entity_type = target.get("entity_type") or ""
    slug = target.get("slug") or ""
    summary = args.get("summary", "")
    conn = get_db(project_path)
    try:
        # Deliberately NOT filtered on is_deleted — that is the point.
        row = conn.execute(
            "SELECT id, is_deleted, deleted_at FROM entities WHERE id=? OR id=?",
            (slug, slug),
        ).fetchone()
        if not row:
            return {"error": f"Entity not found: {entity_type}/{slug}"}
        entity_id, is_deleted, deleted_at = row
        if not is_deleted:
            return {
                "error": f"{entity_id} is not deleted — nothing to restore.",
                "entity_id": entity_id,
            }
        conn.execute(
            "UPDATE entities SET is_deleted=0, deleted_at=NULL WHERE id=?", (entity_id,))
        # Beats cascaded with the character come back too — a restore that left
        # them deleted would silently halve the arc.
        restored_children = [r[0] for r in conn.execute(
            "SELECT id FROM entities WHERE type='arc_beat' AND parent_id=? "
            "AND is_deleted=1 ORDER BY id", (entity_id,)).fetchall()]
        if restored_children:
            conn.execute(
                "UPDATE entities SET is_deleted=0, deleted_at=NULL "
                "WHERE type='arc_beat' AND parent_id=? AND is_deleted=1", (entity_id,))
    finally:
        conn.close()

    return {
        "success": True,
        "message": f"Restored: {summary}",
        "entity_id": entity_id,
        "was_deleted_at": deleted_at,
        "restored_cascade_children": restored_children,
    }
