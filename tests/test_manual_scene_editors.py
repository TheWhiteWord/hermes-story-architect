"""Scene form, part two: value turns and the beat sheet.

Both are edited on the scene's own overlay. Value turns are stored on the scene; the beat
sheet is a separate record (`<scene>-beats`) the form reads and writes alongside it. These tests
read back through the same write path the agent uses, and check that what the form accepts is
what the core accepts, because a form that passes what the write path then refuses is worse
than no form."""
import json

import pytest

from story_architect.core import manual_entities as me
from story_architect.core.db import get_db
from story_architect.core.writes import create_entity, edit_entity

TURN = {"plot": "main", "value": "trust", "from": "trust", "to": "betrayal",
        "effects": [{"character": "kael", "levels": [
            {"conflict_level": "inner", "effect": "He doubts his own judgement."},
            {"conflict_level": "personal", "effect": "Mira's loyalty is in question."}]}]}


@pytest.fixture
def project(tmp_path):
    from story_architect.core.writes import create_project
    (tmp_path / "projects").mkdir()
    create_project("demo", {"name": "Demo"}, tmp_path)
    p = tmp_path / "projects" / "demo"
    for slug, name in (("kael", "Kael"), ("mira", "Mira"), ("oak", "Oak")):
        create_entity(p, "character", slug, {"name": name, "one_sentence": "x"})
    create_entity(p, "location", "kitchen", {"name": "Kitchen", "one_sentence": "x"})
    create_entity(p, "world", "gilead", {"name": "Gilead", "one_sentence": "x"})
    create_entity(p, "relationship", "kael-mira", {"name": "Kael & Mira", "characters": ["kael", "mira"],
                                                   "perspectives": {"kael": {}, "mira": {}}})
    create_entity(p, "value", "trust", {"name": "trust", "p": "trust", "c": "distrust", "cd": "betrayal", "nn": "blind faith"})
    create_entity(p, "plot", "main", {"name": "The Escape", "characters": ["kael"]})
    create_entity(p, "act", "a1", {"title": "Act One", "order": 1})
    create_entity(p, "sequence", "s1", {"title": "Seq", "act_id": "a1", "order": 1})
    create_entity(p, "scene", "sc1", {"title": "Dinner", "sequence_id": "s1", "act_id": "a1"})
    return p


def _extra(p, eid):
    conn = get_db(p)
    try:
        r = conn.execute("SELECT extra FROM entities WHERE id=?", (eid,)).fetchone()
        return json.loads(r[0]) if r and r[0] else None
    finally:
        conn.close()


def _save(p, scene_id="sc1", **changes):
    cur = me.load_entity(p, "scene", scene_id)
    return me.edit_form_entity(p, "scene", scene_id, {"base_version": cur["version"],
                                                      "values": {**cur["values"], **changes}})


def _errors(p, values, scene_id="sc1"):
    cur = me.load_entity(p, "scene", scene_id)
    return me.check_entity(p, "scene", {"values": {**cur["values"], **values}}, scene_id)


# ─── spec ────────────────────────────────────────────────────────────────────

class TestSpec:
    def test_two_tabs_and_their_editors(self):
        sp = me.form_spec("scene")
        by = {f["key"]: f for f in sp["fields"]}
        assert [t["id"] for t in sp["tabs"]] == ["turns", "beats"]
        assert by["value_turns"]["kind"] == "valueturns" and by["value_turns"]["tab"] == "turns"
        assert [l["key"] for l in by["value_turns"]["levels"]] == ["inner", "personal", "extra-personal"]
        assert by["beat_sheet"]["kind"] == "beatsheet" and by["beat_sheet"]["tab"] == "beats"
        assert by["beat_sheet"]["default"] == {"driver": "", "turning_point": "", "true_character": [], "changes": [], "beats": []}

    def test_other_types_have_no_extra_tabs(self):
        assert "tabs" not in me.form_spec("character")


# ─── value turns ─────────────────────────────────────────────────────────────

