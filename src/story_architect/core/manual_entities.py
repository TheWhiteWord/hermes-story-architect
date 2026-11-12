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

from .constants import (ACT_STATUSES, ENTITY_LABELS, ENTITY_SCHEMAS, PLOT_ROLES, PLOT_SCOPES,
                        PLOT_TYPES, SCENE_DRAMATIC_ROLES, SCENE_STATUSES, SEQUENCE_STATUSES,
                        STRUCTURE_TYPES, VALID_ROLES, VALID_STATUSES, VALUE_ARCS, VALUE_LADDER)
from .db import get_db
from .entity import (ENTITY_COLUMN_MAP, REVERSED_RELATION_KINDS, _RELATION_FIELDS,
                     coerce_number, standard_sections)

# What the form can edit today. The spec builder is generic; this is the gate,
# so a type goes live when its form has been exercised, not when its schema exists.
FORM_TYPES = ("character", "location", "world", "value", "plot", "relationship", "project",
              "act", "sequence", "scene")

# The project is a single record that exists from the start: it can be edited,
# never created or deleted from here.
SINGLETONS = ("project",)

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
    "plot_scope": "Scope", "plot_type": "Kind of subplot", "value_arc": "Value arc",
    "characters": "Characters", "perspectives": "Perspectives", "scenes": "Scenes featured",
    "history": "History", "status": "Status", "logline": "Logline",
    "structure_type": "Structure", "act_count": "Number of acts",
    "screenplay_title": "Screenplay title", "controlling_idea": "Controlling idea",
    "draft_date": "Draft date", "setups": "Setups", "inciting_incident": "Inciting incident",
    "complications": "Complications", "crisis": "Crisis", "climax": "Climax",
    "resolutions": "Resolutions", "value_focus": "Values that shift",
    "act_id": "Act", "sequence_id": "Sequence", "primary_plot": "Primary plot",
    "act_objective": "Objective", "scene_objective": "Objective", "purpose": "Purpose",
    "dramatic_role": "Dramatic role", "plot_roles": "Plot roles", "no_cast": "No characters",
    "heading": "Heading", "time_of_day": "Time of day", "turning_point": "Turning point",
    "scene_beats": "Beats record", "value_turns": "Value turns", "location": "Location",
}

# Closed vocabularies that live in `constants` / `entity`, not in the schema.
ENUMS = {
    ("character", "story_role"): VALID_ROLES,
    ("plot", "status"): VALID_STATUSES,
    ("plot", "value_arc"): VALUE_ARCS,
    ("plot", "plot_scope"): PLOT_SCOPES,
    ("plot", "plot_type"): PLOT_TYPES,
    ("relationship", "status"): ["active", "resolved", "complex"],
    ("project", "status"): ["active", "abandoned", "archived"],
    ("project", "structure_type"): STRUCTURE_TYPES,
    ("act", "status"): ACT_STATUSES,
    ("sequence", "status"): SEQUENCE_STATUSES,
    ("scene", "status"): SCENE_STATUSES,
    ("scene", "dramatic_role"): SCENE_DRAMATIC_ROLES,
}

# Labels for options whose stored word reads badly in a list.
OPTION_LABELS = {
    "role": {"setup": "Setup", "inciting_incident": "Inciting incident", "complication": "Complication",
             "crisis": "Crisis", "climax": "Climax", "resolution": "Resolution"},
    "dramatic_role": {"plot_role": "Plot role", "transition": "Transition", "non-event": "Non-event"},
}

# The kinds a perspective can have. The schema only lists them in prose, and the
# write path doesn't enforce them, so the form offers them and keeps anything
# already stored.
REL_TYPES = ["ally", "enemy", "family", "romantic", "professional", "mentor", "rival", "neutral", "custom"]

# Relational fields the schema does not declare as `ref` (it must not: a `ref`
# makes the write path check it, which changes what the agent is held to).
# Declared here, for the form only. Value = the type the slug must belong to.
UI_REFS = {
    ("location", "world"): "world",
    ("location", "variant_of"): "location",
    ("world", "variant_of"): "world",
    ("relationship", "characters"): "character",
    ("relationship", "scenes"): "scene",
    ("sequence", "act_id"): "act",
    ("sequence", "primary_plot"): "plot",
    ("scene", "sequence_id"): "sequence",
}

