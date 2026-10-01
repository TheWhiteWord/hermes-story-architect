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

- [x] Phases 1–6 complete
- [x] Payload shape confirmed unchanged (not assumed) before editing JS
- [x] `entity-panels.js` — role rename + `complications` block + `has_complication`
- [x] `scene.plots[].beat` → `.role` in `db.py` and `entity-panels.js`, matching `story_load`
- [x] `data-load.js` mock updated to five roles
- [x] Comments updated (`core.js:67`, `entity-panels.js:253,427`)
- [x] CSS `.beat-*` classes confirmed untouched
- [x] Headless-Chrome render test **ran** (not skipped) with a plot-role assertion
- [x] Chrome presence confirmed; a skip is not a pass
- [x] No compatibility alias for the old key
- [x] Full suite green

---

## Final brief

**Most of this phase was already done by phase 3.** Verified before editing, not
assumed: commit `4f46a12` had already landed the role rename in the act/sequence
badges, the `complications` section, the `has_*` flags, the mock data and both
comments — all of it derived from `DASH.PLOT_ROLES` in `colors.js`, pinned to
Python by `test_plot_roles.py:36`. Two of the three checklist items were therefore
already green before this session started.

**What was actually left, and what it turned out to be:**

1. **`scene.plots[].beat` → `.role`** — the one live inconsistency the task named.
   `core/db.py:1001` emitted `{"id", "beat"}`, `story_load.py:271` emitted `role`,
   and `entity-panels.js:413` read `beat`. Renamed all three. The two `has_*`
   aggregation sites in `db.py` read the same key and were renamed with it — they
   are readers of the producer, so leaving them would have silently blanked every
   role badge.

2. **The sample data never rendered the plot panel at all.** Not on the checklist,
   found by the new render test: `data-load.js` mock plot roles used
   `{heading: ...}` where the backend emits `{scene_id: ...}`, so
   `renderBeats` found no scene and every role section came back empty. Fixed the
   mock to the real shape, gave the scenes slugs and titles, and added the missing
   `crisis` role. Scene slugs are `kitchen-night` etc. rather than `kitchen` —
   the location already owns that id and `DASH.findLocation` matches on it.

3. **The render test needed to drive a click.** `--dump-dom` gives the initial
   view; the scene and plot panels are built on click, so a role label inside one
   is unreachable by a plain dump. Added a `_dom(html, tmp, name, drive_js)`
   helper that injects one `<script>` calling the dashboard's own
   `DASH.showScenePanel(...)` / `DASH.loadSampleData()` before dumping. The page
   is still the shipped bundle; only the entry point is scripted.

**Verification.** Chrome present at `/usr/bin/google-chrome`; the render class ran,
did not skip. Mutation-checked: reverting the JS reader to `pref.beat` fails
`test_a_scenes_plot_role_reaches_the_dom` with the role label absent from the
DOM, and passes again on restore — so the test really does catch the mismatch it
was written for. Full suite **1000 passed** — and clean, so the three failures phase 3
recorded as pre-existing no longer reproduce on this tree.

`.beat-*` CSS left alone as instructed — `statistics.js` and the sequence/act
panels still use them as generic row styling. `docs/html_ui_dashboard/*.html` left
alone: design mockups, not shipped code, and not worth churning for accuracy
nobody renders. No compatibility alias for `beat` anywhere.

### NITE — carried forward

- **Sample data has never been exercised by a test.** The `{heading}` vs
  `{scene_id}` mismatch sat in `data-load.js` through at least two renames because
  the sample path is manual-only. The new five-roles render test now covers the
  plot panel; the rest of the sample (worlds, relationships, perspectives) is
  still unrendered by anything. Cheap to extend, not done here.
- **`core/db.py:386` and `:1098` still say "plot beat"** in comments, and
  `PLOT_BEAT_FIELDS` in `entity.py:256` is still named for the old word. Cosmetic;
  the constant is imported in four places, so the rename is churn with no reader
  benefit. Left deliberately.
- **`docs/research/starc-data-model.md:230`** still names a
  `setups/payoffs` analysis category. Research doc, not code, and the category
  belongs to whatever consumes it — not this task's to change.
- **Skill docs remain stale by decision** (see above). `story_describe` is the
  source of truth. Unchanged from the plan.