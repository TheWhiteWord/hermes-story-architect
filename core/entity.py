"""Entity extraction, validation, and DB column/relation mapping."""
import json
import frontmatter
from pathlib import Path
from .constants import (
    REQUIRED_FIELDS, ENTITY_SCHEMAS, VALID_ROLES, VALID_STATUSES,
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

    _validate_shapes(entity_type, frontmatter, warnings)

    if entity_type == "character":
        if "story_role" in frontmatter and frontmatter["story_role"] not in VALID_ROLES:
            warnings.append(f"Invalid story_role: {frontmatter['story_role']}")
        _validate_enum(frontmatter, "arc_type", ARC_TYPES, warnings, empty_ok=True)
        _validate_enum(frontmatter, "character_value_at_open", VALUE_CHARGES, warnings, empty_ok=True)
        _validate_enum(frontmatter, "character_value_at_close", VALUE_CHARGES, warnings, empty_ok=True)

    if entity_type == "plot" and "status" in frontmatter:
        if frontmatter["status"] not in VALID_STATUSES:
            warnings.append(f"Invalid status: {frontmatter['status']}")
        _validate_enum(frontmatter, "plot_type", PLOT_TYPES, warnings, empty_ok=True)
        _validate_enum(frontmatter, "plot_scope", PLOT_SCOPES, warnings, empty_ok=True)
        _validate_enum(frontmatter, "value_arc", VALUE_ARCS, warnings, empty_ok=True)

    if entity_type == "project":
        _validate_enum(frontmatter, "story_value_at_open", VALUE_CHARGES, warnings, empty_ok=True)
        _validate_enum(frontmatter, "story_value_at_close", VALUE_CHARGES, warnings, empty_ok=True)
        _validate_enum(frontmatter, "structure_type", STRUCTURE_TYPES, warnings, empty_ok=True)

    if entity_type == "scene":
        _validate_enum(frontmatter, "status", SCENE_STATUSES, warnings)
        _validate_enum(frontmatter, "time_of_day", SCENE_TIMES_OF_DAY, warnings, empty_ok=True)
        _validate_enum(frontmatter, "dramatic_role", SCENE_DRAMATIC_ROLES, warnings, empty_ok=True)
        _validate_enum(frontmatter, "value_at_open", VALUE_CHARGES, warnings, empty_ok=True)
        _validate_enum(frontmatter, "value_at_close", VALUE_CHARGES, warnings, empty_ok=True)
        _validate_numeric(frontmatter, "order", warnings)
        _validate_y(frontmatter, warnings)

    if entity_type == "sequence":
        _validate_enum(frontmatter, "status", SEQUENCE_STATUSES, warnings)
        _validate_enum(frontmatter, "value_at_open", VALUE_CHARGES, warnings, empty_ok=True)
        _validate_enum(frontmatter, "value_at_close", VALUE_CHARGES, warnings, empty_ok=True)
        _validate_numeric(frontmatter, "order", warnings)

    if entity_type == "act":
        _validate_enum(frontmatter, "status", ACT_STATUSES, warnings)
        _validate_enum(frontmatter, "value_at_open", VALUE_CHARGES, warnings, empty_ok=True)
        _validate_enum(frontmatter, "value_at_close", VALUE_CHARGES, warnings, empty_ok=True)
        _validate_enum(frontmatter, "structure_type", STRUCTURE_TYPES, warnings, empty_ok=True)
        _validate_numeric(frontmatter, "order", warnings)

    if entity_type == "arc_beat":
        _validate_numeric(frontmatter, "order", warnings)
        _validate_enum(frontmatter, "character_value_at_open", VALUE_CHARGES, warnings, empty_ok=True)
        _validate_enum(frontmatter, "character_value_at_close", VALUE_CHARGES, warnings, empty_ok=True)
        _validate_y(frontmatter, warnings)

    if entity_type == "relationship":
        chars = frontmatter.get("characters", [])
        if len(chars) != 2:
            warnings.append(f"relationship requires exactly 2 characters, got {len(chars)}")
        perspectives = frontmatter.get("perspectives", {})
        # _validate_shapes has already reported a wrong type; iterating it here
        # would raise on the very value we just complained about, and the agent
        # would get a traceback instead of the finding.
        if not isinstance(perspectives, dict):
            perspectives = {}
        for char in chars:
            if char not in perspectives:
                warnings.append(f"Missing perspective for character: {char}")
        for char, p in perspectives.items():
            if "strength" in p and isinstance(p["strength"], (int, float)):
                if not (-1.0 <= float(p["strength"]) <= 1.0):
                    warnings.append(f"strength out of range for {char}: {p['strength']}")

    return warnings


def _validate_shapes(entity_type: str, frontmatter: dict, warnings: list[str]) -> None:
    """A field that declares a shape must actually hold it.

    Six fields declare `sub_fields`, and everything downstream trusts that: a
    `perspectives` string makes `.items()` raise, and a `setups` string is
    iterated one *character* at a time into relation rows — eight rows pointing
    at `' '`, `'e'`, `'f'` for the plot "the first scene". Both were measured,
    and both are silent until something downstream trips.

    Checked here, at stage time, because that is the last point where the agent
    is still looking at a preview and can be told what is wrong.
    """
    for field, meta in ENTITY_SCHEMAS.get(entity_type, {}).items():
        sub = meta.get("sub_fields")
        if not sub or field not in frontmatter:
            continue
        value = frontmatter[field]
        keys = ", ".join(sub)
        if meta["type"] == "list":
            if not isinstance(value, list):
                warnings.append(
                    f"{field} must be a list of objects with keys [{keys}] "
                    f"— got {type(value).__name__}")
            elif any(not isinstance(i, dict) for i in value):
                warnings.append(
                    f"{field} must be a list of objects with keys [{keys}] "
                    f"— got a list containing a non-object")
        elif not isinstance(value, dict):
            warnings.append(
                f"{field} must be an object with keys [{keys}] "
                f"— got {type(value).__name__}")


def _validate_enum(frontmatter: dict, field: str, valid: list[str], warnings: list[str], empty_ok: bool = False) -> None:
    """Append warning if frontmatter[field] is present and not in valid (unless empty_ok and empty)."""
    if field not in frontmatter:
        return
    val = frontmatter[field]
    if empty_ok and val == "":
        return
    if val not in valid:
        warnings.append(f"Invalid {field}: {val}")


def _validate_y(frontmatter: dict, warnings: list[str]) -> None:
    """Append warnings if `y` is present, non-numeric, or outside -1.0…+1.0.

    Every entity carrying a charge curve has a `y`, so the range check lives
    here rather than being repeated per entity type.
    """
    if "y" not in frontmatter:
        return
    _validate_numeric(frontmatter, "y", warnings)
    y_val = frontmatter["y"]
    if isinstance(y_val, (int, float)) and not (-1.0 <= float(y_val) <= 1.0):
        warnings.append(f"y out of range: {y_val} (must be -1.0 to +1.0)")


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

# Relation kinds stored from the OTHER side: a scene's cast rows point AT the
# scene (`from_id=character, to_id=scene`), so a scene does not own them.
# The importer, every existing row, and every reader (story_retrieve,
# story_export, core/db.py) assume this direction; writing it the other way
# left the cast unreadable the moment a scene was authored through story_draft.
# Single authority — relation_endpoints() is the only place direction is decided.
REVERSED_RELATION_KINDS = {"character_scene"}


def relation_endpoints(owner_id: str, kind: str, to_id: str) -> tuple[str, str]:
    """(from_id, to_id) for one relation row, honouring the stored direction."""
    if kind in REVERSED_RELATION_KINDS:
        return to_id, owner_id
    return owner_id, to_id


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


def _is_empty(value, default) -> bool:
    """True when a field holds nothing worth showing.

    Three cases, all of which really are "not set by the user":
      * the schema default — which for a few fields is a real value rather than
        an empty one (project.screenplay_title is "Default"), so a field sitting
        on it holds nothing the user chose;
      * an empty string, list or dict — a field the user deliberately cleared;
      * None.

    Since B12 an unfilled field is stored empty, so the second case is the one
    that fires for prose fields; the first is still load-bearing for the
    defaults that are 0, False, [] or a real value.
    """
    if value is None:
        return True
    if isinstance(value, (str, list, dict)) and len(value) == 0:
        return True
    return value == default


def unfilled_fields(entity_type: str, extra: dict) -> list[str]:
    """Return list of optional field names that hold no user-supplied value.

    Sub-field rule (generalized, driven by `sub_fields` in ENTITY_SCHEMAS):
    - Parent empty → report parent name (e.g. `perspectives`, `setups`)
    - Parent present, object type → report missing expected keys as
      `parent.key` (e.g. `perspectives.kael`). Expected keys come from
      `characters` — the only object-sub_fields field today.
    - Parent present, list type → no per-entry tracking (an entry existing
      = filled; entry notes are optional prose)
    """
    from .constants import ENTITY_SCHEMAS
    schema = ENTITY_SCHEMAS.get(entity_type, {})
    unfilled = []
    for field, meta in schema.items():
        # Skip computed fields — derived at read time, not persisted
        if meta.get("computed"):
            continue
        # variant_of is empty ON a base location or world — that is what a base
        # one is. Reporting it is noise: every project would carry the gap
        # forever and filling it means inventing a parent that does not exist.
        if field == "variant_of":
            continue
        # status: workflow state, always emitted, never "unfilled"
        # boolean/number: binary or scalar values, not "unfilled"
        if (field == "status"
                or not meta.get("optional", True)
                or meta["type"] in ("boolean", "number")):
            continue
        value = extra.get(field, meta["default"])
        if "sub_fields" in meta and not _is_empty(value, meta["default"]):
            if meta["type"] == "object":
                # Report missing expected entries as parent.key
                expected = extra.get("characters", [])
                for key in expected:
                    if key not in value:
                        unfilled.append(f"{field}.{key}")
            # list type: parent present → filled, no per-entry tracking
            continue
        if _is_empty(value, meta["default"]):
            unfilled.append(field)
    return unfilled


def standard_sections(entity_type: str) -> list[str]:
    """Standard body sections for an entity type."""
    sections = {
        "project": ["Premise", "Spine", "Controlling Idea", "Value Arc", "Structure", "Genre", "Notes"],
        "character": ["Identity", "Desires", "Background", "Contradictions", "Psychology", "Arc", "Relationships", "Voice", "Notes"],
        "location": ["Description", "Atmosphere", "Image System", "History", "Dramatic Function", "Notes"],
        "world": ["Description", "History", "Livelihood", "Power", "Rituals", "Values", "Conflict", "Notes"],
        "plot": ["Summary", "Role", "Threads", "Value", "Characters", "Notes"],
        "scene": ["Content", "Objective", "Conflict", "Beats", "Value Turn", "Dramatic Function", "Production", "Notes"],
        "sequence": ["Summary", "Purpose", "Value Arc", "Progression", "Sequence Climax", "Plots", "Notes"],
        "act": ["Summary", "Objective", "Value Arc", "Reversal", "Notes"],
        "arc_beat": ["Action", "The Gap", "Choice", "Value Shift", "Notes"],
        "relationship": ["Nature", "Perspectives", "Tension", "History", "Scenes to Write", "Notes"],
    }
    return sections.get(entity_type, [])


def coerce_number(value):
    """A `number` field as a number, whatever arrived.

    `extra` is a JSON blob and does not enforce types, so a value arriving as
    '3' is stored as '3' and later breaks any reader that compares it — the
    dashboard's `max()` on `act_count` raised and took the whole view down.

    Lives here because `columns_for_insert` is the one place every write path
    passes through, so a third path cannot forget it. A value that is not a
    number is returned as-is: validation reports it, and a wrong value the
    reader can see beats a plausible one it cannot.
    """
    if not isinstance(value, str):
        return value
    try:
        return int(value) if value.strip().lstrip("-").isdigit() else float(value)
    except ValueError:
        return value


def columns_for_insert(entity_type: str, slug: str, fm: dict) -> dict:
    """Map frontmatter to entity columns for INSERT.

    Returns dict with keys: id, type, name, one_sentence, order_key,
    status, parent_id, location_id, extra.
    """
    column_map = ENTITY_COLUMN_MAP.get(entity_type, {})
    relation_fields = _RELATION_FIELDS.get(entity_type, {})
    from .constants import ENTITY_SCHEMAS
    schema = ENTITY_SCHEMAS.get(entity_type, {})

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
        if schema.get(key, {}).get("type") == "number":
            value = coerce_number(value)
        if key in column_map:
            columns[column_map[key]] = value
        else:
            extra[key] = value

    # Arc: the character link is the parent_id column, set from the frontmatter
    # field. It never came from the id, so a beat's id is simply its own slug.
    if entity_type == "arc_beat":
        columns["parent_id"] = fm.get("character") or None

    columns["extra"] = json.dumps(extra) if extra else "{}"
    return columns


def location_scene_relations(scene_id: str, location_id) -> list[dict]:
    """The `location_scene` rows implied by a scene's location.

    `scene.location` is stored twice: in the `location_id` column (what the
    schema declares) and in a `location_scene` relation, which is its reverse
    index — the same fact pointing the other way. Four readers in core/db.py
    use the relation; the column alone leaves them all blind, so a location
    looks orphaned while three scenes depend on it (B8).

    Only the importer ever wrote these. Scenes authored through story_draft
    wrote the column alone, so the relation was stale or absent.

    Direction note: this is `from_id=location, to_id=scene`, the opposite of
    `character_scene` (from the scene to the character). That inconsistency is
    pre-existing and every reader inverts accordingly; changing it is a
    migration, not a fix, so it stays.

    A scene with no location yields nothing — and re-setting the relation to
    empty is the caller's job, since clearing is different from not setting.
    """
    if not location_id:
        return []
    return [{
        "from_id": str(location_id),
        "to_id": scene_id,
        "kind": "location_scene",
        "note": "",
        "order": 1,
    }]


def relations_for_insert(entity_type: str, slug: str, fm: dict) -> list[dict]:
    """Build relation rows from frontmatter for INSERT.

    Returns list of dicts with keys: from_id, to_id, kind, note, order.
    """
    relation_fields = _RELATION_FIELDS.get(entity_type, {})
    relations = []

    # A scene's location is a column AND a reverse-index relation. See
    # location_scene_relations for why both exist.
    if entity_type == "scene":
        relations += location_scene_relations(slug, fm.get("location"))

    for field, (kind, is_list) in relation_fields.items():
        value = fm.get(field, [])
        if not value:
            continue
        if is_list:
            # Guard, not validation: a string here is iterated one character at
            # a time, so `setups: "the first scene"` writes eight relation rows
            # pointing at ' ', 'e', 'f'. Measured. The shape is reported at stage
            # time by _validate_shapes; this stops the garbage reaching the
            # database from any path that skipped that check.
            if not isinstance(value, list):
                continue
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
                    from_id, to_id = relation_endpoints(slug, kind, to_id)
                    relations.append({
                        "from_id": from_id,
                        "to_id": to_id,
                        "kind": kind,
                        "note": note,
                        "order": i + 1,
                    })
        else:
            # Non-list: single string value
            value = fm.get(field)
            if value:
                from_id, to_id = relation_endpoints(slug, kind, str(value))
                relations.append({
                    "from_id": from_id,
                    "to_id": to_id,
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
