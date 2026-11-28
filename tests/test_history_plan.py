"""The planner: three states in, an ordered op list and its open decisions out.

§7.3's four-row table is the backbone, so the first tests are its rows. Everything the
table cannot settle is a numbered decision; these pin each one's default, each one's
effect when resolved the other way, and the paths that must be refused.

The planner never writes. Every assertion here is on the plan — items, decisions, ops —
and the two that do apply a plan go through `core.drafts.apply_op`, which is what T8's
executor will do.
"""

import pytest

from white_words.scriptwriting.core.history import diff, logical, plan
from white_words.scriptwriting.core.writes import (
    create_entity,
    delete_entity,
    edit_entity,
    reorder,
)


@pytest.fixture
def base(fixture_path):
    """The fixture, unchanged — the merge base of every test here."""
    return fixture_path


def _copy(source, name="side"):
    import shutil
    import tempfile
    from pathlib import Path

    dest = Path(tempfile.mkdtemp()) / name
    shutil.copytree(str(source), str(dest))
    return dest


@pytest.fixture
def sides(base):
    """`(base, ours, theirs)` — two independent copies of the base."""
    return base, _copy(base, "ours"), _copy(base, "theirs")


def _items(result, state=None):
    return [i for i in result["items"] if state is None or i.get("state") == state]


def _keys(result, state=None):
    return [i["key"] for i in _items(result, state)]


def _ops(result):
    return [(op["op"], op.get("entity_type") or op.get("type")) for op in result["ops"]]


def _decision(result, key):
    [found] = [d for d in result["decisions"] if d["key"] == key]
    return found


def _resolved(base, ours, theirs, key, choice, **kwargs):
    """Re-plan with one decision answered as a user."""
    return plan.plan(
        base, ours, theirs, decisions={key: {"choice": choice, "set_by": "user"}}, **kwargs
    )


# ─── §7.3, row by row ───────────────────────────────────────────────────────


def test_nothing_changed_plans_nothing(sides):
    base, ours, theirs = sides
    result = plan.plan(base, ours, theirs, selection=_keys(plan.plan(base, base, theirs)))
    assert result["items"] == []
    assert result["ops"] == []
    assert result["ready"] is True


def test_changed_in_theirs_only_is_taken(sides):
    """Row 1: we did not touch it, they did."""
    base, ours, theirs = sides
    edit_entity(theirs, "character", "kael", {"name": "Kael Renamed"}, "theirs")
    result = plan.plan(base, ours, theirs, selection=["field:character:kael:name"])
    [item] = result["items"]
    assert item["state"] == "take" and item["value"] == "Kael Renamed"
    assert result["ops"] == [
        {
            "op": "edit",
            "entity_type": "character",
            "entity_id": "kael",
            "data": {"name": "Kael Renamed"},
            "summary": "Bring theirs' character name",
            "source": "field:character:kael:name",
        }
    ]


def test_changed_in_ours_only_is_kept(sides):
    """Row 2: our change stands; nothing to bring and nothing to decide."""
    base, ours, theirs = sides
    edit_entity(ours, "character", "kael", {"name": "Mine"}, "ours")
    result = plan.plan(base, ours, theirs, selection=["field:character:kael:name"])
    [item] = result["items"]
    assert item["state"] == "keep"
    assert result["ops"] == [] and result["decisions"] == []


def test_the_same_change_on_both_sides_is_nothing_to_do(sides):
    """Row 3: both changed it, identically."""
    base, ours, theirs = sides
    for side in (ours, theirs):
        edit_entity(side, "character", "kael", {"name": "Kael Renamed"}, "both")
    result = plan.plan(base, ours, theirs, selection=["field:character:kael:name"])
    [item] = result["items"]
    assert item["state"] == "same"
    assert result["ops"] == [] and result["decisions"] == []


def test_a_conflict_is_a_decision_and_carries_both_values(sides):
    """Row 4: both changed it, differently."""
    base, ours, theirs = sides
    edit_entity(ours, "character", "kael", {"name": "Mine"}, "ours")
    edit_entity(theirs, "character", "kael", {"name": "Theirs"}, "theirs")
    result = plan.plan(base, ours, theirs, selection=["field:character:kael:name"])

    [item] = result["items"]
    assert item["state"] == "conflict"
    assert (item["ours"], item["theirs"]) == ("Mine", "Theirs")
    decision = _decision(result, item["decision"])
    assert decision["code"] == "D2" and decision["kind"] == "conflict"
    assert decision["options"] == ["mine", "theirs", "custom"]
    assert decision["choice"] == "mine" and decision["set_by"] == "default"
    assert (decision["ours"], decision["theirs"]) == ("Mine", "Theirs")
    assert result["open"] == [decision["key"]]
    assert result["ready"] is False
    assert result["ops"] == []  # the default (mine) writes nothing


def test_a_conflict_nobody_selected_asks_nothing(sides):
    """Unselected, it leaves `mine` in place: there is nothing to answer, and Apply is not
    held up by it."""
    base, ours, theirs = sides
    edit_entity(ours, "character", "kael", {"name": "Mine"}, "ours")
    edit_entity(theirs, "character", "kael", {"name": "Theirs"}, "theirs")
    edit_entity(theirs, "character", "mira", {"one_sentence": "Brought over."}, "theirs")

    result = plan.plan(base, ours, theirs, selection=["field:character:mira:one_sentence"])

    assert result["decisions"] == [] and result["open"] == []
    assert result["ready"] is True
    assert [op["entity_id"] for op in result["ops"]] == ["mira"]
    assert next(i for i in result["items"] if i["state"] == "conflict")["decision"]


def test_the_same_conflict_asks_once_it_is_selected(sides):
    base, ours, theirs = sides
    edit_entity(ours, "character", "kael", {"name": "Mine"}, "ours")
    edit_entity(theirs, "character", "kael", {"name": "Theirs"}, "theirs")

    asked = plan.plan(base, ours, theirs, selection=["field:character:kael:name"])
    nothing = plan.plan(base, ours, theirs, selection=[])

    assert [d["code"] for d in asked["decisions"]] == ["D2"] and asked["ready"] is False
    assert nothing["decisions"] == [] and nothing["ready"] is True


def test_a_section_conflict_is_the_same_decision(sides):
    base, ours, theirs = sides
    edit_entity(ours, "character", "kael", {"Notes": "mine"}, "ours")
    edit_entity(theirs, "character", "kael", {"Notes": "theirs"}, "theirs")
    result = plan.plan(base, ours, theirs, selection=["section:character:kael:Notes"])
    [item] = result["items"]
    assert item["kind"] == "section" and item["state"] == "conflict"
    assert _decision(result, item["decision"])["code"] == "D2"


