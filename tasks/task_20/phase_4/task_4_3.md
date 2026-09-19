# Task 4.3: Remove Legacy Test Patterns

## Goal
Remove any remaining test assertions that reference the old column/relations format across all test files. This is a sweep to ensure no stale assertions remain.

**Scope:** All test files — grep-based verification + removal.

---

## Current State (after Phase 3 implementation)

All test files have been updated (Tasks 3.1-3.5). Need to verify no stale references remain:

1. No `result["entities"]["rows"]` in any test
2. No `result["relations"]["rows"]` in any test
3. No `result["memory"]` in any test (should be `result["memory_outline"]`)
4. No `"cols" in result["entities"]` assertions
5. No `"rows" in result["relations"]` assertions

---

## Verification Checklist

### Sweep all test files for old patterns:
- [ ] `tests/test_core.py` — no `entities["rows"]`, `relations["rows"]`, `memory` references
- [ ] `tests/test_phase2_db_reads.py` — no `entities["rows"]`, `relations["rows"]`, `memory` references
- [ ] `tests/test_field_coverage.py` — no `entities["rows"]`, `relations["rows"]` references
- [ ] `tests/test_phase3_scenario.py` — no `entities["rows"]` references
- [ ] `tests/test_arcs.py` — no `"N arc beats"` confirmation assertions

### Specific patterns to grep and remove:
- [ ] `result["entities"]["rows"]` — gone from all files
- [ ] `result["relations"]["rows"]` — gone from all files
- [ ] `result["memory"]` — gone from all files (replaced by `memory_outline`)
- [ ] `"cols" in result["entities"]` — gone from all files
- [ ] `"rows" in result["relations"]` — gone from all files
- [ ] `load_result["entities"]["cols"]` — gone from all files

---

## Code anchors

| What | Where |
|---|---|
| All test files | `tests/test_*.py` |
| Grep patterns | `entities.*rows`, `relations.*rows`, `result\["memory"\]` |

---

## Remediation (if issues found)

If any stale references found:
- Remove or replace with nested structure assertions
- Ensure no test references old flat format

---

## Final Brief

_To be filled after task completion._
