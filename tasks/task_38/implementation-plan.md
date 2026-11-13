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
- [x] `core/db.py` `get_screenplay_text` (`:1567-1579`) and
      `get_dashboard_data` (`:1434-1444`): compose each scene's line from its
      fields before concatenating; skip scenes with empty Content. Resolve the
      location slug to its `name` (one join, or a name map alongside the scene
      rows).
- [x] `screenplay_scene_ids` is derived from the same per-scene list, so the
      ids align with the rendered headings.
- [x] `core/db.py`: the dashboard's location payload gains the computed `places`
      (batched reverse lookup of each location's scenes' distinct `place`).

**Gate:** the fixture (after Phase 9's markdown edit) assembles to one heading
per scene; stats scenes = 3.

## Phase 4 — Stats + click mapping

**Goal:** the parser understands the place segment; clicks map to the right
scene.

Checklist:
- [x] `app/stats.py` `_parse_scene_location` (`:269-282`): split the location
      segment on ` - `; last = time, middle = place, first = parent. Location
      stats key on the parent only.
- [x] `web/js/script-view.js:89-93`: map ids by the rendered headings, not
      positionally against the scene list. (Phase 4 found it already true of the
      scene list; the Phase 4 addendum goes further and matches by heading text,
      so a heading the server did not compose shifts nothing.)

**Gate:** a scene with a place shows the parent in location stats; a scene
without a heading (imported, permissive) does not shift the click mapping.

## Phase 5 — Editor backend

**Goal:** load/check/save carry the fields.

Checklist:
- [x] `core/manual_edits.py`: `_scene_state` reads the fields; `_view_from_blocks`
      exposes them; `save_scene_script` writes the fields + Content in one
      `edit_entity` call; `check_scene_script` validates the same way.
- [x] `core/scene_script.py`: retire `parse_heading`; keep `split_heading` for
      paste/import; `compose_content` takes the composed line.
- [x] `core/scene_content_lint.py`: authored writes are guaranteed by the
      boundary, so the lint becomes an import/legacy check. **Resolved as
      removal** — the module, its `core/drafts.py` call and its two test files
      are gone (see the Phase 5 brief).

**Gate:** the editor opens a scene, edits `place`, saves, and the assembled
script shows the new heading line.

## Phase 6 — Editor frontend

**Goal:** the heading row edits the fields.

Checklist:
- [x] `web/js/script-editor/model.js`: `composeHeading` gains `place`; the
      save blocker validates `int_ext` + location.
- [x] `web/js/script-editor/editor.js`: `headingFrom` / `payload` carry
      `int_ext`, `place`, `forced_heading`; the custom mode becomes
      `forced_heading`. The place input suggests from the parent location's
      `places` (free text still allowed).

**Gate:** a manual edit of `place` and `time_of_day` round-trips through the
editor and the assembled script.

## Phase 7 — Import / export

**Goal:** the vault carries the fields.

Checklist:
- [x] `tools/story_import.py`: read the fields from frontmatter; if `## Content`
      opens with a heading line, parse it into the fields and strip it.
- [x] `tools/story_export.py`: write the fields to frontmatter; Content stays
      body-only.

**Gate:** import → export → import is byte-stable on the fixture.

## Phase 8 — Dashboard readers

**Goal:** every reader of the old field reads the new ones.

Checklist:
- [x] `core/manual_structure.py:62`, `core/db.py:1153,1202`,
      `core/manual_entities.py:468`, `core/drafts.py:599`: derive the heading
      from the fields.
- [x] `web/js/views/scenes.js:62`, `panels/entity-panels.js:509`,
      `core.js:111-121`: heading display from the fields.
- [x] `tools/story_retrieve.py:128-167`: `_entity_fields` derives a location's
      computed `places` (distinct `place` of its scenes) for the agent's read.

**Gate:** the scene list, scene panel, character/location panels and the
structure tree show the heading for a scene edited in the editor.

## Phase 9 — Fixture + migration

**Goal:** the test projects are in the target shape.

Checklist:
- [x] `tests/fixtures/save-the-children/scenes/*.md`: replace `heading:` with
      `int_ext:` + `place: ""`. (Done in Phase 1; gate re-verified in Phase 9 —
      fixture DB builds, 3 scenes assemble with 3 composed headings.)
- [x] Standalone one-off script for the live project: parse each scene's FM
      `heading` into `int_ext`/`place`. Not part of the app.
      (`tasks/task_38/migrate_live_headings.py`. Applied to the live project;
      DB rebuilt; 6 scenes assemble with headings.)

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

---

## Phase 3 brief — assembly

**Short summary.** The assembled script now carries a heading line per scene.
Both assembly paths (`get_dashboard_data` §3 and `get_screenplay_text`) select
each scene's `extra` and its resolved location name alongside the body and pass
the rows to one shared composer, `_compose_screenplay`: it emits
`scene_heading(int_ext, location_name, place, time_of_day, forced_heading)`
above the body and joins entries with a blank line. A scene with Content but no
heading fields contributes its body alone, so imported notes stay visible.
`screenplay_scene_ids` comes from the same list and holds only the ids whose
entry rendered a heading, so ids align 1:1 with heading lines. The dashboard
location payload gains `places`: the distinct non-empty `place` of each
location's scenes, derived in one pass over the reverse lookup the denormalizer
already builds.

**Deviations.**

- **`places` is computed from the existing reverse lookup, not a new query.**
  `scene_locs` (scene → location ids) and `entity_by_id` extras are already
  loaded for the dashboard; one in-memory pass fills the buckets, sorted
  alphabetically. Same result as a batched SQL lookup, no extra round-trip.
- **`screenplay_scene_ids` excludes body-only scenes.** The plan said the ids
  are derived from the same per-scene list; deriving them from the entries
  that rendered a heading is what makes them align with the rendered headings —
  the property Phase 4's click-mapping gate checks.
- **Each path keeps its own ordering query** (dashboard: sequence order;
  `get_screenplay_text`: act→sequence→scene) and shares only the composer.
  Unifying the queries would change the dashboard's concatenation order for a
  project whose sequences interleave across acts.

**Contract changes.**

- `screenplay_text` is now `<heading>\n\n<body>` per scene instead of bare
  bodies; a scene with no heading fields contributes its body alone.
- `screenplay_scene_ids` aligns 1:1 with rendered heading lines (fewer ids than
  content-bearing scenes when some scene has no heading).
- Dashboard `story_data.locations[].places` = sorted distinct non-empty `place`
  of that location's scenes.

**Verification.**

- Gate, fixture DB built by import: three heading lines (`INT. THE CENTRAL ROOM
  - DAY`, `… - NIGHT`, `EXT. THE GARDEN - DAY`), stats `scenes = 3`,
  `sceneIds` = the three scene ids.
- Focused probe against real `create_entity` writes: place segment
  (`INT. THE KITCHEN - PANTRY - NIGHT`), forced heading (`.SNIPER SCOPE POV`),
  unset time → `UNSPECIFIED`, a body-only scene kept in the text but absent
  from `screenplay_scene_ids`, and `places` = `["cellar", "pantry"]` on the
  parent location, `[]` on a location without places.
- Full suite: **1339 passed, 2 failed** — identical to the Phase 2 baseline
  (`test_no_hermes_imports`, `task_30/test_skill_references`; both fail on the
  stashed base).

---

## Phase 4 brief — stats + click mapping

**Short summary.** `_parse_scene_location` now splits the location segment on
` - ` into parent / place / time: the first segment is the parent location, the
last is the time, the middle ones are the place. Location stats key on the
parent, so `INT. THE KITCHEN - PANTRY - NIGHT` folds into `THE KITCHEN` instead
of opening a second location row. The parser returns `place` beside the parent,
the time and the int/ext flags; `web/js/script-view.js` needed no change (see
the first deviation).

**Deviations.**

- **`web/js/script-view.js` was already correct.** The plan's premise — that the
  view maps ids "positionally against the scene list" — describes the
  pre-Phase-3 `screenIds`. The view maps `stats.sceneIds[sceneIdx]`, where
  `sceneIdx` counts the **rendered headings**, and Phase 3 made `sceneIds`
  heading-aligned (one id per composed heading, in order). That is "by the
  rendered headings" already, so the item was verified rather than changed.
- **The separator keeps its spaces.** `re.split(r'\s+[-–—−]\s+', …)` instead of
  the old bare `[-–—−]`, so a hyphenated location name (`TWENTY-ONE`) is not
  split apart. The composer only ever emits ` - `, so nothing legitimate is
  lost, and the unicode dashes the old parser accepted still work.
- **`place` is returned but not surfaced.** No stats column shows it; the
  parser is the one the import path will share (Cleanup), so it carries the
  place rather than dropping it on the floor.
- **A stored heading line still shifts the click mapping.** The mapping is
  correct only while every rendered heading was composed from fields. A scene
  whose stored Content still opens with a heading line — a legacy note, which
  Phase 7's import parses and strips and Phase 9 migrates — renders an extra
  heading, and every heading after it opens the *next* scene. Reproduced in
  jsdom against the real `script-view.js`. Closing it needs one id per
  rendered heading from the server, which is a design change and not a
  Phase 4 fix; flagged for the user.
- **`fountain_lexer.parse_location_information` still carries the old greedy
  split.** It is the duplicate the Cleanup list retires (nothing reads
  `properties['locations']`), so it was left for the phase that removes it
  rather than fixed twice.

**Contract changes.**

- `locationStats.locations[]` keys on the parent location: a scene with a place
  no longer creates a `<parent> - <place>` row.
- `_parse_scene_location` returns `place` — the middle segments joined with
  ` - `, `''` when the heading has no place.

**Verification.**

- Gate, location stats: fixture DB built by import, plus a place scene written
  through the real `create_entity` / `edit_entity` path and a heading-less scene
  inserted the way the importer does (the import path runs no heading guard).
  Before: three rows — `THE CENTRAL ROOM`, `THE GARDEN`, `THE CENTRAL ROOM -
  PANTRY`. After: two rows, `THE CENTRAL ROOM` at `number_of_scenes = 3`.
- Gate, click mapping: jsdom runs the dashboard's own `script-view.js` on the
  payload `get_dashboard_data` produced for that project. Four rendered
  headings, four `sceneIds`, `opened == sceneIds` heading by heading; the
  heading-less scene's prose renders and carries no click handler.
- Parser probe: `INT. THE KITCHEN - PANTRY - NIGHT` → name `THE KITCHEN`,
  place `PANTRY`, time `NIGHT`; `INT. THE KITCHEN - NIGHT` → no place;
  `INT. KITCHEN` → no time; `.SNIPER SCOPE POV` → name `SNIPER SCOPE POV`,
  no time (unchanged).
- Full suite: **1339 passed, 2 failed** — identical to the Phase 3 baseline
  (`test_no_hermes_imports`, `task_30/test_skill_references`; both fail on the
  stashed base).

## Phase 4 addendum — click mapping by text (user-approved follow-up)

The Phase 4 brief's "notable" entry — *a stored heading line still shifts the
click mapping* — is superseded by this change. Its diagnosis was right: the
view mapped `stats.sceneIds[sceneIdx]` positionally, which assumes the k-th
rendered heading is the k-th scene that composed one, and the server cannot
guarantee that (the lexer renders any heading line it finds in a body). Closing
it needs the id to travel with the heading, not with a position.

**Change.** `_compose_screenplay` now returns `(text, scene_headings)`, one
`{text, id}` per composed heading in order — it already held both values in its
loop. `_compute_screenplay_stats` takes `scene_headings=` and emits
`sceneHeadings`; `get_dashboard_data` returns `screenplay_scene_headings`. The
view walks its rendered headings and consumes the pairs **in order on a text
match** (normalised: trimmed, whitespace collapsed, upper-cased, one leading
`.` dropped — the lexer drops that dot from a forced heading). A heading that
matches no pair gets no id and shifts nothing; a miss never advances, so a miss
degrades to "no id", never to a wrong scene.

**Contract change.** `screenplay_scene_ids` and `__SCREENPLAY_STATS__.sceneIds`
are **gone**, replaced by `screenplay_scene_headings` /
`__SCREENPLAY_STATS__.sceneHeadings` (`{text, id}[]`). The old key was a bare
positional `string[]` that never said which heading belonged to which scene; the
new one does, so it is strictly more useful to any reader. Neither key reaches
the page beyond `__SCREENPLAY_STATS__`, and the only reader was
`script-view.js` — no agent tool emits either (`tools/` has no reference; the
agent addresses a scene by its slug from `story_load`). `docs/Dashboard
inventory/0.4.4` and `0.4.5` follow the rename.

**Verification.**
- jsdom, real `script-view.js` + real `get_dashboard_data` payload (fixture + a
  place scene + a scene whose Content still opens with a heading line): 5
  rendered headings, 4 composed pairs; the rogue heading is not clickable and
  opens nothing; clicking every heading opens exactly the 4 composed scenes in
  order; prose after the rogue heading is not clickable; prose after a composed
  heading opens that scene.
- `tests/script_editor_harness.js`: the stub carries the new shape and a rogue
  heading, and its script-view block was executed standalone (the full harness
  needs a Phase-5 server) — 2/2 pass. It caught a real regression on the first
  run: resetting the id per element left prose without one.
- Full suite: **1339 passed, 2 failed** — the same two pre-existing failures.

**Findings, not fixed here.**
- `tests/script_editor_serve.py:35` still passes the retired `heading` field to
  `create_entity`, which Phase 1 removed — the harness cannot build its project
  at all yet. It is Phase 5/10 territory (the harness also asserts
  `s.scene.heading`, which Phase 5 produces).
- `tasks/task_38/spec.md:41,179` still name `screenplay_scene_ids` / `sceneIds`;
  the spec is the approved baseline, so the deviation is recorded here instead.
- The rogue line also inflates `lengthStats.scenes` (the lexer counts it as a
  scene). The root-cause fix is at the write guard — refuse a scene whose
  `Content` contains a heading line anywhere — which is a behaviour change and
  a separate call.

---

## Phase 5 brief — editor backend

**Short summary.** The editor's load/check/save carry the structured heading.
`manual_edits._scene_state` reads `int_ext`, `place`, `time_of_day` and
`forced_heading` into the state; `_view_from_blocks` exposes them on `scene`
(plus the composed `scene.heading`), and `findings`' `heading_missing` is decided
by the fields, not by a Content line. `save_scene_script` writes the body-only
Content and the fields in one `edit_entity` call through `_heading_fields` — the
same helper `check_scene_script` uses — so a refusal means the same thing before
and after a save. `scene_script.parse_heading`, `_canon_int_ext` and the three
heading regexes are gone; `split_heading` stays for paste/import.
`core/scene_content_lint.py`, its `core/drafts.py` call and its two test files
are removed.

**Deviations.**

- **The lint was removed, not repurposed.** The checklist said it "becomes an
  import/legacy check"; the Cleanup said remove the module. Removal satisfies
  both: the write boundary guarantees authored writes, and Phase 7's import
  parses and strips a leading heading line, so a "Content present but no heading
  fields" check has no caller. The user confirmed ("we dont need legacy code").
  The `tasks/task_30/skill-structure.md` references to the module were updated
  with it. `tasks/task_38/spec.md:182` still names it as "import-only"; the spec
  is the approved baseline, so the deviation is recorded here.
- **`suggest_location` deleted with its test.** It suggested a registered
  location from the heading's `location_text`, which the editor no longer
  produces (the location is a linked slug). Dead once the `heading` dict went.
- **`_heading_fields` is the editor's own validation, shared by check and save.**
  The plan said `check_scene_script` "validates the same way"; one helper keeps
  the two from drifting. The write boundary re-checks the merged state on every
  path — this is the editor's message before anything is written.
- **`save_scene_script` wraps the boundary's refusal in `ScriptError`.** The
  boundary raises `ValueError`; the editor's tests and route expect `ScriptError`
  (422 either way).
- **`tests/script_editor_serve.py`'s retired `heading` field fixed here.** The
  Phase 4 addendum flagged it; the harness now passes `int_ext`.
- **Legacy tolerance kept in `_view`.** `load_scene_script` still strips a
  leading heading line from stored Content before parsing blocks. Content is
  body-only for anything written from now on, but a pre-migration project's
  stored Content still opens with a heading line, and showing it as a raw
  "Fountain" block in the editor is worse than the one-line split. Phase 9's
  migration removes the need for it.

**Contract changes.**

- `load_scene_script` and the script routes: the `heading` dict is **gone** from
  the response. `scene.int_ext`, `scene.place`, `scene.time_of_day` and
  `scene.forced_heading` are present, and `scene.heading` is the composed line.
  `findings` takes no `heading` argument.
- The save/check payload's `heading` object is
  `{int_ext, place, location, time_of_day, forced_heading}` — no `mode`, no
  `text`, no `location_text`.
- New editor refusals: `int_ext must be one of …`, `place cannot contain ' - '`,
  and the boundary's `forced_heading is exclusive with the composed heading — …`
  (now refused before anything is written).
- `content_hash` covers the four heading fields + location + Content + cast.
- `scene_script.parse_heading`, `_canon_int_ext`, `_HEADING_PARTS_RE`,
  `_TIME_SEP_RE`, `_SCENE_NUMBER_RE` and `suggest_location` are gone.

**Verification.**

- Gate: `test_manual_edits.test_place_is_composed_into_the_heading` saves a
  `place` through the real save path and asserts the assembled
  `get_screenplay_text` contains `INT. KITCHEN - PANTRY - NIGHT`.
- Focused suites: `test_scene_script`, `test_manual_edits`, `test_script_routes`,
  `test_draft_preview`, `test_manual_structure` — 127 passed.
- Full suite: **1297 passed, 2 failed** (Phase 4: 1339 / 2). The 42 dropped are
  the 32 tests in the two removed lint files and the 12 `parse_heading` /
  `suggest_location` tests, offset by 2 new editor refusals. The 2 failures
  pre-date the task (`test_no_hermes_imports`, `task_30/test_skill_references`;
  both fail on the stashed base).

---

## Phase 6 brief — editor frontend

**Short summary.** The heading row now edits the structured fields. It renders
four pills — INT/EXT, LOCATION, PLACE, TIME — between the two `-` separators,
and the preview (`composeHeading`) mirrors `scene_script.compose_heading`
exactly: place upper-cased and omitted when empty, time always emitted
(`UNSPECIFIED` when unset), and an unusable composed heading (no `int_ext`, no
location) shown as empty. The save blocker validates `int_ext` + location and
refuses a ` - ` in the place. The "✎" toggle is now the forced heading: it
prefills from the composed line, clears `int_ext`/`place`/`time_of_day`, and
writes `forced_heading`; "Use fields" clears it again. The payload is exactly
the Phase 5 backend contract `{int_ext, place, location, time_of_day,
forced_heading}`. The place menu suggests the parent location's `places` (from
the dashboard payload) and still accepts free text.

