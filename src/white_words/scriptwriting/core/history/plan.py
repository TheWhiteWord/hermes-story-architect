"""The merge plan: three states in, an ordered op list and its open decisions out.

Base, ours, theirs. For each authored difference it answers §7.3's question — did this
change on my side, on theirs, both, or neither — and everything the table cannot settle
becomes a numbered decision from §7.5 with a conservative default. §7.4's dependency
expansion then drags in what a selection needs, and the result is an op list in the
`core.drafts` vocabulary with §7.7.2's execution order attached.

Nothing here writes. The plan is a description the executor (T8) applies, so a caller can
show it, refuse it, or re-derive it from a changed selection without any state moving.

Three facts this module's shape follows from:

  * ``diff`` reports an added entity as a key and identity only, so an incoming entity's
    content comes from `theirs`' own materialized shape — loaded here, once per side.
  * An entity id is global across types and is refused at create even while the row sits
    in the trash, so "the id is in your bin" (D6) is a restore-then-edit, never a create.
  * The target's trash is invisible to `logical.materialize`, so D6 needs its own query.

An item's key is the diff's (§6.1/T6): `entity:<type>:<id>`, `field:…`, `section:…`,
`order:<type>:<parent>`. A decision's key is that plus its code, so a stored choice
survives a re-plan.
"""

from __future__ import annotations

import re
import sqlite3
from contextlib import closing
from pathlib import Path

from ..constants import PLOT_ROLES, UNIQUE_PLOT_ROLES
from ..db import get_db
from ..trash import restore_check
from . import diff, refmap, fingerprint

# §7.5's catalogue plus D9 (T7's addition: one side deleted what the other edited).
# `options` is what a caller offers, in order, the default first.
CATALOGUE: dict[str, dict] = {
    "D1": {
        "kind": "same_id_both_sides",
        "options": ("keep-mine", "keep-both", "combine", "take-theirs"),
        "default": "keep-mine",
    },
    "D2": {"kind": "conflict", "options": ("mine", "theirs", "custom"), "default": "mine"},
    "D3": {
        "kind": "placement",
        "options": ("after-predecessor", "before-successor", "pick"),
        "default": "after-predecessor",
        # §7.5: a proposal, and "override always allowed". The default is applied and
        # the position is reported; it never blocks Apply.
        "optional": True,
    },
    "D4": {
        "kind": "role_collision",
        "options": ("mine", "theirs", "replace", "custom"),
        "default": "mine",
    },
    "D5": {
        "kind": "missing_reference",
        "options": ("bring", "drop", "cancel"),
        # §7.4.2: bring it, drop it where optional, or cancel. The default (bring) only
        # ADDS to the target and is undone by deleting, so it does not block Apply —
        # unlike D1/D2/D4/D9, whose defaults drop content a user might want.
        "default": "bring",
        "optional": True,
    },
    "D6": {"kind": "in_trash", "options": ("restore", "cancel"), "default": "restore"},
    "D7": {"kind": "order_conflict", "options": ("mine", "theirs", "custom"), "default": "mine"},
    "D8": {
        "kind": "cleanup",
        "options": ("keep", "delete"),
        "default": "keep",
        # §7.4: optional cleanup, unticked. An unoffered option cannot block Apply.
        "optional": True,
    },
    "D9": {
        "kind": "deleted_and_changed",
        "options": ("keep-mine", "take-theirs"),
        "default": "keep-mine",
    },
}

# A default, or an agent's suggestion, leaves the decision outstanding: §7.7.3 keeps
# Apply disabled until somebody with a name chose.
UNANSWERED = ("default", "agent-suggested")

# §7.7.2's execution order. `sorted_ops` cannot express it: its create-before-delete
# order breaks Replace and a Theirs-swap, where the incoming scene cannot take a
# singular role while the old holder still has it.
PHASE = {"restore": 0, "release": 1, "delete": 2, "create": 3, "edit": 4, "reorder": 5}

# A create is emitted in dependency order, or the validators refuse it (§5.1).
CREATE_ORDER = (
    "world",
    "value",
    "project",
    "character",
    "location",
    "plot",
    "relationship",
    "act",
    "sequence",
    "scene",
    "scene_beats",
)

# An `order_of` key is `child_type:<parent_id>`, so its prefix names the CHILD and the
# container's own type comes from here.
PARENT_TYPE = {"scene": "sequence", "sequence": "act", "act": ""}


# ─── entry point ────────────────────────────────────────────────────────────


def plan(
    base: Path,
    ours: Path,
    theirs: Path,
    *,
    selection=None,
    decisions=None,
) -> dict:
    """Plan bringing changes from `theirs` into the head at `ours`, through `base`.

    `selection` is the set of item keys to apply; nothing outside it is applied, and a
    dependency of a selected item is pulled in by §7.4's rules. `decisions` maps a
    decision key to a choice — `{"choice": …, "set_by": …}` or a bare string, which reads
    as a user's answer.

    Returns ``{"items", "decisions", "open", "ops", "ready", "fingerprint"}``:

      * ``items``     — every difference, classified, with both sides' values;
      * ``decisions`` — every decision the plan had to make, defaults included;
      * ``open``      — the ones still unanswered, which is what disables Apply;
      * ``ops``       — the ordered op list, with every default already applied, so a
        caller can preview exactly what Apply would do;
      * ``ready``     — False while a decision is unanswered. §7.7.3 disables Apply on
        `ready`, not on `ops`: a preview of the default plan is the point of a preview;
      * ``fingerprint`` — the target's state at plan time. §7.7.4's stale-plan guard
        compares it against the target before applying; carried on the plan so a caller
        cannot forget to pass it.
    """
    ours_state = diff.load(ours)
    with closing(get_db(ours)) as conn:
        trashed = _trashed(conn)
        target_fingerprint = fingerprint.of_conn(conn)
    ctx = _Context(
        states={"base": diff.load(base), "ours": ours_state, "theirs": diff.load(theirs)},
        target=ours,
        trashed=trashed,
        chosen=_answers(decisions),
        wanted=set(selection or ()),
    )
    ctx.items = _classify(ctx)
    classified = len(ctx.decisions)
    _build(ctx)
    # A conflict nobody selected needs no answer: what stays is `mine`, which is what
    # Apply would leave anyway. Only the decisions raised while building selected items
    # (index `classified` onward) and the classified ones the selection reached remain.
    reached = {_entity_key(k) for k in ctx.wanted}
    ctx.decisions[:] = [
        d
        for i, d in enumerate(ctx.decisions)
        if i >= classified or d["item"] in ctx.wanted or d["item"] in reached
    ]
    open_keys = [
        d["key"]
        for d in ctx.decisions
        if d["error"] or (d["set_by"] in UNANSWERED and not CATALOGUE[d["code"]].get("optional"))
    ]
    return {
        "items": ctx.items,
        "decisions": ctx.decisions,
        "open": open_keys,
        "ops": ctx.ops,
        "ready": not open_keys,
        "fingerprint": target_fingerprint,
    }


