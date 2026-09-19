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

**Completed** — All verification checks pass.

### Verification Results
| Pattern | Files Checked | Result |
|---------|---------------|--------|
| `entities["rows"]` | `test_core.py`, `test_phase2_db_reads.py`, `test_field_coverage.py`, `test_phase3_scenario.py` | ✅ Zero references |
| `relations["rows"]` | All test files | ✅ Zero references |
| `result["memory"]` | `test_core.py`, `test_phase2_db_reads.py` | ✅ Zero references |
| `"cols" in result["entities"]` | All test files | ✅ Zero references |
| `"rows" in result["relations"]` | All test files | ✅ Zero references |
| `load_result["entities"]["cols"]` | All test files | ✅ Zero references |

### Legacy test names checked (all absent)
- `test_load_no_derived_arrays` ✅ removed
- `test_load_relations_completeness` ✅ removed
- `test_load_returns_column_format` ✅ removed
- `test_load_no_sections_list` ✅ removed

### Positive assertions (correctly present)
- `assert "entities" not in result` — present in `test_core.py:604` and `test_phase2_db_reads.py:95`
- `assert "relations" not in result` — present in `test_core.py:605` and `test_phase2_db_reads.py:101`
- `assert "memory" not in result` — present in `test_core.py:606` and `test_phase2_db_reads.py:107`
- `assert "memory_outline" in result` — present in `test_core.py:602` and `test_phase2_db_reads.py:108`

No stale references remain. Task complete.
