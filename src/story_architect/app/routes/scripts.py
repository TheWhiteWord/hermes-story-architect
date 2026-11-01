"""Scene script editor API — the one place the browser writes (see README).

Thin: parse the request, call `core.manual_edits`, map its errors to HTTP.
Non-GET requests already pass through the Host / Origin / `X-Story-Architect`
checks in `server.py`; this adds no second auth model.
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

    @router.get("/api/projects/{slug}/scenes/{scene_id}/script")
    def get_script(slug: str, scene_id: str):
        from story_architect.core import manual_edits as me
        try:
            project = _project(slug)
            return me.load_scene_script(project, scene_id)
        except me.ScriptNotFound as e:
            return _err(404, "not_found", str(e))
        except ValueError as e:  # unknown project
            return _err(404, "not_found", str(e))

    @router.put("/api/projects/{slug}/scenes/{scene_id}/script")
    def put_script(slug: str, scene_id: str, body: dict):
        from story_architect.core import manual_edits as me
        try:
            project = _project(slug)
        except ValueError as e:
            return _err(404, "not_found", str(e))
        try:
            return me.save_scene_script(project, scene_id, body)
        except me.ScriptConflict as e:
            return _err(409, "conflict", str(e), current_hash=e.current_hash)
        except me.ScriptNotFound as e:
            return _err(404, "not_found", str(e))
        except me.ScriptLocked as e:
            return _err(423, "locked", str(e))
        except me.ScriptError as e:
            return _err(422, "invalid", str(e))
        except ValueError as e:  # refused by core.writes
            return _err(422, "invalid", str(e))

    @router.post("/api/projects/{slug}/script/parse")
    def parse_text(slug: str, body: dict):
        """Pasted Fountain -> blocks. Pure; used when text is pasted into the editor."""
        from story_architect.core import scene_script as ss
        text = (body or {}).get("text")
        if not isinstance(text, str):
            return _err(422, "invalid", "`text` must be a string.")
        heading_line, rest = ss.split_heading(text)
        return {"heading": heading_line, "blocks": ss.parse_blocks(rest)}

    return router
