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
            task = asyncio.current_task()
            app.state.active_replies[cid] = task
            from story_architect.app.tool_bus import subscribe, unsubscribe
            bus_q = subscribe()
            out_q = asyncio.Queue()

            async def pump_service():
                try:
                    async for ev in service.send(pp, cid, text, context):
                        await out_q.put(("svc", ev))
                except Exception as e:
                    await out_q.put(("err", e))
                finally:
                    await out_q.put(("done", None))

            async def pump_bus():
                while True:
                    ev = await bus_q.get()
                    await out_q.put(("bus", ev))

            svc_task = asyncio.create_task(pump_service())
            bus_task = asyncio.create_task(pump_bus())
            try:
                while True:
                    kind, payload = await out_q.get()
                    if kind == "svc":
                        ev = payload
                        etype = type(ev).__name__
                        if etype == "TextDelta":
                            pdata = {"type": "text", "text": ev.text}
                        elif etype == "ToolStarted":
                            pdata = {"type": "tool", "id": getattr(ev, "id", None), "name": ev.name, "status": "started", "label": getattr(ev, "label", None)}
                        elif etype == "ToolFinished":
                            pdata = {"type": "tool", "id": getattr(ev, "id", None), "name": ev.name, "status": "finished", "label": getattr(ev, "label", None)}
                        elif etype == "Done":
                            pdata = {"type": "done", "message_id": getattr(ev, "message_id", None)}
                        elif etype == "Error":
                            pdata = {"type": "error", "code": "error", "message": ev.message, "retryable": True}
                        else:
                            pdata = {"type": etype.lower()}
                        yield "event: " + etype + "\ndata: " + _json.dumps(pdata) + "\n\n"
                    elif kind == "bus":
                        ev = payload
                        if ev.get("type") == "draft":
                            yield "event: draft\ndata: " + _json.dumps({"type": "draft", "draft": ev.get("draft")}) + "\n\n"
                        else:
                            status = ev.get("status")
                            if status == "running":
                                status = "started"
                            elif status in ("completed", "finished", "done"):
                                status = "finished"
                            pdata = {"type": "tool", "id": ev.get("id"), "name": ev.get("name"), "status": status, "args": ev.get("args"), "result_preview": ev.get("result_preview"), "duration_ms": ev.get("duration_ms")}
                            yield "event: tool\ndata: " + _json.dumps(pdata) + "\n\n"
                    elif kind == "err":
                        yield "event: error\ndata: " + _json.dumps({"type": "error", "code": "error", "message": str(payload), "retryable": True}) + "\n\n"
                        break
                    elif kind == "done":
                        break
            except asyncio.CancelledError:
                yield "event: cancelled\ndata: {}\n\n"
            finally:
                svc_task.cancel()
                bus_task.cancel()
                unsubscribe(bus_q)
                app.state.active_replies.pop(cid, None)

        import asyncio
        return StreamingResponse(gen(), media_type="text/event-stream")

    @app.post("/api/projects/{slug}/drafts/{draft_id}/approve")
    async def approve_draft(slug: str, draft_id: str, body: dict):
        import json
        from story_architect.tools.story_resolve import resolve_project
        from story_architect.core.drafts import commit, describe_ops, validate_shape, DraftError
        from story_architect.core.db import get_db
        from story_architect.chat import store as chat_store
        from pathlib import Path
        root = Path(config.root)
        try:
            project_path = resolve_project(slug, root)
        except ValueError as e:
            return JSONResponse(status_code=404, content={"error": {"code": "not_found", "message": str(e)}})
        cid = (body or {}).get("conversation_id")
        # fetch draft row for snapshot inputs
        conn = get_db(project_path)
        try:
            row = conn.execute("SELECT ops, summary, created_at, status FROM drafts WHERE id=?", (draft_id,)).fetchone()
        finally:
            conn.close()
        if not row:
            return JSONResponse(status_code=409, content={"error": {"code": "stale_draft", "message": f"No open draft: {draft_id}"}})
        ops = json.loads(row[0]); summary = row[1] or ""; created_at = row[2]
        warnings = validate_shape(ops)
        try:
            result = commit(project_path, draft_id)
        except DraftError as e:
            return JSONResponse(status_code=409, content={"error": {"code": "stale_draft", "message": str(e)}})
        changes = describe_ops(project_path, ops)
        if result.get("success") is False or result.get("failed"):
            status = "failed"
            error = (result.get("failed") or {}).get("error") or result.get("message")
            snapshot = {"id": draft_id, "status": status, "summary": summary, "created_at": created_at, "changes": changes, "warnings": warnings, "error": error}
        else:
            status = "committed"
            snapshot = {"id": draft_id, "status": status, "summary": summary, "created_at": created_at, "changes": changes, "warnings": warnings}
        # update stored snapshot in conversation message
        if cid:
            conv = chat_store.get_conversation(project_path, cid, include_hidden=True)
            if conv:
                for m in conv["messages"]:
                    drafts_list = m.get("drafts") or []
                    for i, d in enumerate(drafts_list):
                        if isinstance(d, dict) and d.get("id") == draft_id:
                            drafts_list[i] = snapshot
                            chat_store.update_message(project_path, m["id"], m["text"], status=m.get("status", "complete"), drafts=drafts_list, update_drafts=True)
                chat_store.add_message(project_path, cid, "assistant", f"Draft {draft_id} was approved by the user and committed", hidden=True)
        return {"status": status, "draft": snapshot}

    @app.post("/api/projects/{slug}/drafts/{draft_id}/reject")
    async def reject_draft(slug: str, draft_id: str, body: dict):
        import json
        from story_architect.tools.story_resolve import resolve_project
        from story_architect.core.drafts import discard, describe_ops, validate_shape, DraftError
        from story_architect.core.db import get_db
        from story_architect.chat import store as chat_store
        from pathlib import Path
        root = Path(config.root)
        try:
            project_path = resolve_project(slug, root)
        except ValueError as e:
            return JSONResponse(status_code=404, content={"error": {"code": "not_found", "message": str(e)}})
        cid = (body or {}).get("conversation_id")
        conn = get_db(project_path)
        try:
            row = conn.execute("SELECT ops, summary, created_at FROM drafts WHERE id=?", (draft_id,)).fetchone()
        finally:
            conn.close()
        if not row:
            return JSONResponse(status_code=409, content={"error": {"code": "stale_draft", "message": f"No open draft: {draft_id}"}})
        ops = json.loads(row[0]); summary = row[1] or ""; created_at = row[2]
        warnings = validate_shape(ops)
        try:
            discard(project_path, draft_id)
        except DraftError as e:
            return JSONResponse(status_code=409, content={"error": {"code": "stale_draft", "message": str(e)}})
        changes = describe_ops(project_path, ops)
        snapshot = {"id": draft_id, "status": "discarded", "summary": summary, "created_at": created_at, "changes": changes, "warnings": warnings}
        if cid:
            conv = chat_store.get_conversation(project_path, cid, include_hidden=True)
            if conv:
                for m in conv["messages"]:
                    drafts_list = m.get("drafts") or []
                    for i, d in enumerate(drafts_list):
                        if isinstance(d, dict) and d.get("id") == draft_id:
                            drafts_list[i] = snapshot
                            chat_store.update_message(project_path, m["id"], m["text"], status=m.get("status", "complete"), drafts=drafts_list, update_drafts=True)
            chat_store.add_message(project_path, cid, "assistant", f"Draft {draft_id} was rejected by the user", hidden=True)
        return {"status": "discarded", "draft": snapshot}

    @app.post("/api/projects/{slug}/conversations/{cid}/retry")
    async def retry_reply(slug: str, cid: str):
        from fastapi.responses import StreamingResponse
        import asyncio
        from story_architect.tools.story_resolve import resolve_project
        from pathlib import Path
        root = Path(config.root)
        try:
            pp = resolve_project(slug, root)
        except ValueError as e:
            return JSONResponse(status_code=404, content={"error": {"code": "not_found", "message": str(e)}})
        if cid in (app.state.active_replies or {}):
            return JSONResponse(status_code=409, content={"error": {"code": "in_progress", "message": "reply in progress"}})
        from story_architect.chat import store as chat_store
        # 400 if no user message
        # check by attempting prepare? Instead peek
        conv = chat_store.get_conversation(pp, cid)
        has_user = any(m.get("role") == "user" for m in (conv["messages"] if conv else []))
        if not has_user:
            return JSONResponse(status_code=400, content={"error": {"code": "no_user_message", "message": "no user message"}})
        service = app.state.chat_service
        async def gen():
            task = asyncio.current_task()
            app.state.active_replies[cid] = task
            try:
                async for ev in service.retry(pp, cid, {}):
                    yield "event: " + type(ev).__name__ + "\ndata: {}\n\n".format("")
            finally:
                app.state.active_replies.pop(cid, None)
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