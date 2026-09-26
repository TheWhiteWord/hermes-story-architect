"""Dedicated project story-memory mutations."""
import json
from pathlib import Path

from core.constants import MEMORY_CATEGORIES, MEMORY_CHAR_LIMIT, MEMORY_ENTRY_LIMIT
from core.db import (
    empty_memory,
    get_project_memory,
    memory_serialized_length,
    set_project_memory,
)

SCHEMA = {
    "description": "Record a durable project fact that should outlive this conversation: a "
                   "decision the user made, a direction for the story, an open question, or a "
                   "continuity warning. One entry at a time. Prefer this over repeating yourself "
                   "in conversation — it survives a new session.",
    "type": "object",
    "properties": {
        "action": {"type": "string", "enum": ["add", "remove", "replace"],
                   "description": "add a new entry, remove an existing one, or replace it."},
        "project": {"type": "string", "description": "Project slug or path"},
        "category": {"type": "string", "enum": list(MEMORY_CATEGORIES),
                     "description": "decisions (choices made), directions (intent for the story), "
                                    "open_questions (unresolved), continuity_warnings (facts that "
                                    "must not be contradicted)."},
        "entry": {"type": "string",
                  "description": "The new text. Required for action=add. Must be non-empty and "
                                 "concise — this is a reminder to a future session, not prose."},
        "old_entry": {"type": "string",
                      "description": "The complete existing text, matched exactly. Required for "
                                     "action=remove and action=replace."},
        "new_entry": {"type": "string",
                      "description": "The replacement text. Required for action=replace."},
    },
    "required": ["action", "project", "category"],
}


def _usage(memory: dict) -> str:
    return f"{memory_serialized_length(memory)}/{MEMORY_CHAR_LIMIT}"


def _error(message: str, memory: dict, category: str, action_required: str) -> str:
    return json.dumps({
        "success": False,
        "error": message,
        "usage": _usage(memory),
        "category": category,
        "current_entries": memory.get(category, []),
        "action_required": action_required,
    })


# Below this score the project match was a guess, not a confident hit. Only
# reported on a successful write (a failed call already lists the alternatives),
# and only by this tool — the other ten share the resolver and were not changed.
CONFIDENT_MATCH = 90


def _match_confidence(user_input: str, resolved: Path) -> dict | None:
    """Flag a project that was fuzzy-matched rather than named exactly."""
    from rapidfuzz import fuzz

    slug = resolved.name
    if user_input.strip() == slug:
        return None
    score = fuzz.WRatio(user_input, slug)
    if score >= CONFIDENT_MATCH:
        return None
    return {
        "warning": f"Project '{user_input}' was matched to '{slug}' "
                   f"(similarity {score:.0f}). Memory was written to '{slug}'.",
        "resolved_project": slug,
        "match_score": round(score),
    }


def handler(args: dict, **kwargs) -> str:
    """Apply one exact-entry mutation to project.extra.memory."""
    from .story_resolve import resolve_project
    from core.config import resolve_root

    root_path = resolve_root(kwargs)
    try:
        project_path = resolve_project(args["project"], root_path)
    except ValueError as exc:
        return json.dumps({"error": str(exc)})
    uncertain = _match_confidence(args["project"], project_path)

    action = args["action"]
    category = args["category"]
    memory = get_project_memory(project_path)
    if action not in ("add", "remove", "replace"):
        return _error("Unknown memory action.", memory, category, "Use add, remove, or replace.")
    entries = list(memory.get(category, []))

    if category not in MEMORY_CATEGORIES:
        return _error("Unknown memory category.", memory, category, "Choose one of the four supported categories.")

    try:
        if action == "add":
            entry = args.get("entry", "")
            if not isinstance(entry, str) or not entry.strip():
                return _error("Memory entries must be non-empty strings.", memory, category, "Provide a concise entry.")
            if len(entry) > MEMORY_ENTRY_LIMIT:
                return _error(f"Memory entries must be at most {MEMORY_ENTRY_LIMIT} characters.", memory, category, "Shorten the entry before retrying.")
            result = {"success": True, "operation": "add", "category": category,
                      "entry": entry, "usage": _usage(memory)}
            if uncertain:
                result.update(uncertain)
            if entry in entries:
                return json.dumps(result)
            entries.append(entry)
            set_project_memory(project_path, {**memory, category: entries})
            return json.dumps(result)

        old_entry = args.get("old_entry", "")
        if old_entry not in entries:
            return _error("Entry not found in category.", memory, category, "Use the complete existing entry text.")
        index = entries.index(old_entry)
        if action == "remove":
            entries.pop(index)
            set_project_memory(project_path, {**memory, category: entries})
            result = {"success": True, "operation": "remove",
                      "category": category, "usage": _usage(memory)}
            if uncertain:
                result.update(uncertain)
            return json.dumps(result)

        new_entry = args.get("new_entry", "")
        if not isinstance(new_entry, str) or not new_entry.strip():
            return _error("Memory entries must be non-empty strings.", memory, category, "Provide a concise replacement.")
        if len(new_entry) > MEMORY_ENTRY_LIMIT:
            return _error(f"Memory entries must be at most {MEMORY_ENTRY_LIMIT} characters.", memory, category, "Shorten the replacement before retrying.")
        if new_entry != old_entry and new_entry in entries:
            return _error("Replacement entry already exists.", memory, category, "Choose a different replacement or remove the duplicate first.")
        entries[index] = new_entry
        try:
            set_project_memory(project_path, {**memory, category: entries})
        except ValueError as exc:
            return _error(str(exc), memory, category, "Replace, merge, or drop an existing entry before retrying.")
        result = {"success": True, "operation": "replace", "category": category,
                  "entry": new_entry, "usage": _usage(memory)}
        if uncertain:
            result.update(uncertain)
        return json.dumps(result)
    except (KeyError, TypeError, ValueError) as exc:
        return _error(str(exc), memory, category, "Review the memory entry and retry.")
