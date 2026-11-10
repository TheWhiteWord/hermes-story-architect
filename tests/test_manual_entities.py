"""The entity form: spec, load, check, create, edit, delete.

Built on real entities through `core.writes`, so every assertion reads back what
the agent's own write path stored. The form is a second door into the same room.
"""
import pytest

from story_architect.core import manual_entities as me
from story_architect.core.db import get_db
from story_architect.core.writes import create_entity, edit_entity


@pytest.fixture
def project(tmp_path):
    p = tmp_path
    create_entity(p, "world", "gilead", {"name": "Gilead", "one_sentence": "A city-state."})
    create_entity(p, "location", "kitchen",
                  {"name": "Kitchen", "one_sentence": "Closed restaurant.", "world": "gilead"})
    for slug, name in [("mara", "Mara"), ("oak", "Oak")]:
        create_entity(p, "character", slug,
                      {"name": name, "story_role": "Protagonist", "one_sentence": "T"})
    create_entity(p, "relationship", "mara-oak", {
        "name": "Mara & Oak", "characters": ["mara", "oak"],
        "perspectives": {"mara": {"label": "Partner", "type": "ally"},
                         "oak": {"label": "Partner", "type": "ally"}}})
    return p


def _live(project, etype, eid):
    conn = get_db(project)
    try:
        r = conn.execute("SELECT is_deleted FROM entities WHERE type=? AND id=?",
                         (etype, eid)).fetchone()
        return None if r is None else not r[0]
    finally:
        conn.close()


# ─── spec ────────────────────────────────────────────────────────────────────

class TestSpec:
    def test_every_form_type_has_a_spec(self):
        specs = me.all_specs()
        assert set(specs) == set(me.FORM_TYPES)
        for s in specs.values():
            assert s["fields"] and s["sections"]

    def test_character_kinds(self):
        by = {f["key"]: f for f in me.form_spec("character")["fields"]}
        assert by["name"]["required"] and by["name"]["kind"] == "text"
        assert by["story_role"]["kind"] == "select" and "Protagonist" in by["story_role"]["options"]
        assert by["knowledge"]["kind"] == "list"
        # computed: shown, with a hint saying where to change it
        assert by["relationships"]["kind"] == "computed" and by["relationships"]["hint"]

    def test_relational_fields_become_pickers(self):
        loc = {f["key"]: f for f in me.form_spec("location")["fields"]}
        assert loc["world"]["kind"] == "ref" and loc["world"]["ref"] == "world"
        assert loc["variant_of"]["ref"] == "location"

    def test_value_rungs_are_required_and_name_locks(self):
        by = {f["key"]: f for f in me.form_spec("value")["fields"]}
        assert all(by[r]["required"] for r in ("p", "c", "cd", "nn"))
        assert by["name"]["locked_on_edit"]

    def test_unsupported_type_is_refused(self, project):
        with pytest.raises(me.EntityNotFound):
            me.load_entity(project, "scene", "x")


# ─── load ────────────────────────────────────────────────────────────────────

class TestLoad:
    def test_reads_stored_values_not_display_values(self, project):
        edit_entity(project, "character", "mara", {"knowledge": ["a", "b"], "goals_short": "go"}, "t")
        d = me.load_entity(project, "character", "mara")
        assert d["values"]["knowledge"] == ["a", "b"]           # a list, not "a · b"
        assert d["values"]["goals_short"] == "go"
        assert set(d["sections"]) == set(me.form_spec("character")["sections"])

    def test_column_and_relation_backed_fields(self, project):
        create_entity(project, "location", "kitchen-2",
                      {"name": "K2", "one_sentence": "x", "world": "gilead", "variant_of": "kitchen"})
        v = me.load_entity(project, "location", "kitchen-2")["values"]
        assert v["world"] == "gilead" and v["variant_of"] == "kitchen"

    def test_computed_relationships(self, project):
        c = me.load_entity(project, "character", "mara")["computed"]["relationships"]
        assert c[0]["display"].startswith("Oak") and "Partner" in c[0]["display"]

    def test_placeholder_prose_reads_as_empty(self, project):
        edit_entity(project, "character", "mara", {"Identity": "[placeholder — character/Identity]"}, "t")
        assert me.load_entity(project, "character", "mara")["sections"]["Identity"] == ""

    def test_missing(self, project):
        with pytest.raises(me.EntityNotFound):
            me.load_entity(project, "character", "nobody")


