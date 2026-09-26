"""Value lives in view='story_value', not in the base structural map.

Regression: acts and sequences both emitted value/value_open/value_close in
the base view, duplicating each other in the view whose stated job is to stay
small — and the value view only covered acts, so stripping the base first would
have lost sequences entirely.
"""
import json
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

FIXTURE = Path(__file__).parent / "fixtures" / "save-the-children"


@pytest.fixture
def project(tmp_path, monkeypatch):
    root = tmp_path / "root"
    shutil.copytree(FIXTURE, root / "projects" / "save-the-children")
    import core.config
    monkeypatch.setattr(core.config, "load_plugin_config", lambda: {"root_path": str(root)})
    from tools.story_import import handler as import_handler
    import_handler({"project": "save-the-children", "confirm": True}, root_path=str(root))
    return root / "projects" / "save-the-children"


def load(project, **args):
    from tools.story_load import handler
    return json.loads(
        handler({"project": "save-the-children", **args}, root_path=str(project.parent.parent))
    )


def test_base_map_carries_no_container_values(project):
    data = load(project)
    assert data["acts"], "fixture should have acts"
    for act in data["acts"]:
        assert not {"value", "value_at_open", "value_at_close"} & act.keys()
        for seq in act["sequences"]:
            assert not {"value", "value_at_open", "value_at_close"} & seq.keys()


def test_base_view_top_level_keys_are_pinned(project):
    """The base view's shape, asserted rather than measured and forgotten.

    Every phase of this task moved keys between the base map and the value
    view, and each move was invisible to the suite — the payload stayed
    well-shaped, just carrying the wrong thing. A key set is the cheapest
    assertion that catches a container field creeping back in, or a view
    key disappearing in a rename.
    """
    assert sorted(load(project)) == [
        "acts", "characters", "confirmation", "loaded",
        "memory", "plots", "project", "worlds",
    ]


def test_base_map_still_carries_the_project_value(project):
    """Stripping the containers must not strip the project's own value."""
    p = load(project)["project"]
    for k in ("story_value", "story_value_at_open", "story_value_at_close"):
        assert k in p


def test_base_map_character_carries_the_character_value(project):
    """The character value is the character's, named as such in the base map.

    Regression: the base map read `arc_value` from a DB that no longer stores
    it, fell through to the schema default, and `_omit` dropped the key — the
    only character with a designed arc had no value in the base map at all.
    """
    chars = {c["id"]: c for c in load(project)["characters"]}
    voss = chars["dr-elena-voss"]
    assert voss["character_value"] == "Redemption"
    assert voss["character_value_at_open"] == "positive"
    assert voss["character_value_at_close"] == "negative"
    # A character with nothing recorded must not grow the keys at defaults.
    assert "character_value" not in chars["kael"]


def test_story_value_view_carries_act_and_sequence_values(project):
    data = load(project, view="story_value")
    assert data["acts"], "expected at least one act"
    with_seq = 0
    for act in data["acts"]:
        assert "value_at_open" in act and "value_at_close" in act
        for seq in act["sequences"]:
            assert "value_at_open" in seq and "value_at_close" in seq
            with_seq += 1
    assert with_seq, "fixture should have sequences to prove they survive"


def test_no_container_payload_carries_a_value_key(project):
    """The value word is stated once, on the project, and inherited downward.

    A `value` key on a container means the story track and a character track
    have been merged back together in the payload — the exact conflation this
    schema exists to separate.
    """
    def containers(data):
        for act in data["acts"]:
            yield act
            for seq in act["sequences"]:
                yield seq
                for sc in seq.get("scenes", []):
                    yield sc

    for c in containers(load(project, view="story_value")):
        assert "value" not in c, f"{c['id']} carries a value word: {c}"


