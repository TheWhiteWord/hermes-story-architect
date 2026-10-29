"""Application configuration for the standalone app."""
from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path


DEFAULT_ROOT = Path.home() / "story-architect"
DEFAULT_PORT = 8731
ENV_PREFIX = "STORY_ARCHITECT_"


@dataclass
class Config:
    root: Path
    port: int = DEFAULT_PORT
    open_browser: bool = True
    hermes_api_port: int = 8642


def _config_file() -> Path:
    # platform standard config dir
    base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "story-architect" / "config.toml"


def load_config(*, cli_root=None, cli_port=None, cli_no_open=False) -> Config:
    # config file
    cf = _config_file()
    file_vals = {}
    if cf.exists():
        try:
            with cf.open("rb") as f:
                file_vals = tomllib.load(f).get("story_architect", {})
        except Exception:
            file_vals = {}

    def pick(key, cli_val, env_key, default, cast=str):
        if cli_val is not None:
            return cast(cli_val)
        env = os.environ.get(ENV_PREFIX + env_key)
        if env is not None and env != "":
            return cast(env)
        if key in file_vals and file_vals[key] not in (None, ""):
            return cast(file_vals[key])
        return default

    root_raw = pick("root", cli_root, "ROOT", str(DEFAULT_ROOT))
    port_raw = pick("port", cli_port, "PORT", DEFAULT_PORT, int)
    hermes_api_port_raw = pick("hermes_api_port", None, "HERMES_API_PORT", 8642, int)
    open_browser = True
    if cli_no_open:
        open_browser = False
    else:
        env = os.environ.get(ENV_PREFIX + "OPEN_BROWSER")
        if env is not None:
            open_browser = env.lower() not in ("0", "false", "no")
        elif "open_browser" in file_vals:
            open_browser = bool(file_vals["open_browser"])

    return Config(root=Path(root_raw).expanduser(), port=int(port_raw), open_browser=open_browser, hermes_api_port=int(hermes_api_port_raw))
