# Phase 5 — Export projection

**Status:** Blocked until Phase 4 is closed.

**Plan source:** `tasks/task_25/memory_implementation_plan.md`, Phase 5.

**Objective:** Project DB memory into the human-facing `.story/memory.md` file.

## Scope

- `tools/story_export.py`
- memory/export tests
- round-trip tests

## Implementation

Export `project.extra.memory` to frontmatter-only `.story/memory.md`. Emit the four categories in fixed order, preserve entry order, emit no Markdown body, and keep the output deterministic and human-readable. The file remains a projection only.

Do not add timestamps, IDs, migration metadata, or file-read fallback.

## Tests

Cover empty export, populated export, fixed category order, entry order, no body, file edits not affecting DB, and DB changes overwriting the projection.

## Verification

```bash
pytest tests/test_memory.py tests/test_round_trip.py -q
```

Confirm this is the only remaining writer and that no runtime path reads the file.

## Legacy cleanup

Remove placeholder memory-section export code and its tests. Do not preserve the old shape as an alias.

## Maintenance and naming

Reuse the canonical serializer/usage helpers. One export writer, one memory file, one projection contract.

## Parallel work

May run in parallel with the dashboard only if both consume the same canonical DB projection and neither writes the runtime path.

## Escalation

Ask the user if an existing import/export contract requires a different file shape.

## Final checklist

- [x] Phase 4 complete
- [x] Frontmatter-only export implemented
- [x] Category and entry order preserved
- [x] No Markdown body emitted
- [x] Runtime file reads absent
- [x] Placeholder export code/tests removed
- [x] Naming and serializer maintenance checked
- [x] Phase closed with no unresolved blocking issue

## Final Brief

- `story_export` now projects `project.extra.memory` to `.story/memory.md` with fixed category order, preserved entry order, and no body.
- The export projection does not affect DB state; file edits are overwritten from DB on the next export.
- Added `tests/test_memory_export.py`; focused tests pass.

