"""Hermes Story Architect — plugin entry point."""
from pathlib import Path
from hermes_constants import get_hermes_home

_SKILL_DIR = Path(__file__).parent / "skills"


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