def _entity_key(key: str) -> str:
    """The entity an item key belongs to: `field:scene:x:place` is part of `entity:scene:x`.

    A decision about the entity itself (deleted on one side, edited on the other) is
    reached by selecting any of its parts.
    """
    kind, _, rest = key.partition(":")
    if kind in ("field", "section"):
        entity_type, _, rest = rest.partition(":")
        return f"entity:{entity_type}:{rest.split(':', 1)[0]}"
    return key


class _Context:
    """One plan's working state, shared by the passes so each stays small."""

    def __init__(self, *, states, target, trashed, chosen, wanted):
        self.b, self.o, self.t = (states[k] for k in ("base", "ours", "theirs"))
        self.ours_view = diff.compare_states(self.b, self.o)
        self.theirs_view = diff.compare_states(self.b, self.t)
        self.target = target  # the project path the target head lives at
        self.trashed = trashed  # id → type, from the target's bin
        self.chosen = chosen  # decision key → (choice, set_by)
        self.wanted = wanted
        self.items: list[dict] = []
        self.decisions: list[dict] = []
        self.ops: list[dict] = []
        self.arriving: dict[str, list[str]] = {}  # parent order key → ids entering
        self.leaving: dict[str, set[str]] = {}
        self.take_order: dict[str, list[str]] = {}
        self.cancelled: set[str] = set()
        self.planned_creates: set[str] = set()  # ids this plan already emits a create for
        self.placement_checks: list[tuple[str, str, str]] = []  # deferred D3 checks
        self.released: set[tuple[str, str, str]] = set()  # (scene, plot, role) let go
        # The item key whose expansion is emitting ops right now; an op's `source`
        # defaults to it (§7.7.3's failure-to-decision mapping).
        self.source: str | None = None

    # ── decisions ──

    def decide(self, code, subject, *, detail=None, options=None, default=None) -> tuple[str, str]:
        """Register one decision; return `(key, choice)`.

        One decision per `(code, subject)`: a second request for the same pair — a
        whole-value role list checked twice, say — answers with the first one's result
        rather than adding a duplicate row.
        """
        key = f"{subject}#{code}"
        for existing in self.decisions:
            if existing["key"] == key:
                return key, existing["choice"]
        entry = CATALOGUE[code]
        choice, set_by, value = self.chosen.get(key, (None, "default", None))
        if choice is None or choice not in (options or entry["options"]):
            choice = default or entry.get("default") or entry["options"][0]
        self.decisions.append(
            {
                "key": key,
                "code": code,
                "kind": entry["kind"],
                "item": subject,
                "options": list(options or entry["options"]),
                "default": entry.get("default") or entry["options"][0],
                "choice": choice,
                "set_by": set_by,
                "value": value,
                "error": None,
                **(detail or {}),
            }
        )
        return key, choice

    def decision(self, key: str) -> dict:
        return next(d for d in self.decisions if d["key"] == key)

    def reject(self, key: str, message: str) -> None:
        """A typed value the plan cannot use: the decision stays open and says why."""
        self.decision(key)["error"] = message

    # ── ops ──

    def op(self, phase: str, source=None, **op) -> None:
        """Record one op, tagged with the item or order key that produced it.

        §7.7.3 maps a dry-run failure back to "the decision or item that produced
        it", and a release op acts on the scene that *holds* a role while its
        decision belongs to the scene *arriving* — the op's own type and id name
        the wrong item. The tag is the item key, which is also a decision's
        subject, so a caller can look it up in `items` or `decisions`.
        """
        op["_phase"] = PHASE[phase]
        op["source"] = source if source is not None else self.source
        self.ops.append(op)

    def shape(self, side: str, entity_id: str) -> dict:
        return {"base": self.b, "ours": self.o, "theirs": self.t}[side][0].get(entity_id, {})

    def name(self, side: str, entity_id: str) -> str:
        fields = self.shape(side, entity_id).get("fields", {})
        return fields.get("name") or fields.get("title") or entity_id


def _answers(decisions) -> dict[str, tuple[str, str, object]]:
    """`{key: choice}` or `{key: {choice, set_by, value}}` → `{key: (choice, set_by, value)}`.

    `value` is what a `custom` (or a keep-both's id and fields) was typed as.
    """
    out = {}
    for key, value in (decisions or {}).items():
        if isinstance(value, dict):
            out[key] = (value.get("choice"), value.get("set_by") or "user", value.get("value"))
        else:
            out[key] = (value, "user", None)
    return out


def _trashed(conn: sqlite3.Connection) -> dict[str, str]:
    """The target's bin: id → type. `materialize` cannot see these (§6.1)."""
    rows = conn.execute("SELECT id, type FROM entities WHERE is_deleted=1")
    return {r[0]: r[1] for r in rows}


