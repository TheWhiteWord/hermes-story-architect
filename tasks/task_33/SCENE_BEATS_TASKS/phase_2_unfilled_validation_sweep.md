# Phase 2 — Unfilled, validation and the sweep

The completeness surface: what is reported as missing, what is refused, and
what export removes.

Verified against code on `feature/issue-redesign`.

---

## Tasks

- [ ] **T2.1** Report the scene's computed `scene_beats` field as unfilled
      when empty, for scenes that are not `planned` and whose
      `dramatic_role` is `plot_role` or empty.

  The precedent is the plot's role fields, reported through
  `story_retrieve._unfilled`, which feeds the derived value in so an absent
  key and an empty one both read as unfilled.

  In `core/db.py`, `_build_scene` already short-circuits a stub to
  `{id, characters}`. The `dramatic_role` clause belongs in the scene
  build, not in the unfilled loop. Add to `_build_scene`:
  ```python
  # After building the result dict, if not a stub:
  if result.get("status") != "planned":
      dramatic_role = result.get("dramatic_role", "")
      if dramatic_role in ("", "plot_role"):
          sb = conn.execute(
              "SELECT id FROM entities WHERE type='scene_beats' AND parent_id=?",
              (sid,)
          ).fetchone()
          if not sb:
              result["scene_beats"] = None  # reported as unfilled
  ```

  **Verify:** a `planned` scene is skipped; a `transition` scene is not
  reported; a `drafted` plot-role scene with no `scene_beats` is reported.

- [ ] **T2.2** Verify the Findings section is the surface for the soft rules
      and that no code path claims to enforce them.

  Soft findings are prose, not code:
  - "A recorded value turn with no turning point"
  - "Scene `effects` that disagree with beat `changes`"
  - "`scene_beats` older than the scene's script" (no timestamp exists —
    unimplementable as written, see B.3)
  - "A character in `by`/`driver`/`true_character` not in the scene's cast"

  **Verify:** `git grep` for `turning_point` and `changes` returns only the
  schema and the reader.

- [ ] **T2.3** Verify the export sweep removes an orphaned `scene_beats` note
      (its scene deleted) and leaves a hand-authored note alone.

  The export sweep is manifest-driven (`tools/story_export.py:95`). It
  removes files the last export wrote and the database no longer has. A
  `scene_beats` note whose scene is deleted is removed by the manifest,
  with no new code.

  **Verify:** a test that deletes the scene in the database, exports, and
  asserts the note is gone.

---

## Findings

None new. F1.1 and F1.2 are carried and resolved in Phase 1.

## Dependencies

Phase 1 must be complete (T1.8 wires the computed field, T1.7 wires export).