# ─── create ──────────────────────────────────────────────────────────────────

class TestCreate:
    def test_creates_and_reads_back(self, project):
        out = me.create_form_entity(project, "character", {
            "values": {"name": "Dr. Elena Voss", "story_role": "Supporting",
                       "one_sentence": "Watcher.", "knowledge": ["x", "  ", "y"]},
            "sections": {"Identity": "Quiet."}})
        assert out["id"] == "dr-elena-voss" and out["created"]
        assert out["values"]["knowledge"] == ["x", "y"]         # blanks dropped
        assert out["sections"]["Identity"] == "Quiet."

    def test_name_is_the_only_requirement(self, project):
        out = me.create_form_entity(project, "character", {"values": {"name": "Cameo Guy"}})
        assert out["values"]["story_role"] == ""

    def test_missing_name_is_a_field_error(self, project):
        with pytest.raises(me.EntityInvalid) as e:
            me.create_form_entity(project, "character", {"values": {"name": "  "}})
        assert "name" in e.value.errors and "name" in e.value.errors["name"].lower()

    def test_same_name_gets_a_second_id_and_a_warning(self, project):
        chk = me.check_entity(project, "character", {"values": {"name": "Mara"}})
        assert chk["ok"] and chk["id"] == "mara-2" and "name" in chk["warnings"]
        assert me.create_form_entity(project, "character", {"values": {"name": "Mara"}})["id"] == "mara-2"

    def test_id_taken_by_another_type_is_not_an_error(self, project):
        # ids are global across types; the form picks a free one
        assert me.create_form_entity(project, "location", {"values": {"name": "Mara"}})["id"] == "mara-2"

    def test_bad_enum_and_missing_ref_name_their_field(self, project):
        with pytest.raises(me.EntityInvalid) as e:
            me.create_form_entity(project, "location", {"values": {"name": "X", "world": "atlantis"}})
        assert "atlantis" in e.value.errors["world"]
        with pytest.raises(me.EntityInvalid) as e:
            me.create_form_entity(project, "character", {"values": {"name": "X", "story_role": "Hero"}})
        assert "Protagonist" in e.value.errors["story_role"]

    def test_unknown_field_is_refused_in_plain_words(self, project):
        with pytest.raises(me.EntityInvalid) as e:
            me.create_form_entity(project, "character", {"values": {"name": "X", "nope": 1}})
        assert "Reload" in e.value.errors["_form"]

    def test_check_writes_nothing(self, project):
        me.check_entity(project, "character", {"values": {"name": "Ghost"}})
        assert _live(project, "character", "ghost") is None


class TestCreateValue:
    W = {"name": "Trust", "p": "trust", "c": "distrust", "cd": "betrayal", "nn": "blind faith"}

    def test_creates(self, project):
        assert me.create_form_entity(project, "value", {"values": self.W})["id"] == "trust"

    def test_rungs_are_required_and_distinct(self, project):
        with pytest.raises(me.EntityInvalid) as e:
            me.create_form_entity(project, "value", {"values": {"name": "Hope", "p": "hope"}})
        assert set(e.value.errors) == {"c", "cd", "nn"}
        with pytest.raises(me.EntityInvalid) as e:
            me.create_form_entity(project, "value", {"values": {**self.W, "cd": "Distrust"}})
        assert "cd" in e.value.errors and "own word" in e.value.errors["cd"]

    def test_duplicate_name_is_an_error_not_a_suffix(self, project):
        me.create_form_entity(project, "value", {"values": self.W})
        with pytest.raises(me.EntityInvalid) as e:
            me.create_form_entity(project, "value", {"values": self.W})
        assert "already exists" in e.value.errors["name"]

    def test_deleted_value_reserves_its_id_and_says_so(self, project):
        me.create_form_entity(project, "value", {"values": self.W})
        me.delete_form_entity(project, "value", "trust")
        with pytest.raises(me.EntityInvalid) as e:
            me.create_form_entity(project, "value", {"values": self.W})
        assert "deleted earlier" in e.value.errors["name"]

    def test_name_cannot_change_on_edit(self, project):
        out = me.create_form_entity(project, "value", {"values": self.W})
        with pytest.raises(me.EntityInvalid) as e:
            me.edit_form_entity(project, "value", "trust", {
                "base_version": out["version"], "values": {**self.W, "name": "Loyalty"}})
        assert "can't be renamed" in e.value.errors["name"]


