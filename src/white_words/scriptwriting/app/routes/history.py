"""Drafts, branches and merges over HTTP — `/api/projects/{slug}/history/`.

Thin, like `trash.py`: resolve the project, call `core.history`, map a refusal to
HTTP. The behaviours live in the core so the agent's tools (T11) reach the same
rules, and this module contains none of them.

Two things are decided here rather than in the core:

  * **A project is resolved by exact slug.** These routes switch the live database
    and delete branches and drafts, and `resolve_project` fuzzy-matches at 75/100
    for the agent's tools, where someone types a name loosely. An HTTP client gets
    the slug from `/api/projects`, so it never needs a guess — and a guess landing
    on a neighbouring project must not be able to delete anything.
  * **A destructive action needs `confirm: true`**: switch, delete branch, delete
    draft, apply. A second line of defence, and it costs the UI one dialog.

Refs: a state is `snapshot:<id>` or `branch:<id>`; a bare id means a draft. A
decision key is a path segment, so the client percent-encodes it — `#` ends a URL
fragment, and an unencoded one arrives truncated and names a different decision.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter

from white_words.scriptwriting.app.routes.errors import _err
from white_words.scriptwriting.core.history import session as session_errors


def _ref(value) -> dict:
    """`{"kind", "id"}` as-is, or `snapshot:<id>` / `branch:<id>` / a bare id.

    A body may send either: a POST body can carry an object, while a query string
    can only carry the string form.
    """
    if isinstance(value, dict):
        if value.get("kind") in ("snapshot", "branch") and value.get("id"):
            return {"kind": value["kind"], "id": value["id"]}
        raise ValueError(f"{value!r} is not a ref. Use `snapshot:<id>` or `branch:<id>`.")
    kind, sep, ref_id = str(value).partition(":")
    if not sep:
        return {"kind": "snapshot", "id": str(value)}
    if kind not in ("snapshot", "branch") or not ref_id:
        raise ValueError(f"{value!r} is not a ref. Use `snapshot:<id>` or `branch:<id>`.")
    return {"kind": kind, "id": ref_id}


def make_router(config, app):
    router = APIRouter()

    def _project(slug):
        """Exact slug only (see the module docstring)."""
        from white_words.scriptwriting.tools.story_resolve import resolve_project

        root = Path(config.root)
        exact = root / "projects" / slug
        if slug and Path(slug).name == slug and exact.is_dir():
            return resolve_project(slug, root)
        raise ValueError(f"No project called {slug!r}.")

    def _run(slug, fn):
        try:
            project = _project(slug)
        except ValueError as e:
            return _err(404, "not_found", str(e))
        try:
            return fn(project)
        except session_errors.DecisionKeyError as e:
            return _err(422, "invalid_decision_key", str(e))
        except ValueError as e:  # a core refusal, already actionable
            return _err(409, "refused", str(e))

    def _confirm(body: dict | None, action: str):
        """`None` when confirmed, else the refusal response."""
        if (body or {}).get("confirm") is True:
            return None
        return _err(422, "confirm_required", f"Pass confirm: true to {action}.")

    # ─── reads ───

    @router.get("/api/projects/{slug}/history/")
    def history(slug: str):
        """Branches, drafts with parents, and what each branch's head holds now."""
        from white_words.scriptwriting.core.history import graph

        return _run(slug, graph.summary)

    @router.get("/api/projects/{slug}/history/status")
    def history_status(slug: str):
        """The current branch and draft, and how far the project has moved since."""
        from white_words.scriptwriting.core.history import listing

        return _run(slug, listing.status)

    @router.get("/api/projects/{slug}/history/diff")
    def history_diff(slug: str, a: str, b: str):
        """Every difference between two states; the script view is a lens on them."""
        from white_words.scriptwriting.core.history import diff, view as views

        try:
            ref_a, ref_b = _ref(a), _ref(b)
        except ValueError as e:
            return _err(422, "invalid", str(e))

        def go(project):
            with views.ref_view(project, ref_a) as pa, views.ref_view(project, ref_b) as pb:
                return diff.compare(pa, pb)

        return _run(slug, go)

    @router.get("/api/projects/{slug}/history/read/{ref}/entities")
    def history_read_index(slug: str, ref: str):
        """Every entity of a state, by id, type and name: the reader's list."""
        from white_words.scriptwriting.core.db import get_db
        from white_words.scriptwriting.core.history import logical, view as views

        try:
            parsed = _ref(ref)
        except ValueError as e:
            return _err(422, "invalid", str(e))

        def go(project):
            with views.ref_view(project, parsed) as path:
                conn = get_db(path)
                try:
                    shape = logical.materialize(conn)
                finally:
                    conn.close()
            return {"ref": ref, "entities": logical.index(shape)}

        return _run(slug, go)

    @router.get("/api/projects/{slug}/history/read/{ref}/entities/{etype}/{eid}")
    def history_read_entity(slug: str, ref: str, etype: str, eid: str):
        """One entity as it exists in that state."""
        from white_words.scriptwriting.core.history import logical, view as views
        from white_words.scriptwriting.core.db import get_db

        try:
            parsed = _ref(ref)
        except ValueError as e:
            return _err(422, "invalid", str(e))

        def go(project):
            with views.ref_view(project, parsed) as path:
                conn = get_db(path)
                try:
                    shape = logical.materialize(conn)
                finally:
                    conn.close()
            entity = shape.get(eid)
            if entity is None or entity["type"] != etype:
                raise ValueError(f"No live {etype} {eid!r} in {ref}.")
            return entity

        return _run(slug, go)

    @router.get("/api/projects/{slug}/history/read/{ref}/script")
    def history_read_script(slug: str, ref: str):
        """The composed screenplay of a state, in story order."""
        from white_words.scriptwriting.core.history import view as views
        from white_words.scriptwriting.core.db import get_screenplay_text

        try:
            parsed = _ref(ref)
        except ValueError as e:
            return _err(422, "invalid", str(e))

        return _run(
            slug,
            lambda p: _script(views, get_screenplay_text, p, parsed, ref),
        )

    # ─── writes ───

    @router.post("/api/projects/{slug}/history/snapshots")
    def save_snapshot(slug: str, body: dict | None = None):
        """Save the live head as a draft. Refused when nothing changed."""
        from white_words.scriptwriting.core.history import store

        body = body or {}
        return _run(
            slug,
            lambda p: store.save_snapshot(p, body.get("label"), body.get("note") or ""),
        )

    @router.post("/api/projects/{slug}/history/branches")
    def branch_from(slug: str, body: dict | None = None):
        """Start a branch at a draft; its head is parked, ready to switch to."""
        from white_words.scriptwriting.core.history import store

        body = body or {}
        if not body.get("snapshot") or not body.get("name"):
            return _err(422, "invalid", "A branch needs `snapshot` and `name`.")
        return _run(slug, lambda p: store.branch_from(p, body["snapshot"], body["name"]))

    @router.post("/api/projects/{slug}/history/switch")
    def switch(slug: str, body: dict | None = None):
        """Make a branch current, loading its head into the live database."""
        from white_words.scriptwriting.core.history import store

        body = body or {}
        refused = _confirm(body, "switch branch")
        if refused:
            return refused
        if not body.get("branch"):
            return _err(422, "invalid", "switch needs `branch`.")
        return _run(slug, lambda p: store.switch(p, body["branch"]))

    @router.patch("/api/projects/{slug}/history/branches/{branch_id}")
    def rename_branch(slug: str, branch_id: str, body: dict | None = None):
        """Change a branch's display name; its id, files and history do not move."""
        from white_words.scriptwriting.core.history import store

        name = (body or {}).get("name")
        if not name:
            return _err(422, "invalid", "rename needs `name`.")
        return _run(slug, lambda p: store.rename_branch(p, branch_id, name))

    @router.delete("/api/projects/{slug}/history/branches/{branch_id}")
    def delete_branch(slug: str, branch_id: str, body: dict | None = None):
        """Delete a branch, its parked head, and every draft nothing else reaches."""
        from white_words.scriptwriting.core.history import store

        refused = _confirm(body, "delete a branch")
        if refused:
            return refused
        return _run(slug, lambda p: store.delete_branch(p, branch_id))

    @router.delete("/api/projects/{slug}/history/snapshots/{snapshot_id}")
    def delete_snapshot(slug: str, snapshot_id: str, body: dict | None = None):
        """Delete one draft, re-attaching its children to its own parents."""
        from white_words.scriptwriting.core.history import store

        refused = _confirm(body, "delete a draft")
        if refused:
            return refused
        return _run(slug, lambda p: store.delete_snapshot(p, snapshot_id))

    # ─── merges ───

    @router.post("/api/projects/{slug}/history/merges")
    def start_merge(slug: str, body: dict | None = None):
        """Open a session bringing `source` into `target`'s head (§7.1)."""
        from white_words.scriptwriting.core.history import session

        body = body or {}
        if not body.get("target") or not body.get("source"):
            return _err(422, "invalid", "A merge needs `target` (a branch) and `source`.")
        try:
            source = _ref(body["source"])
        except ValueError as e:
            return _err(422, "invalid", str(e))
        return _run(
            slug,
            lambda p: session.start(
                p,
                body["target"],
                source,
                selection=body.get("selection"),
                decisions=body.get("decisions"),
            ),
        )

    @router.get("/api/projects/{slug}/history/merges/{session_id}")
    def show_merge(slug: str, session_id: str):
        """The session, its freshly derived plan, and whether it still applies."""
        from white_words.scriptwriting.core.history import session

        return _run(slug, lambda p: session.show(p, session_id))

    @router.put("/api/projects/{slug}/history/merges/{session_id}/selection")
    def set_selection(slug: str, session_id: str, body: dict | None = None):
        """Replace the selected item keys. Apply stays disabled until the plan is ready."""
        from white_words.scriptwriting.core.history import session

        return _run(
            slug,
            lambda p: session.set_selection(p, session_id, (body or {}).get("selection") or []),
        )

    @router.put("/api/projects/{slug}/history/merges/{session_id}/decisions/{key:path}")
    def set_decision(slug: str, session_id: str, key: str, body: dict | None = None):
        """Answer one decision. `key` is `<item>#<code>` and arrives percent-encoded.

        A key this session's plan does not hold is a 422 from the core: malformed, or
        not asked yet because another answer would raise it.
        """
        from white_words.scriptwriting.core.history import session

        body = body or {}
        if "choice" not in body:
            return _err(422, "invalid", "A decision needs `choice`.")
        return _run(
            slug,
            lambda p: session.set_decision(
                p, session_id, key, body["choice"], set_by=body.get("set_by") or "user"
            ),
        )

    @router.post("/api/projects/{slug}/history/merges/{session_id}/preview")
    def preview_merge(slug: str, session_id: str):
        """The dry-run verdict. It copies the target, so call it on an explicit action.

        `blocked` is a 200 here, not a 409: the preview's job is to report the verdict,
        and "some decisions are still unanswered" is a successful report of an
        incomplete plan — the client renders those keys. `refused` is a 409, because
        the ops would fail and the caller has to re-plan or fix something.
        """
        from white_words.scriptwriting.core.history import session

        return _run(slug, lambda p: _preview(session, p, session_id))

    @router.post("/api/projects/{slug}/history/merges/{session_id}/apply")
    def apply_merge(slug: str, session_id: str, body: dict | None = None):
        """Apply the plan. `complete: true` declares §7.9's whole merge."""
        from white_words.scriptwriting.core.history import session

        body = body or {}
        refused = _confirm(body, "apply a merge")
        if refused:
            return refused

        def go(project):
            result = session.apply(project, session_id, complete=bool(body.get("complete")))
            if result.get("status") == "applied":
                return result
            return _refusal(result)

        return _run(slug, go)

    @router.delete("/api/projects/{slug}/history/merges/{session_id}")
    def discard_merge(slug: str, session_id: str):
        """Close a session without applying it. Its row stays, marked `discarded`."""
        from white_words.scriptwriting.core.history import session

        return _run(slug, lambda p: session.discard(p, session_id))

    return router


def _preview(session, project, session_id):
    """A dry run: 200 for a verdict, 409 only when the ops themselves would fail."""
    result = session.preview(project, session_id)
    if result.get("status") in ("clean", "blocked"):
        return result
    return _refusal(result)


def _refusal(result: dict):
    """`execute.apply` / `dry_run` spell a refusal three ways; HTTP spells them once.

    A stale plan keeps its own code, because the client must re-plan rather than fix
    an op. `blocked` carries the unanswered decision keys; `refused` carries the
    `failures` mapped to the items that produced them.
    """
    from starlette.responses import JSONResponse

    code = "stale_plan" if result.get("code") == "stale_plan" else result.get("status", "refused")
    return JSONResponse(status_code=409, content={"error": {"code": code, **result}})


def _script(views, compose, project, parsed, ref):
    """The composed screenplay of one state, through a private copy of it."""
    from white_words.scriptwriting.core.screenplay import render_html

    with views.ref_view(project, parsed) as path:
        text = compose(path)
        return {"ref": ref, "text": text, "html": render_html(text)}
