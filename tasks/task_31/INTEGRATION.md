# Task 31 — integration: plot roles, phased breakdown

Plan of record: `PLAN.md`. Proposal: `PLOT-POSITION-PROPOSAL.md`.
Phases run in order. **No phase starts before the previous one is done** — with one
documented exception: phase 5 (the standalone script) may run alongside phase 4, because it
touches only stored rows and phase 4 does not change those.

## Correction to PLAN.md §5 (found while sequencing)

`PLAN.md` says "no production data, no migration". **That is wrong.** Measured:

| database | plot role rows |
|---|---|
| `tests/fixtures/save-the-children/.story/story.db` | `plot_setup` 2, `plot_payoff` 1 |
| `/media/theww/AI/TWW/hermes-story-architect/projects/browser-verification-test/.story/story.db` | `plot_setup` 2, `plot_crisis` 2, `plot_climax` 2, `plot_payoff` 2 (2 plots, 6 scenes) |

So a rename of the stored kinds **does** need touching real rows. Per the task's standing
rule there is **no migration code in the plugin** — the plugin ships clean. What we need is
a **standalone script** run once by hand. Phase 5 — against the **live project only**; the
fixture is regenerated from its markdown in phase 3 and needs no script.

The live project also shows the vocabulary gap in real data: scenes carry
`dramatic_role` of `setup`/`climax`/`resolution`, while the plot side stores
`plot_payoff`. Same beat, two names — which is the rename's whole point.

---

## Sequencing, and why this order

The ordering is driven by one fact: **every reader keys off the relation `kind` string.**
Renaming a kind without updating its readers breaks the dashboard and the exporters in the
same commit that changes the schema. So the write path is made kind-agnostic first, the
vocabulary is renamed second, and the scene-side writer lands third — by which point
nothing reads the old names any more.

| Phase | Task | Gate |
|---|---|---|
| 1 | Fix the create-path corruption; one dict→row function | `PLAN.md` §2 bug. Pure bugfix, independent of everything else. |
| 2 | Kill hardcoded role lists — one `PLOT_ROLES` source | Makes phases 3–5 cheap. Nothing user-visible. |
| 3 | Rename vocabulary: `plot_payoff`→`plot_resolution`, add `plot_complication` | The visible change. Needs phase 2's loop to stay sane. |
| 4 | Scene-side writing | The actual point of the task. Needs phase 1's shared function. All 5 roles exist by now. |
| 5 | Standalone rename script (not plugin code) | After phase 3; **live project only** — phase 3 regenerates the fixture. |
| 6 | Tests: update, replace, delete what is obsolete | Per phase. |
| 7 | Dashboard | Reads phase 3–4's output. Skill docs out of scope. |

**Parallelisable:** phase 5 is independent of phase 4 once phase 3 is done — the single
exception to the sequential rule, flagged in `task_05_migration_script.md`.

---

## Phase 1 — Fix the create-path corruption

**File:** `task_01_fix_dict_to_row.md`

`relations_for_insert` (`entity.py:442`) unwraps `{scene_id, description}` for
`plot_setup`/`plot_payoff` only; every other kind gets `str(dict)` as `to_id`. Plot
**create** therefore writes corrupt rows for `crisis` and `climax`. Edit and import are
correct, so it is invisible in normal use.

Extract one `dict → (to_id, note)` function; route all three write paths through it.

**This phase alone is a bugfix worth landing** — it is a live data-corruption defect and
it does not depend on any decision in `PLAN.md`.

## Phase 2 — Kill hardcoded role lists

**File:** `task_02_role_vocabulary.md`

Six sites restate the role list: `db.py:707-714`, `db.py:996`, `db.py:1109-1112`,
`entity.py:223-228`, `story_import.py:505`, `story_export.py:170-171` — plus the `has_*`
flags at `db.py:1259` and `db.py:1299`. Adding a role means editing all eight.

`_RELATION_FIELDS["plot"]` (`entity.py:223-228`) is the authoritative field↔kind map;
everything else derives from it. Plus `PLOT_ROLES` in `constants.py`, with a **test**
pinning it to that map — the test prevents drift, a comment would not.

