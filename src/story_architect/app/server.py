"""FastAPI app factory."""
from __future__ import annotations

import hmac

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from story_architect.app.config import Config
from story_architect.app import services
from story_architect.app import token as token_mod
from story_architect.app.mcp_server import create_mcp_server, StreamableHTTPSessionManager


def create_app(config: Config) -> FastAPI:
    server = create_mcp_server(config)
    manager = StreamableHTTPSessionManager(app=server, stateless=True, json_response=True)

    @asynccontextmanager
    async def _lifespan(app):
        async with manager.run():
            yield

    app = FastAPI(docs_url=None, redoc_url=None, lifespan=_lifespan)
    app.state.config = config
    app.state.mcp_manager = manager

    @app.middleware("http")
    async def host_check(request: Request, call_next):
        host = request.headers.get("host", "")
        allowed = {"127.0.0.1", "localhost", f"127.0.0.1:{config.port}", f"localhost:{config.port}"}
        if host not in allowed:
            return JSONResponse(status_code=400, content={"error": {"code": "bad_host", "message": "Invalid Host header"}})
        resp = await call_next(request)
        resp.headers["Cache-Control"] = "no-store"
        return resp

    @app.middleware("http")
    async def mcp_auth(request: Request, call_next):
        if request.url.path.startswith("/mcp"):
            expected = token_mod.load_token()
            auth = request.headers.get("authorization", "")
            ok = bool(expected) and auth.startswith("Bearer ") and hmac.compare_digest(auth[7:].encode(), expected.encode())
            if not ok:
                return JSONResponse(status_code=401, content={"error": {"code": "unauthorized", "message": "Missing or invalid token"}})
        return await call_next(request)

    @app.get("/healthz")
    def healthz():
        return {"ok": True}

    @app.get("/api/projects")
    def projects():
        return {"projects": services.list_projects(config.root)}

    @app.get("/api/projects/{slug}/dashboard")
    def dashboard(slug: str):
        try:
            data = services.get_project_dashboard(config.root, slug)
        except services.ProjectNotFound as e:
            return JSONResponse(status_code=404, content={"error": {"code": "not_found", "message": str(e)}})
        except Exception as e:
            return JSONResponse(status_code=500, content={"error": {"code": "error", "message": str(e)}})
        return data

    class _MCPApp:
        def __init__(self, mgr):
            self.mgr = mgr
        async def __call__(self, scope, receive, send):
            await self.mgr.handle_request(scope, receive, send)

    app.mount("/mcp", app=_MCPApp(manager))

    from pathlib import Path
    import story_architect
    web_dir = Path(story_architect.__file__).parent / "web"
    if web_dir.exists():
        app.mount("/", StaticFiles(directory=str(web_dir), html=True), name="web")
    return app