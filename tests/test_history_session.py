"""A persistent merge session: the row, its re-derived plan, and apply to either target.

The planner's tests prove a plan is right and the executor's prove it lands; these prove
the SESSION holds the inputs that produce it — that a decision answered in one call is
still answered in the next, that a stored fingerprint refuses a target that moved, and
that a merge into a branch nobody has loaded writes that branch's parked head and takes
that branch's pre-merge draft, leaving the live project alone.
"""

import sqlite3

import pytest

from white_words.scriptwriting.core.history import diff, session, store
from white_words.scriptwriting.core.writes import edit_entity

NAME = "field:character:kael:name"
SIDE_LABEL = "Side 1"


@pytest.fixture
def project(fixture_path):
    """The fixture on `main`, with a `side` branch carrying one saved draft."""
    store.adopt(fixture_path)
    root = store.head_state(fixture_path)["branch"]["base_snapshot_id"]
    store.branch_from(fixture_path, root, "side")
    store.switch(fixture_path, "side")
    edit_entity(fixture_path, "character", "kael", {"name": "Kael On Side"}, "side")
    store.save_snapshot(fixture_path, SIDE_LABEL)
    store.switch(fixture_path, "main")
    return fixture_path


def _name(project):
    return diff.load(project)[0]["kael"]["fields"]["name"]


def _side(project, label=SIDE_LABEL):
    """A `side` branch draft id, by label."""
    return next(s["id"] for s in store.list_branches(project)["snapshots"] if s["label"] == label)


def _start(project, target="main", selection=(NAME,)):
    return session.start(
        project, target, {"kind": "snapshot", "id": _side(project)}, selection=list(selection)
    )


def _rows(project):
    conn = sqlite3.connect(str(store.history_path(project)))
    try:
        return conn.execute("SELECT id, status, selection FROM merge_sessions").fetchall()
    finally:
        conn.close()


# ─── the row ────────────────────────────────────────────────────────────────


def test_a_started_session_is_a_row_holding_the_inputs(project):
    started = _start(project)

    assert started["status"] == "open"
    assert started["target_branch_id"] == "main"
    assert started["source"] == {
        "kind": "snapshot",
        "id": _side(project),
        "base_snapshot_id": _side(project),
    }
    assert started["selection"] == [NAME]
    assert started["base_snapshot_id"] == store.head_state(project)["base"]["id"]
    assert [r[0] for r in _rows(project)] == [started["id"]]


def test_the_session_stores_no_plan(project):
    """The inputs are stored, so a re-plan cannot be stale code's memory."""
    started = _start(project)

    assert "plan" not in started and "ops" not in started
    assert "plan" not in _rows(project)[0]


def test_show_re_derives_the_plan_from_the_row(project):
    started = _start(project)

    shown = session.show(project, started["id"])

    assert shown["stale"] is False
    assert [(op["op"], op["entity_id"]) for op in shown["plan"]["ops"]] == [("edit", "kael")]
    assert shown["plan"]["ready"] is True


def test_a_decision_survives_the_next_call(project):
    """The reason a session exists: an answer given in one request is answered in the next."""
    edit_entity(project, "character", "mira", {"name": "Mira Ours"}, "ours")
    theirs = _copy_of_side_changed(project, "mira", "Mira Theirs")
    started = session.start(
        project, "main", {"kind": "snapshot", "id": theirs}, selection=["field:character:mira:name"]
    )
    key = session.show(project, started["id"])["plan"]["decisions"][0]["key"]
    assert session.show(project, started["id"])["plan"]["ready"] is False

    session.set_decision(project, started["id"], key, "theirs")

    shown = session.show(project, started["id"])
    assert shown["plan"]["ready"] is True
    assert shown["plan"]["decisions"][0]["choice"] == "theirs"
    assert session.apply(project, started["id"])["status"] == "applied"
    assert _name_of(project, "mira") == "Mira Theirs"


