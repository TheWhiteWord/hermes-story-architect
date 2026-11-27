"""What changed between two states: entities, order, script, and the items.

One pass, because three readers consume it and none may disagree. §6.2's script
view is a lens over the same items, never a second engine, and §7.2's planner
selects from the items this module emits.

  * ``entities`` — per id, ``added`` / ``removed`` / ``unchanged`` / ``changed``,
    with each changed field and section as ``(a, b)``;
  * ``order``    — per parent, the two child id lists. Order is not a field
    (`logical.order_of`), so a diff of the shapes alone cannot see a reorder.
    Acts are excluded: §5.2 treats act order as part of the act entity's fields,
    and it is in the shape as one.
  * ``script``   — per scene, ``added`` / ``removed`` / ``moved`` / ``edited`` /
    ``unchanged`` with its placement, its composed text and a line diff, plus the
    item keys its group stands for;
  * ``items``    — the flat list the planner builds a selection on.

Two things the shapes alone get wrong, both settled here rather than in a caller:
a field `refmap` declares derived is in the shape twice (a role edit is one edit
of `scene.plot_roles`, but the plot's read-side list moves with it), so it is not
reported; and a plain id-list field is unordered, so it is diffed per element.

A scene's script text is composed here from its materialized fields, not read
from `get_screenplay_text`, which drops every scene whose `Content` is empty. A
heading-only scene is a scene in the entity view and would silently vanish from
the script view.
"""

from __future__ import annotations

import difflib
from pathlib import Path

from ..db import get_db
from .. import scene_script
from ..scene_script import scene_heading
from . import logical, refmap

State = tuple[dict, dict]


def load(project_path: Path) -> State:
    """A project's ``(entities, order)`` — the two shapes a diff compares.

    Takes a project path like every read function (F10), so a draft is compared
    through the copy `view.project_view` hands out and no frozen file is opened.
    """
    conn = get_db(project_path)
    try:
        return logical.materialize(conn), logical.order_of(conn)
    finally:
        conn.close()


def text_diff(a: str, b: str) -> list[str]:
    """Line-level diff of two texts; empty when they are equal."""
    if a == b:
        return []
    return list(difflib.unified_diff(a.splitlines(), b.splitlines(), "a", "b", lineterm=""))


def compare(a: Path, b: Path) -> dict:
    """Everything that differs between the projects at `a` and `b`."""
    return compare_states(load(a), load(b))


def compare_states(a: State, b: State) -> dict:
    """`compare` over two already-loaded states.

    The planner holds all three states of a merge and compares two pairs, so it
    must not materialize the base twice more to do it.
    """
    entities_a, order_a = a
    entities_b, order_b = b
    entities = _entities(entities_a, entities_b)
    order = _order(order_a, order_b)
    return {
        "entities": entities,
        "order": order,
        "items": _items(entities, order),
        "script": _script(entities, order, entities_a, entities_b, order_a, order_b),
    }


# ─── per-entity fields and sections ──────────────────────────────────────────


def _derived(entity_type: str) -> set[str]:
    """`refmap`'s derived paths for a type: in the shape, not authored there."""
    return {path for path, _ in refmap.DERIVED.get(entity_type, ())}


def _list_sites(entity_type: str) -> set[str]:
    """Fields holding a plain id list — a site declared as `field[]`."""
    return {site.path[:-2] for site in refmap.sites(entity_type) if site.path.endswith("[]")}


def _changed_fields(a: dict, b: dict) -> dict:
    entity_type = a["type"]
    derived = _derived(entity_type)
    lists = _list_sites(entity_type)
    out = {}
    for name in a["fields"].keys() | b["fields"].keys():
        old, new = a["fields"].get(name), b["fields"].get(name)
        if name in derived or old == new:
            continue
        if name in lists and isinstance(old, list) and isinstance(new, list):
            # An id list is a set: the same ids in another order are the same
            # state, so what changed is which ids are in it.
            out[name] = {
                "a": old,
                "b": new,
                "added": sorted(set(new) - set(old)),
                "removed": sorted(set(old) - set(new)),
            }
        else:
            out[name] = {"a": old, "b": new}
    return out


