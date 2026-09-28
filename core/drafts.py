"""Draft staging — propose a set of entity changes, write them on commit.

A draft is a row in the project's own `drafts` table holding a list of ops.
Nothing here touches `entities`, `sections` or `relations` until `commit_draft`
dispatches the ops into `core.writes`, so a staged batch is inert: staging a
change and never committing it leaves no trace in the story.

Ops mirror what the write functions already take, so staging is the same
computation as a dry run with a different sink. Design of record:
tasks/task_28/draft-staging-design.md.
"""
import json
import sqlite3
from datetime import datetime
from pathlib import Path

from .constants import ENTITY_SCHEMAS

# Dispatch order. Creates must land before edits (an edit referencing a staged
# create), edits before deletes, deletes before reorders. Stable within a kind:
# Python's sort is stable, so ops the agent wrote in one kind keep their order.
OP_ORDER = {"create": 0, "edit": 1, "delete": 2, "reorder": 3}

# Per-kind required keys. Mirrors what the replayed handler needs, so a missing
# key is reported at stage time rather than escaping the commit loop.
_REQUIRED = {
    "create": ("type", "id", "frontmatter", "summary"),
    "edit": ("entity_type", "entity_id", "data", "summary"),
    "delete": ("entity_type", "entity_id", "summary"),
    "reorder": ("entity_type", "ordered_ids", "summary"),
}


class DraftError(ValueError):
    """A draft op is not dispatchable. The message is agent-facing."""


def new_draft_id(conn: sqlite3.Connection) -> str:
    """Return an unused draft id.

    Timestamp with a one-second granularity plus a counter suffix, the same
    collision defence `backup_database` uses: two drafts staged in the same
    second would otherwise overwrite each other, the second destroying the
    first while both reported success.
    """
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    candidate = f"d-{stamp}"
    n = 1
    while conn.execute(
        "SELECT 1 FROM drafts WHERE id=?", (candidate,)
    ).fetchone():
        candidate = f"d-{stamp}-{n}"
        n += 1
    return candidate


def validate_ops(ops) -> list[dict]:
    """Shape-check an op list. Returns the ops unchanged, or raises.

    Structural only — is each op dispatchable, with the keys its handler
    reads. Field-level checks (required fields, enums) are Phase 6's
    `validate_entity` pass, and cross-entity references stay at commit: they
    read committed state, and a staged create is not there yet.
    """
    if not isinstance(ops, list) or not ops:
        raise DraftError("`ops` must be a non-empty list of op objects.")

    for i, op in enumerate(ops):
        where = f"ops[{i}]"
        if not isinstance(op, dict):
            raise DraftError(f"{where} must be an object.")
        kind = op.get("op")
        if kind not in OP_ORDER:
            raise DraftError(
                f"{where}.op must be one of {sorted(OP_ORDER)}; got {kind!r}."
            )
        missing = [k for k in _REQUIRED[kind] if k not in op]
        if missing:
            raise DraftError(
                f"{where} ({kind}) is missing: {', '.join(missing)}."
            )
        if kind == "create":
            if op["type"] not in ENTITY_SCHEMAS:
                raise DraftError(
                    f"{where}.type: unknown entity_type {op['type']!r}."
                )
            if op["type"] == "project":
                # A project that does not exist has no DB to hold the draft,
                # and _create_project is a separate arg shape entirely.
                raise DraftError(
                    f"{where}: projects cannot be drafted. "
                    "Call story_admin(action=\"create_project\") directly."
                )
            if not op["id"].replace("-", "").replace("_", "").isalnum():
                raise DraftError(
                    f"{where}.id must be alphanumeric with hyphens/underscores only."
                )
            if not isinstance(op["frontmatter"], dict):
                raise DraftError(f"{where}.frontmatter must be an object.")
        if kind in ("edit", "delete", "reorder"):
            if op["entity_type"] not in ENTITY_SCHEMAS:
                raise DraftError(
                    f"{where}.entity_type: unknown entity_type {op['entity_type']!r}."
                )
        if kind == "edit" and not isinstance(op["data"], dict):
            raise DraftError(f"{where}.data must be an object of field → value.")
        if kind == "reorder" and (
            not isinstance(op["ordered_ids"], list) or not op["ordered_ids"]
        ):
            raise DraftError(f"{where}.ordered_ids must be a non-empty list of ids.")
    return ops


