"""The diff: entity, order, script, and the items the planner selects from.

Order is not a field (`logical.order_of`), so a diff of the materialized shapes
alone reports a reorder as no change — the two must be paired. A role edit is in
the shape twice (the scene's authored side and the plot's read side), so a diff
that reports both makes a merge item out of a derived view. And a scene's script
entry is composed here rather than read from `get_screenplay_text`, which drops a
scene whose `Content` is empty.
"""

import json

import pytest

from white_words.scriptwriting.core.db import get_db, get_screenplay_text
from white_words.scriptwriting.core.history import diff, logical, store, view
from white_words.scriptwriting.core.writes import (
    create_entity,
    delete_entity,
    edit_entity,
    reorder,
)


@pytest.fixture
def state(fixture_path):
    """The fixture, plus a second copy of it to change: `(a, b)`."""
    other = fixture_path.parent / "changed"
    other.mkdir()
    import shutil

    for entry in fixture_path.iterdir():
        target = other / entry.name
        shutil.copytree(entry, target) if entry.is_dir() else shutil.copy2(entry, target)
    return fixture_path, other


def _keys(result, kind=None):
    return [i["key"] for i in result["items"] if kind is None or i["kind"] == kind]


def _fields(project):
    conn = get_db(project)
    try:
        return logical.materialize(conn)["central-room-day"]["fields"]
    finally:
        conn.close()


# ─── an unchanged pair ───────────────────────────────────────────────────────


def test_two_identical_states_have_no_items(state):
    a, _ = state
    assert diff.compare(a, a)["items"] == []


def test_every_scene_is_reported_unchanged(state):
    a, _ = state
    rows = diff.compare(a, a)["script"]
    assert rows and {r["status"] for r in rows} == {"unchanged"}


# ─── fields and sections ─────────────────────────────────────────────────────


def test_a_field_change_is_one_item_with_both_values(state):
    a, b = state
    edit_entity(b, "character", "kael", {"name": "Kael Renamed"}, "rename")
    result = diff.compare(a, b)
    change = result["entities"]["kael"]["fields"]["name"]
    assert change == {"a": "Kael", "b": "Kael Renamed"}
    assert _keys(result) == ["field:character:kael:name"]


def test_a_section_change_carries_its_line_diff(state):
    a, b = state
    edit_entity(b, "character", "kael", {"Notes": "one\ntwo"}, "note")
    result = diff.compare(a, b)
    section = result["entities"]["kael"]["sections"]["Notes"]
    assert section["b"] == "one\ntwo"
    assert section["a"] == "[placeholder — character/Notes]"
    assert any(line.startswith("+two") for line in section["diff"])
    assert _keys(result) == ["section:character:kael:Notes"]


def test_a_plain_id_list_is_diffed_per_element(state):
    """The same ids in another order are the same state; the moved ones are what
    changed."""
    a, b = state
    edit_entity(b, "scene", "central-room-day", {"characters": ["mira", "kael"]}, "reorder cast")
    result = diff.compare(a, b)
    assert result["entities"]["central-room-day"]["fields"]["characters"] == {
        "a": ["kael", "mira"],
        "b": ["mira", "kael"],
        "added": [],
        "removed": [],
    }


def test_a_removed_id_in_a_plain_list_is_the_element_that_went(state):
    a, b = state
    edit_entity(b, "plot", "the-resistance", {"characters": ["kael"]}, "drop mira")
    result = diff.compare(a, b)
    change = result["entities"]["the-resistance"]["fields"]["characters"]
    assert change["removed"] == ["mira"] and change["added"] == []


def test_a_non_list_value_is_whole(state):
    a, b = state
    edit_entity(b, "scene", "central-room-day", {"int_ext": "EXT."}, "exterior")
    change = diff.compare(a, b)["entities"]["central-room-day"]["fields"]["int_ext"]
    assert change == {"a": "INT.", "b": "EXT."}


def test_a_computed_field_read_from_the_other_end_is_not_reported_twice(state):
    """A role edit edits the scene; the plot's role list moves with it and is a
    derived view (`refmap.DERIVED`), not a second authored change."""
    a, b = state
    roles = json.loads(json.dumps(_fields(b)["plot_roles"]))
    roles[0]["description"] = "Kael discovers the door was never locked, and the cage was his."
    edit_entity(b, "scene", "central-room-day", {"plot_roles": roles}, "role description")
    result = diff.compare(a, b)
    assert _keys(result) == ["field:scene:central-room-day:plot_roles"]
    assert result["entities"]["the-resistance"]["status"] == "unchanged"