# ─── classification (§7.3) ──────────────────────────────────────────────────


def _classify(ctx: _Context) -> list[dict]:
    """Every difference between the three states, with its §7.3 verdict."""
    items: list[dict] = []
    for entity_id in sorted(set(ctx.b[0]) | set(ctx.o[0]) | set(ctx.t[0])):
        items.extend(_entity_items(ctx, entity_id))
    for view in (ctx.ours_view, ctx.theirs_view):
        for item in view["items"]:
            if item["key"].startswith("entity:"):
                continue  # the entity's own presence is classified above
            entry = (
                _order_item(ctx, item["key"])
                if item["kind"] == "order"
                else _change_item(ctx, item["key"])
            )
            if entry is not None and not any(i["key"] == entry["key"] for i in items):
                items.append(entry)
    return items


def _entity_items(ctx: _Context, entity_id: str) -> list[dict]:
    """One entity's item, in whichever of the §7.3 shapes it falls into.

    Membership of base / ours / theirs decides it:
      both added          → D1 when they differ, `same` when they do not
      we added it only    → ours already; nothing to bring
      they added it only  → take (D6 when the id is in our bin)
      all three           → its fields and sections are their own items
      they deleted it     → D9 when we changed it, otherwise take the deletion
      we deleted it       → D9 when they changed it, otherwise keep the deletion
      both deleted it     → nothing
    """
    in_b = entity_id in ctx.b[0]
    in_o = entity_id in ctx.o[0]
    in_t = entity_id in ctx.t[0]
    ident = _ident(ctx, entity_id)
    key = f"entity:{ident['type']}:{entity_id}"
    base_item = {"key": key, "kind": "entity", **ident}

    if in_o and in_t and not in_b:
        if _equivalent(ctx.o[0][entity_id], ctx.t[0][entity_id]):
            return [{**base_item, "state": "same"}]
        _, choice = ctx.decide(
            "D1",
            key,
            detail={
                "message": f"“{ctx.name('theirs', entity_id)}” was added on both sides and "
                "they differ.",
                "ours": ctx.o[0][entity_id],
                "theirs": ctx.t[0][entity_id],
                "suggested_id": _new_id(ctx, entity_id),
            },
        )
        return [{**base_item, "state": "conflict", "decision": f"{key}#D1"}]

    if in_o and not in_t:
        if not in_b:
            return [{**base_item, "state": "keep"}]  # only we added it
        if _touches(ctx.ours_view, entity_id):
            _, choice = ctx.decide("D9", key, detail=_d9_detail(ctx, entity_id, "theirs"))
            return [{**base_item, "state": "conflict", "decision": f"{key}#D9"}]
        return [{**base_item, "state": "take", "deletes": True}]

    if in_t and not in_o:
        if not in_b:
            if entity_id in ctx.trashed:
                ctx.decide(
                    "D6",
                    key,
                    detail={
                        "message": f"“{ctx.name('theirs', entity_id)}” is in your trash; it "
                        "will be restored and updated.",
                        "trashed_type": ctx.trashed[entity_id],
                    },
                )
                return [{**base_item, "state": "take", "in_trash": True, "decision": f"{key}#D6"}]
            return [{**base_item, "state": "take"}]
        if _touches(ctx.theirs_view, entity_id):
            _, choice = ctx.decide("D9", key, detail=_d9_detail(ctx, entity_id, "ours"))
            return [{**base_item, "state": "conflict", "decision": f"{key}#D9"}]
        return [{**base_item, "state": "keep", "deleted_here": True}]

    return []  # in all three, or deleted on both sides


def _ident(ctx: _Context, entity_id: str) -> dict:
    for shapes in (ctx.t[0], ctx.o[0], ctx.b[0]):
        if entity_id in shapes:
            return {"type": shapes[entity_id]["type"], "id": entity_id}
    return {"type": ctx.trashed.get(entity_id, ""), "id": entity_id}


def _equivalent(a: dict, b: dict) -> bool:
    return a["fields"] == b["fields"] and a["sections"] == b["sections"]


def _touches(view: dict, entity_id: str) -> bool:
    """Whether a side changed anything about `entity_id` beyond its own presence."""
    return any(
        item["kind"] in ("field", "section") and item["id"] == entity_id for item in view["items"]
    )


def _d9_detail(ctx: _Context, entity_id: str, deleted_on: str) -> dict:
    other = "theirs" if deleted_on == "ours" else "ours"
    where = "your side" if deleted_on == "ours" else "theirs"
    there = "theirs" if deleted_on == "ours" else "your side"
    return {
        "message": f"“{ctx.name('base', entity_id)}” was deleted on {where} and changed on "
        f"{there}.",
        "deleted_on": deleted_on,
        "changed_on": other,
    }


def _change_item(ctx: _Context, key: str) -> dict | None:
    """A changed field or section, resolved three ways (§7.3)."""
    kind, entity_type, entity_id, name = key.split(":", 3)
    if entity_id not in ctx.o[0]:
        # Ours deleted this entity. Its presence is already a `D9` item, and the
        # cascade rows a delete produces are that item's, not separate edits (T6).
        return None
    mine, theirs = _change(ctx.ours_view, key), _change(ctx.theirs_view, key)
    if mine is None and theirs is None:
        return None
    item = {"key": key, "kind": kind, "type": entity_type, "id": entity_id, "name": name}
    if mine is not None and theirs is not None:
        if _value(theirs) == _value(mine):
            return {**item, "state": "same"}
        ctx.decide(
            "D2",
            key,
            detail={
                "message": f"“{name}” changed on both sides.",
                "theirs": _value(theirs),
                "ours": _value(mine),
            },
        )
        return {
            **item,
            "state": "conflict",
            "decision": f"{key}#D2",
            "theirs": _value(theirs),
            "ours": _value(mine),
        }
    if theirs is not None:
        return {**item, "state": "take", "value": _value(theirs)}
    return {**item, "state": "keep", "value": _value(mine)}


