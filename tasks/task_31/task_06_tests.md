# Phase 6 — Tests

**Phase 6 of 7.** Test changes land **with** phases 1–4, not as a separate sweep — this file
is the map of what each phase owes the suite, plus the work that is genuinely test-only.
See `INTEGRATION.md`.

Running the suite after every phase is non-negotiable. A phase is not done until it is green.

## Verified: baseline

55 test files. The suite must be green **before** phase 1 starts, otherwise a pre-existing
failure will be blamed on the change. Run it first and record the result.

## DECIDED — the plugin's pre-existing migration code stays, scoped out

Your rule for this task is no migration code in the plugin. But `core/db.py` **already
ships two**, unrelated to plot roles:

- `ensure_soft_delete_columns` (`db.py:86-97`) — adds `is_deleted` / `deleted_at`
- `ensure_draft_status_column` (`db.py:68-82`) — adds `drafts.status`

Both are called unconditionally from `get_db` (`db.py:124-126`), and
`tests/test_legacy_db_migration.py` exists specifically to guard them. `get_db`'s own
docstring says it "repairs a database this build did not create".

**Decision: scope the rule to this task's change.** No *new* migration code is added for
plot roles; these two pre-existing repairs are left alone and **not touched**. They do real
work for the live test project, whose `story.db` predates the soft-delete change, so
removing them here would break live verification as well as widening the diff.

Removing them is real debt and is now a **named follow-up**, not an unrecorded exception:
see `tasks/task_32/`.

Phase 5's script remains the only migration this task introduces, and it stays outside the
plugin.

## Test debt this phase owns

### 1. The create-path gap that hid the phase 1 bug

`tests/test_field_coverage.py:446` asserts `plot_crisis` survives — but only through the
**edit** path. The create path was never covered, which is why a data-corruption bug sat in
the code unnoticed. Phase 1 adds the create-path test.

Worth checking the wider shape: does every relation field have a create-path test, or only
the ones someone thought to try? A single audit is cheaper than finding the next one the
same way.

### 2. Tests that will describe removed behaviour

- Any test writing a plot's five role fields directly — after phase 4 they are `computed`,
  so the correct assertion becomes "the draft validator refuses this as read-only".
  **Replace** the test, do not delete it: the refusal is worth asserting.
- `tests/test_unfilled_fields.py:115,118` — `setups` unfilled semantics. Phase 2 changes how
  the unfilled map is built; confirm the assertion still describes reality rather than
  deleting it because it broke.
- `tests/test_phase2_db_reads.py:354` and `test_story_load_views.py:47-76` aggregate the four
  role fields; they become five.

### 3. Per-phase test debt

| phase | tests owed |
|---|---|
| 1 | create-path regression (**fails without the fix**); malformed-entry consistency across all three paths |
| 2 | `PLOT_ROLES` == roles in `_RELATION_FIELDS["plot"]`; five-role `has_*` on both sequence and act |
| 3 | five-role read; `complications` round-trip; 9 files updated |
| 4 | 6 new tests listed in `task_04_scene_side_writing.md` |

## Legacy / obsolete code to clear

- `tests/test_legacy_db_migration.py` — **out of scope, do not touch.** It guards the two
  pre-existing repairs; removing it belongs to `tasks/task_32/`.
- Tests that only assert a field name round-trips are weak: they pass whether or not the
  field means anything. Where one exists, replace it with an assertion about behaviour.
- `tests/test_coherence.py` does not exist; coherence between schema and code is currently
  unenforced except by the drift test phase 2 adds. That test is the substitute — do not
  also add a general coherence harness.

## Notes

- No new test framework, fixtures, or helpers. Extend what exists.
- Phase 2's drift test is the highest-value test in this phase: it is the only thing stopping
  `PLOT_ROLES` and `_RELATION_FIELDS` from drifting apart silently.
- Prefer replacing a weak test over keeping it. The suite is 55 files and several assert
  names rather than behaviour — this task is a good moment to remove that kind.

## Checklist

- [ ] Baseline suite run and recorded **before** phase 1
- [x] Decision recorded on the pre-existing migration code in `core/db.py` (scoped out)
- [ ] Phase 1 create-path test added and confirmed to fail without the fix
- [ ] Create-path coverage audited across all relation fields
- [ ] Phase 2 drift test (`PLOT_ROLES` vs `_RELATION_FIELDS`) added
- [ ] Phase 2 five-role `has_*` test added
- [ ] Phase 3: 9 files updated; `complications` round-trip added
- [ ] Phase 4: 6 tests added per `task_04` file
- [ ] Tests writing the 5 plot fields now assert read-only refusal, not removed silently
- [ ] `test_unfilled_fields.py:115,118` re-verified against reality, not just made green
- [ ] Name-only assertions replaced with behavioural ones where found
- [ ] Suite green after every phase, not only at the end
- [ ] No new test framework, fixture, or helper introduced