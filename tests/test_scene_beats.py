"""Phase 0 T0.3 — pin the read contract for a beat reference.

A ref target that does not exist must be:
  - an error on write (Phase 1, T1.5)
  - a soft finding on read (Phase 3, prose in Findings section)

This test asserts that `check_references` uses id+type lookup, so the fix
in Phase 1 (adding `scene_beats` refs to the write path) is not regressed
by a later refactor. Uses `plot.characters` (ref: character) as the
concrete case since `scene_beats` schema does not exist yet.
"""
import json

import pytest

from tools.story_retrieve import handler as retrieve_handler
from tools.story_search import handler as search_handler
from core import writes
from core.db import get_db, get_unfilled_map
from core.entity import check_references
from core.drafts import stage as draft_stage


def test_check_references_id_only_lookup(fixture_path):
    """A ref resolves by id+type. Phase 1 adds scene_beats refs to this path."""
    # Create a character
    writes.create_entity(fixture_path, "character", "alice", {"name": "Alice"})

    # A plot referencing that character passes
    check_references(fixture_path, "plot", {"characters": ["alice"]})

    # A plot referencing a non-existent character raises
    with pytest.raises(ValueError, match="Character not found"):
        check_references(fixture_path, "plot", {"characters": ["ghost"]})


# ── T2.1: unfilled reporting for the scene's computed scene_beats field ──

def _make_project(tmp_path):
    """Create a minimal project with acts/sequences/scenes folders."""
    from pathlib import Path
    project_path = Path(tmp_path) / "test-project"
    project_path.mkdir()
    (project_path / "characters").mkdir(parents=True)
    (project_path / "locations").mkdir(parents=True)
    (project_path / "worlds").mkdir(parents=True)
    (project_path / "plots").mkdir(parents=True)
    (project_path / "scenes").mkdir(parents=True)
    (project_path / "sequences").mkdir(parents=True)
    (project_path / "acts").mkdir(parents=True)
    (project_path / ".story").mkdir(parents=True)
    (project_path / "project.md").write_text("---\nname: Test\n---\n")
    return project_path


def _make_scene(project_path, scene_id, status, dramatic_role):
    """Create a scene with the given status and dramatic_role."""
    writes.create_entity(project_path, "act", f"act-{scene_id}", {"title": f"Act {scene_id}"})
    writes.create_entity(project_path, "sequence", f"seq-{scene_id}",
                        {"title": f"Seq {scene_id}", "act_id": f"act-{scene_id}"})
    writes.create_entity(project_path, "scene", scene_id, {
        "title": f"Scene {scene_id}",
        "status": status,
        "dramatic_role": dramatic_role,
        "sequence_id": f"seq-{scene_id}",
        "act_id": f"act-{scene_id}",
    })


def test_unfilled_reports_scene_beats_for_drafted_plot_role_scene(tmp_path):
    """A drafted plot-role scene with no scene_beats is reported unfilled."""
    p = _make_project(tmp_path)
    _make_scene(p, "drafted-plot", "drafted", "plot_role")
    unfilled = get_unfilled_map(p)
    assert "drafted-plot" in unfilled.get("scene_beats", [])


def test_unfilled_reports_scene_beats_for_drafted_empty_role_scene(tmp_path):
    """A drafted scene with empty dramatic_role is reported unfilled."""
    p = _make_project(tmp_path)
    _make_scene(p, "drafted-empty", "drafted", "")
    unfilled = get_unfilled_map(p)
    assert "drafted-empty" in unfilled.get("scene_beats", [])


def test_unfilled_skips_planned_scene(tmp_path):
    """A planned scene is a stub and is skipped."""
    p = _make_project(tmp_path)
    _make_scene(p, "planned-scene", "planned", "plot_role")
    unfilled = get_unfilled_map(p)
    assert "planned-scene" not in unfilled.get("scene_beats", [])


def test_unfilled_skips_transition_scene(tmp_path):
    """A transition scene is never reported."""
    p = _make_project(tmp_path)
    _make_scene(p, "transition-scene", "drafted", "transition")
    unfilled = get_unfilled_map(p)
    assert "transition-scene" not in unfilled.get("scene_beats", [])


