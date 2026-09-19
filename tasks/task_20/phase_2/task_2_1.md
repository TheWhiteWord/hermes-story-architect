# Task 2.1: Simplify `_db_response` — Pass-Through Wrapper

## Goal
Simplify `_db_response` in `tools/story_load.py` to pass through the new nested payload from `get_project_summary()` directly, removing all old column/relation/memory extraction logic.

**Scope:** `tools/story_load.py` — rewrite `_db_response()` and simplify `handler()`.

---

## Current State (verified against code)

`tools/story_load.py:65-104` — `_db_response()`:
- Extracts `project`, `entities`, `relations` from summary dict
- Counts entities by type from `entities["rows"]` for confirmation string
- Reads full `.story/memory.md` text via `memory_path.read_text()`
- Returns `{loaded, confirmation, project, entities, relations, memory, unfilled}`

`tools/story_load.py:18-62` — `handler()`:
- Resolves project path
- Checks DB exists and has schema
- Calls `get_project_summary(project_path)` → passes to `_db_response`

---

## Target State

`get_project_summary()` (after Phase 1) returns the complete payload:
```json
{
  "loaded": true,
  "confirmation": "...",
  "project": {...},
  "acts": [...],
  "characters": {...},
  "plots": {...},
  "locations": {...},
  "worlds": {...},
  "unfilled": {...},
  "memory_outline": {...}
}
```

`_db_response()` becomes a thin pass-through:
```python
def _db_response(summary: dict, project_path: Path) -> str:
    return json.dumps(summary)
```

Or the handler can call `json.dumps(summary)` directly, making `_db_response` unnecessary.

---

## Implementation Plan

### Step 1: Simplify `_db_response`
- Remove all extraction of `entities`, `relations`, `memory` keys
- Remove entity-type counting logic (confirmation now from builder)
- Remove `memory_path.read_text()` call (memory_outline now from builder)
- Return `json.dumps(summary)` directly — the summary IS the response

### Step 2: Simplify `handler` (if needed)
- After Phase 1, `summary` already contains `loaded: True` and `confirmation`
- `handler` can return `_db_response(summary, project_path)` as before, or inline it
- Keep the error handling (DB not found, schema not found, exceptions)

### Step 3: Remove unused imports
- After simplification, check if `json` import is still needed (yes — for error responses)
- Check if `Path` import is still needed (yes — for type hints and error paths)

---

## Code anchors

| What | Where |
|---|---|
| Current `_db_response()` | `tools/story_load.py:65-104` |
| Current `handler()` | `tools/story_load.py:18-62` |
| Memory file read (to remove) | `tools/story_load.py:90-94` |
| Entity counting (to remove) | `tools/story_load.py:72-88` |

---

## Test impact

No tests in this task (Phase 3). After this task, the tool output shape changes completely — all load tests will fail until Phase 3.

---

## Legacy code removal

This task deletes:
- `entities` key from response (replaced by nested `acts`/`characters`/etc.)
- `relations` key from response (gone — embedded in nested structure)
- `memory` key from response (replaced by `memory_outline`)
- Entity-type counting logic in `_db_response`
- Full memory file read in `_db_response`

---

## Checklist

- [ ] `_db_response` returns `json.dumps(summary)` — pure pass-through
- [ ] No reference to `entities`, `relations`, `memory` keys in `_db_response`
- [ ] No entity-type counting logic
- [ ] No `memory_path.read_text()` call
- [ ] `handler` still handles errors (DB not found, schema not found, exceptions)
- [ ] Response contains `loaded: True` and `confirmation` from builder
- [ ] Response contains `acts`, `characters`, `plots`, `locations`, `worlds`, `unfilled`, `memory_outline`
- [ ] Response does NOT contain `entities`, `relations`, `memory` keys

---

## Final Brief

_To be filled after task completion._