def validate_shape(ops: list) -> list[str]:
    """Field-level findings for an op list. Shape only, no DB.

    `validate_entity` is a pure function of (entity_type, frontmatter), so a
    create can be checked before the row exists. Cross-entity references are
    deliberately NOT checked here: validate_plot_characters, validate_scene_act_id
    and validate_arc_parents each open their own connection and read committed
    state, so a staged create's id is not there yet and every cross-op
    reference in a batch would report a false error. Those surface at commit,
    where the earlier op has already landed.

    A `create` is checked on the frontmatter merged over its schema defaults —
    the same merge the write path does, so the check sees what will actually be
    written rather than what was explicitly passed.

    That merge makes `validate_entity`'s own required-field check inert: it
    tests `field not in frontmatter`, and after a merge every schema field IS
    in there. A required field is therefore checked on its merged *value*
    instead — present-but-empty is the real failure, and it is the one the
    merge would otherwise hide.
    """
    from .entity import REQUIRED_FIELDS, validate_entity
    from .scene_content_lint import check_scene_content

    findings = []
    for i, op in enumerate(ops):
        where = f"ops[{i}] ({_describe(op)})"
        entity_type = op.get("type") or op.get("entity_type")
        schema = ENTITY_SCHEMAS.get(entity_type, {})

        # A computed field is derived at read time. The write path drops it and
        # says so, but only AFTER the agent has committed a draft and read a
        # preview promising the change — so the preview is the only place the
        # agent can still be told. Checked for every op kind, not just create:
        # a create cannot carry one (the merge drops it), an edit can.
        payload = op.get("frontmatter") if op["op"] == "create" else op.get("data")
        for key in (payload or {}):
            if schema.get(key, {}).get("computed"):
                findings.append(
                    f"{where}: '{key}' is read-only (computed from "
                    f"{entity_type} entities) — it cannot be set")

        # A scene whose Content has no opening scene heading renders as nothing,
        # or silently drops the lines before its heading. Nothing downstream
        # reports it, so the preview is the last place the agent can hear.
        # Sections arrive under `sections` on a create and inside `data` on an
        # edit, so both have to be read or the edit path is unchecked — which is
        # where a reformat usually happens.
        if entity_type == "scene" and op["op"] != "delete":
            content = (op.get("sections") or {}).get("Content")
            if not content and op["op"] == "edit":
                content = (payload or {}).get("Content")
            if content:
                for f in check_scene_content(content, (payload or {}).get("heading", "")):
                    findings.append(f"{where}: {f}")

        if op["op"] != "create":
            continue
        merged = {f: op["frontmatter"].get(f, m["default"])
                  for f, m in schema.items() if not m.get("computed")}
        # Unrecognised keys would land in `extra` verbatim, exactly as an
        # unrecognised edit key used to — reported rather than written.
        for key in [k for k in op["frontmatter"] if k not in schema]:
            findings.append(f"{where}: unknown {entity_type} field '{key}'")
        for field in REQUIRED_FIELDS.get(entity_type, []):
            if not merged.get(field):
                findings.append(f"{where}: Missing required field: {field}")
        findings += [f"{where}: {w}" for w in validate_entity(entity_type, merged)]
    return findings