No rename, no schema change, no user-visible difference. Pure duplication removal so
phases 3–4 are one-line changes.

**Correction recorded while verifying:** an earlier draft proposed deriving *everything*
from `PLOT_ROLES`. That is wrong — field names are not role names pluralised (`crisis` →
`crisis`, not `crisiss`; `climax` stays singular), so a naive `role + "s"` yields keys that
exist nowhere and reads that silently return empty. The mapping stays explicit; only the
iteration is derived.

## Phase 3 — Rename the vocabulary

**File:** `task_03_rename_vocabulary.md`

- `plot_payoff` → `plot_resolution`; field `payoffs` → `resolutions`
- add `plot_complication`; field `complications`
- `PLOT_ROLES` = the 5 dramatic roles

`transition`/`non-event` are never plot roles. No completeness mechanism.

Decided during verification:
- **Fixture:** edit `plots/The Resistance.md`, then regenerate its committed `story.db`
  from it via `story_import`. They are a matched pair — the DB is a build artefact of that
  markdown. Leaving it alone would leave a fixture the new importer rejects.
- **Delete** `tests/fixtures/save-the-children/.story/index.yaml` — verified dead (no code
  reads or writes it), a leftover of the old YAML-index design. Deleting removes five stale
  occurrences instead of renaming them.

A site a `grep plot_` sweep misses: `story_import.py:466` is a skip-set naming the fields
explicitly. Miss it and the importer calls `resolutions` an unknown field.

Scope: rename + one added role only. Writing stays plot-side here; phase 4 moves it. Keeping
them apart makes this phase reviewable on its own.

## Phase 4 — Scene-side writing

**File:** `task_04_scene_side_writing.md`

The agent records which plot a scene runs through **on the scene**, so a plot is never
reopened when a scene joins it. New scene field `plot_roles: [{plot, role, description}]`;
plot's five role fields become computed. Direction unchanged (`PLAN.md` §3).

Decided during verification:
- **Direction:** keep plot-owns-row. Flipping costs the 8 reader rewrites in `PLAN.md` §3
  for no added capability.
- **Entry shape:** flat, each entry names its own plot — that is what lets one scene hold
  different roles in different plots.
- **Delete:** deleting a plot clears its `plot_*` rows.

Needs bespoke code because `_RELATION_FIELDS` is one-field-to-one-kind and `plot_roles` is
one field to **five** kinds; the generic loop at `writes.py:374-409` cannot express it.

**Correction to an earlier assumption:** `location_scene` is *not* swept on delete — it gets
correct behaviour free because deleting the scene hits the `to_id` sweep. Plot roles are the
opposite case (plot owns the row) and need genuinely new code, or a deleted plot's rows
survive and silently reattach when a plot with the same slug is recreated.

Deleting a plot therefore trades exact `restore` for these rows. Accepted: silent
reattachment is worse than a lost role row. Comment it at the code.

## Phase 5 — Standalone rename script

**File:** `task_05_migration_script.md`

**Not plugin code.** A one-shot script under `tasks/task_31/` that renames
`plot_payoff`→`plot_resolution`. **Live project only** — phase 3 regenerates the fixture from
its edited markdown, so the fixture never needs the script. 2 rows. Run manually; not
shipped, not imported by the plugin, no compat layer.

## Phase 6 — Tests

**File:** `task_06_tests.md`

Test changes land **with** phases 1–4, not as a separate sweep. Phase 6 is the map of what
each phase owes the suite, plus the test-only work.

Baseline: 55 files, must be green **before** phase 1 or a pre-existing failure gets blamed
on the change.

Decided during verification:
- The plugin **already ships two migration functions** — `ensure_soft_delete_columns`
  (`db.py:86-97`) and `ensure_draft_status_column` (`db.py:68-82`), both called from
  `get_db` (`db.py:124-126`) and guarded by `tests/test_legacy_db_migration.py`. Unrelated to
  plot roles, but contrary to this task's no-migration rule.
  **Decision: scope the rule to plot roles.** No new migration code here; those two are left
  untouched. They do real work for the live test project, whose DB predates soft delete.
  Carved out as a named follow-up: `tasks/task_32/remove_plugin_migration_code.md`.

