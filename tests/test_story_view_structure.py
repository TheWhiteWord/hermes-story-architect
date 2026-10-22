"""Story view: Setting field placement and subplot milestones removal.

The story view is JS inside a single-page dashboard, so a string check
against the source proves nothing. These run the real file in node
against a stub DOM and assert the markup it produced.
"""

import json
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
STORY_VIEW = PLUGIN_ROOT / "src/dashboard/js/views/story.js"

pytestmark = pytest.mark.skipif(
    not shutil.which("node"), reason="node not available"
)

# Runs story.js with a stub DOM and writes out the story-body markup.
_HARNESS = r"""
const fs = require('fs');
global.window = global;
const els = {};
global.document = {
  getElementById: id => (els[id] || (els[id] = { innerHTML: '', textContent: '' })),
  querySelectorAll: () => [],
};
eval(fs.readFileSync(process.argv[1], 'utf8'));
DASH.escapeHtml = s => String(s == null ? '' : s)
  .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
DASH.valueGraphLink = () => '';
DASH.PLOT_TYPE_COLORS = {};
DASH.PLOT_ROLES = ['setup', 'inciting_incident', 'complication', 'crisis', 'climax', 'resolution'];
DASH.story = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
DASH.buildStoryView();
process.stdout.write(els['story-body'].innerHTML);
"""


def render(story):
    """Run buildStoryView() on `story` and return the markup it produced."""
    with tempfile.NamedTemporaryFile("w", suffix="..json", delete=False) as f:
        json.dump(story, f)
        data_path = f.name
    try:
        out = subprocess.run(
            ["node", "-e", _HARNESS, str(STORY_VIEW), data_path],
            capture_output=True, text=True, timeout=60,
        )
    finally:
        Path(data_path).unlink()
    assert out.returncode == 0, out.stderr[-2000:]
    return out.stdout


def _story(**kw):
    """A minimal DASH.story with setting, controlling idea, value arc, and plots."""
    return {
        "project": {
            "name": "Save the Children",
            "setting": "The Institute — a decaying research facility, 400 years apart",
            "controlling_idea": "Freedom requires the courage to leave what you know",
            "story_value": "Freedom",
            "spine": "A young person fights to escape an oppressive system",
            "structure_type": "Classical",
            "value_focus": {"major": [], "minor": []},
        },
        "plots": [
            {"id": "main-plot", "name": "The Resistance", "plot_scope": "main", "status": "active"},
        ],
        "scenes": [],
        "story_memory": {},
        **kw,
    }


def test_setting_appears_between_controlling_idea_and_value_arc():
    """Setting must appear in the Structure section between Controlling Idea and Value Arc."""
    html = render(_story())
    ci = html.index("Controlling Idea")
    setting = html.index("Setting")
    va = html.index("Value Arc")
    assert ci < setting < va


def test_subplot_milestones_not_rendered():
    """The 'Subplot milestones' section must not appear in the story view."""
    html = render(_story())
    assert "Subplot milestones" not in html
