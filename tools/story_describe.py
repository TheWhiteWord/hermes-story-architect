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
from core.entity import FIELDS_TO_SKIP, ENTITY_COLUMN_MAP, _RELATION_FIELDS


def _storage_label(entity_type: str, field: str) -> str | None:
    """Where a field actually lives, or None if it is not worth labelling.

    Only *references* get a label — a field that points at another entity.
    Plain values (`name`, `order`, `status`) are columns like every other, and
    saying so for 25 of them is noise that buries the five that matter.

    The label comes from the declared maps, never from the field's NAME. A
    name-based match labelled `plot.characters` and `relationship.characters`
    as relations when both are stored in `extra` — and the agent has no way to
    know the tool was guessing (B4, B5).

    `extra` is the documented home for links that are not on the structural
    spine (see task_20/archived/data_model.md); saying so is the point. A
    denormalized link like `scene.act_id` is redundant on purpose, and telling
    the agent it is `extra` stops it looking for a column that is not there.
    """
    if field in _RELATION_FIELDS.get(entity_type, {}):
        return "relation"
    column = ENTITY_COLUMN_MAP.get(entity_type, {}).get(field)
    if column and column.endswith("_id"):
        return "column"
    return None


def _is_reference(entity_type: str, field: str) -> bool:
    """True when the field's value points at another entity by slug.

    Independent of *where* it is stored. A link in `extra` is still a link, and
    an agent needs to know that before writing a value — the alternative is
    inventing a display name where a slug belongs. The schema's `type` already
    says string or list; this says what the string is.

    The nine `extra` links (scene.act_id, arc_beat.scene, plot.characters,
    relationship.characters/scenes, act/sequence climax_scene_id,
    sequence.primary_plot, project.*_scene_id) are the ones this catches that
    `stored_as` cannot: they have no special storage, and every one of them
    says "slug" in its description. Making that machine-readable rather than
    prose is the same D1 fix as `sub_fields`.
    """
    # A relation field describes its target in prose ("Scenes where plot is
    # established") without saying "slug", so the word is not the test for
    # these. Anything the maps declare is a reference by definition.
    if field in _RELATION_FIELDS.get(entity_type, {}):
        return True
    # A reference column is declared, so it does not need the word either.
    column = ENTITY_COLUMN_MAP.get(entity_type, {}).get(field)
    if column and column.endswith("_id"):
        return True
    # Beyond the declared maps this is a heuristic, and it is the weakest part
    # of this module: it reads the word "slug" out of the description. It
    # misses `relationship.scenes` ("Scenes where this relationship is
    # featured" — no "slug"), so that link is unlabelled. Adding a real
    # `is_reference` flag to ENTITY_SCHEMAS would retire the guess entirely;
    # until then this is a best-effort improvement, not a guarantee.
    meta = ENTITY_SCHEMAS.get(entity_type, {}).get(field, {})
    description = meta.get("description", "").lower()
    if "slug" not in description:
        return False
    # `id` mentions "slug" because it *is* the slug — it is not a reference to
    # another entity, and labelling it one is worse than not labelling it.
    if field in FIELDS_TO_SKIP:
        return False
    return not meta.get("computed")


def _entity_schemas(entity_types: list) -> dict:
    """Field metadata per entity type, flagging relation-backed and computed fields.

    Every key the schema carries is emitted, not a hand-picked few. The
    hand-picked version silently dropped `sub_fields`, which is how a
    `relationship.perspectives` object came to be written as a bare string and
    a plot's `setups` descriptions were discarded on write — the schema knew
    the shape and the tool did not say so. A schema key nobody is shown is a
    schema key that does not exist, and the list of missing ones is only
    discoverable by reading this function. Copy the dict; decorate it.
    """
    out = {}
    for entity_type in entity_types:
        fields = {}
        for field, meta in ENTITY_SCHEMAS.get(entity_type, {}).items():
            entry = dict(meta)
            entry.setdefault("optional", True)
            if meta.get("computed"):
                entry["description"] += " (read-only, computed — do not set)"
            label = _storage_label(entity_type, field)
            if label:
                entry["stored_as"] = label
            if _is_reference(entity_type, field):
                entry["is_reference"] = True
            fields[field] = entry
        out[entity_type] = fields
    return out


SCHEMA = {
    "name": "story_describe",
    "description": "List the fields an entity type expects, with types, defaults and descriptions. "
                   "Call this before creating an entity or asking the user about one, so you know "
                   "which questions are worth asking and which fields are still empty. "
                   "These are the field names to pass to story_draft, and the ones story_load "
                   "returns — an entity's `id` is the `slug` argument of its op.",
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
