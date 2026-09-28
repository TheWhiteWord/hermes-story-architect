"""The preview the user actually reads, and the shape findings beside it.

Two things are asserted here that no other test covers: that each op kind
leaves a recognisable marker in the rendered block, and that stage-time
validation reports what is wrong with a shape while staying silent about a
cross-entity reference that is not wrong yet.
"""
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from core.drafts import commit, render_preview_md, stage, validate_shape  # noqa: E402

BATCH = [
    {"op": "create", "type": "scene", "slug": "mira-tells-kael",
     "frontmatter": {"title": "The Telling", "sequence_id": "seq-discovery",
                     "act_id": "act-1", "status": "drafted", "time_of_day": "DUSK",
                     "location": "the-central-room", "characters": ["mira", "kael"],
                     "dramatic_role": "crisis"},
     "sections": {"Objective": "Mira confesses the reservoir is failing."},
     "summary": "New scene: The Telling"},
    {"op": "edit", "entity_type": "location", "entity_id": "the-central-room",
     "data": {"mood": "claustrophobic warmth"},
     "summary": "The room tightens once Mira speaks"},
    {"op": "delete", "entity_type": "world", "entity_id": "the-real-world",
     "summary": "Cut the parallel world"},
    {"op": "reorder", "entity_type": "scene", "entity_id": "seq-discovery",
     "ordered_ids": ["central-room-day", "mira-tells-kael", "central-room-night",
                     "the-core-day"],
     "summary": "The Telling lands mid-sequence"},
]


# ─── the renderer ───

def test_the_block_carries_a_marker_for_every_op_kind(fixture_path):
    """Each kind must be recognisable at a glance — that is the whole point."""
    md = stage(fixture_path, BATCH, "The Telling")["preview_md"]
    assert "**＋ NEW SCENE**" in md
    assert "**✏ EDIT**" in md
    assert "**🗑 DELETE**" in md
    assert "**↕ REORDER**" in md


def test_the_block_carries_the_field_count(fixture_path):
    """Decision 1: a count, not a list. The batch's create sets 8 fields, so
    8 of 23 — counting only the non-computed fields the model was offered."""
    md = stage(fixture_path, BATCH, "The Telling")["preview_md"]
    assert "8 of 23 fields set" in md


def test_the_count_never_enumerates_the_empty_fields(fixture_path):
    md = stage(fixture_path, BATCH, "The Telling")["preview_md"]
    header = md.split("\n")[4]
    assert "unset" not in header and "missing" not in header


def test_an_edit_renders_one_line_per_changed_field(fixture_path):
    """Decision 2: a delta, not a table. Two fields, two lines."""
    op = {"op": "edit", "entity_type": "location", "entity_id": "the-central-room",
          "data": {"mood": "warm", "dramatic_function": "the trap closes"},
          "summary": "two fields"}
    md = stage(fixture_path, [op], "two fields")["preview_md"]
    lines = [ln for ln in md.split("\n") if ln.startswith("`")]
    assert len(lines) == 2
    assert not any(ln.startswith("|") for ln in md.split("\n"))


def test_an_unset_field_reads_as_not_set_not_as_a_blank(fixture_path):
    """The fixture's location has no mood, so a blank before the arrow would
    read as a rendering fault rather than as 'this was empty'."""
    op = {"op": "edit", "entity_type": "location", "entity_id": "the-central-room",
          "data": {"mood": "claustrophobic warmth"}, "summary": "set the mood"}
    md = stage(fixture_path, [op], "set the mood")["preview_md"]
    assert "`mood`: _not set_ → **claustrophobic warmth**" in md


def test_the_prose_an_op_carries_is_rendered(fixture_path):
    """Prose is fenced, one block per section (D), not flattened onto the
    heading line — a body whose whitespace matters cannot be a `— body` line."""
    md = stage(fixture_path, BATCH, "The Telling")["preview_md"]
    assert "**Objective**" in md
    assert "Mira confesses the reservoir is failing." in md
    # The body sits inside a fence, immediately after its heading.
    assert "**Objective**\n```\nMira confesses the reservoir is failing." in md


