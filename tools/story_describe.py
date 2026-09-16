"""story_describe tool — return full schemas for story tools (non-deferred)."""
import json
from core.constants import ENTITY_SCHEMAS


def _all_fields() -> dict:
    """Collect all unique fields across all entity types."""
    all_fields: dict = {}
    for entity_type, fields in ENTITY_SCHEMAS.items():
        for field, meta in fields.items():
            if field not in all_fields:
                all_fields[field] = {
                    "type": meta["type"],
                    "description": meta["description"],
                    "default": meta["default"],
                    "optional": meta.get("optional", True),
                    "_entity_types": [entity_type],
                }
            else:
                all_fields[field]["_entity_types"].append(entity_type)
    return all_fields


def _build_tool_schema(name: str) -> dict:
    """Build schema for a single tool."""
    schemas = {
        "story_create": {
            "name": "story_create",
            "description": "Create new entity notes (characters, locations, worlds, plots, scenes, sequences, acts, projects).",
            "parameters": {
                "type": "object",
                "properties": {
                    "entity_type": {
                        "type": "string",
                        "enum": list(ENTITY_SCHEMAS.keys()),
                        "description": "Type of entity to create",
                    },
                    "slug": {
                        "type": "string",
                        "description": "Entity slug (unique identifier, used as filename)",
                    },
                    "project": {
                        "type": "string",
                        "description": "Project slug or path",
                    },
                    "frontmatter": {
                        "type": "object",
                        "description": "Frontmatter fields. Only include fields relevant to your entity type.",
                        "properties": {
                            field: {
                                "type": meta["type"],
                                "description": f"{meta['description']} (default: {meta['default']})",
                            }
                            for field, meta in _all_fields().items()
                        },
                    },
                },
                "required": ["entity_type", "slug", "project", "frontmatter"],
            },
        },
        "story_load": {
            "name": "story_load",
            "description": "Load a story project's index and memory into context.",
            "parameters": {
                "type": "object",
                "properties": {
                    "project": {
                        "type": "string",
                        "description": "Project slug or name",
                    },
                },
                "required": ["project"],
            },
        },
        "story_index": {
            "name": "story_index",
            "description": "Regenerate the project index from existing files. Errors if project.md or memory.md are missing.",
            "parameters": {
                "type": "object",
                "properties": {
                    "project": {
                        "type": "string",
                        "description": "Project slug or name",
                    },
                },
                "required": ["project"],
            },
        },
        "story_retrieve": {
            "name": "story_retrieve",
            "description": "Get specific sections from a note.",
            "parameters": {
                "type": "object",
                "properties": {
                    "entity_type": {
                        "type": "string",
                        "enum": list(ENTITY_SCHEMAS.keys()),
                        "description": "Type of entity",
                    },
                    "slug": {
                        "type": "string",
                        "description": "Entity slug",
                    },
                    "project": {
                        "type": "string",
                        "description": "Project slug or path",
                    },
                    "sections": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Section names to retrieve",
                    },
                },
                "required": ["entity_type", "slug", "project", "sections"],
            },
        },
        "story_search": {
            "name": "story_search",
            "description": "Search across project notes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query",
                    },
                    "project": {
                        "type": "string",
                        "description": "Project slug or path",
                    },
                },
                "required": ["query", "project"],
            },
        },
        "story_edit": {
            "name": "story_edit",
            "description": "Edit story entities and memory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["edit_note", "delete_entity", "update_story_memory", "reorder"],
                        "description": "Edit action",
                    },
                    "target": {
                        "type": "object",
                        "description": "Target entity (entity_type, slug, project)",
                    },
                    "data": {
                        "type": "object",
                        "description": "Key-value pairs for edits (frontmatter fields or body sections)",
                    },
                    "order_context": {
                        "type": "object",
                        "description": "For reorder action: {ordered_ids: [...]}",
                    },
                    "summary": {
                        "type": "string",
                        "description": "Summary of changes",
                    },
                },
                "required": ["action", "target"],
            },
        },
        "story_dashboard": {
            "name": "story_dashboard",
            "description": "Open the story dashboard in the preview pane.",
            "parameters": {
                "type": "object",
                "properties": {
                    "project": {
                        "type": "string",
                        "description": "Project slug or name",
                    },
                },
                "required": ["project"],
            },
        },
    }
    return schemas.get(name)


SCHEMA = {
    "type": "object",
    "properties": {
        "tools": {
            "type": "array",
            "items": {
                "type": "string",
                "enum": ["story_create", "story_load", "story_index", "story_retrieve", "story_search", "story_edit", "story_dashboard"],
            },
            "description": "Tool names to describe. Omit for all tools.",
        },
        "entity_type": {
            "type": "string",
            "enum": list(ENTITY_SCHEMAS.keys()),
            "description": "Describe fields for a specific entity type. Omit for all entities.",
        },
    },
}


def handler(args: dict, **kwargs) -> str:
    """Return full schemas for story tools, optionally filtered."""
    tool_names = args.get("tools")
    entity_type_filter = args.get("entity_type")

    # Build tool schemas
    if tool_names:
        tools = {}
        for name in tool_names:
            schema = _build_tool_schema(name)
            if schema:
                tools[name] = schema
    else:
        tools = {name: _build_tool_schema(name) for name in
                 ["story_create", "story_load", "story_index", "story_retrieve",
                  "story_search", "story_edit", "story_dashboard"]
                 if _build_tool_schema(name)}

    # Build entity schemas
    if entity_type_filter:
        entity_schemas = {
            entity_type_filter: {
                field: {
                    "type": meta["type"],
                    "default": meta["default"],
                    "optional": meta.get("optional", True),
                    "description": meta["description"],
                }
                for field, meta in ENTITY_SCHEMAS[entity_type_filter].items()
            }
        } if entity_type_filter in ENTITY_SCHEMAS else {}
    else:
        entity_schemas = {
            entity_type: {
                field: {
                    "type": meta["type"],
                    "default": meta["default"],
                    "optional": meta.get("optional", True),
                    "description": meta["description"],
                }
                for field, meta in fields.items()
            }
            for entity_type, fields in ENTITY_SCHEMAS.items()
        }

    return json.dumps({
        "success": True,
        "tools": tools,
        "entity_schemas": entity_schemas,
    })
