"""Entity form (acts, sequences, scenes) and Reorder.

Moves are checked against what the database holds afterwards — the scene's parent,
its denormalised `act_id`, and its order — because those three agreeing with each
other is the whole point of doing a move through one place.
"""
import json

import pytest

from story_architect.core import manual_entities as me
from story_architect.core import manual_structure as ms
from story_architect.core.db import get_db
from story_architect.core.writes import create_entity, edit_entity


@pytest.fixture
def project(tmp_path):
    from story_architect.core.writes import create_project
    (tmp_path / "projects").mkdir()
    create_project("demo", {"name": "Demo"}, tmp_path)
    p = tmp_path / "projects" / "demo"
    create_entity(p, "plot", "main", {"name": "Main"})
    create_entity(p, "act", "a1", {"title": "Act One", "order": 1})
    create_entity(p, "act", "a2", {"title": "Act Two", "order": 2})
    for sid, act, order in (("s1", "a1", 1), ("s2", "a1", 2), ("s3", "a2", 1)):
        create_entity(p, "sequence", sid, {"title": f"Seq {sid}", "act_id": act, "order": order})
    for sc, seq, act in (("sc1", "s1", "a1"), ("sc2", "s1", "a1"), ("sc3", "s1", "a1"), ("sc4", "s2", "a1")):
        create_entity(p, "scene", sc, {"title": f"Scene {sc}", "sequence_id": seq, "act_id": act})
    return p


def _scene(p, sid):
    conn = get_db(p)
    try:
        r = conn.execute("SELECT parent_id, order_key, extra FROM entities WHERE id=?", (sid,)).fetchone()
        return {"seq": r[0], "order": r[1], "act": json.loads(r[2]).get("act_id")}
    finally:
        conn.close()


def _ids(tree):
    return {a["id"]: {q["id"]: [s["id"] for s in q["scenes"]] for q in a["sequences"]} for a in tree["acts"]}


def _target(p, mutate):
    t = ms.load_tree(p)
    shape = {"base_version": t["version"],
             "acts": [{"id": a["id"], "sequences": [{"id": q["id"], "scenes": [s["id"] for s in q["scenes"]]}
                                                    for q in a["sequences"]]} for a in t["acts"]]}
    mutate(shape)
    return shape


def _seq(shape, sid):
    return next(q for a in shape["acts"] for q in a["sequences"] if q["id"] == sid)


# ─── forms ───────────────────────────────────────────────────────────────────

class TestSpec:
    def test_scene(self):
        sp = me.form_spec("scene")
        by = {f["key"]: f for f in sp["fields"]}
        assert "order" not in by and "act_id" not in by            # Reorder's, not the form's
        assert by["sequence_id"]["required"] and by["sequence_id"]["ref"] == "sequence"
        assert all(by[k]["kind"] == "linked" for k in ("heading", "location", "time_of_day", "characters"))
        assert by["plot_roles"]["kind"] == "repeater" and by["value_turns"]["kind"] == "valueturns"
        assert "turning_point" not in by and "scene_beats" not in by          # they live in the Beats tab
        assert "Content" not in sp["sections"] and sp["script_link"]
        assert [f["key"] for f in sp["fields"]][:3] == ["title", "sequence_id", "status"]

    def test_sequence_and_act(self):
        assert {f["key"] for f in me.form_spec("sequence")["fields"]} >= {"title", "act_id", "primary_plot", "purpose"}
        assert "order" not in {f["key"] for f in me.form_spec("act")["fields"]}