# ─── order ───────────────────────────────────────────────────────────────────


def test_a_pure_reorder_moves_no_field(state):
    """The gate the materialized shape cannot meet: fields equal, order changed."""
    a, b = state
    reorder(b, "scene", ["the-core-day", "central-room-day", "central-room-night"], "reorder")
    result = diff.compare(a, b)
    assert {e["status"] for e in result["entities"].values()} == {"unchanged"}
    assert result["order"] == {
        "scene:seq-discovery": {
            "a": ["central-room-day", "central-room-night", "the-core-day"],
            "b": ["the-core-day", "central-room-day", "central-room-night"],
        }
    }
    assert _keys(result) == ["order:scene:seq-discovery"]


def test_act_order_is_the_act_field_not_a_list_item(state):
    """§5.2: acts are not reorderable, so their order is part of the act and must
    not come back as a second `order` item.

    Two acts on purpose: with one act the `act:` order list cannot change, so the
    assertion would hold for a reason unrelated to the rule.
    """
    a, b = state
    create_entity(b, "act", "act-2", {"title": "Act Two", "order": 2})
    edit_entity(b, "act", "act-1", {"order": 2}, "renumber")
    edit_entity(b, "act", "act-2", {"order": 1}, "renumber")
    result = diff.compare(a, b)
    assert _keys(result) == ["field:act:act-1:order", "entity:act:act-2"]
    assert result["order"] == {}


def test_the_act_order_lists_really_move_when_acts_swap(state):
    """The reason the exclusion is needed: the `act:` list does change."""
    a, b = state
    create_entity(b, "act", "act-2", {"title": "Act Two", "order": 2})
    edit_entity(b, "act", "act-1", {"order": 2}, "renumber")
    edit_entity(b, "act", "act-2", {"order": 1}, "renumber")
    conn = get_db(b)
    try:
        assert logical.order_of(conn)["act:"] == ["act-2", "act-1"]
    finally:
        conn.close()


def test_a_reorder_shows_as_moved_in_the_script_view(state):
    a, b = state
    reorder(b, "scene", ["the-core-day", "central-room-day", "central-room-night"], "reorder")
    rows = {r["id"]: r for r in diff.compare(a, b)["script"]}
    assert rows["the-core-day"]["status"] == "moved"
    assert rows["the-core-day"]["placement"]["a"]["position"] == 3
    assert rows["the-core-day"]["placement"]["b"]["position"] == 1
    assert "order:scene:seq-discovery" in rows["the-core-day"]["items"]


# ─── entities appearing and disappearing ─────────────────────────────────────


def test_a_created_entity_is_one_added_item(state):
    a, b = state
    create_entity(
        b,
        "location",
        "the-greenhouse",
        {"name": "The Greenhouse", "world": "the-i"},
    )
    result = diff.compare(a, b)
    assert result["entities"]["the-greenhouse"]["status"] == "added"
    assert _keys(result) == ["entity:location:the-greenhouse"]


def test_a_trashed_entity_is_removed_and_its_references_go_with_it(state):
    """The trashed row is not content, and the ids naming it are hidden from every
    reader — including this one (D-1), so a delete reads as a delete rather than a
    delete plus a ghost id in `relationship.characters`."""
    a, b = state
    delete_entity(b, "character", "mira", "cut", confirm=True)
    result = diff.compare(a, b)
    assert result["entities"]["mira"]["status"] == "removed"
    assert result["entities"]["central-room-day"]["fields"]["characters"]["removed"] == ["mira"]
    assert result["entities"]["kael-mira"]["fields"]["characters"]["removed"] == ["mira"]
    assert "mira" not in {
        entity_id for entity_id, row in result["entities"].items() if row["status"] != "removed"
    }


def test_a_trashed_reference_column_reads_empty_in_the_diff(state):
    """`location_id` is a reference column: the location is gone from the shape,
    so the scene names nothing rather than a dead id."""
    a, b = state
    delete_entity(b, "location", "the-central-room", "cut", confirm=True)
    result = diff.compare(a, b)
    assert result["entities"]["the-central-room"]["status"] == "removed"
    assert result["entities"]["central-room-day"]["fields"]["location"] == {
        "a": "the-central-room",
        "b": "",
    }