**Deviations.**

- **`headingFrom` reads `res.scene`.** Phase 5 removed the response's
  `heading` dict; the old reader returned an empty object, so every field
  silently defaulted and `int_ext` lost its `'INT.'` fallback. The editor was
  effectively blind to the stored heading until this phase.
- **The payload actually carries the fields now.** It sent `mode`,
  `location_text` and `text`, none of which `_heading_fields` reads — so a
  "custom" heading saved the structured fields instead of the typed text. That
  path is gone; the custom mode *is* `forced_heading`.
- **A UI-only `forced` flag decides the text-input branch.** `forced_heading`
  alone cannot discriminate "empty forced draft" from "structured scene": a
  forced heading with no location is legal and saveable. The flag is not sent;
  it only drives rendering and is part of the dirty snapshot.
- **Toggling clears the exclusive source.** The server refuses a forced heading
  together with `int_ext`/`place`/`time_of_day`, so the toggle clears them and
  the state always holds what a save writes. Switching back and forth therefore
  loses the other source's values — they were never stored either way.
- **Free-text locations are gone.** `location` is a ref in the target schema
  and the backend has no `location_text` storage (`_heading_fields` returns
  only the slug), so typing an unregistered location could never persist. The
  picker offers registered locations only; the rail's "not a registered
  location" chip went with it. A location must be registered before it can be
  used in a heading.