class TestCreate:
    def test_acts_are_numbered_in_turn(self, project):
        out = me.create_form_entity(project, "act", {"values": {"title": "Act Three"}})
        conn = get_db(project)
        try:
            assert conn.execute("SELECT order_key FROM entities WHERE id=?", (out["id"],)).fetchone()[0] == 3
        finally:
            conn.close()

    def test_sequence_needs_an_act(self, project):
        with pytest.raises(me.EntityInvalid) as e:
            me.create_form_entity(project, "sequence", {"values": {"title": "X"}})
        assert "Choose the act" in e.value.errors["act_id"]
        out = me.create_form_entity(project, "sequence", {"values": {"title": "X", "act_id": "a2", "primary_plot": "main"}})
        assert out["values"]["act_id"] == "a2" and out["values"]["primary_plot"] == "main"

    def test_no_acts_yet_says_so(self, tmp_path):
        from story_architect.core.writes import create_project
        (tmp_path / "projects").mkdir()
        create_project("empty", {"name": "E"}, tmp_path)
        with pytest.raises(me.EntityInvalid) as e:
            me.create_form_entity(tmp_path / "projects" / "empty", "sequence", {"values": {"title": "X"}})
        assert "no acts yet" in e.value.errors["act_id"]

    def test_scene_takes_its_acts_from_its_sequence(self, project):
        out = me.create_form_entity(project, "scene", {"values": {"title": "New", "sequence_id": "s3"}})
        assert _scene(project, out["id"]) == {"seq": "s3", "order": 1, "act": "a2"}

    def test_scene_needs_a_sequence(self, project):
        with pytest.raises(me.EntityInvalid) as e:
            me.create_form_entity(project, "scene", {"values": {"title": "New"}})
        assert "Choose the sequence" in e.value.errors["sequence_id"]

    def test_unknown_sequence_is_named(self, project):
        with pytest.raises(me.EntityInvalid) as e:
            me.create_form_entity(project, "scene", {"values": {"title": "New", "sequence_id": "nope"}})
        assert "nope" in e.value.errors["sequence_id"]


class TestScene:
    def test_plot_roles_round_trip(self, project):
        out = me.create_form_entity(project, "scene", {"values": {
            "title": "Dinner", "sequence_id": "s1",
            "plot_roles": [{"plot": "main", "role": "crisis", "description": "Boom"}, {"plot": "", "role": "", "description": ""}]}})
        assert out["values"]["plot_roles"] == [{"plot": "main", "role": "crisis", "description": "Boom"}]   # blank card dropped
        v = out["values"]
        v["plot_roles"][0]["description"] = "Bigger boom"
        got = me.edit_form_entity(project, "scene", out["id"], {"base_version": out["version"], "values": v})
        assert got["values"]["plot_roles"][0]["description"] == "Bigger boom"
        v = got["values"]; v["plot_roles"] = []
        got = me.edit_form_entity(project, "scene", out["id"], {"base_version": got["version"], "values": v})
        assert got["values"]["plot_roles"] == []

    def test_card_errors_are_keyed_to_the_card(self, project):
        chk = me.check_entity(project, "scene", {"values": {"title": "X", "sequence_id": "s1", "plot_roles": [
            {"plot": "main", "role": "crisis"}, {"plot": "main", "role": "climax"},
            {"plot": "ghost", "role": "setup"}, {"plot": "main"}]}})
        e = chk["errors"]
        assert "one role per plot" in e["plot_roles.1.plot"]
        assert "ghost" in e["plot_roles.2.plot"]
        assert e["plot_roles.3.role"] == "Choose a role."

    def test_transition_scene_cannot_have_plot_roles(self, project):
        chk = me.check_entity(project, "scene", {"values": {
            "title": "X", "sequence_id": "s1", "dramatic_role": "transition",
            "plot_roles": [{"plot": "main", "role": "setup"}]}})
        assert "serves no plot" in chk["errors"]["dramatic_role"]

    def test_position_cannot_change_from_the_form(self, project):
        cur = me.load_entity(project, "scene", "sc1")
        v = {**cur["values"], "sequence_id": "s3"}
        with pytest.raises(me.EntityInvalid) as e:
            me.edit_form_entity(project, "scene", "sc1", {"base_version": cur["version"], "values": v})
        assert "Reorder" in e.value.errors["sequence_id"]
        assert me.check_entity(project, "scene", {"values": v}, "sc1")["errors"]["sequence_id"]
        assert _scene(project, "sc1")["seq"] == "s1"

    def test_script_fields_are_shown_not_written(self, project):
        create_entity(project, "location", "kitchen", {"name": "Kitchen", "one_sentence": "x"})
        create_entity(project, "character", "kael", {"name": "Kael", "one_sentence": "x"})
        edit_entity(project, "scene", "sc1", {"heading": "INT. KITCHEN - DAY", "time_of_day": "DAY",
                                              "location": "kitchen", "characters": ["kael"]}, "t")
        c = me.load_entity(project, "scene", "sc1")["computed"]
        assert c["heading"][0]["display"] == "INT. KITCHEN - DAY" and c["location"][0]["display"] == "Kitchen"
        assert c["time_of_day"][0]["display"] == "DAY" and c["characters"][0]["display"] == "Kael"
        cur = me.load_entity(project, "scene", "sc1")
        assert "heading" not in cur["values"]
        out = me.edit_form_entity(project, "scene", "sc1", {"base_version": cur["version"], "values": {
            **cur["values"], "heading": "HACKED", "location": "x", "characters": [], "one_sentence": "s"}})
        assert out["computed"]["heading"][0]["display"] == "INT. KITCHEN - DAY"       # untouched
        assert out["computed"]["characters"][0]["display"] == "Kael"

    def test_the_script_is_never_touched(self, project):
        edit_entity(project, "scene", "sc1", {"Content": "INT. KITCHEN - DAY\n\nKael waits."}, "t")
        cur = me.load_entity(project, "scene", "sc1")
        assert "Content" not in cur["sections"]
        me.edit_form_entity(project, "scene", "sc1", {"base_version": cur["version"], "values": {
            **cur["values"], "one_sentence": "Waiting."}, "sections": {"Objective": "Wait."}})
        conn = get_db(project)
        try:
            body = conn.execute("SELECT body FROM sections WHERE entity_id='sc1' AND heading='Content'").fetchone()[0]
        finally:
            conn.close()
        assert "Kael waits." in body

    def test_a_legacy_value_does_not_block_check_either(self, project):
        """`check` is what 'Review changes' calls — it must hold the person to the same bar as save."""
        create_entity(project, "plot", "old", {"name": "Old"})
        conn = get_db(project)
        try:
            ex = json.loads(conn.execute("SELECT extra FROM entities WHERE id='old'").fetchone()[0])
            ex["value_arc"] = "Legacy"
            conn.execute("UPDATE entities SET extra=? WHERE id='old'", (json.dumps(ex),))
        finally:
            conn.close()
        cur = me.load_entity(project, "plot", "old")
        assert me.check_entity(project, "plot", {"values": cur["values"]}, "old")["ok"]


