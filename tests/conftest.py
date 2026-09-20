import sys
import shutil
import tempfile
from pathlib import Path

import pytest

# Add repo root to sys.path so `core` and `tools` are importable as top-level packages
repo_root = Path(__file__).parent
sys.path.insert(0, str(repo_root))


@pytest.fixture(autouse=True)
def _isolate_vault(monkeypatch, tmp_path):
    """Patch load_plugin_config so tests never write to the live Hermes vault.

    Handlers that don't pass vault_path fall back to load_plugin_config().
    Without this, they'd read ~/.hermes/config.yaml and write to the real vault.
    """
    monkeypatch.setattr("core.config.load_plugin_config", lambda: {"vault_path": str(tmp_path)})


@pytest.fixture
def fixture_path():
    """Path to the save-the-children fixture, copied to a temp dir.

    Tests that need to import or modify the fixture must use this to avoid
    creating .story/story.db in the repo.
    """
    src = Path(__file__).parent / "fixtures" / "save-the-children"
    tmp = tempfile.mkdtemp()
    dst = Path(tmp) / "save-the-children"
    shutil.copytree(str(src), str(dst))
    yield dst
    shutil.rmtree(tmp, ignore_errors=True)
