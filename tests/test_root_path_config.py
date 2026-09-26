"""_ensure_root_path makes story_architect.root_path visible in config.yaml."""
import importlib.util
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))


def _load_init(tmp_home, monkeypatch, config_text):
    """Import a fresh copy of the plugin package bound to a fake hermes home."""
    import types

    fake = types.ModuleType("hermes_constants")
    fake.get_hermes_home = lambda: tmp_home
    monkeypatch.setitem(sys.modules, "hermes_constants", fake)

    (tmp_home / "config.yaml").write_text(config_text, encoding="utf-8")
    sys.modules.pop("hermes_rootpath_probe", None)
    spec = importlib.util.spec_from_file_location(
        "hermes_rootpath_probe", REPO / "__init__.py",
        submodule_search_locations=[str(REPO)],
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["hermes_rootpath_probe"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_key_is_injected_with_default_when_missing(tmp_path, monkeypatch):
    cfg = "story_architect:\n  some_other_key: 1\n"
    mod = _load_init(tmp_path, monkeypatch, cfg)

    mod._ensure_root_path()

    block = yaml.safe_load((tmp_path / "config.yaml").read_text())["story_architect"]
    assert block["root_path"] == "~/story-architect"
    assert block["some_other_key"] == 1  # existing keys untouched


def test_block_is_created_when_absent(tmp_path, monkeypatch):
    mod = _load_init(tmp_path, monkeypatch, "model: hermes\n")

    mod._ensure_root_path()

    block = yaml.safe_load((tmp_path / "config.yaml").read_text())["story_architect"]
    assert block["root_path"] == "~/story-architect"


def test_existing_root_path_is_not_touched(tmp_path, monkeypatch):
    cfg = "story_architect:\n  root_path: /somewhere/else\n"
    mod = _load_init(tmp_path, monkeypatch, cfg)

    mod._ensure_root_path()

    block = yaml.safe_load((tmp_path / "config.yaml").read_text())["story_architect"]
    assert block["root_path"] == "/somewhere/else"


def test_comments_survive(tmp_path, monkeypatch):
    """A safe_dump rewrite would drop these — the whole reason for text surgery."""
    cfg = "# my config\nstory_architect:\n  other: 1  # keep me\n"
    mod = _load_init(tmp_path, monkeypatch, cfg)

    mod._ensure_root_path()

    text = (tmp_path / "config.yaml").read_text()
    assert "# my config" in text
    assert "# keep me" in text
    assert "root_path: ~/story-architect" in text
