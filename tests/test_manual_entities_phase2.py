"""Entity form, phase 2: plots, relationships and the project record."""
import json

import pytest

from story_architect.core import manual_entities as me
from story_architect.core.db import get_db
from story_architect.core.writes import create_entity, edit_entity


@pytest.fixture
def project(tmp_path):
    from story_architect.core.writes import create_project
    root = tmp_path
    (root / "projects").mkdir()
    create_project("demo", {"name": "Demo", "logline": "A test"}, root)
    p = root / "projects" / "demo"
    for slug, name in [("kael", "Kael"), ("mira", "Mira"), ("oak", "Oak")]:
        create_entity(p, "character", slug, {"name": name, "one_sentence": "x"})
    return p


def _scene_with_role(p, plot="main", role="setup", note="The door opens"):
    create_entity(p, "act", "a1", {"title": "A"})
    create_entity(p, "sequence", "s1", {"title": "S", "act_id": "a1"})
    create_entity(p, "scene", "sc1", {"title": "Dinner", "sequence_id": "s1", "act_id": "a1",
                                      "plot_roles": [{"plot": plot, "role": role, "description": note}]})


def _extra(p, eid):
    conn = get_db(p)
    try:
        return json.loads(conn.execute("SELECT extra FROM entities WHERE id=?", (eid,)).fetchone()[0])
    finally:
        conn.close()


# ─── plot ────────────────────────────────────────────────────────────────────

class TestPlot:
    def test_spec(self):
        by = {f["key"]: f for f in me.form_spec("plot")["fields"]}
        assert by["characters"]["kind"] == "reflist" and by["characters"]["ref"] == "character"
        assert by["plot_type"]["show_if"] == {"plot_scope": "sub"}
        assert by["status"]["kind"] == "select" and not by["status"]["allow_blank"]
        assert by["value_arc"]["allow_blank"]
        assert by["climax"]["kind"] == "computed" and "plot roles" in by["climax"]["hint"]

    def test_create_and_read_back(self, project):
        out = me.create_form_entity(project, "plot", {"values": {
            "name": "Escape", "one_sentence": "Get out.", "characters": ["kael"],
            "plot_scope": "main", "value_arc": "Education"}})
        assert out["id"] == "escape" and out["values"]["characters"] == ["kael"]
        assert out["values"]["status"] == "active"

    def test_type_only_applies_to_subplots(self, project):
        sub = me.create_form_entity(project, "plot", {"values": {
            "name": "Rival", "plot_scope": "sub", "plot_type": "Resonant"}})
        assert sub["values"]["plot_type"] == "Resonant"
        main = me.create_form_entity(project, "plot", {"values": {
            "name": "Spine", "plot_scope": "main", "plot_type": "Resonant"}})
        assert main["values"]["plot_type"] == ""            # hidden -> reset, not left behind

    def test_switching_to_main_clears_the_type(self, project):
        sub = me.create_form_entity(project, "plot", {"values": {
            "name": "Rival", "plot_scope": "sub", "plot_type": "Setup"}})
        out = me.edit_form_entity(project, "plot", "rival", {
            "base_version": sub["version"], "values": {**sub["values"], "plot_scope": "main"}})
        assert out["values"]["plot_type"] == "" and _extra(project, "rival")["plot_type"] == ""

    def test_subplot_without_a_kind_is_a_warning_not_an_error(self, project):
        chk = me.check_entity(project, "plot", {"values": {"name": "Rival", "plot_scope": "sub"}})
        assert chk["ok"] and "plot_type" in chk["warnings"]

    def test_unknown_protagonist_is_named(self, project):
        with pytest.raises(me.EntityInvalid) as e:
            me.create_form_entity(project, "plot", {"values": {"name": "X", "characters": ["nobody"]}})
        assert "nobody" in e.value.errors["characters"]

    def test_derived_roles_show_scene_and_note(self, project):
        create_entity(project, "plot", "main", {"name": "Main", "plot_scope": "main"})
        _scene_with_role(project)
        c = me.load_entity(project, "plot", "main")["computed"]
        assert c["setups"][0]["display"] == "Dinner — The door opens"
        assert c["crisis"] == []

    def test_a_stored_legacy_value_does_not_block_an_unrelated_edit(self, project):
        out = me.create_form_entity(project, "plot", {"values": {"name": "Old"}})
        conn = get_db(project)
        try:
            ex = json.loads(conn.execute("SELECT extra FROM entities WHERE id='old'").fetchone()[0])
            ex["value_arc"] = "Legacy"
            conn.execute("UPDATE entities SET extra=? WHERE id='old'", (json.dumps(ex),))
        finally:
            conn.close()
        cur = me.load_entity(project, "plot", "old")
        got = me.edit_form_entity(project, "plot", "old", {
            "base_version": cur["version"], "values": {**cur["values"], "one_sentence": "now with a summary"}})
        assert got["values"]["one_sentence"] == "now with a summary"
        # …but choosing a bad one is still refused
        with pytest.raises(me.EntityInvalid):
            me.edit_form_entity(project, "plot", "old", {
                "base_version": got["version"], "values": {**got["values"], "value_arc": "Nonsense"}})

    def test_delete_reports_scene_roles(self, project):
        create_entity(project, "plot", "main", {"name": "Main"})
        _scene_with_role(project)
        prev = me.delete_preview(project, "plot", "main")
        assert prev["can_delete"] and any("Dinner" in e and "plot role" in e for e in prev["effects"])
        me.delete_form_entity(project, "plot", "main")
        assert me.load_entity  # still importable; the plot is gone:
        with pytest.raises(me.EntityNotFound):
            me.load_entity(project, "plot", "main")

    def test_plot_named_in_value_turns_blocks_the_delete(self, project):
        create_entity(project, "value", "trust", {"name": "trust", "p": "trust", "c": "distrust",
                                                  "cd": "betrayal", "nn": "blind faith"})
        create_entity(project, "plot", "main", {"name": "Main", "characters": ["kael"]})
        create_entity(project, "act", "a1", {"title": "A"})
        create_entity(project, "sequence", "s1", {"title": "S", "act_id": "a1"})
        create_entity(project, "scene", "sc1", {
            "title": "Dinner", "sequence_id": "s1", "act_id": "a1",
            "value_turns": [{"plot": "main", "value": "trust", "from": "trust", "to": "betrayal",
                             "effects": [{"character": "kael",
                                          "levels": [{"conflict_level": "inner", "effect": "x"}]}]}]})
        prev = me.delete_preview(project, "plot", "main")
        assert not prev["can_delete"] and "Main" in prev["blockers"][0] and "Dinner" in prev["blockers"][0]