# ─── edit ────────────────────────────────────────────────────────────────────

class TestEdit:
    def _load(self, project, t="character", i="mara"):
        return me.load_entity(project, t, i)

    def test_edits_and_returns_fresh_state(self, project):
        cur = self._load(project)
        out = me.edit_form_entity(project, "character", "mara", {
            "base_version": cur["version"],
            "values": {**cur["values"], "goals_short": "Find it."},
            "sections": {"Voice": "Clipped."}})
        assert out["values"]["goals_short"] == "Find it." and out["sections"]["Voice"] == "Clipped."
        assert out["version"] != cur["version"] and not out["unchanged"]

    def test_no_change_writes_nothing(self, project):
        cur = self._load(project)
        out = me.edit_form_entity(project, "character", "mara",
                                  {"base_version": cur["version"], "values": cur["values"],
                                   "sections": cur["sections"]})
        assert out["unchanged"] and out["version"] == cur["version"]

    def test_a_stale_form_cannot_overwrite_an_agent_edit(self, project):
        """The form opened with goals_long empty; the agent then filled it. The
        save carries the old copy, so it must be refused, not applied."""
        cur = self._load(project)
        edit_entity(project, "character", "mara", {"goals_long": "agent wrote this"}, "t")
        with pytest.raises(me.EntityConflict):
            me.edit_form_entity(project, "character", "mara", {
                "base_version": cur["version"],
                "values": {**cur["values"], "goals_short": "mine"}})
        assert me.load_entity(project, "character", "mara")["values"]["goals_long"] == "agent wrote this"

    def test_untouched_fields_are_not_rewritten(self, project, monkeypatch):
        sent = {}
        from story_architect.core import writes
        real = writes.edit_entity
        monkeypatch.setattr(writes, "edit_entity",
                            lambda p, t, i, data, summary: sent.update(data) or real(p, t, i, data, summary))
        cur = self._load(project)
        me.edit_form_entity(project, "character", "mara",
                            {"base_version": cur["version"],
                             "values": {**cur["values"], "goals_short": "g"}})
        assert sent == {"goals_short": "g"}

    def test_conflict_when_changed_underneath(self, project):
        cur = self._load(project)
        edit_entity(project, "character", "mara", {"one_sentence": "changed by the agent"}, "t")
        with pytest.raises(me.EntityConflict) as e:
            me.edit_form_entity(project, "character", "mara",
                                {"base_version": cur["version"], "values": cur["values"]})
        assert e.value.current_version != cur["version"]

    def test_world_and_variant_can_be_changed_and_cleared(self, project):
        cur = self._load(project, "location", "kitchen")
        create_entity(project, "world", "zion", {"name": "Zion", "one_sentence": "x"})
        out = me.edit_form_entity(project, "location", "kitchen", {
            "base_version": cur["version"], "values": {**cur["values"], "world": "zion"}})
        assert out["values"]["world"] == "zion"
        out = me.edit_form_entity(project, "location", "kitchen", {
            "base_version": out["version"], "values": {**out["values"], "world": ""}})
        assert out["values"]["world"] == ""

    def test_cannot_be_its_own_variant(self, project):
        cur = self._load(project, "location", "kitchen")
        with pytest.raises(me.EntityInvalid) as e:
            me.edit_form_entity(project, "location", "kitchen", {
                "base_version": cur["version"], "values": {**cur["values"], "variant_of": "kitchen"}})
        assert "itself" in e.value.errors["variant_of"]

    def test_computed_fields_are_ignored_not_written(self, project):
        cur = self._load(project)
        out = me.edit_form_entity(project, "character", "mara", {
            "base_version": cur["version"],
            "values": {**cur["values"], "relationships": [{"x": 1}], "goals_short": "g"}})
        assert out["values"]["goals_short"] == "g"
        assert out["computed"]["relationships"][0]["display"].startswith("Oak")


