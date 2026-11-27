"""`render_html`: the Script view's screenplay HTML, for the draft reader.

The lexer's output goes into the page as markup, and `tokens_to_html` does not escape it.
A scene is free text, so the renderer has to.
"""

from white_words.scriptwriting.core.screenplay import render_html

SCRIPT = """INT. THE KITCHEN - DUSK

Aunt Em stands at the stove.

DOROTHY
(quietly)
Do you ever think about somewhere else.

EXT. THE ROAD - DAY

A long yellow road.
"""


def test_headings_are_numbered_in_the_order_they_appear():
    html = render_html(SCRIPT)
    assert html.index('data-scenenumber="1"') < html.index('data-scenenumber="2"')
    assert html.count("fountain-scene_heading") == 2


def test_cues_parentheticals_and_dialogue_keep_their_classes():
    html = render_html(SCRIPT)
    assert '<h4 class="fountain-character">DOROTHY</h4>' in html
    assert '<p class="fountain-parenthetical">(quietly)</p>' in html
    assert '<p class="fountain-dialogue">Do you ever think about somewhere else.</p>' in html


def test_an_explicit_scene_number_is_kept():
    html = render_html("INT. THE KITCHEN - DUSK #12A#\n\nAunt Em stands.\n")
    assert 'data-scenenumber="12A"' in html


def test_markup_in_a_scene_cannot_reach_the_page():
    hostile = (
        "INT. <img src=x onerror=alert(1)> - DAY\n\n"
        "He reads <script>alert(2)</script> & leaves.\n\n"
        "KAEL\nI say <b>no</b>.\n"
    )
    html = render_html(hostile)
    assert "<img" not in html and "<script" not in html and "<b>" not in html
    assert "&lt;script&gt;" in html and "&amp;" in html


def test_title_page_fields_are_not_part_of_the_body():
    html = render_html("cc: Someone\n\nINT. THE KITCHEN - DUSK\n\nAunt Em stands.\n")
    assert "cc:" not in html


def test_an_empty_screenplay_is_empty_html():
    assert render_html("") == ""
