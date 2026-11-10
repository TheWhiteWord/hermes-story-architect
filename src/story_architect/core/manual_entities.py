"""Entities authored by a person in the UI form (create, edit, delete).

The sibling of `manual_edits` (the script editor). Same rule: a person using a
form IS the approval, so there is no draft. Everything here validates what a
form can get wrong, in words a writer can act on, and then calls the one write
path the agent's commits use (`core.writes`). There is no second way to write.

Three jobs:

  * `form_spec`     — the schema turned into a form description, so the UI has
                      ONE renderer and a field added to `ENTITY_SCHEMAS` shows
                      up in the form without touching JavaScript.
  * `load_entity` / `check_entity` / `create_form_entity` / `edit_form_entity`
                    — read, dry-run and write one entity. Errors are keyed by
                      FIELD, so the form can put the message next to the input.
  * `delete_preview` / `delete_form_entity`
                    — what a delete takes with it, what blocks it, and the
                      cascade the agent path does not do (a character's
                      relationships go with it).

Concurrency matches the script editor: a load hands back a `version`, a save
must present it, and a mismatch (the agent committed in between) is refused.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .constants import (ENTITY_LABELS, ENTITY_SCHEMAS, PLOT_SCOPES, PLOT_TYPES,
                        VALID_ROLES, VALID_STATUSES, VALUE_ARCS, VALUE_LADDER)
from .db import get_db
from .entity import (ENTITY_COLUMN_MAP, REVERSED_RELATION_KINDS, _RELATION_FIELDS,
                     coerce_number, standard_sections)

# What the form can edit today. The spec builder is generic; this is the gate,
# so a type goes live when its form has been exercised, not when its schema exists.
FORM_TYPES = ("character", "location", "world", "value")

NAME_KEY = {"scene": "title", "sequence": "title", "act": "title"}


# ─── Errors ──────────────────────────────────────────────────────────────────

class EntityFormError(ValueError):
    """Something the form sent that cannot be applied. Message is user-facing."""


class EntityNotFound(EntityFormError):
    pass


class EntityConflict(EntityFormError):
    def __init__(self, current_version: str):
        super().__init__("This was changed since you opened it.")
        self.current_version = current_version


class EntityInvalid(EntityFormError):
    """`errors` maps a field key (or `_form`) to a message."""

    def __init__(self, errors: dict, warnings: dict | None = None):
        super().__init__("; ".join(errors.values()) or "Invalid.")
        self.errors = errors
        self.warnings = warnings or {}


class EntityBlocked(EntityFormError):
    def __init__(self, message: str, blockers: list[str]):
        super().__init__(message)
        self.blockers = blockers


# ─── Form spec ───────────────────────────────────────────────────────────────

LABELS = {
    "name": "Name", "title": "Title", "one_sentence": "In one sentence",
    "story_role": "Role", "goals_short": "Immediate goal", "goals_long": "Deeper goal",
    "knowledge": "What they know", "relationships": "Relationships",
    "dramatic_function": "Dramatic function", "mood": "Mood", "world": "World",
    "variant_of": "Variant of", "rules": "Rules", "period": "Period",
    "values": "What the world holds sacred", "power": "Who holds power",
    "p": "Positive", "c": "Contrary", "cd": "Contradictory",
    "nn": "Negation of the negation", "note": "Note",
}

# Closed vocabularies that live in `constants` / `entity`, not in the schema.
ENUMS = {
    ("character", "story_role"): VALID_ROLES,
    ("plot", "status"): VALID_STATUSES,
    ("plot", "value_arc"): VALUE_ARCS,
    ("plot", "plot_scope"): PLOT_SCOPES,
    ("plot", "plot_type"): PLOT_TYPES,
}

# Relational fields the schema does not declare as `ref` (it must not: a `ref`
# makes the write path check it, which changes what the agent is held to).
# Declared here, for the form only. Value = the type the slug must belong to.
UI_REFS = {
    ("location", "world"): "world",
    ("location", "variant_of"): "location",
    ("world", "variant_of"): "world",
}

MULTILINE = {"note", "history", "purpose"}

# Help written for the person at the form. The schema's own descriptions are
# written for the agent ("Slug of the base location…") and would read as jargon.
HELP = {
    "one_sentence": "One line that sums it up — it's what appears on the cards.",
    "goals_short": "What they want right now.",
    "goals_long": "What they really need, underneath.",
    "knowledge": "Facts this character holds. One per line.",
    "dramatic_function": "What this place does for the story.",
    "mood": "The feeling of the place, in a few words.",
    "period": "When this world is set, in your own words.",
    "rules": "One rule per line.",
    "values": "One per line.",
    "power": "One per line.",
    "note": "Anything to remember about this value.",
    ("location", "world"): "Which world this place belongs to.",
    ("location", "variant_of"): "Pick the original if this is another version of it. Leave empty otherwise.",
    ("world", "variant_of"): "Pick the original if this is another version of it. Leave empty otherwise.",
    ("value", "name"): "The positive pole, e.g. “trust”. Scenes refer to the value by this name.",
    **{k: v for k, v in VALUE_LADDER.items()},
}

HINTS = {
    ("character", "relationships"):
        "Managed as relationship entities — edit them from the Relationships view.",
}

# A field whose value cannot change once the entity exists.
LOCKED_ON_EDIT = {
    ("value", "name"):
        "A value is named by its positive pole, and scenes refer to it by that name — "
        "it can't be renamed. Create a new value instead.",
}


def _humanize(key: str) -> str:
    return key.replace("_", " ").capitalize()


def name_key(entity_type: str) -> str:
    return NAME_KEY.get(entity_type, "name")


def _ref_for(entity_type: str, key: str, meta: dict):
    return meta.get("ref") or UI_REFS.get((entity_type, key))


def _field_spec(entity_type: str, key: str, meta: dict) -> dict:
    spec = {
        "key": key,
        "label": LABELS.get(key) or meta.get("label") or _humanize(key),
        "help": HELP.get((entity_type, key)) or HELP.get(key, ""),
        "required": False,
    }
    if meta.get("computed"):
        spec.update(kind="computed", hint=HINTS.get((entity_type, key), ""))
        return spec
    enum = ENUMS.get((entity_type, key))
    ref = _ref_for(entity_type, key, meta)
    kind_t = meta.get("type")
    if enum:
        spec.update(kind="select", options=list(enum))
    elif ref and kind_t == "list":
        spec.update(kind="reflist", ref=ref)
    elif ref:
        spec.update(kind="ref", ref=ref)
    elif kind_t == "string":
        spec["kind"] = "textarea" if key in MULTILINE else "text"
    elif kind_t == "list" and meta.get("sub_fields"):
        spec["kind"] = "unsupported"        # nested editors arrive with the types that need them
    elif kind_t == "list":
        spec["kind"] = "list"
    elif kind_t == "number":
        spec["kind"] = "number"
    elif kind_t == "boolean":
        spec["kind"] = "toggle"
    else:
        spec["kind"] = "unsupported"
    if (entity_type, key) in LOCKED_ON_EDIT:
        spec["locked_on_edit"] = LOCKED_ON_EDIT[(entity_type, key)]
    return spec


def form_spec(entity_type: str) -> dict:
    """One entity type as a form: ordered fields, then the prose sections."""
    if entity_type not in ENTITY_SCHEMAS:
        raise EntityNotFound(f"Unknown entity type: {entity_type}")
    nk = name_key(entity_type)
    fields = [_field_spec(entity_type, k, m) for k, m in ENTITY_SCHEMAS[entity_type].items()
              if k not in ("id", "type")]
    for f in fields:
        if f["key"] == nk:
            f["required"] = True
        if entity_type == "value" and f["key"] in VALUE_LADDER:
            f["required"] = True
    return {
        "type": entity_type,
        "label": ENTITY_LABELS.get(entity_type, entity_type.capitalize()),
        "name_key": nk,
        "fields": fields,
        "sections": standard_sections(entity_type),
    }


def all_specs() -> dict:
    return {t: form_spec(t) for t in FORM_TYPES}


def _require_type(entity_type: str) -> None:
    if entity_type not in FORM_TYPES:
        raise EntityNotFound(f"{entity_type} can't be edited from the form yet.")


# ─── Reading ─────────────────────────────────────────────────────────────────

def _slug_of(name: str) -> str:
    from .writes import _slug_of as slug
    return slug(name)


def _row(conn, entity_type: str, entity_id: str):
    row = conn.execute(
        "SELECT id, name, one_sentence, order_key, status, parent_id, location_id, extra "
        "FROM entities WHERE type=? AND id=? AND is_deleted=0", (entity_type, entity_id)
    ).fetchone()
    if not row:
        raise EntityNotFound(f"{ENTITY_LABELS.get(entity_type, entity_type)} not found: {entity_id}")
    return row


def _is_placeholder(text) -> bool:
    return str(text or "").lstrip().lower().startswith("[placeholder")


def _computed(conn, entity_type: str, entity_id: str) -> dict:
    """Derived fields, as display rows. Shown, never written."""
    out = {}
    if entity_type == "character":
        names = {r[0]: r[1] for r in conn.execute(
            "SELECT id, name FROM entities WHERE type='character' AND is_deleted=0")}
        rows = []
        for rid, extra in conn.execute(
                "SELECT id, extra FROM entities WHERE type='relationship' AND is_deleted=0 ORDER BY name"):
            ex = json.loads(extra) if extra else {}
            chars = ex.get("characters") or []
            if entity_id not in chars:
                continue
            other = next((c for c in chars if c != entity_id), "")
            p = (ex.get("perspectives") or {}).get(entity_id) or {}
            bits = [b for b in (p.get("label"), p.get("type")) if b]
            rows.append({"display": names.get(other, other) + (f" — {' · '.join(bits)}" if bits else ""),
                         "ref": f"relationship:{rid}"})
        out["relationships"] = rows
    return out


def _version(values: dict, sections: dict) -> str:
    blob = json.dumps({"v": values, "s": sections}, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def load_entity(project_path: Path, entity_type: str, entity_id: str) -> dict:
    """The stored state of one entity, in the shape the form edits.

    Read from the database rather than the dashboard payload: the dashboard is
    normalised for display (a character's `knowledge` is joined into one string),
    and a form built from that would write the display form back.
    """
    _require_type(entity_type)
    conn = get_db(project_path)
    try:
        row = _row(conn, entity_type, entity_id)
        extra = json.loads(row[7]) if row[7] else {}
        schema = ENTITY_SCHEMAS[entity_type]
        colmap = ENTITY_COLUMN_MAP.get(entity_type, {})
        cols = {"name": row[1], "one_sentence": row[2], "order_key": row[3],
                "status": row[4], "parent_id": row[5], "location_id": row[6]}
        rels = _RELATION_FIELDS.get(entity_type, {})
        values = {}
        for key, meta in schema.items():
            if meta.get("computed") or key in ("id", "type"):
                continue
            if key in colmap:
                v = cols.get(colmap[key])
            elif key in rels:
                kind, is_list = rels[key]
                own, other = ("to_id", "from_id") if kind in REVERSED_RELATION_KINDS else ("from_id", "to_id")
                found = [r[0] for r in conn.execute(
                    f"SELECT {other} FROM relations WHERE {own}=? AND kind=? ORDER BY \"order\"",
                    (entity_id, kind))]
                v = found if is_list else (found[0] if found else "")
            else:
                v = extra.get(key)
            if v is None:
                v = json.loads(json.dumps(meta.get("default", "")))
            values[key] = v
        sections = {h: "" for h in standard_sections(entity_type)}
        for heading, body in conn.execute(
                "SELECT heading, body FROM sections WHERE entity_id=?", (entity_id,)):
            if heading in sections:
                sections[heading] = "" if _is_placeholder(body) else (body or "")
        return {
            "type": entity_type, "id": entity_id, "values": values, "sections": sections,
            "computed": _computed(conn, entity_type, entity_id),
            "version": _version(values, sections),
        }
    finally:
        conn.close()


# ─── Validation ──────────────────────────────────────────────────────────────

def _clean(entity_type: str, raw) -> tuple[dict, dict]:
    """Normalise what the form sent. Returns (values, errors)."""
    if not isinstance(raw, dict):
        raise EntityInvalid({"_form": "The form sent something unexpected. Reload and try again."})
    schema = ENTITY_SCHEMAS[entity_type]
    values, errors = {}, {}
    for key, v in raw.items():
        meta = schema.get(key)
        if meta is None:
            errors["_form"] = f"Unknown field “{key}”. Reload the page and try again."
            continue
        if meta.get("computed"):
            continue                                   # derived: never written
        t = meta.get("type")
        label = LABELS.get(key) or _humanize(key)
        if t == "string":
            values[key] = "" if v is None else str(v).strip()
        elif t == "list":
            if not isinstance(v, list):
                errors[key] = f"{label} should be a list."
            elif meta.get("sub_fields"):
                values[key] = v
            else:
                values[key] = [str(i).strip() for i in v if isinstance(i, (str, int, float)) and str(i).strip()]
        elif t == "number":
            if v in ("", None):
                values[key] = meta.get("default", 0)
            else:
                n = coerce_number(v)
                if isinstance(n, (int, float)) and not isinstance(n, bool):
                    values[key] = n
                else:
                    errors[key] = f"{label} should be a number."
        elif t == "boolean":
            values[key] = bool(v)
        else:
            values[key] = v
    return values, errors


def _exists(conn, entity_type: str, entity_id: str) -> bool:
    return conn.execute("SELECT 1 FROM entities WHERE id=? AND type=? AND is_deleted=0",
                        (entity_id, entity_type)).fetchone() is not None


def _unique_id(conn, slug: str) -> str:
    candidate, n = slug, 2
    while conn.execute("SELECT 1 FROM entities WHERE id=?", (candidate,)).fetchone():
        candidate = f"{slug}-{n}"
        n += 1
    return candidate


def _validate(conn, entity_type: str, entity_id: str | None, values: dict,
              errors: dict) -> tuple[dict, str | None]:
    """Everything the form can get wrong, keyed by field. Returns (warnings, id)."""
    spec = form_spec(entity_type)
    nk = spec["name_key"]
    label = spec["label"]
    warnings: dict = {}
    mode_edit = entity_id is not None
    is_value = entity_type == "value"

    name = values.get(nk, "")
    if not name:
        errors.setdefault(nk, "Give the value a name — its positive pole, e.g. “trust”."
                          if is_value else f"Give this {label.lower()} a name.")
    slug = _slug_of(name) if name else ""
    if name and not slug:
        errors[nk] = "Use at least one letter or number in the name."

    # The id.
    new_id = entity_id
    if not mode_edit and slug and nk not in errors:
        taken = conn.execute("SELECT type, is_deleted FROM entities WHERE id=?", (slug,)).fetchone()
        if not taken:
            new_id = slug
        elif is_value:
            # A value's id IS the slug of its name, so it cannot be suffixed.
            if taken[0] == "value" and not taken[1]:
                errors[nk] = f"A value called “{name}” already exists."
            elif taken[1]:
                errors[nk] = (f"“{name}” was deleted earlier and its id is still reserved. "
                              f"Pick a different name, or ask the agent to restore it.")
            else:
                errors[nk] = f"The id “{slug}” is already used by a {taken[0]}. Pick a different name."
        else:
            new_id = _unique_id(conn, slug)
    if mode_edit and is_value and slug and slug != entity_id:
        errors[nk] = LOCKED_ON_EDIT[("value", "name")]

    # A second one with the same name is allowed, but worth a nudge.
    if name and not is_value:
        dup = conn.execute(
            "SELECT id FROM entities WHERE type=? AND is_deleted=0 AND lower(name)=lower(?) AND id<>?",
            (entity_type, name, entity_id or "")).fetchone()
        if dup:
            warnings[nk] = (f"A {label.lower()} named “{name}” already exists ({dup[0]}). "
                            f"Saving creates a second one.")

    for f in spec["fields"]:
        key, kind = f["key"], f["kind"]
        v = values.get(key)
        if key in errors or v in (None, "", []):
            continue
        if kind == "select" and v not in f["options"]:
            errors[key] = f"Pick one of: {', '.join(f['options'])}."
        elif kind == "ref":
            if not _exists(conn, f["ref"], v):
                errors[key] = f"There is no {ENTITY_LABELS.get(f['ref'], f['ref']).lower()} “{v}” — pick one from the list."
            elif v == (entity_id or new_id):
                errors[key] = f"A {label.lower()} can't be a variant of itself."
        elif kind == "reflist":
            missing = [i for i in v if not _exists(conn, f["ref"], i)]
            if missing:
                errors[key] = f"Not found: {', '.join(missing)}."

    if is_value:
        words = {r: values.get(r, "") for r in VALUE_LADDER}
        seen: dict[str, str] = {}
        for rung in VALUE_LADDER:
            w = words[rung]
            if not w:
                errors.setdefault(rung, "Add the word for this rung.")
                continue
            prior = seen.get(w.lower())
            if prior:
                errors.setdefault(rung, f"“{w}” is already the word for “{LABELS[prior]}”. "
                                        f"Each rung needs its own word.")
            else:
                seen[w.lower()] = rung
        if name and not any(k == nk for k in errors):
            clash = conn.execute(
                "SELECT id FROM entities WHERE type='value' AND is_deleted=0 "
                "AND lower(name)=lower(?) AND id<>?", (name, entity_id or "")).fetchone()
            if clash:
                errors[nk] = f"A value called “{name}” already exists."
    return warnings, new_id


def _clean_sections(entity_type: str, raw, errors: dict) -> dict:
    if raw in (None, {}):
        return {}
    if not isinstance(raw, dict):
        errors["_form"] = "The form sent something unexpected. Reload and try again."
        return {}
    allowed = set(standard_sections(entity_type))
    out = {}
    for h, body in raw.items():
        if h not in allowed:
            errors["_form"] = f"Unknown section “{h}”. Reload the page and try again."
            continue
        out[h] = "" if body is None else str(body).strip()
    return out


def check_entity(project_path: Path, entity_type: str, payload: dict,
                 entity_id: str | None = None) -> dict:
    """What a save WOULD say. Writes nothing; the form calls it while typing."""
    _require_type(entity_type)
    values, errors = _clean(entity_type, (payload or {}).get("values") or {})
    _clean_sections(entity_type, (payload or {}).get("sections"), errors)
    conn = get_db(project_path)
    try:
        if entity_id is not None:
            _row(conn, entity_type, entity_id)
        warnings, new_id = _validate(conn, entity_type, entity_id, values, errors)
    finally:
        conn.close()
    return {"ok": not errors, "errors": errors, "warnings": warnings, "id": new_id}


# ─── Writing ─────────────────────────────────────────────────────────────────

SUMMARY = "Edited by hand in the entity form"


def _write_error(e: ValueError) -> EntityInvalid:
    return EntityInvalid({"_form": str(e)})


def create_form_entity(project_path: Path, entity_type: str, payload: dict) -> dict:
    from .writes import create_entity

    _require_type(entity_type)
    values, errors = _clean(entity_type, (payload or {}).get("values") or {})
    sections = _clean_sections(entity_type, (payload or {}).get("sections"), errors)
    conn = get_db(project_path)
    try:
        warnings, new_id = _validate(conn, entity_type, None, values, errors)
    finally:
        conn.close()
    if errors or not new_id:
        raise EntityInvalid(errors or {"_form": "Could not make an id from that name."}, warnings)

    fm = {k: v for k, v in values.items() if v not in ("", [], None)}
    try:
        create_entity(project_path, entity_type, new_id, fm,
                      {h: b for h, b in sections.items() if b})
    except ValueError as e:
        raise _write_error(e)
    return {**load_entity(project_path, entity_type, new_id), "created": True, "warnings": warnings}


def edit_form_entity(project_path: Path, entity_type: str, entity_id: str, payload: dict) -> dict:
    from .writes import edit_entity

    _require_type(entity_type)
    current = load_entity(project_path, entity_type, entity_id)
    if (payload or {}).get("base_version") != current["version"]:
        raise EntityConflict(current["version"])

    values, errors = _clean(entity_type, (payload or {}).get("values") or {})
    sections = _clean_sections(entity_type, (payload or {}).get("sections"), errors)
    conn = get_db(project_path)
    try:
        warnings, _ = _validate(conn, entity_type, entity_id, values, errors)
    finally:
        conn.close()
    if errors:
        raise EntityInvalid(errors, warnings)

    # Only what changed is written: a field the person never touched is not
    # rewritten, so an agent edit to it elsewhere is not clobbered by a stale copy.
    changed = {k: v for k, v in values.items() if current["values"].get(k) != v}
    changed.update({h: b for h, b in sections.items() if current["sections"].get(h, "") != b})
    if not changed:
        return {**current, "unchanged": True, "warnings": warnings}
    try:
        edit_entity(project_path, entity_type, entity_id, changed, SUMMARY)
    except ValueError as e:
        raise _write_error(e)
    return {**load_entity(project_path, entity_type, entity_id), "unchanged": False,
            "warnings": warnings}


# ─── Delete ──────────────────────────────────────────────────────────────────

def _names(conn, ids) -> dict:
    ids = list(ids)
    if not ids:
        return {}
    marks = ",".join("?" * len(ids))
    return {r[0]: r[1] or r[0] for r in conn.execute(
        f"SELECT id, name FROM entities WHERE id IN ({marks})", ids)}


def _list(names: list[str], limit: int = 4) -> str:
    shown = [f"“{n}”" for n in names[:limit]]
    rest = len(names) - len(shown)
    return ", ".join(shown) + (f" and {rest} more" if rest > 0 else "")


def _plural(n: int, one: str, many: str | None = None) -> str:
    return f"{n} {one}" if n == 1 else f"{n} {many or one + 's'}"


def _beat_refs(extra: dict) -> set:
    """Every entity id a scene_beats record names."""
    refs = set()
    if extra.get("driver"):
        refs.add(str(extra["driver"]))
    for t in extra.get("true_character") or []:
        if isinstance(t, dict) and t.get("character"):
            refs.add(str(t["character"]))
    for c in extra.get("changes") or []:
        if isinstance(c, dict) and c.get("entity"):
            refs.add(str(c["entity"]))
    for b in extra.get("beats") or []:
        for side in ("action", "reaction"):
            s = b.get(side) if isinstance(b, dict) else None
            if isinstance(s, dict) and s.get("by"):
                refs.add(str(s["by"]))
    return refs


def delete_preview(project_path: Path, entity_type: str, entity_id: str) -> dict:
    """What a delete takes with it and what stops it. Changes nothing."""
    _require_type(entity_type)
    conn = get_db(project_path)
    try:
        row = _row(conn, entity_type, entity_id)
        label = ENTITY_LABELS[entity_type]
        children = conn.execute(
            "SELECT id, type, name FROM entities WHERE parent_id=? AND is_deleted=0",
            (entity_id,)).fetchall()
        also = [{"id": c[0], "type": c[1], "name": c[2] or c[0]} for c in children]

        # A character's relationships go with them: a bond with one person left
        # is not a relationship. (The agent path keeps the surviving half; the
        # form deliberately does not.)
        rels = []
        if entity_type == "character":
            for rid, rname, rex in conn.execute(
                    "SELECT id, name, extra FROM entities WHERE type='relationship' AND is_deleted=0"):
                ex = json.loads(rex) if rex else {}
                if entity_id in (ex.get("characters") or []):
                    rels.append({"id": rid, "type": "relationship", "name": rname or rid})

        gone = {entity_id} | {c["id"] for c in also} | {r["id"] for r in rels}
        marks = ",".join("?" * len(gone))
        gone_l = list(gone)
        effects: list[str] = []

        # What survives but loses a link.
        cast = [r[0] for r in conn.execute(
            f"SELECT DISTINCT e.name FROM relations r JOIN entities e ON e.id=r.to_id "
            f"WHERE r.kind='character_scene' AND r.from_id IN ({marks}) AND e.is_deleted=0", gone_l)]
        if cast:
            effects.append(f"Removed from the cast of {_plural(len(cast), 'scene')}: {_list(cast)}.")
        plots = []
        for pid, pname, pex in conn.execute(
                "SELECT id, name, extra FROM entities WHERE type='plot' AND is_deleted=0"):
            ex = json.loads(pex) if pex else {}
            if gone & set(map(str, ex.get("characters") or [])):
                plots.append(pname or pid)
        if plots:
            effects.append(f"No longer a protagonist of {_plural(len(plots), 'plot')}: {_list(plots)}.")
        located = [r[0] for r in conn.execute(
            f"SELECT name FROM entities WHERE type='scene' AND is_deleted=0 "
            f"AND location_id IN ({marks})", gone_l)]
        if located:
            effects.append(f"{_plural(len(located), 'scene')} will have no location: {_list(located)}.")
        variants = [r[0] for r in conn.execute(
            f"SELECT DISTINCT e.name FROM relations r JOIN entities e ON e.id=r.from_id "
            f"WHERE r.kind IN ('location_variant','world_variant') AND r.to_id IN ({marks}) "
            f"AND r.from_id NOT IN ({marks}) AND e.is_deleted=0", gone_l + gone_l)]
        if variants:
            effects.append(f"{_plural(len(variants), 'variant')} will lose their base: {_list(variants)}.")

        # What cannot be cleaned up safely: references inside scene data. The
        # agent's delete leaves these dangling; here the delete is refused until
        # they're gone, because a dangling one makes the NEXT edit of that scene fail.
        names = _names(conn, gone)
        scene_names = {r[0]: r[1] or r[0] for r in conn.execute(
            "SELECT id, name FROM entities WHERE type='scene' AND is_deleted=0")}
        blockers: list[str] = []
        by_scene: dict[str, set] = {}
        for sid, bex in conn.execute(
                "SELECT parent_id, extra FROM entities WHERE type='scene_beats' AND is_deleted=0"):
            hit = _beat_refs(json.loads(bex) if bex else {}) & gone
            if hit:
                by_scene.setdefault(sid, set()).update(hit)
        for sid, hit in by_scene.items():
            who = _list(sorted(names.get(h, h) for h in hit))
            blockers.append(f"{who} is still named in the beats of “{scene_names.get(sid, sid)}”. "
                            f"Remove it there first.")
        value_name = (row[1] or "").strip().lower() if entity_type == "value" else None
        turn_scenes: dict[str, set] = {}
        for sid, sname, sex in conn.execute(
                "SELECT id, name, extra FROM entities WHERE type='scene' AND is_deleted=0"):
            for t in (json.loads(sex) if sex else {}).get("value_turns") or []:
                if not isinstance(t, dict):
                    continue
                if value_name and str(t.get("value") or "").strip().lower() == value_name:
                    turn_scenes.setdefault(sid, set()).add(row[1] or entity_id)
                for eff in t.get("effects") or []:
                    if isinstance(eff, dict) and str(eff.get("character")) in gone:
                        turn_scenes.setdefault(sid, set()).add(names.get(str(eff["character"]), str(eff["character"])))
        for sid, who in turn_scenes.items():
            blockers.append(f"{_list(sorted(who))} is used in the value turns of “{scene_names.get(sid, sid)}”. "
                            f"Remove it there first.")

        return {
            "entity": {"id": entity_id, "type": entity_type, "name": row[1] or entity_id,
                       "label": label},
            "also_deleted": also, "relationships": rels,
            "effects": effects, "blockers": blockers, "can_delete": not blockers,
        }
    finally:
        conn.close()


def delete_form_entity(project_path: Path, entity_type: str, entity_id: str) -> dict:
    from .writes import delete_entity

    prev = delete_preview(project_path, entity_type, entity_id)
    if prev["blockers"]:
        raise EntityBlocked("This can't be deleted yet.", prev["blockers"])
    # Relationships first: once the character is flagged deleted, the agent-path
    # purge would otherwise strip the character out of them and leave a husk.
    for rel in prev["relationships"]:
        res = delete_entity(project_path, "relationship", rel["id"],
                            f"Deleted with {entity_id}", confirm=True)
        if res.get("error"):
            raise EntityBlocked(res["error"], [res["error"]])
    res = delete_entity(project_path, entity_type, entity_id, SUMMARY, confirm=True)
    if res.get("error"):
        raise EntityBlocked(res["error"], [res["error"]])
    return {
        "deleted": [{"id": entity_id, "type": entity_type}]
                   + [{"id": c["id"], "type": c["type"]} for c in prev["also_deleted"]]
                   + [{"id": r["id"], "type": "relationship"} for r in prev["relationships"]],
        "detached": res.get("detached", []),
        "reversible": True,
    }
