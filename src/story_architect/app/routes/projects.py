from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse
import asyncio
from pathlib import Path


def make_router(config, app):
    router = APIRouter()

    @router.get("/api/projects")
    def projects():
        from story_architect.app import services
        return {"projects": services.list_projects(config.root)}

    @router.get("/api/projects/{slug}/dashboard")
    def dashboard(slug: str):
        from story_architect.app import services
        try:
            data = services.get_project_dashboard(config.root, slug)
        except services.ProjectNotFound as e:
            return JSONResponse(status_code=404, content={"error": {"code": "not_found", "message": str(e)}})
        except Exception as e:
            return JSONResponse(status_code=500, content={"error": {"code": "error", "message": str(e)}})
        return data

    @router.get("/api/projects/{slug}/events")
    async def project_events(slug: str, request: Request):
        root = Path(config.root)
        db_path = root / "projects" / slug / ".story" / "story.db"

        async def gen():
            import sqlite3
            last_version = None
            try:
                while True:
                    if await request.is_disconnected():
                        break
                    try:
                        conn = sqlite3.connect(str(db_path))
                        cur = conn.execute("PRAGMA data_version")
                        version = cur.fetchone()[0]
                        conn.close()
                    except Exception:
                        version = None
                    if last_version is not None and version != last_version:
                        yield "event: update\ndata: {\"type\": \"update\"}\n\n"
                    last_version = version
                    await asyncio.sleep(1)
            except asyncio.CancelledError:
                return

        return StreamingResponse(gen(), media_type="text/event-stream")

    return router
