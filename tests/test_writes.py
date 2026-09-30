"""core/writes.py — the write path, called directly.

Every mutation in the plugin funnels through these functions. A staged draft
replays ops straight into them, so the invariant worth holding here is narrow
and specific: **calling them directly must land exactly the rows a committed
draft would land.** A divergence here is invisible until a committed draft
quietly writes the wrong thing.
"""
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from core import writes  # noqa: E402
from core.db import get_db  # noqa: E402


def test_core_never_imports_tools():
    """`core/` is the layer everything else sits on; `tools/` imports down into it.

    Draft staging is the temptation: a committed op has to be replayed
    somewhere, and reaching up into `tools/` to do it would invert the layering
    again — silently, because nothing else would fail.
    """
    import ast

    offenders = []
    for path in sorted((REPO / "core").glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and (node.module or "").startswith("tools"):
                offenders.append(f"{path.name}: from {node.module}")
            elif isinstance(node, ast.Import):
                offenders += [f"{path.name}: import {a.name}"
                              for a in node.names if a.name.startswith("tools")]
    assert not offenders, f"core/ must not import tools/: {offenders}"


def _q(project_path, sql, params=()):
    conn = get_db(project_path)
    try:
        return conn.execute(sql, params).fetchall()
    finally:
        conn.close()


# ─── create_entity ───

class TestCreateEntity:
    def test_lands_the_row_and_the_relation(self, fixture_path):
        before = len(_q(fixture_path, "SELECT 1 FROM entities"))
        result = writes.create_entity(
            fixture_path, "scene", "mira-tells-kael",
            {"title": "The Telling", "sequence_id": "seq-discovery",
             "act_id": "act-1", "characters": ["mira", "kael"]},
            {"Objective": "Mira confesses."},
        )
        assert result["success"] is True
        assert result["entity_id"] == "mira-tells-kael"
        assert len(_q(fixture_path, "SELECT 1 FROM entities")) == before + 1
        assert _q(fixture_path,
                  "SELECT one_sentence FROM entities WHERE id=?", ("mira-tells-kael",))

    def test_standard_sections_are_all_created(self, fixture_path):
        """Every standard section exists whether or not prose was supplied."""
        writes.create_entity(fixture_path, "scene", "quiet-room", {"title": "Quiet"})
        headings = {r[0] for r in _q(
            fixture_path, "SELECT heading FROM sections WHERE entity_id=?",
            ("quiet-room",))}
        from core.entity import standard_sections
        assert set(standard_sections("scene")) <= headings

    def test_nonstandard_heading_is_rejected(self, fixture_path):
        """The section set is closed. edit_entity already refused one; create
        accepted it, so the same key was valid on one path and an error on the
        other. A rejected create writes nothing."""
        before = len(_q(fixture_path, "SELECT 1 FROM entities"))
        with pytest.raises(ValueError, match="closed"):
            writes.create_entity(fixture_path, "scene", "odd-scene", {"title": "Odd"},
                                 {"Beat Sheet": "something bespoke"})
        assert len(_q(fixture_path, "SELECT 1 FROM entities")) == before
        assert not _q(fixture_path,
                      "SELECT 1 FROM sections WHERE entity_id=?", ("odd-scene",))

    def test_rejection_names_the_valid_sections(self, fixture_path):
        """An error naming nothing actionable gets retried the same wrong way."""
        from core.entity import standard_sections
        with pytest.raises(ValueError) as exc:
            writes.create_entity(fixture_path, "scene", "odd2", {"title": "Odd"},
                                 {"Beat Sheet": "x"})
        message = str(exc.value)
        assert "Beat Sheet" in message
        for name in standard_sections("scene")[:3]:
            assert name in message

    def test_duplicate_slug_raises_and_writes_nothing(self, fixture_path):
        before = len(_q(fixture_path, "SELECT 1 FROM entities"))
        with pytest.raises(ValueError, match="already exists"):
            writes.create_entity(fixture_path, "scene", "central-room-day", {"title": "Dup"})
        assert len(_q(fixture_path, "SELECT 1 FROM entities")) == before

    def test_slug_collision_across_types_names_the_occupant(self, fixture_path):
        """Ids are global: a retrying caller must be told who holds the name."""
        with pytest.raises(ValueError, match="already used by a scene"):
            writes.create_entity(fixture_path, "location", "central-room-day", {"name": "X"})

    def test_unknown_entity_type_raises_and_names_the_valid_ones(self, fixture_path):
        with pytest.raises(ValueError, match="Unknown entity_type"):
            writes.create_entity(fixture_path, "widget", "w1", {})

    def test_path_traversal_slug_rejected(self, fixture_path):
        with pytest.raises(ValueError, match="Slug must be alphanumeric"):
            writes.create_entity(fixture_path, "location", "../../etc/passwd", {"name": "X"})

    def test_new_scene_is_auto_ordered_last(self, fixture_path):
        writes.create_entity(fixture_path, "scene", "late-scene",
                             {"title": "Late", "sequence_id": "seq-discovery"})
        existing = [r[0] for r in _q(
            fixture_path,
            "SELECT order_key FROM entities WHERE type='scene' AND id!=? "
            "AND parent_id='seq-discovery'", ("late-scene",))]
        mine = _q(fixture_path, "SELECT order_key FROM entities WHERE id=?",
                  ("late-scene",))[0][0]
        assert mine > max(existing), "auto-order must land after the existing scenes"

    def test_missing_parent_sequence_raises(self, fixture_path):
        with pytest.raises(ValueError, match="Sequence not found"):
            writes.create_entity(fixture_path, "scene", "orphan",
                                 {"title": "Orphan", "sequence_id": "no-such-seq"})


# ─── edit_entity ───

class TestEditEntity:
    def test_column_field_lands_in_the_column(self, fixture_path):
        """A mapped schema field writes the COLUMN, not `extra`."""
        result = writes.edit_entity(
            fixture_path, "location", "the-central-room",
            {"one_sentence": "A room with no windows."}, "one-liner")
        assert result["success"] is True
        assert result["applied"]["fields"] == ["one_sentence"]
        assert _q(fixture_path, "SELECT one_sentence FROM entities WHERE id=?",
                  ("the-central-room",))[0][0] == "A room with no windows."
        # And not in extra, which is the failure mode of a stale column map.
        extra = _q(fixture_path, "SELECT extra FROM entities WHERE id=?",
                   ("the-central-room",))[0][0]
        assert "one_sentence" not in extra

    def test_unmapped_field_lands_in_extra(self, fixture_path):
        writes.edit_entity(fixture_path, "location", "the-central-room",
                           {"mood": "claustrophobic"}, "mood")
        extra = json.loads(_q(fixture_path, "SELECT extra FROM entities WHERE id=?",
                              ("the-central-room",))[0][0])
        assert extra["mood"] == "claustrophobic"

    def test_section_name_lands_in_the_sections_table(self, fixture_path):
        writes.edit_entity(fixture_path, "location", "the-central-room",
                           {"Description": "A low room."}, "prose")
        body = _q(fixture_path,
                  "SELECT body FROM sections WHERE entity_id=? AND heading='Description'",
                  ("the-central-room",))
        assert body and body[0][0] == "A low room."

    def test_relation_field_rewrites_only_its_own_kind(self, fixture_path):
        """Writing a scene's cast must not disturb existing relations.

        The scene's cast rows are keyed on to_id (character→scene, the
        importer's direction), so the delete is keyed there too. Keying the
        delete on from_id would leave the old cast in place and append a
        second copy of the new one.
        """
        before = _q(fixture_path, "SELECT from_id, to_id, kind FROM relations ORDER BY from_id, to_id")
        writes.edit_entity(fixture_path, "scene", "central-room-day",
                           {"characters": ["mira"]}, "recast")
        owned = [r[0] for r in _q(
            fixture_path,
            "SELECT from_id FROM relations WHERE to_id=? AND kind='character_scene'",
            ("central-room-day",))]
        assert owned == ["mira"]
        survivors = [r for r in _q(
            fixture_path, "SELECT from_id, to_id, kind FROM relations ORDER BY from_id, to_id")
            if r[1] != "central-room-day"]
        assert survivors == [r for r in before if r[1] != "central-room-day"]

    def test_response_names_what_landed(self, fixture_path):
        result = writes.edit_entity(
            fixture_path, "location", "the-central-room",
            {"mood": "warmer", "Description": "Warmer still."}, "two things")
        assert result["applied"] == {"fields": ["mood"], "sections": ["Description"],
                                     "relations": []}

    def test_unrecognised_key_raises_and_names_the_valid_ones(self, fixture_path):
        """A nested call used to be dumped into `extra` and silently lost."""
        before = _q(fixture_path, "SELECT extra FROM entities WHERE id=?",
                    ("the-central-room",))
        with pytest.raises(ValueError, match="Unrecognised"):
            writes.edit_entity(fixture_path, "location", "the-central-room",
                               {"frontmatter": {"mood": "x"}}, "nested")
        assert _q(fixture_path, "SELECT extra FROM entities WHERE id=?",
                  ("the-central-room",)) == before

    def test_missing_entity_raises(self, fixture_path):
        with pytest.raises(ValueError, match="Entity not found"):
            writes.edit_entity(fixture_path, "location", "no-such-place",
                               {"mood": "x"}, "s")

    def test_arc_beat_id_is_the_beat_own_slug(self, fixture_path):
        """A beat's id is its own slug — the character link is parent_id.

        It used to be stored as '{character}-{beat}', which made the id a join
        of two fields: ambiguous to parse back (a character named `kael-the`
        with a beat `choice` produced `kael-the-choice`, same as kael/the-choice)
        and impossible to look up without a pattern match.
        """
        created = writes.create_entity(
            fixture_path, "arc_beat", "beat-nine",
            {"label": "Beat Nine", "character": "kael",
             "scene": "central-room-day", "action": "stays silent"})
        assert created["entity_id"] == "beat-nine"
        # the character link is unaffected — it never came from the id
        assert _q(fixture_path, "SELECT parent_id FROM entities WHERE id=?",
                  ("beat-nine",))[0][0] == "kael"

    def test_arc_beat_edits_the_beat_named_and_no_other(self, fixture_path):
        """Two characters, same beat label: an edit must touch exactly one.

        This is the silent wrong-entity write. The id used to be
        '{character}-{beat}' and a bare beat label resolved through
        `id LIKE '%-{slug}'`, which matched both rows and took the first — so
        editing Mira's beat silently rewrote Kael's and returned success.
        """
        for who, char in (("kael", "kael"), ("mira", "mira")):
            writes.create_entity(
                fixture_path, "arc_beat", f"{who}-choice",
                {"label": "The Choice", "character": char,
                 "scene": "central-room-day", "action": f"{who}'s choice"})

        # A bare label is now simply not an id.
        with pytest.raises(ValueError, match="not found"):
            writes.edit_entity(fixture_path, "arc_beat", "the-choice",
                               {"label": "x"}, "s")

        # Each full id edits its own beat and leaves the other alone.
        writes.edit_entity(fixture_path, "arc_beat", "mira-choice",
                           {"label": "Mira's revised choice"}, "s")
        assert _q(fixture_path, "SELECT name FROM entities WHERE id=?",
                  ("mira-choice",))[0][0] == "Mira's revised choice"
        assert _q(fixture_path, "SELECT name FROM entities WHERE id=?",
                  ("kael-choice",))[0][0] == "The Choice"

    def test_computed_field_is_skipped_not_written(self, fixture_path):
        result = writes.edit_entity(fixture_path, "character", "kael",
                                    {"relationships": [{"partner": "mira"}]}, "s")
        assert result["skipped_read_only"] == ["relationships"]
        assert result["warning"]
        assert not result["applied"]["fields"]


# ─── current_values ───

class TestPreviews:
    def test_current_values_reports_before_and_to(self, fixture_path):
        before = writes.current_values(fixture_path, "location", "the-central-room",
                                      {"mood": "new mood"})
        assert before["dry_run"] is True
        change = [c for c in before["changes"] if c["field"] == "mood"][0]
        assert change["to"] == "new mood" and change["from"] != "new mood"

    def test_current_values_touches_nothing(self, fixture_path):
        before = _q(fixture_path, "SELECT id, name, extra FROM entities ORDER BY id")
        writes.current_values(fixture_path, "location", "the-central-room",
                              {"mood": "new mood", "Description": "new prose"})
        assert _q(fixture_path, "SELECT id, name, extra FROM entities ORDER BY id") == before


# ─── delete_entity ───

class TestDeleteEntity:
    def test_refuses_without_confirm_and_writes_nothing(self, fixture_path):
        before = _q(fixture_path, "SELECT id, is_deleted FROM entities ORDER BY id")
        result = writes.delete_entity(fixture_path, "location", "the-central-room", "s")
        assert "error" in result
        assert "the-central-room" in result["would_delete"]
        assert _q(fixture_path, "SELECT id, is_deleted FROM entities ORDER BY id") == before

    def test_confirmed_delete_flags_rather_than_removes(self, fixture_path):
        """Flag, not DELETE — sections and relations survive for an exact restore."""
        result = writes.delete_entity(fixture_path, "location", "the-central-room",
                                      "s", confirm=True)
        assert result["success"] is True and result["reversible"] is True
        assert _q(fixture_path, "SELECT is_deleted FROM entities WHERE id=?",
                  ("the-central-room",))[0][0] == 1
        assert _q(fixture_path, "SELECT COUNT(*) FROM sections WHERE entity_id=?",
                  ("the-central-room",))[0][0] > 0

    def test_structural_children_block_the_delete(self, fixture_path):
        """A sequence with scenes is refused outright, confirm or not."""
        result = writes.delete_entity(fixture_path, "sequence", "seq-discovery",
                                      "s", confirm=True)
        assert "error" in result
        assert result["blocking_children"]
        assert _q(fixture_path, "SELECT is_deleted FROM entities WHERE id=?",
                  ("seq-discovery",))[0][0] == 0

    def test_cascade_scrubs_dangling_relation_targets(self, fixture_path):
        """A live entity must not be left pointing at a deleted id."""
        writes.delete_entity(fixture_path, "location", "the-central-room",
                             "s", confirm=True)
        dead = {"the-central-room"}
        for from_id, to_id in _q(fixture_path, "SELECT from_id, to_id FROM relations"):
            assert not (to_id in dead and from_id not in dead), \
                f"{from_id} still points at deleted {to_id}"

    def test_missing_entity_raises(self, fixture_path):
        with pytest.raises(ValueError, match="Entity not found"):
            writes.delete_entity(fixture_path, "location", "no-such-place", "s",
                                 confirm=True)


# ─── reorder ───

class TestReorder:
    def test_renumbers_from_the_given_list(self, fixture_path):
        ids = [r[0] for r in _q(
            fixture_path,
            "SELECT id FROM entities WHERE type='scene' AND parent_id='seq-discovery'")]
        wanted = list(reversed(ids))
        writes.reorder(fixture_path, "scene", wanted, "resequence")
        got = [r[0] for r in _q(
            fixture_path,
            "SELECT id FROM entities WHERE type='scene' AND parent_id='seq-discovery' "
            "ORDER BY order_key")]
        assert got == wanted

    def test_foreign_entity_rejected_and_nothing_moved(self, fixture_path):
        """Mixing entities from two parents is refused, and nothing renumbers."""
        writes.create_entity(fixture_path, "sequence", "seq-2",
                             {"title": "Two", "act_id": "act-1"})
        writes.create_entity(fixture_path, "scene", "scene-2",
                             {"title": "Two", "sequence_id": "seq-2"})
        before = _q(fixture_path, "SELECT id, order_key FROM entities ORDER BY id")
        with pytest.raises(ValueError, match="does not belong"):
            writes.reorder(fixture_path, "scene",
                           ["central-room-day", "scene-2"], "s")
        assert _q(fixture_path, "SELECT id, order_key FROM entities ORDER BY id") == before

    def test_unknown_id_rejected(self, fixture_path):
        with pytest.raises(ValueError, match="scene not found"):
            writes.reorder(fixture_path, "scene", ["no-such-scene"], "s")

    def test_unknown_entity_type_rejected(self, fixture_path):
        with pytest.raises(ValueError, match="not supported"):
            writes.reorder(fixture_path, "location", ["the-central-room"], "s")


# ─── create_project ───

class TestCreateProject:
    def test_creates_the_folder_and_db(self, tmp_path):
        result = writes.create_project("new-film", {"name": "New Film"}, tmp_path)
        assert result["success"] is True
        assert (tmp_path / "projects" / "new-film" / ".story" / "story.db").exists()
        assert _q(tmp_path / "projects" / "new-film",
                  "SELECT name FROM entities WHERE type='project'")[0][0] == "New Film"

    def test_missing_required_field_raises(self, tmp_path):
        with pytest.raises(ValueError, match="Missing required fields"):
            writes.create_project("thin", {}, tmp_path)

    def test_a_number_field_is_stored_as_a_number(self, tmp_path):
        """create_project coerces `number` fields, as every other write path does.

        `extra` is a JSON blob and enforces nothing, so a `number` arriving as
        a string is stored as a string — and the dashboard's `max()` on
        act_count then raises and takes the whole view down. This path had no
        coercion at all while edit_entity did, which is the same value being a
        string, an int and an int in three readers.
        """
        import json
        writes.create_project("coerced", {"name": "C", "act_count": "4"}, tmp_path)
        proj = tmp_path / "projects" / "coerced"
        extra = json.loads(_q(proj, "SELECT extra FROM entities WHERE type='project'")[0][0])
        assert extra["act_count"] == 4
        assert isinstance(extra["act_count"], int)

    def test_a_non_numeric_value_is_left_alone_for_validation(self, tmp_path):
        """A value that is not a number is stored as sent, not silently replaced.

        A wrong value the reader can see beats a plausible one it cannot — and
        `validate_shape` reports it.
        """
        import json
        writes.create_project("bad", {"name": "B", "act_count": "four"}, tmp_path)
        proj = tmp_path / "projects" / "bad"
        extra = json.loads(_q(proj, "SELECT extra FROM entities WHERE type='project'")[0][0])
        assert extra["act_count"] == "four"

    def test_traversal_slug_rejected_before_touching_disk(self, tmp_path):
        """A project slug IS a directory name, so this is a traversal, not hygiene."""
        with pytest.raises(ValueError, match="Slug must be alphanumeric"):
            writes.create_project("../escape", {"name": "X"}, tmp_path)
        assert not (tmp_path.parent / "escape").exists()
