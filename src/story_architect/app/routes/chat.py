from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse
import asyncio
from pathlib import Path


def make_router(config, app):
    router = APIRouter()

    def _resolve_project(slug) -> tuple:  # type: ignore
        from story_architect.tools.story_resolve import resolve_project
        root = Path(config.root)
        try:
            return resolve_project(slug, root), None
        except ValueError as e:
            return None, str(e)
        except Exception as e:
            return None, str(e)

    async def stream_reply(slug, cid, user_text, context, retry=False):
        from story_architect.app import tool_bus
        pp, err = _resolve_project(slug)
        if pp is None:
            yield ("error", {"type": "error", "code": "not_found", "message": err, "retryable": False})
            return
        from story_architect.app.token import load_api_key
        api_key = load_api_key()
        if not api_key:
            yield ("error", {"type": "error", "code": "agent_not_configured", "message": "no api key", "retryable": False})
            return
        active = getattr(app.state, "active_replies", None)
        if active and len(active) > 0:
            yield ("error", {"type": "error", "code": "reply_in_progress", "message": "reply in progress", "retryable": True})
            return

        queue: asyncio.Queue = asyncio.Queue()

        async def producer():
            bus_q = tool_bus.subscribe()
            async def _bus_fwd():
                while True:
                    ev = await bus_q.get()
                    await queue.put(("bus", ev))
            fwd_task = asyncio.ensure_future(_bus_fwd())
            service = app.state.chat_service
            try:
                async for ev in (service.retry(pp, cid, context or {}) if retry else service.send(pp, cid, user_text, context or {})):
                    from story_architect.chat.events import TextDelta, ToolStarted, ToolFinished, Done, Error
                    if isinstance(ev, TextDelta):
                        await queue.put(("sse", ("text", {"type": "text", "text": ev.text})))
                    elif isinstance(ev, ToolStarted):
                        await queue.put(("sse", ("tool", {"type": "tool", "id": ev.id, "name": ev.name, "status": "started", "label": ev.label})))
                    elif isinstance(ev, ToolFinished):
                        st = ev.status if ev.status in ("finished", "failed") else "finished"
                        await queue.put(("sse", ("tool", {"type": "tool", "id": ev.id, "name": ev.name, "status": st, "label": ev.label})))
                    elif isinstance(ev, Done):
                        await queue.put(("sse", ("done", {"type": "done", "message_id": ev.message_id})))
                    elif isinstance(ev, Error):
                        await queue.put(("sse", ("error", {"type": "error", "code": "agent_error", "message": ev.message, "retryable": False})))
            except asyncio.CancelledError:
                await queue.put(("sse", ("cancelled", {"type": "cancelled"})))
                raise
            except Exception as e:
                await queue.put(("sse", ("error", {"type": "error", "code": "agent_error", "message": str(e), "retryable": False})))
            finally:
                tool_bus.unsubscribe(bus_q)
                fwd_task.cancel()

        task = asyncio.ensure_future(producer())
        app.state.active_replies[cid] = task
        try:
            while True:
                if task.done() and queue.empty():
                    break
                try:
                    kind, payload = await asyncio.wait_for(queue.get(), timeout=0.1)
                except asyncio.TimeoutError:
                    continue
                if kind == "bus":
                    ev = payload
                    t = ev.get("type") if isinstance(ev, dict) else None
                    if t in ("started", "finished", "failed"):
                        await queue.put(("sse", ("tool", {"type": "tool", "id": ev.get("id"), "name": ev.get("name"), "status": "started" if t == "started" else ("failed" if t == "failed" else "finished"), "args": ev.get("args"), "result_preview": ev.get("result_preview"), "duration_ms": ev.get("duration_ms")})))
                    if t == "draft":
                        await queue.put(("sse", ("draft", {"type": "draft", "draft": ev.get("draft")})))
                    continue
                etype, data = payload
                yield (etype, data)
                if etype in ("done", "error", "cancelled"):
                    break
        finally:
            app.state.active_replies.pop(cid, None)
            if not task.done():
                task.cancel()

    # messages route
    @router.post("/api/projects/{slug}/conversations")
    async def create_conv(slug: str, request: Request):
        pp, err = _resolve_project(slug)
        if pp is None:
            return JSONResponse(status_code=404, content={"error": {"code": "not_found", "message": err}})
        from story_architect.chat import store as chat_store
        body = await request.json() if request.headers.get("content-type", "").startswith("application/json") else {}
        cid = chat_store.create_conversation(pp, body.get("title", ""))
        return {"id": cid}

    @router.get("/api/projects/{slug}/conversations")
    async def list_conv(slug: str):
        pp, err = _resolve_project(slug)
        if pp is None:
            return JSONResponse(status_code=404, content={"error": {"code": "not_found", "message": err}})
        from story_architect.chat import store as chat_store
        convs = chat_store.list_conversations(pp)
        return {"conversations": [{"id": c["id"], "title": c.get("title", ""), "updated_at": c.get("updated_at")} for c in convs]}

    @router.get("/api/projects/{slug}/conversations/{cid}")
    async def get_conv(slug: str, cid: str):
        pp, err = _resolve_project(slug)
        if pp is None:
            return JSONResponse(status_code=404, content={"error": {"code": "not_found", "message": err}})
        from story_architect.chat import store as chat_store
        conv = chat_store.get_conversation(pp, cid)
        if not conv:
            return JSONResponse(status_code=404, content={"error": {"code": "not_found", "message": "conversation not found"}})
        msgs = []
        for m in conv.get("messages", []):
            if m.get("hidden"):
                continue
            msgs.append({"id": m["id"], "role": m["role"], "text": m.get("text", ""), "status": m.get("status", "complete"), "created_at": m.get("created_at"), "tools": m.get("tools"), "drafts": m.get("drafts"), "attachments": m.get("attachments"), "error": m.get("error")})
        return {"id": conv["id"], "title": conv.get("title", ""), "messages": msgs}

    @router.delete("/api/projects/{slug}/conversations/{cid}")
    async def del_conv(slug: str, cid: str):
        pp, err = _resolve_project(slug)
        if pp is None:
            return JSONResponse(status_code=404, content={"error": {"code": "not_found", "message": err}})
        from story_architect.chat import store as chat_store
        chat_store.delete_conversation(pp, cid)
        return {"deleted": True}

    async def _messages_handler(slug: str, request: Request, cid_path: str | None = None):
        # preflight
        try:
            body = await request.json()
        except Exception:
            body = {}
        text = (body.get("text") or "").strip()
        context = body.get("context") or {}
        # project resolve
        pp, err = _resolve_project(slug)
        if pp is None:
            return JSONResponse(status_code=404, content={"error": {"code": "not_found", "message": err}})
        if not text:
            return JSONResponse(status_code=400, content={"error": {"code": "empty_text", "message": "empty text"}})
        from story_architect.app.token import load_api_key
        if not load_api_key():
            return JSONResponse(status_code=503, content={"error": {"code": "agent_not_configured", "message": "no api key"}})
        active = getattr(app.state, "active_replies", None)
        if active and len(active) > 0:
            return JSONResponse(status_code=409, content={"error": {"code": "reply_in_progress", "message": "reply in progress"}})
        cid = cid_path or body.get("conversation_id")
        if not cid:
            from story_architect.chat import store as chat_store
            cid = chat_store.create_conversation(pp, text[:60])
        async def gen():
            async for etype, data in stream_reply(slug, cid, text, context, retry=False):
                yield f"event: {etype}\ndata: {__import__('json').dumps(data)}\n\n"
        return StreamingResponse(gen(), media_type="text/event-stream")

    @router.post("/api/projects/{slug}/messages")
    async def messages_route(slug: str, request: Request):
        return await _messages_handler(slug, request)

    @router.post("/api/projects/{slug}/conversations/{cid}/messages")
    async def conv_messages_route(slug: str, cid: str, request: Request):
        return await _messages_handler(slug, request, cid_path=cid)
    @router.post("/api/projects/{slug}/conversations/{cid}/retry")
    async def retry_route(slug: str, cid: str, request: Request):
        pp, err = _resolve_project(slug)
        if pp is None:
            return JSONResponse(status_code=404, content={"error": {"code": "not_found", "message": err}})
        from story_architect.chat import store as chat_store
        conv = chat_store.get_conversation(pp, cid)
        has_user = any(m.get("role") == "user" for m in (conv["messages"] if conv else []))
        if not has_user:
            return JSONResponse(status_code=400, content={"error": {"code": "no_user_message", "message": "no user message"}})
        from story_architect.app.token import load_api_key
        if not load_api_key():
            return JSONResponse(status_code=503, content={"error": {"code": "agent_not_configured", "message": "no api key"}})
        active = getattr(app.state, "active_replies", None)
        if active and len(active) > 0:
            return JSONResponse(status_code=409, content={"error": {"code": "reply_in_progress", "message": "reply in progress"}})
        try:
            body = await request.json()
        except Exception:
            body = {}
        context = body.get("context") or {}
        async def gen():
            async for etype, data in stream_reply(slug, cid, "", context, retry=True):
                yield f"event: {etype}\ndata: {__import__('json').dumps(data)}\n\n"
        return StreamingResponse(gen(), media_type="text/event-stream")

    @router.post("/api/projects/{slug}/conversations/{cid}/cancel")
    async def cancel_reply(slug: str, cid: str):
        task = (getattr(app.state, "active_replies", {}) or {}).get(cid)
        if task is not None:
            task.cancel()
            return {"cancelled": True}
        return {"cancelled": False}

    return router