def test_unfilled_skips_non_event_scene(tmp_path):
    """A non-event scene is never reported."""
    p = _make_project(tmp_path)
    _make_scene(p, "non-event-scene", "drafted", "non-event")
    unfilled = get_unfilled_map(p)
    assert "non-event-scene" not in unfilled.get("scene_beats", [])


def test_unfilled_not_reported_when_scene_beats_exists(tmp_path):
    """A scene with a scene_beats record is not reported."""
    p = _make_project(tmp_path)
    _make_scene(p, "has-beats", "drafted", "plot_role")
    writes.create_entity(p, "scene_beats", "has-beats-beats", {
        "scene": "has-beats",
        "beats": [{"action": {"surface": "test"}, "reaction": {"surface": "test"}}],
    })
    unfilled = get_unfilled_map(p)
    assert "has-beats" not in unfilled.get("scene_beats", [])


# ── T3.1: story_retrieve returns scene_beats fields and sections ─────────────


class TestRetrieveSceneBeats:
    """T3.1 — story_retrieve returns a scene_beats entity's fields and sections."""

    def _make_scene_beats(self, p):
        """Create a scene + scene_beats with nested beats and true_character."""
        writes.create_entity(p, "character", "t3-alice", {"name": "Alice"})
        writes.create_entity(p, "act", "t3-act", {"title": "Act I"})
        writes.create_entity(p, "sequence", "t3-seq",
                            {"title": "Seq 1", "act_id": "t3-act"})
        writes.create_entity(p, "scene", "t3-scene", {
            "title": "Scene 1", "sequence_id": "t3-seq", "act_id": "t3-act",
        })
        writes.create_entity(p, "scene_beats", "t3-scene-beats", {
            "scene": "t3-scene",
            "driver": "t3-alice",
            "scene_objective": "Alice wants the truth",
            "turning_point": "Alice learns the secret",
            "true_character": [
                {"character": "t3-alice", "dilemma": "Trust vs. safety",
                 "choice_reveals": "She chooses trust"}
            ],
            "beats": [
                {
                    "action": {"by": "t3-alice", "surface": "Asks about the door",
                               "subtext": "She already knows"},
                    "reaction": {"by": "t3-alice", "surface": "Silence",
                                 "subtext": "He is hiding something"},
                    "gap": "She knows he is lying",
                }
            ],
            "changes": [{"entity": "t3-alice", "change": "Now suspicious"}],
        }, sections={
            "Notes": "The scene needs more subtext in the middle.",
        })

    def test_retrieve_returns_nested_beats_and_true_character(self, fixture_path):
        """The nested shape survives a round trip through story_retrieve."""
        p = fixture_path
        self._make_scene_beats(p)

        result = json.loads(retrieve_handler({
            "project": str(p),
            "entity_type": "scene_beats",
            "id": ["t3-scene-beats"],
            "fields": ["all"],
            "sections": ["all"],
        }))

        assert result["entities"], f"Entity not found: {result}"
        entity = result["entities"][0]
        assert entity["id"] == "t3-scene-beats"

        fields = entity["fields"]
        assert fields["scene"] == "t3-scene"
        assert fields["driver"] == "t3-alice"
        assert fields["scene_objective"] == "Alice wants the truth"
        assert fields["turning_point"] == "Alice learns the secret"

        tc = fields["true_character"]
        assert isinstance(tc, list) and len(tc) == 1
        assert tc[0]["character"] == "t3-alice"
        assert tc[0]["dilemma"] == "Trust vs. safety"
        assert tc[0]["choice_reveals"] == "She chooses trust"

        beats = fields["beats"]
        assert isinstance(beats, list) and len(beats) == 1
        beat = beats[0]
        assert beat["action"]["by"] == "t3-alice"
        assert beat["action"]["surface"] == "Asks about the door"
        assert beat["action"]["subtext"] == "She already knows"
        assert beat["reaction"]["by"] == "t3-alice"
        assert beat["reaction"]["surface"] == "Silence"
        assert beat["reaction"]["subtext"] == "He is hiding something"
        assert beat["gap"] == "She knows he is lying"
        # The beat is action, reaction, gap — nothing else.
        assert set(beat) == {"action", "reaction", "gap"}

        # `changes` moved up: the scene's closing state, not one exchange's.
        changes = fields["changes"]
        assert changes[0]["entity"] == "t3-alice"
        assert changes[0]["change"] == "Now suspicious"

        sections = entity["sections"]
        assert set(sections) == {"Notes"}


