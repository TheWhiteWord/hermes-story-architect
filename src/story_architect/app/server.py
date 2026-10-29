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
        if request.method != "GET":
            origin = request.headers.get("origin")
            if origin is not None:
                own = {f"http://127.0.0.1:{config.port}", f"http://localhost:{config.port}"}
                if origin not in own:
                    return JSONResponse(status_code=403, content={"error": {"code": "forbidden_origin", "message": "Foreign origin"}})
            if request.headers.get("x-story-architect") != "1":
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

    @app.get("/api/agent/state")
    def agent_state():
        from story_architect.adapters.hermes.gateway import agent_state as _state
        return _state(config)

    @app.post("/api/agent/start")
    def agent_start():
        from story_architect.adapters.hermes.gateway import start_gateway as _start
        res = _start(config)
        app.state.agent_started_by_app = bool(res.get("started_by_app"))
        return res
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

    @app.get("/api/projects/{slug}/events")
    async def project_events(slug: str, request: Request):
        from fastapi.responses import StreamingResponse
        import asyncio
        import sqlite3
        from pathlib import Path

        root = Path(config.root)
        db_path = root / "projects" / slug / ".story" / "story.db"
        # also resolve via services? keep simple

        async def gen():
            last = None
            while True:
                if await request.is_disconnected():
                    break
                try:
                    conn = sqlite3.connect(str(db_path))
                    v = conn.execute("PRAGMA data_version").fetchone()[0]
                    conn.close()
                except Exception:
                    v = None
                if last is None:
                    last = v
                elif v is not None and v != last:
                    last = v
                    yield "event: update\ndata: changed\n\n"
                await asyncio.sleep(1)

        return StreamingResponse(gen(), media_type="text/event-stream")

    app.state.active_replies = {}

    from story_architect.app import services as _svc
    from story_architect.tools.story_resolve import resolve_project
    from story_architect.chat import store as chat_store
    from story_architect.chat.service import ChatService
    from story_architect.app import token as token_mod
    from story_architect.adapters.hermes.chat_backend import HermesChatBackend
    try:
        api_key = token_mod.load_api_key() or ""
        base_url = f"http://127.0.0.1:{config.hermes_api_port}"
        app.state.chat_backend = HermesChatBackend(base_url=base_url, api_key=api_key, model="story-architect")
    except Exception:
        app.state.chat_backend = None

    def _project_path(slug):
        return resolve_project(slug, Path(config.root))

    @app.get("/api/projects/{slug}/conversations")
    def list_convs(slug: str):
        try:
            pp = _project_path(slug)
        except ValueError as e:
            return JSONResponse(status_code=404, content={"error": {"code": "not_found", "message": str(e)}})
        return {"conversations": chat_store.list_conversations(pp)}

    @app.post("/api/projects/{slug}/conversations")
    async def create_conv(slug: str, request: Request):
        title = ""
        try:
            body = await request.json()
            title = (body.get("title") or "").strip()
        except Exception:
            pass
        try:
            pp = _project_path(slug)
        except ValueError as e:
            return JSONResponse(status_code=404, content={"error": {"code": "not_found", "message": str(e)}})
        cid = chat_store.create_conversation(pp, title)
        return {"id": cid}

    @app.get("/api/projects/{slug}/conversations/{cid}")
    def get_conv(slug: str, cid: str):
        try:
            pp = _project_path(slug)
        except ValueError as e:
            return JSONResponse(status_code=404, content={"error": {"code": "not_found", "message": str(e)}})
        conv = chat_store.get_conversation(pp, cid)
        if conv is None:
            return JSONResponse(status_code=404, content={"error": {"code": "not_found", "message": "conversation not found"}})
        return conv

    @app.delete("/api/projects/{slug}/conversations/{cid}")
    def delete_conv(slug: str, cid: str):
        try:
            pp = _project_path(slug)
        except ValueError as e:
            return JSONResponse(status_code=404, content={"error": {"code": "not_found", "message": str(e)}})
        ok = chat_store.delete_conversation(pp, cid)
        return {"deleted": bool(ok)}

    @app.post("/api/projects/{slug}/conversations/{cid}/messages")
    async def send_message(slug: str, cid: str, request: Request):
        from fastapi.responses import StreamingResponse
        import json as _json
        try:
            pp = _project_path(slug)
        except ValueError as e:
            return JSONResponse(status_code=404, content={"error": {"code": "not_found", "message": str(e)}})
        backend = app.state.chat_backend
        if backend is None:
            return JSONResponse(status_code=503, content={"error": {"code": "agent_not_configured", "message": "Chat backend not configured"}})
        try:
            body = await request.json()
        except Exception:
            body = {}
        text = (body.get("text") or "").strip()
        if not text:
            return JSONResponse(status_code=400, content={"error": {"code": "bad_request", "message": "text required"}})
        context = body.get("context") or {}
        # one reply at a time
        if cid in app.state.active_replies:
            return JSONResponse(status_code=409, content={"error": {"code": "reply_in_progress", "message": "A reply is already streaming"}})
        service = ChatService(backend)

        async def gen():
            task = asyncio.current_task()
            app.state.active_replies[cid] = task
            try:
                async for ev in service.send(pp, cid, text, context):
                    etype = type(ev).__name__
                    payload = {}
                    if etype == "TextDelta":
                        payload = {"type": "text", "text": ev.text}
                    elif etype == "ToolStarted":
                        payload = {"type": "tool_started", "name": ev.name}
                    elif etype == "ToolFinished":
                        payload = {"type": "tool_finished", "name": ev.name}
                    elif etype == "Done":
                        payload = {"type": "done", "backend_state": ev.backend_state}
                    elif etype == "Error":
                        payload = {"type": "error", "message": ev.message}
                    else:
                        payload = {"type": etype.lower()}
                    yield f"event: {etype}\ndata: {_json.dumps(payload)}\n\n"
            except asyncio.CancelledError:
                yield "event: cancelled\ndata: {}\n\n"
            finally:
                app.state.active_replies.pop(cid, None)

        import asyncio
        return StreamingResponse(gen(), media_type="text/event-stream")

    @app.post("/api/projects/{slug}/conversations/{cid}/cancel")
    async def cancel_reply(slug: str, cid: str):
        task = app.state.active_replies.get(cid)
        if task is not None:
            task.cancel()
            return {"cancelled": True}
        return {"cancelled": False}
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