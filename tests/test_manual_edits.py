"""A person's edit of a scene script: load, save, conflict, and what is written.

The save goes through `core.writes.edit_entity`, so these tests read the result
back through the same load the editor uses — the heading in the script and the
scene's fields must agree after every save.
"""
import pytest

from story_architect.core import manual_edits as me
from story_architect.core.db import get_db
from story_architect.core.writes import create_entity, edit_entity


@pytest.fixture
def project(tmp_path):
    p = tmp_path
    create_entity(p, "act", "act-1", {"title": "Act I"})
    create_entity(p, "sequence", "seq-1", {"title": "One", "act_id": "act-1"})
    create_entity(p, "world", "london-1950", {"name": "London 1950", "one_sentence": "T"})
    create_entity(p, "location", "kitchen", {"name": "Kitchen", "one_sentence": "T", "world": "london-1950"})
    create_entity(p, "location", "attic", {"name": "Attic", "one_sentence": "T"})
    for slug, name, role in [("mara-chen", "Mara Chen", "Protagonist"),
                             ("detective-oak", "Detective Oak", "Antagonist")]:
        create_entity(p, "character", slug, {"name": name, "story_role": role, "one_sentence": "T"})
    create_entity(p, "scene", "the-kitchen",
                  {"title": "The Kitchen", "sequence_id": "seq-1", "act_id": "act-1", "order": 2,
                   "location": "kitchen", "int_ext": "INT.", "time_of_day": "NIGHT",
                   "characters": ["mara-chen"]},
                  sections={"Content": "INT. KITCHEN - NIGHT\n\nMara stands at the counter.\n\n"
                                       "MARA\n(quietly)\nYou knew.\n\nLEO\nSorry.\n"})
    return p


def _payload(scene, **over):
    p = {"base_hash": scene["hash"],
         "blocks": scene["blocks"],
         "heading": {"mode": "structured", "int_ext": "INT.", "location": "kitchen",
                     "location_text": "", "place": "", "time_of_day": "NIGHT"},
         "extra_cast": []}
    p.update(over)
    return p


class TestLoad:
    def test_shape(self, project):
        s = me.load_scene_script(project, "the-kitchen")
        assert s["heading"]["int_ext"] == "INT." and s["heading"]["location"] == "kitchen"
        assert s["location"] == {"id": "kitchen", "name": "Kitchen",
                                 "world": {"id": "london-1950", "name": "London 1950"}}
        assert [c["id"] for c in s["cast"]] == ["mara-chen"]
        assert [c["cue"] for c in s["adhoc"]] == ["LEO"]       # speaks, not registered
        assert s["stats"]["speaking_parts"] == 2
        assert not s["locked"]

    def test_unregistered_speaker_is_a_critical_finding_with_a_block_anchor(self, project):
        s = me.load_scene_script(project, "the-kitchen")
        f = [x for x in s["findings"] if x["code"] == "character_unregistered"]
        assert len(f) == 1 and "Leo" in f[0]["message"] and isinstance(f[0]["block"], int)

    def test_unknown_scene(self, project):
        with pytest.raises(me.ScriptNotFound):
            me.load_scene_script(project, "nope")

    def test_adhoc_names_from_other_scenes_are_offered(self, project):
        create_entity(project, "scene", "the-attic",
                      {"title": "Attic", "sequence_id": "seq-1", "act_id": "act-1",
                       "int_ext": "INT.", "location": "attic"},
                      sections={"Content": "INT. ATTIC - DAY\n\nLEO\nHello.\n\nNORA\nHi.\n"})
        s = me.load_scene_script(project, "the-kitchen")
        assert {a["cue"]: a["scenes"] for a in s["adhoc_elsewhere"]} == {"LEO": 1, "NORA": 1}

    def test_empty_scene_opens_with_no_blocks(self, project):
        create_entity(project, "scene", "blank", {"title": "Blank", "sequence_id": "seq-1", "act_id": "act-1"})
        # create appends an undecided order; 0 is what a scene sits at when it was
        # un-placed on purpose, which is the state the warning exists for.
        edit_entity(project, "scene", "blank", {"order": 0}, "unplace")
        s = me.load_scene_script(project, "blank")
        assert s["blocks"] == [] and s["content"] == "" and not s["locked"]
        codes = {f["code"] for f in s["findings"]}
        assert {"heading_missing", "order_unset"} <= codes

    def test_a_linked_location_is_not_suggested_again(self, project):
        s = me.load_scene_script(project, "the-kitchen")
        assert s["scene"]["location"] == "kitchen"
        assert "suggested_location" not in s["heading"]

    def test_locked_scene_loads_locked(self, project):
        edit_entity(project, "scene", "the-kitchen", {"status": "locked"}, "lock")
        assert me.load_scene_script(project, "the-kitchen")["locked_reason"] == "status"


