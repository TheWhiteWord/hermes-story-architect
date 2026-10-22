"""Track view: one entity's journey across the scenes of a story.

`story_load view='track'` reads a character's path, or the changing state of a
location, world or relationship, scene by scene in story order. It is an
analysis read: the code orders and groups what is recorded, and the reader
judges the escalation.

Nothing is stored for this. Every row is derived from the scenes — their cast,
their `scene_beats` record (driver, objective, true-character moments, closing
changes) and their `value_turns` effects — exactly as `value_focus` derives a
unit's values.

Rows are grouped by act and sequence, so those ids appear once, and a row
exists only for a scene where something is recorded. Appearances with nothing
recorded are counted in `coverage`, not listed. The beats themselves are never
read: the row is what the record says about the scene, not the mechanism.
"""
import json
from collections import defaultdict

from .constants import VALUE_LADDER
from .db import get_db, get_scene_value_turns, scene_order

# The four rungs of a value ladder, shallowest first. `deepest` in the header
# is the deepest of these visited by a value's turns in the scope, so this
# order is the whole meaning of the field.
LADDER_DEPTH = ["p", "c", "cd", "nn"]


def for_entity(project_path, entity_id, act=None, sequence=None, value=None) -> dict:
    """The ordered rows for one entity, grouped by act then sequence.

    `value` narrows the header `values` and every row's `effects` to one
    value. The scope is the whole story unless `act` or `sequence` narrows it.
    """
    conn = get_db(project_path)
    try:
        row = conn.execute(
            "SELECT type FROM entities WHERE id=? AND is_deleted=0",
            (entity_id,)).fetchone()
        if row is None:
            return {"view": "track", "entity": entity_id,
                    "error": f"No entity with id '{entity_id}'."}
        entity_type = row[0]

        scenes = _scenes(conn, act, sequence)
        for scene_id, turns in _turns_for(project_path, set(scenes)).items():
            scenes[scene_id]["turns"] = turns
        _attach_cast(conn, scenes)

        # Which scenes name the entity at all. That set is the coverage and
        # decides which scenes are considered: an appearance with nothing
        # recorded is counted, never listed.
        appears = []
        with_beats = 0
        with_change = 0
        for scene_id in sorted(scenes, key=lambda s: scenes[s]["order"]):
            scene = scenes[scene_id]
            if not _names(scene, entity_id):
                continue
            appears.append(scene_id)
            if scene["beats"]:
                with_beats += 1
            if _change_for(entity_id, scene["beats"]):
                with_change += 1

        out = {
            "view": "track",
            "entity": entity_id,
            "coverage": {
                "appears": len(appears),
                "with_scene_beats": with_beats,
                "with_change": with_change,
            },
        }
        if act or sequence:
            out["scope"] = {"act": act, "sequence": sequence}
        else:
            out["scope"] = "story"
        if value:
            out["value"] = value

        if entity_type == "character":
            out["plots"] = _plots_of(conn, entity_id)
            out["values"] = _value_path(conn, entity_id, scenes, appears, value)

        acts = []
        for scene_id in appears:
            scene_row = _row_for(entity_id, entity_type, scenes[scene_id], value)
            if scene_row is not None:
                _place(scenes[scene_id], scene_row, acts)
        out["acts"] = [a for a in acts if all(s["scenes"] for s in a["sequences"])]
        return out
    finally:
        conn.close()


def _scenes(conn, act, sequence) -> dict:
    """Every scene in the scope, keyed by id, with its beats record.

    The act and sequence ids are carried so the tree can group by them without
    a second pass, and their order keys so a scene's story position is total.
    """
    rows = conn.execute(
        "SELECT e.id, e.parent_id, e.order_key, p.parent_id, p.order_key, "
        "pp.order_key, e.extra, sb.extra FROM entities e "
        "LEFT JOIN entities p ON e.parent_id = p.id "
        "LEFT JOIN entities pp ON p.parent_id = pp.id "
        "LEFT JOIN entities sb ON sb.parent_id = e.id "
        "AND sb.type='scene_beats' AND sb.is_deleted=0 "
        "WHERE e.type='scene' AND e.is_deleted=0").fetchall()
    out = {}
    for scene_id, seq_id, scene_key, act_id, act_key, seq_key, \
            extra_json, beats_json in rows:
        if act and act_id != act:
            continue
        if sequence and seq_id != sequence:
            continue
        out[scene_id] = {
            "id": scene_id,
            "act_id": act_id,
            "sequence_id": seq_id,
            "order": scene_order(act_id, seq_id, scene_id,
                                 act_key, seq_key, scene_key),
            "beats": _json(beats_json),
            "turns": [],
            "cast": [],
            "location": None,
        }
    return out


