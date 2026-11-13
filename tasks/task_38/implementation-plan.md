# Structured scene headings — implementation plan

Spec: `spec.md`. Phases run in order; each ends at a verification gate. The
order matters: the schema is the contract every later phase reads, the write
boundary is the only enforcement point, and the assembly is the fix for the
0-scene bug. Changing the order means a later phase encodes a guess about an
earlier one.

## Findings the spec did not assume

- **The fixture already stores the heading as frontmatter and Content as
  body-only.** So the vault round-trip is already half-way to the target; the
  missing half is the structured fields and the composition at assembly.
- **The 0-scene bug is real and reproducible.** Built the fixture DB, ran
  `get_screenplay_text` → assembled text has no heading lines, stats scenes = 0.
  This is the bug the assembly phase fixes.
- **`GROUPS` already exists** (`core/manual_entities.py:200-202`) and the form
  already renders it (`:316-317,387`). Grouping is a schema-key change, not new
  machinery.
- **`writes` and `story_import` are the only section writers.** So the write
  boundary is `writes` (authored) plus `import` (vault); no third path.
- **Retiring `heading` breaks the fixture immediately.** `story_import._extra_for`
  refuses any frontmatter key the schema does not declare, so the fixture's
  `heading:` lines stopped importing the moment Phase 1 landed. The fixture
  markdown was therefore migrated in Phase 1 (Phase 9 item 1); the live-project
  one-off script stays in Phase 9.

## Assumptions to verify

Written as claims before checking. Each is marked with the verified result.

- [x] `get_screenplay_text` and `get_dashboard_data` are the only two assembly
      paths. (Verified: the only `FROM sections` scene-body queries are
      `core/db.py:1437` and `core/db.py:1572`. `assemble_scene_content` no longer
      exists; no desktop or JS assembly. Other `heading='Content'` reads are not
      assembly — `core/manual_edits.py:61,116`, `core/db.py:1423` (`__SECTIONS__`),
      and the FTS index — and they keep working on body-only Content.)
- [x] No reader depends on `extra.heading` outside the surfaces listed in the
      spec. (Verified by grep; the spec table was **incomplete** and is corrected
      there. Full list: `scene_content_lint.py:71`, `manual_structure.py:62`,
      `manual_edits.py:103,145,151,174,236,304`, `manual_entities.py:468`,
      `db.py:1153,1202`, `drafts.py:183,599`; JS — `data-load.js:34,46,74-76`,
      `core.js:111-120,143-146`, `views/scenes.js:16,62`, `views/locations.js:12`,
      `views/reorder.js:79`, `utils.js:12`, `panels/entity-panels.js:169-186,509-511`,
      `forms/entity-form.js:346,353`, `script-editor/editor.js`, `model.js`,
      `script-view.js:69-91`. Verified NOT heading-dependent: `db.py` `_build_scene`
      (the base `story_load` view omits heading), `manual_entities.py:1325`
      (delete preview reads Content length only), `tools/story_retrieve.py`
      (returns extra fields dynamically, no hardcoded heading).)
- [x] The fixture's DB is always rebuilt from markdown, so a markdown edit is
      enough. (Verified: `git ls-files tests/fixtures` tracks no `.db`;
      `build_fixture_db` deletes the DB before importing; every test that copies
      `FIXTURE` re-imports, and `story_import` is destructive — it deletes every
      row and rebuilds. The on-disk `.story/story.db` is a local artefact.)
