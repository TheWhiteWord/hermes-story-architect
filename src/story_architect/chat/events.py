"""Chat event model (plain dataclasses)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class TextDelta:
    text: str


@dataclass
class ToolStarted:
    name: str
    id: Any = None
    label: str | None = None
    args: Any = None


@dataclass
class ToolFinished:
    name: str
    id: Any = None
    label: str | None = None
    status: str = "finished"
    args: Any = None
    result_preview: str | None = None
    duration_ms: int | None = None


@dataclass
class DraftEvent:
    draft: Any = None


@dataclass
class Done:
    backend_state: Any = None
    message_id: Any = None


@dataclass
class Error:
    message: str


ChatEvent = TextDelta | ToolStarted | ToolFinished | DraftEvent | Done | Error
"""Union of all chat events yielded by a backend."""