def _change(view: dict, key: str):
    for item in view["items"]:
        if item["key"] == key:
            row = view["entities"].get(item["id"]) or {}
            bucket = row.get("fields" if item["kind"] == "field" else "sections") or {}
            return bucket.get(item["name"])
    return None


def _value(change):
    return change["b"] if isinstance(change, dict) and "b" in change else change


def _order_item(ctx: _Context, key: str) -> dict | None:
    """A parent's child order, compared over the ids all three states share.

    Both sides adding a *different* child to one parent report that parent's order list,
    and the raw lists differ by construction — each holds its own new child. What they
    can disagree about is the order of the children they share, so that is what is
    compared; a child's arrival is D3's business, not D7's. `None` means "no conflict
    here", which is why an unchanged shared order yields no item at all.
    """
    parent_key = key[len("order:") :]
    common = set(ctx.b[0]) & set(ctx.o[0]) & set(ctx.t[0])
    base = [i for i in ctx.b[1].get(parent_key, []) if i in common]
    mine = [i for i in ctx.o[1].get(parent_key, []) if i in common]
    theirs = [i for i in ctx.t[1].get(parent_key, []) if i in common]
    if mine == theirs:
        return None
    entity_type, parent = parent_key.split(":", 1)
    item = {"key": key, "kind": "order", "type": entity_type, "id": parent}
    if theirs == base:
        return {**item, "state": "keep"}
    if mine == base:
        return {**item, "state": "take"}
    ctx.decide(
        "D7",
        key,
        detail={
            "message": f"The {entity_type}s of {parent or 'the story'} were reordered on "
            "both sides.",
            "theirs": theirs,
            "ours": mine,
        },
    )
    return {**item, "state": "conflict", "decision": f"{key}#D7"}


# ─── building the ops ───────────────────────────────────────────────────────


def _build(ctx: _Context) -> None:
    """Turn the selected items into ops, in §7.7.2's order."""
    by_key = {i["key"]: i for i in ctx.items}
    for key in ctx.wanted:
        item = by_key.get(key)
        if item is None or item.get("state") in ("keep", "same"):
            continue
        ctx.source = key
        if item["kind"] == "entity":
            _emit_entity(ctx, item)
        elif item["kind"] in ("field", "section"):
            _emit_change(ctx, item)
        elif item["kind"] == "order":
            _emit_order(ctx, item)
    _settle_orders(ctx)
    for entity_type, entity_id, parent in ctx.placement_checks:
        _check_placement(ctx, entity_type, entity_id, parent)
    ctx.ops = [op for op in ctx.ops if op.get("entity_id") not in ctx.cancelled]
    ctx.ops.sort(key=_order_key)
    for op in ctx.ops:
        op.pop("_phase", None)


def _order_key(op: dict) -> tuple:
    creatable = op["op"] == "create" and op["type"] in CREATE_ORDER
    rank = CREATE_ORDER.index(op["type"]) if creatable else 0
    return (op["_phase"], rank, 0)


def _emit_entity(ctx: _Context, item: dict) -> None:
    entity_id, entity_type = item["id"], item["type"]
    if item.get("deletes"):
        _emit_delete(ctx, entity_id, entity_type)
        return
    if item.get("in_trash"):
        if _choice(ctx, item) == "cancel":
            ctx.cancelled.add(entity_id)
            return
        _emit_restore(ctx, entity_id, entity_type)
        _emit_shape_edit(ctx, entity_id, entity_type)
        return
    if item["state"] == "conflict":
        code = item["decision"].rsplit("#", 1)[-1]
        if code == "D1":
            _emit_d1(ctx, item, _choice(ctx, item))
        elif code == "D9" and _choice(ctx, item) == "take-theirs":
            _emit_restore(ctx, entity_id, entity_type)
            _emit_shape_edit(ctx, entity_id, entity_type)
        return
    if item["state"] == "take":
        _emit_create(ctx, entity_id, entity_type)


def _choice(ctx: _Context, item: dict) -> str:
    for decision in ctx.decisions:
        if decision["key"] == item["decision"]:
            return decision["choice"]
    raise KeyError(item["decision"])


def _emit_d1(ctx: _Context, item: dict, choice: str) -> None:
    """D1: the same id arrived on both sides."""
    entity_id, entity_type = item["id"], item["type"]
    if choice == "keep-mine":
        return
    if choice == "take-theirs":
        _emit_shape_edit(ctx, entity_id, entity_type)
        return
    if choice == "combine":
        # Per field, the Mine/Theirs/Custom rule: a field only theirs changed comes
        # across; a field both changed differently becomes its own D2 with theirs as
        # the pre-filled Custom value; a field only we changed stays.
        mine = ctx.o[0][entity_id]["fields"]
        theirs = ctx.t[0][entity_id]["fields"]
        data = {}
        for name, value in theirs.items():
            if name in ("id", "type") or value == mine.get(name):
                continue
            ours_value = mine.get(name)
            # Unset on one side is not a disagreement: only two different non-empty
            # values make a field a Custom input.
            if not ours_value or not value:
                data[name] = value or ours_value
                continue
            ctx.decide(
                "D2",
                f"field:{entity_type}:{entity_id}:{name}",
                detail={
                    "message": f"“{name}” differs between the two additions.",
                    "theirs": value,
                    "ours": ours_value,
                },
            )
        for name, value in ctx.t[0][entity_id]["sections"].items():
            if value != ctx.o[0][entity_id]["sections"].get(name) and value:
                data[name] = value
        if data:
            ctx.op(
                "edit",
                op="edit",
                entity_type=entity_type,
                entity_id=entity_id,
                data=data,
                summary=f"Combine both {entity_type} {entity_id}",
            )
        return
    typed = ctx.decision(item["decision"])["value"]
    typed = typed if isinstance(typed, dict) else {}
    new_id = _keep_both_id(ctx, item["decision"], entity_id, typed.get("id"))
    _emit_create(
        ctx,
        entity_id,
        entity_type,
        as_id=new_id,
        rewrite_id={entity_id: new_id},
        overrides=(typed.get("fields") or {}, typed.get("sections") or {}),
    )