- **Place suggestions come from the dashboard payload**
  (`DASH.story.locations[].places`, computed in Phase 3), not from a new
  registry query — the spec names that payload as the derivation site, so no
  backend change was needed.
- **`composeHeading` was corrected, not just extended.** It previously omitted
  the time when unset and treated `int_ext` as always set; the server emits
  `UNSPECIFIED` and refuses an unset `int_ext`. The preview now matches the
  composer case for case (verified against the real function, below).
- **The harness was not updated here.** `tests/script_editor_harness.js`
  expects three pills, types an unregistered location, and its `DASH` stub
  carries no `locations`. Phase 10 owns the harness.

**Contract changes.**

- The editor's load/save/check `heading` payload is
  `{int_ext, place, location, time_of_day, forced_heading}` — the Phase 5
  backend contract, which the frontend had never actually sent.
- The heading row gains a PLACE pill; an unset `int_ext` shows an `INT/EXT`
  placeholder (pill warn-coloured), an unset place is dim, an unset time keeps
  its `TIME` warn.
- `res.heading` is no longer read by the editor; the composed preview is
  derived from the fields.

**Verification.**

- Model probe against the real `core/scene_script.compose_heading`: six cases
  (place, `UNSPECIFIED`, whitespace, `INT./EXT.`, `EST.`) plus ten
  blocker/composer assertions — all pass.