def _changed_sections(a: dict, b: dict) -> dict:
    out = {}
    for name in a["sections"].keys() | b["sections"].keys():
        old, new = a["sections"].get(name, ""), b["sections"].get(name, "")
        if old != new:
            out[name] = {"a": old, "b": new, "diff": text_diff(old, new)}
    return out


def _entities(a: dict, b: dict) -> dict[str, dict]:
    out = {}
    for entity_id in sorted(a.keys() | b.keys()):
        old, new = a.get(entity_id), b.get(entity_id)
        if new is None:
            out[entity_id] = {"id": entity_id, "type": old["type"], "status": "removed"}
        elif old is None:
            out[entity_id] = {"id": entity_id, "type": new["type"], "status": "added"}
        else:
            fields, sections = _changed_fields(old, new), _changed_sections(old, new)
            out[entity_id] = {
                "id": entity_id,
                "type": new["type"],
                "status": "changed" if fields or sections else "unchanged",
                "fields": fields,
                "sections": sections,
            }
    return out


# ─── child order ─────────────────────────────────────────────────────────────


def _order(a: dict, b: dict) -> dict[str, dict]:
    """Per parent, the two id lists — scenes and sequences only (§5.2)."""
    return {
        key: {"a": a.get(key, []), "b": b.get(key, [])}
        for key in sorted(a.keys() | b.keys())
        if not key.startswith("act:") and a.get(key) != b.get(key)
    }


# ─── script ──────────────────────────────────────────────────────────────────


def _story_order(entities: dict, order: dict) -> list[str]:
    """Every scene, in story order: act, then sequence, then scene."""
    out = []
    for act in order.get("act:", []):
        for sequence in order.get(f"sequence:{act}", []):
            out.extend(order.get(f"scene:{sequence}", []))
    return [s for s in out if entities.get(s, {}).get("type") == "scene"]


def _placement(entities: dict, order: dict, entity_id: str) -> dict:
    """Where a scene sits: act, sequence, 1-based position in the sequence."""
    sequence = entities[entity_id]["fields"].get("sequence_id") or ""
    siblings = order.get(f"scene:{sequence}", [])
    act = entities.get(sequence, {}).get("fields", {}).get("act_id") or ""
    return {
        "act": act,
        "sequence": sequence,
        "position": siblings.index(entity_id) + 1 if entity_id in siblings else None,
    }


def _numbers(entities: dict, order: dict) -> dict[str, int]:
    """Each scene's number in the composed screenplay: its rank among scenes with text.

    The assembly (`db._screenplay_rows`) leaves out a scene whose `Content` is empty, so
    such a scene has no number, and the scenes after it count one fewer.
    """
    with_text = [
        s for s in _story_order(entities, order) if entities[s]["sections"].get("Content", "") != ""
    ]
    return {scene_id: n for n, scene_id in enumerate(with_text, 1)}


def _blocks(text: str | None) -> list[dict] | None:
    """A scene's script entry as screenplay blocks: its heading, then what `scene_script`
    makes of the body."""
    if text is None:
        return None
    heading, body = scene_script.split_heading(text)
    head = [{"type": "heading", "text": heading}] if heading else []
    return head + scene_script.parse_blocks(body)


def _text(entities: dict, entity_id: str) -> str:
    """A scene's script entry, composed the way the screenplay assembly does."""
    fields = entities[entity_id]["fields"]
    location = entities.get(fields.get("location") or "", {}).get("fields", {}).get("name", "")
    heading = scene_heading(
        fields.get("int_ext", ""),
        location,
        fields.get("place", ""),
        fields.get("time_of_day", ""),
        fields.get("forced_heading", ""),
    )
    body = entities[entity_id]["sections"].get("Content", "")
    return "\n\n".join(part for part in (heading, body) if part)