# ─── delete ──────────────────────────────────────────────────────────────────

class TestDelete:
    def test_character_takes_its_relationships_with_it(self, project):
        prev = me.delete_preview(project, "character", "mara")
        assert [r["id"] for r in prev["relationships"]] == ["mara-oak"] and prev["can_delete"]
        me.delete_form_entity(project, "character", "mara")
        assert _live(project, "character", "mara") is False
        assert _live(project, "relationship", "mara-oak") is False
        assert _live(project, "character", "oak") is True       # the other one is untouched

    def test_world_deletes_its_locations_and_says_so(self, project):
        prev = me.delete_preview(project, "world", "gilead")
        assert [c["id"] for c in prev["also_deleted"]] == ["kitchen"]
        me.delete_form_entity(project, "world", "gilead")
        assert _live(project, "location", "kitchen") is False

    def test_location_in_use_reports_the_scenes(self, project):
        create_entity(project, "act", "a1", {"title": "A"})
        create_entity(project, "sequence", "s1", {"title": "S", "act_id": "a1"})
        create_entity(project, "scene", "sc1", {"title": "Dinner", "sequence_id": "s1", "act_id": "a1",
                                                "location": "kitchen"})
        prev = me.delete_preview(project, "location", "kitchen")
        assert any("Dinner" in e and "no location" in e for e in prev["effects"])
        me.delete_form_entity(project, "location", "kitchen")
        conn = get_db(project)
        try:
            assert conn.execute("SELECT location_id FROM entities WHERE id='sc1'").fetchone()[0] in ("", None)
        finally:
            conn.close()

    def test_cast_removal_is_reported(self, project):
        create_entity(project, "act", "a1", {"title": "A"})
        create_entity(project, "sequence", "s1", {"title": "S", "act_id": "a1"})
        create_entity(project, "scene", "sc1", {"title": "Dinner", "sequence_id": "s1", "act_id": "a1",
                                                "characters": ["oak"]})
        prev = me.delete_preview(project, "character", "oak")
        assert any("Dinner" in e and "cast" in e for e in prev["effects"])

    def test_character_named_in_beats_blocks_the_delete(self, project):
        create_entity(project, "act", "a1", {"title": "A"})
        create_entity(project, "sequence", "s1", {"title": "S", "act_id": "a1"})
        create_entity(project, "scene", "sc1", {"title": "Dinner", "sequence_id": "s1", "act_id": "a1"})
        create_entity(project, "scene_beats", "sc1-beats", {"scene": "sc1", "driver": "mara"})
        prev = me.delete_preview(project, "character", "mara")
        assert not prev["can_delete"] and "Dinner" in prev["blockers"][0]
        with pytest.raises(me.EntityBlocked):
            me.delete_form_entity(project, "character", "mara")
        assert _live(project, "character", "mara") is True       # nothing was touched
        assert _live(project, "relationship", "mara-oak") is True

    def test_value_used_in_value_turns_blocks_the_delete(self, project):
        create_entity(project, "value", "trust", {"name": "trust", "p": "trust", "c": "distrust",
                                                  "cd": "betrayal", "nn": "blind faith"})
        create_entity(project, "plot", "main", {"name": "Main", "characters": ["mara"]})
        create_entity(project, "act", "a1", {"title": "A"})
        create_entity(project, "sequence", "s1", {"title": "S", "act_id": "a1"})
        create_entity(project, "scene", "sc1", {
            "title": "Dinner", "sequence_id": "s1", "act_id": "a1",
            "value_turns": [{"plot": "main", "value": "trust", "from": "trust", "to": "betrayal",
                             "effects": [{"character": "mara",
                                          "levels": [{"conflict_level": "inner", "effect": "x"}]}]}]})
        prev = me.delete_preview(project, "value", "trust")
        assert not prev["can_delete"] and "Dinner" in prev["blockers"][0]
        # and the protagonist of that turn is protected too
        assert not me.delete_preview(project, "character", "mara")["can_delete"]

    def test_delete_is_reversible_with_restore(self, project):
        from story_architect.tools.story_admin import _restore_entity
        me.delete_form_entity(project, "location", "kitchen")
        res = _restore_entity({"target": {"entity_type": "location", "id": "kitchen"},
                               "summary": "undo"}, project)
        assert not res.get("error")
        assert me.load_entity(project, "location", "kitchen")["values"]["name"] == "Kitchen"


