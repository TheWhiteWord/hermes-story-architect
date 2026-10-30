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


@dataclass
class ToolFinished:
    name: str
    id: Any = None
    label: str | None = None
    status: str = "finished"


@dataclass
class Done:
    backend_state: Any = None


@dataclass
class Error:
    message: str


ChatEvent = TextDelta | ToolStarted | ToolFinished | Done | Error
"""Union of all chat events yielded by a backend."""