# Where an act / sequence / scene sits is chosen once, when it is made. After that it
# changes only through Reorder, which keeps the three levels consistent with each other.
POSITION = {("sequence", "act_id"), ("scene", "sequence_id")}
# `order` is Reorder's; a scene's `act_id` is just its sequence's act, kept in step by the form.
HIDDEN = {("act", "order"), ("sequence", "order"), ("scene", "order"), ("scene", "act_id")}
# Written by the script editor together with the script, so the heading line and
# these fields can never disagree. Shown, with a way to get there; never edited here.
SCRIPT_FIELDS = ("heading", "location", "time_of_day", "characters")
# Shown but not editable in this form (yet).
READ_ONLY = {("scene", "value_turns"): "Edited with the agent for now."}
HIDDEN_SECTIONS = {"scene": {"Content"}}            # the script itself: the script editor's

# A list of small records, edited as a stack of cards.
PLOT_ROLE_FIELDS = [
    {"key": "plot", "label": "Plot", "kind": "ref", "ref": "plot", "required": True},
    {"key": "role", "label": "Role", "kind": "select", "options": list(PLOT_ROLES),
     "option_labels": OPTION_LABELS["role"], "allow_blank": False, "required": True},
    {"key": "description", "label": "What happens", "kind": "text",
     "help": "What this scene does for the plot."},
]
REPEATERS = {("scene", "plot_roles"): PLOT_ROLE_FIELDS}

# Fields that only matter when another field has a given value. Hidden, they are
# reset to their default, so a stale value can't linger behind the form.
SHOW_IF = {("plot", "plot_type"): {"plot_scope": "sub"}}

# Where the schema's own order reads badly in a form.
FIELD_ORDER = {
    "relationship": ["name", "characters", "perspectives", "status", "history", "scenes"],
    "act": ["title", "status", "act_objective"],
    "sequence": ["title", "act_id", "status", "primary_plot", "purpose"],
    "scene": ["title", "sequence_id", "status", "one_sentence", "scene_objective", "no_cast",
              "dramatic_role", "plot_roles"],
}

# A name the form can suggest from other fields until the person types their own.
AUTO_NAME = {"relationship": {"from": "characters", "join": " & "}}

# Visual grouping inside one form.
GROUPS = {("project", k): "Title page" for k in
          ("screenplay_title", "credit", "author", "contact", "draft_date", "draft")}

MULTILINE = {"note", "history", "purpose", "spine", "controlling_idea", "act_objective"}

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
    ("plot", "one_sentence"): "One line that sums up this plot.",
    ("plot", "characters"): "The protagonists of this plot only — not everyone who appears in it.",
    ("plot", "value_arc"): "The kind of change this plot puts its protagonist through.",
    ("plot", "plot_scope"): "A main plot carries the story; a subplot supports it.",
    ("plot", "plot_type"): "How this subplot relates to the main plot.",
    ("relationship", "name"): "Usually the two names, e.g. “Kael & Mira”.",
    ("relationship", "history"): "How this relationship came to be and how it has changed.",
    ("relationship", "scenes"): "Scenes where this relationship is featured.",
    ("project", "logline"): "One sentence that sums up the story.",
    ("project", "genre"): "e.g. Sci-fi thriller.",
    ("project", "setting"): "e.g. Near-future city-state.",
    ("project", "spine"): "The protagonist’s desire — what drives the whole story.",
    ("project", "controlling_idea"): "The argument the story makes.",
    ("project", "act_count"): "Grows by itself if you add more acts than this.",
    ("project", "credit"): "e.g. Written by.",
    ("project", "draft"): "e.g. First Draft.",
    ("project", "draft_date"): "Printed bottom-left on the title page.",
    ("project", "contact"): "Printed bottom-right on the title page.",
    ("project", "screenplay_title"): "Printed centred on the title page.",
    ("act", "title"): "e.g. Act I.",
    ("act", "act_objective"): "The protagonist’s immediate goal in this act.",
    ("sequence", "purpose"): "What this sequence is for, dramatically.",
    ("sequence", "primary_plot"): "The plot this sequence mainly serves.",
    ("sequence", "act_id"): "Which act it belongs to. Choose once — move it later with Reorder.",
    ("scene", "sequence_id"): "Which sequence it belongs to. Choose once — move it later with Reorder.",
    ("scene", "one_sentence"): "One line that sums up the scene.",
    ("scene", "scene_objective"): "What the driving character wants in this scene.",
    ("scene", "dramatic_role"): "Leave empty if the scene serves a plot. Transition and non-event scenes serve none.",
    ("scene", "no_cast"): "Tick this when nobody appears on purpose, e.g. an empty room.",
    **{k: v for k, v in VALUE_LADDER.items()},
}

