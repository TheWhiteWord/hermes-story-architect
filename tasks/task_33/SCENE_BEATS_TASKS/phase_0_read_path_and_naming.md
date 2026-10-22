# Phase 0 — Read path and naming conventions

Phase 0 of the scene_beats refactor. Establishes the read contract and
naming conventions before any schema exists. No behaviour changes —
removes dead code and records the read contract for later phases.

Verified against code on `feature/issue-redesign` (commit `a9b256e`).

---

## Tasks

- [ ] **T0.1** Add `scene_beats` to `ENTITY_LABELS` in `core/constants.py`.

  Insert `"scene_beats": "Scene Beats"` into the dict at line 53-65.
  This lets `story_describe` (whose enum is `list(ENTITY_SCHEMAS)`) name
  the type. Also required so `story_draft` accepts the type once the
  schema lands in Phase 1.

  **Verify:** `python -c "from core.constants import ENTITY_LABELS; assert 'scene_beats' in ENTITY_LABELS"`

- [ ] **T0.2** Remove the dead `scene.arc_beats` block from `_build_scene` in `core/db.py:1272-1289`.

  The block (lines 1272-1289) builds a `scene_beats` dict from `arcs`
  and attaches it to each scene as `s["arc_beats"]`. Nothing reads this
  value — `_build_scene` has already returned by line 594, and the
  `arc_beats` key on the scene dict is never accessed by any reader.
  Phase 1 replaces this block with the real `scene_beats` computed field.

  Delete lines 1272-1289 (the comment, the `scene_beats = {}` init, the
  two loops, and the `for s in scenes` loop that assigns).

  **Verify:** `git grep arc_beats core/` returns only the
  `ENTITY_SCHEMAS` declaration site and the `arc_beats_list` computed
  field on character (line 99 of constants.py). No remaining reference
  in `core/db.py`.

- [ ] **T0.3** Pin the read contract for a beat reference.

  A ref target that does not exist must be:
  - An **error on write** (Phase 1, T1.5)
  - A **soft finding on read** (Phase 3, prose in Findings section)

  Record this contract so Phase 3 has something to implement.

  **Verify:** Write a test asserting that `check_references` uses
  id-only lookup (`SELECT 1 FROM entities WHERE id=? AND type=?`), so
  the fix in Phase 1 (adding `scene_beats` refs to the write path) is
  not regressed by a later refactor.

  ```python
  # tests/test_scene_beats.py (or appropriate existing file)
  def test_check_references_id_only_lookup(tmp_path):
      """A ref resolves by id+type. Phase 1 adds scene_beats refs to this path."""
      # Setup: create a scene and a scene_beats entity
      # Assert: check_references passes when the ref target exists
      # Assert: check_references raises ValueError when the ref target is deleted
  ```

- [x] **T0.4** Audit naming against the design. **Already complete — no code change needed.**

  The design uses `beats`, `true_character`, `changes`, `gap`, `risk`,
  `surface`, `subtext`, `turning_point`, `driver`, `scene_objective`.
  Confirmed none collides with an existing field name on another type
  in a reader's flat key space. `gap` is already `arc_beat.gap` (removed
  in Phase 6); `character` is already `scene.characters` and is reused
  deliberately on `true_character[].character`.

  Section names: `Conflict` already exists on `world` and `scene` (moved
  to `scene_beats` in Phase 1, stays at two). `Findings` is new and unique.
  `Notes` is on every type and free to reuse.

---

## Findings carried forward

None. This phase changes no behaviour; it removes dead code and fixes naming.

## Dependencies

None — Phase 0 is first.

## Parallel work

None — all tasks are in different files but trivially small.
