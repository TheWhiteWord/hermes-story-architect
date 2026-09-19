# Task 5.1: Final Verification — Full Test Suite + Token Budget

## Goal
Run the complete test suite and verify the token budget target is met. This is the final gate for the entire redesign.

**Scope:** Run tests, measure payload size, verify all spec targets.

---

## Steps

### Step 1: Run full test suite
```bash
cd /media/theww/AI/Projects/Plugins/Hermes/hermes-story-architect && python -m pytest tests/test_core.py tests/test_phase2_db_reads.py tests/test_arcs.py tests/test_phase3_scenario.py tests/test_field_coverage.py -v
```

All tests must pass. If any fail:
- Identify the failing test
- Determine if it's a test issue or implementation issue
- Fix and re-run

### Step 2: Measure fixture payload size
```python
import json
from tools.story_load import handler as load_handler
from pathlib import Path

fixture = Path("tests/fixtures/save-the-children")
result = json.loads(load_handler({"project": str(fixture)}))
data = json.dumps(result)
est_tokens = len(data) // 4
print(f"Estimated tokens: {est_tokens}")
print(f"Characters: {len(data)}")
assert est_tokens < 8500, f"Over budget: {est_tokens} tokens"
```

### Step 3: Verify confirmation format
```python
conf = result["confirmation"]
assert conf.startswith("Loaded Save the Children — ")
assert "scenes" in conf
assert "developed" in conf
assert "sequences" in conf
assert "acts" in conf
assert "characters" in conf
assert "locations" in conf
assert "plots" in conf
assert "worlds" in conf
```

### Step 4: Verify stub classification in fixture
```python
# Count full vs stub scenes
full_scenes = 0
stub_scenes = 0
for act in result["acts"]:
    for seq in act.get("sequences", []):
        for scene in seq.get("scenes", []):
            if isinstance(scene, dict) and scene.get("dramatic_role"):
                full_scenes += 1
            else:
                stub_scenes += 1

print(f"Full scenes: {full_scenes}, Stub scenes: {stub_scenes}")
assert full_scenes > 0, "No full scenes in fixture"
assert stub_scenes > 0, "No stub scenes in fixture"
```

### Step 5: Verify unfilled inverted shape
```python
unfilled = result["unfilled"]
assert isinstance(unfilled, dict)
for field, entities in unfilled.items():
    assert isinstance(entities, list), f"unfilled[{field}] is not a list"
    assert len(entities) > 0, f"unfilled[{field}] is empty"
```

### Step 6: Verify memory_outline
```python
assert "memory_outline" in result
assert "status" in result["memory_outline"]
assert "sections" in result["memory_outline"]
assert isinstance(result["memory_outline"]["sections"], list)
```

---

## Checklist

- [ ] Full test suite passes (test_core, test_phase2_db_reads, test_arcs, test_phase3_scenario, test_field_coverage)
- [ ] Fixture payload < 8,500 tokens
- [ ] Confirmation message matches spec format
- [ ] Stub classification visible in fixture (both full and stub scenes)
- [ ] `unfilled` inverted shape verified against fixture
- [ ] `memory_outline` present (not full memory text)
- [ ] No test references `result["entities"]["rows"]` or `result["relations"]["rows"]`
- [ ] `get_dashboard_data()` unaffected (dashboard tests pass)

---

## Final Brief

_To be filled after task completion._
