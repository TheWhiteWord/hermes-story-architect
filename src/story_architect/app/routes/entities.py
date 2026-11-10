"""Entity form API — create, edit and delete from the browser.

Thin, like `scripts.py`: parse the request, call `core.manual_entities`, map its
errors to HTTP. Non-GET requests already pass through the Host / Origin /
`X-Story-Architect` checks in `server.py`; this adds no second auth model.

Error bodies are `{"error": {"code", "message", ...}}`. A field-level problem
(422) carries `errors` — `{field: message}` — so the form can put each message
next to its input.
"""
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import JSONResponse


def _err(status: int, code: str, message: str, **extra):
    return JSONResponse(status_code=status,
                        content={"error": {"code": code, "message": message, **extra}})


def make_router(config, app):
    router = APIRouter()

    def _project(slug):
        from story_architect.tools.story_resolve import resolve_project
        return resolve_project(slug, Path(config.root))

    def _run(slug, fn):
        """Call `fn(project_path)` and translate the form errors."""
        from story_architect.core import manual_entities as me
        try:
            project = _project(slug)
        except ValueError as e:                     # unknown project
            return _err(404, "not_found", str(e))
        try:
            return fn(project)
        except me.EntityNotFound as e:
            return _err(404, "not_found", str(e))
        except me.EntityConflict as e:
            return _err(409, "conflict", str(e), current_version=e.current_version)
        except me.EntityBlocked as e:
            return _err(409, "blocked", str(e), blockers=e.blockers)
        except me.EntityInvalid as e:
            return _err(422, "invalid", str(e), errors=e.errors, warnings=e.warnings)
        except ValueError as e:                     # refused by core.writes
            return _err(422, "invalid", str(e), errors={"_form": str(e)}, warnings={})

    @router.get("/api/projects/{slug}/form-spec")
    def form_spec(slug: str):
        from story_architect.core import manual_entities as me
        return {"types": me.all_specs()}

    @router.get("/api/projects/{slug}/entities/{etype}/{eid}/form")
    def load(slug: str, etype: str, eid: str):
        from story_architect.core import manual_entities as me
        return _run(slug, lambda p: me.load_entity(p, etype, eid))

    @router.post("/api/projects/{slug}/entities/{etype}/check")
    def check(slug: str, etype: str, body: dict):
        """Dry run: errors and warnings for an unsaved form. Writes nothing."""
        from story_architect.core import manual_entities as me
        return _run(slug, lambda p: me.check_entity(p, etype, body, (body or {}).get("id")))

    @router.post("/api/projects/{slug}/entities/{etype}")
    def create(slug: str, etype: str, body: dict):
        from story_architect.core import manual_entities as me
        return _run(slug, lambda p: me.create_form_entity(p, etype, body))

    @router.put("/api/projects/{slug}/entities/{etype}/{eid}")
    def edit(slug: str, etype: str, eid: str, body: dict):
        from story_architect.core import manual_entities as me
        return _run(slug, lambda p: me.edit_form_entity(p, etype, eid, body))

    @router.get("/api/projects/{slug}/entities/{etype}/{eid}/delete-preview")
    def preview(slug: str, etype: str, eid: str):
        from story_architect.core import manual_entities as me
        return _run(slug, lambda p: me.delete_preview(p, etype, eid))

    @router.delete("/api/projects/{slug}/entities/{etype}/{eid}")
    def delete(slug: str, etype: str, eid: str):
        from story_architect.core import manual_entities as me
        return _run(slug, lambda p: me.delete_form_entity(p, etype, eid))

    return router
