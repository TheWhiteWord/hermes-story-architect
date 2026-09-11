"""Hermes Story Architect — plugin entry point."""
import json
import sys
from pathlib import Path

# Ensure repo root is on sys.path so core/ and tools/ are importable
_REPO_ROOT = Path(__file__).parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from core.config import load_plugin_config

_SKILL_DIR = _REPO_ROOT / "skills"


def _requirements_met() -> bool:
    """Check if vault_path is configured."""
    config = load_plugin_config()
    return bool(config.get("vault_path"))


def register(ctx) -> None:
    """Register all Story Architect tools and skills."""
    from .tools import story_load
    from .tools import story_retrieve
    from .tools import story_index
    from .tools import story_search
    from .tools import story_edit
    from .tools import story_create

    ctx.register_tool(
        name="story_load",
        toolset="story_architect",
        schema=story_load.SCHEMA,
        handler=story_load.handler,
        check_fn=_requirements_met,
        emoji="📖",
    )
    ctx.register_tool(
        name="story_retrieve",
        toolset="story_architect",
        schema=story_retrieve.SCHEMA,
        handler=story_retrieve.handler,
        check_fn=_requirements_met,
        emoji="🔍",
    )
    ctx.register_tool(
        name="story_index",
        toolset="story_architect",
        schema=story_index.SCHEMA,
        handler=story_index.handler,
        check_fn=_requirements_met,
        emoji="📊",
    )
    ctx.register_tool(
        name="story_search",
        toolset="story_architect",
        schema=story_search.SCHEMA,
        handler=story_search.handler,
        check_fn=_requirements_met,
        emoji="🔎",
    )
    ctx.register_tool(
        name="story_edit",
        toolset="story_architect",
        schema=story_edit.SCHEMA,
        handler=story_edit.handler,
        check_fn=_requirements_met,
        emoji="✏️",
    )
    ctx.register_tool(
        name="story_create",
        toolset="story_architect",
        schema=story_create.SCHEMA,
        handler=story_create.handler,
        check_fn=_requirements_met,
        emoji="➕",
    )

    # Register skills
    for child in _SKILL_DIR.iterdir():
        skill_md = child / "SKILL.md"
        if child.is_dir() and skill_md.exists():
            ctx.register_skill(child.name, skill_md)

    from .tools import story_dashboard

    ctx.register_tool(
        name="story_dashboard",
        toolset="story_architect",
        schema=story_dashboard.SCHEMA,
        handler=story_dashboard.handler,
        check_fn=_requirements_met,
        emoji="📊",
    )

    # Auto-open preview pane when story_dashboard succeeds
    def auto_open_dashboard(*, tool_name, result, **kwargs):
        if tool_name != "story_dashboard":
            return
        try:
            data = json.loads(result)
            url = data.get("dashboard_url")
            if url:
                ctx.dispatch_tool("desktop_preview", {"action": "open", "url": url})
        except Exception:
            pass

    ctx.register_hook("post_tool_call", auto_open_dashboard)