class TestSave:
    def test_edit_a_line_keeps_everything_in_sync(self, project):
        s = me.load_scene_script(project, "the-kitchen")
        blocks = [dict(b) for b in s["blocks"]]
        blocks[0]["text"] = "Mara stands at the counter, a ledger open."
        out = me.save_scene_script(project, "the-kitchen", _payload(s, blocks=blocks))
        assert "a ledger open" in out["content"]
        assert out["content"].lstrip().startswith("Mara stands at the counter, a ledger open.")
        assert out["scene"]["heading"] == "INT. KITCHEN - NIGHT"
        assert out["previous_content"] == s["content"]
        assert out["scene"]["status"] == s["scene"]["status"]      # status is not touched

    def test_changing_location_and_time_rewrites_heading_everywhere(self, project):
        s = me.load_scene_script(project, "the-kitchen")
        out = me.save_scene_script(project, "the-kitchen", _payload(
            s, heading={"mode": "structured", "int_ext": "EXT.", "location": "attic",
                        "location_text": "", "time_of_day": "DAWN"}))
        assert out["content"].lstrip().startswith("Mara stands at the counter.")
        assert out["scene"]["heading"] == "EXT. ATTIC - DAWN"
        assert out["scene"]["location"] == "attic" and out["scene"]["time_of_day"] == "DAWN"
        assert "location_no_world" in {f["code"] for f in out["findings"]}   # attic has no world

    def test_place_is_composed_into_the_heading(self, project):
        s = me.load_scene_script(project, "the-kitchen")
        out = me.save_scene_script(project, "the-kitchen", _payload(
            s, heading={"mode": "structured", "int_ext": "INT.", "location": "kitchen",
                        "place": "pantry", "time_of_day": "NIGHT"}))
        assert out["scene"]["heading"] == "INT. KITCHEN - PANTRY - NIGHT"
        assert out["scene"]["place"] == "pantry"

    def test_cast_is_script_speakers_plus_hand_added(self, project):
        s = me.load_scene_script(project, "the-kitchen")
        blocks = s["blocks"] + [{"type": "character", "text": "DETECTIVE OAK"},
                                {"type": "dialogue", "text": "Evening."}]
        out = me.save_scene_script(project, "the-kitchen", _payload(s, blocks=blocks))
        assert {c["id"] for c in out["cast"]} == {"mara-chen", "detective-oak"}
        # and an unregistered speaker never becomes a stored character
        conn = get_db(project)
        try:
            assert conn.execute("SELECT COUNT(*) FROM entities WHERE type='character'").fetchone()[0] == 2
        finally:
            conn.close()

    def test_hand_added_cast_without_a_cue(self, project):
        s = me.load_scene_script(project, "the-kitchen")
        out = me.save_scene_script(project, "the-kitchen", _payload(s, extra_cast=["detective-oak"]))
        oak = next(c for c in out["cast"] if c["id"] == "detective-oak")
        assert oak["in_script"] is False

    def test_custom_heading_is_kept_verbatim(self, project):
        s = me.load_scene_script(project, "the-kitchen")
        out = me.save_scene_script(project, "the-kitchen", _payload(
            s, heading={"mode": "custom", "text": ".SNIPER SCOPE POV", "location": "kitchen",
                        "time_of_day": "NIGHT"}))
        assert out["scene"]["forced_heading"] == ".SNIPER SCOPE POV"
        assert out["heading"]["mode"] == "custom"

    def test_stale_save_is_refused_and_nothing_is_written(self, project):
        s = me.load_scene_script(project, "the-kitchen")
        edit_entity(project, "scene", "the-kitchen",
                    {"Content": "INT. KITCHEN - NIGHT\n\nHermes was here.\n"}, "agent edit")
        blocks = [{"type": "action", "text": "Mine."}]
        with pytest.raises(me.ScriptConflict) as e:
            me.save_scene_script(project, "the-kitchen", _payload(s, blocks=blocks))
        assert e.value.current_hash != s["hash"]
        assert "Hermes was here." in me.load_scene_script(project, "the-kitchen")["content"]

    def test_locked_scene_is_refused(self, project):
        s = me.load_scene_script(project, "the-kitchen")
        edit_entity(project, "scene", "the-kitchen", {"status": "locked"}, "lock")
        s2 = me.load_scene_script(project, "the-kitchen")
        with pytest.raises(me.ScriptLocked):
            me.save_scene_script(project, "the-kitchen", _payload(s2))

    @pytest.mark.parametrize("over,msg", [
        ({"heading": {"mode": "structured", "int_ext": "INT.", "location": "ghost"}}, "Location not found"),
        ({"heading": {"mode": "structured", "int_ext": "INT.", "location": "kitchen", "time_of_day": "EVENING"}}, "time_of_day"),
        ({"heading": {"mode": "structured", "int_ext": "OUT.", "location": "kitchen"}}, "int_ext"),
        ({"heading": {"mode": "structured", "int_ext": "INT.", "location": "", "location_text": ""}}, "location"),
        ({"heading": {"mode": "custom", "text": "just words"}}, "scene heading"),
        ({"extra_cast": ["ghost"]}, "Character not found"),
        ({"blocks": [{"type": "bogus", "text": "x"}]}, r"blocks\[0\]"),
        ({"blocks": "nope"}, "list"),
    ])
    def test_invalid_payloads_are_refused_before_writing(self, project, over, msg):
        s = me.load_scene_script(project, "the-kitchen")
        with pytest.raises(me.ScriptError, match=msg):
            me.save_scene_script(project, "the-kitchen", _payload(s, **over))
        assert me.load_scene_script(project, "the-kitchen")["hash"] == s["hash"]

    def test_the_agent_sees_the_edit(self, project):
        """The point of one source of truth: the same Content the agent reads."""
        s = me.load_scene_script(project, "the-kitchen")
        me.save_scene_script(project, "the-kitchen", _payload(
            s, blocks=[{"type": "action", "text": "A new line."}]))
        from story_architect.core.db import get_screenplay_text
        assert "A new line." in get_screenplay_text(project)