# ── T3.2: scene computed fields are in the load payload and read-only ─────────


class TestSceneComputedFields:
    """T3.2 — turning_point and scene_beats are in the payload and read-only."""

    def _make_scene_with_beats(self, p):
        writes.create_entity(p, "character", "t3-alice", {"name": "Alice"})
        writes.create_entity(p, "act", "t3-act", {"title": "Act I"})
        writes.create_entity(p, "sequence", "t3-seq",
                            {"title": "Seq 1", "act_id": "t3-act"})
        writes.create_entity(p, "scene", "t3-scene", {
            "title": "Scene 1", "sequence_id": "t3-seq", "act_id": "t3-act",
        })
        writes.create_entity(p, "scene_beats", "t3-scene-beats", {
            "scene": "t3-scene",
            "turning_point": "The moment of change",
            "beats": [{"action": {"surface": "test"}, "reaction": {"surface": "test"}}],
        })

    def test_retrieve_scene_returns_computed_fields(self, fixture_path):
        """story_retrieve on a scene returns turning_point and the scene_beats POINTER."""
        p = fixture_path
        self._make_scene_with_beats(p)

        result = json.loads(retrieve_handler({
            "project": str(p),
            "entity_type": "scene",
            "id": ["t3-scene"],
            "fields": ["turning_point", "scene_beats"],
        }))

        entity = result["entities"][0]
        assert entity["fields"]["turning_point"] == "The moment of change"
        # A slug, not the record: the id cannot be derived from the scene id, so
        # the pointer is what tells the reader where to look. The record itself
        # is a second call on `scene_beats` with this id.
        assert entity["fields"]["scene_beats"] == "t3-scene-beats"

    def test_the_pointer_is_empty_without_a_record(self, fixture_path):
        """A scene with no record returns an empty pointer, not a record."""
        p = fixture_path
        writes.create_entity(p, "act", "t3-act", {"title": "Act I"})
        writes.create_entity(p, "sequence", "t3-seq",
                            {"title": "Seq 1", "act_id": "t3-act"})
        writes.create_entity(p, "scene", "t3-scene", {
            "title": "Scene 1", "sequence_id": "t3-seq", "act_id": "t3-act",
        })

        result = json.loads(retrieve_handler({
            "project": str(p),
            "entity_type": "scene",
            "id": ["t3-scene"],
            "fields": ["scene_beats"],
        }))

        assert result["entities"][0]["fields"]["scene_beats"] == ""

    def test_the_record_is_read_with_the_pointer(self, fixture_path):
        """The pointer and the record are two calls, and they agree."""
        p = fixture_path
        self._make_scene_with_beats(p)

        scene = json.loads(retrieve_handler({
            "project": str(p), "entity_type": "scene",
            "id": ["t3-scene"], "fields": ["scene_beats"],
        }))["entities"][0]["fields"]["scene_beats"]

        record = json.loads(retrieve_handler({
            "project": str(p), "entity_type": "scene_beats",
            "id": [scene], "fields": ["all"],
        }))["entities"][0]
        assert record["id"] == scene
        assert record["fields"]["turning_point"] == "The moment of change"

    def test_draft_refuses_computed_fields_on_edit(self, fixture_path):
        """story_draft with turning_point or scene_beats in data refuses."""
        p = fixture_path
        self._make_scene_with_beats(p)

        result = draft_stage(p, [
            {"op": "edit", "entity_type": "scene", "entity_id": "t3-scene",
             "data": {"turning_point": "Fake turning point"},
             "summary": "Try to set turning_point"},
        ], summary="test")

        assert result["success"] is True
        assert result["validation"]
        assert any("turning_point" in v and "read-only" in v
                    for v in result["validation"])

    def test_draft_refuses_scene_beats_computed_field(self, fixture_path):
        """story_draft with scene_beats in data refuses."""
        p = fixture_path
        self._make_scene_with_beats(p)

        result = draft_stage(p, [
            {"op": "edit", "entity_type": "scene", "entity_id": "t3-scene",
             "data": {"scene_beats": {"id": "fake"}},
             "summary": "Try to set scene_beats"},
        ], summary="test")

        assert result["success"] is True
        assert result["validation"]
        assert any("scene_beats" in v and "read-only" in v
                    for v in result["validation"])


