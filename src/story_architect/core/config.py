"""Story Architect — plugin config loader.

The configured directory is ``root_path``: the folder that holds
``projects/<slug>/.story/story.db``. The SQLite DB is the source of truth;
markdown is an export (see tools/story_export.py), so the directory is a
plain root, not a markdown vault.
"""
from pathlib import Path

# Used when the user has not set story_architect.root_path.
DEFAULT_ROOT_PATH = "~/story-architect"


def load_plugin_config() -> dict:
    """Load plugin config. Standalone app no longer uses external config."""
    return {}


def resolve_root(kwargs: dict | None = None) -> Path:
    """The root directory holding all story projects.

    ``kwargs.get("root_path")`` wins, so a caller or test can override
    without touching config. Otherwise ``story_architect.root_path``.
    """
    override = (kwargs or {}).get("root_path")
    if override:
        return Path(override)
    return Path(load_plugin_config().get("root_path", DEFAULT_ROOT_PATH)).expanduser()
