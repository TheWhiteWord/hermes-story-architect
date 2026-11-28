"""A persistent merge session: plan, selection, decisions and apply, over several calls.

A plan is derived from three states, and deriving it again from the same inputs gives
the same plan. So a session stores the INPUTS — the source, the base, the selection, the
decisions — and never the op list. `show`, `preview` and `apply` each re-plan from the
row, which is why a stored session cannot disagree with the code that would apply it.

What `merge_sessions` keeps (§4.2):

  * ``source_ref`` — where the changes come from: a draft, or another branch's head.
  * ``base_snapshot_id`` — the draft the three-way comparison starts at, resolved once
    when the session opens: it is a property of the two sides' history, not of the
    selection.
  * ``selection`` — the item keys to bring.
  * ``decisions`` — the answers already given, keyed by the planner's stable decision
    key. An unanswered decision is absent, never a stored default.
  * ``target_fingerprint`` — the target at the moment the session opened, which is what
    §7.7.4's stale check compares. A refusal is not a refresh: the caller starts a new
    session with the same selection and decisions, which `show` returns.
  * ``status`` — `open`, `applied` or `discarded`.

The target is a branch's head, live or parked (§7.8). A live target delegates to
`execute.apply`. A parked target cannot: `execute.apply` takes the manifest lock and
adopts its project path as a new project, so on a scratch copy it writes a throwaway
history and leaves the real branch no pre-merge draft. That path therefore takes the
lock once, copies the head out, freezes that branch's pre-merge draft from the copy,
runs the ops there, and writes the copy back.
"""

from __future__ import annotations

import json
import sqlite3
import tempfile
from contextlib import ExitStack, closing
from pathlib import Path

from .. import clock
from ..db import get_db
from . import execute, fingerprint, plan, store, view


class DecisionKeyError(ValueError):
    """The key names no decision this session's plan holds.

    A subclass so a boundary can tell a bad request (a key that will never be valid
    as sent) from a core refusal (a valid request the rules declined), which are
    different HTTP statuses.
    """


__all__ = [
    "start",
    "show",
    "set_selection",
    "set_decision",
    "preview",
    "apply",
    "discard",
    "DecisionKeyError",
]

OPEN, APPLIED, DISCARDED = "open", "applied", "discarded"

_COLUMNS = (
    "id, target_branch_id, source_ref, base_snapshot_id, target_fingerprint, "
    "selection, decisions, status, created_at, updated_at"
)


# ─── the row ───


def _row(row) -> dict:
    return {
        "id": row[0],
        "target_branch_id": row[1],
        "source": json.loads(row[2]),
        "base_snapshot_id": row[3],
        "target_fingerprint": row[4],
        "selection": json.loads(row[5] or "[]"),
        "decisions": json.loads(row[6] or "{}"),
        "status": row[7],
        "created_at": row[8],
        "updated_at": row[9],
    }


def _get(conn: sqlite3.Connection, session_id: str) -> dict:
    row = conn.execute(
        f"SELECT {_COLUMNS} FROM merge_sessions WHERE id=?", (session_id,)
    ).fetchone()
    if not row:
        raise ValueError(f"No such merge session: {session_id}.")
    return _row(row)


def _new_id(conn: sqlite3.Connection) -> str:
    """An unused session id: its microsecond timestamp, plus a counter if that is taken."""
    stamp = clock.now_iso(timespec="microseconds")  # 2026-11-26T02:11:01.123456+00:00
    base = f"m-{stamp[:19].replace('-', '').replace(':', '')}{stamp[20:26]}"
    candidate, n = base, 1
    while conn.execute("SELECT 1 FROM merge_sessions WHERE id=?", (candidate,)).fetchone():
        n += 1
        candidate = f"{base}-{n}"
    return candidate


def _write(conn: sqlite3.Connection, session: dict, **changes) -> dict:
    """Update one row's mutable columns and return it re-read."""
    fields = {**session, **changes, "updated_at": clock.now_iso()}
    conn.execute(
        "UPDATE merge_sessions SET base_snapshot_id=?, target_fingerprint=?, selection=?, "
        "decisions=?, status=?, updated_at=? WHERE id=?",
        (
            fields["base_snapshot_id"],
            fields["target_fingerprint"],
            json.dumps(fields["selection"]),
            json.dumps(fields["decisions"]),
            fields["status"],
            fields["updated_at"],
            fields["id"],
        ),
    )
    return _get(conn, fields["id"])


def _require_open(session: dict) -> None:
    if session["status"] != OPEN:
        raise ValueError(f"This merge session is {session['status']}; start a new one.")


# ─── refs and paths ───