# ─── relationship ────────────────────────────────────────────────────────────

REL = {"name": "Kael & Mira", "characters": ["kael", "mira"],
       "perspectives": {"kael": {"label": "Friend", "type": "family", "strength": 0.9},
                        "mira": {"label": "Watcher"}}}


class TestRelationship:
    def test_spec(self):
        by = {f["key"]: f for f in me.form_spec("relationship")["fields"]}
        assert by["characters"]["kind"] == "reflist" and by["characters"]["count"] == 2
        assert by["perspectives"]["kind"] == "perspectives" and by["perspectives"]["keyed_by"] == "characters"
        assert {f["key"] for f in by["perspectives"]["fields"]} == {"label", "feeling", "type", "strength", "secret"}
        assert [f["key"] for f in me.form_spec("relationship")["fields"]][:4] == \
            ["name", "characters", "perspectives", "status"]

    def test_create_stores_only_what_was_filled_but_a_key_per_character(self, project):
        out = me.create_form_entity(project, "relationship", {"values": REL})
        assert out["id"] == "kael-mira"
        stored = _extra(project, "kael-mira")["perspectives"]
        assert stored["kael"] == {"label": "Friend", "type": "family", "strength": 0.9}
        assert stored["mira"] == {"label": "Watcher"}
        # a character with nothing filled in still has a key
        out = me.create_form_entity(project, "relationship", {"values": {
            "name": "Oak & Kael", "characters": ["oak", "kael"]}})
        assert set(_extra(project, out["id"])["perspectives"]) == {"oak", "kael"}

    def test_two_different_characters_are_required(self, project):
        for bad in ([], ["kael"], ["kael", "kael"], ["kael", "mira", "oak"]):
            with pytest.raises(me.EntityInvalid) as e:
                me.create_form_entity(project, "relationship", {"values": {"name": "X", "characters": bad}})
            assert e.value.errors["characters"] == "Pick two different characters."

    def test_unknown_character(self, project):
        with pytest.raises(me.EntityInvalid) as e:
            me.create_form_entity(project, "relationship", {"values": {"name": "X", "characters": ["kael", "zed"]}})
        assert "zed" in e.value.errors["characters"]

    def test_same_pair_twice_is_a_warning(self, project):
        me.create_form_entity(project, "relationship", {"values": REL})
        chk = me.check_entity(project, "relationship", {"values": {**REL, "name": "Again", "characters": ["mira", "kael"]}})
        assert chk["ok"] and "already have a relationship" in chk["warnings"]["characters"]

    def test_strength_range_is_keyed_to_the_card_field(self, project):
        bad = {**REL, "perspectives": {"kael": {"strength": 3}, "mira": {}}}
        with pytest.raises(me.EntityInvalid) as e:
            me.create_form_entity(project, "relationship", {"values": bad})
        assert "perspectives.kael.strength" in e.value.errors

    def test_untouched_form_is_a_no_op(self, project):
        out = me.create_form_entity(project, "relationship", {"values": REL})
        again = me.edit_form_entity(project, "relationship", "kael-mira",
                                    {"base_version": out["version"], "values": out["values"]})
        assert again["unchanged"]

    def test_edit_one_perspective_leaves_the_other(self, project):
        out = me.create_form_entity(project, "relationship", {"values": REL})
        v = out["values"]
        v["perspectives"]["mira"].update(strength=-0.3, secret=True)
        got = me.edit_form_entity(project, "relationship", "kael-mira", {"base_version": out["version"], "values": v})
        assert _extra(project, "kael-mira")["perspectives"]["mira"] == {"label": "Watcher", "strength": -0.3, "secret": True}
        assert _extra(project, "kael-mira")["perspectives"]["kael"]["label"] == "Friend"
        assert got["values"]["perspectives"]["mira"]["secret"] is True

    def test_swapping_a_character_rekeys_the_perspectives(self, project):
        out = me.create_form_entity(project, "relationship", {"values": REL})
        v = {**out["values"], "characters": ["kael", "oak"]}
        got = me.edit_form_entity(project, "relationship", "kael-mira", {"base_version": out["version"], "values": v})
        assert set(got["values"]["perspectives"]) == {"kael", "oak"}
        assert got["values"]["perspectives"]["kael"]["label"] == "Friend"      # kept
        assert got["values"]["perspectives"]["oak"]["label"] == ""             # new card, blank

    def test_status_and_history(self, project):
        out = me.create_form_entity(project, "relationship", {"values": {**REL, "status": "complex", "history": "Long."}})
        assert out["values"]["status"] == "complex" and out["values"]["history"] == "Long."
        with pytest.raises(me.EntityInvalid):
            me.edit_form_entity(project, "relationship", "kael-mira", {
                "base_version": out["version"], "values": {**out["values"], "status": "frenemies"}})

    def test_delete(self, project):
        me.create_form_entity(project, "relationship", {"values": REL})
        assert me.delete_preview(project, "relationship", "kael-mira")["can_delete"]
        me.delete_form_entity(project, "relationship", "kael-mira")
        with pytest.raises(me.EntityNotFound):
            me.load_entity(project, "relationship", "kael-mira")