class TestDelete:
    def test_sequence_with_scenes_is_blocked_with_a_way_out(self, project):
        prev = me.delete_preview(project, "sequence", "s1")
        assert not prev["can_delete"] and "3 scenes" in prev["blockers"][0] and "Reorder" in prev["blockers"][0]
        one = me.delete_preview(project, "sequence", "s2")
        assert "Move or delete it first" in one["blockers"][0]

    def test_empty_sequence_deletes(self, project):
        me.delete_form_entity(project, "sequence", "s3")
        with pytest.raises(me.EntityNotFound):
            me.load_entity(project, "sequence", "s3")

    def test_act_with_sequences_is_blocked(self, project):
        prev = me.delete_preview(project, "act", "a1")
        assert not prev["can_delete"] and "2 sequences" in prev["blockers"][0]

    def test_scene_delete_warns_about_its_script_and_beats(self, project):
        edit_entity(project, "scene", "sc1", {"Content": "INT. ROOM - DAY\n\nSomething happens."}, "t")
        create_entity(project, "scene_beats", "sc1-beats", {"scene": "sc1"})
        prev = me.delete_preview(project, "scene", "sc1")
        assert prev["can_delete"] and "script" in prev["effects"][0] and "characters" in prev["effects"][0]
        assert [c["label"] for c in prev["also_deleted"]] and prev["also_deleted"][0]["id"] == "sc1-beats"
        me.delete_form_entity(project, "scene", "sc1")
        with pytest.raises(me.EntityNotFound):
            me.load_entity(project, "scene", "sc1")


# ─── reorder ─────────────────────────────────────────────────────────────────