def test_a_rename_inside_the_trash_changes_nothing(state):
    a, b = state
    delete_entity(b, "character", "mira", "cut", confirm=True)
    before = diff.compare(a, b)
    conn = get_db(b)
    conn.execute("UPDATE entities SET name='Mira Renamed' WHERE id='mira'")
    conn.commit()
    conn.close()
    assert diff.compare(a, b) == before


def test_a_relationship_naming_a_trashed_character_loses_it(state):
    """`characters` is `extra`-backed, so this is the `live_extra` path — the
    relation-backed cast list is the `live_relations` view and hides it anyway.
    Without the guard the id survives in a shape where the entity is absent."""
    a, b = state
    delete_entity(b, "character", "mira", "cut", confirm=True)
    result = diff.compare(a, b)
    change = result["entities"]["kael-mira"]["fields"]["characters"]
    assert change["b"] == ["kael"]
    assert change["removed"] == ["mira"]


# ─── script ──────────────────────────────────────────────────────────────────


def test_the_script_text_agrees_with_the_screenplay_assembly(state):
    """The composition in `diff` is the assembly's, so the two cannot drift."""
    a, _ = state
    composed = "\n\n".join(
        row["text"]["a"] for row in diff.compare(a, a)["script"] if row["text"]["a"]
    )
    assert composed == get_screenplay_text(a)


def test_a_heading_only_scene_is_in_the_script_view(state):
    """`get_screenplay_text` filters an empty `Content` out; a scene is still a
    scene, and a script view that loses one is worse than one showing no body."""
    a, b = state
    create_entity(
        b,
        "scene",
        "empty-scene",
        {
            "title": "Empty",
            "sequence_id": "seq-discovery",
            "int_ext": "INT.",
            "location": "the-central-room",
            "time_of_day": "NIGHT",
        },
    )
    assert "EMPTY SCENE" not in get_screenplay_text(b)
    row = {r["id"]: r for r in diff.compare(a, b)["script"]}["empty-scene"]
    assert row["status"] == "added"
    assert row["text"]["b"] == "INT. THE CENTRAL ROOM - NIGHT"
    assert row["items"] == ["entity:scene:empty-scene"]


def test_a_body_edit_is_an_edited_scene_with_the_heading_kept(state):
    a, b = state
    edit_entity(b, "scene", "central-room-day", {"Content": "KAEL opens the door."}, "rewrite")
    row = {r["id"]: r for r in diff.compare(a, b)["script"]}["central-room-day"]
    assert row["status"] == "edited"
    assert row["text"]["b"].startswith("INT. THE CENTRAL ROOM - DAY\n\n")
    assert any("KAEL opens the door." in line for line in row["diff"])
    assert row["items"] == ["section:scene:central-room-day:Content"]


def test_a_heading_field_edit_is_an_edited_scene(state):
    a, b = state
    edit_entity(b, "scene", "central-room-day", {"time_of_day": "NIGHT"}, "night")
    row = {r["id"]: r for r in diff.compare(a, b)["script"]}["central-room-day"]
    assert row["status"] == "edited"
    assert "NIGHT" in row["text"]["b"]
    assert row["items"] == ["field:scene:central-room-day:time_of_day"]


def test_a_removed_scene_is_reported_after_the_live_ones(state):
    a, b = state
    delete_entity(b, "scene", "the-core-day", "cut", confirm=True)
    rows = diff.compare(a, b)["script"]
    assert rows[-1]["id"] == "the-core-day"
    assert rows[-1]["status"] == "removed"
    assert rows[-1]["text"] == {"a": rows[-1]["text"]["a"], "b": None}


def test_the_script_view_selects_the_items_it_shows(state):
    """§6.2: a lens over the same items. Every key a scene row names is an item."""
    a, b = state
    edit_entity(b, "scene", "central-room-day", {"time_of_day": "NIGHT"}, "night")
    result = diff.compare(a, b)
    item_keys = set(_keys(result))
    row = {r["id"]: r for r in result["script"]}["central-room-day"]
    assert row["items"] and set(row["items"]) <= item_keys


