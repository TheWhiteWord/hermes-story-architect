# F1 — Add Deprecation Note to `tasks/task_12/phase_2/plan.md`

**Goal:** Document that the two-file approach (Phase 2) was reverted in favor of unified index.

## Why

The historical record matters. Future maintainers will see Phase 2 (split index) and wonder if it was ever implemented. This note tells them: yes, but it was reverted.

## Changes

1. **`tasks/task_12/phase_2/plan.md`** — Add at the top:
   ```markdown
   > **Deprecated (2026-09-14):** The two-file approach (main index + structure-index sidecar) was reverted in Task 13 in favor of a unified index. This plan is preserved for historical context.
   ```

## Verification Checklist
- [x] Deprecation note added at top of Phase 2 plan
- [x] Note references Task 13 (unified index)

## Completed
- Added deprecation note after the frontmatter block in `tasks/task_12/phase 2/plan.md`