- End-to-end jsdom probe driving the shipped `model.js` + `editor.js` against
  a real server (a demo project whose Kitchen has the places `cellar` and
  `pantry`): opens the scene on `INT. / KITCHEN / PANTRY / NIGHT`; the place
  menu lists both known places; picking `cellar` and `DUSK` saves
  `{int_ext: 'INT.', place: 'cellar', location: 'kitchen', time_of_day: 'DUSK',
  forced_heading: ''}`; the GET round-trip returns those fields and
  `scene.heading = 'INT. KITCHEN - CELLAR - DUSK'`; the assembled
  `screenplay_text` and `screenplay_stats.sceneHeadings` show the same line.
  The ✎ flow prefills `INT. KITCHEN - CELLAR - DUSK`, clears the exclusive
  fields, saves `forced_heading: '.SNIPER SCOPE POV'`, and the assembled script
  shows it; "Use fields" restores the field row.
- Full suite: **1297 passed, 2 failed** — identical to the Phase 5 baseline
  (`test_no_hermes_imports`, `task_30/test_skill_references`; both fail on the
  stashed base).

---

## Phase 7 brief — import / export

**Short summary.** The vault carries the structured heading. A scene note whose
`## Content` opens with a heading line is canonicalised on import: the line is
parsed into `int_ext` / `location` / `place` / `time_of_day` (or
`forced_heading`), the fields are merged into the note, and the line is
stripped, so Content is body-only and the heading is composed at assembly like
any other. Frontmatter wins field by field; the line fills the gaps, so a note
already carrying the fields keeps them and just loses the duplicate line. The
location segment is a NAME, resolved to a slug against the locations imported
before the scenes. Export needed no change: the four fields already ride
`extra` into frontmatter and Content is written from the stored body.