def test_theirs_wins_the_conflict_when_chosen(sides):
    base, ours, theirs = sides
    edit_entity(ours, "character", "kael", {"name": "Mine"}, "ours")
    edit_entity(theirs, "character", "kael", {"name": "Theirs"}, "theirs")
    conflicts = plan.plan(base, ours, theirs, selection=["field:character:kael:name"])
    key = conflicts["decisions"][0]["key"]

    result = _resolved(base, ours, theirs, key, "theirs", selection=["field:character:kael:name"])
    assert result["ready"] is True and result["ops"][0]["data"] == {"name": "Theirs"}


def test_a_selection_applies_only_what_it_names(sides):
    base, ours, theirs = sides
    edit_entity(theirs, "character", "kael", {"name": "Renamed"}, "theirs")
    edit_entity(theirs, "character", "mira", {"name": "Mira Renamed"}, "theirs")
    result = plan.plan(base, ours, theirs, selection=["field:character:kael:name"])
    assert [op["entity_id"] for op in result["ops"]] == ["kael"]


# ─── entities arriving and leaving ──────────────────────────────────────────


def test_an_entity_only_theirs_has_is_a_create(sides):
    base, ours, theirs = sides
    create_entity(theirs, "character", "newbie", {"name": "Newbie"}, {"Notes": "fresh"})
    result = plan.plan(base, ours, theirs, selection=["entity:character:newbie"])
    [op] = [o for o in result["ops"] if o["op"] == "create"]
    assert op["type"] == "character" and op["id"] == "newbie"
    assert op["frontmatter"]["name"] == "Newbie"
    assert op["sections"]["Notes"] == "fresh"


def test_a_create_is_planned_in_dependency_order(sides):
    """A scene names a sequence, which names an act: created in that order or refused."""
    base, ours, theirs = sides
    create_entity(theirs, "act", "act-2", {"title": "Act Two", "order": 2})
    create_entity(theirs, "sequence", "seq-2", {"title": "Seq Two", "act_id": "act-2"})
    create_entity(
        theirs,
        "scene",
        "scene-2",
        {
            "sequence_id": "seq-2",
            "int_ext": "INT.",
            "location": "the-central-room",
            "time_of_day": "DAY",
            "title": "Scene Two",
        },
        {"Content": "Action."},
    )
    keys = ["entity:act:act-2", "entity:sequence:seq-2", "entity:scene:scene-2"]
    result = plan.plan(base, ours, theirs, selection=keys)
    created = [op["type"] for op in result["ops"] if op["op"] == "create"]
    assert created == ["act", "sequence", "scene"]


def test_an_entity_we_deleted_is_removed(sides):
    base, ours, theirs = sides
    delete_entity(theirs, "scene", "the-core-day", "theirs", confirm=True)
    result = plan.plan(base, ours, theirs, selection=["entity:scene:the-core-day"])
    deletes = [op for op in result["ops"] if op["op"] == "delete"]
    assert [(o["entity_type"], o["entity_id"]) for o in deletes] == [("scene", "the-core-day")]
    # The beats row is `delete_entity`'s own cascade, so no second op repeats it.
    assert len(deletes) == 1


def test_both_sides_deleting_the_same_entity_plans_nothing(sides):
    base, ours, theirs = sides
    for side in (ours, theirs):
        delete_entity(side, "scene", "the-core-day", "both", confirm=True)
    result = plan.plan(base, ours, theirs, selection=["entity:scene:the-core-day"])
    assert [i for i in result["items"] if i["key"] == "entity:scene:the-core-day"] == []
    assert result["ops"] == []


def test_an_entity_we_added_is_ours_and_nothing_is_planned(sides):
    base, ours, theirs = sides
    create_entity(ours, "character", "mine-only", {"name": "Mine"}, {})
    result = plan.plan(base, ours, theirs, selection=["entity:character:mine-only"])
    assert [i["state"] for i in result["items"]] == ["keep"]
    assert result["ops"] == []


# ─── D1: the same id on both sides ──────────────────────────────────────────


def _both_add(theirs, ours, name="dup"):
    create_entity(ours, "character", name, {"name": "Ours"}, {"Notes": "a"})
    create_entity(theirs, "character", name, {"name": "Theirs"}, {"Notes": "b"})


def test_d1_defaults_to_keeping_mine_and_writes_nothing(sides):
    base, ours, theirs = sides
    _both_add(theirs, ours)
    result = plan.plan(base, ours, theirs, selection=["entity:character:dup"])
    [item] = result["items"]
    decision = _decision(result, item["decision"])
    assert decision["code"] == "D1" and decision["kind"] == "same_id_both_sides"
    assert decision["choice"] == "keep-mine" and decision["set_by"] == "default"
    assert result["ready"] is False
    assert result["ops"] == []  # keep-mine is what the target already holds


def test_d1_keep_both_creates_under_a_new_id(sides):
    base, ours, theirs = sides
    _both_add(theirs, ours)
    key = plan.plan(base, ours, theirs, selection=["entity:character:dup"])["decisions"][0]["key"]
    result = _resolved(base, ours, theirs, key, "keep-both", selection=["entity:character:dup"])
    [op] = [o for o in result["ops"] if o["op"] == "create"]
    assert op["id"] == "dup-2" and op["frontmatter"]["name"] == "Theirs"


def test_d1_keep_both_suggests_an_id_that_is_free(base):
    """A third `dup-2` already in play pushes the suggestion on, not through it."""
    ours, theirs = _copy(base, "ours"), _copy(base, "theirs")
    _both_add(theirs, ours)
    create_entity(ours, "character", "dup-2", {"name": "Taken"}, {})
    key = plan.plan(base, ours, theirs, selection=["entity:character:dup"])["decisions"][0]["key"]
    result = _resolved(base, ours, theirs, key, "keep-both", selection=["entity:character:dup"])
    [op] = [o for o in result["ops"] if o["op"] == "create"]
    assert op["id"] == "dup-3"


def test_d1_take_theirs_writes_their_shape_over_ours(sides):
    base, ours, theirs = sides
    _both_add(theirs, ours)
    key = plan.plan(base, ours, theirs, selection=["entity:character:dup"])["decisions"][0]["key"]
    result = _resolved(base, ours, theirs, key, "take-theirs", selection=["entity:character:dup"])
    [op] = result["ops"]
    assert op["op"] == "edit" and op["data"]["name"] == "Theirs"