class TestTree:
    def test_shape_and_version(self, project):
        t = ms.load_tree(project)
        assert _ids(t) == {"a1": {"s1": ["sc1", "sc2", "sc3"], "s2": ["sc4"]}, "a2": {"s3": []}}
        assert t["unassigned"] == [] and t["version"] == ms.load_tree(project)["version"]
        edit_entity(project, "scene", "sc4", {"sequence_id": "s1"}, "t")
        assert ms.load_tree(project)["version"] != t["version"]


class TestPlan:
    def test_no_change_no_moves(self, project):
        p = ms.plan(project, _target(project, lambda s: None))
        assert p["unchanged"] and p["changes"] == []

    def test_a_jump_lists_only_the_item_that_moved(self, project):
        def mut(s): _seq(s, "s1")["scenes"] = ["sc2", "sc3", "sc1"]          # sc1 jumps from 1st to 3rd
        p = ms.plan(project, _target(project, mut))
        assert [c["id"] for c in p["changes"]] == ["sc1"]
        assert p["changes"][0]["text"] == "Move scene “Scene sc1” from Act One › Seq s1 · 1 to Act One › Seq s1 · 3"

    def test_a_move_across_acts_reads_as_a_move(self, project):
        def mut(s):
            _seq(s, "s1")["scenes"].remove("sc2"); _seq(s, "s3")["scenes"].append("sc2")
        p = ms.plan(project, _target(project, mut))
        assert p["changes"][0]["text"] == "Move scene “Scene sc2” from Act One › Seq s1 · 2 to Act Two › Seq s3 · 1"

    def test_a_sequence_move_says_its_scenes_go_with_it(self, project):
        def mut(s):
            q = _seq(s, "s1"); s["acts"][0]["sequences"].remove(q); s["acts"][1]["sequences"].append(q)
        p = ms.plan(project, _target(project, mut))
        assert p["changes"][0]["type"] == "sequence" and "its 3 scenes move with it" in p["changes"][0]["text"]
        assert len(p["changes"]) == 1                    # the scenes inside are not listed as moves

    def test_stale_version_is_refused(self, project):
        shape = _target(project, lambda s: None)
        edit_entity(project, "scene", "sc4", {"sequence_id": "s1"}, "t")
        with pytest.raises(ms.StructureConflict):
            ms.plan(project, shape)

    @pytest.mark.parametrize("mut,msg", [
        (lambda s: _seq(s, "s2")["scenes"].append("sc1"), "appears in two places"),
        (lambda s: _seq(s, "s1")["scenes"].remove("sc2"), "can't be taken out"),
        (lambda s: _seq(s, "s2")["scenes"].append("ghost"), "Not found"),
        (lambda s: s["acts"].pop(), "not added or removed"),
    ])
    def test_invalid_shapes(self, project, mut, msg):
        with pytest.raises(ms.StructureError) as e:
            ms.plan(project, _target(project, mut))
        assert msg in str(e.value)


