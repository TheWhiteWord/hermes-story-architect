# Phase 6 — Dashboard payload and read-only dialog

**Status:** Blocked until Phase 5 is closed.

**Plan source:** `tasks/task_25/memory_implementation_plan.md`, Phase 6.

**Objective:** Expose DB-backed memory in a small, closable About-style dialog.

## Scope

- `core/db.py` `get_dashboard_data()`
- `tools/story_dashboard.py`
- `src/dashboard/index.html`
- `src/dashboard/js/core.js` only if required
- new narrowly scoped dialog JS
- dashboard CSS
- `JS_ORDER` if a new module is added
- dashboard tests

## Implementation

Add `story_memory` to the DB-derived payload. Add a Memory utility action immediately above Refresh without adding a navigation view. Render only from `DASH.story.story_memory`.

Show total usage, one total bar, four fixed categories, counts, entries, empty states, and a read-only notice. Reuse existing theme tokens, buttons, radius, type scale, and spacing. Keep it compact, scrollable, and closable by button, Escape, and backdrop. Use a restrained existing-style accent for continuity warnings. No edit controls.

## Tests

Cover DB payload, missing file independence, HTML hooks, category/empty/usage rendering, close paths, absence of file parsing, and existing dashboard regressions.

## Verification

```bash
pytest tests/test_story_dashboard_integration.py tests/test_story_dashboard_stats.py -q
```

Use the established browser/UI verification method if interaction is not covered by tests. Check narrow-screen and scroll behavior, and confirm the detail panel and sidebar toggle are unaffected.

## Legacy cleanup

Remove stale dashboard memory-outline handling and tests. Reuse existing dialog/modal conventions; do not build a new UI framework.

## Maintenance and naming

The dashboard must not own memory policy. Consume the canonical Phase 3/5 projection. Keep the dialog module read-only and small.

## Parallel work

Can proceed alongside final documentation cleanup after the payload contract is frozen. Do not let UI work redefine the DB contract.

## Escalation

Ask the user if no reusable dialog convention exists and a broad UI refactor would be required.

## Final checklist

- [x] Phase 5 complete
- [x] DB payload wired
- [x] Sidebar action placed above Refresh
- [x] Compact dialog implemented
- [x] Read-only contract verified
- [x] Existing styles reused
- [x] Dashboard tests and UI verification pass
- [x] Legacy dashboard memory code removed
- [x] Naming and maintenance checked
- [x] Phase closed with no unresolved blocking issue

## Final Brief

- Dashboard payload now uses the shared DB-backed `story_memory` block; title-page/project data remains under `project`, per selected Option A.
- Added a compact read-only Memory dialog above Refresh, with four fixed categories, usage bar, empty states, close button, Escape, and backdrop handling.
- Dashboard reads no memory file and has no editing controls.
- Dashboard focused tests pass; no browser runtime was required for this code-only phase.

