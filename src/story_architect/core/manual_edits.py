"""Writes authored by a person in the UI, as opposed to staged by the agent.

Two doors into the same room. The agent proposes through `core.drafts` and a
person approves; a person editing in the UI IS the approval, so their edits go
straight through `core.writes` with no draft in between. There is deliberately
no second write path underneath: every function here validates what the UI can
get wrong and then calls the same `writes.edit_entity` / `create_entity` the
agent's commits dispatch to, so one place defines what an edit means.

This module is where future manual authoring lands too (creating a character
or location by hand): add a function here, validate, call `core.writes`. Keep
HTTP out of it — `app/routes/scripts.py` is the thin layer over this.

Concurrency: nothing in the schema is versioned, so each load hands back a
`hash` of what the editor is looking at and a save must present it. If the
harness committed in between, the save is refused (`ScriptConflict`) and the
person decides, rather than one side's work silently overwriting the other's.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from . import scene_script as ss
from .constants import INT_EXT_CHOICES, SCENE_TIMES_OF_DAY, PLOT_ROLES
from .db import get_db
from .entity import ENTITY_COLUMN_MAP, unfilled_fields
from .fountain_lexer import SCENE_HEADING_RE


class ScriptError(ValueError):
    """A save the UI sent that cannot be applied. The message is user-facing."""


class ScriptNotFound(ScriptError):
    pass


class ScriptLocked(ScriptError):
    pass


class ScriptConflict(ScriptError):
    def __init__(self, current_hash: str):
        super().__init__("The scene changed since you opened it.")
        self.current_hash = current_hash


# ─── Reading ─────────────────────────────────────────────────────────────────

def _scene_state(conn, scene_id: str) -> dict:
    row = conn.execute(
        "SELECT id, name, one_sentence, order_key, status, parent_id, location_id, extra "
        "FROM entities WHERE type='scene' AND id=? AND is_deleted=0", (scene_id,)
    ).fetchone()
    if not row:
        raise ScriptNotFound(f"Scene not found: {scene_id}")
    extra = json.loads(row[7]) if row[7] else {}
    body = conn.execute(
        "SELECT body FROM sections WHERE entity_id=? AND heading='Content'",
        (scene_id,)).fetchone()
    chars = [r[0] for r in conn.execute(
        "SELECT from_id FROM relations WHERE to_id=? AND kind='character_scene' "
        "ORDER BY \"order\", from_id", (scene_id,))]
    n_roles = conn.execute(
        "SELECT COUNT(*) FROM relations WHERE to_id=? AND kind IN (%s)"
        % ",".join("?" * len(PLOT_ROLES)),
        (scene_id, *[f"plot_{r}" for r in PLOT_ROLES])).fetchone()[0]
    return {
        "row": {"name": row[1], "one_sentence": row[2], "order_key": row[3],
                "status": row[4], "parent_id": row[5], "location_id": row[6]},
        "id": row[0], "title": row[1], "status": row[4],
        "order": row[3] or 0, "sequence_id": row[5],
        "location": row[6] or "", "extra": extra,
        "int_ext": extra.get("int_ext", ""),
        "place": extra.get("place", ""),
        "time_of_day": extra.get("time_of_day", ""),
        "forced_heading": extra.get("forced_heading", ""),
        "raw_content": body[0] if body else "",
        "characters": chars, "plot_role_count": n_roles,
    }


def _registry(conn) -> tuple[list[dict], dict]:
    chars = []
    for cid, name, extra in conn.execute(
            "SELECT id, name, extra FROM entities WHERE type='character' AND is_deleted=0 "
            "ORDER BY name"):
        ex = json.loads(extra) if extra else {}
        chars.append({"id": cid, "name": name or cid,
                      "story_role": ex.get("story_role", "")})
    names = {r[0]: r[1] for r in conn.execute(
        "SELECT id, name FROM entities WHERE type='world' AND is_deleted=0")}
    locs = [{"id": i, "name": n or i,
             "world": ({"id": w, "name": names.get(w, w)} if w else None)}
            for i, n, w in conn.execute(
                "SELECT id, name, parent_id FROM entities "
                "WHERE type='location' AND is_deleted=0 ORDER BY name")]
    return chars, {l["id"]: l for l in locs}


def content_hash(state: dict) -> str:
    """The change token: what the editor sees, and what a save overwrites."""
    blob = json.dumps({
        "content": state["raw_content"],
        "int_ext": state["int_ext"],
        "place": state["place"],
        "location": state["location"],
        "time_of_day": state["time_of_day"],
        "forced_heading": state["forced_heading"],
        "characters": sorted(state["characters"]),
    }, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def _adhoc_elsewhere(conn, characters: list[dict], skip: str) -> list[dict]:
    """Unregistered speakers used in OTHER scenes, so a minor character already
    written once is offered again instead of being retyped (and mistyped)."""
    counts: dict[str, int] = {}
    for sid, body in conn.execute(
            "SELECT e.id, s.body FROM sections s JOIN entities e ON e.id=s.entity_id "
            "WHERE e.type='scene' AND e.is_deleted=0 AND s.heading='Content' AND e.id<>?",
            (skip,)):
        _, rest = ss.split_heading(body)
        for c in ss.script_cast(ss.parse_blocks(rest), characters):
            if not c["registered"]:
                counts[c["cue"]] = counts.get(c["cue"], 0) + 1
    return [{"cue": k, "name": k.title(), "scenes": n}
            for k, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))]


def _view(st: dict, characters: list[dict], locations: dict, *, content: str,
          lossless: bool = True) -> dict:
    """Everything derived from one scene state. Shared by `load_scene_script`
    (the stored state) and `check_scene_script` (an unsaved draft), so a warning
    means the same thing before and after a save."""
    _, body = ss.split_heading(content)
    return _view_from_blocks(st, characters, locations, blocks=ss.parse_blocks(body),
                             content=content, lossless=lossless)


def _composed_heading(st: dict, loc: dict | None) -> str:
    """The scene's heading line, for readers that still show one."""
    return ss.scene_heading(st["int_ext"], loc["name"] if loc else "",
                            st["place"], st["time_of_day"], st["forced_heading"])


