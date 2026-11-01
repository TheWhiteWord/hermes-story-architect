from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pathlib import Path


def make_router(config, app):
    router = APIRouter()

    @router.post("/api/projects/{slug}/drafts/{draft_id}/approve")
    async def approve_draft(slug: str, draft_id: str, body: dict):
        import json
        from story_architect.tools.story_resolve import resolve_project
        from story_architect.core.drafts import commit, describe_ops, validate_shape, DraftError
        from story_architect.core.db import get_db
        from story_architect.chat import store as chat_store
        root = Path(config.root)
        try:
            project_path = resolve_project(slug, root)
        except ValueError as e:
            return JSONResponse(status_code=404, content={"error": {"code": "not_found", "message": str(e)}})
        cid = (body or {}).get("conversation_id")
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

    @router.post("/api/projects/{slug}/drafts/{draft_id}/reject")
    async def reject_draft(slug: str, draft_id: str, body: dict):
        import json
        from story_architect.tools.story_resolve import resolve_project
        from story_architect.core.drafts import discard, describe_ops, validate_shape, DraftError
        from story_architect.core.db import get_db
        from story_architect.chat import store as chat_store
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

    return router
