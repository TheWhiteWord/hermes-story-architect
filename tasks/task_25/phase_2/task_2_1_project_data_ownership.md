# Phase 2 — Project creation and import/export data ownership

**Status:** Blocked until Phase 1 is closed.

**Plan source:** `tasks/task_25/memory_implementation_plan.md`, Phase 2.

**Objective:** Make DB memory the operational source and remove placeholder memory-file creation from project creation.

## Scope

- `tools/story_create.py`
- `tools/story_export.py`
- `tools/story_import.py` only if its merge can erase `project.extra.memory`
- `core/db.py` only if initialization must be shared
- project creation, import/export, and memory tests

## Implementation

- Initialize `project.extra.memory` with four empty arrays in the project DB insert.
- Do not create `.story/memory.md` during normal project creation.
- Keep the existing `project.md` path; its broader cleanup is deferred.
- Preserve `project.extra.memory` during import.
- Do not add a file-based fallback.
- The export implementation may be completed in this phase or coordinated with Phase 5; do not duplicate writers.

## Tests

Cover DB initialization, no placeholder memory file dependency, import preservation, and export projection if implemented here.

## Verification

```bash
pytest tests/test_core.py tests/test_memory.py -q
```

Audit `_create_project()`, `story_import`, `story_export._export_all()`, and every `.story/memory.md` read/write.

## Legacy cleanup

Replace tests that assert placeholder memory sections. Do not keep the old file scaffold as a compatibility contract.

## Maintenance and naming

`story_create` should not own memory policy. Use the canonical Phase 1 helpers rather than a second empty-array literal.

## Parallel work

May overlap with Phase 1 helper work only after the audit confirms the `extra` shape. Export projection should be coordinated with Phase 5, not implemented twice.

## Escalation

Ask the user if project resolution or a non-placeholder contract depends on creation-time memory files.

## Final checklist

- [x] Phase 1 helpers reused
- [x] Project DB memory initialized
- [x] Placeholder memory creation removed
- [x] Import preservation verified
- [x] Export ownership not duplicated
- [x] Legacy tests replaced
- [x] All `.story/memory.md` paths audited
- [x] Naming and maintenance checked
- [x] Phase closed with no unresolved blocking issue

## Final Brief

- Project creation initializes `project.extra.memory`; it no longer creates the placeholder memory file.
- Import snapshots existing DB memory before the full rebuild and restores it after re-import.
- Export is the only production writer of `.story/memory.md`, with frontmatter-only output and stable category/entry order.
- Added export projection tests; focused and full suites pass.