_ON_SCENES = "Set on a scene’s plot roles."
HINTS = {
    ("character", "relationships"):
        "Managed as relationship entities — edit them from the Relationships view.",
    **{("plot", k): _ON_SCENES for k in
       ("setups", "inciting_incident", "complications", "crisis", "climax", "resolutions")},
    ("plot", "value_focus"): "Counted from the value turns written on scenes.",
    ("project", "value_focus"): "Counted from the value turns written on scenes.",
    ("act", "value_focus"): "Counted from the value turns written on its scenes.",
    ("sequence", "value_focus"): "Counted from the value turns written on its scenes.",
    ("scene", "turning_point"): "Written with the scene’s beats.",
    ("scene", "scene_beats"): "Edited with the agent for now.",
    **{("scene", k): "Written by the script editor." for k in SCRIPT_FIELDS},
}

# A field whose value cannot change once the entity exists.
LOCKED_ON_EDIT = {
    ("sequence", "act_id"): "To move it to another act, use Reorder in the Scenes tab.",
    ("scene", "sequence_id"): "To move it to another sequence, use Reorder in the Scenes tab.",
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


# What a perspective holds, one card per character.
PERSPECTIVE_FIELDS = [
    {"key": "label", "label": "Label", "kind": "text", "help": "What they call it, e.g. “Closest friend”."},
    {"key": "feeling", "label": "Feeling", "kind": "text", "help": "Their emotional stance."},
    {"key": "type", "label": "Kind", "kind": "select", "options": REL_TYPES, "allow_blank": True},
    {"key": "strength", "label": "Strength", "kind": "number", "min": -1, "max": 1, "step": 0.1,
     "help": "−1 is hostile, 0 neutral, 1 devoted."},
    {"key": "secret", "label": "Hidden from the other character", "kind": "toggle"},
]


def _json_default(meta: dict):
    return json.loads(json.dumps(meta.get("default", "")))


def _field_spec(entity_type: str, key: str, meta: dict) -> dict:
    spec = {
        "key": key,
        "label": LABELS.get(key) or meta.get("label") or _humanize(key),
        "help": HELP.get((entity_type, key)) or HELP.get(key, ""),
        "required": False,
        "default": _json_default(meta),
    }
    if (entity_type, key) in GROUPS:
        spec["group"] = GROUPS[(entity_type, key)]
    if (entity_type, key) in SHOW_IF:
        spec["show_if"] = SHOW_IF[(entity_type, key)]
    if (entity_type, key) in POSITION:
        spec["required"] = True
    if entity_type == "scene" and key in SCRIPT_FIELDS:
        spec.update(kind="linked", hint=HINTS.get((entity_type, key), ""))
        return spec
    if (entity_type, key) in READ_ONLY:
        spec.update(kind="computed", hint=READ_ONLY[(entity_type, key)])
        return spec
    if (entity_type, key) in REPEATERS:
        spec.update(kind="repeater", fields=REPEATERS[(entity_type, key)], add_label="Add plot role")
        return spec
    if meta.get("computed"):
        spec.update(kind="computed", hint=HINTS.get((entity_type, key), ""))
        return spec
    enum = ENUMS.get((entity_type, key))
    ref = _ref_for(entity_type, key, meta)
    kind_t = meta.get("type")
    if enum:
        spec.update(kind="select", options=list(enum),
                    allow_blank=meta.get("default", "") in ("", None))
        if key in OPTION_LABELS:
            spec["option_labels"] = OPTION_LABELS[key]
    elif entity_type == "relationship" and key == "characters":
        spec.update(kind="reflist", ref=ref, count=2, row_labels=["First character", "Second character"])
    elif ref and kind_t == "list":
        spec.update(kind="reflist", ref=ref, add_label=f"Add {ENTITY_LABELS.get(ref, ref).lower()}")
    elif ref:
        spec.update(kind="ref", ref=ref)
    elif kind_t == "object" and meta.get("keyed") and entity_type == "relationship":
        spec.update(kind="perspectives", keyed_by="characters", ref="character",
                    fields=PERSPECTIVE_FIELDS)
    elif kind_t == "string":
        spec["kind"] = "textarea" if key in MULTILINE else "text"
    elif kind_t == "list" and meta.get("sub_fields"):
        spec["kind"] = "unsupported"        # nested editors arrive with the types that need them
    elif kind_t == "list":
        spec["kind"] = "list"
    elif kind_t == "number":
        spec["kind"] = "number"
        if key == "act_count":
            spec.update(integer=True, min=1)
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
              if k not in ("id", "type") and (entity_type, k) not in HIDDEN]
    order = FIELD_ORDER.get(entity_type)
    if order:
        fields.sort(key=lambda f: order.index(f["key"]) if f["key"] in order else len(order))
    fields.sort(key=lambda f: 1 if f.get("group") else 0)       # stable: groups sit together, last
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
        "sections": _sections(entity_type),
        "singleton": entity_type in SINGLETONS,
        **({"script_link": True} if entity_type == "scene" else {}),
        **({"auto_name": AUTO_NAME[entity_type]} if entity_type in AUTO_NAME else {}),
    }