def test_a_scene_content_section_is_fenced_as_fountain(fixture_path):
    """Only script is labelled. A generic fence would be fine too, but the tag
    costs nothing and names the format for whatever renders the block."""
    op = {"op": "create", "type": "scene", "slug": "probe",
          "frontmatter": {"title": "Probe", "time_of_day": "NIGHT"},
          "sections": {"Content": "INT. LAMP ROOM - NIGHT\n\n                ELIAS\n        Still going.\n"},
          "summary": "probe"}
    md = stage(fixture_path, [op], "probe")["preview_md"]
    assert "**Content**\n```fountain\nINT. LAMP ROOM - NIGHT" in md


def test_a_multi_line_section_change_is_stated_then_fenced(fixture_path):
    """C: the one-line delta goes outside the block, the body inside. A
    screenplay diff line is unreadable, and two full copies is worse."""
    op = {"op": "edit", "entity_type": "scene", "entity_id": "mira-tells-kael",
          "data": {"Content": "INT. ROOM - NIGHT\n\nOne.\n\n                MARA\n        Two.\n"},
          "summary": "reformat as script"}
    md = stage(fixture_path, [op], "reformat")["preview_md"]
    assert "`Content` —" in md
    assert "~~" not in md.split("```fountain")[0]  # no struck-through body
    assert "```fountain\nINT. ROOM - NIGHT" in md


def test_a_scalar_field_still_renders_before_after(fixture_path):
    """The fence is for bodies, not fields: a one-line value is still a delta."""
    op = {"op": "edit", "entity_type": "location", "entity_id": "the-central-room",
          "data": {"mood": "claustrophobic warmth"}, "summary": "set the mood"}
    md = stage(fixture_path, [op], "set the mood")["preview_md"]
    assert "`mood`: _not set_ → **claustrophobic warmth**" in md
    assert "```" not in md


def test_the_restage_diff_is_in_the_preview(fixture_path):
    """Decision 3: without it, a dropped op is indistinguishable from one
    that was never proposed."""
    first = stage(fixture_path, BATCH, "four changes")
    again = stage(fixture_path, BATCH[:2], "two changes",
                  draft_id=first["draft_id"])
    assert "**since last stage**" in again["preview_md"]
    assert "－ reorder scene (4 items)" in again["preview_md"]


def test_a_first_stage_has_no_diff_section(fixture_path):
    md = stage(fixture_path, BATCH, "The Telling")["preview_md"]
    assert "since last stage" not in md


def test_the_preview_names_the_project_and_the_op_count(fixture_path):
    md = stage(fixture_path, BATCH, "The Telling")["preview_md"]
    assert "**Save the Children** · 4 changes" in md
    assert "The Telling" in md


def test_a_commit_report_is_terse_and_names_what_landed(fixture_path):
    """Decision 4: the user read the detail moments ago. Repeating it is noise."""
    staged = stage(fixture_path, BATCH, "The Telling")
    md = commit(fixture_path, staged["draft_id"])["preview_md"]
    assert "✅ Committed" in md
    assert "create scene/mira-tells-kael" in md
    # The full field table is NOT repeated.
    assert "| field | value |" not in md


def test_a_partial_failure_report_warns_that_the_project_is_mixed(fixture_path):
    """The user is now looking at a partly-saved project; this message is the
    only thing that says so."""
    ops = BATCH + [{"op": "reorder", "entity_type": "sequence",
                    "entity_id": "act-two", "ordered_ids": ["a", "b"],
                    "summary": "Resequence act two"}]
    staged = stage(fixture_path, ops, "five changes")
    md = commit(fixture_path, staged["draft_id"])["preview_md"]
    assert "⚠️ Partly saved" in md
    assert "❌" in md
    assert "still open, so nothing is lost" in md


def test_rendering_reads_but_never_writes(fixture_path):
    """A preview is presentation. Rendering it must not change the story."""
    from core.db import get_db
    conn = get_db(fixture_path)
    try:
        before = conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0]
    finally:
        conn.close()
    render_preview_md(fixture_path, BATCH, "d-x", "Save the Children", "x")
    conn = get_db(fixture_path)
    try:
        assert conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0] == before
    finally:
        conn.close()


# ─── shape validation ───