def stage(project_path: Path, ops, summary: str = "",
         draft_id: str | None = None) -> dict:
    """Store an op list as a draft. Writes one row and nothing else.

    Staging twice on the same `draft_id` REPLACES the op list — staging is a
    proposal, not a queue — and the replaced list goes to `prev_ops` so the
    response can say what changed since the last stage. Without that, "don't
    resequence" silently drops a queued op and the user cannot tell it was
    dropped rather than never proposed.
    """
    validate_ops(ops)

    from .db import get_db

    conn = get_db(project_path)
    try:
        row = None
        if draft_id:
            row = conn.execute(
                "SELECT ops, summary, created_at FROM drafts WHERE id=?", (draft_id,)
            ).fetchone()
            if not row:
                raise DraftError(f"No open draft: {draft_id}")

        prev_ops = json.loads(row[0]) if row else None
        new_id = draft_id or new_draft_id(conn)
        # Straight copy — the same agent writes the op list each time, and the
        # diff compares it structurally, so there is nothing to normalise.
        conn.execute(
            "INSERT INTO drafts (id, ops, prev_ops, summary, created_at, status) "
            "VALUES (?, ?, ?, ?, ?, 'open') ON CONFLICT(id) DO UPDATE SET "
            "ops=excluded.ops, prev_ops=excluded.prev_ops, "
            "summary=excluded.summary, status='open'",
            (
                new_id,
                json.dumps(ops, ensure_ascii=False),
                json.dumps(prev_ops, ensure_ascii=False) if prev_ops is not None else None,
                summary or (row[1] if row else ""),
                row[2] if row else datetime.now().isoformat(timespec="seconds"),
            ),
        )
    finally:
        conn.close()

    restaged_changes = diff_ops(prev_ops, ops) if prev_ops is not None else None
    result = {
        "success": True,
        "draft_id": new_id,
        "op_count": len(ops),
        "preview_md": render_preview_md(
            project_path, ops, new_id, _project_name(project_path),
            summary=summary or (row[1] if row else ""), changes=restaged_changes,
        ),
        "validation": validate_shape(ops),
    }
    if prev_ops is not None:
        result["restaged"] = True
        result["changes"] = restaged_changes
    return result


def _project_name(project_path: Path) -> str:
    """The project's display name, falling back to the folder name.

    One read, best effort: the preview is presentation, so a project with no
    name row still renders under its slug.
    """
    from .db import get_db

    conn = get_db(project_path)
    try:
        row = conn.execute(
            "SELECT name FROM entities WHERE type='project' LIMIT 1"
        ).fetchone()
    except Exception:
        row = None
    finally:
        conn.close()
    return (row[0] if row and row[0] else "") or project_path.name


def list_drafts(project_path: Path) -> dict:
    """Every open draft: id, summary, age, op count. No staleness verdict.

    A computed "probably stale" would be a guess dressed as a signal — whether
    a two-day-old draft still matters depends on what happened in the project
    since, which this does not model. Age plus op count is enough for the
    agent to ask a sensible question.
    """
    from .db import get_db

    conn = get_db(project_path)
    try:
        rows = conn.execute(
            "SELECT id, ops, summary, created_at FROM drafts "
            "WHERE status='open' ORDER BY created_at, id"
        ).fetchall()
        drafts = [
            {
                "id": r[0],
                "summary": r[2],
                "created_at": r[3],
                "op_count": len(json.loads(r[1])),
            }
            for r in rows
        ]
    finally:
        conn.close()
    return {"success": True, "drafts": drafts, "count": len(drafts)}


def discard(project_path: Path, draft_id: str) -> dict:
    """Drop a draft. Touches no story data — a discarded proposal never landed."""
    from .db import get_db

    conn = get_db(project_path)
    try:
        cur = conn.execute("DELETE FROM drafts WHERE id=?", (draft_id,))
        if not cur.rowcount:
            raise DraftError(f"No open draft: {draft_id}")
    finally:
        conn.close()
    return {"success": True, "discarded": draft_id}


def sorted_ops(ops: list) -> list:
    """Dispatch order: create → edit → delete → reorder, stable within a kind.

    A draft that creates a scene and then sets its `order_key` fails on an
    unknown id in the other order, so this is the caller's problem solved once
    rather than something every staged batch has to get right. Python's sort is
    stable, so ops the agent wrote in one kind keep their order — a batch that
    creates two scenes and references the first from the second depends on it.
    """
    return sorted(ops, key=lambda op: OP_ORDER[op["op"]])