def _turns_for(project_path, scene_ids) -> dict:
    """The value turns of the given scenes, in the shape `get_scene_value_turns`
    gives — one pass over every scene, filtered to the scope."""
    out = defaultdict(list)
    for turn in get_scene_value_turns(project_path):
        if turn["scene_id"] in scene_ids:
            out[turn["scene_id"]].append(turn)
    return out


def _attach_cast(conn, scenes) -> None:
    """Fill each scene's cast and location from the relations that store them.

    The same rows `get_project_summary` reads, so the two agree on who is in a
    scene. A scene with no cast relation is a scene with no cast.
    """
    for from_id, to_id, kind in conn.execute(
            "SELECT from_id, to_id, kind FROM relations "
            "WHERE kind IN ('character_scene', 'location_scene')"):
        scene = scenes.get(to_id)
        if scene is None:
            continue
        if kind == "character_scene":
            scene["cast"].append(from_id)
        else:
            scene["location"] = from_id


def _names(scene, entity_id) -> bool:
    """True when the scene records the entity anywhere: cast, driver, a
    true-character moment, an effect, as the scene's location, or as an entry
    in the record's closing `changes`."""
    beats = scene["beats"]
    if entity_id in scene["cast"] or scene["location"] == entity_id:
        return True
    if entity_id == beats.get("driver"):
        return True
    if entity_id in [c.get("character", "")
                     for c in beats.get("true_character") or []]:
        return True
    if entity_id in [c.get("entity", "")
                     for c in beats.get("changes") or []]:
        return True
    return any(t["character"] == entity_id
               for turn in scene["turns"] for t in turn["effects"])


def _change_for(entity_id, beats) -> list:
    """The entity's entries in the record's `changes`, in written order."""
    return [c.get("change", "") for c in beats.get("changes") or []
            if isinstance(c, dict) and c.get("entity") == entity_id
            and c.get("change")]


def _plots_of(conn, character_id) -> list:
    """The plots the character is a protagonist of, story order.

    `plot.characters` is the declaration, so the list is read from the plot
    rows: the relation records which scenes a plot reaches, not who its
    protagonists are.
    """
    out = []
    for plot_id, extra_json in conn.execute(
            "SELECT id, extra FROM entities WHERE type='plot' "
            "AND is_deleted=0 ORDER BY order_key, id"):
        if character_id in (_json(extra_json).get("characters") or []):
            out.append(plot_id)
    return out


def _value_path(conn, character_id, scenes, appears, value) -> list:
    """Per value: the first state, the deepest rung and the last state.

    Read from the turns whose effects name this character, in story order.
    `deepest` is the deepest rung visited anywhere in the scope, across both
    `from` and `to` — which is what makes a P earned rather than naive.
    """
    lines = defaultdict(list)
    for scene_id in appears:
        for turn in scenes[scene_id]["turns"]:
            if value and turn["value"].strip().lower() != value.strip().lower():
                continue
            if not any(e["character"] == character_id for e in turn["effects"]):
                continue
            lines[turn["value"]].append(turn)

    out = []
    for name in sorted(lines):
        line = lines[name]
        words = _rung_words(conn, name)
        # `from` first, then `to`, in story order — the value's path through
        # the scope. `deepest` is the deepest rung VISITED, so the scan goes
        # deep first and reports the first word of that rung in the path.
        visited = [w for turn in line for w in (turn["from"], turn["to"])]
        deepest = ""
        for rung in reversed(LADDER_DEPTH):
            hit = next((w for w in visited if _word_is(words, rung, w)), None)
            if hit:
                deepest = hit
                break
        out.append({"value": name,
                    "from": line[0]["from"],
                    "deepest": deepest,
                    "to": line[-1]["to"]})
    return out


