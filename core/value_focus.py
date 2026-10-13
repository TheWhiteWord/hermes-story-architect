"""Computed value focus: which values are major and minor in a unit.

A unit is a plot, a sequence, an act or the whole story. A value "shifts" in
a scene when one of the scene's value_turns names it; a scene counts once per
value however many turns of that value it carries. Nothing is stored — every
call recounts from the scenes, so the answer can never drift from them.

One helper (`get_scene_value_turns`, core/db.py) reads every scene's turns
with the plot, act and sequence they sit in; this module filters that one
list per unit scope. Major is the most frequent values, ties at the cut all
major; minor is the rest. Story scope follows the plot scopes: major is the
main plot's major list, minor is the subplots' major values not already
major (design §4).
"""
from collections import defaultdict

from .constants import VALUE_MAJOR_COUNT
from .db import get_scene_value_turns


def _counts(rows, key) -> dict:
    """Distinct scenes per value among the rows matching `key`'s value.

    A scene counts once per value: two turns of the same value in one scene
    are one scene. `rows` are the turns from `get_scene_value_turns`.
    """
    scenes = defaultdict(set)
    for row in rows:
        if key(row):
            scenes[row["value"]].add(row["scene_id"])
    return {value: len(scene_ids) for value, scene_ids in scenes.items()}


def _major_minor(counts: dict) -> dict:
    """Split value→scene-count into the major/minor shape, by frequency.

    Ties at the cut are all major: if the 3rd and 4th most frequent values
    have the same count, both are major (design §4). Order is count desc,
    then value name, so the output is stable across calls. Fewer than
    VALUE_MAJOR_COUNT values means every value is major; none means both
    lists are empty.
    """
    ordered = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    if len(ordered) < VALUE_MAJOR_COUNT:
        major = ordered
    else:
        cut = ordered[VALUE_MAJOR_COUNT - 1][1]
        major = [kv for kv in ordered if kv[1] >= cut]
    minor = [kv for kv in ordered if kv not in major]
    return {"major": [{"value": v, "scenes": n} for v, n in major],
            "minor": [{"value": v, "scenes": n} for v, n in minor]}


def _plot_scopes(project_path) -> dict:
    """Plot id → plot_scope ('main'/'sub'/''), read from the entities."""
    import json
    import sqlite3
    db_path = project_path / ".story" / "story.db"
    conn = sqlite3.connect(str(db_path))
    try:
        rows = conn.execute(
            "SELECT id, extra FROM entities WHERE type='plot' AND is_deleted=0"
        ).fetchall()
    finally:
        conn.close()
    return {pid: (json.loads(extra) or {}).get("plot_scope", "")
            for pid, extra in rows}


def for_plot(project_path, plot_id) -> dict:
    """Value focus of one plot: the turns in that plot's scenes only."""
    rows = get_scene_value_turns(project_path)
    return _major_minor(_counts(rows, lambda r: r["plot"] == plot_id))


def for_sequence(project_path, seq_id) -> dict:
    """Value focus of one sequence: its scenes, all plots together."""
    rows = get_scene_value_turns(project_path)
    return _major_minor(_counts(rows, lambda r: r["sequence_id"] == seq_id))


def for_act(project_path, act_id) -> dict:
    """Value focus of one act: all its sequences' scenes, all plots together."""
    rows = get_scene_value_turns(project_path)
    return _major_minor(_counts(rows, lambda r: r["act_id"] == act_id))


def for_project(project_path) -> dict:
    """Value focus of the story: the main plot's majors, plus the subplots'
    major values that are not already major as minor (design §4).

    With no main plot every plot is treated as one subplot, so the story
    still reports the subplots' major values rather than nothing.
    """
    rows = get_scene_value_turns(project_path)
    scopes = _plot_scopes(project_path)
    main = _major_minor(_counts(
        rows, lambda r: scopes.get(r["plot"]) == "main"))
    major_names = {item["value"] for item in main["major"]}
    minor_counts = {}
    for plot_id, scope in scopes.items():
        if scope == "main":
            continue
        sub = _major_minor(_counts(rows, lambda r, p=plot_id: r["plot"] == p))
        for item in sub["major"]:
            if item["value"] not in major_names:
                minor_counts[item["value"]] = max(
                    minor_counts.get(item["value"], 0), item["scenes"])
    minor = [{"value": v, "scenes": n} for v, n in sorted(
        minor_counts.items(), key=lambda kv: (-kv[1], kv[0]))]
    return {"major": main["major"], "minor": minor}