def commit(project_path: Path, draft_id: str) -> dict:
    """Write a staged draft by replaying its ops into `core.writes`.

    No re-implementation of the writes: each op dispatches in-process to the
    function that means what a create means, so there is one place where that
    meaning lives.

    The guarantee is **atomic per op, resumable per batch**. `create_entity`
    runs in autocommit and the rest wrap each call in their own
    BEGIN/COMMIT, so a multi-op draft cannot be one transaction without
    threading a shared connection through every write path in the plugin. On
    failure the draft row is KEPT and the response names exactly what landed:
    the agent re-stages the remainder and commits again, and an op that
    already landed refuses correctly (a create whose id now exists fails on
    uniqueness). A temporarily inconsistent project, never lost work.
    """
    from .db import get_db

    conn = get_db(project_path)
    try:
        row = conn.execute(
            "SELECT ops, status FROM drafts WHERE id=?", (draft_id,)
        ).fetchone()
    finally:
        conn.close()
    if not row:
        raise DraftError(f"No open draft: {draft_id}")

    ops = sorted_ops(json.loads(row[0]))

    if row[1] == "committed":
        # This draft already landed. Reporting "No open draft" here would tell
        # the caller its changes were lost when they are in the database, and
        # the obvious response to that is to write them again on top. Replay
        # the same answer instead — the ops are still on the row, so the landed
        # list is the same list, not a reconstruction.
        landed = [_describe(op) for op in ops]
        return {
            "success": True,
            "committed": True,
            "already_committed": True,
            "draft_id": draft_id,
            "applied": landed,
            "preview_md": _commit_report(landed, None, draft_id),
            "message": (f"Draft {draft_id} was already committed — "
                        f"{len(landed)} change(s) are in the project. "
                        f"Nothing was written twice."),
        }

    landed, failed = [], None
    for op in ops:
        result = _dispatch(project_path, op)
        if result.get("error"):
            failed = {"op": _describe(op), "error": result["error"]}
            break
        landed.append(_describe(op))

    if failed:
        # The draft row is the resume token — kept, not deleted, so nothing in
        # the batch is lost and the remainder can be re-staged against it.
        return {
            "success": False,
            "committed": landed,
            "failed": failed,
            "draft_id": draft_id,
            "draft_kept": True,
            "preview_md": _commit_report(landed, failed, draft_id),
            "message": (
                f"{len(landed)} of {len(ops)} change(s) written, then it stopped. "
                f"Draft {draft_id} kept so you can retry — re-stage the "
                f"remainder and commit again."
            ),
        }

    # Marked, not deleted: the row is the receipt that makes a repeated commit
    # replay instead of claiming the work was lost. `discard` removes it.
    conn = get_db(project_path)
    try:
        conn.execute("UPDATE drafts SET status='committed' WHERE id=?", (draft_id,))
    finally:
        conn.close()
    return {
        "success": True,
        "committed": True,
        "draft_id": draft_id,
        "applied": landed,
        "preview_md": _commit_report(landed, None, draft_id),
        "message": f"Committed {len(landed)} change(s) from draft {draft_id}.",
    }


def _commit_report(landed: list, failed: dict | None, draft_id: str) -> str:
    """What landed, and what did not. Terse by default (decision 4).

    The user read the full detail moments earlier in the same conversation;
    repeating it is noise. The exception is partial failure, which gets a
    warning line and the resume instruction, because the project is now in a
    mixed state and only this message says so.
    """
    lines = [f"### {'⚠️ Partly saved' if failed else '✅ Committed'} · draft `{draft_id}`", ""]
    for op in landed:
        lines.append(f"· ✅ `{op}`")
    if failed:
        lines.append(f"· ❌ `{failed['op']}` — {failed['error']}")
    if failed:
        lines += ["", f"Draft `{draft_id}` is still open, so nothing is lost. "
                      f"Re-stage the remainder and commit again."]
    return "\n".join(lines) + "\n"


