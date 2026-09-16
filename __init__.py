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

    # Register skills — new combined skill + legacy sub-skills
    _register_skills(ctx)

    from .tools import story_dashboard

    ctx.register_tool(
        name="story_dashboard",
        toolset="story_architect",
        schema=story_dashboard.SCHEMA,
        handler=story_dashboard.handler,
        check_fn=_requirements_met,
        emoji="📊",
    )

    # Inject SOUL.md block if plugin is enabled
    _manage_soul_block()

    # Auto-refresh dashboard after any data-modifying action
    def auto_refresh_dashboard(*, tool_name, result, **kwargs):
        if tool_name not in ("story_dashboard", "story_edit", "story_create", "story_index"):
            return
        try:
            data = json.loads(result)
            # For story_dashboard, just open the existing URL
            if tool_name == "story_dashboard":
                url = data.get("dashboard_url")
                if url:
                    ctx.dispatch_tool("desktop_preview", {"action": "open", "url": url})
            # For data-modifying tools, regenerate dashboard then open
            elif data.get("success") and "error" not in data:
                project = kwargs.get("args", {}).get("project", "")
                if project:
                    ctx.dispatch_tool("story_dashboard", {"project": project})
        except Exception:
            pass

    ctx.register_hook("post_tool_call", auto_refresh_dashboard)


def _register_skills(ctx) -> None:
    """Register the combined hermes-story-architect skill."""
    skill_md = _REPO_ROOT / "skills" / "hermes-story-architect" / "SKILL.md"
    if skill_md.exists():
        ctx.register_skill(
            "hermes-story-architect",
            skill_md,
            description="Story Architect — manage story projects (characters, locations, plots, scenes, sequences, acts, arcs).",
        )


SOUL_ANCHOR = "<!-- story-architect: managed by plugin; do not edit -->"


def _manage_soul_block() -> None:
    """Ensure SOUL.md has the managed block if plugin is enabled.

    Idempotent: safe to call on every Hermes startup.
    """
    try:
        import yaml
    except ImportError:
        return

    try:
        from hermes_constants import get_hermes_home
    except ImportError:
        return

    hermes_home = get_hermes_home()

    # Check if plugin is enabled
    config_path = hermes_home / "config.yaml"
    if not config_path.exists():
        return
    try:
        config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    except Exception:
        return

    enabled = "hermes-story-architect" in config.get("plugins", {}).get("enabled", [])
    if not enabled:
        return

    # Build the managed block
    block = f"""{SOUL_ANCHOR}
## Story Architect

When the user asks about story projects (characters, locations, plots, scenes, 
sequences, acts, arcs, screenplays, value arcs), load the story architect skill:
`skill_view("hermes-story-architect:hermes-story-architect")`

This gives you the full project context, index format, and entity schemas.
{SOUL_ANCHOR}"""

    soul_path = hermes_home / "SOUL.md"

    if not soul_path.exists():
        soul_path.write_text(block, encoding="utf-8")
        return

    try:
        text = soul_path.read_text(encoding="utf-8")
    except Exception:
        return

    if SOUL_ANCHOR in text:
        # Already managed — replace the block in place
        start = text.index(SOUL_ANCHOR)
        end = text.index(SOUL_ANCHOR, start + 1) + len(SOUL_ANCHOR)
        text = text[:start] + block + text[end:]
    else:
        # Append
        text = text.rstrip() + "\n\n" + block

    try:
        soul_path.write_text(text, encoding="utf-8")
    except Exception:
        pass
