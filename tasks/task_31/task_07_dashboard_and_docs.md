# Phase 7 — Dashboard

**Phase 7 of 7.** Starts only after `task_04_scene_side_writing.md` is complete — it verifies
the *output* of that phase. See `INTEGRATION.md`.

## What changes

**Dashboard JS** — role rename plus one added block:
- `entity-panels.js:272-309` — plot panel: `payoffs` → `resolutions`, add `complications`
- `entity-panels.js:30`, `532` — `has_payoff` → `has_resolution`, add `has_complication`
- `entity-panels.js:431` — `scene.plots[].beat` → `.role`, matching what `story_load` already
  emits (`story_load.py:271`). This resolves a live inconsistency between the two readers.
- `data-load.js:62-63` — mock data
- `core.js:67`, `entity-panels.js:253,427` — comments

**Skill docs — OUT OF SCOPE.** The skill files (`story-theory/references/plot.md`,
`story-loader/references/index-format.md`) describe the old model and only 2 of the 5 roles.
They are **not being updated** in this task. They also live only in the installed plugin
(`skills/` is empty and untracked in this repo), so there is no canonical source to edit.

Consequence accepted: after this task the skill docs will describe the pre-change model —
they say the plot names its scenes, and name only `setups`/`crisis`/`climax`/`payoffs`. The
plugin's own schema (`story_describe`) remains the source of truth and is updated by phases
2–4. Whoever owns the skill docs updates them separately.

## Verified: the payload shape does not change, so this phase is smaller than it looks

`get_dashboard_data` (`db.py:939`) serves `story_data`, injected as raw JSON at
`story_dashboard.py:347`. Phases 2–4 change how the data is *built*, not its shape:

- `plot.resolutions` / `plot.complications` appear exactly where `plot.payoffs` did
- `scene.plots[].role` replaces `scene.plots[].beat` — same position, renamed
- `has_*` flags keep their naming shape

So no JS restructuring. **Verify this, do not assume it** — if phase 4 changed a key, this
phase grows.

## Verified: there is a real end-to-end check, and it must be used

`tests/test_dashboard.py:235-263` runs the assembled page through **headless Chrome**
(`--dump-dom`) and asserts story content reaches the DOM. It skips when Chrome is absent.

This is the only check that would catch a JS/backend key mismatch — every other dashboard
test inspects strings (`test_story_dashboard_integration.py` asserts DOM ids and handler
naming, never rendered content). A renamed key that the JS no longer reads produces
perfectly valid HTML and an empty panel.

**Chrome is installed** (`/usr/bin/google-chrome` present), so this class is not skipped in
this environment. If it ever *does* skip, the phase is unverified, not green — check
`shutil.which("google-chrome")` rather than accepting the skip.

## Legacy / obsolete code to clear

- `.beat-row` / `.beat-scene` / `.beat-desc` CSS classes (`views.css:229-248`) — **leave
  them.** `statistics.js:214-216` and the sequence/act panels use them for non-plot rows;
  they are generic row styling, not plot vocabulary. Renaming is churn across files for
  nothing.
- The `beat` key on `scene.plots[]` — renamed to `role`, not aliased.

## Tests

- **Extend** `TestActuallyRenders` in `tests/test_dashboard.py` with a plot-role assertion:
  a scene's plot role reaches the DOM. This is the test that proves phases 2–4 did not
  quietly break the dashboard.
- **Add** a mock-data assertion that all five roles render in the plot panel.
- `test_story_dashboard_integration.py` needs no change — it asserts structure, not content.
  Do not add content assertions there.
- No new test framework; headless Chrome is already wired.

## Notes

- The dashboard is the only surface where a missing key is **silent**. Everything else raises.
  That is why this phase's verification is a render, not a string check.
- `docs/html_ui_dashboard/*.html` are design mockups, not shipped code. They contain the old
  field names. Update only if they are meant to stay accurate; do not let them drive the
  implementation.

## Checklist

- [ ] Phases 1–6 complete
- [ ] Payload shape confirmed unchanged (not assumed) before editing JS
- [ ] `entity-panels.js` — role rename + `complications` block + `has_complication`
- [ ] `scene.plots[].beat` → `.role` in `db.py` and `entity-panels.js`, matching `story_load`
- [ ] `data-load.js` mock updated to five roles
- [ ] Comments updated (`core.js:67`, `entity-panels.js:253,427`)
- [ ] CSS `.beat-*` classes confirmed untouched
- [ ] Headless-Chrome render test **ran** (not skipped) with a plot-role assertion
- [ ] Chrome presence confirmed; a skip is not a pass
- [ ] No compatibility alias for the old key
- [ ] Full suite green