def test_d1_combine_brings_the_fields_ours_does_not_touch(sides):
    base, ours, theirs = sides
    create_entity(ours, "character", "dup", {"name": "Ours", "one_sentence": "same"}, {})
    create_entity(theirs, "character", "dup", {"name": "Theirs", "story_role": "Antagonist"}, {})
    opened = plan.plan(base, ours, theirs, selection=["entity:character:dup"])
    key = opened["decisions"][0]["key"]
    result = _resolved(base, ours, theirs, key, "combine", selection=["entity:character:dup"])
    [edit] = [o for o in result["ops"] if o["op"] == "edit"]
    assert edit["data"]["story_role"] == "Antagonist"
    assert "name" not in edit["data"]  # a conflicting field is left to its own decision
    assert any(d["code"] == "D2" for d in result["decisions"])


def test_identical_additions_on_both_sides_are_not_a_conflict(sides):
    base, ours, theirs = sides
    for side in (ours, theirs):
        create_entity(side, "character", "dup", {"name": "Same"}, {"Notes": "same"})
    result = plan.plan(base, ours, theirs, selection=["entity:character:dup"])
    assert [i["state"] for i in result["items"]] == ["same"]
    assert result["decisions"] == [] and result["ops"] == []


# ─── D9: one side deleted, the other changed ────────────────────────────────


def test_d9_defaults_to_keeping_our_deletion(sides):
    base, ours, theirs = sides
    delete_entity(ours, "scene", "central-room-night", "ours", confirm=True)
    edit_entity(theirs, "scene", "central-room-night", {"place": "YARD"}, "theirs")
    result = plan.plan(base, ours, theirs, selection=["entity:scene:central-room-night"])
    item = [i for i in result["items"] if i["key"] == "entity:scene:central-room-night"][0]
    decision = _decision(result, item["decision"])
    assert decision["code"] == "D9" and decision["kind"] == "deleted_and_changed"
    assert decision["deleted_on"] == "ours" and decision["changed_on"] == "theirs"
    assert decision["choice"] == "keep-mine"
    assert result["open"] == [decision["key"]]
    assert result["ops"] == []


def test_d9_take_theirs_restores_then_writes_the_change(sides):
    base, ours, theirs = sides
    delete_entity(ours, "scene", "central-room-night", "ours", confirm=True)
    edit_entity(theirs, "scene", "central-room-night", {"place": "YARD"}, "theirs")
    key = plan.plan(base, ours, theirs, selection=["entity:scene:central-room-night"])["decisions"][
        0
    ]["key"]
    result = _resolved(
        base, ours, theirs, key, "take-theirs", selection=["entity:scene:central-room-night"]
    )
    assert [op["op"] for op in result["ops"]] == ["restore", "edit"]
    assert result["ops"][1]["data"]["place"] == "YARD"


def test_d9_when_they_deleted_and_we_changed(sides):
    base, ours, theirs = sides
    edit_entity(ours, "scene", "central-room-night", {"place": "YARD"}, "ours")
    delete_entity(theirs, "scene", "central-room-night", "theirs", confirm=True)
    result = plan.plan(base, ours, theirs, selection=["entity:scene:central-room-night"])
    item = [i for i in result["items"] if i["key"] == "entity:scene:central-room-night"][0]
    decision = _decision(result, item["decision"])
    assert decision["deleted_on"] == "theirs" and decision["changed_on"] == "ours"
    assert decision["choice"] == "keep-mine"  # our change stands


def test_d9_a_deleted_entitys_changed_fields_are_not_items_of_their_own(sides):
    """Our delete owns the entity; its field changes are that item's, not edits.

    A selection built from every diff item reaches the field item, which has no `ours`
    row to change — planning it raised KeyError before it was dropped here.
    """
    base, ours, theirs = sides
    delete_entity(ours, "scene", "central-room-night", "ours", confirm=True)
    edit_entity(theirs, "scene", "central-room-night", {"place": "YARD"}, "theirs")
    field = "field:scene:central-room-night:place"

    assert field in [i["key"] for i in diff.compare(base, theirs)["items"]]
    for selection in ([field], [field, "entity:scene:central-room-night"]):
        result = plan.plan(base, ours, theirs, selection=selection)
        assert field not in [i["key"] for i in result["items"]]
        assert [d["code"] for d in result["decisions"]] == ["D9"]
        assert result["ops"] == []  # the default keeps our deletion


# ─── D6: the id is in the target's trash ────────────────────────────────────


def test_d6_restores_instead_of_creating(sides):
    """An id in the bin is refused at create, so the incoming row is restored (§7.5)."""
    base, ours, theirs = sides
    create_entity(ours, "character", "ghost", {"name": "Ghost"}, {"Notes": "old"})
    delete_entity(ours, "character", "ghost", "ours", confirm=True)
    create_entity(theirs, "character", "ghost", {"name": "Ghost", "one_sentence": "new"}, {})
    result = plan.plan(base, ours, theirs, selection=["entity:character:ghost"])

    [item] = result["items"]
    assert item["in_trash"] is True
    decision = _decision(result, item["decision"])
    assert decision["code"] == "D6" and decision["choice"] == "restore"
    assert result["open"] == [decision["key"]]
    assert [op["op"] for op in result["ops"]] == ["restore", "edit"]


def test_d6_cancel_plans_nothing(sides):
    base, ours, theirs = sides
    create_entity(ours, "character", "ghost", {"name": "Ghost"}, {})
    delete_entity(ours, "character", "ghost", "ours", confirm=True)
    create_entity(theirs, "character", "ghost", {"name": "Ghost"}, {})
    key = plan.plan(base, ours, theirs, selection=["entity:character:ghost"])["decisions"][0]["key"]
    result = _resolved(base, ours, theirs, key, "cancel", selection=["entity:character:ghost"])
    assert result["ops"] == []


# ─── D4: a singular role already held in the target ─────────────────────────


def _scene_with_role(theirs, entity_id, plot, role, holder="central-room-day"):
    """Release the role from its current holder, then put it on a new scene.

    A create cannot produce two holders (the validator refuses it, probe 6), so the
    incoming state has to be reached the way a writer reaches it: move the role.
    """
    current = [
        r for r in _plot_roles(theirs, holder) if not (r["plot"] == plot and r["role"] == role)
    ]
    edit_entity(theirs, "scene", holder, {"plot_roles": current}, "release")
    create_entity(
        theirs,
        "scene",
        entity_id,
        {
            "sequence_id": "seq-discovery",
            "int_ext": "INT.",
            "location": "the-central-room",
            "time_of_day": "DAY",
            "title": entity_id,
            "plot_roles": [{"plot": plot, "role": role, "description": "taken"}],
        },
        {"Content": "Action."},
    )