def _view_from_blocks(st, characters, locations, *, blocks, content,
                      lossless=True) -> dict:
    extra = st["extra"]
    loc = locations.get(st["location"])
    cast = ss.script_cast(blocks, characters)
    in_script = {c["id"] for c in cast if c["id"]}
    by_id = {c["id"]: c for c in characters}
    registered_cast = [
        {"id": cid, "name": by_id[cid]["name"], "story_role": by_id[cid]["story_role"],
         "in_script": cid in in_script,
         "cues": next((c["cues"] for c in cast if c["id"] == cid), 0)}
        for cid in dict.fromkeys(list(st["characters"]) + sorted(in_script))
        if cid in by_id]
    # Per character block: what it resolved to. The editor underlines the ones
    # that resolved to nothing without re-implementing the matching rules.
    cues = []
    for i, b in enumerate(blocks):
        if b.get("type") == "character" and b.get("text", "").strip():
            r = ss.resolve_cue(ss.cue_key(b["text"]), characters)
            cues.append({"block": i, "id": r["id"], "candidates": r["candidates"]})

    scene = {
        "id": st["id"], "title": st["title"], "status": st["status"],
        "order": st["order"], "sequence_id": st["sequence_id"],
        "location": st["location"],
        "int_ext": st["int_ext"], "place": st["place"],
        "time_of_day": st["time_of_day"], "forced_heading": st["forced_heading"],
        "heading": _composed_heading(st, loc),
        "dramatic_role": extra.get("dramatic_role", ""),
        "no_cast": bool(extra.get("no_cast")),
        "scene_objective": extra.get("scene_objective", ""),
    }
    unfilled = unfilled_fields("scene", {
        **extra,
        "characters": st["characters"] or [],
        "plot_roles": [1] * st["plot_role_count"],
    }, st["row"])
    return {
        "scene": scene, "blocks": blocks, "location": loc,
        "cast": registered_cast,
        "adhoc": [c for c in cast if not c["registered"]],
        "cues": cues,
        "findings": ss.findings(
            scene=scene, blocks=blocks, cast=cast, location=loc,
            has_plot_roles=st["plot_role_count"] > 0,
            unfilled=unfilled, lossless=lossless),
        "stats": ss.script_stats(content, cast),
    }


def load_scene_script(project_path: Path, scene_id: str) -> dict:
    """Everything the editor needs to open one scene."""
    conn = get_db(project_path)
    try:
        st = _scene_state(conn, scene_id)
        characters, locations = _registry(conn)
        adhoc = _adhoc_elsewhere(conn, characters, scene_id)
    finally:
        conn.close()

    raw = st["raw_content"]
    placeholder = ss.is_placeholder(raw)
    heading_line, body = ss.split_heading(raw)
    blocks = ss.parse_blocks(body)
    lossless = (ss.is_lossless(raw, heading_line, blocks)
                if raw.strip() and not placeholder else True)
    view = _view(st, characters, locations, content="" if placeholder else raw,
                 lossless=lossless)
    return {
        **view,
        "locked": st["status"] == "locked" or not lossless,
        "locked_reason": ("status" if st["status"] == "locked"
                          else "not_roundtrippable" if not lossless else None),
        "hash": content_hash(st),
        "content": "" if placeholder else raw,
        "adhoc_elsewhere": adhoc,
        "registry": {"characters": characters, "locations": list(locations.values())},
    }


