"""In-memory fake chat backend for tests."""
from __future__ import annotations

from typing import Any, AsyncIterator

from .events import Done, TextDelta, ToolStarted


class FakeBackend:
    def __init__(self, replies=None, tool_name=None, error=None, cancel_after=None):
        self.replies = replies or ["hello"]
        self.tool_name = tool_name
        self.error = error
        self.cancel_after = cancel_after
        self.calls = []

    async def send(self, messages, instructions, backend_state) -> AsyncIterator[Any]:
        self.calls.append((messages, instructions, backend_state))
        if self.tool_name:
            yield ToolStarted(name=self.tool_name)
        for r in self.replies:
            yield TextDelta(text=r)
        if self.error:
            from .events import Error
            yield Error(message=self.error)
            return
        yield Done(backend_state={"n": (backend_state or {}).get("n", 0) + 1 if isinstance(backend_state, dict) else 1})
