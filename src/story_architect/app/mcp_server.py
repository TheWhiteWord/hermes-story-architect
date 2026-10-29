"""MCP Streamable HTTP endpoint mounted into the app factory."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from mcp import types
from mcp.server.lowlevel import Server
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager

import story_architect.tools as _tools_pkg
from story_architect.app.config import Config

log = logging.getLogger(__name__)

TOOL_MODULES = [
    "story_admin",
    "story_backup",
    "story_dashboard_link",
    "story_describe",
    "story_draft",
    "story_export",
    "story_import",
    "story_load",
    "story_memory",
    "story_retrieve",
    "story_search",
]


import importlib

def _mod(name: str):
    return importlib.import_module(f"story_architect.tools.{name}")


def mcp_tool_name(module_name: str) -> str:
    return module_name[len("story_"):] if module_name.startswith("story_") else module_name


def build_registry() -> list[tuple[str, Any, Any]]:
    out = []
    for mn in TOOL_MODULES:
        m = _mod(mn)
        out.append((mcp_tool_name(mn), m.SCHEMA, m.handler))
    return out


def create_mcp_server(config: Config) -> Server:
    reg = {name: (schema, handler) for name, schema, handler in build_registry()}

    async def on_list_tools(ctx, params):
        tools = [types.Tool(name=n, description=s.get("description", ""), input_schema=s) for n, (s, _) in reg.items()]
        return types.ListToolsResult(tools=tools)

    async def on_call_tool(ctx, params):
        name = params.name
        if name not in reg:
            raise ValueError(f"Unknown tool: {name}")
        schema, handler = reg[name]
        args = params.arguments or {}
        try:
            result = await asyncio.to_thread(handler, args, root_path=config.root)
        except Exception as e:
            log.exception("tool %s raised", name)
            raise RuntimeError(f"{name}: {e}") from e
        return types.CallToolResult(content=[types.TextContent(type="text", text=result)])

    server = Server(
        "story",
        on_list_tools=on_list_tools,
        on_call_tool=on_call_tool,
    )
    return server


__all__ = ["create_mcp_server", "StreamableHTTPSessionManager", "build_registry", "mcp_tool_name"]