def test_d4_is_reported_when_the_incoming_scene_would_be_a_second_holder(sides):
    """D-T7-C: the check runs on the list an edit would write.

    Theirs moved `inciting_incident` to a new scene; our target still holds it. Bringing
    the new scene alone would make two live holders of one plot's singular role.
    """
    base, ours, theirs = sides
    _scene_with_role(theirs, "rival", "the-resistance", "inciting_incident")

    result = plan.plan(base, ours, theirs, selection=["entity:scene:rival"])
    d4 = [d for d in result["decisions"] if d["code"] == "D4"]
    assert d4, [d["code"] for d in result["decisions"]]
    assert d4[0]["role"] == "inciting_incident" and d4[0]["plot"] == "the-resistance"
    assert d4[0]["holder"]["id"] == "central-room-day"
    assert d4[0]["choice"] == "mine"  # the existing holder keeps it
    assert result["ready"] is False


def test_a_whole_value_role_list_replace_is_checked_for_a_second_holder(sides):
    """Taking an edit that *adds* a singular role already held cannot slip through."""
    base, ours, theirs = sides
    _scene_with_role(theirs, "rival", "the-resistance", "inciting_incident")
    # theirs' own scene lost the role; take that edit in isolation.
    result = plan.plan(base, ours, theirs, selection=["field:scene:central-room-day:plot_roles"])
    assert [d for d in result["decisions"] if d["code"] == "D4"] == []  # it releases, not takes


def test_d4_theirs_takes_the_role_from_the_holder(sides):
    base, ours, theirs = sides
    _scene_with_role(theirs, "rival", "the-resistance", "inciting_incident")
    key = plan.plan(base, ours, theirs, selection=["entity:scene:rival"])["decisions"][0]["key"]
    result = _resolved(base, ours, theirs, key, "theirs", selection=["entity:scene:rival"])
    [create] = [o for o in result["ops"] if o["op"] == "create"]
    assert [r["role"] for r in create["frontmatter"]["plot_roles"]] == ["inciting_incident"]
    assert result["ready"] is True


def _plot_roles(project, scene_id):
    from white_words.scriptwriting.core.history import logical

    return logical.of_project(project)[scene_id]["fields"]["plot_roles"]


# ─── D5: a reference the target does not have ───────────────────────────────


def test_d5_offers_bring_and_drop_for_an_optional_site(sides):
    """A cast link is optional, so dropping it is one of the choices."""
    base, ours, theirs = sides
    create_entity(theirs, "character", "newcomer", {"name": "Newcomer"}, {})
    create_entity(
        theirs,
        "character",
        "anchor",
        {"name": "Anchor"},
        {},
    )
    fields = {"name": "Bridge", "characters": ["newcomer"]}
    edit_entity(theirs, "plot", "the-resistance", fields, "theirs")

    result = plan.plan(base, ours, theirs, selection=["field:plot:the-resistance:characters"])
    d5 = [d for d in result["decisions"] if d["code"] == "D5"]
    assert d5 and d5[0]["required"] is False
    assert "drop" in d5[0]["options"]


def test_d5_bring_creates_the_missing_entity(sides):
    base, ours, theirs = sides
    create_entity(theirs, "character", "newcomer", {"name": "Newcomer"}, {})
    edit_entity(theirs, "plot", "the-resistance", {"characters": ["kael", "newcomer"]}, "theirs")
    opened = plan.plan(base, ours, theirs, selection=["field:plot:the-resistance:characters"])
    d5 = [d for d in opened["decisions"] if d["code"] == "D5"][0]
    result = _resolved(
        base, ours, theirs, d5["key"], "bring", selection=["field:plot:the-resistance:characters"]
    )
    created = [op for op in result["ops"] if op["op"] == "create"]
    assert [c["id"] for c in created] == ["newcomer"]


def test_d5_drop_removes_the_reference_from_the_payload(sides):
    base, ours, theirs = sides
    create_entity(theirs, "character", "newcomer", {"name": "Newcomer"}, {})
    edit_entity(theirs, "plot", "the-resistance", {"characters": ["kael", "newcomer"]}, "theirs")
    opened = plan.plan(base, ours, theirs, selection=["field:plot:the-resistance:characters"])
    d5 = [d for d in opened["decisions"] if d["code"] == "D5"][0]
    result = _resolved(
        base, ours, theirs, d5["key"], "drop", selection=["field:plot:the-resistance:characters"]
    )
    edit = [op for op in result["ops"] if op["op"] == "edit"][0]
    assert edit["data"]["characters"] == ["kael"]


def test_a_required_site_does_not_offer_drop(sides):
    """A beat's actor is what the beat means; dropping it is not a resolution."""
    base, ours, theirs = sides
    create_entity(theirs, "character", "newcomer", {"name": "Newcomer"}, {})
    edit_entity(
        theirs,
        "scene_beats",
        "central-room-day-beats",
        {"driver": "newcomer"},
        "theirs",
    )
    result = plan.plan(
        base, ours, theirs, selection=["field:scene_beats:central-room-day-beats:driver"]
    )
    d5 = [d for d in result["decisions"] if d["code"] == "D5"]
    assert d5 and d5[0]["required"] is False  # driver is an optional site in refmap


def test_a_scene_whose_sequence_the_target_lacks_waits_for_the_brought_sequence(sides):
    """Bringing the sequence along satisfies the scene's placement; nothing is asked."""
    base, ours, theirs = sides
    create_entity(theirs, "act", "act-2", {"title": "Act Two", "order": 2})
    create_entity(theirs, "sequence", "seq-2", {"title": "Seq Two", "act_id": "act-2"})
    create_entity(
        theirs,
        "scene",
        "scene-2",
        {
            "sequence_id": "seq-2",
            "int_ext": "INT.",
            "location": "the-central-room",
            "time_of_day": "DAY",
            "title": "Two",
        },
        {"Content": "Action."},
    )
    keys = ["entity:sequence:seq-2", "entity:scene:scene-2"]
    result = plan.plan(base, ours, theirs, selection=keys)
    assert [d for d in result["decisions"] if d["code"] == "D3"] == []
    assert result["ready"] is True