def test_a_scene_moved_to_another_sequence_is_moved_not_edited(state):
    a, b = state
    create_entity(b, "sequence", "seq-two", {"title": "Second", "act_id": "act-1"})
    edit_entity(b, "scene", "the-core-day", {"sequence_id": "seq-two"}, "move")
    rows = {r["id"]: r for r in diff.compare(a, b)["script"]}
    assert rows["the-core-day"]["status"] == "moved"
    assert rows["the-core-day"]["placement"]["b"]["sequence"] == "seq-two"


# ─── across a draft ──────────────────────────────────────────────────────────


def test_a_draft_is_compared_through_its_view(fixture_path):
    """A frozen draft is never opened: the diff takes project paths (F10), so a
    caller passes a `project_view` copy."""
    store.adopt(fixture_path)
    first = store.list_branches(fixture_path)["snapshots"][0]
    edit_entity(fixture_path, "character", "kael", {"name": "Kael Later"}, "rename")

    with view.project_view(fixture_path, first["id"]) as draft:
        result = diff.compare(draft, fixture_path)

    assert result["entities"]["kael"]["fields"]["name"] == {"a": "Kael", "b": "Kael Later"}
    assert _keys(result) == ["field:character:kael:name"]


# ─── script rows carry what a screenplay view needs ──────────────────────────


def test_a_script_row_carries_its_blocks_heading_first(state):
    a, b = state
    edit_entity(
        b,
        "scene",
        "central-room-day",
        {"Content": "KAEL opens the door.\n\nKAEL\n(low)\nIt is open."},
        "rewrite",
    )
    row = {r["id"]: r for r in diff.compare(a, b)["script"]}["central-room-day"]

    assert [x["type"] for x in row["blocks"]["b"]] == [
        "heading",
        "action",
        "character",
        "parenthetical",
        "dialogue",
    ]
    assert row["blocks"]["b"][0]["text"] == "INT. THE CENTRAL ROOM - DAY"
    assert row["blocks"]["a"][0]["type"] == "heading"


def test_a_missing_side_has_no_blocks_and_no_number(state):
    a, b = state
    delete_entity(b, "scene", "the-core-day", "cut", confirm=True)
    row = {r["id"]: r for r in diff.compare(a, b)["script"]}["the-core-day"]

    assert row["status"] == "removed"
    assert row["blocks"]["b"] is None and row["number"]["b"] is None
    assert row["blocks"]["a"] and row["number"]["a"] is not None


def test_scene_numbers_are_ranks_in_the_composed_script(state):
    """The number a reader sees, not the scene's position in its sequence."""
    a, b = state
    numbers = {r["id"]: r["number"]["a"] for r in diff.compare(a, b)["script"]}
    from white_words.scriptwriting.core.screenplay import extract_scenes

    composed = get_screenplay_text(a)
    assert sorted(n for n in numbers.values() if n) == list(
        range(1, len(extract_scenes(composed)) + 1)
    )


def test_a_scene_without_text_has_no_number_and_does_not_shift_the_rest(state):
    a, b = state
    before = {r["id"]: r["number"]["b"] for r in diff.compare(a, b)["script"]}
    create_entity(
        b,
        "scene",
        "empty-scene",
        {
            "title": "Empty",
            "sequence_id": "seq-discovery",
            "int_ext": "INT.",
            "location": "the-central-room",
            "time_of_day": "NIGHT",
        },
    )
    rows = {r["id"]: r for r in diff.compare(a, b)["script"]}

    assert rows["empty-scene"]["number"]["b"] is None
    assert {i: r["number"]["b"] for i, r in rows.items() if i != "empty-scene"} == before


def test_adding_a_scene_with_text_shifts_the_numbers_after_it(state):
    a, b = state
    create_entity(
        b,
        "scene",
        "new-scene",
        {
            "title": "New",
            "sequence_id": "seq-discovery",
            "int_ext": "INT.",
            "location": "the-central-room",
            "time_of_day": "NIGHT",
        },
        {"Content": "KAEL waits."},
    )
    rows = {r["id"]: r for r in diff.compare(a, b)["script"]}

    shifted = [
        r for r in rows.values() if r["number"]["a"] and r["number"]["b"] != r["number"]["a"]
    ]
    assert rows["new-scene"]["number"]["a"] is None and rows["new-scene"]["number"]["b"] is not None
    assert all(r["number"]["b"] == r["number"]["a"] + 1 for r in shifted)
