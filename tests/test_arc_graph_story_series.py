"""The story value must plot as a curve, from scene `y`, on the arc engine.

The graph is JS inside a single-page dashboard, so every Python test in this
repo that "checked" it was reading strings. These run the real file in node
against a stub DOM and assert the SVG it emits.

The two tracks must not be silently merged: the story series is drawn from
scenes, the character series from beats, and the character-only sanity
heuristics must not be applied to the story.
"""

import json
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
ARC_GRAPH = PLUGIN_ROOT / "src/dashboard/js/graph/arc-graph.js"
FIXTURE = Path(__file__).parent / "fixtures" / "save-the-children"

pytestmark = pytest.mark.skipif(
    not shutil.which("node"), reason="node not available"
)

# Runs arc-graph.js with a stub DOM and returns the SVG (or the empty-state
# HTML) that buildArcGraph() produced.
_HARNESS = r"""
const fs = require('fs');
global.window = global;   // in a browser window IS the global object
const els = {};
global.document = {
  getElementById: id => (els[id] || (els[id] = { innerHTML: '', style: {}, dataset: {},
    classList: { add(){}, remove(){} } })),
  querySelectorAll: () => [],
  addEventListener: () => {},
};
eval(fs.readFileSync(process.argv[1], 'utf8'));
DASH.escapeHtml = s => String(s == null ? '' : s)
  .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
DASH.roleColor = () => '#7b9cf0';
DASH.story = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
DASH.buildArcGraph();
process.stdout.write(els['arc-graph-wrap'].innerHTML);
"""


def render(story, tail=None, setup=None):
    """Run buildArcGraph() on `story` and return the markup it produced.

    `tail` optionally replaces what the harness writes out, so a test can read
    a second element (e.g. the warnings div) as well as the SVG.
    `setup` is JS run after DASH.story is assigned and before the first build,
    so a test can set a toggle (e.g. `DASH.arcStoryMuted = true`).
    """
    src = _HARNESS
    if setup:
        src = src.replace(
            "DASH.buildArcGraph();\nprocess.stdout.write(els['arc-graph-wrap'].innerHTML);",
            f"{setup}\nDASH.buildArcGraph();\nprocess.stdout.write(els['arc-graph-wrap'].innerHTML);",
        )
    if tail:
        src = src.replace(
            "process.stdout.write(els['arc-graph-wrap'].innerHTML);",
            f"DASH.buildArcGraph();\nprocess.stdout.write({tail});",
        )
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(story, f)
        data_path = f.name
    try:
        out = subprocess.run(
            ["node", "-e", src, str(ARC_GRAPH), data_path],
            capture_output=True, text=True, timeout=60,
        )
    finally:
        Path(data_path).unlink()
    assert out.returncode == 0, out.stderr[-2000:]
    return out.stdout


def _story(**kw):
    """A minimal DASH.story: one project header, acts, scenes, no characters."""
    return {
        "project": {"act_count": 3, "story_value": "Trust"},
        "acts": [], "scenes": [], "characters": [],
        **kw,
    }


def _scene(sid, act, order, **kw):
    return {"id": sid, "title": sid, "act_id": act, "order": order, **kw}


@pytest.fixture
def story_project():
    """The real fixture's shape, read from the real dashboard payload."""
    import tempfile
    tmp = Path(tempfile.mkdtemp())
    shutil.copytree(FIXTURE, tmp / "projects" / "save-the-children")
    import core.config
    old = core.config.load_plugin_config
    core.config.load_plugin_config = lambda: {"root_path": str(tmp)}
    try:
        from tools.story_import import handler as import_handler
        import_handler({"project": "save-the-children", "confirm": True}, root_path=str(tmp))
        from core.db import get_dashboard_data
        data = get_dashboard_data(tmp / "projects" / "save-the-children")["story_data"]
    finally:
        core.config.load_plugin_config = old
    return data


def test_dashboard_payload_gives_scenes_a_plottable_y(story_project):
    """The curve needs data the backend actually sends.

    `_entity_dict` merges `extra` to top level, so this holds structurally —
    but the graph is dead without it, and nothing else asserts it for scenes.
    """
    ys = [s.get("y") for s in story_project["scenes"]]
    assert any(isinstance(y, (int, float)) for y in ys), ys
    assert any(s.get("shift") for s in story_project["scenes"])


