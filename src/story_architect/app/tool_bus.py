"""Small in-process bus for MCP tool-call events.

MCP calls carry no conversation id, so subscribers (one active reply at a
time) receive every event; calls made while no subscriber exists are dropped.
"""
from __future__ import annotations

import asyncio

_subscribers: set[asyncio.Queue] = set()


def subscribe() -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue()
    _subscribers.add(q)
    return q


def unsubscribe(q: asyncio.Queue) -> None:
    _subscribers.discard(q)


async def publish(event: dict) -> None:
    for q in list(_subscribers):
        await q.put(event)
