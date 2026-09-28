"""Draft staging: the proposal must be inert until commit.

The whole feature rests on one claim — a staged draft is not a change. If
staging leaked a write, the user would be asked to confirm something that had
already happened, and the confirmation loop would be theatre.
"""
import json
import sqlite3
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from core import drafts  # noqa: E402
from core.db import get_db  # noqa: E402


def _counts(project_path):
    """Row counts in the three tables a stage must not touch."""
    conn = get_db(project_path)
    try:
        return {
            t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            for t in ("entities", "sections", "relations")
        }
    finally:
        conn.close()


def _batch():
    return [
        {"op": "create", "type": "scene", "slug": "mira-tells-kael",
         "frontmatter": {"title": "The Telling", "sequence_id": "seq-discovery",
                         "act_id": "act-1", "characters": ["mira", "kael"]},
         "sections": {"Objective": "Mira confesses."},
         "summary": "New scene: The Telling"},
        {"op": "edit", "entity_type": "location", "entity_id": "the-central-room",
         "data": {"mood": "claustrophobic warmth"},
         "summary": "The room tightens once Mira speaks"},
        {"op": "reorder", "entity_type": "scene", "entity_id": "seq-discovery",
         "ordered_ids": ["mira-tells-kael", "central-room-day", "central-room-night"],
         "summary": "The Telling lands mid-sequence"},
    ]


# ─── Guard 1: staging writes nothing ───

def test_stage_writes_nothing_to_the_story(fixture_path):
    """Guard 1: row counts identical before and after a stage."""
    before = _counts(fixture_path)
    result = drafts.stage(fixture_path, _batch(), "Mira tells Kael")
    assert result["success"] is True
    assert _counts(fixture_path) == before


def test_stage_writes_only_one_draft_row(fixture_path):
    """The draft itself is the only thing that lands."""
    before = _counts(fixture_path)
    drafts.stage(fixture_path, _batch(), "Mira tells Kael")
    conn = get_db(fixture_path)
    try:
        assert conn.execute("SELECT COUNT(*) FROM drafts").fetchone()[0] == 1
    finally:
        conn.close()
    after = _counts(fixture_path)
    for table in ("entities", "sections", "relations"):
        assert after[table] == before[table], table


# ─── Guard 3: discard ───

def test_discard_removes_the_draft_and_leaves_the_story_alone(fixture_path):
    """Guard 3."""
    before = _counts(fixture_path)
    staged = drafts.stage(fixture_path, _batch(), "Mira tells Kael")
    assert drafts.list_drafts(fixture_path)["count"] == 1

    result = drafts.discard(fixture_path, staged["draft_id"])
    assert result["discarded"] == staged["draft_id"]
    assert drafts.list_drafts(fixture_path)["count"] == 0
    assert _counts(fixture_path) == before


def test_discard_of_an_unknown_draft_is_refused(fixture_path):
    with pytest.raises(drafts.DraftError, match="No open draft"):
        drafts.discard(fixture_path, "d-nope")


# ─── Guard 4: restage replaces, and says what changed ───

def test_restage_replaces_the_op_list_rather_than_appending(fixture_path):
    """Guard 4: staging is a proposal, not a queue."""
    ops = _batch()
    first = drafts.stage(fixture_path, ops, "three changes")
    restaged = drafts.stage(fixture_path, ops[:2], "two changes",
                            draft_id=first["draft_id"])

    assert restaged["restaged"] is True
    assert restaged["op_count"] == 2
    assert drafts.list_drafts(fixture_path)["drafts"][0]["op_count"] == 2


def test_restage_reports_the_dropped_op(fixture_path):
    """"Don't resequence" must not look like the reorder was never proposed."""
    ops = _batch()
    first = drafts.stage(fixture_path, ops, "three changes")
    restaged = drafts.stage(fixture_path, ops[:2], "two changes",
                            draft_id=first["draft_id"])

    assert restaged["changes"]["dropped"], restaged["changes"]
    assert "reorder" in restaged["changes"]["dropped"][0]
    assert restaged["changes"]["added"] == []
    assert restaged["changes"]["changed"] == []


