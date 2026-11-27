"""Projects page: the render functions and the branch graph, executed for real.

`web/js/projects.js` and `web/js/history-graph.js` are browser modules, so a string
check against their source proves nothing. `tests/projects_harness.js` runs the repo's
own files with no DOM and asserts the markup and geometry they produce; this test just
drives that harness under pytest so the normal suite covers it.
"""

import re
import shutil
import subprocess
from pathlib import Path

import pytest

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
HARNESS = PLUGIN_ROOT / "tests/projects_harness.js"
WEB = PLUGIN_ROOT / "src/white_words/scriptwriting/web"

pytestmark = pytest.mark.skipif(not shutil.which("node"), reason="node not available")


def run_harness():
    return subprocess.run(
        ["node", str(HARNESS)],
        cwd=str(PLUGIN_ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )


def test_the_projects_page_render_functions_behave():
    out = run_harness()
    tail = (out.stdout + out.stderr)[-3000:]
    assert out.returncode == 0, tail
    assert "all checks passed" in out.stdout, tail
    assert "FAIL" not in out.stdout, tail


def test_the_harness_reports_how_many_checks_it_ran():
    # A harness that silently stops asserting is worse than none: pin the count so
    # deleting a check is a test failure, not a quiet green.
    out = run_harness()
    assert out.returncode == 0, (out.stdout + out.stderr)[-3000:]
    m = re.search(r"all checks passed \((\d+) checks\)", out.stdout)
    assert m is not None, out.stdout[-3000:]
    assert int(m.group(1)) >= 110, out.stdout[-3000:]


def test_the_page_loads_its_scripts_in_an_order_that_works():
    """projects.js and the chip need the API wrapper, the graph and the shared dialogs."""
    html = (WEB / "index.html").read_text()
    order = [
        html.index(f'src="js/{name}"')
        for name in (
            "history-api.js",
            "history-graph.js",
            "history-dialogs.js",
            "text-diff.js",
            "drafts-common.js",
            "reader.js",
            "compare.js",
            "draft-chip.js",
            "projects.js",
            "chat-api.js",
        )
    ]
    assert order == sorted(order)
    assert html.index("DASH.boot();") > order[-1]
    assert 'href="css/projects.css"' in html
