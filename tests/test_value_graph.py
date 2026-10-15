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
const mk = () => ({
  innerHTML: '', textContent: '', clientWidth: 800, value: '', style: {},
  offsetTop: 0, offsetWidth: 0, offsetHeight: 0,
  addEventListener: () => {}, appendChild: () => {}, querySelectorAll: () => [],
  get querySelector() { return () => mk(); },
});
const els = {};
global.document = {
  getElementById: id => (els[id] || (els[id] = mk())),
  querySelectorAll: () => [],
  querySelector: () => mk(),
  createElement: mk,
  body: mk(),
};
global.getComputedStyle = () => ({ paddingLeft: '0px', paddingRight: '0px' });
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


# ---------- scroll zoom
#
# Same stub DOM, plus a recorded wheel listener and a controllable clock, so the
# zoom state machine is driven the way a real gesture drives it: one gesture per
# step, each clear of the 320ms lock. Ctrl is held on every gesture.

_ZOOM_HARNESS = r"""
const fs = require('fs');
global.window = global;
global.DASH = {};
const listeners = {};
const rect = () => ({ left: 0, top: 0, right: 800, bottom: 62, width: 800, height: 62 });
const mk = () => ({
  innerHTML: '', textContent: '', clientWidth: 800, value: '', style: {},
  offsetTop: 0, offsetWidth: 0, offsetHeight: 0,
  addEventListener: () => {}, appendChild: () => {}, querySelectorAll: () => [],
  getBoundingClientRect: rect,
  get querySelector() { return () => mk(); },
});
const els = {};
const content = mk();
content.addEventListener = (type, fn) => { listeners[type] = fn; };
els['vg-content'] = content;
// buildValuesView binds the wheel listener on body.querySelector('#vg-content'),
// so the stub's view body must hand back that same element. A plain object, not
// mk(): mk()'s querySelector is a getter, and assigning over a getter without a
// setter fails silently.
const bodyEl = Object.assign({}, mk());
bodyEl.querySelector = sel => (sel === '#vg-content' ? content : mk());
els['values-body'] = bodyEl;
global.document = {
  getElementById: id => (els[id] || (els[id] = mk())),
  querySelectorAll: () => [],
  querySelector: () => mk(),
  createElement: mk,
  body: mk(),
};
global.getComputedStyle = () => ({ paddingLeft: '0px', paddingRight: '0px' });
DASH.escapeHtml = s => String(s == null ? '' : s)
  .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
DASH.onViewOpened = () => {};
DASH.plotColor = pid => pid === 'main' ? '#b07be0' : '#6bbfb0';

let NOW = 1000;
Date.now = () => NOW;

eval(fs.readFileSync(process.argv[1], 'utf8'));
DASH.story = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
DASH.buildValuesView();

const S = DASH.valueGraphState;
const steps = [];
function gesture(dy) {
  NOW += 1000;                                   // clear the gesture lock
  let prevented = 0;
  listeners.wheel({
    ctrlKey: true, metaKey: false, deltaY: dy, deltaMode: 0,
    clientX: 700, clientY: 100,                  // 700 lands in the second act
    target: { closest: () => null },
    currentTarget: content,
    preventDefault: () => { prevented++; },
  });
  steps.push({ act: S.act, seq: S.seq, base: S.base,
               crumbs: els['vg-crumbs'].innerHTML, prevented });
}

gesture(-300);      // All -> the act under the pointer
gesture(-300);      // act -> the sequence under the pointer
gesture(-300);      // deepest level: no further move
gesture(300);       // back out to the act
gesture(300);       // back out to All
gesture(300);       // ceiling at All: no further move

S.base = 'act-1'; S.act = 'act-1'; S.seq = null;   // an act chosen with the control
DASH.renderValues();
gesture(300);       // the chosen act is the ceiling

process.stdout.write(JSON.stringify(steps));
"""


def zoom_steps(story):
    """Drive the zoom gestures and return the state after each one."""
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(story, f)
        data_path = f.name
    try:
        out = subprocess.run(
            ["node", "-e", _ZOOM_HARNESS, str(VALUE_GRAPH), data_path],
            capture_output=True, text=True, timeout=60,
        )
    finally:
        Path(data_path).unlink()
    assert out.returncode == 0, out.stderr[-2000:]
    return json.loads(out.stdout)


def test_zoom_in_goes_all_then_act_then_sequence():
    s = zoom_steps(_story())
    assert s[0]["act"] == "act-2" and s[0]["seq"] is None    # All -> act
    assert s[1]["act"] == "act-2" and s[1]["seq"] == "seq-2"  # act -> sequence


def test_zoom_in_stops_at_the_deepest_level():
    s = zoom_steps(_story())
    assert s[2]["seq"] == s[1]["seq"]


def test_zoom_out_walks_back_one_level_at_a_time():
    s = zoom_steps(_story())
    assert s[3]["seq"] is None and s[3]["act"] == "act-2"
    assert s[4]["act"] is None and s[4]["seq"] is None


def test_zoom_out_does_not_go_above_all():
    s = zoom_steps(_story())
    assert s[5]["act"] is None and s[5]["seq"] is None


def test_a_chosen_act_is_the_ceiling_for_zoom_out():
    s = zoom_steps(_story())
    assert s[6]["base"] == "act-1"
    assert s[6]["act"] == "act-1" and s[6]["seq"] is None


def test_every_zoom_gesture_suppresses_the_browser_zoom():
    assert all(step["prevented"] == 1 for step in zoom_steps(_story()))


def test_breadcrumb_tracks_the_zoom_level():
    s = zoom_steps(_story())
    # s[0] is after the first gesture (All -> act), so the root is already listed.
    assert "All" in s[0]["crumbs"] and "Act II" in s[0]["crumbs"]
    assert "S1" not in s[0]["crumbs"]                         # no sequence yet
    assert "All" in s[1]["crumbs"] and "Act II" in s[1]["crumbs"]
    assert "S1" in s[1]["crumbs"]