The phase 1 bug hid behind a **test-shaped hole**, not bad luck: `test_field_coverage.py:446`
asserts `plot_crisis` survives, but only via the **edit** path — the create path has no
coverage at all. Phase 6 therefore includes a one-off audit of create-path coverage across
every relation field.

Highest-value test in the phase: phase 2's drift test pinning `PLOT_ROLES` to
`_RELATION_FIELDS["plot"]`. Nothing else stops those two from drifting apart silently.

## Phase 7 — Dashboard

**File:** `task_07_dashboard_and_docs.md`

Dashboard: role rename + `complications` block, `has_complication`, and
`scene.plots[].beat` → `.role` (which also resolves a live inconsistency — `story_load`
already emits `role` while the dashboard reads `beat`).

**Verified: the payload shape does not change**, so no JS restructuring. Verify, don't
assume — if phase 4 changed a key, this phase grows.

**Verification must be a render, not a string check.** `tests/test_dashboard.py:235-263`
runs the assembled page through headless Chrome and asserts content reaches the DOM. It is
the only check that catches a JS/backend key mismatch; every other dashboard test inspects
strings. A renamed key the JS no longer reads yields valid HTML and an empty panel — silent.
Chrome is installed here (`/usr/bin/google-chrome`), so the class is not skipped; if it ever
skips, the phase is unverified, not green.

**Skill docs are out of scope.** `story-theory/references/plot.md` and
`story-loader/references/index-format.md` describe the old model and are **not being
updated**. They live only in the installed plugin (`skills/` is empty and untracked in this
repo), so there is no canonical source to edit anyway. `story_describe` remains the source
of truth for the schema. **Known consequence, accepted:** after this task the skill docs
will describe the pre-change model — the plot naming its scenes, and only 4 of 5 roles.

`docs/html_ui_dashboard/*.html` are design mockups, not shipped code. They hold old field
names; update only if meant to stay accurate, and never let them drive the implementation.

---

## Checklists

- [ ] Phase 1 — dict→row extracted, three paths routed through it, regression test added
- [ ] Phase 2 — `PLOT_ROLES` exists; `has_*` derived in a loop in both `db.py` sites
- [ ] Phase 3 — `plot_resolution`/`plot_complication` live everywhere; `plot_payoff`/`payoffs` gone from code
- [ ] Phase 4 — scene-side write works; plot role fields computed; plot never reopened
- [ ] Phase 5 — script run against the live project (2 rows); no migration code in the plugin
- [ ] Phase 6 — full suite green; obsolete tests removed, not merely skipped
- [ ] Phase 7 — dashboard renders 5 roles, verified by headless-Chrome render
- [ ] No backward-compat shim, alias, or `if old then` anywhere in the diff

## Open, carried forward

- **Skill docs are out of scope by decision.** They will describe the pre-change model after
  this task. Whoever owns them updates them separately.
- **`tasks/task_32/remove_plugin_migration_code.md`** — the plugin's two pre-existing
  migration functions, scoped out of this task by decision. Depends on task 31 finishing.

## Verification summary

Every phase was checked against the code before its task file was written. Nine wrong
assumptions or missed details were found and resolved — four in the plan as first drafted.
The ones that would have shipped silently:

| found in | what it was |
|---|---|
| phase 1 | plot **create** stringifies dicts into `to_id` for 2 of the 4 roles that exist then — live data corruption |
| phase 2 | field names are not role names pluralised (`crisis` → `crisiss`) — reads return empty, no error |
| phase 3 | `story_import.py:466` skip-set — missed by any `grep plot_` sweep |
| phase 3 | fixture markdown and its committed DB are a matched pair; `index.yaml` is dead code |
| phase 4 | the `location_scene` precedent is the **wrong** case — plot rows need a real delete sweep |
| phase 4 | `story_export` drops `plot_roles` entirely — round-trip loses every role, silently |
| phase 5 | running the script before phase 3 lands makes every plot role vanish from the dashboard |
| phase 6 | the plugin already ships two migration functions, contrary to this task's own rule |
| phase 7 | dashboard key mismatches are the one **silent** surface — needs a render, not a string check |
