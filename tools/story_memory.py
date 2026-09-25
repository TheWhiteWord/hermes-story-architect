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
    "type": "object",
    "properties": {
        "action": {"type": "string", "enum": ["add", "remove", "replace"]},
        "project": {"type": "string", "description": "Project slug or path"},
        "category": {"type": "string", "enum": list(MEMORY_CATEGORIES)},
        "entry": {"type": "string"},
        "old_entry": {"type": "string"},
        "new_entry": {"type": "string"},
    },
    "required": ["action", "project", "category"],
    "description": "Add, remove, or replace one explicit project story-memory entry.",
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


def handler(args: dict, **kwargs) -> str:
    """Apply one exact-entry mutation to project.extra.memory."""
    from .story_resolve import resolve_project
    from core.config import load_plugin_config

    vault_path = Path(kwargs["vault_path"]) if kwargs.get("vault_path") else Path(
        load_plugin_config().get("vault_path", "~/story-vault")
    ).expanduser()
    try:
        project_path = resolve_project(args["project"], vault_path)
    except ValueError as exc:
        return json.dumps({"error": str(exc)})

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
            if entry in entries:
                return json.dumps({"success": True, "operation": "add", "category": category, "entry": entry, "usage": _usage(memory)})
            entries.append(entry)
            set_project_memory(project_path, {**memory, category: entries})
            return json.dumps({"success": True, "operation": "add", "category": category, "entry": entry, "usage": _usage(memory)})

        old_entry = args.get("old_entry", "")
        if old_entry not in entries:
            return _error("Entry not found in category.", memory, category, "Use the complete existing entry text.")
        index = entries.index(old_entry)
        if action == "remove":
            entries.pop(index)
            set_project_memory(project_path, {**memory, category: entries})
            return json.dumps({"success": True, "operation": "remove", "category": category, "usage": _usage(memory)})

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
        return json.dumps({"success": True, "operation": "replace", "category": category, "entry": new_entry, "usage": _usage(memory)})
    except (KeyError, TypeError, ValueError) as exc:
        return _error(str(exc), memory, category, "Review the memory entry and retry.")