def _emit_create(
    ctx: _Context,
    entity_id: str,
    entity_type: str,
    *,
    as_id=None,
    rewrite_id=None,
    overrides=({}, {}),
) -> None:
    """Create an entity from `theirs`' shape, pulling in what it names (§7.4).

    Idempotent per id: an entity selected *and* arriving as a dependency is created
    once. The dependency walk hands `rewrite_id` down, so a keep-both rename applies to
    the whole subtree it brings, not just the entity that was renamed.
    """
    target_id = as_id or entity_id
    if target_id in ctx.planned_creates:
        return
    ctx.planned_creates.add(target_id)
    fields, sections = _payload(ctx.t[0][entity_id])
    if rewrite_id:
        fields = refmap.rewrite(
            entity_type, fields, by_id=rewrite_id, by_name=_name_map(ctx, rewrite_id)
        )
    fields, sections = {**fields, **overrides[0]}, {**sections, **overrides[1]}
    fields, sections = _resolve(ctx, entity_type, entity_id, fields, sections, seen={entity_id})
    if entity_id in ctx.cancelled:
        return
    roles = _check_roles(ctx, target_id, entity_type, fields.get("plot_roles"))
    if roles is not None:
        fields["plot_roles"] = roles
    ctx.op(
        "create",
        source=f"entity:{entity_type}:{target_id}",
        op="create",
        type=entity_type,
        id=target_id,
        frontmatter=fields,
        sections=sections,
        summary=f"Bring {entity_type} “{ctx.name('theirs', entity_id)}”",
    )
    parent = _parent_key(entity_type, fields)
    if parent is not None:
        ctx.arriving.setdefault(parent, []).append(target_id)
        ctx.placement_checks.append((entity_type, entity_id, parent))


def _payload(shape: dict) -> tuple[dict, dict]:
    """A create payload: the fields and sections a create can carry."""
    derived = {path for path, _ in refmap.DERIVED.get(shape["type"], ())}
    fields = {
        k: v for k, v in shape["fields"].items() if k not in ("id", "type") and k not in derived
    }
    return fields, dict(shape["sections"])


def _name_map(ctx: _Context, rewrite: dict[str, str]) -> dict[str, str]:
    """`value_turns[].value` is keyed by display name, so a renamed id maps there too."""
    return {ctx.name("theirs", old): new for old, new in rewrite.items() if ctx.name("theirs", old)}


def _resolve(
    ctx: _Context,
    entity_type: str,
    source_id: str,
    fields: dict,
    sections: dict,
    *,
    seen: set[str],
    skip: set[str] = frozenset(),
) -> tuple[dict, dict]:
    """§7.4.2: every reference the incoming content makes must resolve in the target.

    A reference the target already has needs nothing. One it does not becomes D5: bring
    it (recursively, by the same rules), drop it where the site allows, or cancel the
    pick. `refmap`'s `required` decides whether dropping is on the table at all — an
    optional cast link is, a beat's actor is not. A reference whose target is in our bin
    is restored, not created (an id in the trash is refused at create).

    `skip` holds values the target already referenced before this change, so a field
    edit asks only about what it introduces.
    """
    for path, value, site in refmap.iter_references(entity_type, fields):
        if not value or value in seen or value in skip:
            continue
        state, where = _resolves(ctx, site, value)
        if state == "live":
            continue
        if state == "trash":
            _emit_restore(ctx, where, _type_of(ctx, where))
            continue
        options = ["bring", "cancel"] if site.required else ["bring", "drop", "cancel"]
        _, choice = ctx.decide(
            "D5",
            f"{entity_type}:{source_id}:{path}",
            options=options,
            detail={
                "message": f"“{value}” is named by {entity_type} “{source_id}” and the target "
                "does not have it.",
                "path": path,
                "value": value,
                "required": site.required,
                "targets": list(site.targets),
            },
        )
        if choice == "cancel":
            ctx.cancelled.add(source_id)
            return fields, sections
        if choice == "drop":
            fields = _drop(fields, path)
            continue
        brought = _type_of(ctx, value)
        if brought and value in ctx.t[0]:
            _emit_create(ctx, value, brought)
    return fields, sections


def _drop(fields: dict, path: str) -> dict:
    """Remove one concrete reference (`characters[1]`, `plot_roles[0]`, `driver`)."""
    head, _, rest = path.partition(".")
    out = dict(fields)
    if "[" in head:
        name, _, index = head.partition("[")
        index = int(index.rstrip("]"))
        if rest:
            entries = list(out.get(name) or [])
            entries[index] = _drop(entries[index], rest)
            out[name] = entries
        else:
            out[name] = [e for i, e in enumerate(out.get(name) or []) if i != index]
    elif rest:
        out[head] = _drop(out.get(head) or {}, rest)
    else:
        out[head] = ""
    return out


def _resolves(ctx: _Context, site, value: str) -> tuple[str, str]:
    """`live` when the target has it, `trash` when its row is in the bin, else `missing`."""
    live = [eid for eid, shape in ctx.o[0].items() if shape["type"] in site.targets]
    if site.keyed_by == "name":
        if any(ctx.name("ours", eid) == value for eid in live):
            return "live", ""
        return "missing", ""
    if value in live:
        return "live", value
    if value in ctx.trashed and ctx.trashed[value] in site.targets:
        return "trash", value
    return "missing", value


def _type_of(ctx: _Context, entity_id: str) -> str:
    for shapes in (ctx.o[0], ctx.t[0], ctx.b[0]):
        if entity_id in shapes:
            return shapes[entity_id]["type"]
    return ctx.trashed.get(entity_id, "")