def test_a_scene_whose_sequence_is_not_brought_is_a_d5(sides):
    """The sequence is a required reference (`sequence_id`), so the scene cannot land."""
    base, ours, theirs = sides
    create_entity(theirs, "act", "act-2", {"title": "Act Two", "order": 2})
    create_entity(theirs, "sequence", "seq-2", {"title": "Seq Two", "act_id": "act-2"})
    create_entity(
        theirs,
        "scene",
        "scene-2",
        {
            "sequence_id": "seq-2",
            "int_ext": "INT.",
            "location": "the-central-room",
            "time_of_day": "DAY",
            "title": "Two",
        },
        {"Content": "Action."},
    )
    result = plan.plan(base, ours, theirs, selection=["entity:scene:scene-2"])
    d5 = [d for d in result["decisions"] if d["code"] == "D5"]
    assert d5 and d5[0]["value"] == "seq-2" and d5[0]["required"] is True
    assert "drop" not in d5[0]["options"]


def test_a_scene_whose_sequence_the_target_has_needs_no_decision(sides):
    base, ours, theirs = sides
    create_entity(
        theirs,
        "scene",
        "extra",
        {
            "sequence_id": "seq-discovery",
            "int_ext": "INT.",
            "location": "the-central-room",
            "time_of_day": "DAY",
            "title": "Extra",
        },
        {"Content": "Action."},
    )
    result = plan.plan(base, ours, theirs, selection=["entity:scene:extra"])
    assert result["decisions"] == []
    assert result["ready"] is True
    [order] = [op for op in result["ops"] if op["op"] == "reorder"]
    assert order["ordered_ids"][-1] == "extra"


# ─── D7: order ──────────────────────────────────────────────────────────────


def test_both_sides_adding_a_child_is_not_an_order_conflict(sides):
    """Each side's new child is in its own list; the shared order did not move."""
    base, ours, theirs = sides
    create_entity(ours, "scene", "ours-new", _scene("Ours"), {"Content": "a."})
    create_entity(theirs, "scene", "theirs-new", _scene("Theirs"), {"Content": "b."})
    result = plan.plan(
        base, ours, theirs, selection=["entity:scene:ours-new", "entity:scene:theirs-new"]
    )
    assert not [i for i in result["items"] if i["kind"] == "order" and i["state"] == "conflict"]


def _scene(title):
    return {
        "sequence_id": "seq-discovery",
        "int_ext": "INT.",
        "location": "the-central-room",
        "time_of_day": "DAY",
        "title": title,
    }


def test_a_real_order_conflict_is_d7(sides):
    base, ours, theirs = sides
    reorder(ours, "scene", ["central-room-day", "the-core-day", "central-room-night"], "ours")
    reorder(theirs, "scene", ["the-core-day", "central-room-night", "central-room-day"], "theirs")
    result = plan.plan(base, ours, theirs, selection=["order:scene:seq-discovery"])
    [item] = result["items"]
    assert item["state"] == "conflict"
    decision = _decision(result, item["decision"])
    assert decision["code"] == "D7" and decision["choice"] == "mine"
    assert decision["ours"] == ["central-room-day", "the-core-day", "central-room-night"]


def test_d7_theirs_wins_the_order(sides):
    base, ours, theirs = sides
    reorder(ours, "scene", ["central-room-day", "the-core-day", "central-room-night"], "ours")
    reorder(theirs, "scene", ["the-core-day", "central-room-night", "central-room-day"], "theirs")
    key = plan.plan(base, ours, theirs, selection=["order:scene:seq-discovery"])["decisions"][0][
        "key"
    ]
    result = _resolved(base, ours, theirs, key, "theirs", selection=["order:scene:seq-discovery"])
    [op] = result["ops"]
    assert op["op"] == "reorder"
    assert op["ordered_ids"] == ["the-core-day", "central-room-night", "central-room-day"]


def test_a_taken_order_is_one_reorder_op(sides):
    base, ours, theirs = sides
    reorder(theirs, "scene", ["the-core-day", "central-room-day", "central-room-night"], "theirs")
    result = plan.plan(base, ours, theirs, selection=["order:scene:seq-discovery"])
    [op] = result["ops"]
    assert op["op"] == "reorder" and len(op["ordered_ids"]) == 3


# ─── §7.6: the complete sibling list ────────────────────────────────────────


def test_the_reorder_refuses_a_duplicated_sibling_list():
    """The tripwire (§7.6 / F13): `reorder` renumbers any list handed to it.

    Two rows sharing an order key make the emitted list longer than the live set; the
    assert stops a reorder that would leave the parent half-renumbered. Exercised
    directly because no well-formed plan produces one.
    """
    from white_words.scriptwriting.core.history.plan import _Context, _settle_orders

    ctx = _Context(
        states={
            "base": ({}, {}),
            "ours": ({}, {"scene:seq": ["a", "a"]}),
            "theirs": ({}, {}),
        },
        target=None,
        trashed={},
        chosen={},
        wanted=set(),
    )
    ctx.arriving = {"scene:seq": ["b"]}
    with pytest.raises(AssertionError, match="incomplete sibling list"):
        _settle_orders(ctx)


def test_the_reorder_carries_a_complete_list_in_the_normal_case(sides):
    base, ours, theirs = sides
    create_entity(theirs, "scene", "extra", _scene("Extra"), {"Content": "a."})
    result = plan.plan(base, ours, theirs, selection=["entity:scene:extra"])
    [order] = [op for op in result["ops"] if op["op"] == "reorder"]
    assert sorted(order["ordered_ids"]) == sorted(
        ["central-room-day", "central-room-night", "the-core-day", "extra"]
    )


# ─── the plan applies ───────────────────────────────────────────────────────


def test_a_planned_field_edit_applies_cleanly(sides):
    from white_words.scriptwriting.core.drafts import apply_op
    from white_words.scriptwriting.core.history import logical

    base, ours, theirs = sides
    edit_entity(theirs, "character", "kael", {"name": "Kael Renamed"}, "theirs")
    result = plan.plan(base, ours, theirs, selection=["field:character:kael:name"])
    for op in result["ops"]:
        assert apply_op(ours, op).get("success"), op
    assert logical.of_project(ours)["kael"]["fields"]["name"] == "Kael Renamed"