def _sections(entity_type: str) -> list:
    hidden = HIDDEN_SECTIONS.get(entity_type, ())
    return [n for n in standard_sections(entity_type) if n not in hidden]


def all_specs() -> dict:
    return {t: form_spec(t) for t in FORM_TYPES}


def _require_type(entity_type: str) -> None:
    if entity_type not in FORM_TYPES:
        raise EntityNotFound(f"{entity_type} can't be edited from the form yet.")


# ─── Reading ─────────────────────────────────────────────────────────────────

def _slug_of(name: str) -> str:
    from .writes import _slug_of as slug
    return slug(name)


def _resolve(conn, entity_type: str, entity_id: str) -> str:
    """A singleton has one record whatever id the caller names."""
    if entity_type in SINGLETONS:
        r = conn.execute("SELECT id FROM entities WHERE type=?", (entity_type,)).fetchone()
        if r:
            return r[0]
    return entity_id


def _row(conn, entity_type: str, entity_id: str):
    entity_id = _resolve(conn, entity_type, entity_id)
    row = conn.execute(
        "SELECT id, name, one_sentence, order_key, status, parent_id, location_id, extra "
        "FROM entities WHERE type=? AND id=? AND is_deleted=0", (entity_type, entity_id)
    ).fetchone()
    if not row:
        raise EntityNotFound(f"{ENTITY_LABELS.get(entity_type, entity_type)} not found: {entity_id}")
    return row


def _is_placeholder(text) -> bool:
    return str(text or "").lstrip().lower().startswith("[placeholder")


ROLE_FIELD = {"setup": "setups", "inciting_incident": "inciting_incident", "complication": "complications",
              "crisis": "crisis", "climax": "climax", "resolution": "resolutions"}


def _scene_rows(conn, scene_id: str) -> dict:
    """What the script editor owns on a scene, plus the derived records — display only."""
    row = conn.execute("SELECT location_id, extra FROM entities WHERE id=?", (scene_id,)).fetchone()
    ex = json.loads(row[1]) if row and row[1] else {}
    one = lambda text: [{"display": text}] if text else []          # noqa: E731
    loc = ""
    if row and row[0]:
        r = conn.execute("SELECT name FROM entities WHERE id=?", (row[0],)).fetchone()
        loc = (r[0] if r else row[0]) or row[0]
    cast = [r[0] for r in conn.execute(
        "SELECT e.name FROM relations r JOIN entities e ON e.id=r.from_id "
        "WHERE r.to_id=? AND r.kind='character_scene' AND e.is_deleted=0 ORDER BY r.\"order\"", (scene_id,))]
    beats = conn.execute("SELECT id FROM entities WHERE type='scene_beats' AND parent_id=? AND is_deleted=0",
                         (scene_id,)).fetchone()
    turns = []
    for t in ex.get("value_turns") or []:
        if isinstance(t, dict):
            turns.append({"display": f"{t.get('value', '?')}: {t.get('from', '?')} → {t.get('to', '?')}"
                                     + (f" ({t['plot']})" if t.get("plot") else "")})
    return {
        "heading": one(ex.get("heading")), "location": one(loc),
        "time_of_day": one(ex.get("time_of_day")), "characters": [{"display": n} for n in cast],
        "turning_point": one(ex.get("turning_point")),
        "scene_beats": [{"display": "A beats record exists"}] if beats else [],
        "value_turns": turns,
    }


def _focus_rows(focus: dict) -> list:
    rows = []
    for label, key in (("Major", "major"), ("Minor", "minor")):
        items = (focus or {}).get(key) or []
        if items:
            rows.append({"display": f"{label}: " + " · ".join(
                f"{i['value']} ×{i['scenes'] if isinstance(i['scenes'], int) else len(i['scenes'])}"
                for i in items)})
    return rows


