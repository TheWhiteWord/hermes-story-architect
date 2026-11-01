"""Pure block model: parse/serialize, heading, cast resolution, findings.

The parity tests pin the property the module's docstring claims: it agrees
with the lexer about what a heading, a cue and a transition are, on real
scene content, not only on hand-picked strings.
"""
import pytest

from story_architect.core import scene_script as ss
from story_architect.core.fountain_lexer import parse as lex

CHARS = [
    {"id": "mara-chen", "name": "Mara Chen", "story_role": "Protagonist"},
    {"id": "detective-oak", "name": "Detective Oak", "story_role": "Antagonist"},
    {"id": "oak-sr", "name": "Oak Senior", "story_role": "Minor"},
]

SCRIPT = (
    "INT. KITCHEN - NIGHT\n\n"
    "Mara stands at the counter.\n\n"
    "RAIN HAMMERS.\n\n"
    "MARA (V.O.)\n(quietly)\nYou knew.\nThe whole time.\n\n"
    "DETECTIVE OAK\nNo.\n\n"
    "CUT TO:\n\n[[a note]]\n\n!INT. NOT A HEADING\n\n> centered <\n"
)


def _roundtrip(content):
    h, body = ss.split_heading(content)
    return h, ss.parse_blocks(body)


class TestRoundTrip:
    def test_types(self):
        h, blocks = _roundtrip(SCRIPT)
        assert h == "INT. KITCHEN - NIGHT"
        assert [b["type"] for b in blocks] == [
            "action", "action", "character", "parenthetical", "dialogue",
            "character", "dialogue", "transition", "note", "action", "raw"]

    def test_serialization_is_stable(self):
        h, blocks = _roundtrip(SCRIPT)
        again = ss.compose_content(h, blocks)
        h2, blocks2 = _roundtrip(again)
        assert blocks2 == blocks
        assert ss.compose_content(h2, blocks2) == again
        assert ss.is_lossless(SCRIPT, h, blocks)

    def test_all_caps_action_before_dialogue_gets_a_force_marker(self):
        """An action line must not turn into a cue just because it is all-caps."""
        out = ss.serialize_blocks([{"type": "action", "text": "RAIN HAMMERS.\nIt will not stop."}])
        assert out.startswith("!RAIN HAMMERS.")
        assert ss.parse_blocks(out) == [{"type": "action", "text": "RAIN HAMMERS.\nIt will not stop."}]

    def test_plain_action_is_left_clean(self):
        assert ss.serialize_blocks([{"type": "action", "text": "Rain hammers."}]) == "Rain hammers."

    def test_mixed_case_cue_gets_at_sign_and_survives(self):
        out = ss.serialize_blocks([{"type": "character", "text": "McCoy"},
                                   {"type": "dialogue", "text": "Hi."}])
        assert out.startswith("@McCoy")
        assert ss.parse_blocks(out)[0] == {"type": "character", "text": "McCoy"}

    def test_blank_line_inside_dialogue_is_kept(self):
        blocks = [{"type": "character", "text": "MARA"},
                  {"type": "dialogue", "text": "One.\n\nTwo."}]
        again = ss.parse_blocks(ss.serialize_blocks(blocks))
        assert again == blocks

    def test_orphan_dialogue_is_reported_not_hidden(self):
        f = ss.findings(scene={"order": 1, "time_of_day": "DAY"}, heading={}, heading_line="INT. A - DAY",
                        blocks=[{"type": "dialogue", "text": "Hello?"}], cast=[], location=None,
                        has_plot_roles=True, unfilled=[])
        assert any(x["code"] == "orphan_dialogue" and x["block"] == 0 for x in f)

    def test_empty_blocks_are_dropped(self):
        assert ss.serialize_blocks([{"type": "action", "text": "  "}]) == ""

    def test_dual_dialogue_stays_raw_and_lossless(self):
        c = "INT. A - DAY\n\nMARA\nHi.\n\nOAK ^\nHo.\n"
        h, blocks = _roundtrip(c)
        assert any(b["type"] == "raw" for b in blocks)
        assert ss.is_lossless(c, h, blocks)


class TestParityWithLexer:
    """On the fixture's real scenes, the blocks and the lexer agree."""

    def test_fixture_scenes(self, fixture_db):
        import sqlite3
        conn = sqlite3.connect(str(fixture_db / ".story" / "story.db"))
        bodies = [r[0] for r in conn.execute(
            "SELECT body FROM sections WHERE heading='Content' AND body<>'' ")]
        conn.close()
        bodies = [b for b in bodies if not ss.is_placeholder(b)]
        assert bodies, "fixture has no scene content to compare"
        checked = 0
        for body in bodies:
            h, blocks = _roundtrip(body)
            tokens = [t for t in lex(body)["tokens"]
                      if t["type"] in ("character", "transition")]
            lex_cues = [ss.cue_key(t["text"]) for t in tokens if t["type"] == "character"]
            mine = [ss.cue_key(b["text"]) for b in blocks if b["type"] == "character"]
            assert mine == lex_cues, body[:80]
            assert [t["text"] for t in tokens if t["type"] == "transition"] == \
                   [b["text"] for b in blocks if b["type"] == "transition"]
            assert ss.is_lossless(body, h, blocks), body[:80]
            checked += 1
        assert checked