def _parent_key(entity_type: str, fields: dict) -> str | None:
    """The `order_of` key an entity's arrival affects, or None when it has no ordering."""
    if entity_type == "scene":
        return f"scene:{fields.get('sequence_id') or ''}"
    if entity_type == "sequence":
        return f"sequence:{fields.get('act_id') or ''}"
    return None


def _check_placement(ctx: _Context, entity_type: str, source_id: str, parent: str) -> None:
    """D3: where an arriving child goes, when the target cannot host it as-is.

    §7.5's default — after the child that preceded it in the source, else before the one
    that followed, else the end — needs no decision: `_place` applies it and the plan
    reports the position. A decision is required only when the container itself is not
    in the target and this plan is not bringing it, because then there is no list to
    insert into and the user must choose a home.
    """
    if entity_type not in ("scene", "sequence"):
        return
    if _parent_present(ctx, parent) or parent in ctx.arriving:
        return
    ctx.decide(
        "D3",
        f"entity:{entity_type}:{source_id}",
        detail={
            "message": f"“{ctx.name('theirs', source_id)}” arrives in "
            f"{_container_name(ctx, parent)}, which the target does not have. "
            "Bring it along, or place it in a sequence you already have.",
            "parent": parent,
            "proposal": _proposal(ctx, source_id, parent),
        },
    )


def _parent_present(ctx: _Context, parent: str) -> bool:
    """Whether the target has the container an order key names.

    A key's prefix is the CHILD type (`scene:<sequence_id>`), so the parent's own type
    is `PARENT_TYPE`, not the prefix.
    """
    child_type, parent_id = parent.split(":", 1)
    parent_type = PARENT_TYPE[child_type]
    return parent_id in ctx.o[0] and ctx.o[0][parent_id]["type"] == parent_type


def _container_name(ctx: _Context, parent: str) -> str:
    _child_type, parent_id = parent.split(":", 1)
    return ctx.name("theirs", parent_id) if parent_id else "the story"


def _proposal(ctx: _Context, source_id: str, parent: str) -> dict:
    """Which neighbour the default placement puts the arriving child next to."""
    source = ctx.t[1].get(parent, [])
    if source_id not in source:
        return {"after": None, "before": None}
    at = source.index(source_id)
    live = set(ctx.o[1].get(parent, []))
    after = next((s for s in reversed(source[:at]) if s in live), None)
    before = next((s for s in source[at + 1 :] if s in live), None)
    return {"after": after, "before": before}


def _emit_change(ctx: _Context, item: dict) -> None:
    """A field or section arriving from theirs — or the one side a conflict chose."""
    if item["state"] == "conflict":
        found, value = _conflict_value(ctx, item)
        if not found:
            return
    else:
        value = item.get("value")
    name = item["name"]
    if item["kind"] == "field":
        value = _resolve_change(ctx, item, value)
    if item["kind"] == "field" and name == "plot_roles":
        roles = _check_roles(ctx, item["id"], item["type"], value)
        if roles is not None:
            value = roles
    ctx.op(
        "edit",
        op="edit",
        entity_type=item["type"],
        entity_id=item["id"],
        data={name: value},
        summary=f"Bring theirs' {item['type']} {name}",
    )
    if item["kind"] == "field" and name == "sequence_id":
        old = ctx.o[0].get(item["id"], {}).get("fields", {}).get("sequence_id")
        if old:
            ctx.leaving.setdefault(f"scene:{old}", set()).add(item["id"])
        ctx.arriving.setdefault(f"scene:{value}", []).append(item["id"])


def _conflict_value(ctx: _Context, item: dict) -> tuple[bool, object]:
    """What a conflict writes: theirs' value, or the one typed for `custom`.

    `(False, None)` when `mine` stays, or when a custom answer has no usable value, in
    which case the decision is told why and stays open.
    """
    choice = _choice(ctx, item)
    if choice == "theirs":
        return True, item["theirs"]
    if choice != "custom":
        return False, None
    typed = ctx.decision(item["decision"])["value"]
    if typed is None or (item["kind"] == "section" and not isinstance(typed, str)):
        ctx.reject(item["decision"], "Write the value you want to keep.")
        return False, None
    return True, typed


def _resolve_change(ctx: _Context, item: dict, value):
    """Resolve references THIS change introduces, not every reference already in the row.

    A field edit carries one field, so the references to resolve are the ones in the
    new value that the current one did not already make. A plot's cast list arriving
    whole therefore asks about the added characters only. Any create it plans is
    already in `ctx.ops`.
    """
    entity_id, entity_type = item["id"], item["type"]
    before = ctx.o[0][entity_id]["fields"]
    candidate = {**before, item["name"]: value}
    already = {ref[1] for ref in refmap.iter_references(entity_type, before)}
    resolved, _sections = _resolve(
        ctx, entity_type, entity_id, candidate, {}, seen={entity_id}, skip=already
    )
    return resolved.get(item["name"], value)


def _emit_shape_edit(ctx: _Context, entity_id: str, entity_type: str) -> None:
    """Write theirs' whole shape over the target's row."""
    fields, sections = _payload(ctx.t[0][entity_id])
    roles = _check_roles(ctx, entity_id, entity_type, fields.get("plot_roles"))
    if roles is not None:
        fields["plot_roles"] = roles
    ctx.op(
        "edit",
        op="edit",
        entity_type=entity_type,
        entity_id=entity_id,
        data=fields | sections,
        summary=f"Bring theirs' {entity_type} {entity_id}",
    )


