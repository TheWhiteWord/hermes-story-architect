"""Story Architect — plugin config loader."""
from pathlib import Path


def load_plugin_config() -> dict:
    """Load plugin config from Hermes config.yaml."""
    import yaml
    from hermes_constants import get_hermes_home
    path = get_hermes_home() / "config.yaml"
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}
    block = data.get("story_architect")
    return block if isinstance(block, dict) else {}
