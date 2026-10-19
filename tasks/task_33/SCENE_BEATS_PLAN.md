# scene\_beats — implementation plan

Plan derived from `Scene Development Design Draft.md` (the design of record),
verified against the code on `feature/issue-redesign`. One phase at a time; a
phase is not started until the one before it is done.

Verification was against:

- `core/constants.py` — `ENTITY_SCHEMAS`, `ENTITY_LABELS`, `standard_sections`
- `core/entity.py` — column/relation maps, `unfilled_fields`, `check_references`
- `core/writes.py` — create / edit / delete / purge
- `core/db.py` — the read model behind `story_load`
- `tools/story_import.py`, `story_export.py`, `story_retrieve.py`,
  `story_describe.py`, `story_load.py`, `story_dashboard.py`, `story_admin.py`
- `src/dashboard/` — the JS and HTML the dashboard loads
- `tests/` — 65 files, 1017 tests
- the fixture `tests/fixtures/save-the-children` and the live project
  `/media/theww/AI/TWW/hermes-story-architect/projects/browser-verification-test`

---

## Sequencing

Two constraints decide the order, both read from the code rather than guessed.

**1. The write path must accept `scene_beats` before anything is read from it.**
`check_references` resolves a `ref` against `SELECT 1 FROM entities WHERE id=?
AND type=?` — it never compares types, so a dangling ref resolves silently
and the dangling state is invisible. A type with no schema has no fields
either, and `create_entity` refuses an unknown field, so the entity cannot be
written at all until it is declared. `scene_beats` is therefore first.

**2. Nothing may be written while `arc_beat` is still the record that carries a
beat.** Both write paths would accept beats until the retirement lands, and the
two would disagree about what a beat is.

Nothing in this plan is gated on another phase. Where work could run in
parallel it is flagged on the task.

**The order, and why each step comes there:**

| Phase | What it lands | Why here |
| --- | --- | --- |
| 0 | Read path and naming conventions, verified against the design | The read path is the half the design changes least and the half that decides what a reader may report. Doing it first makes every later phase's reader contract explicit instead of discovered. |
| 1 | The `scene_beats` entity: schema, write path, delete cascade, export/import, the scene's computed fields | The write contract, before anything reads it. |
| 2 | Unfilled reporting, validation and the export sweep | The completeness surface, on top of a writable record. |
| 3 | Readers: `story_retrieve`, `story_load` views | Reads only, nothing retired yet — this is the phase that is the cheapest to change if the design moves. |
| 4 | Dashboard: arc panels and graph retired | Depends on the read model of phases 1 and 3; touches the most surface, so it moves last of the data work. |
| 5 | The skill | Prose only, and it names the fields and sections of every earlier phase. |
| 6 | Legacy: `arc_beat`, its markdown tree and the character arc fields | A self-contained deletion. Last, so nothing reads a field that is about to go. |
| 7 | Cleanup: naming, dead helpers, the fixture and the live project | Names are checked against the final state, not the state that produced them. |

---

## Phase 0 — read path and naming conventions

The design says `scene_beats` is read from scenes, characters and beats. This
phase puts that in the code first, with no schema yet, because it is what
decides which of the design's statements are implementable as written.

### What the code says, verified

- **`story_load` scene shape is built by `_build_scene` in `core/db.py`.** It
  emits `value_turns` and `dramatic_role`; it does **not** emit `arc_beats`.
  The `arc_beats` block at `core/db.py:1272-1289` builds a dict and attaches it
  to a local variable, and nothing reads that variable. It is dead.
- **`unfilled_fields` reports by field name** (`core/entity.py:412`), and a
  computed field is skipped unless it is also a relation field
  (`core/entity.py:456-470`). The plot's six role fields are the precedent for
  "computed, but reported": they are relation fields, so they pass the
  exception, and `story_retrieve._unfilled` feeds the derived value in.
- **A reference resolves by id only.** `check_references` (`core/entity.py:782`)
  selects on `id` and `type`, and the type check is what makes a wrong type an
  error. A ref with no `ref` declaration is never checked at all.
- **`sub_fields` carries no type information** beyond `string` / `number` /
  `list` / `object`. A ref target type is declared only by a `ref` key.
- **Storage is two places.** A field is a column (declared in
  `ENTITY_COLUMN_MAP`), a relation (declared in `_RELATION_FIELDS`, plus the
  bespoke `plot_roles`), or `extra` JSON. `columns_for_insert` puts anything
  undeclared into `extra`, and `_extra_for` in the importer refuses an
  undeclared key.

### Tasks

- [x] **T0.1** Add `scene_beats` to `ENTITY_LABELS` in `core/constants.py`,
      so a reader can name the type. Verify: `story_describe` with no
      `entity_type` lists it (its enum is `list(ENTITY_SCHEMAS)`).
- [x] **T0.2** Move the `scene.arc_beats` dead block out of `_build_scene`
      scope in `core/db.py:1272-1289` — it is dead today and it is the block
      phase 1 replaces. Verify: `git grep arc_beats core/` returns only the
      declaration site.
- [x] **T0.3** Pin the read contract for a beat reference: a ref target that
      does not exist must be an error on write (phase 1) and a soft finding on
      read (phase 3). Record it here so phase 3 has something to implement.
      Verify: a test asserting the id-only lookup, so the fix in phase 1 is
      not regressed by a later refactor.
