# Task 32 — Remove the plugin's pre-existing DB migration code

**Status:** not started. Carved out of `tasks/task_31/` by decision during its phase 6
verification.

## Why this exists

`tasks/task_31/` runs under the rule *no migration code in the plugin*, because the plugin
has never been deployed. Verification found the plugin **already violates that rule**, in
code unrelated to plot roles:

- `core/db.py:86-97` — `ensure_soft_delete_columns`, adds `is_deleted` / `deleted_at`
- `core/db.py:68-82` — `ensure_draft_status_column`, adds `drafts.status`

Both are called unconditionally from `get_db` (`core/db.py:124-126`), which documents
itself as repairing "a database this build did not create". Guarded by
`tests/test_legacy_db_migration.py`.

## Decision taken in task 31

Leave them alone there. They do real work — the live test project's `story.db` predates the
soft-delete change, so removing them mid-task would break live verification as well as widen
a plot-role diff into an unrelated refactor. **Scoped out, not excused.**

## What this task does

1. Delete `ensure_soft_delete_columns` and `ensure_draft_status_column`.
2. Delete their call sites in `get_db`, and the paragraph in its docstring describing them.
3. Delete `tests/test_legacy_db_migration.py`.
4. Regenerate every database that predates those columns — at minimum the live project at
   `/media/theww/AI/TWW/hermes-story-architect/projects/browser-verification-test`. Any
   other project DB found is the same call.
5. Confirm no code reads a `drafts.status` or `is_deleted` value that a fresh DB lacks —
   `create_schema` must create the current shape outright.

## Precondition

**Task 31 must be complete.** Removing the repairs while any pre-rename database still
exists will break reads, and task 31's databases are mid-rename.

## Notes

- Fresh databases are unaffected: `create_schema` already creates the current shape. This
  task only removes the ability to repair old ones.
- No replacement repair. That is the point.
- Once done, `get_db` becomes: open, pragmas, return. No `sqlite_master` probes.

## Checklist

- [ ] Task 31 complete
- [ ] Both `ensure_*` functions deleted
- [ ] `get_db` call sites and docstring paragraph removed
- [ ] `tests/test_legacy_db_migration.py` deleted
- [ ] Every project DB regenerated; live test project done first
- [ ] `grep -rn 'ensure_soft_delete\|ensure_draft_status'` returns nothing
- [ ] `grep -rn 'ALTER TABLE' core/` returns nothing
- [ ] Suite green
- [ ] No replacement repair, shim, or version check added