def test_a_planned_create_applies_cleanly(sides):
    from white_words.scriptwriting.core.drafts import apply_op
    from white_words.scriptwriting.core.history import logical

    base, ours, theirs = sides
    create_entity(theirs, "character", "newbie", {"name": "Newbie"}, {"Notes": "fresh"})
    result = plan.plan(base, ours, theirs, selection=["entity:character:newbie"])
    for op in result["ops"]:
        assert apply_op(ours, op).get("success"), op
    assert "newbie" in logical.of_project(ours)


def test_a_scene_lands_after_its_source_predecessor(sides):
    """§7.5 D3's default, and the reason the reorder carries a complete list.

    Our target's order is `[night, day, core]`, so the two proposals differ: after its
    source predecessor (`day`) puts it third, before its successor (`night`) puts it
    first. Only the predecessor rule yields the order asserted below.

    Applied and re-read, because the rule is only true if `reorder` renumbers the whole
    set — a partial list silently leaves the rest where they were (F13).
    """
    from white_words.scriptwriting.core.drafts import apply_op
    from white_words.scriptwriting.core.history import logical

    base, ours, theirs = sides
    reorder(ours, "scene", ["central-room-night", "central-room-day", "the-core-day"], "ours")
    create_entity(
        theirs,
        "scene",
        "middle",
        {
            "sequence_id": "seq-discovery",
            "int_ext": "INT.",
            "location": "the-central-room",
            "time_of_day": "DAY",
            "title": "Middle",
        },
        {"Content": "Action."},
    )
    # Its predecessor is `day`, its successor `night`: different slots in our order.
    reorder(
        theirs,
        "scene",
        ["central-room-day", "middle", "central-room-night", "the-core-day"],
        "theirs",
    )

    result = plan.plan(base, ours, theirs, selection=["entity:scene:middle"])
    for op in result["ops"]:
        assert apply_op(ours, op).get("success"), op
    conn = __import__("sqlite3").connect(str(ours / ".story" / "story.db"))
    try:
        order = logical.order_of(conn)["scene:seq-discovery"]
    finally:
        conn.close()
    assert order == ["central-room-night", "central-room-day", "middle", "the-core-day"]


def test_a_scene_with_no_predecessor_lands_before_its_successor(sides):
    """The other half of D3: theirs puts it first, so only the successor can place it."""
    from white_words.scriptwriting.core.drafts import apply_op
    from white_words.scriptwriting.core.history import logical

    base, ours, theirs = sides
    create_entity(
        theirs,
        "scene",
        "opener",
        {
            "sequence_id": "seq-discovery",
            "int_ext": "INT.",
            "location": "the-central-room",
            "time_of_day": "DAY",
            "title": "Opener",
        },
        {"Content": "Action."},
    )
    reorder(
        theirs,
        "scene",
        ["opener", "central-room-day", "central-room-night", "the-core-day"],
        "theirs",
    )

    result = plan.plan(base, ours, theirs, selection=["entity:scene:opener"])
    for op in result["ops"]:
        assert apply_op(ours, op).get("success"), op
    conn = __import__("sqlite3").connect(str(ours / ".story" / "story.db"))
    try:
        order = logical.order_of(conn)["scene:seq-discovery"]
    finally:
        conn.close()
    assert order == ["opener", "central-room-day", "central-room-night", "the-core-day"]


def test_d4_mine_brings_the_scene_without_the_colliding_role(sides):
    """D-T7-D: keep-mine drops the incoming entry rather than displacing the holder."""
    base, ours, theirs = sides
    _scene_with_role(theirs, "rival", "the-resistance", "inciting_incident")
    key = plan.plan(base, ours, theirs, selection=["entity:scene:rival"])["decisions"][0]["key"]
    result = _resolved(base, ours, theirs, key, "mine", selection=["entity:scene:rival"])
    [create] = [op for op in result["ops"] if op["op"] == "create"]
    assert create["frontmatter"]["plot_roles"] == []
    assert [op["op"] for op in result["ops"]] == ["create", "reorder"]


def test_a_release_edit_comes_before_the_create_that_needs_the_role(sides):
    """§7.7.2: an incoming scene cannot take a singular role while the old holder has it.

    Ordering only — the create is refused by the validator if the release lands after.
    """
    base, ours, theirs = sides
    _scene_with_role(theirs, "rival", "the-resistance", "inciting_incident")
    key = plan.plan(base, ours, theirs, selection=["entity:scene:rival"])["decisions"][0]["key"]
    result = _resolved(base, ours, theirs, key, "theirs", selection=["entity:scene:rival"])
    kinds = [op["op"] for op in result["ops"]]
    create_at = kinds.index("create")
    releases = [
        i
        for i, op in enumerate(result["ops"])
        if op["op"] == "edit" and op["entity_id"] == "central-room-day"
    ]
    assert releases and max(releases) < create_at


def test_moving_a_role_by_selecting_both_scenes_is_not_a_collision(sides):
    """Theirs moved the role from A to B and the selection holds both edits.

    The holder is released by the same selection, so no decision is raised, and the plan
    must not leave the plot without a holder (the default answer to a false collision
    strips the arriving scene's role while the holder's edit strips the other one).
    """
    from white_words.scriptwriting.core.drafts import apply_op

    base, ours, theirs = sides
    _scene_with_role(theirs, "rival", "the-resistance", "inciting_incident")
    selection = ["entity:scene:rival", "field:scene:central-room-day:plot_roles"]

    result = plan.plan(base, ours, theirs, selection=selection)

    assert [d for d in result["decisions"] if d["code"] == "D4"] == []
    assert result["ready"] is True
    for op in result["ops"]:
        assert apply_op(ours, op).get("success"), op
    holders = [
        sid
        for sid, shape in logical.of_project(ours).items()
        if shape["type"] == "scene"
        and any(
            r["plot"] == "the-resistance" and r["role"] == "inciting_incident"
            for r in shape["fields"].get("plot_roles") or []
        )
    ]
    assert holders == ["rival"]


def test_a_collision_is_still_raised_when_the_holders_release_is_not_selected(sides):
    base, ours, theirs = sides
    _scene_with_role(theirs, "rival", "the-resistance", "inciting_incident")
    result = plan.plan(base, ours, theirs, selection=["entity:scene:rival"])
    assert [d["code"] for d in result["decisions"]] == ["D4"]


def test_the_role_release_and_create_apply_in_that_order(sides):
    from white_words.scriptwriting.core.drafts import apply_op

    base, ours, theirs = sides
    _scene_with_role(theirs, "rival", "the-resistance", "inciting_incident")
    key = plan.plan(base, ours, theirs, selection=["entity:scene:rival"])["decisions"][0]["key"]
    result = _resolved(base, ours, theirs, key, "theirs", selection=["entity:scene:rival"])
    for op in result["ops"]:
        assert apply_op(ours, op).get("success"), (op, "refused")


