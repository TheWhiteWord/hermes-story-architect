"""story_describe tool — what fields does an entity type expect?

The LLM calls this before creating or completing an entity, so it knows which
questions to ask the user and which fields are worth filling in.

It deliberately does NOT describe the other tools. Tool schemas are already in
the model's context at all times — that is how tool calling works — so repeating
them here spends tokens telling the model something it already knows. Each tool
carries its own `description` instead, which is where the model actually reads it.
"""
import json

from core.constants import ENTITY_SCHEMAS
from core.entity import _RELATION_FIELDS

# Fields stored as rows in `relations` rather than in the entity's own columns/extra.
# The most surprising thing about the model, and invisible unless we say so.
_RELATION_FIELDS_BY_NAME = {field for fields in _RELATION_FIELDS.values() for field in fields}


def _entity_schemas(entity_types: list) -> dict:
    """Field metadata per entity type, flagging relation-backed and computed fields."""
    out = {}
    for entity_type in entity_types:
        fields = {}
        for field, meta in ENTITY_SCHEMAS.get(entity_type, {}).items():
            entry = {
                "type": meta["type"],
                "default": meta["default"],
                "optional": meta.get("optional", True),
                "description": meta["description"],
            }
            if meta.get("computed"):
                entry["computed"] = True
                entry["description"] += " (read-only, computed — do not set)"
            if field in _RELATION_FIELDS_BY_NAME:
                entry["stored_as"] = "relation"
            fields[field] = entry
        out[entity_type] = fields
    return out


SCHEMA = {
    "name": "story_describe",
    "description": "List the fields an entity type expects, with types, defaults and descriptions. "
                   "Call this before creating an entity or asking the user about one, so you know "
                   "which questions are worth asking and which fields are still empty.",
    "type": "object",
    "properties": {
        "entity_type": {
            "type": "string",
            "enum": list(ENTITY_SCHEMAS),
            "description": "Entity type to describe. Omit for all types.",
        }
    },
}


def handler(args: dict, **kwargs) -> str:
    """Return field metadata for the requested entity type(s)."""
    entity_type = args.get("entity_type")

    if entity_type and entity_type not in ENTITY_SCHEMAS:
        return json.dumps({
            "success": False,
            "error": f"Unknown entity_type: {entity_type}. "
                     f"Available: {', '.join(ENTITY_SCHEMAS)}",
        })

    types = [entity_type] if entity_type else list(ENTITY_SCHEMAS)
    return json.dumps({
        "success": True,
        "entity_schemas": _entity_schemas(types),
    })