def _script(
    diff: dict, order_diff: dict, a: dict, b: dict, order_a: dict, order_b: dict
) -> list[dict]:
    """One row per scene, in the second state's story order, then the removed ones."""
    in_b = _story_order(b, order_b)
    numbers = {"a": _numbers(a, order_a), "b": _numbers(b, order_b)}
    gone = [i for i, row in diff.items() if row["type"] == "scene" and row["status"] == "removed"]
    rows = []
    for entity_id in in_b + gone:
        old, new = a.get(entity_id), b.get(entity_id)
        placement = {
            "a": _placement(a, order_a, entity_id) if old else None,
            "b": _placement(b, order_b, entity_id) if new else None,
        }
        text = {
            "a": _text(a, entity_id) if old else None,
            "b": _text(b, entity_id) if new else None,
        }
        if new is None:
            status = "removed"
        elif old is None:
            status = "added"
        elif text["a"] != text["b"]:
            status = "edited"
        elif placement["a"] != placement["b"]:
            status = "moved"
        else:
            status = "unchanged"
        rows.append(
            {
                "id": entity_id,
                "type": "scene",
                "status": status,
                "placement": placement,
                "text": text,
                "blocks": {"a": _blocks(text["a"]), "b": _blocks(text["b"])},
                "number": {
                    "a": numbers["a"].get(entity_id) if old else None,
                    "b": numbers["b"].get(entity_id) if new else None,
                },
                "diff": text_diff(text["a"] or "", text["b"] or "") if status == "edited" else [],
                "items": _scene_items(diff, order_diff, entity_id, status, placement),
            }
        )
    return rows


def _scene_items(
    diff: dict, order_diff: dict, entity_id: str, status: str, placement: dict
) -> list[str]:
    """The item keys a scene-level selection stands for.

    The scene itself, its changed fields and sections, and the order list of the
    sequence it sits in — its placement. Its `scene_beats` record is a dependency
    the planner expands (§7.2), not a diff item; so is a scene brought along with
    a selected field's reference.
    """
    if status in ("added", "removed"):
        return [f"entity:scene:{entity_id}"]
    row = diff[entity_id]
    keys = [f"field:scene:{entity_id}:{name}" for name in row.get("fields") or {}]
    keys += [f"section:scene:{entity_id}:{name}" for name in row.get("sections") or {}]
    sequence = (placement["b"] or {}).get("sequence") or ""
    if f"scene:{sequence}" in order_diff:
        keys.append(f"order:scene:{sequence}")
    return keys


# ─── items ───────────────────────────────────────────────────────────────────


def _items(entities: dict, order: dict) -> list[dict]:
    """The flat list a selection names: one item per create, remove, field,
    section and order list.

    A key only — the change itself is in `entities` / `order`, and repeating the
    section text here would send it twice to every reader.
    """
    items = []
    for entity_id, row in entities.items():
        kind = row["status"] if row["status"] in ("added", "removed") else "entity"
        if kind != "entity":
            items.append(
                {
                    "key": f"entity:{row['type']}:{entity_id}",
                    "kind": kind,
                    "type": row["type"],
                    "id": entity_id,
                }
            )
            continue
        items.extend(
            {
                "key": f"field:{row['type']}:{entity_id}:{name}",
                "kind": "field",
                "type": row["type"],
                "id": entity_id,
                "name": name,
            }
            for name in row.get("fields") or {}
        )
        items.extend(
            {
                "key": f"section:{row['type']}:{entity_id}:{name}",
                "kind": "section",
                "type": row["type"],
                "id": entity_id,
                "name": name,
            }
            for name in row.get("sections") or {}
        )
    for key in order:
        entity_type, parent = key.split(":", 1)
        items.append({"key": f"order:{key}", "kind": "order", "type": entity_type, "id": parent})
    return items