def test_a_planned_delete_applies_cleanly(sides):
    from white_words.scriptwriting.core.drafts import apply_op
    from white_words.scriptwriting.core.history import logical

    base, ours, theirs = sides
    delete_entity(theirs, "scene", "the-core-day", "theirs", confirm=True)
    result = plan.plan(base, ours, theirs, selection=["entity:scene:the-core-day"])
    for op in result["ops"]:
        assert apply_op(ours, op).get("success"), op
    assert "the-core-day" not in logical.of_project(ours)


# ─── D8: optional cleanup after a removal ───────────────────────────────────


def _delete_case(base):
    """A base where one scene alone casts a character; only `theirs` removes that scene."""

    staged = _copy(base, "staged")
    create_entity(staged, "character", "lone", {"name": "Lone"}, {})
    edit_entity(staged, "scene", "the-core-day", {"characters": ["lone"]}, "cast")
    ours, theirs = _copy(staged, "ours"), _copy(staged, "theirs")
    delete_entity(theirs, "scene", "the-core-day", "theirs", confirm=True)
    return staged, ours, theirs, "entity:scene:the-core-day"


def test_d8_offers_what_only_the_removed_scene_used(sides):
    """§7.4: an entity nothing else references is offered, unticked, and never blocks."""
    base = sides[0]
    base, ours, theirs, key = _delete_case(base)
    result = plan.plan(base, ours, theirs, selection=[key])

    d8 = {d["cleanup"]: d for d in result["decisions"] if d["code"] == "D8"}
    assert "lone" in d8  # cast nowhere else
    assert d8["lone"]["choice"] == "keep" and d8["lone"]["set_by"] == "default"
    assert result["ready"] is True and result["open"] == []
    assert [op["op"] for op in result["ops"]] == ["delete"]


def test_d8_deletes_only_when_chosen(sides):
    base = sides[0]
    base, ours, theirs, key = _delete_case(base)
    opened = plan.plan(base, ours, theirs, selection=[key])
    cleanup_key = next(
        d["key"] for d in opened["decisions"] if d["code"] == "D8" and d["cleanup"] == "lone"
    )
    result = plan.plan(base, ours, theirs, selection=[key], decisions={cleanup_key: "delete"})
    deleted = [op["entity_id"] for op in result["ops"] if op["op"] == "delete"]
    assert deleted == ["the-core-day", "lone"]


def test_d8_never_offers_an_entity_with_another_referrer(sides):
    """A character cast in two scenes is not orphaned by removing one of them."""
    base = sides[0]
    base, ours, theirs, key = _delete_case(base)
    result = plan.plan(base, ours, theirs, selection=[key])
    offered = {d["cleanup"] for d in result["decisions"] if d["code"] == "D8"}
    assert "kael" not in offered  # still cast in the other two scenes
    assert "the-central-room" not in offered


# ─── decisions answered by the agent ────────────────────────────────────────


def test_an_agent_suggestion_does_not_answer_a_decision(sides):
    """§11: a suggestion is pre-filled, not accepted. Apply stays disabled."""
    base, ours, theirs = sides
    edit_entity(ours, "character", "kael", {"name": "Mine"}, "ours")
    edit_entity(theirs, "character", "kael", {"name": "Theirs"}, "theirs")
    key = plan.plan(base, ours, theirs, selection=["field:character:kael:name"])["decisions"][0][
        "key"
    ]
    result = plan.plan(
        base,
        ours,
        theirs,
        selection=["field:character:kael:name"],
        decisions={key: {"choice": "theirs", "set_by": "agent-suggested"}},
    )
    assert result["ready"] is False and result["open"] == [key]
    assert _decision(result, key)["choice"] == "theirs"  # pre-filled, not applied


def test_a_user_answer_marks_the_decision_set(sides):
    base, ours, theirs = sides
    edit_entity(ours, "character", "kael", {"name": "Mine"}, "ours")
    edit_entity(theirs, "character", "kael", {"name": "Theirs"}, "theirs")
    key = plan.plan(base, ours, theirs, selection=["field:character:kael:name"])["decisions"][0][
        "key"
    ]
    result = plan.plan(
        base,
        ours,
        theirs,
        selection=["field:character:kael:name"],
        decisions={key: {"choice": "theirs", "set_by": "user"}},
    )
    assert _decision(result, key)["set_by"] == "user" and result["ready"] is True


def test_an_unknown_choice_falls_back_to_the_default(sides):
    base, ours, theirs = sides
    edit_entity(ours, "character", "kael", {"name": "Mine"}, "ours")
    edit_entity(theirs, "character", "kael", {"name": "Theirs"}, "theirs")
    key = plan.plan(base, ours, theirs, selection=["field:character:kael:name"])["decisions"][0][
        "key"
    ]
    result = plan.plan(
        base,
        ours,
        theirs,
        selection=["field:character:kael:name"],
        decisions={key: "not-an-option"},
    )
    assert _decision(result, key)["choice"] == "mine"


# ─── nothing is written ─────────────────────────────────────────────────────


def test_planning_changes_neither_side(sides):
    from white_words.scriptwriting.core.history import fingerprint

    base, ours, theirs = sides
    edit_entity(theirs, "character", "kael", {"name": "Theirs"}, "theirs")
    create_entity(theirs, "character", "newbie", {"name": "Newbie"}, {})
    before = {
        s: fingerprint.of_project(p)
        for s, p in (("base", base), ("ours", ours), ("theirs", theirs))
    }
    plan.plan(base, ours, theirs, selection=["field:character:kael:name"])
    after = {
        s: fingerprint.of_project(p)
        for s, p in (("base", base), ("ours", ours), ("theirs", theirs))
    }
    assert before == after


# ─── a typed value: what `custom`, and a keep-both's id and fields, are answered with ──


def _typed(base, ours, theirs, key, choice, value, **kwargs):
    return plan.plan(
        base,
        ours,
        theirs,
        decisions={key: {"choice": choice, "value": value, "set_by": "user"}},
        **kwargs,
    )


def test_d2_custom_writes_the_typed_value(sides):
    base, ours, theirs = sides
    edit_entity(ours, "character", "kael", {"name": "Mine"}, "ours")
    edit_entity(theirs, "character", "kael", {"name": "Theirs"}, "theirs")
    key = "field:character:kael:name#D2"

    result = _typed(base, ours, theirs, key, "custom", "Kael Both", selection=[key.split("#")[0]])

    [op] = result["ops"]
    assert op["data"] == {"name": "Kael Both"}
    assert _decision(result, key)["value"] == "Kael Both" and result["ready"] is True


