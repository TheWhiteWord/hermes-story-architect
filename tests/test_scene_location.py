"""A scene's location must resolve to a location record.

Mirrors the arc_beat parent check in test_arcs.py, and the convention it
follows: the write refuses, the error names the thing that is missing, and an
empty value is a deliberate absence rather than a gap.

The ordering note in validate_scene_location is load-bearing — the check reads
the DB, so a location created in the same draft is invisible to it. That is
why the "create it first" test is here as a positive case rather than assumed.
"""
import pytest

from core.writes import create_entity


def _act_and_sequence(project):
    create_entity(project, "act", "act-1", {"title": "Act I"})
    create_entity(project, "sequence", "seq-1", {"title": "One", "act_id": "act-1"})


def _scene(project, **overrides):
    return create_entity(project, "scene", "s1", {
        "title": "The room", "sequence_id": "seq-1", "act_id": "act-1",
        **overrides})


class TestSceneLocation:
    def test_unknown_location_is_refused(self, tmp_path):
        _act_and_sequence(tmp_path)
        with pytest.raises(ValueError, match="Location not found"):
            _scene(tmp_path, location="the-burnt-shed")

    def test_a_character_slug_is_not_a_location(self, tmp_path):
        """The check is on type, not on existence alone."""
        _act_and_sequence(tmp_path)
        create_entity(tmp_path, "character", "kael",
                      {"name": "Kael", "story_role": "Protagonist",
                       "one_sentence": "T"})
        with pytest.raises(ValueError, match="Location not found"):
            _scene(tmp_path, location="kael")

    def test_existing_location_commits(self, tmp_path):
        _act_and_sequence(tmp_path)
        create_entity(tmp_path, "location", "the-shed",
                      {"name": "The shed", "one_sentence": "T"})
        assert _scene(tmp_path, location="the-shed")["success"] is True

    def test_create_the_location_first_then_the_scene(self, tmp_path):
        """The order the error message tells the agent to use."""
        _act_and_sequence(tmp_path)
        create_entity(tmp_path, "location", "the-burnt-shed",
                      {"name": "The burnt shed", "one_sentence": "T"})
        assert _scene(tmp_path, location="the-burnt-shed")["success"] is True

    def test_empty_location_is_a_field_still_to_set(self, tmp_path):
        """Not a scene in the void — a scene whose location is not set yet.

        The field may be left empty while the story is still being shaped, and
        it is reported by unfilled_fields until it is set. What is refused is a
        value that names a location which does not exist.
        """
        _act_and_sequence(tmp_path)
        assert _scene(tmp_path)["success"] is True
        from core.entity import unfilled_fields
        assert "location" in unfilled_fields("scene", {})

    def test_free_text_that_happens_to_match_commits(self, tmp_path):
        """Free text stays legal — it is the resolution that is required."""
        _act_and_sequence(tmp_path)
        create_entity(tmp_path, "location", "the-shed",
                      {"name": "The shed", "one_sentence": "T"})
        assert _scene(tmp_path, location="the-shed")["success"] is True