def _check_roles(ctx: _Context, scene_id: str, entity_type: str, entries) -> list | None:
    """D4: a singular role the incoming content would put on a second live scene.

    Runs on the list the edit would actually write, so a whole-value role list cannot
    slip a second climax past the planner (D-T7-C). Returns the list to write instead:
    `mine` drops the colliding entry from the incoming scene, `theirs`/`replace` take it
    off the holder first (§7.7.2's "edits that release roles"), `custom` gives the
    incoming scene the role that was typed instead, and leaves the holder alone.
    """
    if entity_type != "scene" or not isinstance(entries, list):
        return None
    out = list(entries)
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        role, plot = entry.get("role"), entry.get("plot")
        if role not in UNIQUE_PLOT_ROLES or not plot:
            continue
        holder = _role_holder(ctx, plot, role, exclude=scene_id)
        if not holder or holder in {s for s, _, _ in ctx.released}:
            continue
        if _released_by_selection(ctx, holder, plot, role):
            ctx.released.add((holder, plot, role))
            _emit_release(ctx, holder, plot, role)
            continue
        decision_key, choice = ctx.decide(
            "D4",
            f"entity:scene:{scene_id}",
            detail={
                "roles": list(PLOT_ROLES),
                "message": f"Plot “{ctx.name('ours', plot)}” already has its "
                f"{role.replace('_', ' ')} on “{ctx.name('ours', holder)}”.",
                "plot": plot,
                "role": role,
                "holder": {"id": holder, "name": ctx.name("ours", holder)},
            },
        )
        if choice in ("theirs", "replace"):
            ctx.released.add((holder, plot, role))
            _emit_release(ctx, holder, plot, role)
        elif choice == "mine":
            out = [e for e in out if not (e.get("plot") == plot and e.get("role") == role)]
        elif choice == "custom":
            typed = ctx.decision(decision_key)["value"]
            if typed not in PLOT_ROLES:
                ctx.reject(decision_key, "Pick the role this scene plays in that plot instead.")
                out = [e for e in out if not (e.get("plot") == plot and e.get("role") == role)]
            else:
                out = [
                    {**e, "role": typed} if e.get("plot") == plot and e.get("role") == role else e
                    for e in out
                ]
    return out if out != list(entries) else None


def _released_by_selection(ctx: _Context, holder: str, plot: str, role: str) -> bool:
    """True when a selected item already takes `role` off `holder`.

    A writer who moves a singular role from one scene to another has made two edits, and
    selecting both is the move. Judged against the target as it stands, the arriving
    scene collides with a holder the same selection is about to release, and the default
    answer to that false collision (`mine`) would strip the arriving scene's role as well,
    leaving the plot with no holder at all.
    """
    key = f"field:scene:{holder}:plot_roles"
    if key not in ctx.wanted:
        return False
    item = next((i for i in ctx.items if i["key"] == key), None)
    if item is None:
        return False
    if item["state"] == "take":
        value = item.get("value")
    elif item["state"] == "conflict" and _choice(ctx, item) in ("theirs", "custom"):
        value = (
            item["theirs"]
            if _choice(ctx, item) == "theirs"
            else ctx.decision(item["decision"])["value"]
        )
    else:
        return False
    return not any(
        isinstance(entry, dict) and entry.get("plot") == plot and entry.get("role") == role
        for entry in value or []
    )


def _emit_release(ctx: _Context, holder: str, plot: str, role: str) -> None:
    """Take one role off the scene that holds it, as its own edit."""
    remaining = [
        entry
        for entry in ctx.o[0][holder]["fields"].get("plot_roles") or []
        if not (entry.get("plot") == plot and entry.get("role") == role)
    ]
    ctx.op(
        "release",
        op="edit",
        entity_type="scene",
        entity_id=holder,
        data={"plot_roles": remaining},
        summary=f"Release {role} in {plot} from {holder}",
    )


def _role_holder(ctx: _Context, plot: str, role: str, *, exclude: str) -> str | None:
    for entity_id, shape in ctx.o[0].items():
        if shape["type"] != "scene" or entity_id == exclude:
            continue
        for entry in shape["fields"].get("plot_roles") or []:
            if entry.get("plot") == plot and entry.get("role") == role:
                return entity_id
    return None


def _emit_delete(ctx: _Context, entity_id: str, entity_type: str) -> None:
    """A removal. `delete_entity` cascades the beats and hides referring links itself.

    §7.4's optional cleanup is D8: an entity only this one referenced is offered,
    unticked, and only its own explicit choice deletes it.
    """
    ctx.op(
        "delete",
        op="delete",
        entity_type=entity_type,
        entity_id=entity_id,
        summary=f"Remove {entity_type} {entity_id}",
    )
    for candidate in _orphans(ctx, entity_id):
        _, choice = ctx.decide(
            "D8",
            f"entity:{candidate}:{entity_id}",
            detail={
                "message": f"“{ctx.name('ours', candidate)}” is only used by "
                f"“{ctx.name('ours', entity_id)}”. Remove it too?",
                "cleanup": candidate,
            },
        )
        if choice == "delete":
            ctx.op(
                "delete",
                op="delete",
                entity_type=_type_of(ctx, candidate),
                entity_id=candidate,
                summary=f"Clean up {candidate}",
            )


def _orphans(ctx: _Context, removed: str) -> list[str]:
    """Entities nothing but `removed` uses any more: §7.4's optional cleanup.

    The candidates are what the removed entity NAMED — a character cast in that scene
    and nowhere else, say — kept only while no other live entity still names them.
    Anything with another referrer is never offered, and neither is a row `delete_entity`
    cascades (its beats). Unticked by default: the delete is the decision, this is spare
    parts.
    """
    shape = ctx.o[0].get(removed)
    if not shape or shape["type"] != "scene":
        return []  # §7.4's cleanup is about what a removed scene leaves behind
    referrers = _referrers(ctx)
    cascaded = _already_cascaded(ctx, removed)
    candidates = {
        value for _path, value, _site in refmap.iter_references(shape["type"], shape["fields"])
    }
    return sorted(
        candidate
        for candidate in candidates
        if candidate in ctx.o[0]
        and candidate != removed
        and candidate not in cascaded
        and referrers.get(candidate, set()) == {removed}
    )