def test_restage_reports_a_changed_op_and_an_added_one(fixture_path):
    ops = _batch()
    first = drafts.stage(fixture_path, ops, "three changes")
    revised = [dict(ops[0], summary="The Telling, rewritten"), ops[1], {
        "op": "delete", "entity_type": "world", "entity_id": "the-wetlands",
        "summary": "Cut the wetlands world",
    }]
    restaged = drafts.stage(fixture_path, revised, "revised",
                            draft_id=first["draft_id"])

    assert len(restaged["changes"]["changed"]) == 1
    assert "summary" in restaged["changes"]["changed"][0]["fields"]
    assert restaged["changes"]["added"] == ["delete world/the-wetlands"]
    # The reorder went out with the new delete op in its place.
    assert len(restaged["changes"]["dropped"]) == 1
    assert restaged["changes"]["dropped"][0].startswith("reorder scene")


def test_restage_of_an_unknown_draft_is_refused(fixture_path):
    with pytest.raises(drafts.DraftError, match="No open draft"):
        drafts.stage(fixture_path, _batch(), "x", draft_id="d-nope")


# ─── Guard 7: the migration ───
#
# Removed. This asserted that opening a database written before draft staging
# existed would create the `drafts` table — a repair for a database no build
# has ever produced. The table is created by create_schema like every other,
# so a project that lacks it was never a project. What replaced it is below:
# a fresh project has the table, and staging works against it.


def test_drafts_table_exists_on_a_fresh_project(tmp_path):
    """create_schema makes the drafts table, so no open-time repair is needed.

    The old guard proved the opposite case — that get_db invented a missing
    table. That is a repair for a database no build has produced, and it cost a
    function plus a call on every connection. This proves the case that can
    actually happen: a project created now has the table, without get_db
    creating anything.
    """
    from core.writes import create_project

    create_project("fresh", {"name": "Fresh", "logline": "x"}, tmp_path)
    proj = tmp_path / "projects" / "fresh"

    conn = get_db(proj)
    try:
        tables = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        assert "drafts" in tables
    finally:
        conn.close()

    # And usable, not merely present — the old guard's second half.
    result = drafts.stage(proj, _batch(), "staged against a fresh project")
    assert result["success"] is True


# ─── list ───

def test_list_reports_id_summary_age_and_op_count(fixture_path):
    """Decision 6: no staleness verdict, just the facts to ask a question on."""
    drafts.stage(fixture_path, _batch(), "Mira tells Kael")
    result = drafts.list_drafts(fixture_path)
    assert result["count"] == 1
    entry = result["drafts"][0]
    assert set(entry) == {"id", "summary", "created_at", "op_count"}
    assert entry["op_count"] == 3
    assert entry["summary"] == "Mira tells Kael"
    assert entry["created_at"]


def test_list_on_a_project_with_no_drafts_is_empty_not_an_error(fixture_path):
    assert drafts.list_drafts(fixture_path) == {
        "success": True, "drafts": [], "count": 0}


# ─── op validation ───

@pytest.mark.parametrize("bad,message", [
    ([], "non-empty list"),
    ([{"op": "explode", "summary": "x"}], "must be one of"),
    ([{"op": "create", "type": "scene", "summary": "x"}], "missing: slug, frontmatter"),
    ([{"op": "edit", "entity_type": "scene", "summary": "x"}],
     "missing: entity_id, data"),
    ([{"op": "create", "type": "sculpture", "slug": "x", "frontmatter": {},
       "summary": "x"}], "unknown entity_type"),
    ([{"op": "create", "type": "project", "slug": "new-film", "frontmatter": {},
       "summary": "x"}], "projects cannot be drafted"),
    ([{"op": "create", "type": "scene", "slug": "bad slug!", "frontmatter": {},
       "summary": "x"}], "alphanumeric"),
    ([{"op": "reorder", "entity_type": "sequence", "ordered_ids": [],
       "summary": "x"}], "non-empty list"),
])
def test_a_malformed_op_is_refused_at_stage_time(bad, message):
    with pytest.raises(drafts.DraftError, match=message):
        drafts.validate_ops(bad)


