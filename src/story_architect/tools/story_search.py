"""story_search tool — search within a project."""
import json
from pathlib import Path

DEFAULT_LIMIT = 10
MAX_LIMIT = 50      # snippets are capped at 200 chars, so 50 hits is ~14 KB


def _clamp_limit(raw) -> tuple[int, bool]:
    """The limit to use, and whether the caller's value had to be cut down.

    The schema's `maximum` is advice, not enforcement: nothing between the model
    and this handler validates it, and SQLite reads `LIMIT -1` as "no limit", so
    an unclamped value can return every match in the project. A bad type falls
    back to the default; an out-of-range number is brought into range.
    """
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return DEFAULT_LIMIT, False
    clamped = max(1, min(value, MAX_LIMIT))
    return clamped, clamped != value


SCHEMA = {
    "description": "Find where something is mentioned, across all section prose in a project. "
                   "Returns short snippets, not full text, and reports the true total match count "
                   "so nothing is silently hidden. Follow up with story_retrieve to read a hit.",
    "type": "object",
    "properties": {
        "project": {
            "type": "string",
            "description": "Project slug or name"
        },
        "query": {
            "type": "string",
            "description": "Search query. All words must be present (AND). Punctuation is safe."
        },
        "limit": {
            "type": "integer",
            "description": "Max results to return (default 10). total_matches always reports the full count.",
            "minimum": 1,
            "maximum": 50,
        }
    },
    "required": ["project", "query"]
}


def handler(args: dict, **kwargs) -> str:
    """Search across project section prose."""
    from story_architect.core.config import resolve_root
    from story_architect.core.db import get_db, has_schema, search_sections
    from .story_resolve import resolve_project

    root_path = resolve_root(kwargs)

    try:
        project_path = resolve_project(args["project"], root_path)
    except ValueError as e:
        return json.dumps({"error": str(e)})

    db_path = project_path / ".story" / "story.db"
    if not db_path.exists():
        return json.dumps({"error": "Database not found. Run story_import first."})

    conn = get_db(project_path)
    try:
        if not has_schema(conn):
            return json.dumps({"error": "Database schema incomplete. Run story_import first."})
    finally:
        conn.close()

    # No blanket except: a failed search must not be reported as a missing DB,
    # which would send the agent to story_import and wipe runtime work.
    limit, was_clamped = _clamp_limit(args.get("limit", DEFAULT_LIMIT))
    found = search_sections(project_path, args["query"], limit=limit)

    results, total = found["results"], found["total_matches"]
    response = {
        "query": args["query"],
        "results": results,
        "total": len(results),
        "total_matches": total,
    }
    notes = []
    if was_clamped:
        notes.append(f"limit was brought into range (1-{MAX_LIMIT}).")
    if total > len(results):
        notes.append(
            f"Showing {len(results)} of {total} matches. Narrow the query, or raise "
            f"limit (max {MAX_LIMIT}). Use story_retrieve to read a section in full."
        )
    if notes:
        response["note"] = " ".join(notes)
    return json.dumps(response)
