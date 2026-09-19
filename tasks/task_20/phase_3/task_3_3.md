# Task 3.3: Update `test_field_coverage.py` — Nested Dict Assertions

## Goal
Update load assertions in `tests/test_field_coverage.py` to find entities in the nested dict structure instead of `entities.rows`.

**Scope:** `tests/test_field_coverage.py` — 2 test functions updated.

---

## Current State (verified against code)

### Tests to update (2):

**1. `test_create_load_retrieve`** (lines 169-208):
```python
# Load → entity appears in rows
load_result = json.loads(load_handler({"project": str(project)}))
assert load_result.get("loaded"), f"Load failed: {load_result}"

rows = load_result["entities"]["rows"]
entity_ids = [r[0] for r in rows]
expected_id = slug
if entity_type == "arc":
    expected_id = f"parent-char-{slug}"
assert expected_id in entity_ids, f"Entity {expected_id} not in load: {entity_ids}"
```
Currently searches `load_result["entities"]["rows"]` for entity IDs. New structure has no `entities` key — entities are in nested `acts`/`characters`/`plots`/`locations`/`worlds` dicts.

**2. `test_edit_all_field_types`** (lines 215-330):
```python
# Verify edit persisted
load_after = json.loads(load_handler({"project": str(project)}))
rows_after = [r for r in load_after["entities"]["rows"] if r[0] == entity_id]
assert rows_after, f"Entity {entity_id} missing after edit"

row_after = rows_after[0]
cols = load_after["entities"]["cols"]
by_col = dict(zip(cols, row_after))

# Column checks
if "one_sentence" in edit_data and entity_type in ("character", "plot"):
    assert by_col["one_sentence"] == edit_data["one_sentence"]
if "status" in edit_data and entity_type == "plot":
    assert by_col["status"] == edit_data["status"]

# Extra checks
extra_after = row_after[8]
if isinstance(extra_after, str):
    extra_after = json.loads(extra_after)

if entity_type == "character":
    assert extra_after.get("arc_type") == "negative"
    assert extra_after.get("arc_complete") is True
if entity_type == "plot":
    assert extra_after.get("plot_type") == "Resonant"
if entity_type == "scene":
    assert extra_after.get("dramatic_role") == "crisis"
if entity_type == "arc":
    assert extra_after.get("action") == "Updated action"
    assert extra_after.get("y") == -0.7
    assert extra_after.get("is_crisis") is True

# Relation check (the critical bug area)
if entity_type == "plot":
    relations_after = load_after["relations"]["rows"]
    plot_rels = [r for r in relations_after if r[0] == entity_id]
    kinds = {r[2] for r in plot_rels}
    assert "plot_setup" in kinds, f"plot_setup missing: {kinds}"
    assert "plot_payoff" in kinds, f"plot_payoff missing: {kinds}"
    assert "plot_crisis" in kinds, f"plot_crisis missing after edit: {kinds}"
    assert "plot_climax" in kinds, f"plot_climax missing after edit: {kinds}"
```
Currently reads `entities.rows` and `relations.rows`. New structure: entities in nested dicts, relations embedded.

---

## Target State

### 1. `test_create_load_retrieve` — find entity in nested dict:
```python
# Load → entity appears in nested structure
load_result = json.loads(load_handler({"project": str(project)}))
assert load_result.get("loaded"), f"Load failed: {load_result}"

# Find entity in nested structure
found = False
if entity_type == "character":
    found = slug in load_result["characters"]
elif entity_type == "plot":
    found = slug in load_result["plots"]
elif entity_type == "location":
    found = slug in load_result["locations"]
elif entity_type == "world":
    found = slug in load_result["worlds"]
elif entity_type == "scene":
    # Search nested acts → sequences → scenes
    for act in load_result["acts"]:
        for seq in act.get("sequences", []):
            for scene in seq.get("scenes", []):
                if isinstance(scene, dict) and scene.get("id") == slug:
                    found = True
                    break
                elif isinstance(scene, str) and scene == slug:
                    found = True
                    break
elif entity_type == "sequence":
    for act in load_result["acts"]:
        for seq in act.get("sequences", []):
            if seq.get("id") == slug:
                found = True
                break
elif entity_type == "act":
    found = any(a.get("id") == slug for a in load_result["acts"])
elif entity_type == "arc":
    # Arc beats are nested in characters
    expected_id = f"parent-char-{slug}"
    for char in load_result["characters"].values():
        for beat in char.get("arc", []):
            if isinstance(beat, dict) and beat.get("id") == expected_id:
                found = True
                break
            elif isinstance(beat, str) and beat == expected_id:
                found = True
                break

assert found, f"Entity {slug} not in load result"
```