def test_a_malformed_op_never_reaches_the_drafts_table(fixture_path):
    before = drafts.list_drafts(fixture_path)["count"]
    with pytest.raises(drafts.DraftError):
        drafts.stage(fixture_path, [{"op": "create", "type": "scene"}], "nope")
    assert drafts.list_drafts(fixture_path)["count"] == before


# ─── op vocabulary ───

def test_op_order_is_create_edit_delete_reorder():
    assert [k for k, _ in sorted(drafts.OP_ORDER.items(), key=lambda kv: kv[1])] == \
        ["create", "edit", "delete", "reorder"]


def test_a_batch_may_hold_two_ops_on_the_same_entity():
    """The diff must not collapse them — a dict keyed on identity would."""
    ops = [
        {"op": "edit", "entity_type": "location", "entity_id": "the-central-room",
         "data": {"mood": "warm"}, "summary": "first"},
        {"op": "edit", "entity_type": "location", "entity_id": "the-central-room",
         "data": {"mood": "cold"}, "summary": "second"},
    ]
    result = drafts.diff_ops(ops, ops[:1])
    assert result["dropped"], result


# ─── commit ───

def _rows(project_path, sql, *params):
    conn = get_db(project_path)
    try:
        return conn.execute(sql, params).fetchall()
    finally:
        conn.close()


def _create_scene(slug, sequence_id="seq-discovery", **frontmatter):
    fm = {"title": slug, "sequence_id": sequence_id, "act_id": "act-1"}
    fm.update(frontmatter)
    return {"op": "create", "type": "scene", "slug": slug,
            "frontmatter": fm, "sections": {}, "summary": f"new {slug}"}


def test_commit_writes_the_batch_and_clears_the_draft(fixture_path):
    staged = drafts.stage(fixture_path, _batch(), "Mira tells Kael")
    result = drafts.commit(fixture_path, staged["draft_id"])

    assert result["success"] is True
    assert result["committed"] is True
    assert result["draft_id"] == staged["draft_id"]
    assert len(result["applied"]) == 3
    assert drafts.list_drafts(fixture_path)["count"] == 0
    assert _rows(fixture_path, "SELECT name FROM entities WHERE id=?",
                 "mira-tells-kael")


def test_commit_of_an_unknown_draft_is_refused(fixture_path):
    with pytest.raises(drafts.DraftError, match="No open draft"):
        drafts.commit(fixture_path, "d-nope")


# ─── Guard 2: partial failure keeps the draft and names what landed ───

def test_a_failing_batch_keeps_the_draft_and_names_what_landed(fixture_path):
    """Guard 2: atomic per op, resumable per batch — not all-or-nothing."""
    ops = [
        _create_scene("mira-tells-kael"),
        # Fails: no such sequence.
        {"op": "reorder", "entity_type": "sequence", "entity_id": "act-two",
         "ordered_ids": ["a", "b"], "summary": "Resequence act two"},
    ]
    staged = drafts.stage(fixture_path, ops, "two changes")
    result = drafts.commit(fixture_path, staged["draft_id"])

    assert result["success"] is False
    assert result["draft_kept"] is True
    assert result["committed"] == ["create scene/mira-tells-kael"]
    assert "act-two" in result["failed"]["error"] or \
        "not found" in result["failed"]["error"]
    # The resume token survives, and the create that landed is not repeated.
    assert drafts.list_drafts(fixture_path)["count"] == 1
    assert _rows(fixture_path, "SELECT COUNT(*) FROM entities WHERE id=?",
                 "mira-tells-kael")[0][0] == 1