class TestValueTurns:
    def test_round_trip_reaches_the_write_path_unchanged(self, project):
        out = _save(project, value_turns=[TURN])
        assert out["values"]["value_turns"] == [TURN]
        assert _extra(project, "sc1")["value_turns"] == [TURN]          # stored exactly as the agent stores it

    def test_empty_shells_are_dropped_not_errors(self, project):
        shells = [{"plot": "", "value": "", "from": "", "to": "", "effects": []},
                  {**TURN, "effects": TURN["effects"] + [{"character": "", "levels": []},
                                                         {"character": "", "levels": [{"conflict_level": "", "effect": ""}]}]}]
        out = _save(project, value_turns=shells)
        assert out["values"]["value_turns"] == [TURN]

    def test_each_missing_piece_names_its_field(self, project):
        e = _errors(project, {"value_turns": [{"plot": "", "value": "", "from": "", "to": "", "effects": [
            {"character": "kael", "levels": [{"conflict_level": "inner", "effect": "x"}]}]}]})["errors"]
        assert e["value_turns.0.plot"] == "Choose the plot this shift belongs to."
        assert e["value_turns.0.value"] == "Choose the value that shifts."
        assert "when the scene opens" in e["value_turns.0.from"] and "when the scene closes" in e["value_turns.0.to"]

    def test_a_word_must_belong_to_the_value(self, project):
        e = _errors(project, {"value_turns": [{**TURN, "from": "serenity"}]})["errors"]
        assert e["value_turns.0.from"] == "“serenity” isn’t one of the words of “trust”."

    def test_words_match_case_insensitively_like_the_core(self, project):
        assert _errors(project, {"value_turns": [{**TURN, "value": "TRUST", "from": "Trust"}]})["ok"]

    def test_effects_are_required(self, project):
        e = _errors(project, {"value_turns": [{**TURN, "effects": []}]})["errors"]
        assert "tick at least one level" in e["value_turns.0.effects"]

    def test_only_protagonists_of_the_plot(self, project):
        bad = {**TURN, "effects": [{"character": "mira", "levels": TURN["effects"][0]["levels"]}]}
        e = _errors(project, {"value_turns": [bad]})["errors"]
        assert e["value_turns.0.effects.0.character"] == ("Mira isn’t a protagonist of “The Escape”. "
                                                          "Add them to the plot first, or remove this effect.")

    def test_a_level_needs_its_sentence_and_circles_are_unique(self, project):
        bad = {**TURN, "effects": [{"character": "kael", "levels": [
            {"conflict_level": "inner", "effect": ""}, {"conflict_level": "inner", "effect": "x"}]}]}
        e = _errors(project, {"value_turns": [bad]})["errors"]
        assert e["value_turns.0.effects.0.levels.0.effect"] == "Say in one sentence what this does to Kael at the inner level."
        assert e["value_turns.0.effects.0.levels.1.conflict_level"] == "One entry per level."

    def test_a_character_twice_and_a_card_with_no_levels(self, project):
        e = _errors(project, {"value_turns": [{**TURN, "effects": [
            {"character": "kael", "levels": TURN["effects"][0]["levels"]},
            {"character": "kael", "levels": []}]}]})["errors"]
        assert "appears twice" in e["value_turns.0.effects.1.character"]
        assert e["value_turns.0.effects.1.levels"] == "Tick at least one level."

    def test_no_shift_is_a_warning_not_an_error(self, project):
        chk = _errors(project, {"value_turns": [{**TURN, "to": "trust"}]})
        assert chk["ok"] and "ends where it started" in chk["warnings"]["value_turns.0.to"]

    def test_whatever_the_form_accepts_the_core_accepts(self, project):
        from story_architect.core.entity import validate_scene_value_turns
        turns = me.load_entity(project, "scene", "sc1")["values"]["value_turns"] + [TURN]
        assert _errors(project, {"value_turns": turns})["ok"]
        validate_scene_value_turns(project, turns)                     # raises if the core disagrees

    def test_a_stale_turn_is_explained_on_its_card_and_removing_it_unblocks_the_scene(self, project):
        """The write path re-validates stored turns on ANY scene edit, so a stale one blocks
        unrelated changes. The form says why, in place, instead of passing a check the save then fails."""
        conn = get_db(project)
        try:
            ex = _extra(project, "sc1")
            ex["value_turns"] = [{**TURN, "value": "deleted-value"}]
            conn.execute("UPDATE entities SET extra=? WHERE id='sc1'", (json.dumps(ex),))
        finally:
            conn.close()
        chk = _errors(project, {"one_sentence": "New summary."})
        assert not chk["ok"] and "isn’t a defined value" in chk["errors"]["value_turns.0.value"]
        with pytest.raises(me.EntityInvalid):
            _save(project, one_sentence="New summary.")
        assert _save(project, one_sentence="New summary.", value_turns=[])["values"]["one_sentence"] == "New summary."


# ─── beat sheet ──────────────────────────────────────────────────────────────

