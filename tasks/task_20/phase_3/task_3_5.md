# Task 3.5: Update `test_arcs.py` — Confirmation Format

## Goal
Update the confirmation assertion in `tests/test_arcs.py` to match the new confirmation format.

**Scope:** `tests/test_arcs.py` — 1 test function updated.

---

## Current State (verified against code)

**`test_load_includes_arc_count`** (lines 343-365):
```python
def test_load_includes_arc_count(self, tmp_path):
    """story_load confirmation includes arc count."""
    from tools.story_create import handler as create_handler
    from tools.story_load import handler as load_handler

    create_handler({
        "entity_type": "character", "slug": "kael", "project": str(tmp_path),
        "frontmatter": {"name": "Kael", "story_role": "Protagonist", "one_sentence": "Test"}
    })
    create_handler({
        "entity_type": "arc", "slug": "1", "project": str(tmp_path),
        "frontmatter": {
            "id": "1", "character": "kael",
            "label": "Beat", "action": "a", "gap": "g",
            "choice": "c", "shift": "s", "y": 0.0, "order": 1,
        }
    })

    result = load_handler({
        "project": str(tmp_path)
    })
    data = json.loads(result)
    assert "1 arc beat" in data["confirmation"]
```

**`test_load_fixture_includes_arc_count`** (lines 405-413):
```python
def test_load_fixture_includes_arc_count(self):
    """story_load confirmation includes fixture arc count."""
    from tools.story_load import handler as load_handler

    result = load_handler({
        "project": str(self.FIXTURE_PATH)
    })
    data = json.loads(result)
    assert "11 arc beats" in data["confirmation"]
```

---

## Target State

The new confirmation format (spec §2):
```
Loaded <name> — N scenes (M developed), N sequences, N acts, N characters, N locations, N plots, N worlds.
```

Note: **no arc count** in the new confirmation. Arc beats are no longer a top-level count — they're nested inside characters.

### 1. `test_load_includes_arc_count` — updated:
```python
def test_load_includes_arc_count(self, tmp_path):
    """story_load confirmation includes character count."""
    from tools.story_create import handler as create_handler
    from tools.story_load import handler as load_handler

    create_handler({
        "entity_type": "character", "slug": "kael", "project": str(tmp_path),
        "frontmatter": {"name": "Kael", "story_role": "Protagonist", "one_sentence": "Test"}
    })
    create_handler({
        "entity_type": "arc", "slug": "1", "project": str(tmp_path),
        "frontmatter": {
            "id": "1", "character": "kael",
            "label": "Beat", "action": "a", "gap": "g",
            "choice": "c", "shift": "s", "y": 0.0, "order": 1,
        }
    })

    result = load_handler({
        "project": str(tmp_path)
    })
    data = json.loads(result)
    # New format: no arc count, but character count present
    assert "1 characters" in data["confirmation"]
    # Arc beat is nested in character
    assert "kael" in data["characters"]
    assert len(data["characters"]["kael"]["arc"]) > 0
```

### 2. `test_load_fixture_includes_arc_count` — updated:
```python
def test_load_fixture_includes_arc_count(self):
    """story_load confirmation includes fixture character count."""
    from tools.story_load import handler as load_handler

    result = load_handler({
        "project": str(self.FIXTURE_PATH)
    })
    data = json.loads(result)
    # New format: character count instead of arc count
    assert "characters" in data["confirmation"]
    # Arc beats are nested in characters
    total_arcs = sum(len(c.get("arc", [])) for c in data["characters"].values())
    assert total_arcs > 0
```

---

## Code anchors

| What | Where |
|---|---|
| `test_load_includes_arc_count` | `tests/test_arcs.py:343-365` |
| `test_load_fixture_includes_arc_count` | `tests/test_arcs.py:405-413` |
| `TestArcLoadTool` class | `tests/test_arcs.py:342-413` |

---

## Test impact

This IS the test task. After updates:
- Confirmation assertions match new format (no arc count)
- Arc beats verified via nested character structure

---

## Legacy code removal

No code deletion — only test assertion updates.

---

## Checklist

- [x] `test_load_includes_arc_count` asserts new confirmation format
- [x] `test_load_fixture_includes_arc_count` asserts new confirmation format
- [x] Both tests verify arc beats via nested character structure
- [x] No test asserts "N arc beats" in confirmation
- [x] All tests pass against Phase 1+2 implementation

---

## Final Brief

Updated both load tests in `tests/test_arcs.py` to match the new confirmation format (no arc count — arc beats are nested in characters):

1. **`test_load_includes_arc_count`** — now asserts `"1 characters"` in confirmation, verifies arc beat is nested in `data["characters"]["kael"]["arc"]`.
2. **`test_load_fixture_includes_arc_count`** — now asserts `"characters"` in confirmation, sums arc beats across all characters to verify > 0.

All 23 tests in `test_arcs.py` pass.