# ── T3.3: story_search reaches scene_beats prose ─────────────────────────────

class TestBeatShape:
    """Issue 3 + 5 — the beat is action, reaction, gap; `risk` is gone and
    `changes` moved up to the record."""

    def _parents(self, p, slug="shape"):
        writes.create_entity(p, "character", "shape-alice", {"name": "Alice"})
        writes.create_entity(p, "act", "shape-act", {"title": "Act I"})
        writes.create_entity(p, "sequence", "shape-seq",
                             {"title": "Seq", "act_id": "shape-act"})
        writes.create_entity(p, "scene", slug, {
            "title": "Scene", "sequence_id": "shape-seq", "act_id": "shape-act"})
        return slug

    def test_the_beat_has_exactly_action_reaction_and_gap(self, fixture_path):
        p = fixture_path
        slug = self._parents(p)
        writes.create_entity(p, "scene_beats", f"{slug}-beats", {
            "scene": slug,
            "beats": [{"action": {"surface": "Asks"},
                       "reaction": {"surface": "Silence"},
                       "gap": "She knows he is lying"}],
        })
        fields = json.loads(retrieve_handler({
            "project": str(p), "entity_type": "scene_beats",
            "id": [f"{slug}-beats"], "fields": ["all"],
        }))["entities"][0]["fields"]
        assert set(fields["beats"][0]) == {"action", "reaction", "gap"}

    def test_risk_is_not_a_field_any_more(self, fixture_path):
        """The retired field must not be described, and must not be writable."""
        from tools.story_describe import handler as describe_handler
        schema = json.loads(describe_handler({"entity_type": "scene_beats"}))
        beat = schema["entity_schemas"]["scene_beats"]["beats"]["sub_fields"]
        assert "risk" not in beat
        assert set(beat) == {"action", "reaction", "gap"}

    def test_changes_lives_at_the_top_level(self, fixture_path):
        p = fixture_path
        slug = self._parents(p)
        writes.create_entity(p, "scene_beats", f"{slug}-beats", {
            "scene": slug,
            "beats": [{"action": {"surface": "Asks"},
                       "reaction": {"surface": "Silence"},
                       "gap": "x"}],
            "changes": [{"entity": "shape-alice", "change": "Now suspicious"}],
        })
        fields = json.loads(retrieve_handler({
            "project": str(p), "entity_type": "scene_beats",
            "id": [f"{slug}-beats"], "fields": ["all"],
        }))["entities"][0]["fields"]
        assert fields["changes"] == [
            {"entity": "shape-alice", "change": "Now suspicious"}]

    def test_a_changes_entity_must_resolve(self, fixture_path):
        """`changes[].entity` is checked where the field now lives."""
        p = fixture_path
        slug = self._parents(p)
        with pytest.raises(ValueError, match="changes\\[0\\].entity"):
            writes.create_entity(p, "scene_beats", f"{slug}-beats", {
                "scene": slug,
                "beats": [{"action": {"surface": "Asks"},
                           "reaction": {"surface": "Silence"},
                           "gap": "x"}],
                "changes": [{"entity": "ghost-entity", "change": "x"}],
            })

    def test_effects_stay_on_the_scene(self, fixture_path):
        """`changes` is the state of any entity; `effects` still ties a value
        shift to a plot protagonist. Neither replaces the other."""
        from tools.story_describe import handler as describe_handler
        scene = json.loads(describe_handler({"entity_type": "scene"}))
        effects = scene["entity_schemas"]["scene"]["value_turns"]["sub_fields"]["effects"]
        assert "conflict_level" in effects["sub_fields"]["levels"]["sub_fields"]


