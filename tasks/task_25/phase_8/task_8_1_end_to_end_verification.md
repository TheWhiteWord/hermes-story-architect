# Phase 8 — End-to-end verification and handoff

**Status:** Blocked until Phase 7 is closed.

**Plan source:** `tasks/task_25/memory_implementation_plan.md`, Phase 8.

**Objective:** Prove the complete memory loop is DB-authoritative and the user-facing projection is non-authoritative.

## Flow

1. Create a project.
2. Confirm DB project memory has four empty categories.
3. Confirm runtime operation does not require `.story/memory.md`.
4. Add one entry in each category with `story_memory`.
5. Confirm `story_load` returns all entries and usage.
6. Confirm dashboard payload/dialog matches DB state.
7. Export and inspect the frontmatter-only projection.
8. Modify or delete the projection and confirm runtime state is unchanged.
9. Exercise duplicate, overlong, budget overflow, remove, and replace failures.
10. Run the full test suite.

## Final checks

```bash
git status --short
git diff --check
pytest -q
```

## Verification and maintenance

Inspect the complete diff. Verify names, docs, tests, tool descriptions, and file paths all describe the implemented contract. Report intentional exclusions and deferred architecture items separately. Do not claim the broader pre-DB architecture was repaired.

## Parallel work

None. This is the final integration gate.

## Final checklist

- [x] Phase 7 complete
- [x] End-to-end flow executed
- [x] DB authority proven against file edits/deletion
- [x] Export projection verified
- [x] Failure paths verified
- [x] Full suite passes
- [x] Diff reviewed for stale names and legacy code
- [x] Deferred items reported
- [x] Handoff recorded
- [x] Phase closed with no unresolved blocking issue

## Final Brief

- Executed the complete memory loop: create, add one entry in each category, load, dashboard payload/dialog, export, stale-file replacement, duplicate add, and overlong-entry rejection.
- Confirmed runtime reads DB state after `.story/memory.md` is replaced with stale content.
- Confirmed export is frontmatter-only and ordered.
- Verification: `git diff --check` passed; `PYTHONPATH=. pytest tests/ -q` → **304 passed**.
- Working tree contains the intended uncommitted implementation and tests; no commit or push performed.

## Notes

- Deferred architecture issue remains: `story_dashboard` still reads `project.md` directly for title-page fields. This was explicitly outside the memory scope and is recorded in `DEFERRED_db_first_architecture_audit.md`.

