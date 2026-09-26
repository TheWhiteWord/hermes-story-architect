"""Hermes Story Architect — plugin entry point."""
import json
import re
import sys
from pathlib import Path

# Ensure repo root is on sys.path so core/ and tools/ are importable
_REPO_ROOT = Path(__file__).parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from core.config import DEFAULT_ROOT_PATH, load_plugin_config

_SKILL_DIR = _REPO_ROOT / "skills"


def _requirements_met() -> bool:
    """Check if root_path is configured."""
    return bool(load_plugin_config().get("root_path"))


def _ensure_root_path() -> None:
    """Make ``story_architect.root_path`` visible in config.yaml.

    The key used to be ``vault_path``, back when markdown was the source of
    truth. The DB is authoritative now, so the directory is a plain root —
    and nothing reads the old name any more. Inject the key when it is absent
    so the user can see and change it instead of guessing which directory the
    tools are pointed at.

    Text-level YAML edit, not safe_load/safe_dump — a dump would rewrite the
    whole file and drop every comment in the user's config.
    """
    try:
        import yaml
        from hermes_constants import get_hermes_home
    except ImportError:
        return

    path = get_hermes_home() / "config.yaml"
    if not path.exists():
        return
    try:
        text = path.read_text(encoding="utf-8")
        data = yaml.safe_load(text) or {}
    except Exception:
        return

    block = data.get("story_architect")
    if isinstance(block, dict) and "root_path" in block:
        return  # already configured — nothing to do

    if re.search(r"^story_architect\s*:", text, re.M):
        new_text = re.sub(
            r"^(story_architect\s*:)[ \t]*$",
            rf"\1\n  root_path: {DEFAULT_ROOT_PATH}",
            text,
            count=1,
            flags=re.M,
        )
    else:
        new_text = text.rstrip("\n") + f"\n\nstory_architect:\n  root_path: {DEFAULT_ROOT_PATH}\n"

    try:
        path.write_text(new_text, encoding="utf-8")
    except Exception:
        pass


def _tool_schema(schema: dict) -> dict:
    """Wrap a tool module's SCHEMA into the shape Hermes registers.

    Tool modules declare a plain JSON Schema (``properties``/``required`` at the
    top level). Hermes reads ``schema["parameters"]`` — so passing that
    straight through registered every tool with ZERO parameters and an empty
    description, and the model had to guess what to pass. One place to fix it.
    """
    return {
        "description": schema.get("description", ""),
        "parameters": {
            "type": "object",
            "properties": schema.get("properties", {}),
            "required": schema.get("required", []),
        },
    }


def register(ctx) -> None:
    """Register all Story Architect tools and skills."""
    _ensure_root_path()

    from .tools import story_load
    from .tools import story_retrieve
    from .tools import story_search
    from .tools import story_edit
    from .tools import story_create
    from .tools import story_memory
    from .tools import story_describe
    from .tools import story_import
    from .tools import story_export
    from .tools import story_backup

    ctx.register_tool(
        name="story_describe",
        toolset="story_architect",
        schema=_tool_schema(story_describe.SCHEMA),
        handler=story_describe.handler,
        check_fn=_requirements_met,
        emoji="📋",
    )

    ctx.register_tool(
        name="story_load",
        toolset="story_architect",
        schema=_tool_schema(story_load.SCHEMA),
        handler=story_load.handler,
        check_fn=_requirements_met,
        emoji="📖",
    )
    ctx.register_tool(
        name="story_retrieve",
        toolset="story_architect",
        schema=_tool_schema(story_retrieve.SCHEMA),
        handler=story_retrieve.handler,
        check_fn=_requirements_met,
        emoji="🔍",
    )
    ctx.register_tool(
        name="story_search",
        toolset="story_architect",
        schema=_tool_schema(story_search.SCHEMA),
        handler=story_search.handler,
        check_fn=_requirements_met,
        emoji="🔎",
    )
    ctx.register_tool(
        name="story_edit",
        toolset="story_architect",
        schema=_tool_schema(story_edit.SCHEMA),
        handler=story_edit.handler,
        check_fn=_requirements_met,
        emoji="✏️",
    )
    ctx.register_tool(
        name="story_memory",
        toolset="story_architect",
        schema=_tool_schema(story_memory.SCHEMA),
        handler=story_memory.handler,
        check_fn=_requirements_met,
        emoji="🧠",
    )

    ctx.register_tool(
        name="story_create",
        toolset="story_architect",
        schema=_tool_schema(story_create.SCHEMA),
        handler=story_create.handler,
        check_fn=_requirements_met,
        emoji="➕",
    )

    # Register skills — new combined skill + legacy sub-skills
    _register_skills(ctx)

    ctx.register_tool(
        name="story_import",
        toolset="story_architect",
        schema=_tool_schema(story_import.SCHEMA),
        handler=story_import.handler,
        check_fn=_requirements_met,
        emoji="📥",
    )
    ctx.register_tool(
        name="story_export",
        toolset="story_architect",
        schema=_tool_schema(story_export.SCHEMA),
        handler=story_export.handler,
        check_fn=_requirements_met,
        emoji="📤",
    )
    ctx.register_tool(
        name="story_backup",
        toolset="story_architect",
        schema=_tool_schema(story_backup.SCHEMA),
        handler=story_backup.handler,
        check_fn=_requirements_met,
        emoji="💾",
    )

    from .tools import story_dashboard

    ctx.register_tool(
        name="story_dashboard",
        toolset="story_architect",
        schema=_tool_schema(story_dashboard.SCHEMA),
        handler=story_dashboard.handler,
        check_fn=_requirements_met,
        emoji="📊",
    )

    # Inject SOUL.md block if plugin is enabled
    _manage_soul_block()

    # Auto-refresh dashboard after any data-modifying action
    def auto_refresh_dashboard(*, tool_name, result, **kwargs):
        if tool_name not in ("story_dashboard", "story_edit", "story_create", "story_memory"):
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
