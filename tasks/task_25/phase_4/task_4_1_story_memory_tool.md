# Phase 4 — Dedicated `story_memory` tool

**Status:** Blocked until Phase 3 is closed.

**Plan source:** `tasks/task_25/memory_implementation_plan.md`, Phase 4.

**Objective:** Add the sole v1 memory mutation surface.

## Scope

- Create `tools/story_memory.py`
- `__init__.py`
- `tools/story_describe.py`
- `skills/hermes-story-architect/SKILL.md`
- new tool tests

## Contract

```text
story_memory(
  action: "add" | "remove" | "replace",
  project: str,
  category: "decisions" | "directions" | "open_questions" | "continuity_warnings",
  entry: str,
  old_entry: str,
  new_entry: str
)
```

`add` appends; `remove` removes the complete matching entry; `replace` replaces the complete matching entry. No IDs, numbering, or substring-only mutation. Duplicate add is a no-op. Enforce the per-entry and total budgets. Return compact success and actionable error responses with usage and affected entries.

No confirmation workflow: the agent policy handles critical operations.

## Legacy cleanup

Remove or disable the old `story_edit(action="update_story_memory")` path if it is obsolete. Do not leave two memory writers.

## Tests

Cover schema, DB persistence, invalid category, empty/overlong/duplicate entries, budget overflow, full-entry remove/replace, no mutation on failure, response shape, and auto-refresh behaviour.

## Verification

```bash
pytest tests/test_memory.py tests/test_story_memory.py tests/test_core.py -q
```

Audit every `update_story_memory` reference and every direct memory file write. Confirm the tool never depends on the export file.

## Maintenance and naming

Use the Phase 1 canonical helpers. Keep the tool a thin semantic boundary over DB operations, not a second policy engine.

## Parallel work

Registration/docs can be prepared with the tool, but the old writer must not be removed until the audit confirms no required consumer exists.

## Escalation

Ask the user before removing an externally used legacy path.

## Final checklist

- [x] Phase 3 complete
- [x] Tool implemented
- [x] Schema registered and described
- [x] Skill guidance updated
- [x] Old writer removed or escalation raised
- [x] Tool tests pass
- [x] Naming and maintenance checked
- [x] Phase closed with no unresolved blocking issue

## Final Brief

- Added `tools/story_memory.py` with add/remove/replace, exact-entry targeting, duplicate no-op, entry/budget validation, compact success/error responses, and DB-only reads/writes.
- Registered the tool, included it in `story_describe`, and added it to dashboard auto-refresh.
- Removed the legacy `story_edit(update_story_memory)` implementation and public schema action.
- Added `tests/test_story_memory.py`; focused tests pass and the full suite is green.