def _computed(conn, entity_type: str, entity_id: str, project_path: Path | None = None) -> dict:
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
    elif entity_type == "plot":
        by_field = {f: [] for f in ROLE_FIELD.values()}
        for sname, sid, kind, note in conn.execute(
                "SELECT e.name, e.id, r.kind, r.note FROM relations r JOIN entities e ON e.id=r.to_id "
                "WHERE r.from_id=? AND r.kind LIKE 'plot\\_%' ESCAPE '\\' AND e.is_deleted=0 "
                "ORDER BY r.\"order\"", (entity_id,)):
            field = ROLE_FIELD.get(kind[len("plot_"):])
            if field:
                by_field[field].append({"display": (sname or sid) + (f" — {note}" if note else ""),
                                        "ref": f"scene:{sid}"})
        out.update(by_field)
    elif entity_type == "scene":
        out.update(_scene_rows(conn, entity_id))
    if entity_type in ("plot", "project", "act", "sequence") and project_path is not None:
        try:
            from . import value_focus
            focus = {"plot": lambda: value_focus.for_plot(project_path, entity_id),
                     "project": lambda: value_focus.for_project(project_path),
                     "act": lambda: value_focus.for_act(project_path, entity_id),
                     "sequence": lambda: value_focus.for_sequence(project_path, entity_id)}[entity_type]()
            out["value_focus"] = _focus_rows(focus)
        except Exception:                      # a derived display must never block the form
            out["value_focus"] = []
    return out


def _persp_form(raw) -> dict:
    """Perspectives as the form holds them: every field present, `""` when unset."""
    out = {}
    for cid, p in (raw or {}).items():
        p = p if isinstance(p, dict) else {}
        st = p.get("strength")
        out[cid] = {
            "label": str(p.get("label") or ""), "feeling": str(p.get("feeling") or ""),
            "type": str(p.get("type") or ""),
            "strength": st if isinstance(st, (int, float)) and not isinstance(st, bool) else "",
            "secret": bool(p.get("secret")),
        }
    return out


