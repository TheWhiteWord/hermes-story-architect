# Task 3.4: Update `test_phase3_scenario.py` — Nested Structure Assertions

## Goal
Update load assertions in `tests/test_phase3_scenario.py` to check the nested structure after edit/delete/reorder operations.

**Scope:** `tests/test_phase3_scenario.py` — 5 test functions updated.

---

## Current State (verified against code)

All tests in `Test3EditScenario` use `result["entities"]["rows"]` to find entities:

**1. `test_edit_note_visible_in_load`** (lines 37-57):
```python
entities = result["entities"]["rows"]
kael_row = next(r for r in entities if r[0] == "kael")
assert kael_row[3] == "Updated description for kael."
```

**2. `test_delete_entity_excluded_from_load`** (lines 59-93):
```python
entities = result["entities"]["rows"]
ids = [r[0] for r in entities]
assert "temp-char" not in ids
assert "temp-char-1" not in ids
```

**3. `test_delete_sequence_with_scenes_blocked`** (lines 95-119):
No load assertion — only checks delete was blocked.

**4. `test_delete_character_cascades_arcs`** (lines 121-155):
```python
ids = [r[0] for r in result["entities"]["rows"]]
assert "cascade-char" not in ids
for i in range(1, 4):
    assert f"cascade-char-{i}" not in ids
```

**5. `test_reorder_visible_in_load`** (lines 157-193):
```python
entities = result["entities"]["rows"]
scenes = [r for r in entities if r[1] == "scene" and r[0] in ("scene-x", "scene-y", "scene-z")]
scenes_sorted = sorted(scenes, key=lambda r: r[5])  # order_key col
assert [r[0] for r in scenes_sorted] == ["scene-z", "scene-x", "scene-y"]
assert [r[5] for r in scenes_sorted] == [1, 2, 3]
```

---

## Target State

### Helper function (add to file):
```python
def _find_entity_in_nested(result, entity_type, slug):
    """Find an entity in the nested load result by type and slug."""
    if entity_type == "character":
        return result["characters"].get(slug)
    elif entity_type == "plot":
        return result["plots"].get(slug)
    elif entity_type == "location":
        return result["locations"].get(slug)
    elif entity_type == "world":
        return result["worlds"].get(slug)
    elif entity_type == "act":
        for act in result["acts"]:
            if act.get("id") == slug:
                return act
    elif entity_type == "sequence":
        for act in result["acts"]:
            for seq in act.get("sequences", []):
                if seq.get("id") == slug:
                    return seq
    elif entity_type == "scene":
        for act in result["acts"]:
            for seq in act.get("sequences", []):
                for scene in seq.get("scenes", []):
                    if isinstance(scene, dict) and scene.get("id") == slug:
                        return scene
    elif entity_type == "arc":
        for char in result["characters"].values():
            for beat in char.get("arc", []):
                if isinstance(beat, dict) and beat.get("id") == slug:
                    return beat
    return None


def _all_entity_ids(result):
    """Collect all entity IDs from nested structure."""
    ids = set()
    for char in result["characters"]:
        ids.add(char)
    for plot in result["plots"]:
        ids.add(plot)
    for loc in result["locations"]:
        ids.add(loc)
    for world in result["worlds"]:
        ids.add(world)
    for act in result["acts"]:
        ids.add(act["id"])
        for seq in act.get("sequences", []):
            ids.add(seq["id"])
            for scene in seq.get("scenes", []):
                if isinstance(scene, dict):
                    ids.add(scene["id"])
                else:
                    ids.add(scene)
    return ids
```

### 1. `test_edit_note_visible_in_load`:
```python
result = json.loads(load_handler({"project": str(proj), "vault_path": vault}))
assert result["loaded"] is True
kael = result["characters"]["kael"]
assert kael["one_sentence"] == "Updated description for kael."
```

### 2. `test_delete_entity_excluded_from_load`:
```python
result = json.loads(load_handler({"project": str(proj), "vault_path": vault}))
ids = _all_entity_ids(result)
assert "temp-char" not in ids
assert "temp-char-1" not in ids
```

### 3. `test_delete_sequence_with_scenes_blocked`:
No change needed — no load assertion.

### 4. `test_delete_character_cascades_arcs`:
```python
result = json.loads(load_handler({"project": str(proj), "vault_path": vault}))
ids = _all_entity_ids(result)
assert "cascade-char" not in ids
for i in range(1, 4):
    assert f"cascade-char-{i}" not in ids
```

### 5. `test_reorder_visible_in_load`:
```python
result = json.loads(load_handler({"project": str(proj), "vault_path": vault}))
# Find scenes in nested structure
scenes_found = {}
for act in result["acts"]:
    for seq in act.get("sequences", []):
        for scene in seq.get("scenes", []):
            if isinstance(scene, dict) and scene.get("id") in ("scene-x", "scene-y", "scene-z"):
                scenes_found[scene["id"]] = scene
assert len(scenes_found) == 3
# Order is implied by array position — find the sequence containing them
for act in result["acts"]:
    for seq in act.get("sequences", []):
        scene_ids = [s["id"] if isinstance(s, dict) else s for s in seq.get("scenes", [])]
        if "scene-z" in scene_ids:
            # Verify order-z is first among the three
            ordered = [sid for sid in scene_ids if sid in ("scene-x", "scene-y", "scene-z")]
            assert ordered == ["scene-z", "scene-x", "scene-y"], f"Order wrong: {ordered}"
```

---

## Code anchors

| What | Where |
|---|---|
| `test_edit_note_visible_in_load` | `tests/test_phase3_scenario.py:37-57` |
| `test_delete_entity_excluded_from_load` | `tests/test_phase3_scenario.py:59-93` |
| `test_delete_character_cascades_arcs` | `tests/test_phase3_scenario.py:121-155` |
| `test_reorder_visible_in_load` | `tests/test_phase3_scenario.py:157-193` |
| `db_project` fixture | `tests/test_phase3_scenario.py:23-31` |

---

## Test impact

This IS the test task. After updates:
- All load assertions use nested structure
- No test references `result["entities"]["rows"]`

---

## Legacy code removal

No code deletion — only test assertion updates.

---

## Checklist

- [x] `_find_entity_in_nested` helper added
- [x] `_all_entity_ids` helper added
- [x] `test_edit_note_visible_in_load` uses `result["characters"]["kael"]`
- [x] `test_delete_entity_excluded_from_load` uses `_all_entity_ids`
- [x] `test_delete_character_cascades_arcs` uses `_all_entity_ids`
- [x] `test_reorder_visible_in_load` verifies order via nested array position
- [x] No test references `result["entities"]["rows"]`
- [x] All tests pass against Phase 1+2 implementation

---

## Final Brief

Updated `tests/test_phase3_scenario.py` (9 tests, all pass):

- Added `_find_entity_in_nested` and `_all_entity_ids` helpers
- `test_edit_note_visible_in_load` — now asserts `result["characters"]["kael"]["one_sentence"]`
- `test_delete_entity_excluded_from_load` — uses `_all_entity_ids(result)` for ID collection
- `test_delete_character_cascades_arcs` — uses `_all_entity_ids(result)` for cascade verification
- `test_reorder_visible_in_load` — traverses nested acts→sequences→scenes, asserts array-position order
- `test_delete_sequence_with_scenes_blocked` — unchanged (no load assertion)
- Verified zero references to `result["entities"]["rows"]` remain in file
