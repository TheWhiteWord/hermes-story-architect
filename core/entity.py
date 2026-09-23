"""Entity extraction, validation, and DB column/relation mapping."""
import json
import frontmatter
from pathlib import Path
from .constants import (
    REQUIRED_FIELDS, VALID_ROLES, VALID_STATUSES,
    SCENE_STATUSES, SEQUENCE_STATUSES, ACT_STATUSES,
    SCENE_TIMES_OF_DAY, SCENE_DRAMATIC_ROLES,
    VALUE_CHARGES, STRUCTURE_TYPES, PLOT_TYPES,
    PLOT_SCOPES, VALUE_ARCS, ARC_TYPES,
)
from .section_parser import list_sections


def extract_entity(note_path: Path, entity_type: str) -> dict:
    """Extract entity data from a note file.

    Returns dict with:
    - id: note stem (slug)
    - all frontmatter fields
    - sections: list of ## headings in body
    """
    post = frontmatter.load(note_path)
    body = post.content
    sections = list_sections(body)
    return {
        "id": note_path.stem,
        **dict(post.metadata),
        "sections": sections,
    }


def validate_entity(entity_type: str, frontmatter: dict) -> list[str]:
    """Validate entity frontmatter. Return list of warnings."""
    warnings = []

    for field in REQUIRED_FIELDS.get(entity_type, []):
        if field not in frontmatter:
            warnings.append(f"Missing required field: {field}")

    if entity_type == "character":
        if "story_role" in frontmatter and frontmatter["story_role"] not in VALID_ROLES:
            warnings.append(f"Invalid story_role: {frontmatter['story_role']}")
        _validate_enum(frontmatter, "arc_type", ARC_TYPES, warnings, empty_ok=True)
        _validate_enum(frontmatter, "arc_value_at_open", VALUE_CHARGES, warnings, empty_ok=True)
        _validate_enum(frontmatter, "arc_value_at_close", VALUE_CHARGES, warnings, empty_ok=True)

    if entity_type == "plot" and "status" in frontmatter:
        if frontmatter["status"] not in VALID_STATUSES:
            warnings.append(f"Invalid status: {frontmatter['status']}")
        _validate_enum(frontmatter, "plot_type", PLOT_TYPES, warnings, empty_ok=True)
        _validate_enum(frontmatter, "plot_scope", PLOT_SCOPES, warnings, empty_ok=True)
        _validate_enum(frontmatter, "value_arc", VALUE_ARCS, warnings, empty_ok=True)

    if entity_type == "project":
        _validate_enum(frontmatter, "value_at_open", VALUE_CHARGES, warnings, empty_ok=True)
        _validate_enum(frontmatter, "value_at_close", VALUE_CHARGES, warnings, empty_ok=True)
        _validate_enum(frontmatter, "structure_type", STRUCTURE_TYPES, warnings, empty_ok=True)

    if entity_type == "scene":
        _validate_enum(frontmatter, "status", SCENE_STATUSES, warnings)
        _validate_enum(frontmatter, "time_of_day", SCENE_TIMES_OF_DAY, warnings, empty_ok=True)
        _validate_enum(frontmatter, "dramatic_role", SCENE_DRAMATIC_ROLES, warnings, empty_ok=True)
        _validate_enum(frontmatter, "value_open", VALUE_CHARGES, warnings, empty_ok=True)
        _validate_enum(frontmatter, "value_close", VALUE_CHARGES, warnings, empty_ok=True)
        _validate_numeric(frontmatter, "order", warnings)

    if entity_type == "sequence":
        _validate_enum(frontmatter, "status", SEQUENCE_STATUSES, warnings)
        _validate_enum(frontmatter, "value_open", VALUE_CHARGES, warnings, empty_ok=True)
        _validate_enum(frontmatter, "value_close", VALUE_CHARGES, warnings, empty_ok=True)
        _validate_numeric(frontmatter, "order", warnings)

    if entity_type == "act":
        _validate_enum(frontmatter, "status", ACT_STATUSES, warnings)
        _validate_enum(frontmatter, "value_open", VALUE_CHARGES, warnings, empty_ok=True)
        _validate_enum(frontmatter, "value_close", VALUE_CHARGES, warnings, empty_ok=True)
        _validate_enum(frontmatter, "structure_type", STRUCTURE_TYPES, warnings, empty_ok=True)
        _validate_numeric(frontmatter, "order", warnings)

    if entity_type == "arc_beat":
        _validate_numeric(frontmatter, "y", warnings)
        _validate_numeric(frontmatter, "order", warnings)
        if "y" in frontmatter:
            y_val = frontmatter["y"]
            if isinstance(y_val, (int, float)) and not (-1.0 <= float(y_val) <= 1.0):
                warnings.append(f"y out of range: {y_val} (must be -1.0 to +1.0)")

    if entity_type == "relationship":
        chars = frontmatter.get("characters", [])
        if len(chars) != 2:
            warnings.append(f"relationship requires exactly 2 characters, got {len(chars)}")
        perspectives = frontmatter.get("perspectives", {})
        for char in chars:
            if char not in perspectives:
                warnings.append(f"Missing perspective for character: {char}")
        for char, p in perspectives.items():
            if "strength" in p and isinstance(p["strength"], (int, float)):
                if not (-1.0 <= float(p["strength"]) <= 1.0):
                    warnings.append(f"strength out of range for {char}: {p['strength']}")

    return warnings