def _persp_storage(form: dict) -> dict:
    """…and as it is stored: only what was filled in, but every character keeps a key."""
    out = {}
    for cid, p in form.items():
        d = {k: p[k] for k in ("label", "feeling", "type") if p.get(k)}
        if p.get("strength") not in ("", None):
            d["strength"] = p["strength"]
        if p.get("secret"):
            d["secret"] = True
        out[cid] = d
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
        entity_id = row[0]
        extra = json.loads(row[7]) if row[7] else {}
        schema = ENTITY_SCHEMAS[entity_type]
        colmap = ENTITY_COLUMN_MAP.get(entity_type, {})
        editable_keys = {f["key"] for f in form_spec(entity_type)["fields"]
                         if f["kind"] not in ("computed", "linked", "unsupported")}
        cols = {"name": row[1], "one_sentence": row[2], "order_key": row[3],
                "status": row[4], "parent_id": row[5], "location_id": row[6]}
        rels = _RELATION_FIELDS.get(entity_type, {})
        values = {}
        for key, meta in schema.items():
            if key not in editable_keys:
                continue
            if key == "plot_roles" and entity_type == "scene":
                v = [{"plot": r[0], "role": r[1][len("plot_"):], "description": r[2] or ""}
                     for r in conn.execute(
                         "SELECT from_id, kind, note FROM relations WHERE to_id=? AND kind LIKE 'plot\\_%' "
                         "ESCAPE '\\' ORDER BY \"order\"", (entity_id,))]
                values[key] = v
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
            if key == "perspectives" and entity_type == "relationship":
                v = _persp_form(v)
            values[key] = v
        sections = {h: "" for h in _sections(entity_type)}
        for heading, body in conn.execute(
                "SELECT heading, body FROM sections WHERE entity_id=?", (entity_id,)):
            if heading in sections:
                sections[heading] = "" if _is_placeholder(body) else (body or "")
        return {
            "type": entity_type, "id": entity_id, "values": values, "sections": sections,
            "computed": _computed(conn, entity_type, entity_id, project_path),
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
    spec = {f["key"]: f for f in form_spec(entity_type)["fields"]}
    values, errors = {}, {}
    for key, v in raw.items():
        meta = schema.get(key)
        if meta is None:
            errors["_form"] = f"Unknown field “{key}”. Reload the page and try again."
            continue
        if (meta.get("computed") or (entity_type, key) in HIDDEN or (entity_type, key) in READ_ONLY
                or (entity_type == "scene" and key in SCRIPT_FIELDS)):
            continue                                   # derived, or someone else's: never written
        t = meta.get("type")
        label = LABELS.get(key) or _humanize(key)
        if (entity_type, key) in REPEATERS:
            values[key] = _clean_repeater(REPEATERS[(entity_type, key)], v, key, errors)
        elif entity_type == "relationship" and key == "perspectives":
            values[key] = _clean_perspectives(v, errors)
        elif t == "string":
            values[key] = "" if v is None else str(v).strip()
        elif t == "list":
            if not isinstance(v, list):
                errors[key] = f"{label} should be a list."
            elif meta.get("sub_fields"):
                values[key] = v
            else:
                values[key] = [str(i).strip() for i in v if isinstance(i, (str, int, float)) and str(i).strip()]
        elif t == "number":
            f = spec.get(key, {})
            if v in ("", None):
                values[key] = meta.get("default", 0)
            else:
                n = coerce_number(v)
                if not isinstance(n, (int, float)) or isinstance(n, bool):
                    errors[key] = f"{label} should be a number."
                elif f.get("integer") and n != int(n):
                    errors[key] = f"{label} should be a whole number."
                elif "min" in f and n < f["min"]:
                    errors[key] = f"{label} should be at least {f['min']}."
                else:
                    values[key] = int(n) if f.get("integer") else n
        elif t == "boolean":
            values[key] = bool(v)
        else:
            values[key] = v
    # A field that only applies under a condition is reset when the condition fails.
    for key, f in spec.items():
        cond = f.get("show_if")
        if cond and key in values and any(values.get(dep) != want for dep, want in cond.items()):
            values[key] = f["default"]
    if "perspectives" in values and "characters" in values:
        keep = [c for c in values["characters"] if c]
        values["perspectives"] = {c: values["perspectives"].get(c) or _persp_form({c: {}})[c] for c in keep}
    return values, errors


def _clean_repeater(fields: list, raw, key: str, errors: dict) -> list:
    """A list of records from cards. A card with nothing in it is not a record: dropped."""
    if not isinstance(raw, list):
        errors[key] = "This should be a list of cards."
        return []
    out = []
    for entry in raw:
        entry = entry if isinstance(entry, dict) else {}
        rec = {f["key"]: ("" if entry.get(f["key"]) is None else str(entry[f["key"]]).strip()) for f in fields}
        if any(rec.values()):
            out.append(rec)
    return out


def _clean_perspectives(raw, errors: dict) -> dict:
    if not isinstance(raw, dict):
        errors["perspectives"] = "Perspectives should be a set of cards, one per character."
        return {}
    out = {}
    for cid, p in raw.items():
        p = p if isinstance(p, dict) else {}
        st = p.get("strength")
        if st in ("", None):
            st = ""
        else:
            n = coerce_number(st)
            if not isinstance(n, (int, float)) or isinstance(n, bool) or not -1.0 <= float(n) <= 1.0:
                errors[f"perspectives.{cid}.strength"] = "Strength is a number from −1 (hostile) to 1 (devoted)."
                st = ""
            else:
                st = n
        out[cid] = {"label": str(p.get("label") or "").strip(), "feeling": str(p.get("feeling") or "").strip(),
                    "type": str(p.get("type") or "").strip(), "strength": st, "secret": bool(p.get("secret"))}
    return out


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
              errors: dict, baseline: dict | None = None) -> tuple[dict, str | None]:
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
    if mode_edit and baseline is not None:
        for key in [k for (t, k) in POSITION if t == entity_type]:
            if key in values and values[key] != baseline.get(key) and key not in errors:
                errors[key] = LOCKED_ON_EDIT[(entity_type, key)]
    if mode_edit and is_value and slug and slug != entity_id:
        errors[nk] = LOCKED_ON_EDIT[("value", "name")]

    # A second one with the same name is allowed, but worth a nudge.
    if name and not is_value and entity_type not in SINGLETONS:
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
        if baseline is not None and baseline.get(key) == v:
            continue                       # untouched: don't hold the person to a stored legacy value
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

    if not mode_edit:
        for f in spec["fields"]:
            if (entity_type, f["key"]) in POSITION and f["key"] not in errors and not values.get(f["key"]):
                target = ENTITY_LABELS.get(f["ref"], f["ref"]).lower()
                none = conn.execute("SELECT 1 FROM entities WHERE type=? AND is_deleted=0", (f["ref"],)).fetchone() is None
                errors[f["key"]] = (f"There are no {target}s yet — create one first." if none
                                    else f"Choose the {target} this belongs in.")
    _validate_kind_specific(conn, entity_type, entity_id, values, errors, warnings)

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