def test_view_story_value_key_is_the_schema_field(project):
    """The key the view returns is the key the schema writes.

    These disagreed until the rename: the view returned `story_value` while the
    field was called `value`. Asserted because the agreement is the point — a
    well-shaped payload naming a field nothing writes is a silent lie.
    """
    from core.constants import ENTITY_SCHEMAS
    data = load(project, view="story_value")
    for key in ("story_value", "story_value_at_open", "story_value_at_close"):
        assert key in ENTITY_SCHEMAS["project"], f"{key} is not a project field"
        assert key in data, f"{key} missing from the story_value view"
    # The containers inherit the word, so they must not claim one.
    for field in ("value_at_open", "value_at_close", "shift", "y"):
        assert field in ENTITY_SCHEMAS["scene"]


def test_story_value_view_carries_a_real_shift_and_curve(project):
    """Scenes must carry a real `shift` and a real `y` — and nothing else may.

    The bug this guards: keys present but always empty reads as "no value data",
    which is a different lie. A well-shaped all-empty payload must not pass —
    `value_open` vs `value_at_open` recurred exactly that way.

    Scenes are the assertion, and the only place it can live: a turn is only
    observable once the scene exists. Act and sequence state an expectation, so
    `shift`/`y` there could only be the model predicting unwritten scenes — the
    old container-level half of this test passed only because phase 4
    hand-filled the fixture, and failed against the live project.
    """
    from core.constants import ENTITY_SCHEMAS
    data = load(project, view="story_value")
    scenes = [sc for act in data["acts"] for seq in act["sequences"]
              for sc in seq.get("scenes", [])]
    assert any(sc.get("shift") for sc in scenes), "scenes carry no shift — they are where it turns"
    assert any(sc.get("y") for sc in scenes), "every scene y is 0.0 — the curve is not plottable"

    # The fields exist on scenes and beats only. A container carrying them again
    # means the shape has crept back to a guess with no observation behind it.
    for entity_type in ("scene", "arc_beat"):
        for field in ("shift", "y"):
            assert field in ENTITY_SCHEMAS[entity_type], f"{entity_type} lost {field}"
    for entity_type in ("project", "act", "sequence"):
        for field in ("shift", "y"):
            assert field not in ENTITY_SCHEMAS[entity_type], f"{entity_type} re-gained {field}"
    for c in [d for act in data["acts"] for d in [act] + act["sequences"]]:
        assert "shift" not in c, f"{c['id']} carries a shift: {c}"
        assert "y" not in c, f"{c['id']} carries a y: {c}"


def test_an_unrecorded_y_is_not_reported_as_zero(project):
    """An unrecorded curve point must read as absent, not as `y: 0.0`.

    0.0 is a charge a writer can legitimately choose; "not observed" is a
    different statement, and the graph already treats it as one —
    `get_dashboard_data` omits the key so `storySeries` skips the point. The
    view used to disagree with the plot it feeds, reporting the schema default
    as a real measurement.

    The fixture has all three scenes filled, so the unfilled case is built here:
    a test that only ever sees a full project would pass against the bug.
    """
    from core.db import get_db
    conn = get_db(project)
    try:
        row = conn.execute(
            "SELECT id, extra FROM entities WHERE type='scene' AND is_deleted=0"
        ).fetchone()
        scene_id, extra_json = row
        extra = json.loads(extra_json or "{}")
        extra.pop("y", None)
        extra.pop("shift", None)
        conn.execute("UPDATE entities SET extra=? WHERE id=?", (json.dumps(extra), scene_id))
        conn.commit()
    finally:
        conn.close()

    scenes = [sc for act in load(project, view="story_value")["acts"]
              for seq in act["sequences"] for sc in seq.get("scenes", [])]
    blanked = next(sc for sc in scenes if sc["id"] == scene_id)
    assert blanked["y"] == "", f"an unrecorded y reads as {blanked['y']!r}, not as absent"
    assert blanked["shift"] == "", "an unrecorded shift must not read as recorded"

    # The filled scenes are untouched — the rule is about defaults, not zeroes.
    filled = [sc for sc in scenes if sc["id"] != scene_id]
    assert any(isinstance(sc["y"], float) for sc in filled), "no scene kept a real y"


