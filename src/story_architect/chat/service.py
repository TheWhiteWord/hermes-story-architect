"""Chat service: ties conversations, store, and backend together."""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, AsyncIterator

from . import store
from .backend import ChatBackend
from .context import build_bootstrap
from .events import Done, DraftEvent, Error, TextDelta, ToolFinished, ToolStarted


class ChatService:
    def __init__(self, backend: ChatBackend):
        self.backend = backend

    def create_conversation(self, project_path, title=""):
        return store.create_conversation(project_path, title)

    def list_conversations(self, project_path):
        return store.list_conversations(project_path)

    def get_conversation(self, project_path, cid):
        return store.get_conversation(project_path, cid)

    def delete_conversation(self, project_path, cid):
        return store.delete_conversation(project_path, cid)

    async def send(
        self,
        project_path,
        conversation_id: str,
        user_text: str,
        context: dict,
        title_from_first: bool = True,
    ) -> AsyncIterator[Any]:
        # persist user message
        store.add_message(project_path, conversation_id, "user", user_text)
        conv = store.get_conversation(project_path, conversation_id)
        backend_state = conv["backend_state"] if conv else None
        # build message history
        messages = [{"role": m["role"], "text": m["text"]} for m in (conv["messages"] if conv else [])]
        # build bootstrap instructions (never persisted)
        from story_architect.core.drafts import _project_name
        slug = Path(project_path).name if not isinstance(project_path, str) else str(project_path).rstrip("/").split("/")[-1]
        name = _project_name(Path(project_path))
        instructions = build_bootstrap(slug, name, (context or {}).get("attachments") or [])
        # title derive
        if title_from_first and conv and not conv.get("title"):
            store.set_title(project_path, conversation_id, user_text[:60])

        # assistant accumulator
        assistant_text = ""
        tools_by_id = {}
        drafts_by_id = {}
        metadata = {}
        msg_id = store.add_message(project_path, conversation_id, "assistant", "", metadata=metadata, status="streaming")
        cancelled = False
        try:
            async for ev in self.backend.send(messages, instructions, backend_state):
                if isinstance(ev, TextDelta):
                    assistant_text += ev.text
                    store.update_message(project_path, msg_id, assistant_text, status="streaming", metadata=metadata, tools=list(tools_by_id.values()), drafts=list(drafts_by_id.values()), update_tools=True, update_drafts=True)
                    yield ev
                elif isinstance(ev, ToolStarted):
                    tid = ev.id if ev.id is not None else ev.name
                    entry = tools_by_id.get(tid, {})
                    entry.update({k: v for k, v in {"id": tid, "name": ev.name, "label": ev.label, "args": ev.args, "status": "started"}.items() if v is not None})
                    tools_by_id[tid] = entry
                    store.update_message(project_path, msg_id, assistant_text, status="streaming", metadata=metadata, tools=list(tools_by_id.values()), drafts=list(drafts_by_id.values()), update_tools=True, update_drafts=True)
                    yield ev
                elif isinstance(ev, ToolFinished):
                    tid = ev.id if ev.id is not None else ev.name
                    entry = tools_by_id.get(tid, {"id": tid, "name": ev.name})
                    for k, v in {"name": ev.name, "label": ev.label, "args": ev.args, "result_preview": ev.result_preview, "duration_ms": ev.duration_ms, "status": ev.status}.items():
                        if v is not None:
                            entry[k] = v
                    tools_by_id[tid] = entry
                    store.update_message(project_path, msg_id, assistant_text, status="streaming", metadata=metadata, tools=list(tools_by_id.values()), drafts=list(drafts_by_id.values()), update_tools=True, update_drafts=True)
                    yield ev
                elif isinstance(ev, DraftEvent):
                    d = ev.draft or {}
                    did = d.get("id") if isinstance(d, dict) else None
                    if did is None:
                        did = len(drafts_by_id)
                    drafts_by_id[did] = d
                    store.update_message(project_path, msg_id, assistant_text, status="streaming", metadata=metadata, tools=list(tools_by_id.values()), drafts=list(drafts_by_id.values()), update_tools=True, update_drafts=True)
                    yield ev
                elif isinstance(ev, Done):
                    store.update_message(project_path, msg_id, assistant_text, status="complete", metadata=metadata, tools=list(tools_by_id.values()), drafts=list(drafts_by_id.values()), update_tools=True, update_drafts=True)
                    store.set_backend_state(project_path, conversation_id, ev.backend_state)
                    from .events import Done as _Done
                    yield _Done(backend_state=ev.backend_state, message_id=msg_id)
                elif isinstance(ev, Error):
                    store.update_message(project_path, msg_id, assistant_text, status="error", metadata=metadata, tools=list(tools_by_id.values()), drafts=list(drafts_by_id.values()), update_tools=True, update_drafts=True)
                    yield ev
                else:
                    yield ev
        except asyncio.CancelledError:
            cancelled = True
            store.update_message(project_path, msg_id, assistant_text, status="cancelled", metadata=metadata, tools=list(tools_by_id.values()), drafts=list(drafts_by_id.values()), update_tools=True, update_drafts=True)
            raise
        except Exception as e:
            store.update_message(project_path, msg_id, assistant_text, status="error", metadata=metadata, tools=list(tools_by_id.values()), drafts=list(drafts_by_id.values()), update_tools=True, update_drafts=True)
            yield Error(message=str(e))
    async def retry(
        self,
        project_path,
        conversation_id: str,
        context: dict | None = None,
    ) -> AsyncIterator[Any]:
        user_text = store.prepare_retry(project_path, conversation_id)
        if not user_text:
            raise ValueError("no user message")
        conv = store.get_conversation(project_path, conversation_id)
        backend_state = conv["backend_state"] if conv else None
        messages = [{"role": m["role"], "text": m["text"]} for m in (conv["messages"] if conv else [])]
        from story_architect.core.drafts import _project_name
        slug = Path(project_path).name if not isinstance(project_path, str) else str(project_path).rstrip("/").split("/")[-1]
        name = _project_name(Path(project_path))
        instructions = build_bootstrap(slug, name, (context or {}).get("attachments") or [])
        assistant_text = ""
        tools_by_id = {}
        drafts_by_id = {}
        metadata = {}
        msg_id = store.add_message(project_path, conversation_id, "assistant", "", metadata=metadata, status="streaming")
        try:
            async for ev in self.backend.send(messages, instructions, backend_state):
                if isinstance(ev, TextDelta):
                    assistant_text += ev.text
                    store.update_message(project_path, msg_id, assistant_text, status="streaming", metadata=metadata, tools=list(tools_by_id.values()), drafts=list(drafts_by_id.values()), update_tools=True, update_drafts=True)
                    yield ev
                elif isinstance(ev, ToolStarted):
                    tid = ev.id if ev.id is not None else ev.name
                    entry = tools_by_id.get(tid, {})
                    entry.update({k: v for k, v in {"id": tid, "name": ev.name, "label": ev.label, "args": ev.args, "status": "started"}.items() if v is not None})
                    tools_by_id[tid] = entry
                    store.update_message(project_path, msg_id, assistant_text, status="streaming", metadata=metadata, tools=list(tools_by_id.values()), drafts=list(drafts_by_id.values()), update_tools=True, update_drafts=True)
                    yield ev
                elif isinstance(ev, ToolFinished):
                    tid = ev.id if ev.id is not None else ev.name
                    entry = tools_by_id.get(tid, {"id": tid, "name": ev.name})
                    for k, v in {"name": ev.name, "label": ev.label, "args": ev.args, "result_preview": ev.result_preview, "duration_ms": ev.duration_ms, "status": ev.status}.items():
                        if v is not None:
                            entry[k] = v
                    tools_by_id[tid] = entry
                    store.update_message(project_path, msg_id, assistant_text, status="streaming", metadata=metadata, tools=list(tools_by_id.values()), drafts=list(drafts_by_id.values()), update_tools=True, update_drafts=True)
                    yield ev
                elif isinstance(ev, DraftEvent):
                    d = ev.draft or {}
                    did = d.get("id") if isinstance(d, dict) else None
                    if did is None:
                        did = len(drafts_by_id)
                    drafts_by_id[did] = d
                    store.update_message(project_path, msg_id, assistant_text, status="streaming", metadata=metadata, tools=list(tools_by_id.values()), drafts=list(drafts_by_id.values()), update_tools=True, update_drafts=True)
                    yield ev
                elif isinstance(ev, Done):
                    store.update_message(project_path, msg_id, assistant_text, status="complete", metadata=metadata, tools=list(tools_by_id.values()), drafts=list(drafts_by_id.values()), update_tools=True, update_drafts=True)
                    store.set_backend_state(project_path, conversation_id, ev.backend_state)
                    from .events import Done as _Done
                    yield _Done(backend_state=ev.backend_state, message_id=msg_id)
                elif isinstance(ev, Error):
                    store.update_message(project_path, msg_id, assistant_text, status="error", metadata=metadata, tools=list(tools_by_id.values()), drafts=list(drafts_by_id.values()), update_tools=True, update_drafts=True)
                    yield ev
                else:
                    yield ev
        except asyncio.CancelledError:
            store.update_message(project_path, msg_id, assistant_text, status="cancelled", metadata=metadata, tools=list(tools_by_id.values()), drafts=list(drafts_by_id.values()), update_tools=True, update_drafts=True)
            raise
        except Exception as e:
            store.update_message(project_path, msg_id, assistant_text, status="error", metadata=metadata, tools=list(tools_by_id.values()), drafts=list(drafts_by_id.values()), update_tools=True, update_drafts=True)
            yield Error(message=str(e))
