# Phase 3 — Rename the vocabulary

**Phase 3 of 7.** Starts only after `task_02_role_vocabulary.md` is complete.
See `INTEGRATION.md`. Phase 2 must land first — this phase's diff is only small because of it.

## What changes

| old | new |
|---|---|
| field `payoffs` | field `resolutions` |
| kind `plot_payoff` | kind `plot_resolution` |
| `beat == "payoff"` | `role == "resolution"` |
| `has_payoff` | `has_resolution` |
| — | field `complications`, kind `plot_complication`, `has_complication` |

`PLOT_ROLES` = `setup, complication, crisis, climax, resolution`.
`transition` / `non-event` are never plot roles. No completeness mechanism.

## Verified: every site that must change

**Code — Python (12):**
`constants.py:98` · `db.py:713-714`, `996`, `1112`, `1262`, `1271`, `1301`, `1310` ·
`entity.py:227` · `story_import.py:466`, `505` · `story_export.py:171`

Note `story_import.py:466` is a **skip-set** listing `payoffs` explicitly. Easy to miss; if
it is not renamed, the importer reports `resolutions` as an unknown frontmatter field.

**Code — JS (5):** `entity-panels.js:30`, `275`, `279`, `307-309`, `532` ·
`data-load.js:63` (mock) · `core.js:67` (comment)

**Tests (9):** `test_story_describe.py:61` · `test_phase2_db_reads.py:354` ·
`test_field_coverage.py:62,278,285,372,446` · `test_retrieve_reading.py:79` ·
`test_story_load_views.py:47,57,65,76,178` · `test_unfilled_fields.py:115,118` ·
`test_write_shape.py` · `test_core.py:285,895`

`test_story_load_views.py:65` asserts `roles <= {"setup","crisis","climax","payoff"}` and
`:178` asserts `role == "payoff"` — both need the new value.

## DECIDED — fixture markdown is hand-authored, and it is the test input

`tests/fixtures/save-the-children/plots/The Resistance.md` carries `payoffs:` in its
frontmatter, and `tests/test_unfilled_truncation.py` **re-imports that fixture** to
exercise the importer. So this file is live test input, not documentation.

**Decision: edit the markdown and regenerate the committed `story.db` from it.** The two
are a matched pair — the DB is a build artefact of that markdown — so they change together
or the fixture contradicts itself.

Rejected: deleting the committed DB and importing on demand (a larger cleanup than this
phase should absorb), and leaving the fixture alone (**wrong** — the new importer would
reject `resolutions` as an unknown field and the import test would fail).

Regenerate with the plugin's own `story_import`, not by hand-editing SQLite.

**This makes phase 5 redundant for this fixture.** Regenerating from markdown writes
`plot_resolution` rows directly, so the fixture never contains a `plot_payoff` row for the
script to rewrite. Phase 5's script exists for the **live** project only — its DB has no
markdown regeneration path in this task. `task_05_migration_script.md` is updated to match;
do not run the script against the fixture expecting 1 row.

## DECIDED — delete `index.yaml`

`tests/fixtures/save-the-children/.story/index.yaml` is **referenced by no code**.
Verified: `grep index.yaml` across `core/` and `tools/` returns nothing, and
`story_export.py` neither reads nor writes it. It is a leftover from the old YAML-index
design, still described in `archieved/` docs, and it carries `payoffs:`, `has_payoff:` and
`beat: payoff` at lines 292, 310, 339, 369, 499.

**Decision: delete it in this phase.** It is genuine legacy cleanup — a file that names
fields which will no longer exist, kept alive only by being committed. Deleting removes
five stale occurrences rather than renaming them.

It is tracked in git, so this is a real deletion and shows in the diff. Nothing regenerates
it.

## Scope note — what this phase is NOT

This is **not** the scene-side write path. The five fields stay writable from the plot side
here; phase 4 moves writing to the scene. Keeping them separate means this phase is a
rename plus one added role — reviewable on its own.

## Legacy / obsolete code to clear

- `story_import.py:466` skip-set entry `payoffs` → `resolutions` (plus add `complications`).
- Any literal `"payoff"` left in code, comments or mock data.
- **`tests/fixtures/save-the-children/.story/index.yaml` — delete** (decided above).
- Fixture markdown renamed, then its `story.db` regenerated from it via `story_import`.

## Tests

- **Update** the 9 files listed above. Where an assertion only exists to prove the old name
  round-trips, **replace** it rather than renaming the string — a test asserting
  `plot_resolution` exists is worth more than one asserting `plot_payoff` did.
- **New:** a plot with all five roles set returns five role fields, each populated.
- **New:** `complications` round-trips through create → export → import.
- `test_field_coverage.py:446` asserts `plot_payoff` survives import — update to
  `plot_resolution`.
- Keep `tests/test_phase2_db_reads.py:207` as-is.

## Notes

- Rename the **kind** string and the **field** name together. A partial rename is what makes
  the dashboard go quietly blank rather than fail.
- `db.py:997` already derives the role generically (`kind.replace("plot_","")`), so it needs
  no edit beyond the tuple it filters on — which phase 2 already removed.
- Direction unchanged (`PLAN.md` §3).

## Checklist

- [ ] Decisions taken on fixture markdown + `index.yaml`
- [ ] `constants.py` — `resolutions`, `complications`; `PLOT_ROLES` has 5 entries
- [ ] `entity.py:227` — field/kind map carries all five
- [ ] All 12 Python sites renamed
- [ ] `story_import.py:466` skip-set updated (missed by grep-for-`plot_` searches)
- [ ] JS: `entity-panels.js` (5), `data-load.js`, `core.js` comment
- [ ] 9 test files updated or replaced; obsolete assertions deleted, not just reworded
- [ ] Five-role round-trip test added
- [ ] `complications` round-trip test added
- [ ] Fixture markdown renamed and its DB regenerated via `story_import`
- [ ] `tests/fixtures/save-the-children/.story/index.yaml` deleted
- [ ] `grep -rn payoff` returns nothing outside `archieved/` and `tasks/`
- [ ] Full suite green
- [ ] No alias, shim, or dual-name support