class TestApply:
    def test_reorder_within_a_sequence(self, project):
        def mut(s): _seq(s, "s1")["scenes"] = ["sc3", "sc1", "sc2"]
        out = ms.apply(project, _target(project, mut))
        assert _ids(out["tree"])["a1"]["s1"] == ["sc3", "sc1", "sc2"] and out["applied"] == 1
        assert [_scene(project, s)["order"] for s in ("sc3", "sc1", "sc2")] == [1, 2, 3]

    def test_scene_into_another_act_updates_all_three(self, project):
        def mut(s):
            _seq(s, "s1")["scenes"].remove("sc2"); _seq(s, "s3")["scenes"].append("sc2")
        ms.apply(project, _target(project, mut))
        assert _scene(project, "sc2") == {"seq": "s3", "order": 1, "act": "a2"}       # parent, order AND act
        assert _ids(ms.load_tree(project))["a1"]["s1"] == ["sc1", "sc3"]
        assert [_scene(project, s)["order"] for s in ("sc1", "sc3")] == [1, 2]        # the gap closed

    def test_sequence_into_another_act_carries_its_scenes_act(self, project):
        def mut(s):
            q = _seq(s, "s1"); s["acts"][0]["sequences"].remove(q); s["acts"][1]["sequences"].insert(0, q)
        ms.apply(project, _target(project, mut))
        assert _ids(ms.load_tree(project)) == {"a1": {"s2": ["sc4"]}, "a2": {"s1": ["sc1", "sc2", "sc3"], "s3": []}}
        assert all(_scene(project, s)["act"] == "a2" for s in ("sc1", "sc2", "sc3"))  # the denormalised act followed
        assert _scene(project, "sc4")["act"] == "a1"                                   # a bystander did not

    def test_move_into_an_empty_sequence(self, project):
        ms.apply(project, _target(project, lambda s: (_seq(s, "s2")["scenes"].clear(), _seq(s, "s3")["scenes"].append("sc4"))))
        assert _scene(project, "sc4") == {"seq": "s3", "order": 1, "act": "a2"}

    def test_acts_swap(self, project):
        out = ms.apply(project, _target(project, lambda s: s["acts"].reverse()))
        assert [a["id"] for a in out["tree"]["acts"]] == ["a2", "a1"]

    def test_unassigned_scene_can_be_placed(self, project):
        conn = get_db(project)
        try:
            conn.execute("UPDATE entities SET parent_id='' WHERE id='sc4'")
        finally:
            conn.close()
        assert [s["id"] for s in ms.load_tree(project)["unassigned"]] == ["sc4"]
        ms.apply(project, _target(project, lambda s: _seq(s, "s3")["scenes"].append("sc4")))
        assert _scene(project, "sc4")["seq"] == "s3" and ms.load_tree(project)["unassigned"] == []

    def test_script_text_survives_a_move(self, project):
        edit_entity(project, "scene", "sc2", {"Content": "INT. ROOM - DAY\n\nKeep me."}, "t")
        ms.apply(project, _target(project, lambda s: (_seq(s, "s1")["scenes"].remove("sc2"), _seq(s, "s3")["scenes"].append("sc2"))))
        conn = get_db(project)
        try:
            assert "Keep me." in conn.execute("SELECT body FROM sections WHERE entity_id='sc2' AND heading='Content'").fetchone()[0]
        finally:
            conn.close()

    def test_applying_nothing_writes_nothing(self, project):
        before = ms.load_tree(project)["version"]
        assert ms.apply(project, _target(project, lambda s: None))["applied"] == 0
        assert ms.load_tree(project)["version"] == before


# ─── over HTTP ───────────────────────────────────────────────────────────────

class TestHttp:
    @pytest.fixture
    def client(self, project, monkeypatch):
        from fastapi.testclient import TestClient
        from story_architect.app.config import Config
        from story_architect.app.server import create_app
        monkeypatch.setattr("story_architect.app.token.load_api_key", lambda: "k")
        c = TestClient(create_app(Config(root=project.parent.parent, port=8731)), base_url="http://127.0.0.1:8731")
        c.headers.update({"X-Story-Architect": "1"})
        return c

    def test_plan_apply_and_refusals(self, client):
        t = client.get("/api/projects/demo/structure").json()
        shape = {"base_version": t["version"], "acts": [
            {"id": a["id"], "sequences": [{"id": q["id"], "scenes": [s["id"] for s in q["scenes"]]} for q in a["sequences"]]}
            for a in t["acts"]]}
        shape["acts"][0]["sequences"][0]["scenes"].reverse()
        plan = client.post("/api/projects/demo/structure/plan", json=shape).json()
        assert not plan["unchanged"] and plan["changes"][0]["text"].startswith("Move scene")
        r = client.post("/api/projects/demo/structure/apply", json=shape)
        assert r.status_code == 200 and [s["id"] for s in r.json()["tree"]["acts"][0]["sequences"][0]["scenes"]] == ["sc3", "sc2", "sc1"]
        assert client.post("/api/projects/demo/structure/apply", json=shape).status_code == 409      # now stale
        bad = {**shape, "base_version": r.json()["version"], "acts": shape["acts"][:1]}
        assert client.post("/api/projects/demo/structure/apply", json=bad).status_code == 422
        assert client.post("/api/projects/demo/structure/apply", json=shape).headers  # still responds
        assert client.get("/api/projects/nope/structure").status_code == 404

    def test_writes_need_the_custom_header(self, client):
        del client.headers["X-Story-Architect"]
        assert client.post("/api/projects/demo/structure/apply", json={}).status_code == 403
