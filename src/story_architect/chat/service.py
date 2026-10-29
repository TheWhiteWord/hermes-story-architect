"""Chat service: ties conversations, store, and backend together."""
from __future__ import annotations

import asyncio
from typing import Any, AsyncIterator

from . import store
from .backend import ChatBackend
from .events import Done, Error, TextDelta, ToolFinished, ToolStarted


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
        # title derive
        if title_from_first and conv and not conv.get("title"):
            store.set_title(project_path, conversation_id, user_text[:60])

        # assistant accumulator
        assistant_text = ""
        metadata = {"tools": []}
        msg_id = store.add_message(project_path, conversation_id, "assistant", "", metadata=metadata, status="streaming")
        cancelled = False
        try:
            async for ev in self.backend.send(messages, context or {}, backend_state):
                if isinstance(ev, TextDelta):
                    assistant_text += ev.text
                    store.update_message(project_path, msg_id, assistant_text, status="streaming", metadata=metadata)
                    yield ev
                elif isinstance(ev, ToolStarted):
                    metadata["tools"].append(ev.name)
                    store.update_message(project_path, msg_id, assistant_text, status="streaming", metadata=metadata)
                    yield ev
                elif isinstance(ev, ToolFinished):
                    yield ev
                elif isinstance(ev, Done):
                    store.update_message(project_path, msg_id, assistant_text, status="complete", metadata=metadata)
                    store.set_backend_state(project_path, conversation_id, ev.backend_state)
                    yield ev
                elif isinstance(ev, Error):
                    store.update_message(project_path, msg_id, assistant_text, status="error", metadata=metadata)
                    yield ev
                else:
                    yield ev
        except asyncio.CancelledError:
            cancelled = True
            store.update_message(project_path, msg_id, assistant_text, status="cancelled", metadata=metadata)
            raise
        except Exception as e:
            store.update_message(project_path, msg_id, assistant_text, status="error", metadata=metadata)
            yield Error(message=str(e))
        finally:
            if cancelled:
                pass