def test_story_series_is_a_polyline_through_scenes(story_project):
    svg = render(story_project)
    assert 'class="arc-line story-line"' in svg
    assert svg.count("story-point") >= 2, "story curve needs at least two points"


def test_story_points_carry_the_tooltip_data(story_project):
    """`shift` already has a tooltip element — verify it is fed, not added."""
    svg = render(story_project)
    for circle in (seg for seg in svg.split("<circle") if "story-point" in seg):
        assert "data-shift=" in circle
        assert "data-y=" in circle
        assert "data-label=" in circle


def test_story_points_are_in_story_order():
    """Scenes in story order are the same polyline on a different x-axis.

    The payload is not guaranteed to arrive in story order, so the series must
    sort itself. Asserted on a deliberately shuffled input — against the
    already-sorted fixture this test passes whether or not the sort exists.
    """
    story = _story(
        acts=[{"id": "act-1", "title": "Act 1"}, {"id": "act-2", "title": "Act 2"}],
        scenes=[
            _scene("s3", "act-2", 1, y=0.1),
            _scene("s1", "act-1", 1, y=0.9),
            _scene("s4", "act-2", 2, y=-0.2),
            _scene("s2", "act-1", 2, y=0.5),
        ],
    )
    series = json.loads(render(
        story, tail="JSON.stringify(DASH.storySeries(DASH.scenePositions())"
                    ".map(p => [p.scene.id, DASH.arcXScale(p.t)]))"))
    assert [s[0] for s in series] == ["s1", "s2", "s3", "s4"], series
    xs = [s[1] for s in series]
    assert xs == sorted(xs), f"story points out of story order: {series}"


def test_no_two_scenes_share_an_x():
    """Every scene gets its own pixel, including across an act boundary.

    Regression: scenes spanned their act band edge to edge, so an act's last
    scene and the next act's first both landed on the band edge — two dots
    stacked on one x, and the beat positions shared it. Scenes now sit at the
    centre of their slot, which makes a band own [actIdx, actIdx+1) outright.
    """
    story = _story(
        acts=[{"id": f"act-{i}", "title": f"Act {i}"} for i in (1, 2, 3)],
        # 2, 1 and 3 scenes per act. The collision needs two or more scenes on
        # BOTH sides of a boundary — a lone scene centres at 0.5 and never
        # lands on an edge, which is why the old 1-scene special case hid it.
        scenes=(
            [_scene("a1", "act-1", 1, y=0.5), _scene("a2", "act-1", 2, y=0.1)]
            + [_scene("b1", "act-2", 1, y=0.2)]
            + [_scene(f"c{i}", "act-3", i, y=0.0) for i in (1, 2, 3)]
        ),
    )
    xs = [s[1] for s in json.loads(render(
        story, tail="JSON.stringify(DASH.storySeries(DASH.scenePositions())"
                    ".map(p => [p.scene.id, DASH.arcXScale(p.t)]))"))]
    assert len(xs) == 6
    assert len(set(xs)) == len(xs), f"two scenes share an x: {xs}"
    assert xs == sorted(xs), xs

    # The act-1/act-3 boundary specifically: two scenes, then two more.
    boundary = _story(
        acts=[{"id": f"act-{i}", "title": f"Act {i}"} for i in (1, 2)],
        scenes=(
            [_scene("a1", "act-1", 1, y=0.5), _scene("a2", "act-1", 2, y=0.1)]
            + [_scene("b1", "act-2", 1, y=0.2), _scene("b2", "act-2", 2, y=-0.2)]
        ),
    )
    at = dict((s[0], s[1]) for s in json.loads(render(
        boundary, tail="JSON.stringify(DASH.storySeries(DASH.scenePositions())"
                       ".map(p => [p.scene.id, DASH.arcXScale(p.t)]))")))
    assert at["a2"] != at["b1"], (
        f"act-1's last scene and act-2's first share x={at['a2']}: {at}")


def test_story_line_draws_without_any_character_arcs():
    """A story curve alone is a real state, not an empty graph.

    Regression: the empty state keyed on `chars.length === 0`, so a project
    mid-write — scenes charged, no arc designed yet — showed nothing at all.
    """
    story = _story(
        acts=[{"id": "act-1", "title": "Act 1"}],
        scenes=[
            _scene("s1", "act-1", 1, y=0.6, shift="doubt → trust"),
            _scene("s2", "act-1", 2, y=0.2, shift="trust → suspicion"),
        ],
        characters=[],
    )
    svg = render(story)
    assert "story-line" in svg
    assert "arc-empty" not in svg