class TestHeading:
    @pytest.mark.parametrize("text,ie,loc,tod", [
        ("INT. KITCHEN - NIGHT", "INT.", "KITCHEN", "NIGHT"),
        ("EXT. LONDON STREET - DAY", "EXT.", "LONDON STREET", "DAY"),
        ("INT./EXT. CAR - DUSK", "INT./EXT.", "CAR", "DUSK"),
        ("I/E. CAR - DAWN", "INT./EXT.", "CAR", "DAWN"),
        ("INT. KITCHEN", "INT.", "KITCHEN", ""),
        ("EXT. A - B - DUSK", "EXT.", "A - B", "DUSK"),
        ("INT. KITCHEN - PANTRY", "INT.", "KITCHEN - PANTRY", ""),
    ])
    def test_parse(self, text, ie, loc, tod):
        p = ss.parse_heading(text)
        assert (p["mode"], p["int_ext"], p["location_text"], p["time_of_day"]) == ("structured", ie, loc, tod)

    @pytest.mark.parametrize("text", [".SNIPER SCOPE POV", "INT. KITCHEN - EVENING #12#", "INT. HALL - MOMENTS LATER"])
    def test_custom_headings_are_kept_verbatim(self, text):
        p = ss.parse_heading(text)
        # "MOMENTS LATER" is not an enum time, so it stays part of the location text
        if text.startswith("INT. HALL"):
            assert p["mode"] == "structured" and p["time_of_day"] == ""
        else:
            assert p["mode"] == "custom" and p["text"] == text

    def test_compose(self):
        assert ss.compose_heading("INT.", "The kitchen", "NIGHT") == "INT. THE KITCHEN - NIGHT"
        assert ss.compose_heading("EXT.", "Pier") == "EXT. PIER"
        with pytest.raises(ValueError):
            ss.compose_heading("INT.", "", "DAY")
        with pytest.raises(ValueError):
            ss.compose_heading("INT.", "A", "EVENING")

    def test_compose_then_parse_is_identity(self):
        h = ss.compose_heading("INT./EXT.", "Car", "DUSK")
        p = ss.parse_heading(h)
        assert ss.compose_heading(p["int_ext"], p["location_text"], p["time_of_day"]) == h

    def test_suggest_is_exact_only(self):
        locs = [{"id": "kitchen", "name": "The Kitchen"}, {"id": "kitchen-annex", "name": "Kitchen Annex"}]
        assert ss.suggest_location("KITCHEN", locs) == "kitchen"
        assert ss.suggest_location("KITCH", locs) is None


class TestCast:
    def test_exact_and_whole_word(self):
        assert ss.resolve_cue("MARA CHEN", CHARS)["id"] == "mara-chen"
        assert ss.resolve_cue("MARA", CHARS)["id"] == "mara-chen"
        assert ss.resolve_cue("DETECTIVE", CHARS)["id"] == "detective-oak"

    def test_no_prefix_or_fuzzy_match(self):
        """The mock's own example: DET must not silently become Detective Oak."""
        assert ss.resolve_cue("DET", CHARS)["id"] is None
        assert ss.resolve_cue("MA", CHARS)["id"] is None

    def test_ambiguity_resolves_to_nothing_and_names_candidates(self):
        r = ss.resolve_cue("OAK", CHARS)
        assert r["id"] is None and set(r["candidates"]) == {"detective-oak", "oak-sr"}

    def test_cue_key_strips_extensions_and_markers(self):
        assert ss.cue_key("@McCoy (V.O.)") == "MCCOY"
        assert ss.cue_key("MARA (CONT'D)") == "MARA"

    def test_two_cues_one_person_count_once(self):
        blocks = [{"type": "character", "text": "MARA"}, {"type": "dialogue", "text": "a"},
                  {"type": "character", "text": "MARA CHEN"}, {"type": "dialogue", "text": "b"},
                  {"type": "character", "text": "LEO"}, {"type": "dialogue", "text": "c"}]
        cast = ss.script_cast(blocks, CHARS)
        assert [c["id"] for c in cast] == ["mara-chen", None]
        assert cast[0]["cues"] == 2 and cast[1]["name"] == "Leo" and not cast[1]["registered"]
        assert ss.script_stats("x", cast)["speaking_parts"] == 2


class TestFindings:
    def _f(self, **kw):
        base = dict(scene={"order": 3, "time_of_day": "NIGHT", "dramatic_role": "", "id": "s", "title": "S"},
                    heading={"location_text": "KITCHEN"}, heading_line="INT. KITCHEN - NIGHT",
                    blocks=[], cast=[], location={"id": "k", "name": "Kitchen", "world": {"id": "w", "name": "W"}},
                    has_plot_roles=True, unfilled=[])
        base.update(kw)
        return {x["code"] for x in ss.findings(**base)}

    def test_clean_scene_has_no_critical(self):
        assert self._f() == set()

    def test_every_critical_rule(self):
        codes = self._f(scene={"order": 0, "time_of_day": "", "dramatic_role": "", "id": "s"},
                        heading_line=None, location=None, has_plot_roles=False)
        assert {"order_unset", "time_of_day_missing", "heading_missing",
                "location_unregistered", "plot_roles_missing"} <= codes

    def test_transition_scene_needs_no_plot_roles(self):
        assert "plot_roles_missing" not in self._f(
            scene={"order": 1, "time_of_day": "DAY", "dramatic_role": "transition", "id": "s"},
            has_plot_roles=False)

    def test_location_without_world(self):
        assert "location_no_world" in self._f(location={"id": "k", "name": "Kitchen", "world": None})

    def test_unfilled_critical_fields_are_not_reported_twice(self):
        f = ss.findings(scene={"order": 1, "time_of_day": "", "id": "s"}, heading={}, heading_line="INT. A",
                        blocks=[], cast=[], location={"id": "k", "name": "K", "world": {"id": "w"}},
                        has_plot_roles=True, unfilled=["time_of_day", "scene_objective"])
        assert [x["field"] for x in f if x["level"] == "other"] == ["scene_objective"]
