"""Reordering the story's structure by hand: acts, sequences and scenes.

The Scenes tab's Reorder mode edits a COPY of the tree and sends the whole target
shape back. Three steps, all here, so the browser holds no rules:

  * `load_tree` — the current shape, plus a `version` that changes whenever any
    act, sequence or scene is added, removed or moved. A plan or an apply made
    against an older version is refused (the agent may have changed things).
  * `plan`      — validates the target shape and lists what MOVES, in words.
    Only the items that actually moved are listed: if one scene jumps from 3rd to
    7th, the four it passed are not "changed". (Longest increasing subsequence.)
  * `apply`     — writes it through `core.writes`, the agent's own path, in an
    order that keeps the three levels consistent: sequences into their new acts
    first, then each scene into its new sequence AND act (a scene carries its act
    as a denormalised shortcut, and `edit_entity` would not otherwise update it),
    then the renumbering.

Nothing is invented: a move is `edit_entity`, a renumber is `reorder`.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .db import get_db

SUMMARY = "Reordered by hand"


class StructureError(ValueError):
    """Something in the requested shape cannot be applied. Message is user-facing."""


class StructureConflict(StructureError):
    def __init__(self, current_version: str):
        super().__init__("The structure changed since you opened Reorder — probably by the agent.")
        self.current_version = current_version


# ─── Reading ─────────────────────────────────────────────────────────────────

def _rows(conn):
    acts = conn.execute("SELECT id, name, order_key FROM entities WHERE type='act' AND is_deleted=0 "
                        "ORDER BY order_key, name, id").fetchall()
    seqs = conn.execute("SELECT id, name, parent_id FROM entities WHERE type='sequence' AND is_deleted=0 "
                        "ORDER BY order_key, name, id").fetchall()
    scenes = conn.execute("SELECT id, name, parent_id, extra FROM entities WHERE type='scene' AND is_deleted=0 "
                          "ORDER BY order_key, name, id").fetchall()
    return acts, seqs, scenes


def _shape(acts, seqs, scenes) -> dict:
    tree = {"acts": [], "unassigned": []}
    by_act = {a[0]: [] for a in acts}
    for q in seqs:
        if q[2] in by_act:
            by_act[q[2]].append({"id": q[0], "title": q[1] or q[0], "scenes": []})
    seq_node = {q["id"]: q for qs in by_act.values() for q in qs}
    for sc in scenes:
        ex = json.loads(sc[3]) if sc[3] else {}
        node = {"id": sc[0], "title": sc[1] or sc[0], "heading": ex.get("heading") or ""}
        if sc[2] in seq_node:
            seq_node[sc[2]]["scenes"].append(node)
        else:
            tree["unassigned"].append(node)
    for a in acts:
        tree["acts"].append({"id": a[0], "title": a[1] or a[0], "sequences": by_act[a[0]]})
    return tree


def _version(tree: dict) -> str:
    flat = [[a["id"], [[q["id"], [s["id"] for s in q["scenes"]]] for q in a["sequences"]]] for a in tree["acts"]]
    flat.append([s["id"] for s in tree["unassigned"]])
    return hashlib.sha256(json.dumps(flat).encode()).hexdigest()[:16]


def load_tree(project_path: Path) -> dict:
    conn = get_db(project_path)
    try:
        tree = _shape(*_rows(conn))
    finally:
        conn.close()
    tree["version"] = _version(tree)
    return tree


# ─── Planning ────────────────────────────────────────────────────────────────

def _lis_keep(old_positions: list[int | None]) -> set[int]:
    """Indices of the longest increasing run among entries that have an old position.

    These are the items that did not move relative to each other; everything else
    in the list is what the person actually moved.
    """
    idx = [i for i, p in enumerate(old_positions) if p is not None]
    best: dict[int, tuple[int, int | None]] = {}        # i -> (length, previous i)
    for pos, i in enumerate(idx):
        length, prev = 1, None
        for j in idx[:pos]:
            if old_positions[j] < old_positions[i] and best[j][0] + 1 > length:
                length, prev = best[j][0] + 1, j
        best[i] = (length, prev)
    if not best:
        return set()
    end = max(best, key=lambda i: best[i][0])
    keep = set()
    while end is not None:
        keep.add(end)
        end = best[end][1]
    return keep


def _validate_target(cur: dict, target) -> dict:
    """The requested shape, checked against what exists. Returns it normalised."""
    if not isinstance(target, dict) or not isinstance(target.get("acts"), list):
        raise StructureError("The order sent was not understood. Reload and try again.")
    cur_acts = {a["id"] for a in cur["acts"]}
    cur_seqs = {q["id"] for a in cur["acts"] for q in a["sequences"]}
    cur_assigned = {s["id"] for a in cur["acts"] for q in a["sequences"] for s in q["scenes"]}
    cur_unassigned = {s["id"] for s in cur["unassigned"]}

    seen_a, seen_q, seen_s = [], [], []
    acts = []
    for a in target["acts"]:
        if not isinstance(a, dict) or not isinstance(a.get("sequences"), list):
            raise StructureError("The order sent was not understood. Reload and try again.")
        seqs = []
        for q in a["sequences"]:
            if not isinstance(q, dict) or not isinstance(q.get("scenes"), list):
                raise StructureError("The order sent was not understood. Reload and try again.")
            seen_s += [str(x) for x in q["scenes"]]
            seqs.append({"id": str(q.get("id")), "scenes": [str(x) for x in q["scenes"]]})
        seen_a.append(str(a.get("id")))
        seen_q += [q["id"] for q in seqs]
        acts.append({"id": str(a.get("id")), "sequences": seqs})

    def dupes(xs):
        return sorted({x for x in xs if xs.count(x) > 1})
    for kind, xs in (("act", seen_a), ("sequence", seen_q), ("scene", seen_s)):
        if dupes(xs):
            raise StructureError(f"A {kind} appears in two places: {', '.join(dupes(xs))}.")
    if set(seen_a) != cur_acts or set(seen_q) != cur_seqs:
        raise StructureError("Acts and sequences can be moved here, not added or removed. "
                             "Reload and try again.")
    unknown = set(seen_s) - cur_assigned - cur_unassigned
    if unknown:
        raise StructureError(f"Not found: {', '.join(sorted(unknown))}.")
    lost = cur_assigned - set(seen_s)
    if lost:
        raise StructureError("A scene can't be taken out of the story here: "
                             + ", ".join(sorted(lost)) + ".")
    return {"acts": acts}


def _index(tree: dict) -> dict:
    """Where everything is now: id -> (parent id, position)."""
    where = {}
    for i, a in enumerate(tree["acts"]):
        where[a["id"]] = (None, i)
        for j, q in enumerate(a["sequences"]):
            where[q["id"]] = (a["id"], j)
            for k, s in enumerate(q["scenes"]):
                where[s["id"]] = (q["id"], k)
    for k, s in enumerate(tree["unassigned"]):
        where[s["id"]] = ("_unassigned", k)
    return where


def plan(project_path: Path, payload: dict) -> dict:
    """Validate a target shape and list what it moves. Writes nothing."""
    cur = load_tree(project_path)
    if (payload or {}).get("base_version") != cur["version"]:
        raise StructureConflict(cur["version"])
    target = _validate_target(cur, payload)
    old = _index(cur)
    title = {a["id"]: a["title"] for a in cur["acts"]}
    for a in cur["acts"]:
        for q in a["sequences"]:
            title[q["id"]] = q["title"]
            for s in q["scenes"]:
                title[s["id"]] = s["title"]
    for s in cur["unassigned"]:
        title[s["id"]] = s["title"]
    act_of_seq = {q["id"]: a["id"] for a in cur["acts"] for q in a["sequences"]}
    for a in target["acts"]:
        for q in a["sequences"]:
            act_of_seq.setdefault(q["id"], a["id"])
    new_act_of_seq = {q["id"]: a["id"] for a in target["acts"] for q in a["sequences"]}

    def where_is(parent, kind):                 # words for a place
        if parent == "_unassigned":
            return "Unassigned"
        if kind == "scene":
            return f"{title[new_act_of_seq.get(parent) or act_of_seq[parent]]} › {title[parent]}"
        return title[parent] if parent else "the story"

    def old_place(eid, kind):
        parent, pos = old[eid]
        if kind == "scene":
            return "Unassigned" if parent == "_unassigned" else \
                f"{title[act_of_seq[parent]]} › {title[parent]} · {pos + 1}"
        if kind == "sequence":
            return f"{title[parent]} · {pos + 1}"
        return f"position {pos + 1}"

    changes = []

    def visit(kind, parent, ids):
        positions = [old[i][1] if old[i][0] == parent else None for i in ids]
        stable = _lis_keep(positions)
        for pos, eid in enumerate(ids):
            if pos in stable:
                continue
            was_parent = old[eid][0]
            new_place = (f"{where_is(parent, kind)} · {pos + 1}" if kind != "act" else f"position {pos + 1}")
            text = f"Move {kind} “{title[eid]}” from {old_place(eid, kind)} to {new_place}"
            changes.append({"type": kind, "id": eid, "title": title[eid], "text": text,
                            "moved": was_parent != parent})

    visit("act", None, [a["id"] for a in target["acts"]])
    for a in target["acts"]:
        visit("sequence", a["id"], [q["id"] for q in a["sequences"]])
        for q in a["sequences"]:
            visit("scene", q["id"], q["scenes"])
    # A sequence that changed act carries its scenes' act with it; say so once.
    for c in changes:
        if c["type"] == "sequence" and c["moved"]:
            n = sum(len(q["scenes"]) for a in cur["acts"] for q in a["sequences"] if q["id"] == c["id"])
            if n:
                c["text"] += f" (its {n} scene{'s' if n != 1 else ''} {'move' if n != 1 else 'moves'} with it)"
    return {"changes": changes, "unchanged": not changes, "target": target, "current": cur}


# ─── Applying ────────────────────────────────────────────────────────────────

def apply(project_path: Path, payload: dict) -> dict:
    """Write a planned shape. Everything is validated first; the writes then go in an
    order that keeps acts, sequences and scenes agreeing with each other."""
    from .writes import edit_entity, reorder

    p = plan(project_path, payload)
    if p["unchanged"]:
        return {"applied": 0, "tree": p["current"], "version": p["current"]["version"]}
    cur, target = p["current"], p["target"]
    old = _index(cur)
    new_act_of_seq = {q["id"]: a["id"] for a in target["acts"] for q in a["sequences"]}
    steps = 0
    try:
        # 1. Sequences into their new acts.
        for q, act in new_act_of_seq.items():
            if old[q][0] != act:
                edit_entity(project_path, "sequence", q, {"act_id": act}, SUMMARY); steps += 1
        # 2. Scenes into their new sequence — and the act that sequence is now in.
        conn = get_db(project_path)
        try:
            cur_act = {sid: (json.loads(ex) if ex else {}).get("act_id", "")
                       for sid, ex in conn.execute("SELECT id, extra FROM entities WHERE type='scene' AND is_deleted=0")}
        finally:
            conn.close()
        for a in target["acts"]:
            for q in a["sequences"]:
                for sid in q["scenes"]:
                    if old[sid][0] != q["id"] or cur_act.get(sid) != a["id"]:
                        edit_entity(project_path, "scene", sid,
                                    {"sequence_id": q["id"], "act_id": a["id"]}, SUMMARY); steps += 1
        # 3. Renumber every list whose membership or order changed.
        for a in target["acts"]:
            ids = [q["id"] for q in a["sequences"]]
            if ids and ids != [q["id"] for ca in cur["acts"] if ca["id"] == a["id"] for q in ca["sequences"]]:
                reorder(project_path, "sequence", ids, SUMMARY); steps += 1
            for q in a["sequences"]:
                before = [s["id"] for ca in cur["acts"] for cq in ca["sequences"] if cq["id"] == q["id"]
                          for s in cq["scenes"]]
                if q["scenes"] and q["scenes"] != before:
                    reorder(project_path, "scene", q["scenes"], SUMMARY); steps += 1
        # 4. Acts have no parent, so `reorder` does not cover them: number them directly.
        act_ids = [a["id"] for a in target["acts"]]
        if act_ids != [a["id"] for a in cur["acts"]]:
            for i, aid in enumerate(act_ids, 1):
                edit_entity(project_path, "act", aid, {"order": i}, SUMMARY); steps += 1
    except ValueError as e:
        raise StructureError(f"Stopped after {steps} change{'s' if steps != 1 else ''}: {e} "
                             f"Reload to see where things stand.")
    tree = load_tree(project_path)
    return {"applied": len(p["changes"]), "tree": tree, "version": tree["version"]}
