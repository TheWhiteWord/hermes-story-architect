# Phase 1 — The `scene_beats` entity

The write contract: what a `scene_beats` record is, how it is written, and
what happens when its scene goes.

Verified against code on `feature/issue-redesign`.

---

## Tasks

- [ ] **T1.1** Add `scene_beats` to `ENTITY_SCHEMAS` (`core/constants.py`).

  Fields, in the order a reader scans them:
  - `scene` — ref: scene, required
  - `driver` — ref: character, optional
  - `scene_objective` — string, optional
  - `turning_point` — string, optional
  - `true_character` — list, optional, sub_fields: `character` (ref: character), `dilemma`, `choice_reveals`
  - `beats` — list, optional, sub_fields per F1.5 (nested):
    - `action` — object, sub_fields: `by` (ref), `surface`, `subtext`
    - `reaction` — object, sub_fields: `by` (ref), `surface`, `subtext`
    - `gap` — string
    - `risk` — string
    - `changes` — list, sub_fields: `entity` (ref), `change`

  The `ref` target for `by` and `changes[].entity` is **not expressible**
  as a single `ref` value — see F1.1. The `by` field allows character,
  location, or world (three types). The `changes[].entity` field allows
  character, relationship, location, or world (four types). A bespoke
  validator (`validate_beat_references`) handles both.

  **Verify:** `story_describe(entity_type="scene_beats")` returns the schema.

- [ ] **T1.2** Give `scene_beats` its standard sections: `Conflict`, `Findings`, `Notes`.

  Add to `standard_sections` in `core/entity.py:490`:
  ```python
  "scene_beats": ["Conflict", "Findings", "Notes"],
  ```

  Also remove `Conflict` and `Beats` from the scene's `standard_sections`
  (line 498) — they move to `scene_beats`:
  ```python
  # Current:
  "scene": ["Content", "Objective", "Conflict", "Beats", "Value Turn", "Dramatic Function", "Production", "Notes"],
  # After:
  "scene": ["Content", "Objective", "Value Turn", "Dramatic Function", "Production", "Notes"],
  ```

  **Verify:** `story_describe(entity_type="scene_beats")["sections"]["standard_sections"]` returns `["Conflict", "Findings", "Notes"]`; `story_describe(entity_type="scene")["sections"]["standard_sections"]` has no `Conflict` or `Beats`.

- [ ] **T1.3** Declare `scene_beats.scene` in `ENTITY_COLUMN_MAP` as a column.

  Add to `ENTITY_COLUMN_MAP` in `core/entity.py:299`:
  ```python
  "scene_beats": {"scene": "parent_id"},
  ```

  This makes the delete cascade reach it — `delete_entity` selects every
  entity whose `parent_id` points at the deleted one (`core/writes.py:702`).
  The frontmatter field is `scene`, the column is `parent_id`, and
  `columns_for_insert` maps between them.

  **Verify:** `delete_entity` on a scene soft-deletes the `scene_beats` row, and `restore` brings it back.

- [ ] **T1.4** Add the hard write rule "the scene exists and has no other `scene_beats`".

  In `create_entity` (`core/writes.py`), add a `scene_beats` branch:
  ```python
  if entity_type == "scene_beats":
      from .entity import check_references, validate_beat_references
      scene_id = merged.get("scene", "")
      if not scene_id:
          raise ValueError("scene_beats requires a scene")
      # The scene must exist
      scene = conn.execute(
          "SELECT id FROM entities WHERE id=? AND type='scene'", (scene_id,)
      ).fetchone()
      if not scene:
          raise ValueError(f"Scene not found: {scene_id}")
      # One scene_beats per scene
      existing = conn.execute(
          "SELECT id FROM entities WHERE type='scene_beats' AND parent_id=?",
          (scene_id,)
      ).fetchone()
      if existing:
          raise ValueError(
              f"Scene '{scene_id}' already has scene_beats: {existing[0]}. "
              f"Edit it instead of creating another."
          )
      check_references(project_path, entity_type, merged)
      validate_beat_references(project_path, merged.get("beats", []),
                               merged.get("true_character", []))
  ```

  **Verify:** a second `scene_beats` for the same scene is refused, and the refusal names the existing one.

- [ ] **T1.5** Add the hard rule "every referenced entity exists".

  `check_references` is called in T1.4 above. It resolves `ref` declarations
  at field level and inside `sub_fields`. The `scene` field has `ref: scene`
  in the schema, so it is checked. The `driver` field has `ref: character`.
  The `true_character[].character` field has `ref: character`.

  The `by` and `changes[].entity` refs are **not expressible** as single
  `ref` values (F1.1) — they are handled by `validate_beat_references` in T1.4.

  **Verify:** a ref to a deleted entity is refused with a `ValueError`.

- [ ] **T1.6** Add the rule "a beat has content".

  A `beats` entry whose `action` and `reaction` both hold no `surface` and
  no `subtext`, and which has no `gap`, no `risk` and no `changes`, is
  refused. Per F1.5 the beat is two-sided, so "no content" means no content
  on **either** side.

  Add to the `scene_beats` branch in `create_entity`:
  ```python
  for i, beat in enumerate(merged.get("beats", [])):
      action = beat.get("action", {})
      reaction = beat.get("reaction", {})
      has_surface = (action.get("surface") or reaction.get("surface"))
      has_subtext = (action.get("subtext") or reaction.get("subtext"))
      has_gap = bool(beat.get("gap"))
      has_risk = bool(beat.get("risk"))
      has_changes = bool(beat.get("changes"))
      if not (has_surface or has_subtext or has_gap or has_risk or has_changes):
          raise ValueError(
              f"Beat {i} has no content: no surface, subtext, gap, risk, or changes."
          )
  ```

  **Verify:** the refusal is a `ValueError` naming the entry index.