SHEET = {"driver": "kael", "turning_point": "The door swings open.",
         "true_character": [{"character": "kael", "dilemma": "Stay or go.", "choice_reveals": "He goes."}],
         "changes": [{"entity": "kael-mira", "change": "They now trust each other less."},
                     {"entity": "kitchen", "change": "No longer safe."}],
         "beats": [{"action": {"by": "kael", "surface": "Tries the handle.", "subtext": "testing the rules"},
                    "reaction": {"by": "kitchen", "surface": "It gives.", "subtext": ""}, "gap": "It was never locked."},
                   {"action": {"by": "", "surface": "", "subtext": ""},
                    "reaction": {"by": "mira", "surface": "Mira freezes.", "subtext": "hiding fear"}, "gap": ""}]}


class TestBeatSheet:
    def test_blank_until_there_is_a_record(self, project):
        v = me.load_entity(project, "scene", "sc1")["values"]
        assert v["beat_sheet"] == me.BLANK_SHEET and _extra(project, "sc1-beats") is None

    def test_first_save_makes_the_record(self, project):
        out = _save(project, beat_sheet=SHEET)
        assert out["values"]["beat_sheet"] == SHEET
        rec = _extra(project, "sc1-beats")
        assert rec["driver"] == "kael" and rec["beats"][0]["gap"] == "It was never locked."
        conn = get_db(project)
        try:
            assert conn.execute("SELECT parent_id FROM entities WHERE id='sc1-beats'").fetchone()[0] == "sc1"
        finally:
            conn.close()

    def test_a_scene_made_with_a_sheet_gets_its_record(self, project):
        out = me.create_form_entity(project, "scene", {"values": {"title": "Breakfast", "sequence_id": "s1",
                                                                  "beat_sheet": SHEET}})
        assert out["values"]["beat_sheet"] == SHEET and _extra(project, f"{out['id']}-beats")["driver"] == "kael"

    def test_a_scene_made_without_one_does_not_get_an_empty_record(self, project):
        out = me.create_form_entity(project, "scene", {"values": {"title": "Breakfast", "sequence_id": "s1"}})
        assert _extra(project, f"{out['id']}-beats") is None

    def test_second_save_edits_only_what_changed(self, project, monkeypatch):
        _save(project, beat_sheet=SHEET)
        sent = []
        from story_architect.core import writes
        real = writes.edit_entity
        monkeypatch.setattr(writes, "edit_entity", lambda p, t, i, d, s: sent.append((t, i, d)) or real(p, t, i, d, s))
        cur = me.load_entity(project, "scene", "sc1")["values"]["beat_sheet"]
        cur["turning_point"] = "The door swings wide."
        _save(project, beat_sheet=cur)
        assert sent == [("scene_beats", "sc1-beats", {"turning_point": "The door swings wide."})]

    def test_a_scene_only_edit_leaves_the_record_alone(self, project, monkeypatch):
        _save(project, beat_sheet=SHEET)
        sent = []
        from story_architect.core import writes
        real = writes.edit_entity
        monkeypatch.setattr(writes, "edit_entity", lambda p, t, i, d, s: sent.append(t) or real(p, t, i, d, s))
        _save(project, one_sentence="Only the scene.")
        assert sent == ["scene"]

    def test_there_is_one_objective_and_it_is_the_scenes(self, project):
        create_entity(project, "scene_beats", "sc1-beats", {"scene": "sc1", "scene_objective": "From the beats"})
        cur = me.load_entity(project, "scene", "sc1")["values"]
        assert cur["scene_objective"] == "From the beats"               # the same merge the dashboard shows
        assert "scene_objective" not in cur["beat_sheet"]
        _save(project, scene_objective="Edited here")
        assert _extra(project, "sc1")["scene_objective"] == "Edited here"
        assert _extra(project, "sc1-beats")["scene_objective"] == "From the beats"    # the record is not rewritten

    def test_empty_entries_are_dropped(self, project):
        out = _save(project, beat_sheet={**SHEET, "true_character": [{"character": "", "dilemma": "", "choice_reveals": ""}],
                                         "changes": [], "beats": [SHEET["beats"][0], {"action": {}, "reaction": {}, "gap": ""}]})
        assert out["values"]["beat_sheet"]["true_character"] == [] and len(out["values"]["beat_sheet"]["beats"]) == 1

    def test_every_reference_names_its_field(self, project):
        bad = {**SHEET, "driver": "ghost",
               "true_character": [{"character": "", "dilemma": "d", "choice_reveals": ""}],
               "changes": [{"entity": "nowhere", "change": "x"}, {"entity": "kael", "change": ""}],
               "beats": [{"action": {"by": "kael-mira", "surface": "s", "subtext": ""}, "reaction": {"by": "", "surface": "", "subtext": ""}, "gap": ""},
                         {"action": {"by": "kael", "surface": "", "subtext": ""}, "reaction": {"by": "", "surface": "", "subtext": ""}, "gap": ""}]}
        e = _errors(project, {"beat_sheet": bad})["errors"]
        assert "ghost" in e["beat_sheet.driver"]
        assert e["beat_sheet.true_character.0.character"] == "Choose who faces the choice."
        assert "nowhere" in e["beat_sheet.changes.0.entity"]
        assert e["beat_sheet.changes.1.change"] == "Say what is different for Kael now — the new state, not the event."
        assert "isn’t a character, location or world" in e["beat_sheet.beats.0.action.by"]     # a relationship cannot act
        assert e["beat_sheet.beats.1"].startswith("A beat needs something")

    def test_a_relationship_can_be_what_changed_but_not_who_acts(self, project):
        ok = {**SHEET, "beats": []}
        assert _errors(project, {"beat_sheet": ok})["ok"]                # changes[].entity = a relationship: fine

    def test_whatever_the_form_accepts_the_core_accepts(self, project):
        from story_architect.core.entity import validate_scene_beats
        assert _errors(project, {"beat_sheet": SHEET})["ok"]
        _save(project, beat_sheet=SHEET)                                # the write path ran its own validation

    def test_the_agent_changing_the_record_is_a_conflict(self, project):
        _save(project, beat_sheet=SHEET)
        cur = me.load_entity(project, "scene", "sc1")
        edit_entity(project, "scene_beats", "sc1-beats", {"turning_point": "Agent rewrote this."}, "agent")
        with pytest.raises(me.EntityConflict):
            me.edit_form_entity(project, "scene", "sc1", {"base_version": cur["version"],
                                                          "values": {**cur["values"], "one_sentence": "x"}})
        assert me.load_entity(project, "scene", "sc1")["values"]["beat_sheet"]["turning_point"] == "Agent rewrote this."

    def test_scene_saved_but_beats_failed_says_which(self, project, monkeypatch):
        from story_architect.core import writes
        real = writes.create_entity
        def boom(p, t, i, fm, sec=None):
            if t == "scene_beats":
                raise ValueError("beats exploded")
            return real(p, t, i, fm, sec or {})
        monkeypatch.setattr(writes, "create_entity", boom)
        cur = me.load_entity(project, "scene", "sc1")
        with pytest.raises(me.EntityInvalid) as e:
            me.edit_form_entity(project, "scene", "sc1", {"base_version": cur["version"], "values": {
                **cur["values"], "one_sentence": "Saved.", "beat_sheet": SHEET}})
        assert "The scene was saved, but the beats were not: beats exploded" in e.value.errors["_form"]
        assert me.load_entity(project, "scene", "sc1")["values"]["one_sentence"] == "Saved."

    def test_deleting_the_scene_takes_its_beats_and_says_so(self, project):
        _save(project, beat_sheet=SHEET)
        prev = me.delete_preview(project, "scene", "sc1")
        assert [c["id"] for c in prev["also_deleted"]] == ["sc1-beats"]
        me.delete_form_entity(project, "scene", "sc1")
        with pytest.raises(me.EntityNotFound):
            me.load_entity(project, "scene", "sc1")


# ─── over HTTP ───────────────────────────────────────────────────────────────

class TestHttp:
    def test_turns_and_beats_round_trip(self, project, monkeypatch):
        from fastapi.testclient import TestClient
        from story_architect.app.config import Config
        from story_architect.app.server import create_app
        monkeypatch.setattr("story_architect.app.token.load_api_key", lambda: "k")
        c = TestClient(create_app(Config(root=project.parent.parent, port=8731)), base_url="http://127.0.0.1:8731")
        c.headers.update({"X-Story-Architect": "1"})
        d = c.get("/api/projects/demo/entities/scene/sc1/form").json()
        r = c.put("/api/projects/demo/entities/scene/sc1", json={"base_version": d["version"], "values": {
            **d["values"], "value_turns": [TURN], "beat_sheet": SHEET}})
        assert r.status_code == 200 and r.json()["values"]["beat_sheet"]["driver"] == "kael"
        bad = {**r.json()["values"], "value_turns": [{**TURN, "from": "serenity"}]}
        r2 = c.put("/api/projects/demo/entities/scene/sc1", json={"base_version": r.json()["version"], "values": bad})
        assert r2.status_code == 422 and "value_turns.0.from" in r2.json()["error"]["errors"]
