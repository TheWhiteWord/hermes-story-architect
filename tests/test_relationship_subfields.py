"""The declared sub_fields of a computed list must match what the payload emits.

`character.relationships` is computed, so its sub_fields exist for
*interpretation*, not for writing. That makes them easy to declare wrongly and
never notice: nothing crashes, the description is just quietly untrue. These
tests compare the declaration against the real payload and the real data.
"""
import json
import shutil
import tempfile


from core.constants import ENTITY_SCHEMAS


def _load(project_dir):
    from core.db import get_project_summary

    return get_project_summary(project_dir)


def test_declared_sub_fields_match_the_load_payload(fixture_path):
    declared = set(
        ENTITY_SCHEMAS["character"]["relationships"]["sub_fields"])
    emitted = set()
    for char in _load(fixture_path)["characters"]:
        for entry in char.get("relationships") or []:
            emitted |= set(entry)
    if not emitted:
        return  # fixture has no relationships; nothing to compare against
    # `strength` is dashboard-only, so it may be declared but never emitted here.
    assert emitted <= declared, f"undeclared: {sorted(emitted - declared)}"


def test_describe_surfaces_the_sub_fields():
    from tools.story_describe import handler

    out = json.loads(handler({"entity_type": "character"}))
    sub = out["entity_schemas"]["character"]["relationships"]["sub_fields"]
    assert set(sub) >= {"with", "label", "type"}


def test_with_is_documented_as_the_other_character(fixture_path):
    """The one genuinely confusing key: `with` names the OTHER character, so
    reading it as this character inverts the relationship."""
    sub = ENTITY_SCHEMAS["character"]["relationships"]["sub_fields"]
    assert "other" in sub["with"]["description"].lower()
    assert "never this one" in sub["with"]["description"].lower()


def test_strength_is_documented_as_signed():
    """It is a signed scale, not 0-5: real data runs -0.6 to 0.9, and an agent
    told 0-5 would clamp every antagonist relationship to zero."""
    sub = ENTITY_SCHEMAS["character"]["relationships"]["sub_fields"]
    assert "negative" in sub["strength"]["description"].lower()


def test_type_is_not_declared_as_a_closed_enum():
    """`romantic` exists in the data and no enum list would survive contact with
    the next project, so the description must not pretend to be one."""
    sub = ENTITY_SCHEMAS["character"]["relationships"]["sub_fields"]
    desc = sub["type"]["description"].lower()
    assert "not a closed set" in desc or "free text" in desc
    for known in ("ally", "rival", "enemy", "family", "romantic"):
        assert known in desc, f"{known} missing from the documented values"