def test_a_key_that_is_not_a_decision_is_refused(project):
    """A typo used to be stored and ignored, so the answer silently did nothing."""
    name = NAME  # `field:character:kael:name`
    edit_entity(project, "character", "kael", {"name": "Kael Ours"}, "ours")
    theirs = _copy_of_side_changed(project, "kael", "Kael Theirs")
    started = session.start(project, "main", {"kind": "snapshot", "id": theirs}, selection=[name])
    valid = session.show(project, started["id"])["plan"]["decisions"][0]["key"]
    assert valid == f"{name}#D2"

    with pytest.raises(ValueError, match="not a decision key"):
        session.set_decision(project, started["id"], name, "theirs")

    # A known code this plan does not hold: "not asked (yet)", naming the real keys.
    with pytest.raises(ValueError, match="is not asked"):
        session.set_decision(project, started["id"], f"{name}#D4", "theirs")

    assert session.show(project, started["id"])["plan"]["open"] == [valid]


def test_a_decision_another_answer_would_raise_is_not_yet_asked(project):
    """A D2 chosen `theirs` on `plot_roles` can raise a D4 the default plan never had.

    Answering the D4 in advance cannot work: it is not a decision until the D2's value
    is known, so the refusal says "not yet asked" rather than naming a bad key.
    """
    scene = "central-room-night"
    d2 = f"field:scene:{scene}:plot_roles"
    d4 = f"entity:scene:{scene}#D4"

    store.switch(project, "side")
    edit_entity(project, "scene", "central-room-day", {"plot_roles": []}, "side")
    edit_entity(
        project,
        "scene",
        scene,
        {
            "plot_roles": [
                {"plot": "the-resistance", "role": "inciting_incident", "description": "s"}
            ]
        },
        "side",
    )
    snapshot = store.save_snapshot(project, "Side role move")["id"]
    store.switch(project, "main")
    edit_entity(
        project,
        "scene",
        scene,
        {"plot_roles": [{"plot": "the-resistance", "role": "climax", "description": "o"}]},
        "ours",
    )

    started = session.start(project, "main", {"kind": "snapshot", "id": snapshot}, selection=[d2])

    assert [d["key"] for d in session.show(project, started["id"])["plan"]["decisions"]] == [
        f"{d2}#D2"
    ]
    with pytest.raises(ValueError, match="is not asked"):
        session.set_decision(project, started["id"], d4, "mine")

    session.set_decision(project, started["id"], f"{d2}#D2", "theirs")
    keys = [d["key"] for d in session.show(project, started["id"])["plan"]["decisions"]]
    assert d4 in keys


def test_an_agent_suggestion_does_not_answer_a_decision(project):
    edit_entity(project, "character", "mira", {"name": "Mira Ours"}, "ours")
    theirs = _copy_of_side_changed(project, "mira", "Mira Theirs")
    started = session.start(
        project, "main", {"kind": "snapshot", "id": theirs}, selection=["field:character:mira:name"]
    )
    key = session.show(project, started["id"])["plan"]["decisions"][0]["key"]

    session.set_decision(project, started["id"], key, "theirs", set_by="agent-suggested")

    shown = session.show(project, started["id"])
    assert shown["plan"]["ready"] is False and shown["plan"]["open"] == [key]
    assert session.apply(project, started["id"])["status"] == "blocked"


def test_the_selection_can_be_narrowed_and_widened(project):
    store.switch(project, "side")
    edit_entity(project, "character", "mira", {"name": "Mira On Side"}, "side")
    store.save_snapshot(project, "Side 2")
    store.switch(project, "main")
    started = session.start(
        project,
        "main",
        {"kind": "snapshot", "id": _side(project, "Side 2")},
        selection=[NAME, "field:character:mira:name"],
    )
    assert sorted(
        op["entity_id"] for op in session.show(project, started["id"])["plan"]["ops"]
    ) == [
        "kael",
        "mira",
    ]

    session.set_selection(project, started["id"], [])
    assert session.show(project, started["id"])["plan"]["ops"] == []

    session.set_selection(project, started["id"], [NAME])
    ops = session.show(project, started["id"])["plan"]["ops"]
    assert [op["entity_id"] for op in ops] == ["kael"]