def _dispatch(project_path: Path, op: dict) -> dict:
    """Apply one op by calling the core write function for its kind.

    The op fields are already what the write functions take, so there is
    nothing to translate: `project_path` is resolved, and each op names its
    entity directly. The tool-boundary shapes this used to build — a top-level
    `project` for one handler and a nested `target.project` for the other,
    relations folded into `frontmatter`, the reorder list as
    `order_context.ordered_ids` — were artifacts of the JSON handlers and do
    not exist here.
    """
    from . import writes

    kind = op["op"]
    if kind == "create":
        return _call(
            writes.create_entity, project_path,
            op["type"], op["id"], op["frontmatter"], op.get("sections") or {},
        )
    if kind == "edit":
        return _call(
            writes.edit_entity, project_path,
            op["entity_type"], op["entity_id"], op["data"], op["summary"],
        )
    if kind == "delete":
        # NOT a safety bypass: delete_entity's `confirm` gate exists so the
        # user sees what is about to go before it goes. Committing a draft
        # IS that confirmation — the user read the preview and said save.
        # The delete is still reversible, and the preview still listed the
        # cascade, so nothing is hidden from the person deciding.
        return _call(
            writes.delete_entity, project_path,
            op["entity_type"], op["entity_id"], op["summary"], True,
        )
    return _call(
        writes.reorder, project_path,
        op["entity_type"], op["ordered_ids"], op["summary"],
    )


def _call(fn, *args) -> dict:
    """Run a write function and get its result or its error as a dict.

    The write functions raise on failure; the commit loop keys off a returned
    `error` key so it can name the op that failed and keep the draft. Funnel
    the raise into that shape here — and keep a surprise from aborting a
    half-applied batch, which validate_ops should already have prevented.
    """
    try:
        return fn(*args)
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}


# ─── op identity and the restage diff ───

def op_key(op: dict) -> tuple:
    """What makes two ops "the same change" across restages.

    The target, not the payload: re-staging with a rewritten `shift` is one
    op changed, not one op dropped and one added.
    """
    kind = op.get("op")
    if kind == "create":
        return (kind, "create", op.get("type"), op.get("id"))
    if kind in ("edit", "delete"):
        return (kind, op.get("entity_type"), op.get("entity_id"))
    if kind == "reorder":
        return (kind, op.get("entity_type"), tuple(op.get("ordered_ids") or ()))
    return (kind, json.dumps(op, sort_keys=True, ensure_ascii=False))


def diff_ops(prev: list, current: list) -> dict:
    """What changed between two op lists, keyed on op identity.

    Three buckets because "don't resequence" must not be indistinguishable
    from "the reorder was never proposed": an op quietly missing from the new
    list is the one case where the user could otherwise hold a wrong belief
    about the state of their work.

    Walks the lists rather than indexing them by key: a batch may hold two ops
    on the same entity, and a dict would collapse them into one.
    """
    added, changed = [], []
    remaining = list(prev)
    for op in current:
        key = op_key(op)
        match = next((p for p in remaining if op_key(p) == key), None)
        if match is None:
            added.append(_describe(op))
        else:
            remaining.remove(match)
            if match != op:
                changed.append({
                    "op": _describe(op),
                    "fields": _changed_keys(match, op),
                })
    return {
        "added": added,
        "dropped": [_describe(op) for op in remaining],
        "changed": changed,
    }


def _changed_keys(before: dict, after: dict) -> list[str]:
    keys = set(before) | set(after)
    return sorted(k for k in keys if before.get(k) != after.get(k))


def _describe(op: dict) -> str:
    """One line naming an op, for the diff.

    A reorder has no single target — it renumbers a whole list — so it is
    named by the list, not by an entity id that does not exist.
    """
    kind = op["op"]
    entity_type = op.get("entity_type") or op.get("type", "")
    if kind == "reorder":
        return f"reorder {entity_type} ({len(op.get('ordered_ids') or [])} items)"
    return f"{kind} {entity_type}/{op.get('entity_id') or op.get('id', '')}"


# ─── preview renderer ───

def render_preview_md(project_path: Path, ops: list, draft_id: str, project_name: str,
                      summary: str = "", changes: dict | None = None,
                      committed: bool = False) -> str:
    """Render an op list as the block the user reads.

    One renderer, two callers — the stage and commit responses share it, so
    what the user approves and what they are told landed are the same
    rendering. Pure presentation: it reads, it never writes.
    """
    lines = [f"### {'✅' if committed else '📝'} Draft `{draft_id}`"
             + (f" — *{summary}*" if summary else "")
             + (" committed" if committed else ""),
             "",
             f"**{project_name}** · {len(ops)} change" + ("s" if len(ops) != 1 else ""),
             ""]

    for op in ops:
        lines += ["---", ""] + _render_op(project_path, op) + [""]

    if changes:
        lines += ["---", ""] + _render_diff(changes)

    return "\n".join(lines).rstrip() + "\n"