**Deviations.**

- **Export is unchanged.** The checklist item was already satisfied —
  `_frontmatter_for` merges `extra` (which holds `int_ext`, `place`,
  `time_of_day`, `forced_heading`) and `location` comes from `location_id`.
  Verified with a probe: a scene written with `place: pantry` and one with
  `forced_heading: '.SNIPER SCOPE POV'` export both fields and body-only
  Content.
- **The parser is shared with stats, not duplicated.** `parse_heading_line`
  lives in `core/scene_script.py` (the Fountain ↔ fields bridge) and
  `app/stats.py` now imports it; `_parse_scene_location` is gone. This is the
  Cleanup's "one parser survives (the one stats and import share)". Parity is
  pinned against the deleted function over a 22-heading corpus (place, unicode
  dash, scene number, forced heading with a dash, lowercase `int.`, forced
  action marker) — exact, including the case-sensitivity of the int/ext flags.
- **Frontmatter wins; the line fills gaps.** The alternative (the line is
  authoritative) would make a migrated note's duplicate Content line override
  the declared fields, and would refuse the live project's `The Core - Day`
  (its line says `THE CORE`, its frontmatter says `the-garden`). Filling gaps
  lets a half-migrated note complete itself and a fully migrated one self-heal.
- **An unresolvable location is refused, not stored.** A heading line naming a
  location that is not registered raises `… names location 'X', which is not a
  registered location. Register it, or set 'location' in the note's
  frontmatter.` Storing the name as a slug would leave a heading that renders
  empty, which is the 0-scene bug in a new place.