def test_a_new_selection_does_not_change_the_drafts_the_session_holds(project):
    """Nothing about the plan is stored: widening it re-reads the same three states."""
    started = _start(project)
    session.set_selection(project, started["id"], [])

    assert _side(project) == started["source"]["id"]
    assert session.show(project, started["id"])["base_snapshot_id"] == started["base_snapshot_id"]


def test_a_preview_writes_nothing(project):
    started = _start(project)

    verdict = session.preview(project, started["id"])

    assert verdict["status"] == "clean"
    assert _name(project) == "Kael"
    assert [r[1] for r in _rows(project)] == ["open"]
    assert len(store.list_branches(project)["snapshots"]) == 2  # the two drafts it started with


def test_a_preview_of_an_unanswered_plan_is_blocked_not_refused(project):
    edit_entity(project, "character", "mira", {"name": "Mira Ours"}, "ours")
    theirs = _copy_of_side_changed(project, "mira", "Mira Theirs")
    started = session.start(
        project, "main", {"kind": "snapshot", "id": theirs}, selection=["field:character:mira:name"]
    )

    verdict = session.preview(project, started["id"])
    assert verdict["status"] == "blocked" and verdict["open"]


# ─── apply, live target ─────────────────────────────────────────────────────


def test_apply_lands_the_plan_and_closes_the_session(project):
    started = _start(project)

    result = session.apply(project, started["id"])

    assert result["status"] == "applied"
    assert [a["op"] for a in result["applied"]] == ["edit"]
    assert _name(project) == "Kael On Side"
    assert session.show(project, started["id"])["status"] == "applied"
    assert session.show(project, started["id"])["plan"] is None


def test_a_closed_session_cannot_be_applied_again(project):
    started = _start(project)
    session.apply(project, started["id"])

    with pytest.raises(ValueError, match="start a new one"):
        session.apply(project, started["id"])


def test_a_target_that_moved_since_start_is_refused(project):
    """§7.7.4: the plan was made against another state, so it is refused, not re-based."""
    started = _start(project)
    edit_entity(project, "character", "mira", {"name": "Moved After The Plan"}, "ours")

    shown = session.show(project, started["id"])
    result = session.apply(project, started["id"])

    assert shown["stale"] is True
    assert result["status"] == "refused" and result["code"] == "stale_plan"
    assert _name(project) == "Kael"


def test_a_stale_session_offers_its_inputs_for_a_new_one(project):
    """The refusal names no refresh: the next session is started with what `show` returns."""
    started = _start(project)
    edit_entity(project, "character", "mira", {"name": "Moved"}, "ours")
    shown = session.show(project, started["id"])

    again = session.start(
        project,
        shown["target_branch_id"],
        shown["source"],
        selection=shown["selection"],
        decisions=shown["decisions"],
    )

    assert session.show(project, again["id"])["stale"] is False
    assert session.apply(project, again["id"])["status"] == "applied"


def test_a_complete_merge_records_its_source_as_a_parent(project):
    started = _start(project)

    result = session.apply(project, started["id"], complete=True)

    assert result["parents"] == [_side(project)]
    edit_entity(project, "character", "mira", {"name": "After"}, "ours")
    saved = store.save_snapshot(project, "After merge")
    assert saved["parents"] == [result["baseline"]["id"], _side(project)]


def test_a_cherry_pick_records_no_parent(project):
    started = _start(project)

    result = session.apply(project, started["id"])

    assert result["parents"] is None
    edit_entity(project, "character", "mira", {"name": "After"}, "ours")
    saved = store.save_snapshot(project, "After the pick")
    assert _side(project) not in saved["parents"]


def test_discard_closes_the_session_without_touching_the_project(project):
    started = _start(project)

    discarded = session.discard(project, started["id"])

    assert discarded["status"] == "discarded"
    assert _name(project) == "Kael"
    with pytest.raises(ValueError, match="discarded"):
        session.apply(project, started["id"])


# ─── source refs (§7.1) ─────────────────────────────────────────────────────