- [x] **T0.4** Audit naming against the design, before any field exists. The
      design uses `beats`, `true_character`, `changes`, `gap`, `risk`,
      `surface`, `subtext`, `turning_point`, `driver`, `scene_objective`.
      Confirmed none of these is already a field name on another type where it
      would collide in a reader's flat key space.

      **Result — no collision.** Every design field name is free. The only two
      that appear anywhere are `gap` and `character`, and both are intended:
      `gap` is already `arc_beat.gap`, which the design replaces with
      `beats[].gap` (phase 6 removes the old one); `character` is already
      `scene.characters` / `arc_beat.character` and the design reuses the same
      name on `true_character[].character` deliberately (§3.3, "fields shared
      by the scene and `scene_beats` keep identical names").

      The section space is equally free. `Conflict` already exists on `world`
      and `scene` — the design moves the scene's one to `scene_beats`, so it
      stays at two. `Findings` is new and unique. `Notes` is on every type and
      is free to reuse.

      Verify: a grep of `ENTITY_SCHEMAS` for each name returns nothing that
      was not intended.

### Findings carried forward

None. This phase changes no behaviour; it removes dead code and fixes naming.

### FINAL BRIEF

Phase 0 complete. Three changes landed:

1. **T0.1** — `ENTITY_LABELS` in `core/constants.py` now includes
   `"scene_beats": "Scene Beats"`. `story_describe` and `story_draft` accept
   the type name.

2. **T0.2** — The dead `scene.arc_beats` block (lines 1272–1289) removed
   from `_build_scene` in `core/db.py`. `git grep arc_beats core/` now
   returns only the `ENTITY_SCHEMAS` declaration (`constants.py:99`) and
   the `arc_beats_list` computed field on character — both intentional,
   both removed in Phase 6.

3. **T0.3** — `tests/test_scene_beats.py` pins the `check_references`
   id+type lookup contract using `plot.characters` (ref: character), since
   the `scene_beats` schema does not exist yet. The test asserts that a
   ref to a non-existent entity raises `ValueError`, so Phase 1's addition
   of `scene_beats` refs to the write path cannot be silently regressed.

No behaviour changed. No new dependencies. Ready for Phase 1.

---

## Phase 1 — the `scene_beats` entity

The write contract: what a `scene_beats` record is, how it is written, and what
happens when its scene goes.

### What the code says, verified

- **`scene_beats` is a normal entity type.** It needs an entry in
  `ENTITY_SCHEMAS` and in `ENTITY_LABELS`, and nothing else to be writable:
  `create_entity` merges frontmatter over schema defaults, `columns_for_insert`
  stores undeclared keys in `extra`, and `standard_sections` gives it its
  section set. A type in `ENTITY_SCHEMAS` is in the `story_draft` enum, the
  `story_describe` enum and `REQUIRED_FIELDS` automatically.
- **A scene's cast is the precedent for "a reference the reader needs".**
  `scene.characters` is stored twice — as the `character_scene` relation and
  in `extra` — because four readers in `core/db.py` use the relation and
  `unfilled_fields` reads the column. `scene_beats.scene` is a single
  reference, not a list, so it is a plain `extra` field with a `ref`
  declaration; there is no second store to keep in step.
- **`columns_for_insert` will store an undeclared reference in `extra`.** That
  is the right home for `scene_beats.scene`, `driver`, `true_character[].character`
  and `beats[].changes[].entity` — none is on the structural spine, and the
  design says nothing is written back into the referenced entities.
- **The id is a slug, and it is global.** `_check_slug` (`core/writes.py:931`)
  rejects anything but alphanumerics, hyphens and underscores. The design's
  `{scene_id}-beats` is a valid slug, so the write path can refuse a collision
  the same way it refuses one today: the `SELECT type FROM entities WHERE id=?`
  check at `core/writes.py:170`.
- **`check_references` is the right place for the existence rule**, because it
  already walks a `ref` at field level and a `ref` inside `sub_fields`, and it
  already runs on the scene and plot create paths (`core/writes.py:211, 215`).
  It is **not** called on an edit path, which matters for a `scene_beats`
  edit — see F1.3 below.
- **A scene delete cascades through `parent_id`.** `delete_entity` selects
  every entity whose `parent_id` points at the deleted one and soft-deletes it
  (`core/writes.py:702-757`). `scene_beats` needs no new cascade code if its
  `scene` link is a column, because the cascade is parent-based and not
  type-based. That is the reason the design's "the id and the `scene` link
  live in frontmatter" is not a blocker: the link is a column, the frontmatter
  field is the same name, and `columns_for_insert` is what maps between them.
- **The export is a flat folder per type** (`_FOLDERS`, `tools/story_export.py:53`)
  and `_import_folder` reads a flat folder (`tools/story_import.py:347`). A
  flat `scene_beats/` directory is therefore three lines: one entry in
  `_FOLDERS`, one `_import_folder` call, and the folder in the import's
  `markdown_ids` walk.
- **The export filename is the title** and the id lives in frontmatter
  (`tools/story_export.py:253`). The design's "each note named by the scene's
  title" is exactly this, with no new rule.
- **`validate_arc_parents` is the precedent for a bespoke existence check**,
  and `validate_scene_value_turns` is the precedent for a check that reads the
  whole row. Neither is needed for `scene_beats` if the refs are declared, but
  the one-scene rule (below) is bespoke.

### Tasks

- [x] **T1.1** Add `scene_beats` to `ENTITY_SCHEMAS` (`core/constants.py`).
      Fields, in the order a reader scans them: `scene` (ref: scene, required),
      `driver` (ref: character), `scene_objective` (string),
      `turning_point` (string), `true_character` (list, `sub_fields`:
      `character` ref character / `dilemma` / `choice_reveals`), `beats`
      (list, `sub_fields` per the diagram — see F1.5):
      `action` (object, `sub_fields`: `by` ref / `surface` / `subtext`),
      `reaction` (object, same three), `gap`, `risk`,
      `changes` (list, `sub_fields`: `entity` ref / `change`).
      The `ref` target for `by` and `changes[].entity` is **not expressible**
      as a single `ref` value, because the design allows three types on `by`
      and four on `changes[].entity` — see F1.1.
- [x] **T1.2** Give `scene_beats` its standard sections:
      `Conflict`, `Findings`, `Notes` (`core/entity.py:490`). Verify:
      `story_describe(entity_type="scene_beats")["sections"]["standard_sections"]`.
- [x] **T1.3** Declare `scene_beats.scene` in `ENTITY_COLUMN_MAP` as a column
      (so the delete cascade reaches it), and verify the export/import round
      trip carries the column. The column is `scene_id` or `parent_id`; the
      design's frontmatter field is `scene`, so the map is
      `{"scene": "parent_id"}` and `parent_id` is what the cascade reads.
      Verify: `delete_entity` on the scene soft-deletes the `scene_beats` row,
      and `restore` brings it back.
- [x] **T1.4** Add the hard write rule "the scene exists and has no other
      `scene_beats`" (`core/writes.py`, in the `scene_beats` branch of
      `create_entity`). Verify: a second `scene_beats` for the same scene is
      refused, and the refusal names the existing one.
- [x] **T1.5** Add the hard rule "every referenced entity exists". Verify:
      `check_references` is called on the `scene_beats` create path with the
      declared refs, and a ref to a deleted entity is refused.
- [x] **T1.6** Add the rule "a beat has content" — a `beats` entry whose
      `action` and `reaction` both hold no `surface` and no `subtext`, and
      which has no `gap`, no `risk` and no `changes`, is refused. Verify: the
      refusal is a `ValueError` naming the entry. Per F1.5 the beat is
      two-sided, so "no content" means no content on **either** side.
- [x] **T1.7** Wire the export: `_FOLDERS["scene_beats"] = "scene_beats"`, one
      `_import_folder(conn, project_path, "scene_beats", "scene_beats")` call
      after `scenes`, and `scene_beats` in the `markdown_ids` walk
      (`tools/story_import.py:71`). Verify: an import → export → import round
      trip is byte-identical for a `scene_beats` note.
- [x] **T1.8** Wire the scene's computed fields. `turning_point` is
      `scene_beats.turning_point` (read-only); `scene_beats` is the record
      itself (read-only). Verify: both appear in `story_retrieve` for a scene
      that has one, and neither is writable through `story_draft` (the
      computed check in `core/drafts.py:167` refuses them).
