import os
import tomllib
import tempfile
from pathlib import Path

from story_architect.app.config import load_config, DEFAULT_PORT


def test_precedence_cli_over_env_and_file(tmp_path, monkeypatch):
    cfgfile = tmp_path / "config.toml"
    cfgfile.write_text('[story_architect]\nroot = "/from/file"\nport = 9999\n')
    monkeypatch.setenv("STORY_ARCHITECT_ROOT", "/from/env")
    monkeypatch.setenv("STORY_ARCHITECT_PORT", "8888")
    # point config file location by monkeypatching _config_file
    import story_architect.app.config as c
    monkeypatch.setattr(c, "_config_file", lambda: cfgfile)
    cfg = load_config(cli_root="/from/cli", cli_port=7777)
    assert str(cfg.root) == "/from/cli"
    assert cfg.port == 7777


def test_env_over_file(tmp_path, monkeypatch):
    cfgfile = tmp_path / "config.toml"
    cfgfile.write_text('[story_architect]\nroot = "/from/file"\n')
    monkeypatch.setenv("STORY_ARCHITECT_ROOT", "/from/env")
    import story_architect.app.config as c
    monkeypatch.setattr(c, "_config_file", lambda: cfgfile)
    cfg = load_config()
    assert str(cfg.root) == "/from/env"


def test_default_port():
    cfg = load_config()
    assert cfg.port == DEFAULT_PORT
    assert cfg.root  # exists default