def _create(fm, entity_type="scene", slug="new-scene"):
    return {"op": "create", "type": entity_type, "slug": slug,
            "frontmatter": fm, "sections": {}, "summary": "x"}


def test_a_bad_enum_and_a_missing_required_field_are_both_reported(fixture_path):
    """The plan's own check: both kinds of finding, in one stage."""
    findings = validate_shape([_create({
        "sequence_id": "seq-discovery", "act_id": "act-1",
        "status": "nonsense", "time_of_day": "MIDNIGHT",
    })])
    assert any("Invalid status: nonsense" in f for f in findings)
    assert any("Invalid time_of_day: MIDNIGHT" in f for f in findings)
    assert any("Missing required field: title" in f for f in findings)


def test_a_missing_required_field_is_measured_on_the_merged_frontmatter(fixture_path):
    """The merge is the point: a field absent from the op but defaulted by the
    schema is NOT missing, and only a field defaulting to empty is."""
    assert validate_shape([_create({"title": "T", "sequence_id": "s", "act_id": "a"})]) == []
    assert validate_shape([_create({"sequence_id": "s", "act_id": "a"})]) != []


def test_an_unknown_field_is_reported_rather_than_written(fixture_path):
    """It would land in `extra` verbatim — a field the caller misspelled
    would be indistinguishable from one the schema does not define."""
    findings = validate_shape([_create({
        "title": "T", "sequence_id": "s", "act_id": "a", "colour": "blue"})])
    assert any("unknown scene field 'colour'" in f for f in findings)


def test_a_valid_cross_entity_reference_that_does_not_exist_yet_is_silent(fixture_path):
    """The design's deliberate omission, asserted rather than merely absent.

    A staged create's id is not in the database, so every reference a batch
    makes to a sibling op would report a false error. Those checks run at
    commit, where the earlier op has already landed.
    """
    ops = [
        # References act-1, which exists.
        _create({"title": "One", "sequence_id": "seq-discovery", "act_id": "act-1"},
                slug="scene-one"),
        # References a sequence created by a LATER op in the same batch —
        # legal in the op list, absent from the database right now.
        _create({"title": "Two", "sequence_id": "not-yet-created", "act_id": "act-1"},
                slug="scene-two"),
    ]
    assert not any("not-yet-created" in f for f in validate_shape(ops))


def test_shape_validation_needs_no_database(fixture_path):
    """It runs on the in-memory merged frontmatter, so a fresh project works."""
    fresh = fixture_path.parent / "brand-new"
    assert validate_shape([_create({"title": "T", "sequence_id": "s", "act_id": "a"})]) == []


def test_edits_and_deletes_and_reorders_produce_no_findings(fixture_path):
    """Nothing shape-checkable in them: their fields are checked
    at commit, against the real row."""
    assert validate_shape(BATCH[1:]) == []


def test_the_stage_response_carries_validation_and_preview(fixture_path):
    result = stage(fixture_path, BATCH, "The Telling")
    assert result["validation"] == []
    assert result["preview_md"].startswith("### 📝 Draft")


def test_a_restage_re_reports_findings(fixture_path):
    """A revision that breaks an enum must be caught on the restage, not
    three commit attempts later."""
    first = stage(fixture_path, BATCH, "ok")
    broken = [dict(BATCH[0], frontmatter=dict(BATCH[0]["frontmatter"],
                                              status="nonsense"))]
    again = stage(fixture_path, broken, "ok", draft_id=first["draft_id"])
    assert any("Invalid status: nonsense" in f for f in again["validation"])


# ─── the mock in chat-preview.md is not valid input ───

def test_the_chat_preview_mock_would_not_pass_validation():
    """`chat-preview.md` writes value_at_open="hope". VALUE_CHARGES is
    positive/negative/mixed/ironic. The mock is illustrative; the validator
    is right. Recorded so nobody 'fixes' the validator to match the mock."""
    from core.constants import VALUE_CHARGES
    assert "hope" not in VALUE_CHARGES
    findings = validate_shape([_create({
        "title": "The Telling", "sequence_id": "seq-discovery", "act_id": "act-1",
        "value_at_open": "hope", "value_at_close": "doubt"})])
    assert any("Invalid value_at_open: hope" in f for f in findings)