def test_the_source_may_be_another_branch_head_with_unsaved_changes(project):
    """§7.1: a merge brings changes from any draft OR another branch's head."""
    store.switch(project, "side")
    edit_entity(project, "character", "kael", {"name": "Unsaved On Side"}, "side")
    store.switch(project, "main")

    started = session.start(project, "main", {"kind": "branch", "id": "side"}, selection=[NAME])
    result = session.apply(project, started["id"])

    assert result["status"] == "applied"
    assert _name(project) == "Unsaved On Side"


def test_a_complete_merge_from_an_unsaved_head_is_refused(project):
    """A parent means "everything in it is accounted for"; no draft accounts for these."""
    started = session.start(project, "main", {"kind": "branch", "id": "side"}, selection=[NAME])

    with pytest.raises(ValueError, match="complete merge needs a saved draft"):
        session.apply(project, started["id"], complete=True)
    assert _name(project) == "Kael"


def test_a_head_source_that_is_the_target_is_refused(project):
    with pytest.raises(ValueError, match="cannot be merged into itself"):
        session.start(project, "main", {"kind": "branch", "id": "main"})


def test_an_unknown_source_is_refused(project):
    with pytest.raises(ValueError, match="No such draft"):
        session.start(project, "main", {"kind": "snapshot", "id": "s-nope"})
    with pytest.raises(ValueError, match="No such branch"):
        session.start(project, "main", {"kind": "branch", "id": "nope"})


# ─── apply, parked target (§7.8) ────────────────────────────────────────────


def test_a_parked_target_is_merged_and_written_back(project):
    """The branch is not loaded, so its head is the target; the live project is untouched."""
    root = store.head_state(project)["base"]["id"]
    store.branch_from(project, root, "target2")
    started = _start(project, target="target2")

    result = session.apply(project, started["id"])

    assert result["status"] == "applied"
    assert _name(project) == "Kael"  # main's head, not the merge target
    assert _head_name(project, "target2") == "Kael On Side"
    assert session.show(project, started["id"])["status"] == "applied"


def test_a_parked_target_takes_its_own_branchs_pre_merge_draft(project):
    """`save_snapshot` only freezes the live head, so this branch needs its own."""
    root = store.head_state(project)["base"]["id"]
    store.branch_from(project, root, "target2")
    store.switch(project, "target2")
    edit_entity(project, "character", "mira", {"name": "Diverged On Target2"}, "target2")
    store.switch(project, "main")
    started = _start(project, target="target2")

    result = session.apply(project, started["id"])

    assert result["baseline"]["created"] is True
    drafts = [s for s in store.list_branches(project)["snapshots"] if s["branch_id"] == "target2"]
    assert [s["label"] for s in drafts] == [result["baseline"]["label"]]
    frozen = store.snapshot_file(project, drafts[0]["id"])
    conn = sqlite3.connect(f"file:{frozen}?mode=ro&immutable=1", uri=True)
    try:
        assert conn.execute("SELECT name FROM entities WHERE id='mira'").fetchone()[0] == (
            "Diverged On Target2"
        )
    finally:
        conn.close()


def test_a_merge_into_a_parked_head_leaves_no_manifest_in_the_scratch(
    project, tmp_path, monkeypatch
):
    """`execute.apply` would adopt a scratch copy as a new project; this path must not.

    Pointed at a scratch copy, the executor writes it its own `history.db` and `history/`
    and adopts it, so the pre-merge draft lands in a throwaway manifest and this branch
    gets none. Every temporary project this merge makes is recorded here, and none of
    them may gain a manifest.
    """
    root = store.head_state(project)["base"]["id"]
    store.branch_from(project, root, "target2")
    started = _start(project, target="target2")
    made = []

    class Keep:
        """A `TemporaryDirectory` that does not delete, so its contents can be inspected."""

        def __init__(self, *args, **kwargs):
            self.path = tmp_path / f"scratch-{len(made)}"
            self.path.mkdir()
            made.append(self.path)

        def __enter__(self):
            return str(self.path)

        def __exit__(self, *exc):
            return False

    monkeypatch.setattr(session.tempfile, "TemporaryDirectory", Keep)
    assert session.apply(project, started["id"])["status"] == "applied"

    assert len(made) > 1, "the merge read its three states and copied the head out"
    assert not [d for d in made if (d / ".story" / "history.db").exists()]
    assert not [d for d in made if (d / ".story" / "history").exists()]