def _render_op(project_path: Path, op: dict) -> list[str]:
    kind = op["op"]
    if kind == "create":
        return _render_create(op)
    if kind == "edit":
        return _render_edit(project_path, op)
    if kind == "delete":
        return [f"**🗑 DELETE** · `{op['entity_type']}/{op['entity_id']}`",
                f"_{op['summary']}_ — reversible; "
                f"`story_admin(action=\"restore\")` undoes it."]
    return _render_reorder(op)


def _render_create(op: dict) -> list[str]:
    """A new entity as a field table, plus whatever prose it carries.

    The field count is a count, not a list (decision 1): a draft is *expected*
    to be incomplete, so `6 of 22 fields set` is the informative part, and
    enumerating sixteen empty fields buries the six that matter. Only
    non-computed fields count — a computed field was never offered to the
    model, so including it would inflate the denominator.
    """
    entity_type, entity_id = op["type"], op["id"]
    fm = op["frontmatter"]
    schema = ENTITY_SCHEMAS.get(entity_type, {})
    settable = {f: m for f, m in schema.items() if not m.get("computed")}
    # A draft is expected to be thin, so this count is the informative part.
    # Only non-computed fields count: the model was never offered the others,
    # so including them would inflate the denominator.
    unset = sum(1 for f, m in settable.items() if _empty(fm.get(f, m["default"]), m))

    out = [f"**＋ NEW {entity_type.upper()}** · `{entity_type}/{entity_id}`"]
    if unset:
        out[0] += f"  ·  {len(settable) - unset} of {len(settable)} fields set"
    if fm:
        out += ["", "| field | value |", "|---|---|"]
        out += [f"| {field} | {_fmt(value)} |" for field, value in fm.items()]

    for heading, body in (op.get("sections") or {}).items():
        if body:
            out += ["", f"**{heading}**"]
            out += _fence(body, _fence_lang(entity_type, heading))
    return out


def _fence(value, lang: str = "") -> list[str]:
    """A section body in its own fenced block.

    Whitespace is part of the value — a Fountain cue is defined by its
    indentation — so a body cannot be rendered as a `before → after` line the
    way a scalar field can. Markdown collapses the indentation that carries
    the meaning, and the reader sees prose where the script has structure.

    A fence also stops the client guessing: indented lines were being rendered
    as code while the surrounding prose did not, so the script appeared to
    start at the first cue rather than at the slugline. The fence delimits the
    whole section, so the boundary is the section, not an accident of
    indentation.
    """
    return [f"```{lang}", value.rstrip("\n"), "```"]


def _fence_lang(entity_type: str, field: str) -> str:
    """Language tag for the fence. Only script is labelled; prose is plain."""
    return "fountain" if (entity_type, field) == ("scene", "Content") else ""


def _section_note(entity_type: str, field: str, before, after) -> str:
    """One line describing a section change. Outside the fence, always.

    The delta has to be readable without scrolling through two full copies of
    a screenplay, so it is stated rather than shown — but the *body* is the
    thing being approved and it goes in the block below.
    """
    if not before:
        n = len(after.splitlines())
        return f"`{field}` — new section, {n} line{'' if n == 1 else 's'}."
    was, now = len(before.splitlines()), len(after.splitlines())
    if was == now:
        return f"`{field}` — rewritten, {now} lines."
    arrow = f"{was} → {now} lines"
    if field == "Content":
        # Only claim cues were added when they were: the count going *down*
        # means the prose was split into cues, and "added" would be a lie.
        verb = "cues and transitions added" if now > was else "reformatted as Fountain"
        return f"`{field}` — rewritten as Fountain; {arrow}, {verb}."
    return f"`{field}` — {arrow}."