def _source_of(project_path: Path, source: dict) -> dict:
    """Check a source ref and keep what the row stores about it.

    `base_snapshot_id` is the source's own latest draft: a draft IS one, a branch head
    is its branch's. It is what `merge_base` walks from, because an unsaved change has
    no place in the snapshot graph.
    """
    kind, ref_id = (source or {}).get("kind"), (source or {}).get("id")
    if kind not in ("snapshot", "branch") or not ref_id:
        raise ValueError('A merge\'s source is {"kind": "snapshot"|"branch", "id": …}.')
    if kind == "snapshot":
        with closing(store.connect(project_path)) as conn:
            if not store._snapshot(conn, ref_id):
                raise ValueError(f"No such draft: {ref_id}.")
        return {"kind": kind, "id": ref_id, "base_snapshot_id": ref_id}
    branch = store.get_branch(project_path, ref_id)
    return {"kind": kind, "id": ref_id, "base_snapshot_id": branch["base_snapshot_id"]}


def _source_view(project_path: Path, session: dict):
    """The source as a project path: a draft, or another branch's parked head."""
    if session["source"]["kind"] == "snapshot":
        return view.project_view(project_path, session["source"]["id"])
    return view.head_view(project_path, session["source"]["id"])


def _source_draft(session: dict) -> str | None:
    """The source's own draft id, or None when it is a head with unsaved changes.

    §7.9's complete merge records the source as a parent, and a parent means "everything
    in it is already accounted for". No draft accounts for an unsaved head's changes, so
    only a draft source can be declared complete.
    """
    source = session["source"]
    return source["id"] if source["kind"] == "snapshot" else None


def _target_view(project_path: Path, branch: dict):
    """The target as a project path — the live project, or a copy of its parked head."""
    if branch["is_current"]:
        return _LiveTarget(project_path)
    return view.head_view(project_path, branch["id"])


class _LiveTarget:
    """The live project, spelled as a context manager so `_plan` has one shape."""

    def __init__(self, project_path: Path):
        self.project_path = project_path

    def __enter__(self) -> Path:
        return self.project_path

    def __exit__(self, *exc) -> None:
        return None


def _base(project_path: Path, session: dict) -> str:
    """The merge base of the target branch's saved draft and the source's (§7.1)."""
    target = store.get_branch(project_path, session["target_branch_id"])
    found = store.merge_base(
        project_path, target["base_snapshot_id"], session["source"]["base_snapshot_id"]
    )
    if not found["base"]:
        raise ValueError(
            "These two sides share no history, so there is no base to merge from. "
            "They are drafts of different projects."
        )
    return found["base"]


def _fingerprint(project_path: Path, branch: dict) -> str:
    """The branch head's fingerprint, reading a parked head from its own copy."""
    if branch["is_current"]:
        return fingerprint.of_project(project_path)
    with view.head_view(project_path, branch["id"]) as target:
        return fingerprint.of_project(target)


def _plan(project_path: Path, session: dict, branch: dict | None = None) -> dict:
    """Re-plan the session from the target's current state.

    The plan is stamped with the fingerprint the session OPENED at, not with the target's
    fingerprint now: §7.7.4's stale check compares the state a plan was made against, and
    a fingerprint read during the re-plan would always match itself.
    """
    _require_open(session)
    branch = branch or store.get_branch(project_path, session["target_branch_id"])
    with ExitStack() as stack:
        base = stack.enter_context(view.project_view(project_path, session["base_snapshot_id"]))
        theirs = stack.enter_context(_source_view(project_path, session))
        ours = stack.enter_context(_target_view(project_path, branch))
        planned = plan.plan(
            base, ours, theirs, selection=session["selection"], decisions=session["decisions"]
        )
    return {**planned, "fingerprint": session["target_fingerprint"]}


# ─── API ───


def start(
    project_path: Path, target_branch_id: str, source: dict, *, selection=None, decisions=None
) -> dict:
    """Open a session bringing `source` into `target_branch_id`'s head.

    The base and the target's fingerprint are resolved now, because both are facts about
    the moment the merge was started: a base found later is a different three-way
    question, and a fingerprint found later guards nothing.
    """
    store.adopt(project_path)
    target = store.get_branch(project_path, target_branch_id)
    resolved = _source_of(project_path, source)
    if resolved["kind"] == "branch" and resolved["id"] == target["id"]:
        raise ValueError(
            f"{target['name']!r} cannot be merged into itself: it is the branch you are on."
        )
    session = {
        "id": None,
        "target_branch_id": target["id"],
        "source": resolved,
        "base_snapshot_id": None,
        "target_fingerprint": None,
        "selection": sorted(set(selection or ())),
        "decisions": dict(decisions or {}),
        "status": OPEN,
    }
    with store.locked(project_path) as conn:
        session["base_snapshot_id"] = _base(project_path, session)
        session["target_fingerprint"] = _fingerprint(project_path, target)
        session["id"] = _new_id(conn)
        conn.execute(
            f"INSERT INTO merge_sessions ({_COLUMNS}) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (
                session["id"],
                session["target_branch_id"],
                json.dumps(session["source"]),
                session["base_snapshot_id"],
                session["target_fingerprint"],
                json.dumps(session["selection"]),
                json.dumps(session["decisions"]),
                OPEN,
                clock.now_iso(),
                clock.now_iso(),
            ),
        )
        return _get(conn, session["id"])