def test_no_curve_at_all_still_shows_the_empty_state():
    story = _story(
        acts=[{"id": "act-1", "title": "Act 1"}],
        scenes=[_scene("s1", "act-1", 1)],
        characters=[],
    )
    svg = render(story)
    assert "arc-empty" in svg
    assert "story-line" not in svg


def test_scene_without_a_y_is_not_plotted():
    """An unrecorded charge must not be drawn as a point at 0.0.

    0.0 is a real value a writer can set; a missing `y` is not the same
    statement, and plotting it would invent a measurement.
    """
    story = _story(
        acts=[{"id": "act-1", "title": "Act 1"}],
        scenes=[
            _scene("s1", "act-1", 1, y=0.6),
            _scene("s2", "act-1", 2),               # no y
            _scene("s3", "act-1", 3, y=-0.4),
        ],
        characters=[],
    )
    svg = render(story)
    assert svg.count("story-point") == 2, svg
    assert "s2" not in svg


def test_story_heuristics_are_not_borrowed_from_the_character_checks():
    """A flat story value is not a flat character arc.

    The >0.8-jump and flat-arc warnings name a character and a beat, and they
    are judgements about a dramatic arc. Running them on the story would cry
    wolf on a deliberate, held-steady value — the same mistake the rejected
    continuity checks would have made.
    """
    flat = _story(
        acts=[{"id": "act-1", "title": "Act 1"}],
        scenes=[_scene(f"s{i}", "act-1", i, y=0.5, shift="held") for i in (1, 2, 3)],
        characters=[],
    )
    svg, _, warnings = render(
        flat, tail="els['arc-graph-wrap'].innerHTML + '||' + els['arc-warnings'].innerHTML"
    ).partition("||")
    assert "story-line" in svg
    assert "flat" not in warnings and "jump" not in warnings, warnings


def test_character_warnings_still_fire():
    """The checks are scoped to characters, not deleted."""
    char = {
        "id": "kael", "name": "Kael", "role": "protagonist", "arc_type": "positive",
        "arc_beat_count": 2,
        "arc_beats_list": [
            {"id": "b1", "label": "one", "scene": "s1", "y": 0.5, "order": 1},
            {"id": "b2", "label": "two", "scene": "s2", "y": 0.5, "order": 2},
        ],
    }
    story = _story(
        acts=[{"id": "act-1", "title": "Act 1"}],
        scenes=[_scene("s1", "act-1", 1), _scene("s2", "act-1", 2)],
        characters=[char],
    )
    warnings = render(story, tail="els['arc-warnings'].innerHTML")
    assert "flat" in warnings, warnings


def test_character_and_story_series_coexist(story_project):
    """One engine, two sources: both lines in one SVG."""
    svg = render(story_project)
    assert "story-line" in svg
    assert 'class="arc-line' in svg
    assert svg.count("<polyline") + svg.count("<path") >= 2


def test_the_story_arc_can_be_muted(story_project):
    """Muting the story must drop its line and its points, and nothing else.

    The character arcs already mute this way; the story curve is the other half
    of one graph, so it needs the same switch — otherwise a story line crossing
    six character lines cannot be read on its own.
    """
    on = render(story_project)
    assert "story-line" in on and "story-point" in on

    off = render(story_project, setup="DASH.arcStoryMuted = true;")
    assert "story-line" not in off, "the story polyline survived muting"
    assert "story-point" not in off, "story points survived muting"
    # Muting one track must not empty the graph or silence the other.
    assert 'class="arc-line' in off, "muting the story removed the character arcs"
    assert "arc-beat-dot" in off, "muting the story removed the beat dots"


def test_a_muted_story_arc_does_not_claim_the_project_has_no_curve():
    """Muting is a viewing choice, not a statement about the data.

    The empty state is reached on `storyPts.length === 0` — the *unmuted* data.
    If muting also emptied the graph, hiding a line would read as "this project
    has no value trajectory", which is the opposite of what the button means.
    """
    story = _story(
        acts=[{"id": "act-1", "title": "Act 1"}],
        scenes=[_scene("s1", "act-1", 1, y=0.4), _scene("s2", "act-1", 2, y=-0.2)],
    )
    muted = render(story, setup="DASH.arcStoryMuted = true;")
    assert "arc-empty" not in muted, "muting the story showed the empty state"
    assert "arc-svg" in muted, "muting the story removed the graph entirely"
