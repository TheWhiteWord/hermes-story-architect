"""Hermes chat backend (adapter over the profile's API server)."""
from __future__ import annotations

import json
import re
from typing import Any, AsyncIterator

try:
    import httpx
except ModuleNotFoundError:
    import httpx2 as httpx

from story_architect.chat.backend import ChatBackend  # noqa: F401
from story_architect.chat.events import Done, DraftEvent, Error, TextDelta, ToolFinished, ToolStarted


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
        instructions: str,
        backend_state: Any,
    ) -> AsyncIterator[Any]:
        system_text = instructions or "You are the Story Architect assistant."
        payload_messages = [{"role": "system", "content": system_text}] + [
            {"role": m.get("role", "user"), "content": m.get("content", m.get("text", ""))}
            for m in (messages or [])
        ]
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": payload_messages,
            "stream": True,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "text/event-stream",
        }
        url = f"{self.base_url}/v1/chat/completions"

        response_id: Any = backend_state
        current_event: str | None = None
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
                            current_event = line[len("event:"):].strip()
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
                        if isinstance(obj, dict):
                            evt = obj.get("event") or obj.get("type")
                            # draft event
                            if evt == "draft" or current_event == "draft":
                                d = obj.get("draft") if isinstance(obj.get("draft"), dict) else (obj.get("data") if isinstance(obj.get("data"), dict) else obj)
                                yield DraftEvent(draft=d)
                            is_tool_progress = evt == "hermes.tool.progress" or current_event == "hermes.tool.progress"
                            if is_tool_progress:
                                d = obj.get("data") if isinstance(obj.get("data"), dict) else obj
                                tname = d.get("tool") or d.get("name")
                                status = d.get("status")
                                if tname and not re.match(r"^mcp_+story_+", str(tname)):
                                    tid = d.get("toolCallId") or d.get("id")
                                    label = d.get("label")
                                    if status in ("completed", "finished", "done"):
                                        yield ToolFinished(name=tname, id=tid, label=label, args=d.get("args"), result_preview=d.get("result_preview"), duration_ms=d.get("duration_ms"))
                                    elif status in ("failed", "error"):
                                        yield ToolFinished(name=tname, id=tid, label=label, status="failed", args=d.get("args"), result_preview=d.get("result_preview"), duration_ms=d.get("duration_ms"))
                                    else:
                                        yield ToolStarted(name=tname, id=tid, label=label, args=d.get("args"))
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