# ─── project ─────────────────────────────────────────────────────────────────

class TestProject:
    def test_title_page_fields_are_grouped_and_last(self):
        fields = me.form_spec("project")["fields"]
        grouped = [f["key"] for f in fields if f.get("group") == "Title page"]
        assert set(grouped) == {"screenplay_title", "credit", "author", "contact", "draft_date", "draft"}
        keys = [f["key"] for f in fields]
        assert keys[-len(grouped):] == grouped or set(keys[-len(grouped):]) == set(grouped)

    def test_loads_whatever_id_is_given(self, project):
        a = me.load_entity(project, "project", "demo")
        b = me.load_entity(project, "project", "anything")
        assert a["id"] == b["id"] == "demo" and a["values"]["name"] == "Demo"

    def test_edit(self, project):
        cur = me.load_entity(project, "project", "demo")
        out = me.edit_form_entity(project, "project", "demo", {
            "base_version": cur["version"],
            "values": {**cur["values"], "genre": "Sci-fi", "author": "Me", "act_count": 4,
                       "structure_type": "Classical", "status": "active"},
            "sections": {"Premise": "What if…"}})
        v = out["values"]
        assert (v["genre"], v["author"], v["act_count"]) == ("Sci-fi", "Me", 4)
        assert out["sections"]["Premise"] == "What if…"

    @pytest.mark.parametrize("bad,msg", [(0, "at least 1"), ("many", "number"), (2.5, "whole number")])
    def test_act_count_is_validated(self, project, bad, msg):
        cur = me.load_entity(project, "project", "demo")
        with pytest.raises(me.EntityInvalid) as e:
            me.edit_form_entity(project, "project", "demo", {
                "base_version": cur["version"], "values": {**cur["values"], "act_count": bad}})
        assert msg in e.value.errors["act_count"]

    def test_lowering_below_existing_acts_warns(self, project):
        for i in (1, 2, 3):
            create_entity(project, "act", f"a{i}", {"title": f"Act {i}"})
        chk = me.check_entity(project, "project", {"values": {"name": "Demo", "act_count": 2}}, "demo")
        assert chk["ok"] and "3 acts" in chk["warnings"]["act_count"]

    def test_bad_structure_is_refused(self, project):
        cur = me.load_entity(project, "project", "demo")
        with pytest.raises(me.EntityInvalid) as e:
            me.edit_form_entity(project, "project", "demo", {
                "base_version": cur["version"], "values": {**cur["values"], "structure_type": "Epic"}})
        assert "Classical" in e.value.errors["structure_type"]

    def test_cannot_be_created_or_deleted_here(self, project):
        with pytest.raises(me.EntityInvalid):
            me.create_form_entity(project, "project", {"values": {"name": "Second"}})
        with pytest.raises(me.EntityInvalid):
            me.delete_preview(project, "project", "demo")
        with pytest.raises(me.EntityInvalid):
            me.delete_form_entity(project, "project", "demo")
        assert me.load_entity(project, "project", "demo")["values"]["name"] == "Demo"

    def test_value_focus_is_shown_not_written(self, project):
        cur = me.load_entity(project, "project", "demo")
        assert "value_focus" in cur["computed"]
        out = me.edit_form_entity(project, "project", "demo", {
            "base_version": cur["version"], "values": {**cur["values"], "value_focus": [{"x": 1}], "genre": "g"}})
        assert out["values"]["genre"] == "g"


