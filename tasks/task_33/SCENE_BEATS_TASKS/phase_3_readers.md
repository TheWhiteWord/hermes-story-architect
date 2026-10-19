# Phase 3 — Readers

`story_retrieve`, `story_load` and the load views. Reads only; nothing is
retired in this phase.

Verified against code on `feature/issue-redesign`.

---

## Tasks

- [ ] **T3.1** Verify `story_retrieve` returns a `scene_beats` entity's fields
      and sections, including the nested `beats` and `true_character` lists.

  `story_retrieve` resolves an entity by exact id and returns its fields and
  sections (`tools/story_retrieve.py:73`). `scene_beats` needs no bespoke
  branch — the generic `SELECT * FROM entities WHERE type=? AND id=?` handles
  it. The arc beat's `LIKE` fallback (`tools/story_retrieve.py:80`) is
  arc-specific and goes with Phase 6.

  **Verify:** a test asserting the nested shape survives a round trip.

- [ ] **T3.2** Verify the scene's computed fields are in the load payload and
      read-only.

  **Verify:** `story_retrieve` on a scene returns `turning_point` and
  `scene_beats`; `story_draft` with either in `frontmatter` refuses (the
  computed check in `core/drafts.py:167` refuses them).

- [ ] **T3.3** Verify `story_search` reaches a `scene_beats` note's prose.

  Sections are indexed by the FTS trigger, so this is free.

  **Verify:** a search for a term written into a `scene_beats` `Findings`
  section finds it.

---

## Findings

None.

## Dependencies

Phase 1 must be complete (T1.8 wires the computed fields).
