# Phase 3 — `story_load` contract

**Status:** Blocked until Phase 2 is closed.

**Plan source:** `tasks/task_25/memory_implementation_plan.md`, Phase 3.

**Objective:** Replace the placeholder `memory_outline` with the full bounded DB-backed memory block.

## Scope

- `core/db.py`
- `tools/story_load.py`
- `tools/story_describe.py`
- `skills/hermes-story-architect/SKILL.md`
- load, core, and memory tests

## Implementation

Expose one `memory` block containing:

- `status`;
- serialized `content`;
- `usage` as `x/3000`;
- four `counts`;
- four `categories`, including empty arrays.

`story_load` must not read `.story/memory.md`. It must remain the project-entry point. The skill must tell the agent to call it before story work. Remove wording that describes memory as an outline or index.

## Tests

Verify the new key, all four categories, full entries, no `memory_outline`, operation with a missing file, operation with stale file contents, and unchanged structural load behavior.

## Verification

```bash
pytest tests/test_phase2_db_reads.py tests/test_core.py tests/test_memory.py -q
```

Search load consumers, tests, skill text, and tool descriptions for the old contract. Ensure memory is not duplicated inside the project/entity payload.

## Legacy cleanup

Replace old load tests and docs. Do not keep `memory_outline` as a compatibility alias without approval.

## Maintenance and naming

One memory projection function should be reused by load and later dashboard work. Avoid serializing memory twice with different rules.

## Parallel work

Dashboard can consume the shared DB projection after this contract is verified, but UI implementation must not modify the load contract independently.

## Escalation

Ask the user if a structural consumer requires the old key or a materially different response shape.

## Final checklist

- [x] Phase 2 complete
- [x] DB-backed memory exposed in `story_load`
- [x] Four categories and usage exposed
- [x] File-based read removed
- [x] Skill and descriptions updated
- [x] Old tests/docs replaced
- [x] Stale contract references searched
- [x] Naming and shared-serializer maintenance checked
- [x] Phase closed with no unresolved blocking issue

## Final Brief

- `story_load` now returns the complete bounded DB-backed `memory` block with status, serialized content, usage, counts, and all four categories.
- `get_memory_block()` is the shared serializer used by load and dashboard paths; `.story/memory.md` is not read by load.
- Updated current skill guidance and tool descriptions; old `memory_outline` assertions now verify the replacement contract.
- Verification: full suite `303 passed`.