def _referrers(ctx: _Context) -> dict[str, set[str]]:
    """`{referenced id: {ids that name it}}` over the target's live entities."""
    out: dict[str, set[str]] = {}
    for entity_id, shape in ctx.o[0].items():
        for _path, value, _site in refmap.iter_references(shape["type"], shape["fields"]):
            out.setdefault(value, set()).add(entity_id)
    return out


def _already_cascaded(ctx: _Context, removed: str) -> set[str]:
    """The children `delete_entity` removes with this row, so no op repeats them."""
    return {
        entity_id
        for entity_id, shape in ctx.o[0].items()
        if shape["type"] == "scene_beats" and shape["fields"].get("scene") == removed
    }


def _emit_restore(ctx: _Context, entity_id: str, entity_type: str) -> None:
    """Restore a row from the target's bin, resolving what the bin left behind.

    Role and position collisions are `restore_check`'s (§8) — one scan, the same one the
    Trash tab and the merge share. `restore` settles the position itself and reports
    `placed`, so no reorder is emitted for that parent (T7 Notes).
    """
    conn = get_db(ctx.target)
    try:
        check = restore_check(conn, entity_id)
    finally:
        conn.close()
    resolutions = []
    for collision in check["collisions"]:
        _, choice = ctx.decide(
            "D4",
            f"entity:{entity_type}:{entity_id}",
            detail={
                "message": collision["message"],
                "plot": collision["plot"],
                "role": collision["role"],
                "holder": collision["holder"],
                "choices": collision["choices"],
            },
        )
        resolutions.append(
            {
                "plot": collision["plot"],
                "role": collision["role"],
                "choice": "take" if choice in ("theirs", "replace") else "drop",
            }
        )
        if choice in ("theirs", "replace"):
            ctx.released.add((collision["holder"]["id"], collision["plot"], collision["role"]))
    ctx.op(
        "restore",
        op="restore",
        entity_type=entity_type,
        entity_id=entity_id,
        resolutions=resolutions,
        summary=f"Restore {entity_id} from the trash",
    )


def _emit_order(ctx: _Context, item: dict) -> None:
    """Order is one item per parent; selecting it takes that side's list (D7 if both)."""
    key = item["key"][len("order:") :]
    if item["state"] == "take":
        ctx.take_order[key] = ctx.t[1].get(key, [])
    elif item["state"] == "conflict":
        choice = _choice(ctx, item)
        if choice == "theirs":
            ctx.take_order[key] = ctx.t[1].get(key, [])
        elif choice == "custom":
            typed = ctx.decision(item["decision"])["value"]
            if isinstance(typed, list) and all(isinstance(i, str) for i in typed):
                ctx.take_order[key] = typed
            else:
                ctx.reject(item["decision"], "Arrange the order you want.")


def _settle_orders(ctx: _Context) -> None:
    """One `reorder` per affected parent, over the COMPLETE live sibling list.

    `reorder` renumbers `1..n` and does not verify completeness (F13), so the full list
    is built here and asserted before the op is emitted (§7.6).
    """
    for key in sorted(set(ctx.arriving) | set(ctx.leaving) | set(ctx.take_order)):
        entity_type, parent = key.split(":", 1)
        if not parent or entity_type not in ("scene", "sequence"):
            continue
        current = list(ctx.o[1].get(key, []))
        leaving = ctx.leaving.get(key, set())
        entering = list(dict.fromkeys(i for i in ctx.arriving.get(key, []) if i not in current))
        result = [i for i in current if i not in leaving]
        if key in ctx.take_order:
            wanted = [i for i in ctx.take_order[key] if i in result or i in entering]
            result = wanted + [i for i in result if i not in wanted]
        for entity_id in entering:
            result = _place(ctx, key, entity_id, result)
        expected = (set(current) - leaving) | set(entering)
        assert set(result) == expected and len(result) == len(expected), (
            f"incomplete sibling list for {key}: reorder would renumber a partial set"
        )
        if result != current:
            ctx.op(
                "reorder",
                source=f"order:{key}",
                op="reorder",
                entity_type=entity_type,
                ordered_ids=result,
                summary=f"Place the arriving {entity_type}(s) in {parent}",
            )


def _place(ctx: _Context, parent_key: str, entity_id: str, result: list[str]) -> list[str]:
    """D3's default position: after the one that preceded it in the source, else before
    the one that followed, else at the end."""
    source = ctx.t[1].get(parent_key, [])
    if entity_id in source:
        at = source.index(entity_id)
        for neighbour in reversed(source[:at]):
            if neighbour in result:
                cut = result.index(neighbour) + 1
                return result[:cut] + [entity_id] + result[cut:]
        for neighbour in source[at + 1 :]:
            if neighbour in result:
                cut = result.index(neighbour)
                return result[:cut] + [entity_id] + result[cut:]
    return result + [entity_id]


_ID = re.compile(r"^[A-Za-z0-9_-]+$")


def _keep_both_id(ctx: _Context, decision_key: str, entity_id: str, typed) -> str:
    """The id a keep-both gives theirs: the one typed if it is usable, else the suggestion."""
    suggestion = _new_id(ctx, entity_id)
    if typed is None or typed == "":
        return suggestion
    taken = set(ctx.o[0]) | set(ctx.t[0]) | set(ctx.trashed) | ctx.planned_creates
    if not isinstance(typed, str) or not _ID.match(typed) or typed in taken:
        ctx.reject(
            decision_key,
            f"“{typed}” cannot be the new id: use letters, digits, hyphens or "
            "underscores, and not an id the story already has.",
        )
        return suggestion
    return typed


def _new_id(ctx: _Context, entity_id: str) -> str:
    """§7.5 D1's suggestion for keep-both: `<id>-2`, onwards while taken."""
    taken = set(ctx.o[0]) | set(ctx.t[0]) | set(ctx.trashed)
    n = 2
    while f"{entity_id}-{n}" in taken:
        n += 1
    return f"{entity_id}-{n}"
