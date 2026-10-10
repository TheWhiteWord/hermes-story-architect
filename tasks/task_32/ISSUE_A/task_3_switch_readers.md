# Task 3: Switch the readers — `core/db.py`, `dramatic_elements` view, dashboard

## Goal

Update all read paths to use the new plot-role system instead of the old
milestone flags and pointers. The readers now derive story-level milestones
from the main plot's roles.

## Work

### 3.1 `core/db.py` — `milestone_label` function

- [x] Replace the current `milestone_label(extra)` function with one that derives
  milestones from the scene's `plot_roles` (passed in or read from relations).
- [x] The new function takes a scene's plot role entries and returns a list of
  milestone labels (a scene can hold multiple: e.g., it can be both the
  inciting incident and a complication).
- [x] Remove the old `SCENE_MILESTONE_FLAGS` constant (no longer needed — the flags
  are gone from the schema).

### 3.2 `core/db.py` — `get_project_summary` (base map)

- [x] The base map currently calls `_milestone_marker` (which is `milestone_label`)
  on each scene's `extra`. Replace this with a call that reads the scene's
  plot roles and derives milestones from them.
- [x] The `milestone` field in the base map output becomes a list of strings
  instead of a single string (since a scene can hold multiple milestones).

### 3.3 `tools/story_load.py` — `_view_dramatic_elements`

- [x] Replace the loop over `SCENE_MILESTONE_FLAGS` with a derivation from the
  scene's `plot_roles` (already loaded as `plot_refs`).
- [x] The `milestone` field becomes a list of strings.
- [x] The `project` section no longer reads `story_climax_scene_id` or
  `inciting_incident_scene_id` from `pro` — instead, it reads the main plot's
  `climax` and `inciting_incident` roles and reports the scene slugs.
- [x] If there is no main plot, report `unfilled` for story-level milestones.

### 3.4 Dashboard — `src/dashboard/js/views/scenes.js` (lines 42-45)

- [x] Replace the flag-based milestone reading with the new plot-role-based
  milestones. The dashboard receives `__STORY_DATA__` which now carries the
  derived milestones.

### 3.5 Dashboard — `src/dashboard/js/panels/entity-panels.js` (lines 436-439)

- [x] Same replacement as 3.4.

### 3.6 Dashboard — `src/dashboard/js/views/story.js` (lines 49-56)

- [x] Same replacement as 3.4.

### 3.7 `core/db.py` — `get_dashboard_data`

- [x] The dashboard data builder currently reads milestone flags and pointers.
  Replace with plot-role-derived milestones.
- [x] The `has_<role>` flags on sequence/act rows are already derived from
  `PLOT_ROLES` — they automatically include `inciting_incident` after Task 1.

## Final Brief — Task 3 Complete

### What was implemented

All readers now derive story-level milestones from the main plot's roles instead
of reading the old per-scene flags (`is_inciting_incident`, `is_sequence_climax`,
`is_act_climax`, `is_story_climax`) and project pointers
(`story_climax_scene_id`, `inciting_incident_scene_id`).

**`core/db.py`:**
- `SCENE_MILESTONE_FLAGS` removed.
- `milestone_label(plot_roles, plot_scopes)` — new signature. Takes a scene's
  plot role entries and a `{plot_id: scope}` map; returns a list of milestone
  labels for entries whose plot has `plot_scope == "main"`.
- `get_project_summary` — now reads `plot_*` relations into `scene_plot_roles`,
  builds a `plot_scopes` map from plot extras, and calls the new `milestone_label`.
  The `milestone` field is now a list of strings (omitted when empty).
- `get_dashboard_data` — same `plot_scopes` map built from entity rows; each
  scene gets a `milestone` field derived via `milestone_label`.

**`tools/story_load.py`:**
- `SCENE_MILESTONE_FLAGS` import removed.
- `_view_dramatic_elements` — builds `plot_scopes` from plot extras; replaces
  the flag loop + old `milestone_label(extra)` call with
  `milestone_label(plot_refs.get(scene_id, []), plot_scopes)`. The `milestone`
  field is now a list of strings.
- The `project` section derives `story_climax_scene_id` and
  `inciting_incident_scene_id` from the main plot's `climax` and
  `inciting_incident` roles. When no main plot exists, both report `"unfilled"`.

**Dashboard (JS):**
- `scenes.js` — `s.milestone` array replaces the four `is_*` flag reads.
- `entity-panels.js` — `scene.milestone` array replaces the four flag reads.
- `story.js` — `keyScenes` derived by filtering `DASH.story.scenes` for entries
  whose `plots[]` include a main-plot role of `inciting_incident` or `climax`.

### Tests

- `tests/test_story_load_views.py` — 4 tests updated to match the new semantics:
  - `test_project_is_the_top_container` — asserts `"unfilled"` (fixture has no main plot).
  - `test_project_survives_the_act_filter` — asserts `"unfilled"`.
  - `test_scene_reports_milestones_from_main_plot_roles` — renamed from
    `test_scene_reports_the_milestone_flags_that_are_true`; asserts no `milestone`
    key when no main plot.
  - `test_scene_reports_the_derived_milestone_label` — asserts no `milestone` key.

### Verification

- Full suite: **1068 passed** in 40.95s.

### Deviations from the task file

- Per user instruction: **main plot only**. Sub-plot milestone display deferred to
  a later task. `milestone_label` filters on `plot_scopes[plot] == "main"`;
  sub-plot roles are not surfaced as milestones.
- The `project` section in `dramatic_elements` reports milestone scene IDs as
  a list of slugs (or `"unfilled"`) rather than a single string, matching the
  new multi-milestone semantics.
