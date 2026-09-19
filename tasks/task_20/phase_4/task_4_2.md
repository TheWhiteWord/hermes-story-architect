# Task 4.2: Naming Convention Sweep — `tools/story_load.py`

## Goal
Ensure `_db_response` and `handler` in `tools/story_load.py` have zero references to old `entities`/`relations`/`memory` keys. Verify all dead code from the old wrapper is removed.

**Scope:** `tools/story_load.py` — grep-based verification + cleanup.

---

## Current State (after Phase 2 implementation)

`_db_response()` was removed entirely in Phase 2 (Task 2.1). `handler()` returns `json.dumps(summary)` directly. Need to verify:

1. No references to `entities`, `relations`, `memory` keys
2. No dead code from the old wrapper remaining
3. No entity-type counting logic
4. No memory file read

---

## Verification Checklist

### No old keys in response builder:
- [x] No `entities` reference in `_db_response()` / `handler()` — **PASS**: grep found zero hits (only docstrings, now updated)
- [x] No `relations` reference in `_db_response()` / `handler()` — **PASS**: grep found zero hits
- [x] No `memory` reference in `_db_response()` / `handler()` (only `memory_outline`) — **PASS**: grep found zero hits (docstrings updated)
- [x] No `summary.get("entities"...)` or `summary.get("relations"...)` calls — **PASS**: none present
- [x] No `summary.get("memory"...)` call — **PASS**: none present

### No dead code:
- [x] No entity-type counting logic (`type_counts`, `counts_arc`, etc.) — **PASS**: none present
- [x] No `memory_path.read_text()` call — **PASS**: none present
- [x] No `confirmation` recomputation from rows — **PASS**: none present

### Response shape:
- [x] `json.dumps(summary)` is the return value (pure pass-through) — **PASS**: line 52
- [x] `loaded: True` and `confirmation` come from the builder, not recomputed here — **PASS**: handler is pure pass-through

---

## Code anchors

| What | Where |
|---|---|
| `_db_response()` | **REMOVED** (Task 2.1) — handler inlines `json.dumps(summary)` |
| `handler()` | `tools/story_load.py:18` |
| `loaded` key | Set by builder (Phase 1), passed through |
| `confirmation` key | Set by builder (Phase 1), passed through |

---

## Remediation (if issues found)

Two stale docstring references found and fixed:
- Module docstring: `"index and memory"` → `"nested index"`
- Handler docstring: `"index and memory"` → `"nested index"`

---

## Final Brief

**Status: COMPLETE ✅**

`_db_response()` was already removed in Phase 2 (Task 2.1). `handler()` is a pure pass-through — it calls `get_project_summary()` and returns `json.dumps(summary)` with zero transformation. No references to `entities`, `relations`, or `memory` keys remain anywhere in the file (grep-verified).

**Changes made:**
- `tools/story_load.py:1` — module docstring: "index and memory" → "nested index"
- `tools/story_load.py:19` — handler docstring: "index and memory" → "nested index"

**Verification:** Full checklist passes. No dead code, no old key references, no entity counting, no memory file reads. Confirmation and `loaded` come from the builder (Phase 1), not recomputed here.

**Deferred:** None.
