import json
import sys
import shutil
import tempfile
from pathlib import Path

import pytest

# Put the REPO ROOT on sys.path so `core` and `tools` import as top-level packages.
# This was `Path(__file__).parent` — i.e. `tests/` — under the name `repo_root`.
# It only appeared to work because 31 test files each carried their own copy of this
# insert, so nobody noticed the one in conftest was wrong. conftest is the single
# place it belongs: pytest imports it before collecting anything, so every test file
# is covered without repeating the line.
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

FIXTURE = Path(__file__).parent / "fixtures" / "save-the-children"


@pytest.fixture(autouse=True)
def _isolate_root(monkeypatch, tmp_path):
    """Patch load_plugin_config so tests never write to the live story root.

    Handlers without an explicit root_path kwarg fall back to
    load_plugin_config(). Without this, they'd read ~/.hermes/config.yaml and
    write to the real projects directory.
    """
    monkeypatch.setattr("core.config.load_plugin_config", lambda: {"root_path": str(tmp_path)})


def build_fixture_db(dest: Path, root: str) -> None:
    """Import the fixture's markdown into `dest`, which must already be a copy.

    The DB is BUILT, never committed. It used to be committed, and `.gitignore`
    (`*.db`) meant git never tracked it anyway — so a fresh clone had no DB and
    **119 tests failed**. Worse, `git checkout` never restored it, so every
    "verified by stashing" claim about a fixture-dependent test was evidence of
    nothing: the stale local DB was always what ran. Three tests were called
    "pre-existing failures" across three phases because of it.

    Markdown is the source of truth and is tracked. The DB is a build artefact of
    it, so it is built from it — which removes the whole class of bug rather than
    the one instance that surfaced.
    """
    from tools.story_import import handler as import_handler

    shutil.rmtree(dest / ".story" / "story.db", ignore_errors=True)
    # This fixture is session-scoped, so `_isolate_root` (function-scoped) has not
    # run yet and `load_plugin_config` still reaches for the real Hermes home.
    # Pass root_path explicitly AND patch the resolver for the duration.
    import core.config

    real = core.config.load_plugin_config
    core.config.load_plugin_config = lambda: {"root_path": root}
    try:
        result = json.loads(import_handler(
            {"project": str(dest), "confirm": True, "root_path": root}))
    finally:
        core.config.load_plugin_config = real
    assert result.get("success"), f"fixture import failed: {result}"


@pytest.fixture(scope="session")
def _built_fixture():
    """The fixture markdown with its DB built, in a temp dir, once per session.

    Session-scoped because the import is ~1s and four test files need it. Tests
    that WRITE to the project must still copy it (`fixture_path` does).
    """
    tmp = tempfile.mkdtemp()
    dst = Path(tmp) / "save-the-children"
    shutil.copytree(str(FIXTURE), str(dst))
    build_fixture_db(dst, tmp)
    yield dst
    shutil.rmtree(tmp, ignore_errors=True)


@pytest.fixture
def fixture_path(_built_fixture):
    """A private, writable copy of the fixture, DB built.

    Tests that import or modify the fixture use this so nothing writes into the
    repo.
    """
    tmp = tempfile.mkdtemp()
    dst = Path(tmp) / "save-the-children"
    shutil.copytree(str(_built_fixture), str(dst))
    yield dst
    shutil.rmtree(tmp, ignore_errors=True)


@pytest.fixture
def fixture_db(_built_fixture):
    """The fixture project, DB built, shared and READ-ONLY.

    For tests that only read. The repo fixture itself no longer carries a DB, so
    the four files that used to reach for it must be given a built one — this is
    that, so the build stays in one place.
    """
    return _built_fixture