# ─── over HTTP: the middleware is part of the contract ───────────────────────

class TestHttp:
    @pytest.fixture
    def client(self, tmp_path, monkeypatch):
        from fastapi.testclient import TestClient
        from story_architect.app.config import Config
        from story_architect.app.server import create_app
        monkeypatch.setattr("story_architect.app.token.load_api_key", lambda: "k")
        root = tmp_path / "root"
        proj = root / "projects" / "demo"
        (proj / ".story").mkdir(parents=True)
        create_entity(proj, "world", "gilead", {"name": "Gilead", "one_sentence": "x"})
        create_entity(proj, "character", "mara", {"name": "Mara", "one_sentence": "x"})
        c = TestClient(create_app(Config(root=root, port=8731)), base_url="http://127.0.0.1:8731")
        c.headers.update({"X-Story-Architect": "1"})
        return c

    def test_spec_and_load(self, client):
        assert set(client.get("/api/projects/demo/form-spec").json()["types"]) == set(me.FORM_TYPES)
        d = client.get("/api/projects/demo/entities/character/mara/form").json()
        assert d["values"]["name"] == "Mara" and d["version"]

    def test_writes_need_the_custom_header(self, client):
        del client.headers["X-Story-Architect"]
        r = client.post("/api/projects/demo/entities/character", json={"values": {"name": "X"}})
        assert r.status_code == 403

    def test_create_edit_delete_round_trip(self, client):
        r = client.post("/api/projects/demo/entities/location",
                        json={"values": {"name": "Attic", "world": "gilead"}})
        assert r.status_code == 200 and r.json()["id"] == "attic"
        v = r.json()["version"]
        r = client.put("/api/projects/demo/entities/location/attic",
                       json={"base_version": v, "values": {**r.json()["values"], "mood": "dusty"}})
        assert r.json()["values"]["mood"] == "dusty"
        assert client.get("/api/projects/demo/entities/location/attic/delete-preview").json()["can_delete"]
        assert client.delete("/api/projects/demo/entities/location/attic").status_code == 200
        assert client.get("/api/projects/demo/entities/location/attic/form").status_code == 404

    def test_status_codes(self, client):
        r = client.post("/api/projects/demo/entities/location",
                        json={"values": {"name": "X", "world": "nope"}})
        assert r.status_code == 422 and "world" in r.json()["error"]["errors"]
        r = client.put("/api/projects/demo/entities/character/mara",
                       json={"base_version": "stale", "values": {"name": "Mara"}})
        assert r.status_code == 409 and r.json()["error"]["code"] == "conflict"
        assert client.get("/api/projects/nope/entities/character/mara/form").status_code == 404
        assert client.get("/api/projects/demo/entities/scene/x/form").status_code == 404