def show(project_path: Path, session_id: str) -> dict:
    """The session, its freshly derived plan, and whether that plan still applies.

    `stale` says the target moved since the session opened; `imprecise_base` says the
    base was a guess on a criss-cross history (§7.1, §14-F). A closed session reports
    no plan: re-deriving one would describe a merge that is not on offer any more.
    """
    with closing(store.connect(project_path)) as conn:
        session = _get(conn, session_id)
    if session["status"] != OPEN:
        return {**session, "plan": None, "stale": False, "imprecise_base": False}
    branch = store.get_branch(project_path, session["target_branch_id"])
    planned = _plan(project_path, session, branch)
    target = store.get_branch(project_path, session["target_branch_id"])
    found = store.merge_base(
        project_path, target["base_snapshot_id"], session["source"]["base_snapshot_id"]
    )
    return {
        **session,
        "plan": planned,
        "stale": bool(execute.stale(planned, _fingerprint(project_path, branch))),
        "imprecise_base": bool(found["imprecise"]),
    }


def set_selection(project_path: Path, session_id: str, selection) -> dict:
    """Replace the selected item keys. Apply stays disabled until the plan is ready."""
    with store.locked(project_path) as conn:
        session = _get(conn, session_id)
        _require_open(session)
        return _write(conn, session, selection=sorted(set(selection or ())))


def set_decision(
    project_path: Path, session_id: str, key: str, choice, *, value=None, set_by="user"
) -> dict:
    """Record one decision's answer. `set_by` is `user` or `agent-suggested` (§7.5).

    `value` is what a `custom` answer, or a keep-both's new id and fields, was typed as;
    an answer replaces the previous one whole, so a changed choice drops the old value.

    An agent's suggestion does not answer the decision: the planner keeps Apply disabled
    for it until a person chooses, which is the whole point of the distinction.

    The key is checked against a fresh plan first. Without that, any key was stored and
    ignored: a typo returned success and left the decision open, which reads as an
    answer that did nothing. A decision can also appear only after another one is
    answered — `D2` on `plot_roles` chosen `theirs` can raise a `D4` the default plan
    never listed — so "your item is in this plan but not this decision" is reported as
    *not yet asked*, not as a bad key.
    """
    with store.locked(project_path) as conn:
        session = _get(conn, session_id)
        _require_open(session)
        valid = _decision_keys(project_path, session)
        if key not in valid:
            item, _, code = key.rpartition("#")
            if not item or code not in plan.CATALOGUE:
                raise DecisionKeyError(
                    f"{key!r} is not a decision key. A decision's key is its item plus its "
                    f"code, like {next(iter(valid), '<item>#D2')!r}. Percent-encode it when "
                    "putting it in a URL."
                )
            raise DecisionKeyError(
                f"Decision {key!r} is not asked (yet). Answering another decision can raise "
                f"it — a D2 chosen `theirs` on `plot_roles` can raise a D4. Its decisions "
                f"now are: {', '.join(sorted(valid)) or 'none'}."
            )
        return _write(
            conn,
            session,
            decisions={
                **session["decisions"],
                key: {
                    "choice": choice,
                    "set_by": set_by,
                    **({"value": value} if value is not None else {}),
                },
            },
        )


def _decision_keys(project_path: Path, session: dict) -> set[str]:
    """The decision keys the session's plan holds right now."""
    return {d["key"] for d in _plan(project_path, session)["decisions"]}


def preview(project_path: Path, session_id: str) -> dict:
    """The dry-run verdict for this session, with the plan it came from."""
    with closing(store.connect(project_path)) as conn:
        session = _get(conn, session_id)
    _require_open(session)
    branch = store.get_branch(project_path, session["target_branch_id"])
    planned = _plan(project_path, session, branch)
    if not planned["ready"]:
        return {
            "status": "blocked",
            "open": planned["open"],
            "plan": planned,
            "message": "Some decisions are still unanswered.",
        }
    with _target_view(project_path, branch) as target:
        return {**execute.dry_run(target, planned), "plan": planned}


