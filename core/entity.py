"""Entity extraction, validation, and DB column/relation mapping."""
import json
import frontmatter
from pathlib import Path
from .constants import (
    REQUIRED_FIELDS, ENTITY_SCHEMAS, VALID_ROLES, VALID_STATUSES,
    SCENE_STATUSES, SEQUENCE_STATUSES, ACT_STATUSES,
    SCENE_TIMES_OF_DAY, SCENE_DRAMATIC_ROLES,
    VALUE_CHARGES, STRUCTURE_TYPES, PLOT_TYPES,
    PLOT_SCOPES, VALUE_ARCS, ARC_TYPES, PLOT_ROLES,
    CONFLICT_LEVELS, VALUE_LADDER,
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

    for field, meta in ENTITY_SCHEMAS.get(entity_type, {}).items():
        if meta.get("sub_fields") and field in frontmatter:
            _validate_field(entity_type, field, frontmatter[field], meta, warnings)

    if entity_type == "character":
        # `empty_ok` like the four enum checks below: since B12 an unfilled
        # field is stored empty, so an exported note carries `story_role: ''`
        # and the write path accepts it. Without this the importer refused
        # exactly what story_export writes, and a DB -> markdown -> DB
        # round-trip failed while the write path stored the same value.
        _validate_enum(frontmatter, "story_role", VALID_ROLES, warnings, empty_ok=True)
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
        _validate_enum(frontmatter, "structure_type", STRUCTURE_TYPES, warnings, empty_ok=True)

    if entity_type == "scene":
        _validate_enum(frontmatter, "status", SCENE_STATUSES, warnings)
        _validate_enum(frontmatter, "time_of_day", SCENE_TIMES_OF_DAY, warnings, empty_ok=True)
        _validate_enum(frontmatter, "dramatic_role", SCENE_DRAMATIC_ROLES, warnings, empty_ok=True)
        _validate_numeric(frontmatter, "order", warnings)

    if entity_type == "sequence":
        _validate_enum(frontmatter, "status", SEQUENCE_STATUSES, warnings)
        _validate_numeric(frontmatter, "order", warnings)

    if entity_type == "act":
        _validate_enum(frontmatter, "status", ACT_STATUSES, warnings)
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


# The problems above fall into two kinds, and only one of them is fatal to an
# import. Naming them here beats having the importer pattern-match the English:
# a reworded message would otherwise silently change which checks run.
#
#   VALUE       — a stored value outside the declared vocabulary or range. No
#                 later pass fixes it, and it is written as-is, so a note
#                 carrying one must be refused rather than imported.
#   STRUCTURE   — a build-order constraint: a required field not yet written, a
#                 relationship still missing one of its two perspectives. An
#                 import creates every entity in one pass and a note is allowed
#                 to be mid-shape, so these are the author's business and not
#                 the importer's to enforce.
STRUCTURAL_WARNINGS = ("Missing required field", "relationship requires",
                       "Missing perspective")


def value_problems(entity_type: str, frontmatter: dict) -> list[str]:
    """Only the VALUE problems from `validate_entity` — see STRUCTURAL_WARNINGS.

    This is what a write path and an import both refuse on: a value the schema
    does not allow. Returning the list rather than raising keeps
    `validate_entity`'s warning contract intact for its other callers.
    """
    return [w for w in validate_entity(entity_type, frontmatter)
            if not w.startswith(STRUCTURAL_WARNINGS)]


# ─── Shape validation ───

# The Python type each declared sub-field `type` means. A `boolean` is listed
# because `secret` is one; `int` is not accepted where `number` is declared,
# so a count is a float like everything else in a JSON blob.
_SUBFIELD_TYPES = {
    "string": str,
    "number": (int, float),
    "boolean": bool,
}


def _validate_field(entity_type: str, field: str, value, meta: dict,
                    warnings: list[str], path: str = "") -> None:
    """A field that declares `sub_fields` must hold them, at every depth.

    The declaration is one form: a `{type, description}` sub-field dict, plus
    optional `required`, `enum`, `ref` and nested `sub_fields`. This walks the
    value against it — container type, entries being objects, required keys,
    scalar types, enum membership — and recurses into nested `sub_fields`.

    The container message is unchanged on purpose: it names the keys, which is
    what lets an agent fix the value without a lookup. Per-entry findings carry
    the path, so a nested one is findable by index rather than by reading the
    whole field back.

    `object` has two shapes, told apart by `keyed`:
      * `keyed: True` (relationship.perspectives) — a map keyed by entity:
        the keys are the entities and the values carry the declarations'
        subjects, so the sub-fields apply to each VALUE.
      * otherwise (a turn's inline `schema`) — a fixed record: the sub-fields
        are the keys of the object itself, so they apply to the dict once.
    """
    sub_fields = meta.get("sub_fields") or {}
    keys = ", ".join(sub_fields)
    at = f"{field}" if not path else f"{path}.{field}"

    if meta["type"] == "list":
        if not isinstance(value, list):
            warnings.append(
                f"{at} must be a list of objects with keys [{keys}] "
                f"— got {type(value).__name__}")
            return
        for i, entry in enumerate(value):
            entry_at = f"{at}[{i}]"
            if not isinstance(entry, dict):
                warnings.append(
                    f"{at} must be a list of objects with keys [{keys}] "
                    f"— got a list containing a non-object")
                continue
            for key, key_meta in sub_fields.items():
                _validate_sub_field(entry_at, entry, key, key_meta, warnings)
    elif meta["type"] == "object":
        if not isinstance(value, dict):
            warnings.append(
                f"{at} must be an object with keys [{keys}] "
                f"— got {type(value).__name__}")
            return
        if meta.get("keyed"):
            # A map keyed by entity (perspectives): the keys are the entities
            # and the values carry the declarations' subjects, so the sub-
            # fields apply to each VALUE.
            for key_name, entry in value.items():
                entry_at = f"{at}.{key_name}"
                if not isinstance(entry, dict):
                    warnings.append(
                        f"{at} must be an object with keys [{keys}] "
                        f"— {key_name} holds a {type(entry).__name__}")
                    continue
                for key, key_meta in sub_fields.items():
                    _validate_sub_field(entry_at, entry, key, key_meta, warnings)
        else:
            # A fixed record (an inline `schema`): the sub-fields are the
            # keys of the object itself, so they apply to the dict once.
            for key, key_meta in sub_fields.items():
                _validate_sub_field(at, value, key, key_meta, warnings)


def _validate_sub_field(path: str, entry: dict, key: str, meta: dict,
                        warnings: list[str]) -> None:
    """One declared key inside one entry: required, type, enum, recursion."""
    at = f"{path}.{key}"
    if key not in entry:
        if meta.get("required"):
            warnings.append(f"{at} is required")
        return
    value = entry[key]
    if "enum" in meta and value not in meta["enum"]:
        warnings.append(
            f"{at} must be one of: {', '.join(meta['enum'])} — got {value!r}")
    declared = meta.get("type")
    if meta.get("sub_fields"):
        _validate_field("", key, value, meta, warnings, path=path)
    elif declared in _SUBFIELD_TYPES and not isinstance(value, _SUBFIELD_TYPES[declared]):
        warnings.append(
            f"{at} must be a {declared} — got {type(value).__name__}")


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

    Only arc_beat carries a curve now (a scene's turn is `value_turns`), so the
    range check lives here rather than being repeated per entity type.
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
        frontmatter.dump(post, f, sort_keys=False)


# ─── DB column/relation mapping (Phase 3) ───

# FM field name → DB column name, per entity type
ENTITY_COLUMN_MAP = {
    "project": {"name": "name", "logline": "one_sentence"},
    "character": {"name": "name", "one_sentence": "one_sentence"},
    "location": {"name": "name", "one_sentence": "one_sentence", "world": "parent_id"},
    "world": {"name": "name", "one_sentence": "one_sentence"},
    "plot": {"name": "name", "one_sentence": "one_sentence", "status": "status"},
    "scene": {"title": "name", "one_sentence": "one_sentence", "order": "order_key", "status": "status", "sequence_id": "parent_id", "location": "location_id"},
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


def relation_entry(item) -> tuple[str, str]:
    """(to_id, note) from one relation field entry — a dict or a bare slug.

    Two shapes serve the same fields: `character_scene` holds plain slugs,
    the plot beat lists hold `{scene_id, description}`. Both reach the same
    loop, so the unwrap lives here once. Role-agnostic on purpose — no kind
    gets its own rule, which is what made a plot create write the dict repr
    into to_id for two of the four roles.

    A dict without a usable `scene_id` yields `("", "")` and the caller drops
    the row: a relation naming a scene that was never identified is not a fact.
    """
    if isinstance(item, dict):
        return str(item.get("scene_id") or ""), str(item.get("description") or "")
    return str(item), ""


# Fields that become relations rows (not extra JSON or columns)
# Maps field name → (kind, is_list)
_RELATION_FIELDS = {
    "scene": {"characters": ("character_scene", True)},
    "plot": {
        "setups": ("plot_setup", True),
        "inciting_incident": ("plot_inciting_incident", True),
        "complications": ("plot_complication", True),
        "crisis": ("plot_crisis", True),
        "climax": ("plot_climax", True),
        "resolutions": ("plot_resolution", True),
    },
    "location": {"variant_of": ("location_variant", False)},
    "world": {"variant_of": ("world_variant", False)},
    "arc_beat": {},
    "relationship": {},
}

# Plot beat fields → relation kinds, read from the map above rather than
# restated. Every reader (db reads, import, export) iterates this; adding a role
# is one edit to `_RELATION_FIELDS` plus `PLOT_ROLES` in constants.
PLOT_BEAT_FIELDS = {field: kind for field, (kind, _) in _RELATION_FIELDS["plot"].items()}

# Relation-stored fields the map above cannot express: `plot_roles` is ONE
# field to SIX kinds (the entry's `role` picks the kind), so it is written
# and read by bespoke blocks — see plot_role_relations.
#
# It is listed separately rather than inside `_RELATION_FIELDS` precisely
# because putting it there would make the generic loop write rows of a kind
# that does not exist. But it is still relation storage and not `extra`, so
# every site that splits those two apart has to know about it — hence
# relation_fields(), which is the one place to ask.
BESPOKE_RELATION_FIELDS = {"scene": {"plot_roles"}}


def relation_fields(entity_type: str) -> dict:
    """Every relation-stored field of a type: the generic map, plus the
    bespoke one-field-to-many-kinds fields."""
    return {**_RELATION_FIELDS.get(entity_type, {}),
            **{f: None for f in BESPOKE_RELATION_FIELDS.get(entity_type, set())}}


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


def unfilled_fields(entity_type: str, extra: dict, row: dict | None = None) -> list[str]:
    """Return list of optional field names that hold no user-supplied value.

    `row` is the entity's DB row. It is optional so the many callers that only
    have the `extra` blob keep working, but every caller that HAS the row
    should pass it: four fields live in columns rather than in `extra`, and
    without the row this function cannot see them and reports them as gaps
    while the same field is returned with a real value one call earlier.

    That is not a cosmetic disagreement. `project.logline`, `plot.one_sentence`,
    `location.world` and `scene.location` were all reported unfilled on live
    data that had them filled — an author reading the unfilled view is told to
    write something they already wrote.

    `extra` is not mutated; the columns are layered on a copy.

    Sub-field rule (generalized, driven by `sub_fields` in ENTITY_SCHEMAS):
    - Parent empty → report parent name (e.g. `perspectives`, `setups`)
    - Parent present, object type, `keyed` → report missing expected keys as
      `parent.key` (e.g. `perspectives.kael`). Expected keys come from
      `characters` — the only keyed object-sub_fields field today.
    - Parent present, list type or a fixed-record object → no per-entry
      tracking (an entry existing = filled; entry notes are optional prose)
    """
    from .constants import ENTITY_SCHEMAS
    if row:
        # Layer the column-backed fields over `extra`. `extra` wins on a
        # collision: it is the newer value if a field ever moves out of a
        # column, and a stale column must not shadow what was just written.
        extra = {**{f: row.get(col) for f, col in
                    ENTITY_COLUMN_MAP.get(entity_type, {}).items()},
                **extra}
    schema = ENTITY_SCHEMAS.get(entity_type, {})
    unfilled = []
    for field, meta in schema.items():
        # A computed field is derived at read time and not persisted, so it has
        # no stored value to be missing. It is still reported when it is a
        # plot's dramatic role: setups/crisis/climax/complications/resolutions
        # are the plot's content, and a plot whose crisis is unfulfilled is
        # exactly the gap an author needs told about. The caller feeds derived
        # values in through `extra` (see story_retrieve._unfilled), so an
        # absent key and an empty one both read as unfulfilled — which is what
        # "this plot has no crisis scene" should say.
        #
        # Other computed fields (a scene's arc_beats_list, a character's
        # relationships) are summaries of entities that exist elsewhere and are
        # reported there, so they stay out.
        if meta.get("computed") and field not in _RELATION_FIELDS.get(entity_type, {}):
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
            if meta["type"] == "object" and meta.get("keyed"):
                # Report missing expected entries as parent.key. Expected
                # keys come from `characters` — the only keyed object field
                # today.
                expected = extra.get("characters", [])
                for key in expected:
                    if key not in value:
                        unfilled.append(f"{field}.{key}")
            # list type (and a fixed-record object): parent present → filled,
            # no per-entry tracking
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
    rel_fields = relation_fields(entity_type)
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
        if key in rel_fields and not (entity_type == "arc_beat" and key == "scene"):
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


def plot_role_relations(scene_id: str, entries) -> list[dict]:
    """The `plot_<role>` rows implied by a scene's `plot_roles`.

    A plot role is WRITTEN on the scene and READ on the plot, so the agent
    never reopens a plot to add a scene to it. The row is still owned by the
    plot (`from_id=plot, to_id=scene`) because every reader in the codebase
    keys off that direction, and flipping it would rewrite eight of them for
    no added capability.

    Bespoke by necessity: `_RELATION_FIELDS` maps one field to ONE kind, and
    this is one field to six — the entry's `role` picks the kind. The generic
    loop in `relations_for_insert` cannot express that.

    An entry with no plot, or a role outside PLOT_ROLES, yields no row: the
    validator refuses both before this runs, so a row reaching here without
    them is a shape the caller should not have passed.
    """
    if not isinstance(entries, list):
        return []
    rows = []
    for i, entry in enumerate(entries, 1):
        if not isinstance(entry, dict):
            continue
        plot = str(entry.get("plot") or "")
        role = str(entry.get("role") or "")
        if not plot or role not in PLOT_ROLES:
            continue
        rows.append({
            "from_id": plot,
            "to_id": scene_id,
            "kind": f"plot_{role}",
            "note": str(entry.get("description") or ""),
            "order": i,
        })
    return rows


def relations_for_insert(entity_type: str, slug: str, fm: dict) -> list[dict]:
    """Build relation rows from frontmatter for INSERT.

    Returns list of dicts with keys: from_id, to_id, kind, note, order.
    """
    # `_RELATION_FIELDS`, not relation_fields(): a bespoke field has no single
    # kind, and this loop is the one-field-to-one-kind writer that cannot
    # express it. The scene branch below calls plot_role_relations directly.
    relation_fields = _RELATION_FIELDS.get(entity_type, {})
    relations = []

    # A scene's location is a column AND a reverse-index relation. See
    # location_scene_relations for why both exist.
    if entity_type == "scene":
        relations += location_scene_relations(slug, fm.get("location"))
        # One field, six kinds — see plot_role_relations for why this is
        # outside the loop below.
        relations += plot_role_relations(slug, fm.get("plot_roles"))

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
                to_id, note = relation_entry(item)
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


def validate_scene_location(project_path, location: str) -> None:
    """Raise ValueError if a scene names a location that doesn't exist.

    A scene may carry free text in `location` while the story is still being
    shaped, but the value has to resolve to a location record: a place that is
    only ever named in scenes holds no mood, image system or history, and the
    scenes cannot reach anything it has. An empty location is a scene
    deliberately placed nowhere, and is left alone.

    Reads committed state, so a location created in the same draft is visible:
    commit applies a draft's ops one at a time, creates before edits, each
    committed before the next.
    """
    if not location:
        return
    from core.db import get_db
    conn = get_db(project_path)
    try:
        row = conn.execute(
            "SELECT id FROM entities WHERE id=? AND type='location'",
            (location,),
        ).fetchone()
        if not row:
            raise ValueError(f"Location not found: {location}")
    finally:
        conn.close()


def _collect_refs(meta: dict, value, path: str, refs: list) -> None:
    """Every `(ref_type, target, path)` a sub_fields declaration names.

    Walks the value the way `_validate_field` does, so the paths in a
    reference error match the paths in a shape finding — an agent fixing
    `plot_roles[1].plot` sees the same name in both.
    """
    if meta["type"] == "list":
        if not isinstance(value, list):
            return
        for i, entry in enumerate(value):
            if isinstance(entry, dict):
                _collect_refs_entry(meta.get("sub_fields") or {}, entry,
                                    f"{path}[{i}]", refs)
    elif meta["type"] == "object":
        if not isinstance(value, dict):
            return
        if meta.get("keyed"):
            for key, entry in value.items():
                if isinstance(entry, dict):
                    _collect_refs_entry(meta.get("sub_fields") or {}, entry,
                                        f"{path}.{key}", refs)
        else:
            _collect_refs_entry(meta.get("sub_fields") or {}, value, path, refs)


def _collect_refs_entry(sub_fields: dict, entry: dict, path: str, refs: list) -> None:
    for key, key_meta in sub_fields.items():
        if key not in entry:
            continue
        at = f"{path}.{key}"
        if key_meta.get("sub_fields"):
            _collect_refs(key_meta, entry[key], at, refs)
        elif key_meta.get("ref"):
            refs.append((key_meta["ref"], str(entry[key]), at))


def check_references(project_path, entity_type: str, frontmatter: dict) -> None:
    """Raise ValueError on the first `ref` that names no existing record.

    Reads the database, so this is write-time only — the same constraint
    `validate_scene_location` and `validate_arc_parents` carry. A `ref` is a
    slug of another entity, and an unresolvable one is invisible to every
    reader: they filter on `to_id`, so the scene looks like it serves no plot
    and the plot looks unpopulated, with nothing to say so.

    Two declaration forms: a field-level `ref` (a flat list of slugs, like
    `plot.characters`) and a sub-field `ref` (nested inside entries, like
    `plot_roles.plot`).
    """
    from core.db import get_db
    from .constants import ENTITY_SCHEMAS

    refs = []
    for field, meta in ENTITY_SCHEMAS.get(entity_type, {}).items():
        if field not in frontmatter:
            continue
        value = frontmatter[field]
        if meta.get("ref"):
            if isinstance(value, list):
                for i, item in enumerate(value):
                    refs.append((meta["ref"], str(item), f"{field}[{i}]"))
            elif value:
                refs.append((meta["ref"], str(value), field))
        elif meta.get("sub_fields"):
            _collect_refs(meta, value, field, refs)
    if not refs:
        return
    conn = get_db(project_path)
    try:
        for ref_type, target, path in refs:
            if not conn.execute(
                    "SELECT 1 FROM entities WHERE id=? AND type=?",
                    (target, ref_type)).fetchone():
                raise ValueError(f"{ref_type.capitalize()} not found: {target} "
                                 f"(at {path})")
    finally:
        conn.close()


def validate_scene_plot_roles(project_path, entries) -> None:
    """Raise ValueError if a scene's `plot_roles` holds an invalid role or
    names no plot.

    The plot existence check is the generic reference check (`ref: "plot"` on
    `plot_roles.plot`); what remains here is the rule the schema cannot say:
    the role must be one of the six dramatic plot roles, and an entry must
    name a plot at all — `check_references` skips an absent key, and an entry
    with no plot is not a row, it is a reference that resolves to nothing.
    """
    if not isinstance(entries, list):
        return
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        role = str(entry.get("role") or "")
        if role not in PLOT_ROLES:
            raise ValueError(
                f"Invalid plot role: {role or '(empty)'}. "
                f"One of: {', '.join(PLOT_ROLES)}")
        if not entry.get("plot"):
            raise ValueError(
                f"plot_roles entry needs a plot slug: {entry!r}")


def validate_scene_dramatic_role(dramatic_role, plot_roles) -> None:
    """Raise ValueError when `dramatic_role` and `plot_roles` contradict each other.

    A scene's role belongs to a plot, so it lives in `plot_roles` — one entry
    per plot, because one scene can be a climax for one plot and a
    complication for another. `dramatic_role` therefore carries no role at
    all; it only distinguishes the scenes that serve NO plot from those that
    do. There are exactly two ways to serve no plot, and they are mutually
    exclusive with carrying roles:

        transition / non-event  ->  plot_roles must be empty
        plot_role / empty        ->  plot_roles may be set

    The two rules are both needed. Without the first, an agent can mark a
    scene a non-event and still give it a climax, and the scene then claims
    to move nothing while demonstrably moving something — with no reader able
    to reconcile them, since one is on the scene and the other is reached
    through the plot. Without the second, `plot_role` would be a word that
    asserts nothing.

    The error names the fix rather than the rule, because the agent hitting
    it is holding both halves of a contradiction and needs to be told which
    one to drop.
    """
    if not dramatic_role:
        return
    if dramatic_role in ("transition", "non-event"):
        if plot_roles:
            raise ValueError(
                f"dramatic_role is '{dramatic_role}', which means this scene "
                f"serves no plot — but plot_roles has "
                f"{len(plot_roles)} entr{'y' if len(plot_roles) == 1 else 'ies'}. "
                f"A scene cannot be both. Either clear plot_roles, or set "
                f"dramatic_role to 'plot_role' and keep the roles."
            )
        return
    # `plot_role`: the roles themselves carry the meaning, so an empty list
    # is not an error — the scene may simply not be placed against a plot yet.
    return


def validate_scene_value_turns(project_path, value_turns) -> None:
    """Raise ValueError on the first value turn that breaks its plot's schema.

    A turn is one shift of a value plus how it lands on each protagonist, and
    every part of it has to resolve on the plot it names: the plot exists, the
    value has a schema there (already registered or supplied inline by this
    turn), `from` and `to` are words of that schema, and each effect names a
    protagonist of that plot through one level per conflict circle.

    The messages teach the vocabulary, because the agent that hits one is
    holding a turn and needs to be told what the plot's words are rather than
    that a rule was broken.

    Runs on write only: it reads the plot's `characters` and `value_schemas`
    from the database, so a plot created in the same draft is visible here —
    commit applies a draft's ops one at a time, creates before edits.
    """
    from .db import get_db

    if not isinstance(value_turns, list):
        return

    conn = get_db(project_path)
    try:
        plots = {}
        for row in conn.execute(
                "SELECT id, extra FROM entities WHERE type='plot'").fetchall():
            extra = json.loads(row[1]) if row[1] else {}
            plots[row[0]] = (extra.get("characters") or [],
                             extra.get("value_schemas") or [])

        # One value per turn: two shifts of the same value are two turns, so
        # the same (plot, value) twice is a duplicate, not a second shift.
        seen = set()
        for i, turn in enumerate(value_turns):
            at = f"value_turns[{i}]"
            if not isinstance(turn, dict):
                raise ValueError(
                    f"{at} must be an object with keys [plot, value, from, "
                    f"to, effects] — got {type(turn).__name__}")
            plot = str(turn.get("plot") or "").strip()
            if not plot:
                raise ValueError(f"{at}.plot is required")
            if plot not in plots:
                raise ValueError(f"Plot not found: {plot} (at {at}.plot)")
            characters, schemas = plots[plot]

            value = str(turn.get("value") or "").strip()
            if not value:
                raise ValueError(f"{at}.value is required")

            inline = turn.get("schema")
            registered = next((s for s in schemas
                               if str(s.get("value") or "").strip().lower()
                               == value.lower()), None)
            if registered is None and inline is None:
                # A turn in THIS scene may have defined the value inline —
                # the words it supplied are the schema the later turn uses.
                inline = next((dict(other[2]) for other in seen
                               if other[:2] == (plot, value.lower())), None)
                if inline is None:
                    raise ValueError(
                        f"{value} has no schema on {plot}. "
                        f"Defined values: {_defined_values(schemas)}. "
                        f"Add a `schema` (p, c, cd, nn) to this turn to define it.")
            if inline is not None and registered is not None:
                raise ValueError(
                    f"{value} already has a schema on {plot}: "
                    f"{_schema_words(registered)}. "
                    f"Remove schema from this turn and use these words.")

            if registered is not None:
                words = {rung: str(registered.get(rung) or "").strip()
                         for rung in VALUE_LADDER}
            else:
                if not isinstance(inline, dict):
                    raise ValueError(
                        f"{at}.schema must be an object with keys "
                        f"[p, c, cd, nn] — got {type(inline).__name__}")
                for rung in VALUE_LADDER:
                    if not str(inline.get(rung) or "").strip():
                        raise ValueError(
                            f"{at}.schema.{rung} is required — a schema is the "
                            f"four words {', '.join(VALUE_LADDER)}")
                words = {rung: str(inline[rung]).strip()
                         for rung in VALUE_LADDER}
                distinct = {w.lower() for w in words.values()}
                if len(distinct) != len(VALUE_LADDER):
                    raise ValueError(
                        f"{at}.schema needs four distinct words — the rungs "
                        f"are: {', '.join(f'{k} {v}' for k, v in words.items())}")
                # Same value, same scene: the words must agree, or the scene
                # defines its value two ways at once.
                for other in seen:
                    if (other[:2] == (plot, value.lower())
                            and other[2] != frozenset(words.items())):
                        raise ValueError(
                            f"{at} defines {value} on {plot} differently from "
                            f"an earlier turn in this scene: "
                            f"{_schema_words(dict(other[2]))} vs "
                            f"{_schema_words(words)}. The words must agree.")
                seen.add((plot, value.lower(), frozenset(words.items())))

            for key in ("from", "to"):
                word = str(turn.get(key) or "").strip()
                if not word:
                    raise ValueError(f"{at}.{key} is required")
                if word.lower() not in {w.lower() for w in words.values()}:
                    raise ValueError(
                        f"{at}.{key} '{word}' is not a word of the {value} "
                        f"schema on {plot}: {_schema_words(words)}")

            effects = turn.get("effects")
            if not effects:
                raise ValueError(
                    f"{at}.effects is required and must list one entry per "
                    f"protagonist the shift affects")
            if not isinstance(effects, list):
                raise ValueError(
                    f"{at}.effects must be a list — got "
                    f"{type(effects).__name__}")
            allowed = characters
            affected = set()
            for j, effect in enumerate(effects):
                where = f"{at}.effects[{j}]"
                if not isinstance(effect, dict):
                    raise ValueError(
                        f"{where} must be an object with keys "
                        f"[character, levels] — got {type(effect).__name__}")
                character = str(effect.get("character") or "").strip()
                if not character:
                    raise ValueError(f"{where}.character is required")
                if character in affected:
                    raise ValueError(
                        f"{character} appears twice in {at}.effects — one "
                        f"entry per protagonist, with one level per circle")
                affected.add(character)
                if character not in allowed:
                    raise ValueError(
                        f"{character} is not a protagonist of {plot}: "
                        f"{', '.join(allowed) or '(none defined)'}. "
                        f"Add them to plot.characters, or name a protagonist.")
                levels = effect.get("levels")
                if not levels:
                    raise ValueError(
                        f"{where}.levels is required — one entry per conflict "
                        f"level through which the shift reaches {character}")
                if not isinstance(levels, list):
                    raise ValueError(
                        f"{where}.levels must be a list — got "
                        f"{type(levels).__name__}")
                circles = set()
                for k, level in enumerate(levels):
                    spot = f"{where}.levels[{k}]"
                    if not isinstance(level, dict):
                        raise ValueError(
                            f"{spot} must be an object with keys "
                            f"[conflict_level, effect] — got "
                            f"{type(level).__name__}")
                    conflict_level = str(level.get("conflict_level") or "").strip()
                    if not conflict_level:
                        raise ValueError(f"{spot}.conflict_level is required")
                    if conflict_level not in CONFLICT_LEVELS:
                        raise ValueError(
                            f"{spot}.conflict_level '{conflict_level}' is not "
                            f"one of: {', '.join(CONFLICT_LEVELS)}")
                    if conflict_level in circles:
                        raise ValueError(
                            f"{character} has two '{conflict_level}' levels in "
                            f"{where}.levels — one level per circle, with an "
                            f"effect focused on that level")
                    circles.add(conflict_level)
                    sentence = str(level.get("effect") or "").strip()
                    if not sentence:
                        raise ValueError(
                            f"{spot}.effect is required — one sentence: what "
                            f"the shift does to {character} at the "
                            f"{conflict_level} level")
    finally:
        conn.close()


def _schema_words(schema) -> str:
    """A schema (or a words dict) as `p x, c y, cd z, nn w` — the vocabulary
    an error message hands over, so the fix is to use these words."""
    return ", ".join(f"{rung} {schema[rung]}" for rung in VALUE_LADDER)


def _defined_values(schemas) -> str:
    """Every value the plot defines, with its words. Empty says why."""
    if not schemas:
        return "none"
    return "; ".join(f"{s.get('value')}: {_schema_words(s)}" for s in schemas)


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
