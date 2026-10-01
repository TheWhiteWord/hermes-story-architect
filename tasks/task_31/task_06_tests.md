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

- [x] Baseline suite run and recorded **before** phase 1
- [x] Decision recorded on the pre-existing migration code in `core/db.py` (scoped out)
- [x] Phase 1 create-path test added and confirmed to fail without the fix
- [x] Create-path coverage audited across all relation fields
- [x] Phase 2 drift test (`PLOT_ROLES` vs `_RELATION_FIELDS`) added
- [x] Phase 2 five-role `has_*` test added
- [x] Phase 3: 9 files updated; `complications` round-trip added
- [x] Phase 4: 6 tests added per `task_04` file
- [x] Tests writing the 5 plot fields now assert read-only refusal, not removed silently
- [x] `test_unfilled_fields.py:115,118` re-verified against reality, not just made green
- [x] Name-only assertions replaced with behavioural ones where found
- [x] Suite green after every phase, not only at the end
- [x] No new test framework, fixture, or helper introduced

## Final brief

**Done.** Most of this phase's debt was already paid by phases 1–4 — this file was
written as a map of what each phase owes, and they each paid their own. What was
genuinely left for phase 6 was one item, and it was the one the phase-1 bug had
been asking for since it was filed.

### The create-path audit — the only new test work

`task_01` deferred this: *"Phase 6 owns the create-path coverage audit across every
relation field."* Done, and it found a real gap.

**Audit result.** Every writable relation field in the schema is `location.variant_of`,
`world.variant_of`, `scene.characters`, `scene.plot_roles`. Coverage before this
phase: the plot roles and `scene.characters` (phase 1/4), and `variant_of` on **both**
types only through `test_round_trip.py` — an **import** round-trip. **The create path
for `variant_of` had no test on either entity type.** It happens to be correct
(verified by execution, not by reading), so this is a hole, not a bug — but it is the
same shape of hole the plot beats had, and that one was a live corruption.

`tests/test_write_shape.py` now carries a parametrised case per field asserting
**the row is written and reads back** — the read-back is the half that matters,
because a row that exists but resolves to nothing is exactly the name-only assertion
this file says to replace.

**The audit guards itself.** `test_every_writable_relation_field_has_a_create_path_case`
compares the hand-written case list against `relation_fields()`, so a relation field
added later without a case **fails and names itself** rather than passing untested.
Verified as a real guard, not a tautology: injected a `sibling_scene` relation field
into `_RELATION_FIELDS`, and the test failed with
`relation fields with no create-path test: [('scene', 'sibling_scene')]`.
`core/` reverted clean afterwards (`git status` shows only `tests/test_write_shape.py`).

One subtlety that cost a cycle: the guard must filter on `computed` via `.get`, not on
schema membership. `writes.py:336` accepts a relation field with **no schema entry**
(`valid = schema | sections | rel_fields`), so a membership filter exempts exactly the
fields create still writes — the guard would pass while exempting its target.

### `test_unfilled_fields.py:115,118` — re-verified, kept

Checked against `unfilled_fields` by execution, not by making the suite green:

| input | result | the test says |
|---|---|---|
| `plot_roles=[{plot, role, description: ""}]` | not a gap | an entry existing = filled ✅ |
| `plot_roles=[]` | gap | ✅ |
| `plot_roles` omitted | gap | (not asserted, but correct) |
| a plot with no roles at all | **no phantom gaps** | the five computed fields no longer report ✅ |

Both assertions still describe reality. Phase 2 changed how the map is built; the
semantics it was testing survived. **Kept as-is, not rewritten.**

### Checklist items already satisfied by earlier phases

Phases 1–4 each landed their own test debt (recorded in their final briefs): phase 1's
create-path regression + the malformed-entry triple, phase 2's drift guard + five-role
`has_*` (`test_plot_roles.py`), phase 3's nine-file rename + `complications` round-trip,
phase 4's 26 tests in `test_scene_plot_roles.py`. Nothing was re-audited here.

### The three failures were ours, not pre-existing — and not code defects

Recorded wrongly in phases 3, 4 and 6 as *"pre-existing, verified by stashing"*.
They were **not**. Verified by bisecting the history: they fail at every commit
that has a `tests/` dir, back to `6a8db71`, long before task 31 existed. Two root
causes, both **test bugs** — the product code was right in every case.

**1. `tests/fixtures/.../story.db` is gitignored** (`.gitignore:6` — `*.db`).
Phase 3 regenerated it from the markdown, which is correct, and that is what exposed
both fixture-dependent bugs below. But it also means `git checkout` never restored
it, so every historical bisect ran against the *regenerated* DB — which is why the
failures appeared to reach further back than they do, and why "verified by stashing"
was never evidence of anything.

**2. `test_an_unset_field_reads_as_not_set_not_as_a_blank` asserted a fixture
accident.** Its docstring said *"the fixture's location has no mood"* — true when
written, false since task 22 gave the location `mood: oppressive stillness`. Fixed
by using **`variant_of`**, which is unset *by design* on a base location and is
already pinned by `test_a_field_that_is_empty_by_design_is_not_a_gap`. A field that
is unset by design does not drift when the fixture is rebuilt.

**3. `test_a_scalar_field_still_renders_before_after` was asserting the wrong
thing.** It is about the *fence* (a one-line value must render as a delta, not a
fenced body) but asserted a `_not set_` before-value — copying its sibling's
premise. Now asserts the `~~oppressive stillness~~ →` delta, which is its actual
subject and is correct for a field that has a value.

**4. `test_every_link_key_story_load_emits_is_a_real_field_name` rejected a name
the schema declares.** `with` is emitted by `story_load` (`db.py:566`, `:1214`) and
is declared — but as a **`sub_fields`** entry of `character.relationships`
(`constants.py:61`), and the test's `known` set collected only *top-level* field
names. The test was calling a correct payload wrong. Now includes declared
`sub_fields`.

**All three verified as real guards**, not weakened into passing:

| reverted | fails |
|---|---|
| `drafts.py` `_not set_` branch removed | the `_not set_` test |
| `drafts.py` scalar wrongly fenced | 3 tests, incl. the fence test |
| `with` removed from `sub_fields` | the vocabulary test |

`core/` and `tools/` reverted clean; the fix is 3 test files, no product change.

**Suite: 998 passed, 0 failed.**

`tests/test_legacy_db_migration.py` untouched, per the recorded decision.

### NOTE — observations, not objectives

1. **The fixture DB being gitignored is the real lesson.** A build artefact that
   tests depend on but git does not track means every "verified by stashing" claim
   about a fixture-dependent test is unverifiable. Either commit it (`!` rule in
   `.gitignore`) or add it in `conftest.py` from the markdown on every run — the
   second removes the whole class. Until then, *any* future fixture edit can break a
   test on a premise, as these three did.
2. **`kind LIKE 'plot_%'` uses `_` as a wildcard** (carried from phase 4) — three
   sites, no reachable defect today, `IN (SELECT …)` would be exact.
3. **`tasks/task_31/rename_plot_roles.py` is still in the tree** after its successful
   run. Phase 5 left the delete call to the owner; not this phase's call.