class TestSearchSceneBeats:
    """T3.3 — story_search reaches a scene_beats note's prose."""

    def test_search_finds_scene_beats_notes(self, fixture_path):
        """A search for a term in a scene_beats note's prose finds it."""
        p = fixture_path
        writes.create_entity(p, "character", "t3-alice", {"name": "Alice"})
        writes.create_entity(p, "act", "t3-act", {"title": "Act I"})
        writes.create_entity(p, "sequence", "t3-seq",
                            {"title": "Seq 1", "act_id": "t3-act"})
        writes.create_entity(p, "scene", "t3-scene", {
            "title": "Scene 1", "sequence_id": "t3-seq", "act_id": "t3-act",
        })
        writes.create_entity(p, "scene_beats", "t3-scene-beats", {
            "scene": "t3-scene",
            "beats": [{"action": {"surface": "test"}, "reaction": {"surface": "test"}}],
        }, sections={
            "Notes": "The zorblatt dialogue needs tightening.",
        })

        result = json.loads(search_handler({
            "project": str(p),
            "query": "zorblatt",
        }))

        assert result["total"] > 0
        entity_ids = [r["entity_id"] for r in result["results"]]
        assert "t3-scene-beats" in entity_ids


class TestBeatObjectShape:
    """A beat's `action`/`reaction` are FIXED-KEY objects, not maps.

    `_validate_field` read every `object` as a map keyed by entity (the
    `relationship.perspectives` shape), so it validated a beat side's *values*
    and reported `by`, `surface` and `subtext` each as "holds a str". Every
    well-formed beat was therefore refused at staging — while `create_entity`
    accepted the same record, so the two write paths disagreed about the shape
    the schema declares. `perspectives` is the only declared map and carries
    `keyed: True`; these are the only fixed-key objects.
    """

    def _parents(self, p, slug="objshape"):
        writes.create_entity(p, "character", "obj-alice", {"name": "Alice"})
        writes.create_entity(p, "act", "obj-act", {"title": "Act I"})
        writes.create_entity(p, "sequence", "obj-seq",
                             {"title": "Seq", "act_id": "obj-act"})
        writes.create_entity(p, "scene", slug, {
            "title": "Scene", "sequence_id": "obj-seq", "act_id": "obj-act"})
        return slug

    def _op(self, slug):
        return [{"op": "create", "type": "scene_beats", "id": f"{slug}-beats",
                 "summary": "beats",
                 "frontmatter": {
                     "scene": slug,
                     "beats": [{
                         "action": {"by": "obj-alice", "surface": "Asks",
                                    "subtext": "pressing for the answer"},
                         "reaction": {"by": "obj-alice", "surface": "Silence",
                                      "subtext": "withholding it"},
                         "gap": "Expects the answer; gets none."}]}}]

    def test_a_well_formed_beat_stages_clean(self, fixture_path):
        """The shape the schema declares must produce no findings."""
        slug = self._parents(fixture_path)
        result = draft_stage(fixture_path, self._op(slug))
        assert result["validation"] == []

    def test_the_write_path_accepts_the_same_record(self, fixture_path):
        """The two write paths must agree about the shape the schema declares."""
        slug = self._parents(fixture_path)
        writes.create_entity(fixture_path, "scene_beats", f"{slug}-beats",
                             self._op(slug)[0]["frontmatter"])

    def test_a_wrong_type_inside_a_fixed_key_object_is_still_reported(self, fixture_path):
        """The fix narrows the reading; it must not stop validating the values."""
        slug = self._parents(fixture_path)
        op = self._op(slug)
        op[0]["frontmatter"]["beats"][0]["action"]["surface"] = 7
        result = draft_stage(fixture_path, op)
        assert any("action.surface" in v and "int" in v
                   for v in result["validation"])

    def test_a_declared_map_is_still_validated_per_value(self, fixture_path):
        """`keyed: True` keeps its own reading: the keys are entities."""
        from core.entity import validate_entity
        warnings = validate_entity("relationship", {
            "characters": ["obj-alice", "obj-alice"],
            "perspectives": {"obj-alice": {"strength": "high"}},
        })
        assert any("perspectives.obj-alice.strength must be a number" in w
                   for w in warnings)
