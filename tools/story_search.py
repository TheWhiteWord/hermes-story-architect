"""story_search tool — search within a project."""
import json
from pathlib import Path

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
    from core.config import load_plugin_config
    from core.db import get_db, has_schema, search_sections
    from .story_resolve import resolve_project

    _vault = kwargs.get("vault_path")
    if _vault:
        vault_path = Path(_vault)
    else:
        config = load_plugin_config()
        vault_path = Path(config.get("vault_path", "~/story-vault")).expanduser()

    try:
        project_path = resolve_project(args["project"], vault_path)
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
    found = search_sections(project_path, args["query"], limit=args.get("limit", 10))

    results, total = found["results"], found["total_matches"]
    response = {
        "query": args["query"],
        "results": results,
        "total": len(results),
        "total_matches": total,
    }
    if total > len(results):
        response["note"] = (
            f"Showing {len(results)} of {total} matches. Narrow the query, or raise "
            f"limit (max 50). Use story_retrieve to read a section in full."
        )
    return json.dumps(response)
