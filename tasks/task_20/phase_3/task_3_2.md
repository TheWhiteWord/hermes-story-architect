# Task 3.2: Update `test_core.py` — Nested Shape Assertions

## Goal
Update load-related tests in `tests/test_core.py` to assert the new nested payload shape instead of old column/relation format. Also update unfilled assertions to inverted shape.

**Scope:** `tests/test_core.py` — 3 test functions updated.

---

## Current State (verified against code)

### Tests to update (3):

**1. `test_story_load_works_after_create`** (lines 583-595):
```python
def test_story_load_works_after_create(self, tmp_path):
    args = {
        "entity_type": "project",
        "slug": "test-proj",
        "project": "",
        "frontmatter": {"name": "Test Project"},
    }
    create_handler(args, vault_path=str(tmp_path))
    load_args = {"project": str(tmp_path / "projects" / "test-proj")}
    result = json.loads(load_handler(load_args, vault_path=str(tmp_path)))
    assert result["loaded"] is True
    assert result["project"]["name"] == "Test Project"
```
Currently only asserts `loaded` and `project.name` — minimal. Should add nested structure assertions.

**2. `test_get_project_summary_includes_unfilled`** (lines 972-993):
```python
def test_get_project_summary_includes_unfilled(self, tmp_path):
    ...
    summary = get_project_summary(project_path)
    assert "unfilled" in summary
    char_unfilled = summary["unfilled"].get("test-char", [])
    assert len(char_unfilled) > 0
    assert "goals_short" in char_unfilled
```
Currently asserts `summary["unfilled"]["test-char"]` is a list of field names. New shape: `summary["unfilled"]["goals_short"]` is a list of entity slugs.

**3. `test_created_character_has_unfilled_fields`** (lines 995-1016):
```python
def test_created_character_has_unfilled_fields(self, tmp_path):
    ...
    summary = get_project_summary(project_path)
    char_unfilled = summary["unfilled"].get("test-char", [])
    assert "goals_short" in char_unfilled
    assert "goals_long" in char_unfilled
    assert "story_role" not in char_unfilled
```
Same inversion needed.

---

## Target State

### 1. `test_story_load_works_after_create` — expanded:
```python
def test_story_load_works_after_create(self, tmp_path):
    args = {
        "entity_type": "project",
        "slug": "test-proj",
        "project": "",
        "frontmatter": {"name": "Test Project"},
    }
    create_handler(args, vault_path=str(tmp_path))
    load_args = {"project": str(tmp_path / "projects" / "test-proj")}
    result = json.loads(load_handler(load_args, vault_path=str(tmp_path)))
    assert result["loaded"] is True
    assert result["project"]["name"] == "Test Project"
    # New: nested structure present
    assert "acts" in result
    assert "characters" in result
    assert "plots" in result
    assert "locations" in result
    assert "worlds" in result
    assert "unfilled" in result
    assert "memory_outline" in result
    # Old keys gone
    assert "entities" not in result
    assert "relations" not in result
    assert "memory" not in result
```

### 2. `test_get_project_summary_includes_unfilled` — inverted:
```python
def test_get_project_summary_includes_unfilled(self, tmp_path):
    from tools.story_create import handler as create_handler
    from core.db import get_project_summary

    project_path = _make_minimal_project(tmp_path)

    args = {
        "entity_type": "character",
        "slug": "test-char",
        "project": str(project_path),
        "frontmatter": {"name": "Test Char", "story_role": "Protagonist"}
    }
    result = json.loads(create_handler(args))
    assert result["success"]

    summary = get_project_summary(project_path)
    assert "unfilled" in summary
    # New: inverted shape — field name → [entity slugs]
    assert "goals_short" in summary["unfilled"]
    assert "test-char" in summary["unfilled"]["goals_short"]
    assert "goals_long" in summary["unfilled"]["goals_short"]
```

### 3. `test_created_character_has_unfilled_fields` — inverted:
```python
def test_created_character_has_unfilled_fields(self, tmp_path):
    from tools.story_create import handler as create_handler
    from core.db import get_project_summary

    project_path = _make_minimal_project(tmp_path)

    char_args = {
        "entity_type": "character",
        "slug": "test-char",
        "project": str(project_path),
        "frontmatter": {"name": "Test Char", "story_role": "Protagonist"}
    }
    json.loads(create_handler(char_args))

    summary = get_project_summary(project_path)
    # New: inverted — field → [entities]
    assert "goals_short" in summary["unfilled"]
    assert "goals_long" in summary["unfilled"]
    assert "test-char" in summary["unfilled"]["goals_short"]
    assert "test-char" in summary["unfilled"]["goals_long"]
```

---

## Code anchors

| What | Where |
|---|---|
| `test_story_load_works_after_create` | `tests/test_core.py:583-595` |
| `test_get_project_summary_includes_unfilled` | `tests/test_core.py:972-993` |
| `test_created_character_has_unfilled_fields` | `tests/test_core.py:995-1016` |
| `_make_minimal_project` helper | `tests/test_core.py:177-187` |

---

## Test impact

This IS the test task. After updates:
- Load test asserts nested shape + old keys gone
- Both unfilled tests assert inverted shape

---

## Legacy code removal

No code deletion — only test assertion updates.

---

## Checklist

- [ ] `test_story_load_works_after_create` asserts nested keys (acts, characters, plots, locations, worlds, unfilled, memory_outline)
- [ ] `test_story_load_works_after_create` asserts old keys gone (entities, relations, memory)
- [ ] `test_get_project_summary_includes_unfilled` asserts inverted unfilled shape
- [ ] `test_created_character_has_unfilled_fields` asserts inverted unfilled shape
- [ ] All 3 tests pass against Phase 1+2 implementation

---

## Final Brief

_To be filled after task completion._