### 2. `test_edit_all_field_types` — verify via nested dict:
```python
# Verify edit persisted
load_after = json.loads(load_handler({"project": str(project)}))

# Find entity in nested structure
entity_data = None
if entity_type == "character":
    entity_data = load_after["characters"].get(entity_id)
elif entity_type == "plot":
    entity_data = load_after["plots"].get(entity_id)
elif entity_type == "scene":
    for act in load_after["acts"]:
        for seq in act.get("sequences", []):
            for scene in seq.get("scenes", []):
                if isinstance(scene, dict) and scene.get("id") == entity_id:
                    entity_data = scene
                    break
elif entity_type == "arc":
    for char in load_after["characters"].values():
        for beat in char.get("arc", []):
            if isinstance(beat, dict) and beat.get("id") == entity_id:
                entity_data = beat
                break

assert entity_data is not None, f"Entity {entity_id} missing after edit"

# Field checks (adapt per entity type)
if entity_type == "character":
    if "one_sentence" in edit_data:
        assert entity_data["name"] == edit_data["one_sentence"]  # or appropriate field
    if "arc_type" in edit_data:
        assert entity_data.get("arc_type") == edit_data["arc_type"]
    if "arc_complete" in edit_data:
        assert entity_data.get("arc_complete") == edit_data["arc_complete"]

if entity_type == "plot":
    if "one_sentence" in edit_data:
        assert entity_data["one_sentence"] == edit_data["one_sentence"]
    if "status" in edit_data:
        assert entity_data["status"] == edit_data["status"]
    if "plot_type" in edit_data:
        assert entity_data.get("plot_type") == edit_data["plot_type"]

if entity_type == "scene":
    if "title" in edit_data:
        assert entity_data["title"] == edit_data["title"]
    if "status" in edit_data:
        assert entity_data["status"] == edit_data["status"]
    if "dramatic_role" in edit_data:
        assert entity_data.get("dramatic_role") == edit_data["dramatic_role"]

if entity_type == "arc":
    if "label" in edit_data:
        assert entity_data["label"] == edit_data["label"]
    if "y" in edit_data:
        assert entity_data.get("y") == edit_data["y"]
    if "is_crisis" in edit_data:
        assert entity_data.get("is_crisis") == edit_data["is_crisis"]

# Relation check — now embedded in plot
if entity_type == "plot":
    all_scenes = entity_data["setups"] + entity_data["crisis"] + entity_data["climax"] + entity_data["payoffs"]
    assert len(all_scenes) > 0, "Plot has no scene references after edit"
```

---

## Code anchors

| What | Where |
|---|---|
| `test_create_load_retrieve` | `tests/test_field_coverage.py:169-208` |
| `test_edit_all_field_types` | `tests/test_field_coverage.py:215-330` |
| `_create_parents` helper | `tests/test_field_coverage.py:98-147` |
| `_sample_frontmatter` helper | `tests/test_field_coverage.py:68-76` |

---

## Test impact

This IS the test task. After updates:
- `test_create_load_retrieve` finds entities in nested dicts
- `test_edit_all_field_types` verifies edits via nested dicts

---

## Legacy code removal

No code deletion — only test assertion updates.

---

## Checklist

- [ ] `test_create_load_retrieve` finds entity in nested structure (not `entities.rows`)
- [ ] `test_edit_all_field_types` verifies edits via nested dict (not `entities.rows`/`relations.rows`)
- [ ] Plot relation check uses embedded `setups`/`crisis`/`climax`/`payoffs` arrays
- [ ] All tests pass against Phase 1+2 implementation

---

## Final Brief

_To be filled after task completion._
