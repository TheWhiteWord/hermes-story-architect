"""Value graph: axis, milestones, carry/jump lines, schema labels.

The value graph is JS inside a single-page dashboard, so every Python test
in this repo that "checked" it was reading strings. These run the real file
in node against a stub DOM and assert the SVG it emits.
"""

import json
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
VALUE_GRAPH = PLUGIN_ROOT / "src/dashboard/js/graph/value-graph.js"

pytestmark = pytest.mark.skipif(
    not shutil.which("node"), reason="node not available"
)

# Runs value-graph.js with a stub DOM and writes out the values-body markup.
_HARNESS = r"""
const fs = require('fs');
global.window = global;
global.DASH = {};
const els = {};
global.document = {
  getElementById: id => (els[id] || (els[id] = { innerHTML: '', textContent: '',
    clientWidth: 800, value: '', addEventListener: () => {},
    querySelectorAll: () => [], querySelector: () => ({ value: '', addEventListener: () => {} }) })),
  querySelectorAll: () => [],
  querySelector: () => ({ value: '', addEventListener: () => {} }),
};
DASH.escapeHtml = s => String(s == null ? '' : s)
  .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
DASH.onViewOpened = () => {};
DASH.plotColor = pid => pid === 'main' ? '#b07be0' : '#6bbfb0';
eval(fs.readFileSync(process.argv[1], 'utf8'));
DASH.story = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
DASH.buildValuesView();
process.stdout.write(els['vg-content'].innerHTML);
"""


def render(story):
    """Run buildValuesView() on `story` and return the markup it produced."""
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(story, f)
        data_path = f.name
    try:
        out = subprocess.run(
            ["node", "-e", _HARNESS, str(VALUE_GRAPH), data_path],
            capture_output=True, text=True, timeout=60,
        )
    finally:
        Path(data_path).unlink()
    assert out.returncode == 0, out.stderr[-2000:]
    return out.stdout


def _story():
    """A minimal story with acts, sequences, values, and value turns."""
    return {
        "project": {"name": "Test Story", "value_focus": {"major": [], "minor": []}},
        "acts": [
            {"id": "act-1", "name": "Act I", "order": 1},
            {"id": "act-2", "name": "Act II", "order": 2},
        ],
        "sequences": [
            {"id": "seq-1", "name": "Discovery", "order": 1, "parent_id": "act-1"},
            {"id": "seq-2", "name": "Confrontation", "order": 2, "parent_id": "act-2"},
        ],
        "scenes": [
            {"id": "s1", "title": "Scene 1", "order": 1, "sequence_id": "seq-1",
             "parent_id": "seq-1", "act_id": "act-1",
             "value_turns": [{"plot": "main", "value": "trust", "from": "despair", "to": "hope",
                              "effects": []}],
             "milestone": ["setup"]},
            {"id": "s2", "title": "Scene 2", "order": 2, "sequence_id": "seq-2",
             "parent_id": "seq-2", "act_id": "act-2",
             "value_turns": [{"plot": "main", "value": "trust", "from": "hope", "to": "despair",
                              "effects": []}],
             "milestone": ["climax"]},
        ],
        "values": [
            {"id": "trust", "name": "trust", "p": "hope", "c": "doubt", "cd": "despair", "nn": "fanatic"},
        ],
        "plots": [
            {"id": "main", "name": "Main Plot", "plot_scope": "main", "status": "active"},
        ],
        "characters": [],
        "story_memory": {},
    }


# ---------- axis

def test_axis_renders_act_labels():
    html = render(_story())
    assert "Act I" in html
    assert "Act II" in html


def test_axis_renders_sequence_labels():
    """Sequences are numbered per-act (S1, S2) in the axis."""
    html = render(_story())
    # Both sequences are in different acts, so both are S1
    assert "S1" in html


def test_axis_renders_milestone_markers():
    """Setup (dot) and Climax (ring) markers must appear in the axis SVG."""
    html = render(_story())
    assert "vg-ring" in html


# ---------- legend

def test_legend_has_shift_and_hold_and_negation():
    html = render(_story())
    assert "shift in a scene" in html
    assert "stayed in the same state" in html
    assert "negation of the negation" in html


def test_legend_does_not_have_carry_or_jump():
    html = render(_story())
    assert "carried on between scenes" not in html
    assert "next scene opens elsewhere" not in html


def test_legend_has_milestones():
    html = render(_story())
    assert "Setup" in html
    assert "Climax" in html
    assert "Inciting Incident" in html


# ---------- chart

def test_schema_labels_render_for_major_values():
    """Lane words (hope, doubt, despair, fanatic) must appear in the chart."""
    html = render(_story())
    assert "hope" in html
    assert "doubt" in html
    assert "despair" in html
    assert "fanatic" in html


def test_hatch_pattern_for_negation_lane():
    html = render(_story())
    assert "vg-hatch" in html


def test_unknown_word_shows_marker():
    """A word not in the schema renders a '?' marker."""
    story = _story()
    story["scenes"][0]["value_turns"][0]["from"] = "unknown-word"
    story["scenes"][0]["value_turns"][0]["to"] = "also-unknown"
    html = render(story)
    assert "vg-unknown" in html


# ---------- empty state

def test_no_turns_shows_empty_state():
    story = _story()
    story["scenes"] = [{"id": "s1", "title": "Scene 1", "order": 1,
                         "sequence_id": "seq-1", "parent_id": "seq-1", "act_id": "act-1",
                         "value_turns": [], "milestone": []}]
    html = render(story)
    assert "No value shifts recorded yet" in html