def test_a_recommitted_draft_refuses_the_op_that_already_landed(fixture_path):
    """The re-stage path the partial-failure message tells the agent to take."""
    ops = [
        _create_scene("mira-tells-kael"),
        {"op": "reorder", "entity_type": "sequence", "entity_id": "act-two",
         "ordered_ids": ["a", "b"], "summary": "Resequence act two"},
    ]
    staged = drafts.stage(fixture_path, ops, "two changes")
    drafts.commit(fixture_path, staged["draft_id"])

    again = drafts.commit(fixture_path, staged["draft_id"])
    assert again["success"] is False
    assert again["committed"] == []
    assert "already exists" in again["failed"]["error"]


# ─── Guard 5: ordering ───

def test_commit_orders_creates_before_edits_deletes_and_reorders(fixture_path):
    """Guard 5: written in the order that would fail, sorted by commit."""
    ops = [
        {"op": "reorder", "entity_type": "scene", "entity_id": "seq-discovery",
         "ordered_ids": ["mira-tells-kael", "central-room-day", "central-room-night"],
         "summary": "order the new scene"},
        {"op": "edit", "entity_type": "scene", "entity_id": "mira-tells-kael",
         "data": {"status": "drafted"}, "summary": "mark it drafted"},
        _create_scene("mira-tells-kael"),
    ]
    assert [op["op"] for op in drafts.sorted_ops(ops)] == \
        ["create", "edit", "reorder"]

    staged = drafts.stage(fixture_path, ops, "a new scene, in three parts")
    result = drafts.commit(fixture_path, staged["draft_id"])
    assert result["success"] is True, result


def test_sorted_ops_is_stable_within_a_kind():
    """Two creates where the second references the first must keep their order."""
    ops = [_create_scene("first"), _create_scene("second")]
    assert drafts.sorted_ops(ops) == ops


# ─── Guard 6: relations ride inside the frontmatter ───

def test_a_committed_create_carrying_cast_produces_relation_rows(fixture_path):
    """Guard 6: relations come from frontmatter, and an op that lost them would
    pass every other test in this file."""
    staged = drafts.stage(
        fixture_path,
        [_create_scene("mira-tells-kael", characters=["mira", "kael"])],
        "new scene with cast",
    )
    assert drafts.commit(fixture_path, staged["draft_id"])["success"] is True

    rels = _rows(fixture_path,
                 "SELECT from_id, to_id, kind FROM relations "
                 "WHERE from_id='mira-tells-kael'")
    assert ("mira-tells-kael", "mira", "character_scene") in rels
    assert ("mira-tells-kael", "kael", "character_scene") in rels


# ─── delete ───

def test_a_committed_delete_soft_deletes_and_is_reversible(fixture_path):
    """The loop synthesises confirm=True; the delete is still a flag."""
    ops = [{"op": "delete", "entity_type": "location",
            "entity_id": "the-central-room", "summary": "Cut the room"}]
    staged = drafts.stage(fixture_path, ops, "cut a location")
    result = drafts.commit(fixture_path, staged["draft_id"])

    assert result["success"] is True, result
    assert _rows(fixture_path,
                 "SELECT is_deleted FROM entities WHERE id='the-central-room'"
                 )[0][0] == 1
    # Prose survives, so `restore` is an exact inverse.
    assert _rows(fixture_path,
                 "SELECT COUNT(*) FROM sections WHERE entity_id='the-central-room'"
                 )[0][0] > 0


# ─── no flag-based drift (guard 8) ───

def test_no_entity_is_flagged_as_a_draft():
    """Guard 8: `is_draft` anywhere means the design drifted to the flag approach."""
    offenders = []
    for folder in ("core", "tools"):
        for path in (REPO / folder).rglob("*.py"):
            if "is_draft" in path.read_text(encoding="utf-8"):
                offenders.append(str(path.relative_to(REPO)))
    assert not offenders, f"draft flag leaked into the entity model: {offenders}"