def _validate_enum(frontmatter: dict, field: str, valid: list[str], warnings: list[str], empty_ok: bool = False) -> None:
    """Append warning if frontmatter[field] is present and not in valid (unless empty_ok and empty)."""
    if field not in frontmatter:
        return
    val = frontmatter[field]
    if empty_ok and val == "":
        return
    if val not in valid:
        warnings.append(f"Invalid {field}: {val}")


def _validate_numeric(frontmatter: dict, field: str, warnings: list[str]) -> None:
    """Append warning if frontmatter[field] is present and not int/float."""
    if field not in frontmatter:
        return
    if not isinstance(frontmatter[field], (int, float)):
        warnings.append(f"Field {field} must be a number, got {type(frontmatter[field]).__name__}")


def update_sections(note_path: Path, sections: list[str]) -> None:
    """Update the sections field in a note's frontmatter."""
    post = frontmatter.load(note_path)
    post["sections"] = sections
    with open(note_path, 'w') as f:
        frontmatter.dump(post, f)


# ─── DB column/relation mapping (Phase 3) ───

# FM field name → DB column name, per entity type
ENTITY_COLUMN_MAP = {
    "project": {"name": "name", "logline": "one_sentence"},
    "character": {"name": "name", "one_sentence": "one_sentence"},
    "location": {"name": "name", "one_sentence": "one_sentence", "world": "parent_id"},
    "world": {"name": "name", "one_sentence": "one_sentence"},
    "plot": {"name": "name", "one_sentence": "one_sentence", "status": "status"},
    "scene": {"title": "name", "order": "order_key", "status": "status", "sequence_id": "parent_id", "location": "location_id"},
    "sequence": {"title": "name", "order": "order_key", "status": "status", "act_id": "parent_id"},
    "act": {"title": "name", "order": "order_key", "status": "status"},
    "arc_beat": {"label": "name", "order": "order_key", "character": "parent_id"},
    "relationship": {"name": "name", "type": "type", "status": "status"},
}

FIELDS_TO_SKIP = {"id", "type"}

# Fields that become relations rows (not extra JSON or columns)
# Maps field name → (kind, is_list)
_RELATION_FIELDS = {
    "scene": {"characters": ("character_scene", True)},
    "plot": {
        "setups": ("plot_setup", True),
        "crisis": ("plot_crisis", True),
        "climax": ("plot_climax", True),
        "payoffs": ("plot_payoff", True),
    },
    "location": {"variant_of": ("location_variant", False)},
    "world": {"variant_of": ("world_variant", False)},
    "arc_beat": {},
    "relationship": {},
}


def unfilled_fields(entity_type: str, extra: dict) -> list[str]:
    """Return list of optional field names whose value matches the schema default."""
    from .constants import ENTITY_SCHEMAS
    schema = ENTITY_SCHEMAS.get(entity_type, {})
    unfilled = []
    for field, meta in schema.items():
        # Skip computed fields — derived at read time, not persisted
        if meta.get("computed"):
            continue
        # status: workflow state, always emitted, never "unfilled"
        # boolean/number: binary or scalar values, not "unfilled"
        if (field != "status"
            and meta.get("optional", True)
            and meta["type"] not in ("boolean", "number")
            and extra.get(field, meta["default"]) == meta["default"]):
            unfilled.append(field)
    return unfilled


def standard_sections(entity_type: str) -> list[str]:
    """Standard body sections for an entity type."""
    sections = {
        "project": ["Synopsis", "Themes", "Structure", "Notes"],
        "character": ["Personality", "Background", "Voice", "Greatest Fear", "Secrets", "Arc", "Relationships", "Goals"],
        "location": ["Description", "Atmosphere", "Image System", "History", "Dramatic Function"],
        "world": ["Description", "History", "Livelihood", "Power", "Rituals", "Values", "Conflict"],
        "plot": ["Summary", "Obstacles", "Stakes"],
        "scene": ["Description", "Dramatic Function", "Notes", "Content"],
        "sequence": ["Summary", "Scene Order", "Notes"],
        "act": ["Summary", "Thematic Function", "Notes"],
        "arc_beat": ["Action", "Gap", "Choice", "Shift", "Development Log"],
        "relationship": ["Description", "History", "Dynamics", "Scenes", "Notes"],
    }
    return sections.get(entity_type, [])


