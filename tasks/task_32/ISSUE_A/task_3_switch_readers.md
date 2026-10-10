# Task 3: Switch the readers — `core/db.py`, `dramatic_elements` view, dashboard

## Goal

Update all read paths to use the new plot-role system instead of the old
milestone flags and pointers. The readers now derive story-level milestones
from the main plot's roles.

## Work

### 3.1 `core/db.py` — `milestone_label` function

- Replace the current `milestone_label(extra)` function with one that derives
  milestones from the scene's `plot_roles` (passed in or read from relations).
- The new function takes a scene's plot role entries and returns a list of
  milestone labels (a scene can hold multiple: e.g., it can be both the
  inciting incident and a complication).
- Remove the old `SCENE_MILESTONE_FLAGS` constant (no longer needed — the flags
  are gone from the schema).

### 3.2 `core/db.py` — `get_project_summary` (base map)

- The base map currently calls `_milestone_marker` (which is `milestone_label`)
  on each scene's `extra`. Replace this with a call that reads the scene's
  plot roles and derives milestones from them.
- The `milestone` field in the base map output becomes a list of strings
  instead of a single string (since a scene can hold multiple milestones).

### 3.3 `tools/story_load.py` — `_view_dramatic_elements`

- Replace the loop over `SCENE_MILESTONE_FLAGS` with a derivation from the
  scene's `plot_roles` (already loaded as `plot_refs`).
- The `milestone` field becomes a list of strings.
- The `project` section no longer reads `story_climax_scene_id` or
  `inciting_incident_scene_id` from `pro` — instead, it reads the main plot's
  `climax` and `inciting_incidents` roles and reports the scene slugs.
- If there is no main plot, report `unfilled` for story-level milestones.

### 3.4 Dashboard — `src/dashboard/js/views/scenes.js` (lines 42-45)

- Replace the flag-based milestone reading with the new plot-role-based
  milestones. The dashboard receives `__STORY_DATA__` which now carries the
  derived milestones.

### 3.5 Dashboard — `src/dashboard/js/panels/entity-panels.js` (lines 436-439)

- Same replacement as 3.4.

### 3.6 Dashboard — `src/dashboard/js/views/story.js` (lines 49-56)

- Same replacement as 3.4.

### 3.7 `core/db.py` — `get_dashboard_data`

- The dashboard data builder currently reads milestone flags and pointers.
  Replace with plot-role-derived milestones.
- The `has_<role>` flags on sequence/act rows are already derived from
  `PLOT_ROLES` — they automatically include `inciting_incident` after Task 1.

## Checklist

- [ ] `milestone_label` replaced with plot-role-derived version
- [ ] `SCENE_MILESTONE_FLAGS` removed
- [ ] `get_project_summary` uses derived milestones
- [ ] `_view_dramatic_elements` uses derived milestones
- [ ] `project` section reads main plot roles instead of pointers
- [ ] Dashboard `scenes.js` updated
- [ ] Dashboard `entity-panels.js` updated
- [ ] Dashboard `story.js` updated
- [ ] `get_dashboard_data` updated
- [ ] Full suite green