- [ ] **T1.7** Wire the export and import.

  **Export** (`tools/story_export.py`):
  - Add `"scene_beats": "scene_beats"` to `_FOLDERS` (line 53).
  - The export filename is the title and the id lives in frontmatter — this
    is already how every flat folder works. No new rule needed.

  **Import** (`tools/story_import.py`):
  - Add one `_import_folder(conn, project_path, "scene_beats", "scene_beats")`
    call after the `scenes` import.
  - Add `"scene_beats"` to the `markdown_ids` walk (line 71).

  **Verify:** an import → export → import round trip is byte-identical for
  a `scene_beats` note.

- [ ] **T1.8** Wire the scene's computed fields.

  In `ENTITY_SCHEMAS["scene"]`, add:
  ```python
  "turning_point": {
      "type": "string", "default": "", "optional": True, "computed": True,
      "description": "The moment of the major gap, read from this scene's scene_beats (read-only)"
  },
  "scene_beats": {
      "type": "object", "default": None, "optional": True, "computed": True,
      "description": "This scene's scene_beats record (read-only)"
  },
  ```

  In `core/db.py`, `_build_scene` must populate these. After the scene
  dict is built, look up the `scene_beats` for this scene:
  ```python
  # In _build_scene, after building the result dict:
  sb = conn.execute(
      "SELECT * FROM entities WHERE type='scene_beats' AND parent_id=?",
      (sid,)
  ).fetchone()
  if sb:
      sb_extra = json.loads(sb["extra"])
      result["turning_point"] = sb_extra.get("turning_point", "")
      result["scene_beats"] = { ... }  # the full record
  ```

  **Verify:** both appear in `story_retrieve` for a scene that has one, and
  neither is writable through `story_draft` (the computed check in
  `core/drafts.py:167` refuses them).

- [ ] **T1.9** Wire the scene's `scene_objective` field and rewrite `effects` description.

  **`scene_objective`:** Add to `ENTITY_SCHEMAS["scene"]`:
  ```python
  "scene_objective": {
      "type": "string", "default": "", "optional": True,
      "description": "The driver's immediate desire. One sentence."
  },
  ```

  **`effects` description:** In `core/constants.py:227`, change:
  ```
  "One entry per protagonist the shift affects"
  ```
  to:
  ```
  "The outcome of the value shift for a plot protagonist, by conflict level"
  ```

  The field's **shape** does not change, only its description.

  **Verify:** `story_describe(entity_type="scene")` reports the new
  `effects` description; `scene_objective` is reported unfilled when empty.

---

## Findings

**F1.1 — the multi-type reference is not expressible in one `ref`.**
`check_references` compares a target against exactly one `type`. The design
allows `by` to be a character, location, or world (three types) and
`changes[].entity` to be a character, relationship, location, or world
(four types). The asymmetry is deliberate: a relationship can be the
**object** of a change but cannot **act**. Resolved by adding
`validate_beat_references(project_path, beats, true_character)` and calling
it with `check_references`. It resolves `by` against three types and
`changes[].entity` against four.

**F1.2 — `check_references` is not called on an edit.** The scene and plot
create paths call it; `edit_entity` calls it only for `plot_roles`
(`core/writes.py:566`). A `scene_beats` edit that sets `scene` to a scene
that exists is fine; one that sets it to nothing is not. Low impact:
the `scene_beats` edit path needs the same call as the create path.
Resolved by calling `check_references` from the `scene_beats` branch of
`edit_entity`.

**F1.3 — the design's "the id and the `scene` link live in frontmatter" is
consistent with a column link.** `columns_for_insert` maps a frontmatter
field to a column and drops it from `extra`. The link is therefore both in
frontmatter (as written) and in `parent_id` (as stored). No conflict.

**F1.4 — §8's soft rule names a `true_character` reference that §5.3 does
not declare.** §8 lists `by`, `driver`, and `true_character` as reference
sites. §5.3's table declares `character` (ref: character) and `dilemma`.
The rule is a list of the two reference sites on `scene_beats` plus the
beat's, written loosely. Resolved by reading it as: "every character a
`scene_beats` record names — in `driver`, in a beat's `by` (either side),
in a `true_character[].character` — is in the scene's cast." That is one
rule over the record's sites, and it is a soft finding, so it is prose.

**F1.5 — §5.2's diagram and its table disagree on the beat shape. Resolved:
nested, per the diagram.** The diagram nests `action` and `reaction`, each
with its own `by`, `surface`, and `subtext`. The table lists them as flat
fields. The diagram is the more specific artifact and is what §5.2's prose
depends on ("the same character on both sides means inner conflict"
requires two `by` fields). The mechanism supports it with no new code:
`_validate_field` recurses into nested `sub_fields`, `_ordered` recurses,
and `_collect_refs` recurses.

**F1.6 — the importer never validates a reference. Resolved: not in scope.**
`_import_folder` calls `_insert_entity` and `_insert_relations` directly;
`check_references` is not called on import at all, for any type. The design
does not ask for it. Recorded so the gap is visible rather than discovered
later.

---

## Parallel work

T1.7 (export/import) is independent of T1.4–T1.6 (validation) and can be
picked up in the same pass.

## Dependencies

Phase 0 must be complete (T0.1 adds `scene_beats` to `ENTITY_LABELS`).