def _rung_words(conn, value_name) -> dict:
    """The four rung words of a value, keyed by rung. Empty when undefined."""
    for _, name, extra_json in conn.execute(
            "SELECT id, name, extra FROM entities WHERE type='value' "
            "AND is_deleted=0"):
        if str(name or "").strip().lower() == value_name.strip().lower():
            extra = _json(extra_json)
            return {rung: str(extra.get(rung) or "").strip()
                    for rung in VALUE_LADDER}
    return {}


def _word_is(words: dict, rung: str, word) -> bool:
    word = str(word or "").strip().lower()
    return bool(word) and word == str(words.get(rung) or "").strip().lower()


def _row_for(entity_id, entity_type, scene, value):
    """The row for one scene, or None when nothing about the entity is recorded.

    A location, world or relationship reduces to `scene` and `change`; a
    character also carries its driving, its true-character moments and the
    effects the value turns record for it.
    """
    beats = scene["beats"]
    row = {"scene": scene["id"]}

    change = _change_for(entity_id, beats)
    if change:
        # More than one entry is one sentence each; joined, not nested, so the
        # row stays a line of prose the reader can follow.
        row["change"] = "; ".join(change)

    if entity_type != "character":
        return row if len(row) > 1 else None

    # `driver` fires when the character drives the scene AND is in its cast: a
    # driver outside the cast is a record of a scene they are not in, and the
    # row would claim a presence the scene does not have.
    if entity_id in scene["cast"] and entity_id == beats.get("driver"):
        row["driver"] = True
        objective = beats.get("scene_objective") or ""
        if objective:
            row["scene_objective"] = objective

    for moment in beats.get("true_character") or []:
        if isinstance(moment, dict) and moment.get("character") == entity_id:
            entry = {k: moment[k] for k in ("dilemma", "choice_reveals")
                     if moment.get(k)}
            if entry:
                row["true_character"] = entry

    effects = _effects_for(entity_id, scene["turns"], value)
    if effects:
        row["effects"] = effects

    return row if len(row) > 1 else None


def _effects_for(character_id, turns, value) -> dict:
    """Value, then conflict level, then the effect sentence.

    The keys are the value names and the level names, so the real field names
    (`conflict_level`, `effect`) are not repeated on every entry. The turn's
    `character`, `plot`, `from` and `to` are left out as repetition: the
    character is the entity, the plot is in the header, and `from`/`to` belong
    to the turn and are reported in the header `values` and `view=values`.
    """
    out = {}
    for turn in turns:
        if value and turn["value"].strip().lower() != value.strip().lower():
            continue
        for effect in turn["effects"]:
            if effect.get("character") != character_id:
                continue
            levels = {level["conflict_level"]: level["effect"]
                      for level in effect["levels"] if level.get("effect")}
            if not levels:
                continue
            # One value can turn under two plots in one scene, and the two
            # turns are distinct evidence: the second is keyed by its plot so
            # neither is silently dropped.
            key = turn["value"]
            if key in out:
                key = f"{turn['value']} ({turn['plot']})"
            out[key] = levels
    return out


def _place(scene, row, acts) -> None:
    """Insert a row into the act/sequence tree, creating the groups as needed.

    A scene with no sequence has no act to group under, so the empty string is
    the key: the row still reads, at the position its order gives it, rather
    than vanishing into a named bucket.
    """
    act_id = scene["act_id"] or ""
    seq_id = scene["sequence_id"] or ""
    for act in acts:
        if act["act"] == act_id:
            break
    else:
        act = {"act": act_id, "sequences": []}
        acts.append(act)
    for seq in act["sequences"]:
        if seq["sequence"] == seq_id:
            break
    else:
        seq = {"sequence": seq_id, "scenes": []}
        act["sequences"].append(seq)
    seq["scenes"].append(row)


def _json(blob) -> dict:
    return json.loads(blob) if blob else {}