def test_sequences_are_titled(project):
    """A sequence id alone cannot be told from another without a lookup."""
    for act in load(project, view="story_value")["acts"]:
        for seq in act["sequences"]:
            assert seq.get("title"), f"sequence {seq['id']} has no title"


def test_scenes_are_included_with_their_values(project):
    """Scenes are where the value turns; without them the progression is a lie."""
    scenes = [
        (seq["id"], sc)
        for act in load(project, view="story_value")["acts"]
        for seq in act["sequences"]
        for sc in seq.get("scenes", [])
    ]
    assert scenes, "no scenes in the value view — the progression cannot be read"
    for seq_id, sc in scenes:
        assert sc.get("id")
        assert "value_at_open" in sc and "value_at_close" in sc


def test_every_scene_in_the_db_appears_in_the_value_view(project):
    """A scene dropped from the view is a value turn the reader cannot see."""
    from core.db import get_db
    conn = get_db(project)
    try:
        in_db = {r[0] for r in conn.execute(
            "SELECT id FROM entities WHERE type='scene' AND is_deleted=0")}
    finally:
        conn.close()
    in_view = {
        sc["id"]
        for act in load(project, view="story_value")["acts"]
        for seq in act["sequences"] for sc in seq.get("scenes", [])
    }
    assert in_db == in_view, f"missing from view: {in_db - in_view}"


def test_scene_titles_present(project):
    for act in load(project, view="story_value")["acts"]:
        for seq in act["sequences"]:
            for sc in seq.get("scenes", []):
                assert "title" in sc, f"scene {sc['id']} has no title"


def test_value_view_is_not_silently_empty(project):
    """The bug: acts stored value_open, the view read value_at_open, all blank.

    Keys present but always "" reads as "no value data", which is a different
    lie. At least one container must carry a real charge.
    """
    data = load(project, view="story_value")
    charges = [
        d[side]
        for act in data["acts"] for d in [act] + act["sequences"]
        for side in ("value_at_open", "value_at_close")
    ]
    assert any(charges), f"every value field empty — key mismatch again: {data}"


def test_story_value_view_growth_is_measured_not_assumed(project):
    """Re-measured after shift/y were added, per the plan's phase-4 note.

    The view's cost per scene is the number that decides whether it can stay a
    view at all. Two fields per container is a real cost, so it is pinned here
    rather than left to be discovered as a slow context leak.
    """
    from tools.story_create import handler as create_handler

    vault = str(project.parent.parent)

    def size():
        return len(json.dumps(load(project, view="story_value")))

    small = size()
    for i in range(40):
        create_handler({"entity_type": "scene", "slug": f"drift-{i:02d}",
                        "project": "save-the-children",
                        "frontmatter": {"title": f"Drift {i}",
                                        "sequence_id": "seq-discovery",
                                        "value_at_open": "positive",
                                        "value_at_close": "negative",
                                        "shift": "blind trust → first doubt",
                                        "y": -0.3}},
                       root_path=vault)
    per_scene = (size() - small) / 40
    # MEASURED at 153.75, not guessed: a fully recorded scene costs that much
    # because the view's whole job is to carry four value fields per scene
    # ({"id", "title", "value_at_open", "value_at_close", "shift", "y"} is 151
    # chars, plus the list separator).
    # The ceiling is deliberately loose — this is a leak alarm, not a budget.
    # What it catches is a field added twice, or a placeholder string
    # reintroduced into the payload (that one cost 125 → 107 when fixed).
    assert per_scene < 200, f"{per_scene:.1f} chars per scene in the value view"


def test_act_filter_still_works_in_the_value_view(project):
    """seq_by_act is built before the filter, so a filtered act keeps its sequences."""
    all_acts = load(project, view="story_value")["acts"]
    target = next(a for a in all_acts if a["sequences"])
    one = load(project, view="story_value", act=target["id"])["acts"]
    assert [a["id"] for a in one] == [target["id"]]
    assert [s["id"] for s in one[0]["sequences"]] == [s["id"] for s in target["sequences"]]