- **A forced line together with composed fields is refused** (the write
  boundary's exclusivity rule), so the importer cannot create a state the
  authored path forbids.
- **`_insert_entity` returns the effective frontmatter.** The relations are
  derived from it, so a location supplied by the heading line also lands in the
  `location_scene` reverse-index row — without this the column was set but four
  readers in `core/db.py` stayed blind.

**Contract changes.**

- `scene_script.parse_heading_line(line)` is new: a heading line →
  `{int_ext, location, place, time_of_day, forced_heading, interior, exterior}`
  or `None`. `location` is the NAME. `app.stats._parse_scene_location` is gone.
- Import of a scene note: a leading `## Content` heading line no longer reaches
  the database. New refusals: unregistered location in the line; a forced
  heading combined with `int_ext` / `place` / `time_of_day`.
- Export: unchanged.

**Verification.**

- Gate: import → export → import on the fixture is **byte-stable** (probe over
  every `.md` in the project, both passes identical).
- Import probe against real notes: a hand-written `INT. THE KITCHEN - PANTRY -
  NIGHT` line yields `int_ext=INT.`, `place=PANTRY`, `time_of_day=NIGHT`,
  `location_id=the-kitchen`, the `location_scene` relation, and Content
  `Rain.`; a note carrying the fields keeps them and loses the duplicate line;
  `.SNIPER SCOPE POV` yields `forced_heading` and no composed fields; a
  body-only note is untouched; an unregistered location is refused with the
  message above.
- Parser parity: 22/22 headings match the deleted `app.stats` parser.
- Full suite: **1297 passed, 2 failed** — identical to the Phase 6 baseline
  (`test_no_hermes_imports`, `task_30/test_skill_references`; both fail on the
  stashed base).

**Findings, not fixed here.**

- `fountain_lexer.parse_location` / `parse_location_information` and
  `screenplay.LOCATION_RE` are still the duplicate parsers the Cleanup list
  retires; `parse_heading_line` is now the one stats and import share.
- The live project still carries the retired `heading:` frontmatter key, so it
  cannot import until Phase 9's one-off migration. After that migration its
  Content heading lines will canonicalise on the next import.

---

## Phase 8 brief — dashboard readers

**Short summary.** Every reader of the retired `extra.heading` now derives the
line from the fields. `core/db.py` composes one `scene_headings` map per scene —
the same `scene_heading` composer the assembled screenplay uses, with the
location slug resolved to its name — and uses it for the scene list and the
character / location scene refs, so all three agree. `core/manual_structure.py`
composes the reorder tree's `heading` from the fields; its scene query now joins
the location name. `core/drafts.py`'s create label falls back to the composed
heading when a scene carries neither a name nor a title.
`tools/story_retrieve.py` derives a location's computed `places` for the agent's
read — the same derivation as the dashboard payload.
`core/manual_entities.py` was already correct (fixed in Phase 2).

**Deviations.**

- **`core/manual_entities.py:468` was already done.** Phase 2 replaced its
  `extra.heading` read with `scene_heading(...)`; verified by blame. No change.
- **The JS items needed no change.** The plan's premise was that the JS reads
  the old field; it reads `scene.heading`, which the dashboard payload now
  carries composed (`core/db.py`). Verified in jsdom against the real payload:
  the scene list renders the composed line, the scene search matches it, the
  scene panel shows it, and `core.js`'s character scene mapping resolves by id
  and heading. `web/js/views/scenes.js:62`, `panels/entity-panels.js:509` and
  `core.js:111-121` are unchanged.
- **`core.js`'s location block was fixed, though the checklist did not list it.**
  The gate names the location panel, and its scene refs were already broken: the
  block kept only bare heading strings from `loc.scenes`, but the backend sends
  `{id, title, heading}` objects, so `_scene_headings` was always `[]`. The
  location card showed no scene tags, the location panel's "Characters here" was
  empty, and `findLocation` could not resolve a heading. It now maps the refs to
  their `heading`. This is a pre-existing bug, not a regression from the
  retirement, but the gate cannot pass without it.
- **`core/drafts.py:599` is line 584.** The plan's line numbers are from the spec
  baseline; the only `fm.get("heading")` left was the create label's fallback.
- **`_scene_headings` is now a heading list, not a string filter.** The
  consumers (`locations.js:12`, `entity-panels.js:170,186`, `utils.js:12`) all
  want heading strings, so the map/filter is the whole fix.

**Contract changes.**

- The dashboard payload's `story_data.scenes[].heading` is now the composed line
  (it was `extra.heading`, then absent). `characters[].scenes[]` and
  `locations[].scenes[]` carry the same composed line.
- `manual_structure.load_tree`'s scene nodes carry the composed `heading`.
- `story_retrieve` on a location returns the computed `places` (distinct
  non-empty `place` of its scenes, sorted) when `places` is requested.
- `describe_ops`' create label falls back to the composed heading for a scene
  with neither a name nor a title.

**Verification.**

- Gate, fresh fixture DB built by import: the dashboard scene list, character
  scene refs and location scene refs all carry the composed heading; the
  structure tree carries it; a scene written with a place shows
  `INT. THE CENTRAL ROOM - PANTRY - NIGHT`, a forced heading shows
  `.SNIPER SCOPE POV`, and the parent location's `places` is `['pantry']`.
- Gate, editor round-trip: `load_scene_script` → `save_scene_script` with
  `place: cellar`, `time_of_day: DUSK` → the dashboard scene, the location scene
  ref and `places` all show `INT. THE CENTRAL ROOM - CELLAR - DUSK`.
- jsdom, the dashboard's own `core.js` / `views/scenes.js` / `views/locations.js`
  / `panels/entity-panels.js` on the real `get_dashboard_data` payload: the scene
  list renders the composed heading, the search matches it, the scene panel shows
  it, the location card shows it, and `findLocation` resolves a heading.
- `tests/dashboard_tabs_harness.js` on a clean fixture payload: all checks pass.
- Full suite: **1297 passed, 2 failed** — identical to the Phase 7 baseline
  (`test_no_hermes_imports`, `task_30/test_skill_references`; both fail on the
  stashed base).

**Findings, not fixed here.**

- `showLocationPanel` computes a `scenes` chip list (`entity-panels.js:171-181`)
  and never renders it — dead code, and the reason the location panel shows no
  scene headings of its own. Removing it is a UI change beyond this phase.
- `docs/Dashboard inventory/0.4.4` still says a scene's `heading` comes "from
  `extra`" and describes `_scene_headings` as a string filter in `utils.js`; both
  are stale.

---

## Phase 9 brief — fixture + migration

**Short summary.** Item 1 was already done in Phase 1; Phase 9 re-ran its gate
against a freshly built DB (import succeeds, 3 scenes, three composed headings).
Item 2's deliverable is `tasks/task_38/migrate_live_headings.py`, a task-local
one-off in the same convention as `tasks/task_31/rename_plot_roles.py`: it
replaces each scene's `heading:` frontmatter line with `int_ext:` +
`place: ""` (or `forced_heading:`), derived through the app's own
`scene_script.parse_heading_line` — no second parser. `location` and
`time_of_day` are left alone; the retired free-text heading is only the source
of the two missing fields. Verified end-to-end on a scratch copy of the live
project: migrate → `story_import` succeeds → 6 scenes assemble with headings.
Backups taken before anything was touched: `.story/story_20261113_225055.db`
(via `core.db.backup_database`, WAL-safe) and
`.story/backups/pre-task38-heading-migration-scenes/`. The live project was then
migrated and its DB rebuilt — 6 scenes, 6 composed headings; the vault holds no
`heading:` key any more.

**Deviations.**

- Item 1 landed in Phase 1; only its gate was re-verified here.
- The script makes a surgical single-line edit instead of a frontmatter
  round-trip dump, so every other byte of the note is untouched.
- Existing structured fields win: a note already carrying `int_ext`/`place` keeps
  them and only loses `heading`.
- Removing `heading:` is what unblocks import — `_extra_for` refuses unknown
  scene fields, so the notes could not be imported until it was gone.
- **The live project was migrated and its DB rebuilt.** The plan assigns this
  migration, the user asked for the DB backup ahead of it, and the `dry_run`
  reported `would_be_destroyed: []`. Two backups exist:
  `.story/story_20261113_225055.db` (taken by hand via `core.db.backup_database`)
  and `.story/story_20261113_225534.db` (the importer's own), plus the markdown
  snapshot `.story/backups/pre-task38-heading-migration-scenes/`.

**Contract changes.** None — no app code changed in this phase.

**Verification.**

- Fixture gate: fresh copy → import → `screenplay_scene_headings` = 3
  (`INT. THE CENTRAL ROOM - DAY`, `… - NIGHT`, `EXT. THE GARDEN - DAY`), and
  `get_screenplay_text` renders them above the bodies.
- Live-project migration on a scratch copy: 6/6 scenes migrated, import success,
  6 headings composed (`EXT. THE GARDEN (DREAM) - DAY`, …); no `heading:` key
  survives; the importer strips the Content lines from the database.
- **Live project after `--apply` + import:** 6 scenes, `screenplay_scene_headings`
  = 6 in sequence order, the dashboard scene list carries the same six lines,
  `get_screenplay_text` renders each heading above its body, no `heading:` key
  remains anywhere in the vault (only in the backup snapshot), and no stored
  `extra` still carries `"heading"`.
- Script dry run against the live project (read-only): 6 scenes, all parsed.
- No app or test file changed, so the suite baseline is untouched (1297 passed,
  2 failed — the two pre-existing failures).

**Open question for the user** (not blocking this phase): the vault notes keep
their `## Content` heading line — see the last finding below.

**Resolved after the brief:** the user confirmed the vault notes are not
needed while the database exists. Verified: nothing outside
`tools/story_import.py` / `tools/story_export.py` reads the vault markdown, so
the leftover Content lines cost nothing and **no export is run**.

**Findings, not fixed here.**

- Three pre-existing data discrepancies surface once the heading composes from
  the linked location:
  - `The Core - Day` — heading said `THE CORE`, linked location is `the-garden`
    ("The Garden") → composes as `EXT. THE GARDEN - DAY`.
  - `Garden Dream` — linked location `the-garden-dream` ("The Garden (dream)") →
    `EXT. THE GARDEN (DREAM) - DAY` (was `THE GARDEN`).
  - `The Door Closes` — FM `heading` said `LATER`; the declared `time_of_day:
    DAY` and the Content line both say `DAY` → `INT. THE CENTRAL ROOM - DAY`.

  These are inherent to composing from the linked entity; resolving them means
  editing the notes' location links or registering a new location, which is
  outside this phase.
- The vault notes keep their `## Content` heading line after import (the
  importer strips it from the database only). Harmless: nothing outside
  `tools/story_import.py` / `tools/story_export.py` reads the vault markdown, and
  re-import is idempotent. The user does not need the notes while the database
  exists, so no export is run.

---

## Phase 9 addendum — scene facts edited in the form (user-approved)

**Change.** The scene form edits the cast and where the scene happens:
`characters` (reflist), `location` (ref) and `place` (text) moved onto the
Fields tab, between `scene_objective` and `no_cast`. `SCRIPT_FIELDS` shrank to
the writing-time trio `int_ext`, `time_of_day`, `forced_heading`; the Script tab
and its read-only listing are gone (`script_link` dropped, `scriptHtml()`,
`goScript()` and the `open-script` action deleted). No capability is lost — the
scene panel already has "Open script" / "Write script"
(`web/js/panels/entity-panels.js:434`). Both surfaces write the same entity
fields, so they cannot drift: the editor reads them back through
`load_scene_script`.

**Why.** Cast, location and place are facts about the scene, settable when it is
created; INT/EXT and the time belong to writing the script. The old Script tab
listed those facts read-only and pointed elsewhere, which was a dead end rather
than an editor.

**Deviations.**

- `location` and `place` render without the "Scene heading" group header
  (`UNGROUPED_IN_FORM`): the form shows only half that group, and a header over
  half a heading misleads. The schema `group` keys are untouched, so
  `story_describe` still teaches the agent the whole model.
- `place` is a plain text input here. The parent location's `places` suggestions
  live in the script editor; wiring them into the form would mean feeding the
  dashboard payload into the form, which this change does not do.
- A client posting `int_ext` / `time_of_day` / `forced_heading` to the form is
  still discarded server-side (`manual_entities._clean`), so the script editor
  stays the only writer of the composed heading's remaining segments.
- Creating a scene with a location and no `int_ext` was already allowed and
  still is: the write boundary requires a heading only when Content is written.

**Contract changes.**

- The scene form spec exposes `characters` / `location` / `place` as editable
  (`reflist` / `ref` / `text`) and no longer carries `script_link`.
- `_clean("scene", …)` now accepts those three keys instead of discarding them.

**Verification.**

- Form spec: order is title, sequence_id, status, one_sentence, scene_objective,
  characters, location, place, no_cast, dramatic_role, plot_roles; the trio
  stays `linked`; `script_link` absent.
- Real writes: `_clean` accepts cast/location/place and still drops the trio;
  create + read-back carries all three.
- Two-way sync through the shipped paths: form-set cast/location/place appear in
  `load_scene_script` (cast `['kael']`, location `the-central-room`, place
  `pantry`); a script save composes `INT. THE CENTRAL ROOM - PANTRY - NIGHT` and
  keeps the cast; a later form edit to `location=the-garden`, `place=''` shows in
  the editor immediately as `INT. THE GARDEN - NIGHT`.
- `tests/test_manual_structure.py::TestSpec::test_scene` updated to the new
  shape; focused suites pass. Full suite: **1297 passed, 2 failed** — the same
  two failures every prior phase recorded (`test_no_hermes_imports`,
  `tasks/task_30/test_skill_references`, both failing on the stashed base).
