"""ChatBackend protocol (harness-agnostic)."""
from __future__ import annotations

from typing import Any, AsyncIterator, Protocol, runtime_checkable

from .events import ChatEvent


@runtime_checkable
class ChatBackend(Protocol):
    def send(
        self,
        messages: list[dict],
        instructions: str,
        backend_state: Any,
    ) -> AsyncIterator[ChatEvent]:
        """Return an async iterator of chat events for a user turn."""
        ...