def apply(project_path: Path, session_id: str, *, complete: bool = False) -> dict:
    """Apply this session's plan to the target branch's head.

    `complete` declares §7.9's complete merge: everything in the source is now accounted
    for, so it becomes a parent at that branch's next save. It needs a draft source — an
    unsaved head's changes are not accounted for by any draft, so the declaration would
    be false.

    No lock is held across this call. A live target's `execute.apply` takes the manifest
    lock itself (§4.5), and a parked target's merge takes it below — so the session row
    is marked in its own short transaction afterwards, never nested in either.
    """
    with closing(store.connect(project_path)) as conn:
        session = _get(conn, session_id)
    _require_open(session)
    if complete and _source_draft(session) is None:
        raise ValueError(
            "A complete merge needs a saved draft as its source. Save that branch's "
            "draft first, or merge without declaring it complete."
        )
    branch = store.get_branch(project_path, session["target_branch_id"])
    if branch["is_current"]:
        result = _live(project_path, session, complete)
    else:
        with store.locked(project_path) as conn:
            result = _parked(project_path, session, conn, branch, complete)
    if result["status"] == "applied":
        _mark(project_path, session_id, APPLIED)
    return result


def _mark(project_path: Path, session_id: str, status: str) -> dict:
    """Set a session's status in its own manifest transaction."""
    with store.locked(project_path) as conn:
        return _write(conn, _get(conn, session_id), status=status)


def _source_name(project_path: Path, session: dict) -> str:
    """The source as a person named it: a draft's label, or a branch's name."""
    source = session["source"]
    if source["kind"] == "branch":
        return f"{store.get_branch(project_path, source['id'])['name']} (open draft)"
    for draft in store.list_branches(project_path)["snapshots"]:
        if draft["id"] == source["id"]:
            return draft["label"]
    return source["id"]


def _live(project_path: Path, session: dict, complete: bool) -> dict:
    """The live head is the target: `execute.apply` owns this path end to end."""
    branch = store.get_branch(project_path, session["target_branch_id"])
    planned = _plan(project_path, session, branch)
    return execute.apply(
        project_path,
        planned,
        parent_source=_source_draft(session) if complete else None,
        label=f"Before merge from {_source_name(project_path, session)}",
    )


def _parked(project_path: Path, session: dict, conn, branch: dict, complete: bool) -> dict:
    """Merge into a branch that is not loaded: copy its head out, apply, write back.

    `execute.apply` would adopt the throwaway copy as a new project instead of merging
    into this branch, so the steps are taken here: the pre-merge draft of THIS branch,
    then the ops in one transaction on the copy, then the head file replaced. The
    manifest lock is already held, which is what makes the file move and the row write
    one operation.
    """
    planned = _plan(project_path, session, branch)
    if not planned["ready"]:
        return {
            "status": "blocked",
            "open": planned["open"],
            "message": "Some decisions are still unanswered. Apply stays disabled until "
            "each one has a choice.",
        }
    refusal = execute.stale(planned, _fingerprint(project_path, branch))
    if refusal:
        return refusal

    head = store.head_file(project_path, branch["id"])
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        scratch = Path(tmp)
        (scratch / ".story").mkdir()
        with closing(sqlite3.connect(f"file:{head}?mode=ro", uri=True)) as src:
            dest = get_db(scratch)
            try:
                src.backup(dest)
            finally:
                dest.close()

        baseline = store.restore_point(
            project_path,
            conn,
            f"Before merge from {_source_name(project_path, session)}",
            branch_id=branch["id"],
            head=scratch,
        )
        failures = execute._run(scratch, planned)
        if failures:
            return {"status": "refused", "failures": failures, "baseline": baseline}
        store._park(project_path, scratch / ".story" / "story.db", head)
        parents = None
        if complete:
            source_id = _source_draft(session)
            assert source_id is not None, "a complete merge was refused without a draft source"
            parents = store.record_pending_parent(
                project_path, source_id, conn=conn, branch_id=branch["id"]
            )
        return {
            "status": "applied",
            "applied": [
                {"op": op["op"], "summary": op.get("summary", ""), "source": op.get("source")}
                for op in planned["ops"]
            ],
            "baseline": baseline,
            "parents": parents["pending_merge_parents"] if parents else None,
        }


def discard(project_path: Path, session_id: str) -> dict:
    """Close a session without applying it. Its row stays, marked `discarded`."""
    with store.locked(project_path) as conn:
        session = _get(conn, session_id)
        _require_open(session)
        return _write(conn, session, status=DISCARDED)
