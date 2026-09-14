# D1 — Remove/Rewrite `TestStructureIndex` Tests

**Goal:** Delete the 5 tests in `TestStructureIndex` class that test `generate_structure_index()` output. Replace with a test that verifies `generate_index()` includes structural fields.

## Why

`generate_structure_index()` is deleted in A2. Tests that call it will fail with `ImportError`. The behavior they tested (structural fields present) is now tested differently — `generate_index()` itself includes those fields.

## Current State

`tests/test_core.py` lines 648-820: `TestStructureIndex` class with 5 tests:
- `test_structure_index_includes_story` (651)
- `test_structure_index_includes_file_scenes` (700)
- `test_structure_index_includes_sequences_and_acts` (732)
- `test_structure_index_scene_fields` (766)
- `test_structure_index_arc_beat_refs_empty` (803)

All call `generate_structure_index(index)` — a function that no longer exists.

## Changes

1. **`tests/test_core.py`** — Delete the entire `TestStructureIndex` class (lines 648-820).

2. **Add replacement test** in `TestIndexGeneration` class (or new class):
   ```python
   def test_generate_index_includes_dramatic_metadata(self, project_path):
       """Unified index: scenes contain dramatic metadata."""
       from core.index import generate_index
       index = generate_index(project_path)
       
       scene = next(s for s in index["scenes"] if s["id"] == "central-room-day")
       assert scene["value"] == "Trust"
       assert scene["value_open"] == "positive"
       assert scene["value_close"] == "negative"
       assert scene["conflict_levels"] == ["inner", "personal"]
       assert scene["dramatic_role"] == "setup"
       assert scene["is_inciting_incident"] is False
       assert scene["is_sequence_climax"] is False
       assert scene["is_act_climax"] is False
       assert scene["is_story_climax"] is False
   ```

## Verification Checklist

- [x] `TestStructureIndex` class removed from `test_core.py`
- [x] No references to `generate_structure_index` in tests
- [x] New test verifies dramatic metadata present in `generate_index()` output
- [x] All remaining tests pass (67/67 after D2)

## Final Notes

`TestStructureIndex` class (lines 648-821, 5 tests) deleted. Replacement test `test_generate_index_includes_dramatic_metadata` added to `TestIndexGeneration` class. Zero references to `generate_structure_index` remain in test file.

## Notes

- Depends on A2 (function deletion)
- The new test verifies the unified behavior: `generate_index()` produces complete data
