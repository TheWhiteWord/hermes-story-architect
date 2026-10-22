"""The linter must be reachable from story_draft, for every op kind.

A check nothing calls is a comment. These go through the real tool, so the
finding has to survive the whole path an agent actually takes.
"""
import json


from tools.story_draft import handler

GOOD = "INT. THE CENTRAL ROOM - DAY\n\nHe waits at the door."
BAD = "KAEL stands before the door, hand on the handle."


def _stage(project, ops):
    return json.loads(handler({"project": str(project), "action": "stage",
                               "ops": ops, "summary": "probe"}))


def test_creating_a_scene_without_a_heading_is_reported(fixture_path):
    r = _stage(fixture_path, [{
        "op": "create", "type": "scene", "id": "mira-tells-kael",
        "frontmatter": {"title": "The Telling", "sequence_id": "seq-discovery",
                        "heading": "INT. THE INSTITUTE - NIGHT"},
        "sections": {"Content": BAD},
        "summary": "New scene",
    }])
    assert any("scene heading" in f for f in r["validation"]), r["validation"]


def test_creating_a_scene_with_a_heading_is_not_reported(fixture_path):
    r = _stage(fixture_path, [{
        "op": "create", "type": "scene", "id": "mira-tells-kael",
        "frontmatter": {"title": "The Telling", "sequence_id": "seq-discovery",
                        "heading": "INT. THE INSTITUTE - NIGHT"},
        "sections": {"Content": GOOD},
        "summary": "New scene",
    }])
    assert not any("scene heading" in f for f in r["validation"]), r["validation"]


def test_editing_a_scenes_content_is_checked(fixture_path):
    """The edit path is where a reformat usually happens, and it is the path
    that was skipping validation entirely before D1a."""
    r = _stage(fixture_path, [{
        "op": "edit", "entity_type": "scene", "entity_id": "central-room-day",
        "data": {"Content": BAD},
        "summary": "Rewrite the content",
    }])
    assert any("scene heading" in f for f in r["validation"]), r["validation"]


def test_a_forced_heading_is_accepted_on_create(fixture_path):
    """.SNIPER SCOPE POV is a heading, not an error — the whole point of
    reusing the renderer's own regex."""
    r = _stage(fixture_path, [{
        "op": "create", "type": "scene", "id": "scope-pov",
        "frontmatter": {"title": "Scope", "sequence_id": "seq-discovery"},
        "sections": {"Content": ".SNIPER SCOPE POV\n\nA face fills the frame."},
        "summary": "New scene",
    }])
    assert not any("scene heading" in f for f in r["validation"]), r["validation"]


def test_a_non_scene_with_a_content_section_is_not_checked(fixture_path):
    """`Content` on a character is prose, not Fountain. Only scenes are."""
    r = _stage(fixture_path, [{
        "op": "create", "type": "character", "id": "someone-new",
        "frontmatter": {"name": "Someone", "one_sentence": "A person.",
                        "story_role": "Minor"},
        "sections": {"Content": "Not a screenplay, just prose about a person."},
        "summary": "New character",
    }])
    assert not any("scene heading" in f for f in r["validation"]), r["validation"]


def test_a_scene_with_no_content_section_is_not_reported(fixture_path):
    """Planned scenes have no script yet. That is a normal state, not a fault."""
    r = _stage(fixture_path, [{
        "op": "create", "type": "scene", "id": "planned-scene",
        "frontmatter": {"title": "Planned", "sequence_id": "seq-discovery",
                        "status": "planned"},
        "sections": {"Objective": "Something happens."},
        "summary": "New scene",
    }])
    assert not any("scene heading" in f for f in r["validation"]), r["validation"]


def test_deleting_a_scene_is_not_checked(fixture_path):
    r = _stage(fixture_path, [{
        "op": "delete", "entity_type": "scene", "entity_id": "garden-dream",
        "summary": "Remove it",
    }])
    assert not any("scene heading" in f for f in r["validation"]), r["validation"]
