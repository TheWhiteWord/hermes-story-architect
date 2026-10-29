"""Chat event model (plain dataclasses)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TextDelta:
    text: str


@dataclass
class ToolStarted:
    name: str


@dataclass
class ToolFinished:
    name: str


@dataclass
class Done:
    backend_state: Any = None


@dataclass
class Error:
    message: str


ChatEvent = TextDelta | ToolStarted | ToolFinished | Done | Error
"""Union of all chat events yielded by a backend."""