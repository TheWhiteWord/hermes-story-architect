"""Hermes chat backend (adapter over the profile's API server)."""
from __future__ import annotations

import json
from typing import Any, AsyncIterator

import httpx

from story_architect.chat.backend import ChatBackend  # noqa: F401
from story_architect.chat.events import Done, Error, TextDelta, ToolStarted


class HermesChatBackend:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str = "story-architect",
        timeout: float = 120.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    async def send(
        self,
        messages: list[dict],
        context: dict,
        backend_state: Any,
    ) -> AsyncIterator[Any]:
        # Build system instructions from context.
        slug = (context or {}).get("project_slug") or (context or {}).get("slug")
        name = (context or {}).get("project_name") or (context or {}).get("display_name")
        parts = ["You are the Story Architect assistant."]
        if slug:
            parts.append(f"Current project slug: {slug}.")
        if name:
            parts.append(f"Current project name: {name}.")
        system_text = " ".join(parts)

        payload_messages = [{"role": "system", "content": system_text}] + list(messages or [])
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": payload_messages,
            "stream": True,
        }
        if backend_state is not None:
            payload["previous_response_id"] = backend_state

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "text/event-stream",
        }
        url = f"{self.base_url}/v1/chat/completions"

        response_id: Any = backend_state
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream("POST", url, json=payload, headers=headers) as resp:
                    if resp.status_code >= 400:
                        body = await resp.aread()
                        yield Error(message=f"HTTP {resp.status_code}: {body.decode('utf-8', 'replace')[:200]}")
                        return
                    async for line in resp.aiter_lines():
                        line = line.strip()
                        if not line:
                            continue
                        if line.startswith("event:"):
                            # event type; data line follows
                            continue
                        if not line.startswith("data:"):
                            continue
                        data_str = line[len("data:"):].strip()
                        if data_str == "[DONE]":
                            break
                        try:
                            obj = json.loads(data_str)
                        except json.JSONDecodeError:
                            continue
                        if isinstance(obj, dict) and obj.get("id"):
                            response_id = obj["id"]
                        # tool progress may be nested
                        choices = obj.get("choices") or []
                        for ch in choices:
                            delta = (ch.get("delta") or {})
                            content = delta.get("content")
                            if content:
                                yield TextDelta(text=content)
                            # hermes tool progress sometimes in delta
                            tp = delta.get("hermes") or {}
                            if isinstance(tp, dict):
                                tname = tp.get("tool") or tp.get("name")
                                if tname:
                                    yield ToolStarted(name=tname)
                        # top-level hermes events
                        if isinstance(obj, dict):
                            evt = obj.get("event") or obj.get("type")
                            if evt == "hermes.tool.progress":
                                tname = None
                                d = obj.get("data") or {}
                                if isinstance(d, dict):
                                    tname = d.get("tool") or d.get("name")
                                if tname:
                                    yield ToolStarted(name=tname)
                            # sometimes tool name at obj["tool"]
                            if "tool" in obj and isinstance(obj["tool"], str) and evt and "tool" in str(evt):
                                yield ToolStarted(name=obj["tool"])
        except httpx.HTTPError as e:
            yield Error(message=f"unreachable: {e}")
            return
        except Exception as e:  # noqa: BLE001
            yield Error(message=str(e))
            return
        yield Done(backend_state=response_id)