def _heading_fields(hd: dict, locations: dict) -> dict:
    """Validate the editor's heading controls; return the fields to write.

    Shared by `save_scene_script` and `check_scene_script`, so a refusal means
    the same thing before and after a save. The write boundary re-checks the
    merged state on every path; this is the editor's own message, before
    anything is written.
    """
    slug = hd.get("location") or ""
    if slug and slug not in locations:
        raise ScriptError(f"Location not found: {slug}")
    int_ext = hd.get("int_ext") or ""
    place = hd.get("place") or ""
    tod = hd.get("time_of_day") or ""
    forced = (hd.get("forced_heading") or "").strip()
    if int_ext and int_ext not in INT_EXT_CHOICES:
        raise ScriptError(f"int_ext must be one of {', '.join(INT_EXT_CHOICES)}.")
    if tod and tod not in SCENE_TIMES_OF_DAY:
        raise ScriptError(f"time_of_day must be one of {', '.join(SCENE_TIMES_OF_DAY)}.")
    if " - " in place:
        raise ScriptError("place cannot contain ' - '.")
    if forced:
        if not SCENE_HEADING_RE.match(forced):
            raise ScriptError("A forced heading must be a scene heading "
                              "(INT./EXT. … or a forced '.HEADING').")
        if int_ext or place or tod:
            raise ScriptError(
                "forced_heading is exclusive with the composed heading — "
                "clear int_ext, place and time_of_day, or unset forced_heading")
    return {"int_ext": int_ext, "place": place, "time_of_day": tod,
            "forced_heading": forced, "location": slug}


def check_scene_script(project_path: Path, scene_id: str, payload: dict) -> dict:
    """What the findings, cast and stats WOULD be for an unsaved draft.

    Writes nothing. The editor calls this (debounced) while a person types so
    the warnings come from the one set of rules the server applies on save,
    instead of a second copy in JavaScript that would drift.
    """
    if not isinstance(payload, dict):
        raise ScriptError("Request body must be an object.")
    blocks = _validate_blocks(payload.get("blocks"))
    hd = payload.get("heading") or {}
    if not isinstance(hd, dict):
        raise ScriptError("`heading` must be an object.")
    conn = get_db(project_path)
    try:
        st = _scene_state(conn, scene_id)
        characters, locations = _registry(conn)
    finally:
        conn.close()

    fields = _heading_fields(hd, locations)
    extra_cast = [c for c in (payload.get("extra_cast") or [])
                  if any(c == x["id"] for x in characters)]
    draft = {**st, **fields, "characters": extra_cast,
             "extra": {**st["extra"], **fields}}
    view = _view_from_blocks(draft, characters, locations, blocks=blocks,
                             content=ss.serialize_blocks(blocks))
    return {k: view[k] for k in ("scene", "location", "cast", "adhoc", "cues",
                                 "findings", "stats")}


# ─── Writing ─────────────────────────────────────────────────────────────────

def _validate_blocks(blocks) -> list[dict]:
    if not isinstance(blocks, list):
        raise ScriptError("`blocks` must be a list.")
    clean = []
    for i, b in enumerate(blocks):
        if not isinstance(b, dict) or b.get("type") not in ss.BLOCK_TYPES \
                or not isinstance(b.get("text", ""), str):
            raise ScriptError(f"blocks[{i}] must be {{type, text}} with a known type.")
        clean.append({"type": b["type"], "text": b.get("text", "")})
    return clean


def save_scene_script(project_path: Path, scene_id: str, payload: dict) -> dict:
    """Save a person's edit of one scene's script. One transaction.

    payload = {
      base_hash: str,                        # from the load this edit is based on
      blocks: [{type, text}],
      heading: {int_ext, place, location (slug|""), time_of_day, forced_heading},
      extra_cast: [character slugs]          # cast added by hand, not via a cue
    }

    Writes the body-only Content, the heading fields, the location link and the
    cast together, so the heading composed at assembly and the scene's fields
    cannot disagree. Does not change `status`.
    """
    from .writes import edit_entity

    if not isinstance(payload, dict):
        raise ScriptError("Request body must be an object.")
    blocks = _validate_blocks(payload.get("blocks"))
    hd = payload.get("heading") or {}
    if not isinstance(hd, dict):
        raise ScriptError("`heading` must be an object.")

    conn = get_db(project_path)
    try:
        st = _scene_state(conn, scene_id)
        characters, locations = _registry(conn)
    finally:
        conn.close()

    if payload.get("base_hash") != content_hash(st):
        raise ScriptConflict(content_hash(st))
    if st["status"] == "locked":
        raise ScriptLocked("This scene is locked. Unlock it before editing.")

    fields = _heading_fields(hd, locations)

    # Cast: who the script names (registered), plus whoever is added by hand.
    by_id = {c["id"]: c for c in characters}
    extra_cast = payload.get("extra_cast") or []
    bad = [c for c in extra_cast if c not in by_id]
    if bad:
        raise ScriptError(f"Character not found: {', '.join(bad)}")
    cast_ids = [c["id"] for c in ss.script_cast(blocks, characters) if c["id"]]
    cast = list(dict.fromkeys(cast_ids + list(extra_cast)))

    data = {"Content": ss.serialize_blocks(blocks), **fields, "characters": cast}
    previous = st["raw_content"]
    try:
        result = edit_entity(
            project_path, "scene", scene_id, data,
            "Script edited by hand in the script editor")
    except ValueError as e:
        # The write boundary refuses a scene whose merged state has no heading.
        raise ScriptError(str(e))
    if result.get("success") is False or result.get("error"):
        raise ScriptError(result.get("error") or result.get("message") or "Save failed.")

    fresh = load_scene_script(project_path, scene_id)
    fresh["previous_content"] = previous  # lets the client offer an in-session undo
    return fresh
