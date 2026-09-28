"""The linter must flag exactly the Content that renders as nothing.

Every "must flag" case below was measured against `core.screenplay.extract_scenes`
— the live render path — and produced 0 scenes. Every "must pass" case produced
1. The test asserts both directions, so the linter cannot drift into flagging
something that renders, or missing something that does not.
"""
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from core.scene_content_lint import check_scene_content, check_scenes  # noqa: E402


# ── Renders, so must not be flagged ────────────────────────────────────────
PASSES = {
    "standard INT": "INT. THE INSTITUTE - NIGHT\n\nHe waits.",
    "standard EXT": "EXT. GARDEN - DAY\n\nWind.",
    "EST": "EST. CITY - NIGHT\n\nSirens.",
    "combined INT./EXT.": "INT./EXT. RONNA'S CAR - NIGHT\n\nDriving.",
    "forced POV heading": ".SNIPER SCOPE POV\n\nA face fills the frame.",
    "forced opening titles": ".OPENING TITLES\n\n> BRICK & STEEL <",
    "forced lowercase": ".opening titles\n\n> THE END <",
    "scene number": "INT. HOUSE - DAY #1A#\n\nBody.",
    "blank lines then heading": "\n\n\nINT. A - DAY\n\nBody.",
    "trailing transition is fine": "INT. A - DAY\n\nBody.\n\nFADE OUT.",
    "empty content": "",
    "whitespace only": "   \n\n  ",
}


# ── Renders as NOTHING: the scene is absent from the script ────────────────
INVISIBLE = {
    "action only": "KAEL stands before the door.",
    "dialogue only": "                MIRA\n        You knew?",
    "inline cue (near-miss)": "MIRA: You knew?",
}


# ── Renders, but the leading text is SILENTLY DROPPED ───────────────────────
# The scene appears, so it looks fine; the content before the heading does not.
DROPS_LEADING = {
    "transition then heading": "CUT TO:\n\nINT. A - DAY\n\nBody.",
    "leading prose": "A cold open. Rain on glass.\n\nINT. A - DAY\n\nBody.",
    "section then heading": "# Act I\n\nINT. A - DAY\n\nBody.",
    "synopsis then heading": "= The setup.\n\nINT. A - DAY\n\nBody.",
}


@pytest.mark.parametrize("name,content", sorted(PASSES.items()))
def test_content_that_renders_is_not_flagged(name, content):
    assert check_scene_content(content) == [], name


@pytest.mark.parametrize("name,content", sorted(INVISIBLE.items()))
def test_content_that_renders_as_nothing_is_flagged(name, content):
    assert check_scene_content(content), name


@pytest.mark.parametrize("name,content", sorted(DROPS_LEADING.items()))
def test_content_whose_leading_lines_are_dropped_is_flagged(name, content):
    assert check_scene_content(content), name


def test_the_premise_holds_against_the_live_renderer():
    """The linter's premise, asserted rather than assumed.

    Two distinct failures, and conflating them would have hidden the second:
    no heading at all means the scene is absent; a heading that is not first
    means the scene renders but the text before it vanishes. Only the first
    shows up as an empty script.
    """
    from core.screenplay import extract_scenes

    for name, content in sorted(INVISIBLE.items()):
        assert extract_scenes(content) == [], (
            f"{name!r} now renders, so the linter should not flag it")

    for name, content in sorted(DROPS_LEADING.items()):
        scenes = extract_scenes(content)
        assert len(scenes) == 1, f"{name!r} no longer produces a scene"
        first_line = content.splitlines()[0].strip()
        assert first_line not in scenes[0]["content"], (
            f"{name!r} no longer drops its leading text, so the linter's "
            f"message would be wrong")


def test_forced_headings_are_accepted_as_headings():
    """`.SNIPER SCOPE POV` and `.OPENING TITLES` are headings, not errors. The
    linter reuses the renderer's own regex, so this cannot disagree with it."""
    from core.fountain_lexer import SCENE_HEADING_RE

    for text in (".SNIPER SCOPE POV", ".OPENING TITLES", ".opening titles"):
        assert SCENE_HEADING_RE.match(text), text
        assert check_scene_content(f"{text}\n\nBody.") == [], text


def test_the_message_says_which_failure_it_is():
    """Absence and silent-drop look identical from the dashboard, so the finding
    names which one happened."""
    absent = check_scene_content("KAEL stands before the door.")[0]
    dropped = check_scene_content("CUT TO:\n\nINT. A - DAY\n\nBody.")[0]
    assert "absent from the script" in absent, absent
    assert "dropped from the script" in dropped, dropped


def test_the_message_names_the_frontmatter_heading_when_there_is_one():
    findings = check_scene_content("KAEL stands before the door.",
                                   heading="INT. THE CENTRAL ROOM - DAY")
    assert len(findings) == 1
    assert "INT. THE CENTRAL ROOM - DAY" in findings[0], findings[0]


def test_the_message_is_actionable_without_a_frontmatter_heading():
    findings = check_scene_content("KAEL stands before the door.")
    assert len(findings) == 1
    # Must say what a heading looks like, or the finding is not actionable.
    assert "INT./EXT." in findings[0] and ".SNIPER SCOPE POV" in findings[0]
    assert "frontmatter" not in findings[0]


def test_check_scenes_labels_each_finding_with_its_entity():
    findings = check_scenes({
        "the-last-watch": {"content": "He waits.", "heading": "INT. A - NIGHT"},
        "the-door-closes": {"content": "INT. B - DAY\n\nBody."},
    })
    assert len(findings) == 1
    assert findings[0].startswith("the-last-watch:")
