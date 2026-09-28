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

from core.constants import ENTITY_SCHEMAS  # noqa: E402
from core.drafts import commit, render_preview_md, stage, validate_shape  # noqa: E402

BATCH = [
    {"op": "create", "type": "scene", "id": "mira-tells-kael",
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
    8 of 22 — counting only the non-computed fields the model was offered.

    Was 23 until `id` left the scene schema: it was being counted as a field
    the model could fill, when the write path discards it. See
    tests/test_id_is_not_a_field.py.
    """
    md = stage(fixture_path, BATCH, "The Telling")["preview_md"]
    assert "8 of 22 fields set" in md


def test_the_count_never_enumerates_the_empty_fields(fixture_path):
    md = stage(fixture_path, BATCH, "The Telling")["preview_md"]
    header = md.split("\n")[4]
    assert "unset" not in header and "missing" not in header


def test_a_field_set_to_its_own_default_still_counts_as_set(fixture_path):
    """A fully-filled entity must not read as one field short.

    `_empty()` treats a value equal to its schema default as unfilled, which is
    right for `unfilled_fields` but wrong here: `type: "act"` is explicitly
    set and "act" is also its default, so every complete act rendered "7 of 8"
    and a complete character rendered no count at all. Presence is the test.
    """
    act = {f: m["default"] for f, m in ENTITY_SCHEMAS["act"].items()
           if not m.get("computed")}
    md = stage(fixture_path, [{"op": "create", "type": "act", "id": "a-full",
                               "frontmatter": act, "summary": "s"}],
               "a complete act")["preview_md"]
    assert "fields set" not in md.split("\n")[4]

    # `title`'s default is "", so it is not a set field — only `type` and
    # `order` carry a value. 2 of 8, and both of those equal their defaults.
    thin = {f: act[f] for f in ("type", "order")}
    md = stage(fixture_path, [{"op": "create", "type": "act", "id": "a-thin",
                               "frontmatter": thin, "summary": "s"}],
               "a thin act")["preview_md"]
    assert "2 of 8 fields set" in md


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
    assert "**Objective**\n```text\nMira confesses the reservoir is failing." in md


def test_every_section_body_carries_a_fence_tag(fixture_path):
    """A bare ``` lets the client infer the block, and a body starting with a
    markdown list broke the inference — the box came back dropped. One tag for
    every section, not a per-section exception, so the next list-shaped body
    cannot fall through it.
    """
    op = {"op": "create", "type": "character", "id": "probe",
          "frontmatter": {"name": "Probe", "story_role": "Supporting",
                          "one_sentence": "x"},
          "sections": {"Desires": "- Short: a line.\n- Long: another line.",
                       "Voice": "Quiet."},
          "summary": "probe"}
    md = stage(fixture_path, [op], "probe")["preview_md"]
    assert "**Desires**\n```text\n- Short:" in md
    assert "**Voice**\n```text\nQuiet." in md
    # Every opening fence is tagged. (Counting openers, not occurrences of
    # "```": the closing fence of a block is an untagged ``` by definition.)
    openers = [ln for ln in md.split("\n") if ln.startswith("```") and ln != "```"]
    assert len(openers) == 2, openers


def test_a_scene_content_section_is_fenced_as_fountain(fixture_path):
    """Only script is labelled. A generic fence would be fine too, but the tag
    costs nothing and names the format for whatever renders the block."""
    op = {"op": "create", "type": "scene", "id": "probe",
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


def test_a_one_line_section_is_still_fenced(fixture_path):
    """A section is fenced by where it lives, not by whether it has newlines.

    `Notes` with a single line has no `\\n`, and the renderer used to decide
    from content alone — so the same section was fenced on a create and
    rendered as a `before → after` scalar on an edit. Two shapes for one
    thing, and the short one was the broken one.
    """
    op = {"op": "edit", "entity_type": "scene", "entity_id": "central-room-day",
          "data": {"Notes": "Do not cut the pause before she answers."},
          "summary": "one line of prose"}
    md = stage(fixture_path, [op], "a note")["preview_md"]
    assert "`Notes` —" in md
    assert "```text\nDo not cut the pause before she answers." in md
    assert "`Notes`: _not set_ →" not in md


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
    return {"op": "create", "type": entity_type, "id": slug,
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


# ─── I2: a structured field must not render as a Python repr ───

def test_a_dict_field_renders_one_line_per_entry():
    """`perspectives` is the field a writer most wants to *see* when approving a
    relationship: two characters, two readings, side by side. A dict repr
    hides exactly that — single quotes, no breaks, wrapping mid-sentence."""
    from core.drafts import _fmt

    out = _fmt({"kael": {"label": "Kael", "feeling": "wary", "strength": 0.6,
                         "secret": False},
                "mira": {"label": "Mira", "feeling": "guarded", "strength": -0.3,
                         "secret": True}})
    assert "'" not in out, f"still a Python repr: {out}"
    assert "{" not in out and "}" not in out, out
    # One bolded line per character — the comparison is the point.
    assert out.count("<br>") == 1
    assert "**kael**" in out and "**mira**" in out
    assert "secret=no" in out and "secret=yes" in out


def test_a_list_of_objects_renders_one_line_per_item():
    """The same defect in the other shape, which the entry only suspected:
    `plot.setups` held a bare `{'scene_id': ...}` for the same reason."""
    from core.drafts import _fmt

    out = _fmt([{"scene_id": "s1", "description": "The lie is told here."},
                {"scene_id": "s2", "description": "And here it costs."}])
    assert "'" not in out, f"still a Python repr: {out}"
    assert out.count("<br>") == 1
    assert "scene_id: s1" in out and "description: The lie is told here." in out


def test_scalars_are_unchanged_by_the_structured_fix():
    """The one-line cases must not move: a fix that also reformats the common
    path is a fix nobody can review."""
    from core.drafts import _fmt

    assert _fmt("prose") == "prose"
    assert _fmt(True) == "yes"
    assert _fmt(False) == "no"
    assert _fmt([]) == "\u2014"
    assert _fmt({}) == "\u2014"
    assert _fmt(["kael", "mira"]) == "kael, mira"
    assert _fmt("") == "\u2014"
