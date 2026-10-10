"""The story view must present each sub-plot's own milestones.

Story-level milestones are the main plot's roles; a sub-plot's are its own,
tracked the same way. The block is JS inside a single-page dashboard, so a
string check proves nothing — these run the real file in node against a stub
DOM and assert the markup it produced.
"""

import json
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
STORY_VIEW = PLUGIN_ROOT / "src/dashboard/js/views/story.js"
FIXTURE = Path(__file__).parent / "fixtures" / "save-the-children"

pytestmark = pytest.mark.skipif(
    not shutil.which("node"), reason="node not available"
)

# Runs story.js with a stub DOM and writes out the story-body markup.
# The eval loads the plugin's OWN source file (a fixed path from this repo),
# never external input — the same pattern the arc-graph render tests use.
_HARNESS = r"""
const fs = require('fs');
global.window = global;
const els = {};
global.document = {
  getElementById: id => (els[id] || (els[id] = { textContent: '', innerHTML: '' })),
};
eval(fs.readFileSync(process.argv[1], 'utf8'));
DASH.escapeHtml = s => String(s == null ? '' : s)
  .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
DASH.PLOT_TYPE_COLORS = {};
DASH.PLOT_ROLES = ['setup', 'inciting_incident', 'complication', 'crisis', 'climax', 'resolution'];
DASH.story = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
DASH.buildStoryView();
process.stdout.write(els['story-body'].innerHTML);
"""


def render(story):
    """Run buildStoryView() on `story` and return the markup it produced."""
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
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
    """A minimal DASH.story: one main plot, one sub-plot, three scenes."""
    return {
        "project": {"name": "Save the Children"},
        "plots": [
            {"id": "main-plot", "name": "The Resistance", "plot_scope": "main", "status": "active"},
            {"id": "sub-plot", "name": "The Scientists Last Stand", "plot_scope": "sub",
             "plot_type": "Setup", "status": "active"},
        ],
        "scenes": [
            {"id": "s1", "title": "Scene One", "order": 1,
             "plots": [{"id": "main-plot", "role": "setup"}]},
            {"id": "s2", "title": "Scene Two", "order": 2,
             "plots": [{"id": "main-plot", "role": "climax"},
                       {"id": "sub-plot", "role": "inciting_incident"}]},
            {"id": "s3", "title": "Scene Three", "order": 3,
             "plots": [{"id": "sub-plot", "role": "climax"}]},
        ],
        "story_memory": {},
        **kw,
    }


def test_subplot_milestones_block_is_rendered():
    html = render(_story())
    assert "Subplot milestones" in html
    assert "The Scientists Last Stand" in html


def test_subplot_block_links_its_own_scenes():
    html = render(_story())
    # The sub-plot's inciting incident and climax scenes are clickable.
    assert "showScenePanel('s2')" in html
    assert "showScenePanel('s3')" in html
    # The role label is humanised, not the raw key.
    assert "inciting incident" in html


def test_main_plot_is_not_duplicated_in_the_subplot_block():
    """The main plot's roles are the story-level ones under Structure; the
    sub-plot block must not repeat them."""
    html = render(_story())
    block = html[html.index("Subplot milestones"):]
    assert "The Resistance</div>" not in block


def test_no_subplot_block_when_there_are_no_subplots():
    html = render(_story(plots=[
        {"id": "main-plot", "name": "The Resistance", "plot_scope": "main", "status": "active"},
    ]))
    assert "Subplot milestones" not in html


def test_subplot_block_is_omitted_when_the_subplot_has_no_roles():
    """A sub-plot with no roles yet contributes nothing to the block — the
    block itself is absent (the plot still lists under Active plot threads)."""
    html = render(_story(plots=[
        {"id": "main-plot", "name": "The Resistance", "plot_scope": "main", "status": "active"},
        {"id": "empty-sub", "name": "Dormant Thread", "plot_scope": "sub", "status": "active"},
    ]))
    assert "Subplot milestones" not in html


def test_real_fixture_payload_renders(tmp_path):
    """The block survives the shape get_dashboard_data actually emits."""
    shutil.copytree(FIXTURE, tmp_path / "projects" / "save-the-children")
    import core.config
    old = core.config.load_plugin_config
    core.config.load_plugin_config = lambda: {"root_path": str(tmp_path)}
    try:
        from tools.story_import import handler as import_handler
        import_handler({"project": "save-the-children", "confirm": True}, root_path=str(tmp_path))
        from core.db import get_dashboard_data
        data = get_dashboard_data(tmp_path / "projects" / "save-the-children")["story_data"]
    finally:
        core.config.load_plugin_config = old
    # The fixture has no main plot, so the sub-plot block is the only one.
    html = render(data)
    assert "Subplot milestones" in html