def test_d2_custom_without_a_value_stays_open_and_says_why(sides):
    base, ours, theirs = sides
    edit_entity(ours, "character", "kael", {"name": "Mine"}, "ours")
    edit_entity(theirs, "character", "kael", {"name": "Theirs"}, "theirs")
    key = "field:character:kael:name#D2"

    result = _resolved(base, ours, theirs, key, "custom", selection=[key.split("#")[0]])

    assert result["ops"] == [] and result["ready"] is False
    assert key in result["open"] and "Write the value" in _decision(result, key)["error"]


def test_a_section_conflict_takes_only_text_as_its_custom_value(sides):
    base, ours, theirs = sides
    edit_entity(ours, "character", "kael", {"Identity": "Mine."}, "ours")
    edit_entity(theirs, "character", "kael", {"Identity": "Theirs."}, "theirs")
    key = "section:character:kael:Identity#D2"

    text = _typed(base, ours, theirs, key, "custom", "Both, merged.", selection=[key.split("#")[0]])
    other = _typed(base, ours, theirs, key, "custom", ["no"], selection=[key.split("#")[0]])

    assert text["ops"][0]["data"] == {"Identity": "Both, merged."}
    assert other["ops"] == [] and _decision(other, key)["error"]


def test_a_changed_answer_does_not_keep_the_old_value(sides):
    base, ours, theirs = sides
    edit_entity(ours, "character", "kael", {"name": "Mine"}, "ours")
    edit_entity(theirs, "character", "kael", {"name": "Theirs"}, "theirs")
    key = "field:character:kael:name#D2"

    result = _resolved(base, ours, theirs, key, "theirs", selection=[key.split("#")[0]])

    assert result["ops"][0]["data"] == {"name": "Theirs"}


def test_d4_custom_gives_the_incoming_scene_the_typed_role(sides):
    base, ours, theirs = sides
    _scene_with_role(theirs, "rival", "the-resistance", "inciting_incident")
    key = "entity:scene:rival#D4"

    result = _typed(
        base, ours, theirs, key, "custom", "complication", selection=["entity:scene:rival"]
    )

    [create] = [op for op in result["ops"] if op["op"] == "create"]
    assert create["frontmatter"]["plot_roles"][0]["role"] == "complication"
    assert [op["op"] for op in result["ops"] if op["op"] == "release"] == []
    assert "complication" in _decision(result, key)["roles"] and result["ready"] is True


def test_d4_custom_with_no_valid_role_drops_the_entry_and_stays_open(sides):
    base, ours, theirs = sides
    _scene_with_role(theirs, "rival", "the-resistance", "inciting_incident")
    key = "entity:scene:rival#D4"

    result = _typed(
        base, ours, theirs, key, "custom", "not-a-role", selection=["entity:scene:rival"]
    )

    [create] = [op for op in result["ops"] if op["op"] == "create"]
    assert create["frontmatter"]["plot_roles"] == []
    assert key in result["open"] and _decision(result, key)["error"]


def test_d1_keep_both_uses_the_id_and_fields_that_were_typed(sides):
    base, ours, theirs = sides
    _both_add(theirs, ours)
    key = "entity:character:dup#D1"

    result = _typed(
        base,
        ours,
        theirs,
        key,
        "keep-both",
        {"id": "dup-the-spy", "fields": {"name": "Dup the Spy"}},
        selection=["entity:character:dup"],
    )

    [op] = [o for o in result["ops"] if o["op"] == "create"]
    assert op["id"] == "dup-the-spy" and op["frontmatter"]["name"] == "Dup the Spy"
    assert _decision(result, key)["suggested_id"] == "dup-2" and result["ready"] is True


def test_d1_keep_both_refuses_an_id_the_story_already_has(sides):
    base, ours, theirs = sides
    _both_add(theirs, ours)
    key = "entity:character:dup#D1"

    for bad in ("kael", "has space", "dup"):
        result = _typed(
            base, ours, theirs, key, "keep-both", {"id": bad}, selection=["entity:character:dup"]
        )
        [op] = [o for o in result["ops"] if o["op"] == "create"]
        assert op["id"] == "dup-2", bad  # the suggestion stands in
        assert key in result["open"] and _decision(result, key)["error"], bad


def test_d7_custom_applies_the_typed_order(sides):
    base, ours, theirs = sides
    reorder(ours, "scene", ["central-room-day", "the-core-day", "central-room-night"], "ours")
    reorder(theirs, "scene", ["the-core-day", "central-room-night", "central-room-day"], "theirs")
    key = "order:scene:seq-discovery#D7"
    arranged = ["central-room-night", "central-room-day", "the-core-day"]

    result = _typed(
        base, ours, theirs, key, "custom", arranged, selection=["order:scene:seq-discovery"]
    )

    [op] = result["ops"]
    assert op["op"] == "reorder" and op["ordered_ids"] == arranged
    assert result["ready"] is True


def test_d7_custom_keeps_the_list_complete_when_the_typed_one_is_partial(sides):
    base, ours, theirs = sides
    reorder(ours, "scene", ["central-room-day", "the-core-day", "central-room-night"], "ours")
    reorder(theirs, "scene", ["the-core-day", "central-room-night", "central-room-day"], "theirs")
    key = "order:scene:seq-discovery#D7"

    result = _typed(
        base,
        ours,
        theirs,
        key,
        "custom",
        ["central-room-night"],
        selection=["order:scene:seq-discovery"],
    )

    [op] = result["ops"]
    assert op["ordered_ids"][0] == "central-room-night"
    assert sorted(op["ordered_ids"]) == sorted(
        ["central-room-day", "the-core-day", "central-room-night"]
    )


def test_d7_custom_with_something_other_than_a_list_stays_open(sides):
    base, ours, theirs = sides
    reorder(ours, "scene", ["central-room-day", "the-core-day", "central-room-night"], "ours")
    reorder(theirs, "scene", ["the-core-day", "central-room-night", "central-room-day"], "theirs")
    key = "order:scene:seq-discovery#D7"

    result = _typed(
        base, ours, theirs, key, "custom", "oops", selection=["order:scene:seq-discovery"]
    )

    assert result["ops"] == [] and key in result["open"] and _decision(result, key)["error"]
