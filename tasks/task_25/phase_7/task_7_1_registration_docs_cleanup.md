# Phase 7 — Registration, documentation, and cleanup

**Status:** Blocked until Phase 6 is closed.

**Plan source:** `tasks/task_25/memory_implementation_plan.md`, Phase 7.

**Objective:** Make the new memory surface discoverable and remove obsolete memory wording, paths, and tests.

## Scope

- `__init__.py`
- `tools/story_describe.py`
- `skills/hermes-story-architect/SKILL.md`
- Story Architect references describing `memory_outline`, `update_story_memory`, or placeholder memory sections
- tests asserting the old contract
- `tasks/task_25/DEFERRED_db_first_architecture_audit.md` only for newly discovered deferred items

## Implementation

Register and describe `story_memory`. Add project-entry and memory-use rules to the skill. Remove the old public memory writer if Phase 4 approved removal. Remove stale `memory_outline` and placeholder guidance. Include `story_memory` in post-tool dashboard refresh if the hook is intended to refresh after DB mutations.

## Tests

Verify plugin registration, `story_describe` output, skill rules, absence of stale public descriptions, and the auto-refresh decision.

## Verification

```bash
pytest -q
```

Search the entire repository for:

- `memory_outline`
- `update_story_memory`
- `get_memory_outline`
- `.story/memory.md` reads
- placeholder `Continuity notes`, `World events`, and `Character knowledge`

Every remaining occurrence must be intentional export code, a new-contract test, or a documented deferred issue.

## Legacy cleanup

This is the repository-wide consistency phase. Refactor stale tests where that is cleaner; otherwise replace them. Do not leave lazily named helpers that describe the old outline model.

## Maintenance and naming

Verify all public names, descriptions, skill text, and file names describe the current DB-backed memory contract.

## Parallel work

Can run documentation cleanup in parallel with dashboard verification, but registration must not be finalized while the tool contract is unsettled.

## Escalation

Ask the user if any stale path is a real external contract rather than legacy placeholder code.

## Final checklist

- [x] Phase 6 complete
- [x] Tool registered
- [x] `story_describe` updated
- [x] Skill/reference docs updated
- [x] Legacy writers, readers, and tests removed or justified
- [x] Auto-refresh decision documented
- [x] Full suite passes
- [x] Repository-wide naming audit complete
- [x] Deferred audit note updated if needed
- [x] Phase closed with no unresolved blocking issue

## Final Brief

- Registered and documented `story_memory`; removed the legacy public memory writer and file reader.
- Updated current Story Architect skill guidance with project-entry, explicit-write, bounded-memory, and authority rules.
- Included `story_memory` in dashboard auto-refresh.
- Repository audit found no remaining production `memory_outline`, `update_story_memory`, `get_memory_outline`, or file-based memory read references.
- Verification: `PYTHONPATH=. pytest tests/ -q` → **303 passed**.

## Notes

- The broader DB-first architecture audit remains deferred: `story_dashboard` still reads `project.md` directly for title-page fields. This is outside the memory feature and already recorded in `DEFERRED_db_first_architecture_audit.md`.