def _validate_kind_specific(conn, entity_type, entity_id, values, errors, warnings) -> None:
    if entity_type == "relationship" and "characters" not in errors:
        chars = values.get("characters") or []
        if len(chars) != 2 or len(set(chars)) != 2:
            errors["characters"] = "Pick two different characters."
        else:
            for rid, rname, rex in conn.execute(
                    "SELECT id, name, extra FROM entities WHERE type='relationship' AND is_deleted=0 AND id<>?",
                    (entity_id or "",)):
                if set((json.loads(rex) if rex else {}).get("characters") or []) == set(chars):
                    nm = _names(conn, chars)
                    warnings["characters"] = (f"{nm.get(chars[0], chars[0])} and {nm.get(chars[1], chars[1])} "
                                              f"already have a relationship (“{rname}”). Saving adds another.")
                    break
    elif entity_type == "scene":
        roles = values.get("plot_roles") or []
        seen = set()
        for i, r in enumerate(roles):
            at = f"plot_roles.{i}"
            if not r.get("plot"):
                errors[f"{at}.plot"] = "Choose the plot."
            elif not _exists(conn, "plot", r["plot"]):
                errors[f"{at}.plot"] = f"There is no plot “{r['plot']}” — pick one from the list."
            elif r["plot"] in seen:
                errors[f"{at}.plot"] = "This scene already has a role in that plot — one role per plot."
            else:
                seen.add(r["plot"])
            if r.get("role") not in PLOT_ROLES:
                errors[f"{at}.role"] = "Choose a role."
        if values.get("dramatic_role") in ("transition", "non-event") and roles and "dramatic_role" not in errors:
            errors["dramatic_role"] = (f"A {values['dramatic_role']} scene serves no plot, but it has plot roles. "
                                       f"Remove them, or leave the dramatic role empty.")
    elif entity_type == "plot":
        if values.get("plot_scope") == "sub" and not values.get("plot_type"):
            warnings["plot_type"] = "A subplot normally has a kind — pick how it relates to the main plot."
    elif entity_type == "project" and isinstance(values.get("act_count"), (int, float)):
        have = conn.execute("SELECT COUNT(*) FROM entities WHERE type='act' AND is_deleted=0").fetchone()[0]
        if "act_count" not in errors and values["act_count"] < have:
            warnings["act_count"] = f"You already have {have} acts, so the count will stay at {have}."


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
    _refuse_singleton(entity_type, entity_id is None)
    values, errors = _clean(entity_type, (payload or {}).get("values") or {})
    _clean_sections(entity_type, (payload or {}).get("sections"), errors)
    conn = get_db(project_path)
    try:
        baseline = None
        if entity_id is not None:
            row = _row(conn, entity_type, entity_id)
            entity_id = row[0]
            baseline = load_entity(project_path, entity_type, entity_id)["values"]   # same bar as save
        warnings, new_id = _validate(conn, entity_type, entity_id, values, errors, baseline=baseline)
    finally:
        conn.close()
    return {"ok": not errors, "errors": errors, "warnings": warnings, "id": new_id}


# ─── Writing ─────────────────────────────────────────────────────────────────

SUMMARY = "Edited by hand in the entity form"


def _refuse_singleton(entity_type: str, creating: bool = False, deleting: bool = False) -> None:
    if entity_type in SINGLETONS and (creating or deleting):
        raise EntityInvalid({"_form": f"The {entity_type} can be edited here, "
                                      f"but not created or deleted."})


def _to_storage(entity_type: str, data: dict) -> dict:
    out = dict(data)
    if entity_type == "relationship" and "perspectives" in out:
        out["perspectives"] = _persp_storage(out["perspectives"])
    return out


def _write_error(e: ValueError) -> EntityInvalid:
    return EntityInvalid({"_form": str(e)})


