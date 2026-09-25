# Story Memory implementation phases

Source plan: `tasks/task_25/memory_implementation_plan.md`

Each phase is executed only after the previous phase is closed. For every phase:

1. inspect the code against the phase scope;
2. implement the smallest correct change;
3. verify the phase against the spec and current code;
4. resolve low-impact issues directly;
5. ask the user before any medium/high-impact design change;
6. run the phase tests and nearest regressions;
7. audit naming, legacy code, stale callers, and maintenance;
8. mark the phase checklist complete only when no blocking issue remains.

## Phases

- [x] Phase 0 — Baseline audit](phase_0/task_0_1_baseline_audit.md)
- [x] Phase 1 — DB memory model](phase_1/task_1_1_db_memory_model.md)
- [x] Phase 2 — Project data ownership](phase_2/task_2_1_project_data_ownership.md)
- [x] Phase 3 — `story_load` contract](phase_3/task_3_1_story_load_contract.md)
- [x] Phase 4 — `story_memory` tool](phase_4/task_4_1_story_memory_tool.md)
- [x] Phase 5 — Export projection](phase_5/task_5_1_memory_export_projection.md)
- [x] Phase 6 — Dashboard dialog](phase_6/task_6_1_dashboard_memory_dialog.md)
- [x] Phase 7 — Registration and cleanup](phase_7/task_7_1_registration_docs_cleanup.md)
- [x] Phase 8 — End-to-end verification](phase_8/task_8_1_end_to_end_verification.md)

## Cross-phase rules

- DB is authoritative for runtime memory.
- `.story/memory.md` is a human-facing export only.
- `story_memory` is the only v1 memory mutation surface.
- `story_load` exposes the full bounded memory once at project start.
- The dashboard is read-only and DB-derived.
- No new table, migration, entry IDs, timestamps, confidence, status, or automatic lifecycle system unless explicitly approved.
- Do not preserve legacy names, code, or tests merely to avoid cleanup.
- Do not mix the broader deferred DB-first architecture audit into this implementation; record new findings in `DEFERRED_db_first_architecture_audit.md`.
