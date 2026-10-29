# Phase 1b: Stabilization (finish Phase 1 properly)

> Prerequisite: `00-overview.md` and `phase-1-standalone-app.md`.
> Phase 2 does not start until this passes. No new features here.

## Why this exists

The Phase 1 report shows the suite went from **1184 passed / 25 skipped / 0 failed** to **1063 passed / 29 failed / 29 skipped**. The 29 failures were described as "pre-existing"; they are not, because the baseline had none. About 88 tests also disappeared (1209 before, 1121 now), and 4 more are skipped. The plan required keeping the suite green and adapting tests rather than deleting them. Also missing from the report: acceptance-test results, the stale-items list, and ruff status.

## Rules for this pass

- A test may be **deleted only if the code it tests was deliberately removed** (for example the old `story_dashboard` tool or the Hermes config path). Every deletion must be listed in `NOTES.md` with the reason.
- A test that covers behavior that still exists must be **fixed or rewritten for the new architecture**, never deleted, skipped, or loosened.
- Do not describe failures as "pre-existing" unless you can show them failing on the baseline commit.

## Tasks

### Task 1: Account for every test

**Must**
- On the baseline (`dev`, before the branch) and on the current branch, list all test IDs (`pytest --collect-only -q`) and diff them.
- Write in `NOTES.md` a table of every test that is **missing** or **newly skipped**: test ID, why, and the decision (justified removal / restore / rewrite).
- Count must reconcile: baseline total = current total - added tests + justified removals.

**Checklist**
- [ ] Baseline and current test ID lists diffed
- [ ] Table of missing/newly-skipped tests in `NOTES.md`, each with a decision
- [ ] Every non-justified one restored or rewritten (see Task 2)

### Task 2: Fix the 29 failures

Group them (the report suggests four groups) and resolve each group by intent, not by making the assertion pass:

- **Config tests that expect Hermes config:** root resolution is now the app's config module (flag, env, file, default). Rewrite these against it. If `core/config.py`'s Hermes path (`hermes_constants`, `story_architect.root_path` from Hermes `config.yaml`) is now unused, **delete it properly** along with `load_plugin_config`. A function that returns `{}` to keep old callers working is a stub; remove the callers instead. Keep `resolve_root(kwargs)` only if the tool handlers need it, and make it free of Hermes.
- **Dashboard tab integration tests expecting the old injection:** rewrite them for the API-fed page (data from `/api/projects/{slug}/dashboard`, script order pinned in `index.html`). They should still verify what they verified before: every tab, every expected element/data binding.
- **Tool description / enum sync tests:** find out why they fail. If they fail because tool definitions changed or the `story_dashboard` tool is gone, update the expectation deliberately. If they fail because something was broken, fix the code.
- **Draft dashboard regeneration:** `core/drafts.py` (or its tool) apparently triggered a dashboard refresh after commits. The dashboard is now live-from-DB, so the refresh is obsolete. Remove the refresh code and rewrite the tests to assert the draft behavior that still matters (stage, commit, discard, results).

**Checklist**
- [x] All 29 failures resolved with the intent preserved
- [x] Hermes config path and `load_plugin_config` stub removed from `core`
- [x] No test skipped/xfailed to hide a problem
- [x] Full suite green; final counts and the reconciliation from Task 1 in `NOTES.md`

### Task 3: Run the real acceptance test

Follow "Definition of done" in `phase-1-standalone-app.md` literally, in a **fresh venv** (`pip install .`, not editable), and record the result of each of the 8 points in `NOTES.md` (pass/fail with a line of evidence). Pay particular attention to:
- point 6 (the real project root shows the same counts and content as the old static dashboard),
- package data included in a non-editable install,
- point 7 (`grep -ri hermes` over the package source).

**Checklist**
- [ ] All 8 acceptance points run and recorded
- [ ] Any failure fixed and re-run

### Task 4: Finish the skipped Phase 1 deliverables

- [ ] Ruff configured; lint clean; formatting applied in its own commit
- [ ] Test that fails if the package imports Hermes (if it does not already exist)
- [ ] `README.md` rewritten for the standalone app
- [ ] Plan files placed under `docs/plan/` with checklists ticked
- [ ] Stale-items list (`plan/`, `archieved/`, `docs/`, `vault-conventions.md`, `core/screenplay.py`, anything else) with keep/archive/delete recommendations in `NOTES.md`. Delete nothing without the owner's decision.

### Task 5: Hand-off notes for Phase 2

In `NOTES.md`, answer concisely:
- Exactly how a tool handler gets its root path today (`resolve_root(kwargs)` and where `kwargs["root_path"]` would come from), and the simplest way for an MCP layer to supply it.
- Which of the 10 remaining tool modules still depend on anything dashboard-related, if any.
- What each tool returns on success and on error (JSON string shapes), in a few lines.
- Anything you changed in `core/` beyond imports.

## Done when

Suite green with a reconciled test count, acceptance test recorded as passing, Task 4 items ticked, and Task 5 answered. Then report back with the final numbers and the contents of `NOTES.md`.
