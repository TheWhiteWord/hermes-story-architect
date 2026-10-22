# VALUE_RANKING — phase task files

Source plan: `../Value Profile Ranking Values by Plot, Act, Sequence and Story.md` (design draft 2).

One file per phase. **Complete them in order** — each depends on the ones before it. Each file: verified against the code, lists its tasks with checkboxes, and ends with a checklist.

| Phase | File | Does | Depends on |
| --- | --- | --- | --- |
| 1 | `phase-1.md` | Fix `compute_value_lines` (plot filter + act order); add `get_scene_value_turns` helper | — |
| 2 | `phase-2.md` | The `value` entity type (constants, validation, write path, retrieve/describe) | 1* |
| 3 | `phase-3.md` | Export/import the single root `values.md` + round-trip | 2 |
| 4 | `phase-4.md` | Move schemas off the plot; turns name value entities; delete `value_schemas`/`value_lines`/inline `schema` | 2, 3 |
| 5 | `phase-5.md` | Computed `value_focus` (major/minor) on plot, sequence, act, project | 4, (1) |
| 6 | `phase-6.md` | `story_load view='values'` (no-arg / scene / unit) | 5 |
| 7 | `phase-7.md` | Fix both value-pass skill docs (`task_30/VALUE_PASS_SKILL_SECTION.md` + `task_30/skill/references/craft/value-pass.md`) for the new model | 6 |
| 8 | `phase-8.md` | One-time migration: fixture + live project → `values.md` | 1-7 |

`*` Phase 2 is technically independent of Phase 1 but sequenced after it.

## Decisions locked while writing these
- **`values.md` is a single file at the project root**, one entry per value (plan §3 literal). It deliberately departs from the one-note-per-entity folder model every other type uses. Phase 2's export/import wiring was deferred to Phase 3 for this.
- **Value id = slug(name)**; the write path keeps the explicit-id create and validates `id == slug(name)` (the plan says "the id is the slug of the name" but no auto-slugging exists in the codebase).
- **No skill-tree authoring in Phase 7** — the skill isn't built; only the existing `task_30` draft is fixed.
- **Baseline test state: 1096 pass / 2 fail.** The 2 failures (`test_plot_roles::test_the_identity_fields_come_before_the_roles`, `test_retrieve_reading::test_fields_come_back_in_schema_order`) are pre-existing schema-ordering issues, unrelated. Decide in Phase 8 whether they are in scope.

## Cross-phase flags
- **Phase 4 leaves the suite red until Phase 8** (the fixture still carries `value_schemas`, which Phase 4 makes import refuse). Land Phase 8's fixture conversion in the same PR as Phase 4, or sequence 4 immediately before 8.
- **Phase 5 and Phase 4 both touch `tools/story_retrieve.py`** (delete `value_lines` branch, add `value_focus` branch). Sequence them; not parallel.
- **Phase 2 ↔ Phase 3 share the `value` entity definition** (3 consumes what 2 builds). Not parallel.

## Project conventions applied throughout
- No backward compatibility; remove obsolete paths and tests (replace, don't shim).
- One-time migration for the live DB + fixture; delete the script after use.
- Dry-run before any destructive `story_import`; back up the live project first.
- Ground truth from the real importer/parser, never hand-written expected output.