- [x] No existing location name contains ` - `. (Checked: fixture — "The
      Central Room", "The Garden"; live project — "The Garden", "The Central
      Room", "The Garden (dream)". The no-dash rule is safe to enforce.)

## Phase 1 — Schema + validation

**Goal:** the scene schema carries the structured heading; the old field is
gone.

Checklist:
- [x] `core/constants.py`: replace `heading` with `int_ext` (enum
      `INT_EXT_CHOICES`), `place` (string, optional), `forced_heading` (string,
      optional); add `group: "Scene heading"` to `int_ext`, `place`, `location`,
      `time_of_day`, `forced_heading`.
- [x] `core/constants.py`: add `places` to the `location` schema
      (`computed: True`, list) — the distinct `place` values of its scenes.
- [x] Rewrite the descriptions of the five grouped fields so each names the
      heading it is part of — the schema description is the channel the model
      learns from, and `story_describe` emits it verbatim. `location` and
      `time_of_day` currently describe themselves as standalone facts.
- [x] `core/entity.py`: add `INT_EXT_CHOICES` to the imports/validators; extend
      `validate_entity` for `scene` to check the `int_ext` enum and the no-dash
      rule on `place`.
- [x] `core/entity.py`: `validate_entity` for `location` refuses a `name`
      containing ` - ` (verified safe: no existing location name contains one).
- [x] `core/manual_entities.py`: `GROUPS` reads the schema `group` key; update
      `LABELS` (`int_ext` → "INT/EXT", `place` → "Place",
      `forced_heading` → "Forced heading"); `SCRIPT_FIELDS` becomes the five
      grouped fields — plus `characters`, which was already linked and has no
      `ref` to fall back on (see Phase 1 brief).

**Gate:** `story_describe` for `scene` lists the five grouped fields together,
each with a heading-derived description, and `validate_entity` refuses a bad
`int_ext`, a ` - ` in `place`, and a ` - ` in a location's `name`.

## Phase 2 — Write boundary

**Goal:** a scene with a script cannot be saved without a heading.

Checklist:
- [x] `core/writes.py` `create_entity` (beside `:186-199`) and `edit_entity`
      (beside `:442-468`): a scene branch on the merged state — Content
      non-empty ⇒ structured (`int_ext` + `location`) or `forced_heading`;
      otherwise `ValueError` before `BEGIN`.
- [x] `core/writes.py`: the same branch refuses `forced_heading` together with
      any of `int_ext` / `place` / `time_of_day` (exclusive heading source).
      `location` is allowed with either.
- [x] `core/scene_script.py`: `compose_heading(int_ext, location_name, place,
      time_of_day)` — always emits a time (`UNSPECIFIED` when unset), uppercases
      the location, validates the no-dash rule. The caller resolves the location
      slug to its `name`.
- [x] A helper that strips a leading heading line from incoming Content
      (`split_heading`) so an agent-written line is replaced, not duplicated.

**Gate:** `create_entity` / `edit_entity` refuse a scene with body-only Content
and no heading fields; a scene with `forced_heading` passes; a scene with both
a forced heading and structured fields is refused.

## Phase 3 — Assembly

**Goal:** the assembled script contains a heading line per scene.

Checklist:
- [ ] `core/db.py` `get_screenplay_text` (`:1567-1579`) and
      `get_dashboard_data` (`:1434-1444`): compose each scene's line from its
      fields before concatenating; skip scenes with empty Content. Resolve the
      location slug to its `name` (one join, or a name map alongside the scene
      rows).
- [ ] `screenplay_scene_ids` is derived from the same per-scene list, so the
      ids align with the rendered headings.
- [ ] `core/db.py`: the dashboard's location payload gains the computed `places`
      (batched reverse lookup of each location's scenes' distinct `place`).

**Gate:** the fixture (after Phase 9's markdown edit) assembles to one heading
per scene; stats scenes = 3.

## Phase 4 — Stats + click mapping

**Goal:** the parser understands the place segment; clicks map to the right
scene.

Checklist:
- [ ] `app/stats.py` `_parse_scene_location` (`:269-282`): split the location
      segment on ` - `; last = time, middle = place, first = parent. Location
      stats key on the parent only.
- [ ] `web/js/script-view.js:89-93`: map ids by the rendered headings, not
      positionally against the scene list.

**Gate:** a scene with a place shows the parent in location stats; a scene
without a heading (imported, permissive) does not shift the click mapping.

## Phase 5 — Editor backend

**Goal:** load/check/save carry the fields.

Checklist:
- [ ] `core/manual_edits.py`: `_scene_state` reads the fields; `_view_from_blocks`
      exposes them; `save_scene_script` writes the fields + Content in one
      `edit_entity` call; `check_scene_script` validates the same way.
- [ ] `core/scene_script.py`: retire `parse_heading`; keep `split_heading` for
      paste/import; `compose_content` takes the composed line.
- [ ] `core/scene_content_lint.py`: authored writes are guaranteed by the
      boundary, so the lint becomes an import/legacy check.

**Gate:** the editor opens a scene, edits `place`, saves, and the assembled
script shows the new heading line.

## Phase 6 — Editor frontend

**Goal:** the heading row edits the fields.

Checklist:
- [ ] `web/js/script-editor/model.js`: `composeHeading` gains `place`; the
      save blocker validates `int_ext` + location.
- [ ] `web/js/script-editor/editor.js`: `headingFrom` / `payload` carry
      `int_ext`, `place`, `forced_heading`; the custom mode becomes
      `forced_heading`. The place input suggests from the parent location's
      `places` (free text still allowed).

**Gate:** a manual edit of `place` and `time_of_day` round-trips through the
editor and the assembled script.

## Phase 7 — Import / export

**Goal:** the vault carries the fields.

Checklist:
- [ ] `tools/story_import.py`: read the fields from frontmatter; if `## Content`
      opens with a heading line, parse it into the fields and strip it.
- [ ] `tools/story_export.py`: write the fields to frontmatter; Content stays
      body-only.

**Gate:** import → export → import is byte-stable on the fixture.

## Phase 8 — Dashboard readers

**Goal:** every reader of the old field reads the new ones.

Checklist:
- [ ] `core/manual_structure.py:62`, `core/db.py:1153,1202`,
      `core/manual_entities.py:468`, `core/drafts.py:599`: derive the heading
      from the fields.
- [ ] `web/js/views/scenes.js:62`, `panels/entity-panels.js:509`,
      `core.js:111-121`: heading display from the fields.
- [ ] `tools/story_retrieve.py:128-167`: `_entity_fields` derives a location's
      computed `places` (distinct `place` of its scenes) for the agent's read.

**Gate:** the scene list, scene panel, character/location panels and the
structure tree show the heading for a scene edited in the editor.

## Phase 9 — Fixture + migration

**Goal:** the test projects are in the target shape.

Checklist:
- [ ] `tests/fixtures/save-the-children/scenes/*.md`: replace `heading:` with
      `int_ext:` + `place: ""`.
- [ ] Standalone one-off script for the live project: parse each scene's FM
      `heading` into `int_ext`/`place`. Not part of the app.

**Gate:** the fixture DB builds and the pipeline shows 3 scenes.

## Phase 10 — Tests

**Goal:** the invariants are pinned.

Checklist:
- [ ] `tests/test_scene_script.py`: `compose_heading` with place; the always-time
      rule; the no-dash refusal.
- [ ] `tests/test_manual_edits.py`: save with fields; refusal without a heading;
      forced heading.
- [ ] `tests/test_scene_heading_lint_integration.py`: update to the new fields.
- [ ] `tests/test_core.py`: round-trip carries the fields; the pipeline shows
      scenes.
- [ ] Dashboard harness: the heading row and the click mapping.

**Gate:** the full suite is green.

## Phase 11 — Skill docs

**Goal:** the agent is taught the new model.

Checklist:
- [ ] `tasks/task_30/skill/references/mechanics/screenplay-format.md:81-90`:
      one heading, structured; the forced-heading rename.
- [ ] `tasks/task_30/skill/references/craft/scene-design.md:199-205`: delete the
      "two different things" coupling.
- [ ] The scene schema description in `constants.py` states the derivation.

**Gate:** no doc tells the agent to write a free-text heading.

## Cleanup

The change retires a model, so the old model's code and tests go with it. Do
this inside the phase that retires each piece, not as a separate sweep at the
end — a dead helper left behind is the next session's guess.

**Remove — code**

- `core/scene_script.py`: `parse_heading`, `_HEADING_PARTS_RE`, `_TIME_SEP_RE`,
  `_canon_int_ext`, `_SCENE_NUMBER_RE`, `INT_EXT_CHOICES` (moves to
  `constants`), and `compose_content` if the editor writes blocks directly.
- `core/scene_content_lint.py`: its rule ("Content opens with a heading") is
  dead once Content is body-only. Its `check_scenes` call in `core/drafts.py`
  goes with it. If a "Content present but no heading fields" check is still
  wanted for imported notes, it belongs in the import path, not here.
- `core/manual_edits.py`: the `heading` dict, the `mode` / `custom` branches.
- `core/drafts.py:183,599`: the lint call and `fm.get("heading")`.
- `core/db.py:1153,1202`, `core/manual_structure.py:62`,
  `core/manual_entities.py:468`: the `extra.heading` reads.
- The duplicate heading parsers: `fountain_lexer.parse_location`,
  `screenplay.LOCATION_RE` / `extract_location`. One parser survives (the one
  stats and import share).
- `web/js/core.js:111-121`: heading-based scene matching, once ids are used.

**Remove — tests**

- `tests/test_scene_content_lint.py` (the module is gone).
- `tests/test_scene_heading_lint_integration.py` (the lint is gone).
- `tests/test_scene_script.py`: the `parse_heading` and `compose_content`
  tests.

**Fix — tests**

Fixed in Phase 2 (the boundary and the dropped `int_ext` default broke them):
`test_scene_script` (the new `compose_heading` signature), `test_manual_edits`
(the payload shape and body-only Content), `test_core` (the `heading` field
assertions, `test_edit_note_with_data_bag`), `test_edit_silent_success` (the
acceptance sweep now probes a valid heading), `test_manual_structure` (every
Content write carries heading fields) and `test_script_routes` (the fixture).

Still open:
- `tests/test_draft_preview.py`: the lint finding.
- `tests/test_round_trip.py`, `tests/test_values_export_import.py`: the field.
- `tests/dashboard_tabs_harness.js`: the heading row and the click mapping.

## Comment hygiene

When editing a file, delete comments that only record history — "was X, now Y",
"used to", "this used to be", phase and issue references ("B12", "D1a"), and
"restored/rewritten after <incident>". State only what the code does now. Keep a
comment only when it explains a non-obvious *why* (a constraint, an invariant, a
trap). If a comment describes a change, it is a line in the git log, not a
comment.

## Sequencing rationale

Schema → boundary → assembly is the dependency chain: the boundary needs the
fields to validate, the assembly needs the fields to compose. Stats and the
editor depend on the assembly being right. The fixture migration lands after the
core so the phases can be verified against a known-good project. Tests and docs
last, because they pin and describe what the code now does — writing them earlier
would encode the old model.

---

## Phase 1 brief — schema + validation

**Short summary.** The scene schema carries the structured heading. `heading` is
retired and replaced by `int_ext` (enum `INT_EXT_CHOICES`, default `INT.` —
dropped in Phase 2, see the Phase 2 brief),
`place` and `forced_heading`; `location` and `time_of_day` keep their storage but
their descriptions now name the heading segment they compose. All five carry
`group: "Scene heading"`, and `manual_entities.GROUPS` derives from that key
rather than a duplicate dict, so `story_describe` and the form share one source.
`location` gained the computed `places` list. `validate_entity` refuses a bad
`int_ext`, a ` - ` in a scene's `place`, and a ` - ` in a location's `name` —
all VALUE problems, so every write path and the importer refuse them, not just
the form. Fixture markdown was migrated to the new fields.

**Deviations.**

- **Fixture markdown migrated in Phase 1** (Phase 9 item 1). `_extra_for`
  refuses unknown frontmatter keys, so removing `heading` stopped the fixture
  import dead; verified an un-migrated note fails with `Unrecognised scene
  field(s): heading`. The live-project one-off script stays in Phase 9.
- **`SCRIPT_FIELDS` keeps `characters`.** The literal "five grouped fields"
  would drop it; the scene schema declares no `ref` for `characters`, so the
  form would render it as a generic list widget instead of the
  script-editor-linked display it has today.
- **`group: "Title page"` added to the six project fields.** Deriving `GROUPS`
  from the schema alone silently dropped the existing title-page grouping; the
  group now lives on the schema like every other group.
- **`INT_EXT_CHOICES` moved to `constants.py`** (a Cleanup item) and declared as
  a list, matching `VALID_ROLES`/`SCENE_TIMES_OF_DAY` and `_validate_enum`'s
  signature. `scene_script.py` imports it, so composer and validator cannot
  drift.

**Contract changes.**

- Scene frontmatter: `heading` gone; `int_ext`, `place`, `forced_heading` new.
  A note still carrying `heading` is refused at import.
- New VALUE refusals: `Invalid int_ext: <value>`, `place cannot contain ' - '`,
  `location name cannot contain ' - '`.
- `story_describe(scene)` emits `group: "Scene heading"` on the five fields and
  `places` on `location`; the five are contiguous in schema order.
- `manual_entities.SCRIPT_FIELDS` = the five heading fields + `characters`.

**Verification.**

- Gate: `story_describe` lists the five grouped fields with heading-derived
  descriptions; `validate_entity` refuses bad `int_ext`, ` - ` in `place`, and
  ` - ` in a location name; clean values produce no VALUE warnings; the form
  renders all five as `linked` under the `Scene heading` group.
- Fixture imports, stores `int_ext`, builds 3 scenes; round-trip and
  scene/location suites pass.
- Full suite: **1307 passed, 7 failed, 27 errors.** Two failures pre-date this
  phase (`test_no_hermes_imports`, `task_30/test_skill_references`; both fail on
  the stashed base). The remaining 32 are the intended retirement of `heading`:
  `test_manual_edits` (27 errors → Phase 5), `test_manual_structure` (2),
  `test_script_routes` (1), `test_core` unfilled (2) — all covered by Phases
  5–10.

---

## Phase 2 brief — write boundary

**Short summary.** A scene with a script can no longer be saved without a
heading. `writes.create_entity` and `writes.edit_entity` run one guard
(`_scene_heading_guard`) on the merged state before `BEGIN`: non-empty Content
requires `int_ext` + `location` or a `forced_heading`, and a `forced_heading`
is refused together with `int_ext`, `place` or `time_of_day`. The guard returns
body-only Content — a leading heading line is stripped with
`scene_script.split_heading`, so the heading composed at assembly replaces an
agent-written line instead of duplicating it. `compose_heading` gained `place`,
always emits a time (`UNSPECIFIED` when unset) and refuses a ` - ` in the
location name or place. A placeholder Content is a template, not a script, so
it passes through untouched.

**Deviations.**

- **`int_ext` has no default.** The schema default is empty, so a composed
  heading requires the caller to set it and a forced heading is empty by
  default — the exclusivity check (`forced_heading and (int_ext or place or
  time_of_day)`) needs no clearing. This replaced the earlier `INT.` default at
  the user's call.
- **`place` is upper-cased too.** The plan says "uppercases the location"; the
  place is a segment of the same uppercase heading line, so it is upper-cased
  as well. The stored `place` keeps the author's case; only the composed line
  is upper-case.
- **The guard strips a leading heading line.** The spec's write-boundary
  pseudocode only validates, but "Content is body-only … never stored" needs
  the strip at the write boundary, or an agent-written heading line is
  duplicated at assembly. `split_heading` already existed and is now used here.
- **The old-model tests were fixed in this phase, not Phase 10.** The boundary
  and the dropped default broke `test_core`, `test_edit_silent_success`,
  `test_manual_structure`, `test_manual_edits`, `test_script_routes` and
  `test_scene_script`; all were updated to the new model (heading fields on
  every Content write, body-only Content, the new `compose_heading` signature).
  Fixing them pulled in the Phase 5 `manual_edits` changes — see below.

**Contract changes.**

- New VALUE refusals on every authored scene write: `a scene with a script
  needs a heading — set int_ext + location, or a forced heading`;
  `forced_heading is exclusive with the composed heading — clear int_ext, place
  and time_of_day, or unset forced_heading`;
  `forced_heading must be a scene heading (INT./EXT. … or a forced '.HEADING')`.
- A forced heading must leave `int_ext`, `place` and `time_of_day` empty; a
  composed heading must set `int_ext`.
- `compose_heading(int_ext, location_name, place, time_of_day)` — the third
  positional is now `place`; a time is always emitted.
- `scene_heading(int_ext, location_name, place, time_of_day, forced_heading)`
  — the heading line for readers that still show one (the form's computed row,
  the editor); empty when the scene has neither heading.
- The script editor writes the structured fields (`int_ext`, `place`,
  `time_of_day`, `forced_heading`) instead of the retired `heading` key, and
  `load_scene_script` reports them; `findings`' `heading_missing` is decided by
  the fields, not by a Content line (Content is body-only now).
- A scene's stored `Content` is body-only: a leading heading line is stripped
  on write.

**Verification.**

- Gate, against a real fixture DB: create/edit refuse body-only Content with no
  heading fields; a forced heading passes with `int_ext` empty, and is refused
  when `int_ext`/`place`/`time_of_day` are set; an edit that adds a forced
  heading to a scene with a stored `int_ext` is refused; an agent-written
  heading line is stripped from stored Content.
- `compose_heading`: `INT. THE KITCHEN - NIGHT`, `INT. THE KITCHEN - PANTRY -
  NIGHT`, `EXT. PIER - UNSPECIFIED`; a ` - ` in a location name or place is
  refused.
- Full suite: **1339 passed, 2 failed** (Phase 1: 1307 / 7 / 27). The 2 failures
  pre-date the task (`test_no_hermes_imports`, `task_30/test_skill_references`;
  both fail on the stashed base). Every old-model test the boundary and the
  dropped default broke is fixed.