# ─── over HTTP ───────────────────────────────────────────────────────────────

class TestHttp:
    @pytest.fixture
    def client(self, tmp_path, monkeypatch):
        from fastapi.testclient import TestClient
        from story_architect.app.config import Config
        from story_architect.app.server import create_app
        from story_architect.core.writes import create_project
        monkeypatch.setattr("story_architect.app.token.load_api_key", lambda: "k")
        root = tmp_path / "root"
        (root / "projects").mkdir(parents=True)
        create_project("demo", {"name": "Demo"}, root)
        proj = root / "projects" / "demo"
        for s, n in (("kael", "Kael"), ("mira", "Mira")):
            create_entity(proj, "character", s, {"name": n, "one_sentence": "x"})
        c = TestClient(create_app(Config(root=root, port=8731)), base_url="http://127.0.0.1:8731")
        c.headers.update({"X-Story-Architect": "1"})
        return c

    def test_spec_exposes_the_new_types(self, client):
        t = client.get("/api/projects/demo/form-spec").json()["types"]
        assert {"plot", "relationship", "project"} <= set(t)
        assert t["project"]["singleton"] and t["relationship"]["auto_name"]["join"] == " & "

    def test_relationship_round_trip(self, client):
        r = client.post("/api/projects/demo/entities/relationship", json={"values": REL})
        assert r.status_code == 200 and r.json()["id"] == "kael-mira"
        r = client.post("/api/projects/demo/entities/relationship",
                        json={"values": {"name": "X", "characters": ["kael", "kael"]}})
        assert r.status_code == 422 and r.json()["error"]["errors"]["characters"] == "Pick two different characters."
        assert client.delete("/api/projects/demo/entities/relationship/kael-mira").status_code == 200

    def test_project_edit_and_refusals(self, client):
        d = client.get("/api/projects/demo/entities/project/demo/form").json()
        r = client.put("/api/projects/demo/entities/project/demo",
                       json={"base_version": d["version"], "values": {**d["values"], "genre": "Noir"}})
        assert r.status_code == 200 and r.json()["values"]["genre"] == "Noir"
        assert client.delete("/api/projects/demo/entities/project/demo").status_code == 422
        assert client.post("/api/projects/demo/entities/project", json={"values": {"name": "B"}}).status_code == 422