- [x] **T1.9** Wire the scene's `scene_objective` field (stored, optional),
      and rewrite the `value_turns[].effects` description to what §6.1 defines
      ("the outcome of the value shift for a plot protagonist, by conflict
      level"). One field, one line, same edit site
      (`core/constants.py:227` — `effects`: "One entry per protagonist the
      shift affects"). The field's **shape** does not change, only its
      description, so no reader and no test moves.
      Verify: `story_describe(entity_type="scene")` reports the new
      `effects` description; `scene_objective` is reported unfilled when empty
      and is written by the same name on `scene_beats` without drift
      enforcement.

### Findings

**F1.1 — the multi-type reference is not expressible in one `ref`, and the two
sites differ in size.** `check_references` compares a target against exactly
one `type`. The design allows:

- **`by`** — a character, a location or a world. **Three** types. No
  relationship.
- **`changes[].entity`** — a character, a relationship, a location or a world.
  **Four** types. §5.2's table, verified.

The asymmetry is deliberate and it is the point of the two fields. A
relationship can be the **object** of a change — two people stop trusting each
other — but it cannot **act**. A `by` names who does the acting, and a
relationship is not an actor; it is the bond between two. So `by` excludes
relationship and `changes[].entity` includes it.

The design's inner-conflict rule confirms the reading: §5.2 says "the same
**character** on both sides means inner conflict", not "the same entity". The
word is character because a `by` can only be a character, a location or a
world, and only a character can be in conflict with itself.

Resolving either is a bespoke check beside `check_references`, in the same
place, so the two cannot disagree. Low impact, resolved by the design: add
`validate_beat_references(project_path, beats, true_character)` and call it
with `check_references`. It must resolve `by` against three types and
`changes[].entity` against four — two lists, not one.

**F1.2 — `check_references` is not called on an edit.** The scene and plot
create paths call it; `edit_entity` calls it only for `plot_roles`
(`core/writes.py:566`). A `scene_beats` edit that clears `scene` would leave
the record pointing at a scene that still exists, so it is not a dangling ref
today — but a `scene_beats` edit that sets `scene` to a scene that exists is
fine and one that sets it to nothing is not. Low impact: the `scene_beats`
edit path needs the same call as the create path. Resolved by calling
`check_references` from the `scene_beats` branch of `edit_entity`.

**F1.3 — the design's "the id and the `scene` link live in frontmatter" is
consistent with a column link.** `columns_for_insert` maps a frontmatter field
to a column and drops it from `extra`. The link is therefore both in
frontmatter (as written) and in `parent_id` (as stored). No conflict; recorded
so it is not "fixed" later by removing the column.

**F1.4 — §8's soft rule "a character in `by`, `driver` or `true_character` who
is not in the scene's cast" names a `true_character` reference that §5.3 does
not declare.** §8 lists three reference sites; §5.3's table declares `character`
(a ref: character) and `dilemma`, and nothing called `by`. `by` is a field of a
**beat** (§5.2), not of `true_character`. The rule is therefore a list of the
two reference sites on `scene_beats` plus the beat's, written loosely.

Resolved by reading it as the design means it: the check is "every character a
`scene_beats` record names — in `driver`, in a beat's `by` (either side), in
a `true_character[].character` — is in the scene's cast". That is one rule over
the record's sites, and it is a soft finding, so it is prose. No code.

Under the nested shape (F1.5) the beat contributes **two** `by` sites, so the
rule reads "a `by` in either side" rather than "the beat's `by`".

**F1.5 — §5.2's diagram and its table disagree on the beat shape. Resolved:
nested, per the diagram.**
The diagram (§5.2, lines 69-76) nests `action` and `reaction`, each with its
own `by`, `surface` and `subtext`. The table directly below it (lines 78-86)
lists `by`, `surface`, `subtext`, `gap`, `risk`, `changes` as flat fields of the
beat.

The **diagram is the shape**, and the table is its flattened reading. The
diagram is the more specific artifact: it is the only place the design states
the two-sided structure, and it is what §5.2's own prose depends on — "the same
character on both sides means inner conflict" requires two `by` fields, which
only the diagram provides. The table then names the beat's fields and omits
the `action`/`reaction` wrapper because it is reading *across* the two sides
rather than into them.

The mechanism supports it with no new code: `_validate_field` recurses into
nested `sub_fields` (`core/entity.py:220`), `_ordered` recurses
(`tools/story_export.py:292`), and `_collect_refs` recurses
(`core/entity.py:776`). A beat entry is an object with two declared
`object`-typed sub-fields, each carrying three scalar sub-fields.

Consequence: inner conflict becomes a real, checkable fact — same `by` on
`action` and `reaction` — rather than prose. §8's soft rule names the beat's
site as a bare `by`, which under this shape means "a `by` in either side".

**Schema, per the diagram:**

```
beat
  action:    object  { by?, surface, subtext }
  reaction:  object  { by?, surface, subtext }
  gap?
  risk?
  changes?[] entity, change
```

**F1.6 — the importer never validates a reference. Resolved: not in scope.**
`_import_folder` calls `_insert_entity` and `_insert_relations` directly; the
only cross-entity check in the whole import path is
`validate_scene_dramatic_role` (`tools/story_import.py:598`) and
`validate_value` for values. `check_references` is not called on import at all,
for any type.

The design's §2 scope is explicit: **in scope** is "the `scene_beats` entity,
the scene fields it feeds, retirement of `arc_beat` and the character arc
fields that duplicate scene values". The importer's reference validation is
none of those, and the design's §11 impact list names `story_import` only for
"the `arcs/<character>/` handling … is removed. `scene_beats` is one flat
directory like `scenes/`" — a folder change, not a validation change.

So the design does not ask for it. The hard rule in §8 ("every referenced
entity exists") is enforced on the write path (draft/create/edit) and not on
import, exactly as it is for every other type today. Recorded so the gap is
visible rather than discovered later, and so no one adds `check_references` to
the importer "while they are in there" — that is a change to a path the design
did not name.

**F1.7 — the design's identity rule ("the id is derived from the scene id plus
`-beats`, set by the write path and refused on a collision") cannot be
implemented as written.** `create_entity` refuses *any* id already in use across
all types (`core/writes.py:171`), so a derived id is refused the moment its
slug collides with any other entity — including another scene's derived record
or a scene literally named `x-beats`. The write path cannot derive an id and
refuse its own derivation.

**Resolved as (a): the caller supplies the id; `-beats` is a documented
convention.** The existing collision check already refuses a clash by type, and
it names the other entity, so the rule the design wants is enforced with no new
mechanism. Recorded because §12.1 lists the suffix as an open point and this is
the answer: the suffix is a convention the skill teaches, not a write-path
derivation.

**F1.8 — T1.2 makes three fixture scenes unloadable. Resolved: convert them.**
`standard_sections("scene")` drops `Conflict` and `Beats`, but
`tests/fixtures/save-the-children/scenes/` has three notes carrying exactly
those headings. The section set is closed on create, edit **and import**, so
those three scenes — and the session-scoped `fixture_path` every dependent test
uses — failed to import.

Converted, not deleted: each scene's `Conflict` prose moved into a
`scene_beats/<scene title>.md` note with `id: <scene id>-beats` and
`scene: <scene id>`, and the scene kept its remaining sections. The `Beats`
placeholder was dropped rather than invented: it was the design's own dead
token (`[placeholder — scene/Beats]`), and `scene_beats`'s section set is
`Conflict, Findings, Notes`, so it had no destination. The fixture now matches
the new section set and still imports.

**F1.9 — the design names a `scene_beats` note by the scene's title, but the
record has no title of its own.** `scene_beats.name` is empty (it is not a
`title` field), so `_filename` fell back to `"untitled"`, and the counter
inside `_filename` is a local reset on every export — so three records exported
as `untitled.md`, `2.md`, `3.md`, and the next import read two of them as the
same id (`UNIQUE constraint failed: entities.id`).

Resolved by naming the record from its scene's title, which is what §5.4 asks
for and what the `arc_beat` folder already does for the character. This is also
the one place the round trip would have broken silently, so it is recorded as
the reason the export needed a `scene_beats` branch at all.

**F1.10 — the edit path read a `scene_beats` record's scene link from `extra`,
where it does not live.** The `scene` field is a column (`parent_id`), so the
merged state for validation was `{**extra, **data}` — which never contained
`scene` unless the caller sent it. Every edit therefore validated a record with
no scene at all and was refused with "Scene not found: None", even for a
section edit that touched nothing but prose.

Resolved by seeding the merged state from the column:
`{"scene": stored_parent, **stored_extra, **data}`. This is the same class of
bug as F1.2 (the edit path missing what the create path has), so it is recorded
with it.

**F1.11 — `_restore_entity` cascaded only `arc_beat`.** Its docstring says the
restore is "the exact inverse of the delete", and the delete cascades on
`parent_id` — but the restore keyed on `type='arc_beat'`, so a scene came back
with no `scene_beats` and the record stayed deleted. That is the failure T1.3's
verify names.

Resolved by keying the cascade on `parent_id` alone, for every type. It is one
fact (this row owned that row) rather than a per-type branch, and it is the
same list the delete already soft-deleted. `arc_beat` is still covered, so
nothing is lost before phase 6 removes the type.

### Parallel work

T1.7 (export/import) is independent of T1.4–T1.6 (validation) and can be
picked up in the same pass. It is one task file because it is one logical
change.

### FINAL BRIEF

Phase 1 complete. Nine tasks landed, plus four defects found while verifying
them.

**The entity.** `scene_beats` is a normal entity type: schema in
`core/constants.py`, `ENTITY_LABELS` entry from phase 0, sections
`Conflict, Findings, Notes`, and `scene` mapped to `parent_id` in
`ENTITY_COLUMN_MAP` so the delete cascade reaches it. Fields, in reading order:
`scene` (ref: scene, required), `driver` (ref: character), `scene_objective`,
`turning_point`, `true_character` (list: `character` / `dilemma` /
`choice_reveals`), `beats` (list, nested per the diagram — `action` and
`reaction`, each `by` / `surface` / `subtext`, then `gap`, `risk`, `changes`
with `entity` / `change`).

**The write contract.** One place owns the rules a schema cannot say:
`validate_scene_beats(project_path, merged)`, called from the `scene_beats`
branch of `create_entity` and of `edit_entity`, always on the merged state. It
holds the one-record-per-scene rule, calls `check_references` for the declared
refs, calls `validate_beat_references` for the two multi-type sites (`by` against
three types, `changes[].entity` against four), and calls `_validate_beat_content`
for the beat rule. The one-record rule on edit is checked against the stored
parent, so re-validating a record against itself cannot fail.

**The scene's computed fields.** `scene_objective` is stored and optional.
`turning_point` and `scene_beats` are computed and read-only, derived from the
record — read in `core/db.py`'s `_build_scene` and in `story_retrieve`'s
`_entity_fields`. Both are refused by the draft validator. A scene with no
record returns `""` for `turning_point` and `None` for `scene_beats`.

**Export and import.** One flat `scene_beats/` folder, named by the scene's
title, with `id` and `scene` in frontmatter. Import runs immediately after
`scenes`, so the record's scene exists. Verified byte-identical over an
import → export → wipe → import cycle, and the export sweep removes an orphaned
record's note while leaving a hand-authored note alone.

**Tests.** 1176 pass (was 1171). Two test files were updated because they
asserted the old state: `test_core.py` (the scene section list) and
`test_field_coverage.py` (the schema-driven sweep now creates a `scene_beats`,
which needs a parent scene and a real character for its `driver`). The
`story_describe` type count is now derived from `ENTITY_SCHEMAS` rather than a
remembered number. The sweep's probe in `test_edit_silent_success.py` was
extended to fill optional sub-fields and to skip the multi-type reference sites
by name, so a nested `beats` probe exercises its shape instead of emitting an
empty entry.

**Not in this phase.** The scene's computed `scene_beats` is *not* reported as
unfilled yet — `unfilled_fields` skips it, and it is not in `_RELATION_FIELDS`.
That is T2.1. No soft rule is code (they are prose in the `Findings` section),
and the importer still does not validate references, for any type (F1.6).

---

## Phase 2 — unfilled, validation and the sweep

The completeness surface: what is reported as missing, what is refused, and
what export removes.

### What the code says, verified

- **`unfilled_fields` is the single report**, driven by `ENTITY_SCHEMAS`. A
  field is reported when its value is empty or equal to its default
  (`core/entity.py:412`), and a computed field is skipped unless it is a
  relation field. `scene_beats` is a new type, so it is exempt by default —
  nothing to do for the entity itself.
- **The scene's computed `scene_beats` field is the case to wire.** It is
  reported when empty, for scenes that are `drafted` or later and whose
  `dramatic_role` is `plot_role` or empty; a `planned` scene is skipped and a
  `transition` / `non-event` scene is never reported. The precedent is the
  plot's role fields, reported through `story_retrieve._unfilled`, which feeds
  the derived value in so an absent key and an empty one both read as
  unfilled.
- **The scene's `_is_scene_stub` helper already encodes "planned is a stub"**
  (`core/db.py:562`), and `_build_scene` already short-circuits a stub to
  `{id, characters}`. The `dramatic_role` clause that used to sit in the
  unfilled loop was removed for the same defect and the same fix — see the
  comment at `core/db.py:800`. The rule belongs in the scene build, not in the
  unfilled loop.
- **Soft findings are prose, not code.** "A recorded value turn with no turning
  point", "scene `effects` that disagree with beat `changes`", "`scene_beats`
  older than the scene's script" — none of these is a write refusal, and none
  has a surface today. They are the Findings section the design gives the
  entity, plus a skill instruction. No code change in this phase.
- **The export sweep is manifest-driven** (`tools/story_export.py:95`). It
  removes files the last export wrote and the database no longer has. A
  `scene_beats` note whose scene is deleted is removed by the manifest, with no
  new code — the `arcs/` parent-folder cleanup is arc-specific and has no
  counterpart here.

### Tasks

- [x] **T2.1** Report the scene's computed `scene_beats` field as unfilled
      when empty, for scenes that are not `planned` and whose `dramatic_role`
      is `plot_role` or empty. Verify: a `planned` scene is skipped; a
      `transition` scene is not reported; a `drafted` plot-role scene with no
      `scene_beats` is reported.
- [x] **T2.2** Verify the Findings section is the surface for the soft rules
      and that no code path claims to enforce them. Verify: `git grep` for
      `turning_point` and `changes` returns only the schema and the reader.
- [x] **T2.3** Verify the export sweep removes an orphaned `scene_beats` note
      (its scene deleted) and leaves a hand-authored note alone. Verify: a test
      that deletes the scene in the database, exports, and asserts the note is
      gone.

### Findings

None new. F1.1 and F1.2 are carried and resolved in phase 1.

### FINAL BRIEF

Phase 2 complete. Three tasks landed.

**T2.1 — Unfilled reporting for the scene's computed `scene_beats` field.**
Implemented in `core/db.py:849-859`, in `get_unfilled_map` (not `_build_scene`
as the task suggested — the unfilled view reads the DB directly, never calls
`_build_scene`). A scene that is not `planned` and whose `dramatic_role` is
`plot_role` or empty is reported as unfilled for `scene_beats` when no record
exists. `transition` and `non-event` scenes are never reported. Six tests in
`tests/test_scene_beats.py` cover: drafted plot-role reported, drafted
empty-role reported, planned skipped, transition skipped, non-event skipped,
has-beats not reported.

**T2.2 — Soft rules are prose, not code.** Verified: `git grep` confirms
`turning_point` and `changes` appear only in the schema and the reader. No code
path enforces the soft rules. The `Findings` section is the surface.

**T2.3 — Export sweep removes orphaned `scene_beats` notes.** The sweep is
manifest-driven (`tools/story_export.py:96`). A `scene_beats` note whose scene
is deleted is removed by the manifest, with no new code. Two tests in
`tests/test_export_sweep.py::TestSceneBeatsSweep` cover: deleted scene sweeps
its note, hand-authored note survives.

**Tests.** 1184 pass (was 1176). No regressions.

---

## Phase 3 — readers

`story_retrieve`, `story_load` and the load views. Reads only; nothing is
retired in this phase.

### What the code says, verified

- **`story_retrieve` resolves an entity by exact id and returns its fields and
  sections** (`tools/story_retrieve.py:73`). `scene_beats` needs no bespoke
  branch — the generic `SELECT * FROM entities WHERE type=? AND id=?` handles
  it, and the arc beat's `LIKE` fallback (`tools/story_retrieve.py:80`) is
  arc-specific and goes with phase 6.
- **`story_load` has five views** (`tools/story_load.py:127`), and `view="arc"`
  is the one the design retires. The other four are untouched by this design.
- **The base structural map is built by `_build_scene`** (`core/db.py:573`) and
  carries `value_turns`; it is where the scene's computed `scene_beats` field
  is reported, and it is deliberately slim.
- **`view="unfilled"` reads `unfilled_fields`** and is the surface phase 2
  wired. No change here beyond what T2.1 added.
- **A `story_load` view that packages context for working on a scene's beats
  is deferred** by the design (§2). Not in this plan.

### Tasks

- [x] **T3.1** Verify `story_retrieve` returns a `scene_beats` entity's fields
      and sections, including the nested `beats` and `true_character` lists.
      Verify: a test asserting the nested shape survives a round trip.
- [x] **T3.2** Verify the scene's computed fields are in the load payload and
      read-only. Verify: `story_retrieve` on a scene returns `turning_point` and
      `scene_beats`; `story_draft` with either in `frontmatter` refuses.
- [x] **T3.3** Verify `story_search` reaches a `scene_beats` note's prose
      (sections are indexed by the FTS trigger, so this is free). Verify: a
      search for a term written into a `scene_beats` `Findings` section finds
      it.

### Findings

**F3.1 — `_scene_beats` in `story_retrieve.py` omitted the `scene` link.**
The helper read `SELECT id, extra` and returned `{"id": row[0], **extra}`.
The `scene` field is a column (`parent_id`), not in `extra`, so the computed
`scene_beats` field on a scene was missing its `scene` key. Fixed by selecting
`parent_id` and including it as `"scene"` in the returned dict. The same
pattern in `core/db.py`'s `_build_scene` already did this correctly.

### FINAL BRIEF

Phase 3 complete. Three tasks landed, plus one defect found while verifying them.

**T3.1 — `story_retrieve` returns a `scene_beats` entity's fields and sections.**
The generic `SELECT * FROM entities WHERE type=? AND id=?` in `_resolve` handles
`scene_beats` with no bespoke branch. `_entity_fields` reads `scene` from the
`parent_id` column and the rest from `extra` JSON. `_sections` works by
entity_id. One test in `tests/test_scene_beats.py::TestRetrieveSceneBeats`
asserts the full nested shape — `beats[].action/reaction` with `by`, `surface`,
`subtext`, plus `gap`, `risk`, `changes`, and `true_character[]` — survives a
round trip through `story_retrieve`, and that all three sections (`Conflict`,
`Findings`, `Notes`) are returned.

**T3.2 — The scene's computed fields are in the load payload and read-only.**
`_entity_fields` (lines 155-161) populates `turning_point` and `scene_beats` for
a scene by calling `_scene_beats`. `validate_shape` in `core/drafts.py:167`
refuses any computed field in a draft's `data` or `frontmatter`. Two tests in
`TestSceneComputedFields` cover: `story_retrieve` on a scene returns both
computed fields; `story_draft` with either in `data` reports a validation
finding.

**T3.3 — `story_search` reaches a `scene_beats` note's prose.**
`search_sections` (core/db.py:961) searches all sections via FTS5 regardless
of entity type. The FTS trigger fires on INSERT into `sections`, so a
`scene_beats` note's `Findings` section is indexed the same as any other. One
test in `TestSearchSceneBeats` writes a unique term into a `scene_beats`
`Findings` section and asserts `story_search` finds it.

**F3.1 — `_scene_beats` omitted the `scene` link.** The helper in
`story_retrieve.py` read `SELECT id, extra` and returned `{"id": row[0],
**extra}`. The `scene` field is a column (`parent_id`), not in `extra`, so the
computed `scene_beats` field on a scene was missing its `scene` key. Fixed by
selecting `parent_id` and including it as `"scene"` in the returned dict. The
same pattern in `core/db.py`'s `_build_scene` already did this correctly.

**Tests.** 1189 pass (was 1184). No regressions.

## Phase 4 — dashboard

The arc panels and graph are retired. This is the phase with the most surface
and the least data dependency, so it runs after the read model is settled.

### What the code says, verified

- **The arc graph is one file**, `src/dashboard/js/graph/arc-graph.js`, listed
  in `JS_ORDER` in `tools/story_dashboard.py:15`. Removing it from that list
  and deleting the file retires it. The tab that opens it is in
  `src/dashboard/index.html:191` (`tab-arcgraph`), and the panel that renders
  it is `#graph-tab-arcgraph` (`src/dashboard/index.html:198`).
- **The character panel's arc section** is `DASH.arcSectionHtml` in
  `src/dashboard/js/panels/panel-manager.js:27`, called from
  `src/dashboard/js/panels/entity-panels.js:119`.
- **The network graph's arc tooltip** is `src/dashboard/js/graph/network.js:134-188`,
  reading `arc_type`, `character_value`, `arc_beats_list`.
- **The statistics arc summary** is `src/dashboard/js/statistics/statistics.js:228-244`,
  rendering into `#structStats-arc-summary` (`src/dashboard/index.html:510`).
- **The scene list's beat dots** are `src/dashboard/js/views/scenes.js:57-64`,
  reading `scene.arc_beats` — the dead field from T0.2.
- **A new visualisation is designed later from the data** (design §11). No
  replacement is built in this plan.

### Tasks

- [x] **T4.1** Remove the arc graph: delete `src/dashboard/js/graph/arc-graph.js`,
      drop it from `JS_ORDER`, remove the tab and the panel from
      `src/dashboard/index.html`. Verify: `story_dashboard` returns HTML that
      loads, and no reference to `arc-graph` remains in `src/`.
- [x] **T4.2** Remove the character panel's arc section: `DASH.arcSectionHtml`
      and its call site. Verify: the character panel still renders.
- [x] **T4.3** Remove the network graph's arc tooltip and the legend's arc
      badge. Verify: hovering a character shows the role, not the arc type.
- [x] **T4.4** Remove the statistics arc summary and its container. Verify: the
      statistics group renders without it.
- [x] **T4.5** Remove the scene list's beat dots. Verify: the scene list
      renders without them.
- [x] **T4.6** Verify no dashboard JS reads a field the schema no longer has.
      Verify: a grep of `src/dashboard/` for `arc_type`, `character_value`,
      `arc_beats_list`, `is_crisis`, `is_climax`, `arc_beats` returns nothing.

### Findings

**F4.1 — `src/dashboard/js/graph/arc-graph.js` is the only file a test runs in
node.** `tests/test_arc_graph_story_series.py` runs the real file against a
stub DOM. Retiring the graph retires that test file; it is replaced by nothing
in this plan (the design defers a new visualisation). Recorded so the deletion
is deliberate rather than a gap.

### FINAL BRIEF

Phase 4 complete. Six tasks landed.

**T4.1 — Arc graph removed.** `src/dashboard/js/graph/arc-graph.js` deleted
(364 lines). Dropped from `JS_ORDER` in `tools/story_dashboard.py`. Tab
(`tab-arcgraph`) and panel (`#graph-tab-arcgraph`) removed from
`src/dashboard/index.html`. The `#arc-beat-tooltip` div also removed (used
only by arc-graph and the network hover, both retired). The arcgraph branch in
`DASH.switchGraphTab` (`navigation.js:56`) removed. The test file
`tests/test_arc_graph_story_series.py` deleted — it ran the real
`arc-graph.js` against a stub DOM and has no counterpart in the design.

**T4.2 — Character panel arc section removed.** `DASH.arcSectionHtml` (23
lines) deleted from `panel-manager.js`. Call site (`<div>` with Arc title)
removed from `entity-panels.js`. The character panel still renders — the arc
section was a self-contained block.

**T4.3 — Network graph arc tooltip and legend badge removed.** The
`hoverNode` handler (24 lines) in `network.js` removed — it existed solely to
show the arc tooltip. The `blurNode` handler removed with it. The legend's
arc badge (lines filtering `arc_type` and rendering the badge) removed.
Hovering a character in the network now does nothing (no tooltip) — the role
is visible in the legend.

**T4.4 — Statistics arc summary removed.** The arc summary block (20 lines)
in `statistics.js` removed, and its HTML container (`structStats-arc-summary`)
removed from `index.html`. The statistics group renders without it.

**T4.5 — Scene list beat dots removed.** The `arcBeatDots` block (8 lines)
in `views/scenes.js` removed, along with its `${arcBeatDots}` reference in the
template. The scene list renders without them.

**T4.6 — No dashboard JS reads a retired field.** A grep of `src/dashboard/`
for `arc_type`, `character_value`, `arc_beats_list`, `is_crisis`, `is_climax`,
`arc_beats` returns zero matches.

**CSS cleanup.** `src/dashboard/css/graph.css` stripped of all arc-graph
styles (cast/char cards, arc-graph panel, SVG elements, beat tooltip,
scene-card dots, legend arc type, warnings, controls). Kept: shared graph
view styles, tab mechanism (network still uses it), `.arc-empty` (used by
`value-graph.js`), `.graph-legend`, `.legend-item`, `.legend-dot`,
`.edge-tooltip`.

**Test updates.** `tests/test_story_dashboard_integration.py` updated:
removed `graph/arc-graph.js` from the hardcoded JS list, removed six arc
handler names from the `handler_fns` assertion list, removed four arc DOM IDs
from `required_ids`.

**Tests.** 1181 pass (was 1189). The 8-test drop is the deleted
`test_arc_graph_story_series.py`. No regressions.

---

## Phase 5 — the skill

Prose only. It names the fields and sections of every earlier phase, so it
lands after them.

### What the code says, verified

- **The skill is `tasks/task_30/skill/`**, a schematic draft — headings and
  notes only. Its `SKILL.md` frontmatter declares
  `name: hermes-story-architect` and its file table names
  `references/craft/scene-design.md`, `character-and-arc/arc-beats.md`,
  `value-pass.md`, `model/value-system.md`.
- **The file table does not match the tree.** `SKILL.md` names
  `craft/character-and-arc/arc-beats.md`, `craft/character-and-arc/relationships.md`,
  `craft/plot-and-structure.md`, `craft/project-design.md`, `craft/world-and-place.md`,
  `craft/character-and-arc.md` and `theory/structure-and-plot.md`; the tree has
  `craft/character-arc.md`, `craft/scene-design.md`, `craft/value-pass.md`,
  `craft/character.md`, `craft/character-relationships.md`, `craft/world.md`,
  `craft/location.md`, `craft/variant.md` and `theory/scene-and-beat.md`. The
  `references/craft/arc-beats.md` the design points at does not exist. This is
  pre-existing and outside this plan; recorded because the design's §11 lists
  the skill as an impact.
- **The skill is not shipped.** `skills/hermes-story-architect/` is empty in the
  repo and the plugin's `_register_skills` (`__init__.py:236`) silently does
  nothing when it is missing. The design's skill impact is therefore a
  documentation change, not a code change.

### Tasks

- [ ] **T5.1** Add a `scene_beats` section to the skill's model file
      (`references/model/entity-sections.md`): the three sections and what goes
      in each, and the rule that `scene_beats` is exempt from unfilled checks.
- [ ] **T5.2** Update `references/craft/scene-design.md`: the scene's `Beats`
      and `Conflict` sections move to `scene_beats`, the scene keeps
      `Objective`, and the two directions (structure-first, content-first) are
      stated. Verify: no reference to a scene `Beats` section remains.
- [ ] **T5.3** Retire the `arc_beat` references in the skill: `character-arc.md`,
      `value-system.md`, `value-pass.md`, `ids-and-links.md`,
      `entity-sections.md`. Verify: `git grep arc_beat tasks/task_30/skill/`
      returns nothing.
- [ ] **T5.4** Fix the `SKILL.md` file table to match the tree it lists.
      Verify: every path in the table exists.

### Findings

**F5.1 — the skill file table is wrong today.** It is pre-existing, not caused
by this design, and it is the one thing in the design's impact list that is
not caused by `scene_beats`. Resolved by T5.4 as part of this phase, because
a skill that cannot be navigated is worse than a skill that is out of date.

### FINAL BRIEF

---

## Phase 6 — legacy

A self-contained deletion: `arc_beat`, its markdown tree, and the character
arc fields that duplicate scene values.

### What the code says, verified

- **`arc_beat` is a type in `ENTITY_SCHEMAS`, `ENTITY_LABELS`,
  `ENTITY_COLUMN_MAP`, `_RELATION_FIELDS`, `standard_sections` and
  `REQUIRED_FIELDS`.** Removing the schema entry removes it from every enum
  derived from `ENTITY_SCHEMAS` — the draft enum, the describe enum and
  `REQUIRED_FIELDS`. The five other declarations are hand-written and must go
  with it.
- **`core/entity.py` has four arc-beat blocks**: the `validate_entity` enum
  checks (`:82-85`), the `ENTITY_COLUMN_MAP` entry (`:308`), the
  `columns_for_insert` special case (`:567`), and the `_purge_references`
  comment (`:1054`). Each is a separate edit.
- **`core/db.py` has the arc read model**: the `get_character_arcs` function
  (`:851`), the `arc_beat` branch in the unfilled loop (`:829`), the
  `arc_beat` branch in `_build_all` (`:1180`), the `arc_beats_list` grouping
  (`:1222-1250`) and the `scene.arc_beats` block (`:1272-1289`, dead since
  T0.2).
- **`tools/story_import.py` has the nested-tree import**: `_import_arcs`
  (`:370`), the `arcs/` walk in the safety guard (`:87-92`), the `_columns_for`
  branch (`:502`), the `_extra_for` skip set (`:567`) and the `_insert_entity`
  `char_slug` parameter.
- **`tools/story_export.py` has the nested-tree export**: the `arc_beat` branch
  (`:237`), the `_frontmatter_for` branch (`:379`), the `_sweep_stale`
  parent-folder cleanup (`:122-128`) and `_FOLDERS` (arcs is absent from it
  because arcs are nested).
- **`tools/story_retrieve.py` has the `LIKE` fallback** (`:73-86`) for a bare
  beat label.
- **`tools/story_admin.py` has the restore cascade** (`:324-333`) that brings
  back a character's beats.
- **`tools/story_load.py` has `view="arc"`** (`:129-165`) and its two schema
  parameters.
- **`core/writes.py` has the `validate_arc_parents` call** (`:190`) and the
  `arc_complete` field is read nowhere except its schema entry and two tests.
- **The fixture carries `arcs/` with four character folders** and 11 beat
  notes; `tests/migrate_fixture_b1_b2.py` is a one-time migration script whose
  docstring already says "arc beat fields (shift, y) are kept until B3".

### Tasks

- [ ] **T6.1** Remove `arc_beat` from `ENTITY_SCHEMAS`, `ENTITY_LABELS`,
      `ENTITY_COLUMN_MAP`, `_RELATION_FIELDS`, `standard_sections`,
      `REQUIRED_FIELDS`, and the `validate_entity` enum checks. Verify:
      `story_describe` no longer lists it, and `story_draft` refuses it.
- [ ] **T6.2** Remove the character arc fields from `ENTITY_SCHEMAS`:
      `arc_type`, `character_value`, `character_value_at_open`,
      `character_value_at_close`, `arc_complete`, `arc_beats_list`. Verify:
      the schema has no field whose name starts with `arc` except
      `scene_beats`-side names.
- [ ] **T6.3** Remove the `arc_beat` read model from `core/db.py`:
      `get_character_arcs`, the unfilled branch, the `_build_all` branch, the
      `arc_beats_list` grouping and the `scene.arc_beats` block. Verify:
      `git grep -n arc core/` returns nothing.
- [ ] **T6.4** Remove the `arc_beat` write model from `core/entity.py`:
      `validate_arc_parents`, the `columns_for_insert` special case, the
      `ENTITY_COLUMN_MAP` entry, the `_purge_references` arc case, and the
      `_validate_y` helper. Verify: `git grep -n arc_beat core/` returns
      nothing.
- [ ] **T6.5** Remove `view="arc"` from `story_load`, and the
      `get_character_arcs` import. Verify: the view enum no longer lists it.
- [ ] **T6.6** Remove the nested-tree import and export: `_import_arcs`, the
      `arcs/` safety walk, the `_columns_for` branch, the `_extra_for` skip
      entry, the `char_slug` parameter, the export branch, the
      `_frontmatter_for` branch, and the `_sweep_stale` parent cleanup. Verify:
      a `scene_beats/` folder imports and exports flat.
- [ ] **T6.7** Remove the restore cascade and the `LIKE` fallback. Verify:
      `restore` on a character no longer touches beats, and a bare beat label
      is simply not an id.
- [ ] **T6.8** Remove the fixture's `arcs/` directory and its 11 beat notes.
      Verify: `build_fixture_db` imports the fixture with no `arcs/` folder and
      every test that depended on it passes.
- [ ] **T6.9** Remove `tests/migrate_fixture_b1_b2.py` — it is a one-time
      migration whose only remaining target is arc beat fields. Verify: it is
      not imported by any test.
- [ ] **T6.10** Remove `tests/test_arcs.py` and
      `tests/test_arc_graph_story_series.py`. Verify: the suite passes without
      them.
- [ ] **T6.11** Remove the arc assertions from the remaining test files:
      `test_core.py`, `test_writes.py`, `test_edit_safety.py`,
      `test_soft_delete.py`, `test_purge.py`, `test_phase3_scenario.py`,
      `test_phase2_db_reads.py`, `test_field_coverage.py`,
      `test_story_load_views.py`, `test_story_describe.py`,
      `test_retrieve_reading.py`, `test_id_is_not_a_field.py`,
      `test_import_enum_validation.py`, `test_unfilled_fields.py`,
      `test_export_sweep.py`, `test_round_trip.py`. Verify: `git grep -ln
      arc_beat tests/` returns nothing.
- [ ] **T6.12** Migrate the live project: delete the 6 `arc_beat` rows from
      `/media/theww/AI/TWW/hermes-story-architect/projects/browser-verification-test/.story/story.db`,
      delete `arcs/`, and rebuild from markdown with `story_import`. Verify:
      the project loads and the scene count is unchanged.

### Findings

**F6.1 — the `arc_complete` flag has no reader.** It appears in `ENTITY_SCHEMAS`
and in two tests; no dashboard, tool or skill reads it. Removing it is a
deletion with no behavioural change. Recorded because the design lists it as
retired and a grep is the only evidence that it was never used.

**F6.2 — `tests/test_arc_graph_story_series.py` is the only node-based test.**
It runs `arc-graph.js` against a stub DOM. The design defers a new
visualisation, so this test file is deleted rather than replaced. Recorded as
a known gap: when a new visualisation lands, it needs a test of the same kind.

### Parallel work

T6.1–T6.4 (the schema and core) are one logical change and must land together.
T6.5–T6.7 (the tools) are independent of each other and can be picked up in
parallel once T6.1–T6.4 land. T6.8–T6.12 (tests, fixture, live project) depend
on T6.1–T6.7 and are one task file.

### FINAL BRIEF

---

## Phase 7 — cleanup

Names checked against the final state, dead helpers removed, and the fixture
and live project confirmed.

### What the code says, verified

- **Naming is enforced by convention, not by a test.** `_check_slug` covers
  ids; field names are free. The design's names are `beats`, `true_character`,
  `changes`, `gap`, `risk`, `surface`, `subtext`, `turning_point`, `driver`,
  `scene_objective`. A name that survives a rename because "it was already
  there" is the failure mode this phase exists to catch.
- **`_default_for` and `_omit` are generic** and survive the retirement. The
  arc-specific helpers (`_validate_y`, `validate_arc_parents`,
  `get_character_arcs`) do not.
- **The fixture's DB is a build artefact** (`tests/conftest.py:build_fixture_db`),
  built from markdown by `story_import` and never committed. Rebuilding it is
  the migration.

### Tasks

- [ ] **T7.1** Verify every field name in `ENTITY_SCHEMAS` matches the design's
      vocabulary, and that no name is kept only because it existed before.
      Verify: a table of design name → schema name, with none unmatched.
- [ ] **T7.2** Verify every section name matches the design's vocabulary, and
      that `scene_beats`'s three sections are exactly `Conflict`, `Findings`,
      `Notes`. Verify: `git grep -n "Beats" core/` returns nothing.
- [ ] **T7.3** Remove dead helpers: `validate_arc_parents`, `_validate_y`,
      `get_character_arcs`, and any arc-specific comment that no longer
      describes code. Verify: `git grep -in arc core/ tools/ src/` returns
      nothing.
- [ ] **T7.4** Verify the fixture and the live project both load, and that the
      live project's scene count is unchanged. Verify: a `story_load` on each,
      comparing scene ids.
- [ ] **T7.5** Verify the suite passes end to end. Verify: `pytest` with no
      failures, and a count of tests that is lower than 1017 by the number
      retired in T6.10 and T6.11.

### Findings

**F7.1 — the test count will drop.** 1017 tests exist today; T6.10 removes two
files and T6.11 removes arc assertions from 17 more. The count after the plan is
not 1017 and is not 1094 (a figure carried in an older note). Recorded so the
final verification is against a stated expectation rather than a remembered
number.

### FINAL BRIEF

---

## Appendix A — coverage matrix

Every statement in the design, mapped to the phase that implements it. A row
marked **not in the plan** is a design claim this plan does not carry; a row
marked **deferred by design** is one the design itself puts outside scope.

### §5.1 — fields

| Design claim | Where | State |
| --- | --- | --- |
| `scene` ref, required, must exist | T1.1, T1.3, T1.5 | in plan |
| `driver` ref character, optional | T1.1 | in plan |
| `scene_objective`, same name/meaning as on the scene | T1.1, T1.9 | in plan |
| `turning_point`, surfaces on the scene computed | T1.1, T1.8 | in plan |
| `true_character` list, none/one/several | T1.1 | in plan |
| `beats` list, ordered | T1.1 | in plan — nested per the diagram (F1.5) |

### §5.2 — beat

| Design claim | Where | State |
| --- | --- | --- |
| diagram: `action`/`reaction`, each `by`/`surface`/`subtext` | T1.1 | in plan — **the shape** (F1.5) |
| table: `by`/`surface`/`subtext`/`gap`/`risk`/`changes` | T1.1 | in plan — the same fields, read across the two sides |
| `by` may be character, location or world | F1.1 | in plan (needs a bespoke check) |
| same character on both sides = inner conflict | F1.5 | prose — now checkable, same `by` on `action` and `reaction` |
| `changes[].entity` may be character, relationship, location or world | F1.1 | in plan — **four** types, and relationship is valid here only |
| every referenced entity exists | T1.5 | in plan |
| a beat has content | T1.6 | in plan |
| surface/subtext describe, gap/risk/changes evaluate | — | prose, no code |

### §5.3 — true character

| Design claim | Where | State |
| --- | --- | --- |
| `character` ref, may differ from `driver` | T1.1 | in plan |
| `dilemma` | T1.1 | in plan |
| `choice_reveals` | T1.1 | in plan |
| none, one or several per scene | T1.1 (list) | in plan |

### §5.4 — sections

| Design claim | Where | State |
| --- | --- | --- |
| `Conflict`, `Findings`, `Notes` | T1.2 | in plan |
| one flat directory named after the entity | T1.7 | in plan |
| each note named by the scene's title | T1.7 (export uses the title) | in plan |
| id and `scene` link live in frontmatter | T1.3, F1.3 | in plan |

### §6 — scene entity changes

| Design claim | Where | State |
| --- | --- | --- |
| `scene_objective` stored, optional | T1.9 | in plan |
| `turning_point` computed, read-only | T1.8 | in plan |
| `scene_beats` computed, read-only, reported unfilled | T1.8, T2.1 | in plan |
| scene sections: `Conflict` and `Beats` move to `scene_beats` | T1.2, T5.2, T7.2 | in plan |
| `Objective` stays on the scene | T5.2 | in plan |
| `value_turns` stays | — | unchanged, no task needed |
| only the `effects` description changes | T1.9 | in plan |

### §6.1 — effects and changes

| Design claim | Where | State |
| --- | --- | --- |
| `effects` = outcome of the value shift for a plot protagonist, by conflict level | — | unchanged |
| beat `changes` = what this exchange changes, for anyone or anything | T1.1 | in plan |
| beat `changes` grain = one beat; entities = character, relationship, location, world | F1.1 | in plan |
| `effects` needs no `scene_beats`; `changes` is part of it | — | by construction |
| when both exist they should agree; divergence is a finding, not an error | — | prose (§8 soft), no code |

### §7 — retired

| Design claim | Where | State |
| --- | --- | --- |
| entity `arc_beat` | T6.1–T6.4 | in plan |
| computed `character.arc_beats_list` | T6.2, T6.3 | in plan |
| character fields `character_value`, `_at_open`, `_at_close`, `arc_type` | T6.2 | in plan |
| beat fields `shift`, `y`, `is_crisis`, `is_climax` | T6.1 | in plan |
| `arc_complete` flag | T6.2 | in plan |
| `arc_type` becomes a reading of the path, not stored | T6.2 | in plan |

### §8 — rules

| Design claim | Where | State |
| --- | --- | --- |
| the scene exists, and has no other `scene_beats` | T1.4 | in plan |
| every referenced entity exists | T1.5 | in plan — write path only; importer is out of scope (F1.6) |
| `by` is a character, location or world; `changes[].entity` is character, relationship, location or world | F1.1 | in plan |
| a beat has content | T1.6 | in plan |
| a character in `by`/`driver`/`true_character` not in the scene's cast | — | soft finding, prose — `by` means either side of the beat |
| a value turn with no turning point, or a turning point in a flat scene | — | soft finding, prose |
| scene `effects` disagreeing with beat `changes` | — | soft finding, prose |
| `scene_beats` older than the scene's script | — | soft finding, prose — **needs a timestamp; no timestamp exists today** |
| a reference left dangling by a later delete | T1.3 (column) | in plan |

### §8.1 — unfilled and completeness

| Design claim | Where | State |
| --- | --- | --- |
| a beat list is allowed on any scene | T1.4 (only one `scene_beats`, list inside) | in plan |
| `scene_beats` itself is exempt from unfilled checks | T2.1 | in plan (exempt by default) |
| the scene's computed `scene_beats` is reported unfilled when empty | T2.1 | in plan |
| reported only for `drafted` or later, `dramatic_role` `plot_role` or empty | T2.1 | in plan |
| a `planned` scene is a stub and is skipped | T2.1 | in plan |
| a `transition` or `non-event` scene is never reported | T2.1 | in plan |
| completeness is existence; `scene_beats` has no status | T1.1 (no status field) | in plan |

### §9 — workflow

| Design claim | Where | State |
| --- | --- | --- |
| structure-first sequence | T5.2 | in plan |
| content-first sequence | T5.2 | in plan |
| skill guidance: reconcile after reworking `scene_beats` | T5.2 | in plan |

### §10 — outputs the record enables

| Design claim | Where | State |
| --- | --- | --- |
| a character's path in story order | — | **deferred by design (§2)** |
| escalation read from gaps and risks | — | **deferred by design (§2)** |
| `changes` entries as soft continuity by reverse lookup | — | **deferred by design (§2)** |

### §11 — impact

| Design claim | Where | State |
| --- | --- | --- |
| `constants.py`, `entity.py`, write and draft path, `effects` description | T1.1, T1.4–T1.6, T1.8, T1.9 | in plan |
| `core/db.py` arc reads, `arc_beats_list`, scene `arc_beats`, computed `turning_point` | T0.2, T1.8, T6.3 | in plan |
| export/import/delete cascade: `arcs/<character>/` removed, `scene_beats` flat, scene delete removes its `scene_beats` | T1.3, T1.7, T6.6 | in plan |
| unfilled: `unfilled_fields` exempts `scene_beats`; scene's computed field through `_RELATION_FIELDS` | T2.1 | in plan |
| tools: `story_describe`, `story_load` (`view='arc'`), `story_retrieve` | T3.1–T3.3, T6.5 | in plan |
| dashboard: arc panels and graph retired | T4.1–T4.6 | in plan |
| skill: `scene-design`, `character-arc`, `value-system`, `value-pass` | T5.1–T5.4 | in plan |
| tests: about 18 test files and the fixture `arcs/` directory | T6.8–T6.11 | in plan — **verified: exactly 18 test files mention `arc_beat`** |

### §12 — open points

| Design claim | Where | State |
| --- | --- | --- |
| 1. confirming the `-beats` id suffix | T1.1, T1.4 | in plan — resolved as `{scene_id}-beats` |
| 2. audience knowledge as an optional field | — | **not decided by the design — no task** |
| 3. the hinge between adjacent scenes, imagery tracking | — | **deferred by design** |
| 4. telling order versus story time | — | **deferred by design** |

---

## Appendix B — gaps found in this pass

Three things this plan did not carry, and one the design did not say.

**B.1 — the `effects` description change had no task. Resolved: added to
T1.9.** §11 lists it under impact and §6.1 defines it ("the outcome of the
value shift for a plot protagonist, by conflict level"), but no task edited
`core/constants.py:227` (`effects`: "One entry per protagonist the shift
affects"). The field's *shape* does not change — only its description.

**B.2 — §8's soft findings, and what the design's own `Findings` section is
for.** §8 splits its rules into **hard** (refused on write) and **soft**
(reported as findings). The five soft ones are listed in the matrix under §8.

The design does not build a soft-finding mechanism. §5.4 gives `scene_beats`
a **`Findings`** section, defined as "the evaluation of the scene (missing
conflict, repetition, misplaced turning point, on-the-nose dialogue)" — a
prose field the author writes. So in this design a soft finding is **written
by the author**, not computed by a reader. That is a deliberate split: the
hard rules are enforceable facts about the record, and the soft ones are
judgements that need the scene's script and the author's eye.

The consequence for the plan: none of the five soft findings gets a task.
They are prose in the skill (T5.1–T5.3), and the `Findings` section is the
surface. Building a checker for any of them would be code the design did not
ask for.

One of them is worth naming because it *looks* computable: "a character in
`by`, `driver` or `true_character` who is not in the scene's cast" is a
set-difference between two things already stored. But it is still a judgement —
a character can drive a scene from off-screen, and a `true_character` moment
can belong to someone who never appears in it. The design puts it in the soft
list precisely because it is often correct. So it stays prose.

**B.3 — "`scene_beats` older than the scene's script" has no timestamp.**
§8 lists it as a soft finding. No entity carries a created-at or updated-at
column (`core/db.py:19-31` has `deleted_at` only), so "older than" cannot be
computed. It cannot be implemented without adding a timestamp, which is a
schema change outside this design. Recorded as unimplementable as written.

**B.4 — the two reference sites differ in size, and the difference is
meaningful.** §5.2's table: `by` is "a character, location or world" (three);
`changes[].entity` is "Character, relationship, location or world" (four). The
fourth — **relationship** — is the object of a change but never an actor. A
relationship cannot be a `by`, because a `by` names who acts and a relationship
is the bond between two people, not a party to the exchange.

This is not an oversight in the design and it is not a typo to fix. It is the
distinction the two fields exist to draw: `by` is agency, `changes[].entity` is
what the exchange lands on. §5.2's inner-conflict rule corroborates it — "the
same **character** on both sides", not "the same entity".

Consequence for the implementation: `validate_beat_references` (F1.1) resolves
two lists, not one — `by` against three types, `changes[].entity` against four.
A single shared list would either let a relationship act or forbid a
relationship from changing.
