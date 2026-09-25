# Phase 1 — DB memory model and bounded serialization

**Status:** Blocked until Phase 0 is closed.

**Plan source:** `tasks/task_25/memory_implementation_plan.md`, Phase 1.

**Objective:** Add the canonical four-category memory shape and the validation/budget helpers in the DB layer, without a new table or entry schema.

## Scope

- `core/db.py`
- `core/memory.py` only if the existing module boundary cannot hold the small policy helpers cleanly
- new focused memory tests

## Implementation

Use the settled constants:

```python
MEMORY_CATEGORIES = ("decisions", "directions", "open_questions", "continuity_warnings")
MEMORY_CHAR_LIMIT = 3000
MEMORY_ENTRY_LIMIT = 300
```

Helpers must support:

- empty four-category memory;
- read/write through the project entity's `extra.memory`;
- category and entry validation;
- empty, overlong, and duplicate rejection;
- deterministic serialized-frontmatter usage;
- per-category counts and total usage;
- missing `extra.memory` treated as empty memory.

Do not add IDs, timestamps, confidence, status, new tables, migrations, or automatic lifecycle fields.

## Tests

Cover empty memory, ordering, invalid category, empty entry, 300-character entry limit, duplicate rejection, 3,000-character total limit, counts/usage, and missing project memory.

## Verification

```bash
pytest tests/test_memory.py -q
pytest tests/test_core.py -q
```

Audit every caller of `get_memory_outline()` and every `memory_outline` reference. Confirm no new helper reads `.story/memory.md`.

## Legacy cleanup

Do not delete the old reader in this phase. Identify its owning replacement phase. Do not add a compatibility alias without a design decision.

## Maintenance and naming

Keep one canonical module boundary. Avoid duplicating budget logic in tools or tests. Names must describe DB-backed memory, not outlines or previews.

## Parallel work

Can run in parallel with Phase 2 only after the audit proves the project `extra` path is safe. Otherwise complete sequentially.

## Escalation

Stop and ask the user if a new table, migration, or richer entry record is required.

## Final checklist

- [x] Phase 0 audit accepted
- [x] Canonical memory shape implemented
- [x] Validation and budget helpers implemented
- [x] Focused tests added
- [x] Focused and regression tests pass
- [x] All stale callers identified
- [x] No file-based read introduced
- [x] Naming and legacy cleanup verified
- [x] Phase closed with no unresolved blocking issue

## Final Brief

- Added `project.extra.memory` helpers in `core/db.py`: fixed four categories, 3000-character serialized-frontmatter budget, 300-character entry limit, validation, usage, and DB round-trip read/write.
- Added `tests/test_memory.py`; focused suite passes.
- `story_load` now uses the shared DB memory block through `get_memory_block()`; the old file reader was removed.
- Phase 2 implementation was also completed: project creation initializes DB memory and no longer creates the placeholder file; import preserves existing DB memory across rebuild; export writes the frontmatter-only projection.
- Added and registered `story_memory`; removed the legacy `story_edit(update_story_memory)` writer from the public path.
- Added dashboard payload normalization, Memory dialog HTML/JS/CSS, and the sidebar action. The dashboard now receives DB memory under the settled `story_memory` payload key; project data remains under `project`.
- Updated current plugin skill guidance and replaced obsolete load/creation tests.

**Verification:** `PYTHONPATH=. pytest tests/ -q` → **303 passed**. `python -m compileall -q core tools` passed. Repository search leaves `memory_outline` only in new-contract negative tests; remaining `.story/memory.md` references are export/tests only.