def create_form_entity(project_path: Path, entity_type: str, payload: dict) -> dict:
    from .writes import create_entity

    _require_type(entity_type)
    _refuse_singleton(entity_type, creating=True)
    values, errors = _clean(entity_type, (payload or {}).get("values") or {})
    sections = _clean_sections(entity_type, (payload or {}).get("sections"), errors)
    conn = get_db(project_path)
    try:
        warnings, new_id = _validate(conn, entity_type, None, values, errors)
    finally:
        conn.close()
    if errors or not new_id:
        raise EntityInvalid(errors or {"_form": "Could not make an id from that name."}, warnings)

    if entity_type in ("scene", "act"):
        conn = get_db(project_path)
        try:
            if entity_type == "scene":                  # a scene's act is its sequence's act
                r = conn.execute("SELECT parent_id FROM entities WHERE id=?", (values["sequence_id"],)).fetchone()
                values["act_id"] = r[0] if r else ""
            else:                                       # acts are not auto-numbered by the write path
                r = conn.execute("SELECT COALESCE(MAX(order_key), 0) FROM entities WHERE type='act' "
                                 "AND is_deleted=0").fetchone()
                values["order"] = int(r[0]) + 1
        finally:
            conn.close()
    if entity_type == "relationship":               # one card per character, even if never opened
        values["perspectives"] = {c: (values.get("perspectives") or {}).get(c) or _persp_form({c: {}})[c]
                                  for c in values.get("characters") or []}
    fm = {k: v for k, v in _to_storage(entity_type, values).items() if v not in ("", [], None)}
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
    entity_id = current["id"]
    if (payload or {}).get("base_version") != current["version"]:
        raise EntityConflict(current["version"])

    values, errors = _clean(entity_type, (payload or {}).get("values") or {})
    sections = _clean_sections(entity_type, (payload or {}).get("sections"), errors)
    conn = get_db(project_path)
    try:
        warnings, _ = _validate(conn, entity_type, entity_id, values, errors, baseline=current["values"])
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
        edit_entity(project_path, entity_type, entity_id, _to_storage(entity_type, changed), SUMMARY)
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
    _refuse_singleton(entity_type, deleting=True)
    conn = get_db(project_path)
    try:
        row = _row(conn, entity_type, entity_id)
        label = ENTITY_LABELS[entity_type]
        children = conn.execute(
            "SELECT id, type, name FROM entities WHERE parent_id=? AND is_deleted=0",
            (entity_id,)).fetchall()
        def _lab(t):
            return ENTITY_LABELS.get(t) or t.replace("_", " ").capitalize()
        also = [{"id": c[0], "type": c[1], "name": c[2] or c[0], "label": _lab(c[1])} for c in children]
        # A sequence or act that still holds scenes / sequences is not deleted around them:
        # they are moved or deleted on purpose first.
        structural: list[str] = []
        if entity_type in ("sequence", "act"):
            kids = [c for c in also if c["type"] in ("scene", "sequence")]
            also = [c for c in also if c not in kids]
            if kids:
                noun = kids[0]["type"]
                structural.append(
                    f"“{row[1] or entity_id}” still contains {_plural(len(kids), noun)}: "
                    f"{_list([k['name'] for k in kids])}. Move or delete them first"
                    f"{' — use Reorder in the Scenes tab to move scenes' if entity_type == 'sequence' else ''}.")
                structural[-1] = structural[-1].replace(
                    "Move or delete them first", "Move or delete " + ("it" if len(kids) == 1 else "them") + " first")

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
        if entity_type == "scene":
            body = conn.execute("SELECT body FROM sections WHERE entity_id=? AND heading='Content'",
                                (entity_id,)).fetchone()
            text = (body[0] or "") if body else ""
            if text.strip() and not _is_placeholder(text):
                effects.insert(0, f"Its script ({len(text):,} characters) is deleted with it.")
        if entity_type == "plot":
            roles = [r[0] for r in conn.execute(
                f"SELECT DISTINCT e.name FROM relations r JOIN entities e ON e.id=r.to_id "
                f"WHERE r.from_id IN ({marks}) AND r.kind LIKE 'plot\\_%' ESCAPE '\\' "
                f"AND e.type='scene' AND e.is_deleted=0", gone_l)]
            if roles:
                effects.append(f"Loses its plot role in {_plural(len(roles), 'scene')}: {_list(roles)}.")
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
        blockers: list[str] = list(structural)
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
                if str(t.get("plot") or "") in gone:
                    turn_scenes.setdefault(sid, set()).add(names.get(str(t["plot"]), str(t["plot"])))
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

    _require_type(entity_type)
    _refuse_singleton(entity_type, deleting=True)
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