def test_a_stale_parked_target_is_refused_and_its_head_is_unchanged(project):
    root = store.head_state(project)["base"]["id"]
    store.branch_from(project, root, "target2")
    started = _start(project, target="target2")
    # Change the parked head behind the session's back, the way another request would.
    store.switch(project, "target2")
    edit_entity(project, "character", "mira", {"name": "Moved On Target2"}, "target2")
    store.switch(project, "main")

    result = session.apply(project, started["id"])

    assert result["status"] == "refused" and result["code"] == "stale_plan"
    assert _head_name(project, "target2") == "Kael"


def test_a_complete_merge_into_a_parked_target_records_on_that_branch(project):
    """Recording on the current branch would attribute the merge to the wrong line."""
    root = store.head_state(project)["base"]["id"]
    store.branch_from(project, root, "target2")
    started = _start(project, target="target2")

    result = session.apply(project, started["id"], complete=True)

    assert result["parents"] == [_side(project)]
    assert store.get_branch(project, "main")["pending_merge_parents"] == []
    assert store.get_branch(project, "target2")["pending_merge_parents"] == [_side(project)]


# ─── helpers ────────────────────────────────────────────────────────────────


def _copy_of_side_changed(project, entity_id, name):
    """A second draft on `side` where `entity_id` differs from `main`."""
    store.switch(project, "side")
    edit_entity(project, "character", entity_id, {"name": name}, "side")
    snapshot = store.save_snapshot(project, name)["id"]
    store.switch(project, "main")
    return snapshot


def _name_of(project, entity_id):
    return diff.load(project)[0][entity_id]["fields"]["name"]


def _head_name(project, branch_id):
    head = store.head_file(project, branch_id)
    conn = sqlite3.connect(f"file:{head}?mode=ro&immutable=1", uri=True)
    try:
        return conn.execute("SELECT name FROM entities WHERE id='kael'").fetchone()[0]
    finally:
        conn.close()


def test_a_typed_value_is_stored_with_the_answer_and_replaced_by_the_next(project):
    edit_entity(project, "character", "mira", {"name": "Mira Ours"}, "ours")
    theirs = _copy_of_side_changed(project, "mira", "Mira Theirs")
    started = session.start(
        project, "main", {"kind": "snapshot", "id": theirs}, selection=["field:character:mira:name"]
    )
    key = session.show(project, started["id"])["plan"]["decisions"][0]["key"]

    typed = session.set_decision(project, started["id"], key, "custom", value="Mira Between")
    assert typed["decisions"][key]["value"] == "Mira Between"
    assert session.show(project, started["id"])["plan"]["ready"] is True

    changed = session.set_decision(project, started["id"], key, "theirs")
    assert "value" not in changed["decisions"][key]

    session.set_decision(project, started["id"], key, "custom", value="Mira Between")
    assert session.apply(project, started["id"])["status"] == "applied"
    assert _name_of(project, "mira") == "Mira Between"


def test_the_draft_saved_before_a_merge_is_named_for_its_source_not_its_id(project):
    edit_entity(project, "character", "mira", {"name": "Mira Ours"}, "ours")
    theirs = _copy_of_side_changed(project, "mira", "Mira Theirs")
    started = session.start(
        project, "main", {"kind": "snapshot", "id": theirs}, selection=["field:character:mira:name"]
    )
    key = session.show(project, started["id"])["plan"]["decisions"][0]["key"]
    session.set_decision(project, started["id"], key, "theirs")

    session.apply(project, started["id"])

    labels = [d["label"] for d in store.list_branches(project)["snapshots"]]
    source_label = next(
        d["label"] for d in store.list_branches(project)["snapshots"] if d["id"] == theirs
    )
    assert f"Before merge from {source_label}" in labels
    assert not any(theirs in label for label in labels)