def columns_for_insert(entity_type: str, slug: str, fm: dict) -> dict:
    """Map frontmatter to entity columns for INSERT.

    Returns dict with keys: id, type, name, one_sentence, order_key,
    status, parent_id, location_id, extra.
    """
    column_map = ENTITY_COLUMN_MAP.get(entity_type, {})
    relation_fields = _RELATION_FIELDS.get(entity_type, {})

    columns = {
        "id": slug,
        "type": entity_type,
        "name": "",
        "one_sentence": "",
        "order_key": 0,
        "status": "",
        "parent_id": None,
        "location_id": None,
    }
    extra = {}

    for key, value in fm.items():
        if key in FIELDS_TO_SKIP:
            continue
        # Arc keeps 'scene' as an extra attribute (which scene the beat occurs in)
        # in addition to the arc_beat relation created separately
        if key in relation_fields and not (entity_type == "arc_beat" and key == "scene"):
            continue  # handled separately as relations
        if key in column_map:
            columns[column_map[key]] = value
        else:
            extra[key] = value

    # Arc: entity_id is composite (character-slug + beat-slug, e.g. "kael-1")
    if entity_type == "arc_beat":
        char_slug = fm.get("character", "")
        columns["id"] = f"{char_slug}-{slug}" if char_slug else slug
        columns["parent_id"] = char_slug or None

    columns["extra"] = json.dumps(extra) if extra else "{}"
    return columns


def relations_for_insert(entity_type: str, slug: str, fm: dict) -> list[dict]:
    """Build relation rows from frontmatter for INSERT.

    Returns list of dicts with keys: from_id, to_id, kind, note, order.
    """
    relation_fields = _RELATION_FIELDS.get(entity_type, {})
    relations = []

    for field, (kind, is_list) in relation_fields.items():
        value = fm.get(field, [])
        if not value:
            continue
        if is_list:
            for i, item in enumerate(value):
                if isinstance(item, dict):
                    if kind in ("plot_setup", "plot_payoff"):
                        to_id = item.get("scene_id", "")
                        note = item.get("description", "")
                    else:
                        to_id = str(item)
                        note = ""
                else:
                    to_id = str(item)
                    note = ""
                if to_id:
                    relations.append({
                        "from_id": slug,
                        "to_id": to_id,
                        "kind": kind,
                        "note": note,
                        "order": i + 1,
                    })
        else:
            # Non-list: single string value
            value = fm.get(field)
            if value:
                relations.append({
                    "from_id": slug,
                    "to_id": str(value),
                    "kind": kind,
                    "note": "",
                    "order": 1,
                })

    return relations


def validate_scene_act_id(project_path, sequence_id: str, act_id: str) -> None:
    """Raise ValueError if sequence's act_id doesn't match the provided act_id."""
    from core.db import get_db
    conn = get_db(project_path)
    try:
        row = conn.execute(
            "SELECT parent_id FROM entities WHERE id=? AND type='sequence'",
            (sequence_id,),
        ).fetchone()
        if row and row[0] and row[0] != act_id:
            raise ValueError(
                f"Sequence {sequence_id} belongs to act {row[0]}, not {act_id}"
            )
    finally:
        conn.close()


def validate_arc_parents(project_path, character: str, scene: str) -> None:
    """Raise ValueError if character or scene doesn't exist in DB."""
    from core.db import get_db
    conn = get_db(project_path)
    try:
        if character:
            row = conn.execute(
                "SELECT id FROM entities WHERE id=? AND type='character'",
                (character,),
            ).fetchone()
            if not row:
                raise ValueError(f"Character not found: {character}")
        if scene:
            row = conn.execute(
                "SELECT id FROM entities WHERE id=? AND type='scene'",
                (scene,),
            ).fetchone()
            if not row:
                raise ValueError(f"Scene not found: {scene}")
    finally:
        conn.close()


def validate_plot_characters(project_path, characters: list) -> None:
    """Raise ValueError if any character slug doesn't exist in DB."""
    from core.db import get_db
    if not characters:
        return
    conn = get_db(project_path)
    try:
        for char_slug in characters:
            row = conn.execute(
                "SELECT id FROM entities WHERE id=? AND type='character'",
                (char_slug,),
            ).fetchone()
            if not row:
                raise ValueError(f"Character not found: {char_slug}")
    finally:
        conn.close()
