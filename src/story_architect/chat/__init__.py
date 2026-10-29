"""Chat package (harness-agnostic)."""
from .backend import ChatBackend
from .events import ChatEvent, Done, Error, TextDelta, ToolFinished, ToolStarted
from .service import ChatService
from .store import connect, create_conversation, list_conversations, get_conversation, delete_conversation

__all__ = [
    "ChatBackend", "ChatEvent", "Done", "Error", "TextDelta",
    "ToolFinished", "ToolStarted", "ChatService",
]
