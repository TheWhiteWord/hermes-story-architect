"""Hermes Story Architect — plugin entry point."""
from pathlib import Path
from hermes_constants import get_hermes_home


def load_plugin_config() -> dict:
    """Load plugin config from Hermes config.yaml."""
    import yaml
    path = get_hermes_home() / "config.yaml"
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}
    block = data.get("story_architect")
    return block if isinstance(block, dict) else {}


def _requirements_met() -> bool:
    """Check if vault_path is configured."""
    config = load_plugin_config()
    return bool(config.get("vault_path"))


def register(ctx) -> None:
    """Register all Story Architect tools."""
    from .tools.story_load import story_load
    from .tools.story_retrieve import story_retrieve
    from .tools.story_index import story_index
    from .tools.story_search import story_search
    from .tools.story_edit import story_edit
    from .tools.story_create import story_create

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
