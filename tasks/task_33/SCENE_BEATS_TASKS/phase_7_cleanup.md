# Phase 7 — Cleanup

Names checked against the final state, dead helpers removed, and the fixture
and live project confirmed.

Verified against code on `feature/issue-redesign`.

---

## Tasks

- [ ] **T7.1** Verify every field name in `ENTITY_SCHEMAS` matches the design's
      vocabulary, and that no name is kept only because it existed before.

  The design's names: `beats`, `true_character`, `changes`, `gap`, `risk`,
  `surface`, `subtext`, `turning_point`, `driver`, `scene_objective`.

  **Verify:** a table of design name → schema name, with none unmatched.

- [ ] **T7.2** Verify every section name matches the design's vocabulary, and
      that `scene_beats`'s three sections are exactly `Conflict`, `Findings`,
      `Notes`.

  **Verify:** `git grep -n "Beats" core/` returns nothing.

- [ ] **T7.3** Remove dead helpers.

  Remove: `validate_arc_parents`, `_validate_y`, `get_character_arcs`, and
  any arc-specific comment that no longer describes code.

  **Verify:** `git grep -in arc core/ tools/ src/` returns nothing.

- [ ] **T7.4** Verify the fixture and the live project both load, and that
      the live project's scene count is unchanged.

  **Verify:** a `story_load` on each, comparing scene ids.

- [ ] **T7.5** Verify the suite passes end to end.

  **Verify:** `pytest` with no failures, and a count of tests that is lower
  than 1017 by the number retired in T6.10 and T6.11.

---

## Findings

**F7.1 — the test count will drop.** 1017 tests exist today; T6.10 removes two
files and T6.11 removes arc assertions from 17 more. The count after the plan
is not 1017 and is not 1094 (a figure carried in an older note). Recorded so
the final verification is against a stated expectation rather than a
remembered number.

## Dependencies

Phase 6 must be complete (all legacy code removed).
