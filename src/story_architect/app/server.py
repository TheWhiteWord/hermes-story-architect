"""FastAPI app factory."""
from __future__ import annotations

import hmac

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from story_architect.app.config import Config
from story_architect.app import token as token_mod
from story_architect.app.mcp_server import create_mcp_server, StreamableHTTPSessionManager
from story_architect.app.routes import agent as agent_routes
from story_architect.app.routes import chat as chat_routes
from story_architect.app.routes import drafts as drafts_routes
from story_architect.app.routes import projects as projects_routes


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
    app.state.active_replies = {}
    app.state.agent_started_by_app = False
    # chat service (backend over the profile's API server)
    try:
        from story_architect.adapters.hermes.chat_backend import HermesChatBackend
        from story_architect.chat.service import ChatService
        from story_architect.app import token as _token_mod
        _ak = _token_mod.load_api_key()
        _base = f"http://127.0.0.1:{config.hermes_api_port}"
        app.state.chat_service = ChatService(HermesChatBackend(base_url=_base, api_key=_ak or "", model=config.hermes_profile))
    except Exception:
        app.state.chat_service = None

    @app.middleware("http")
    async def host_check(request: Request, call_next):
        host = request.headers.get("host", "")
        allowed = {"127.0.0.1", "localhost", f"127.0.0.1:{config.port}", f"localhost:{config.port}"}
        if host not in allowed:
            return JSONResponse(status_code=400, content={"error": {"code": "bad_host", "message": "Invalid Host header"}})
        if request.method != "GET":
            origin = request.headers.get("origin")
            if origin is not None:
                own = {f"http://127.0.0.1:{config.port}", f"http://localhost:{config.port}"}
                if origin not in own:
                    return JSONResponse(status_code=403, content={"error": {"code": "forbidden_origin", "message": "Foreign origin"}})
            if request.headers.get("x-story-architect") != "1" and not request.url.path.startswith("/mcp"):
                return JSONResponse(status_code=403, content={"error": {"code": "missing_custom_header", "message": "Missing custom header"}})
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

    app.include_router(agent_routes.make_router(config, app))
    app.include_router(chat_routes.make_router(config, app))
    app.include_router(drafts_routes.make_router(config, app))
    app.include_router(projects_routes.make_router(config, app))

    @app.get("/healthz")
    def healthz():
        return {"ok": True}

    class _MCPApp:
        def __init__(self, mgr):
            self.mgr = mgr
        async def __call__(self, scope, receive, send):
            await self.mgr.handle_request(scope, receive, send)

    from starlette.responses import RedirectResponse

    @app.api_route("/mcp", methods=["GET", "POST", "DELETE", "PUT", "PATCH", "OPTIONS", "HEAD"])
    async def _mcp_redirect(request: Request):
        return RedirectResponse(url="/mcp/", status_code=307)

    app.mount("/mcp/", app=_MCPApp(manager))

    from pathlib import Path
    import story_architect
    web_dir = Path(story_architect.__file__).parent / "web"
    if web_dir.exists():
        app.mount("/", StaticFiles(directory=str(web_dir), html=True), name="web")
    return app