def _render_edit(project_path: Path, op: dict) -> list[str]:
    """An edit as one line per field, `before → after` (decision 2).

    A table is for a whole entity; an edit is a delta. Two changed fields get
    two lines, not a five-row table with one populated row. A *section* is the
    exception: its body is fenced, because its whitespace is significant.
    """
    out = [f"**✏ EDIT** · `{op['entity_type']}/{op['entity_id']}`"]
    changes = _current_values(project_path, op)
    for field, value in op["data"].items():
        before = changes.get(field, (None, None))[0]
        if before == value:
            continue
        if isinstance(value, str) and "\n" in value:
            out += [_section_note(op["entity_type"], field, before, value), ""]
            out += _fence(value, _fence_lang(op["entity_type"], field))
            out.append("")
            continue
        # An unset field is `_not set_`, not an empty gap: a blank before an
        # arrow reads as a rendering fault rather than as "this was empty".
        was = f"~~{_fmt(before)}~~" if before not in (None, "") else "_not set_"
        out.append(f"`{field}`: {was} → **{_fmt(value)}**")
    if len(out) == 1:
        out.append("_No field would change._")
    return out


def _current_values(project_path: Path, op: dict) -> dict:
    """Current value per edited field, via the same lookup the edit uses.

    Reusing `writes.current_values` rather than re-deriving it: that function
    already knows a field lives in a column, in `extra`, or in a section, and
    getting that wrong would show the user a `before` that is not the real one.
    """
    from .writes import current_values

    try:
        result = current_values(
            project_path, op["entity_type"], op["entity_id"], op["data"],
        )
    except Exception:
        return {}
    return {c["field"]: (c.get("from"), c.get("to")) for c in result.get("changes", [])}


def _render_reorder(op: dict) -> list[str]:
    ids = op["ordered_ids"]
    return [f"**↕ REORDER** · `{op['entity_type']}`",
            " → ".join(f"**`{i}`**" if n == 1 else f"`{i}`"
                        for n, i in enumerate(ids, 1))]


def _render_diff(changes: dict) -> list[str]:
    """What changed since the last stage (decision 3 — the load-bearing one).

    Without this, "don't resequence" produces a preview that silently omits a
    queued change and the user cannot tell it was dropped rather than never
    proposed.
    """
    out = ["**since last stage**"]
    for key in ("added", "dropped", "changed"):
        items = changes.get(key) or []
        if not items:
            continue
        if key == "changed":
            out += [f"· ~changed~ {i['op']} ({', '.join(i['fields'])})" for i in items]
        else:
            prefix = "＋" if key == "added" else "－"
            out += [f"· {prefix} {i}" for i in items]
    return out


def _fmt_scalar(value) -> str:
    """One value, inline. A nested object becomes `k=v, k=v`."""
    if isinstance(value, dict):
        return ", ".join(f"{k}={_fmt_scalar(v)}" for k, v in value.items())
    if isinstance(value, bool):
        return "yes" if value else "no"
    return str(value)


def _fmt(value) -> str:
    """A field value for the preview.

    A structured field used to fall through to `str()`, which is a Python repr:
    single quotes, no line breaks, and it wraps mid-sentence. For
    `relationship.perspectives` that hid the one thing the field is for — two
    characters side by side — so a dict is one bolded line per entry and a list
    of objects is one line per item. `<br>` because these live in a table cell,
    where a newline would end the row.
    """
    if isinstance(value, dict):
        if not value:
            return "—"
        return "<br>".join(f"**{k}** — {_fmt_scalar(v)}" for k, v in value.items())
    if isinstance(value, list):
        if not value:
            return "—"
        if isinstance(value[0], dict):
            return "<br>".join(
                ", ".join(f"{k}: {_fmt_scalar(v)}" for k, v in item.items())
                for item in value)
        return ", ".join(str(v) for v in value)
    if isinstance(value, bool):
        return "yes" if value else "no"
    return str(value) if value not in (None, "") else "—"


def _empty(value, meta: dict) -> bool:
    """Empty in the sense unfilled_fields means: absent, blank, or the default."""
    if value is None or value == "" or value == [] or value == {}:
        return True
    return value == meta.get("default")
