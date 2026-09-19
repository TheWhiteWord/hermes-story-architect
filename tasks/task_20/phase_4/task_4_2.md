# Task 4.2: Naming Convention Sweep — `tools/story_load.py`

## Goal
Ensure `_db_response` and `handler` in `tools/story_load.py` have zero references to old `entities`/`relations`/`memory` keys. Verify all dead code from the old wrapper is removed.

**Scope:** `tools/story_load.py` — grep-based verification + cleanup.

---

## Current State (after Phase 2 implementation)

`_db_response()` has been simplified (Task 2.1) to a pass-through. Need to verify:

1. No references to `entities`, `relations`, `memory` keys
2. No dead code from the old wrapper remaining
3. No entity-type counting logic
4. No memory file read

---

## Verification Checklist

### No old keys in response builder:
- [ ] No `entities` reference in `_db_response()` / `handler()`
- [ ] No `relations` reference in `_db_response()` / `handler()`
- [ ] No `memory` reference in `_db_response()` / `handler()` (only `memory_outline`)
- [ ] No `summary.get("entities"...)` or `summary.get("relations"...)` calls
- [ ] No `summary.get("memory"...)` call

### No dead code:
- [ ] No entity-type counting logic (`type_counts`, `counts_arc`, etc.)
- [ ] No `memory_path.read_text()` call
- [ ] No `confirmation` recomputation from rows

### Response shape:
- [ ] `json.dumps(summary)` is the return value (pure pass-through)
- [ ] `loaded: True` and `confirmation` come from the builder, not recomputed here

---

## Code anchors

| What | Where |
|---|---|
| `_db_response()` | `tools/story_load.py:65` (simplified in Phase 2) |
| `handler()` | `tools/story_load.py:18` |
| `loaded` key | Set by builder (Phase 1), passed through |
| `confirmation` key | Set by builder (Phase 1), passed through |

---

## Remediation (if issues found)

If any old references found:
- Remove dead code
- Ensure pure pass-through of builder output

---

## Final Brief

_To be filled after task completion._
