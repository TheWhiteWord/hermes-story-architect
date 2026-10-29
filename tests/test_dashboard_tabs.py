"""The Beats and Journey tabs, executed in node against the real payload.

builds a page and headless Chrome renders the panes. This file proves the two
tabs' own logic — the payload reader, the empty states, the lane/stacked switch,
the self-directed arrow, the act focus, the ribbon's fill rule — by running the
dashboard's own modules in node.

The payload is not a fixture written for the test: it is what
`core.db.get_dashboard_data` produced for the repo's own fixture project, so a
reader that expects a key the backend stopped emitting fails here rather than in
a browser.
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
DASHBOARD = PLUGIN_ROOT / "src" / "dashboard"
HARNESS = Path(__file__).parent / "dashboard_tabs_harness.js"
FIXTURE = Path(__file__).parent / "fixtures" / "save-the-children"

pytestmark = pytest.mark.skipif(not shutil.which("node"), reason="node not available")


@pytest.fixture
def payload(tmp_path):
    """The dashboard payload for the fixture project, as the dashboard gets it."""
    import story_architect.core.config

    vault = tmp_path / "v"
    dest = vault / "projects" / "stc"
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(str(FIXTURE), str(dest))

    from story_architect.tools.story_import import handler as import_handler

    story_architect.core.config.load_plugin_config = lambda: {"root_path": str(vault)}
    result = json.loads(import_handler(
        {"project": "stc", "confirm": True, "root_path": str(vault)}))
    assert result.get("success"), result

    from story_architect.core.db import get_dashboard_data

    data = get_dashboard_data(dest)
    path = tmp_path / "payload.json"
    path.write_text(json.dumps(
        {"story": data["story_data"], "sections": data["sections"]}))
    return path


@pytest.fixture
def run(payload):
    def _run():
        return subprocess.run(
            ["node", str(HARNESS), str(DASHBOARD), str(payload)],
            capture_output=True, text=True, timeout=120)
    return _run


class TestTheTabsRun:
    def test_every_check_passes(self, run):
        out = run()
        assert out.returncode == 0, out.stdout + out.stderr
        assert "all checks passed" in out.stdout

    def test_the_harness_actually_ran_its_checks(self, run):
        """A harness that checks nothing passes the test above for free."""
        out = run()
        checked = sum(1 for line in out.stdout.splitlines() if line.startswith("  ok   "))
        assert checked >= 60, f"only {checked} checks ran — the harness is not loading"

    def test_the_harness_reads_the_tree_it_is_pointed_at(self, tmp_path, payload):
        """The checks are about the dashboard's own files, not a copy of them.

        Pointing it at a tree with a broken module must fail: that is what proves
        the 60-odd checks above are reading `src/story_architect/web`, and not something
        cached, delivered, or skipped.
        """
        broken = tmp_path / "dashboard"
        shutil.copytree(str(DASHBOARD), str(broken))
        module = broken / "js" / "graph" / "track-data.js"
        module.write_text(module.read_text().replace(
            "D.sceneBeatsOf =", "D.sceneBeatsOf_DISABLED ="))

        out = subprocess.run(
            ["node", str(HARNESS), str(broken), str(payload)],
            capture_output=True, text=True, timeout=120)
        assert out.returncode != 0, "the harness passed against a tree it was not reading"
        assert "sceneBeatsOf" in out.stdout, out.stdout[-800:]
