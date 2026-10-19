# Phase 4 — Dashboard

The arc panels and graph are retired. This is the phase with the most surface
and the least data dependency, so it runs after the read model is settled.

Verified against code on `feature/issue-redesign`.

---

## Tasks

- [ ] **T4.1** Remove the arc graph.

  - Delete `src/dashboard/js/graph/arc-graph.js`.
  - Drop it from `JS_ORDER` in `tools/story_dashboard.py:15`.
  - Remove the tab (`tab-arcgraph`) from `src/dashboard/index.html:191`.
  - Remove the panel (`#graph-tab-arcgraph`) from `src/dashboard/index.html:198`.

  **Verify:** `story_dashboard` returns HTML that loads, and no reference
  to `arc-graph` remains in `src/`.

- [ ] **T4.2** Remove the character panel's arc section.

  Remove `DASH.arcSectionHtml` from `src/dashboard/js/panels/panel-manager.js:27`
  and its call site in `src/dashboard/js/panels/entity-panels.js:119`.

  **Verify:** the character panel still renders.

- [ ] **T4.3** Remove the network graph's arc tooltip and the legend's arc
  badge.

  Remove the arc tooltip from `src/dashboard/js/graph/network.js:134-188`,
  which reads `arc_type`, `character_value`, `arc_beats_list`.

  **Verify:** hovering a character shows the role, not the arc type.

- [ ] **T4.4** Remove the statistics arc summary and its container.

  Remove from `src/dashboard/js/statistics/statistics.js:228-244`, rendering
  into `#structStats-arc-summary` (`src/dashboard/index.html:510`).

  **Verify:** the statistics group renders without it.

- [ ] **T4.5** Remove the scene list's beat dots.

  Remove from `src/dashboard/js/views/scenes.js:57-64`, reading
  `scene.arc_beats` — the dead field from T0.2.

  **Verify:** the scene list renders without them.

- [ ] **T4.6** Verify no dashboard JS reads a field the schema no longer has.

  **Verify:** a grep of `src/dashboard/` for `arc_type`, `character_value`,
  `arc_beats_list`, `is_crisis`, `is_climax`, `arc_beats` returns nothing.

---

## Findings

**F4.1 — `src/dashboard/js/graph/arc-graph.js` is the only file a test runs
in node.** `tests/test_arc_graph_story_series.py` runs the real file against
a stub DOM. Retiring the graph retires that test file; it is replaced by
nothing in this plan (the design defers a new visualisation). Recorded so
the deletion is deliberate rather than a gap.

## Dependencies

Phases 1 and 3 must be complete (read model settled).