class TestCheck:
    """The draft's warnings come from the same rules as a saved scene's."""

    def test_draft_findings_without_writing(self, project):
        s = me.load_scene_script(project, "the-kitchen")
        before = s["hash"]
        blocks = s["blocks"] + [{"type": "character", "text": "NORA"}, {"type": "dialogue", "text": "Hi."}]
        out = me.check_scene_script(project, "the-kitchen", {
            "blocks": blocks,
            "heading": {"mode": "structured", "int_ext": "INT.", "location": "attic", "time_of_day": ""},
            "extra_cast": ["detective-oak"]})
        codes = {f["code"] for f in out["findings"]}
        assert {"character_unregistered", "location_no_world", "time_of_day_missing"} <= codes
        assert {c["id"] for c in out["cast"]} == {"mara-chen", "detective-oak"}
        assert out["heading"]["location"] == "attic"
        assert me.load_scene_script(project, "the-kitchen")["hash"] == before   # nothing written

    def test_cues_say_which_blocks_resolved(self, project):
        s = me.load_scene_script(project, "the-kitchen")
        by_block = {c["block"]: c["id"] for c in s["cues"]}
        assert list(by_block.values()).count(None) == 1          # LEO
        assert "mara-chen" in by_block.values()

    def test_check_matches_load_for_unchanged_draft(self, project):
        s = me.load_scene_script(project, "the-kitchen")
        out = me.check_scene_script(project, "the-kitchen", {
            "blocks": s["blocks"],
            "heading": {"mode": "structured", "int_ext": "INT.", "location": "kitchen", "time_of_day": "NIGHT"},
            "extra_cast": ["mara-chen"]})
        norm = lambda fs: sorted((f["code"], f.get("block"), f.get("field")) for f in fs)
        assert norm(out["findings"]) == norm(s["findings"])
        assert out["stats"]["speaking_parts"] == s["stats"]["speaking_parts"]
