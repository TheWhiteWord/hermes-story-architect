# Task 27 — Implementation plan: two value tracks

> **REVISION 2 (after phases 1–4 landed).** `shift` and `y` are **removed from
> `project`, `act` and `sequence`**. They now exist only on `scene` and
> `arc_beat`. See [Revision 2](#revision-2--shift-and-y-are-scene-and-beat-only)
> for the reasoning and the exact list of things to undo. Everything above this
> line is the original plan and is superseded where they disagree.

**Status:** phases 1–4 implemented (665 passing), phases 5–7 outstanding.
Design of record: `value-system-issue.md` (same folder). Read that first — this
file only says *how*, in what order, and what to check.

**Rule for every phase:** verify an assumption against the code before relying
on it. Every "Assumption to verify" below is a claim made *before* looking, so
that being wrong is a finding rather than a surprise in phase 5.

---

## Target field table

| scope | value word | charge | reading | curve |
|---|---|---|---|---|
| `project` | `story_value` | `story_value_at_open` / `_close` | `shift` | `y` |
| `act` / `sequence` / `scene` | *inherited from project* | `value_at_open` / `_close` | `shift` | `y` |
| `character` | `character_value` | `character_value_at_open` / `_close` | — | — |
| `arc_beat` | *inherited from character* | `character_value_at_open` / `_close` | `shift` | `y` |

The value word is stated once per track and inherited downward. Charge, `shift`
and `y` are per-entity everywhere and never inherited — that is where the story
turns.

---

## What the code sweep found (read this before the phases)

Four things the design did not anticipate. Each is a phase or a checklist item.

1. **`_PROJECT_DEFAULTS` in `core/db.py:154` is a hand-copied duplicate of the
   project schema defaults**, and `:305` uses it to decide what to `_omit` from
   the base map. Rename the schema and this dict still holds the old keys, so
   every renamed project field is emitted as if it were filled — the
   "present but always the default" lie, in a new place. **It is also a third
   copy of the defaults, which is the hand-written-list drift this repo has
   already been bitten by three times.** Fix it in phase 1 or notice it in
   phase 4.

2. **`docs/html_ui_dashboard/story-dashboard .html` is a git-tracked *build
   output* containing `arc_value` 3×** (a 176 KB copy of the dashboard, plus
   three earlier variants from other tools). Nothing generates it and nothing
   reads it at runtime. It will keep the old field names forever unless it is
   deleted or refreshed. **Needs a user decision — see Open Questions.**

3. **`src/dashboard/js/data-load.js:27` hardcodes the old project keys**
   (`value`, `value_at_open`, `value_at_close`) inside `loadSampleData`, which
   is described in the file as "in the REAL backend schema — exercises the
   normaliser". So a stale sample is a *test surface*, not decoration: it
   exercises `core.js:26 normalise` and will quietly feed a renamed field.

4. **`view='story_value'` already returns the project's value under the key
   `story_value`** (`tools/story_load.py`, project branch) while the field is
   called `value`. The view and the fields disagree *today*. After the rename
   they agree — worth asserting, because the agreement is the point.

**Good news, also verified:** three of the surfaces most likely to drift are
already schema-driven and will follow the rename for free —
`unfilled_fields` (`core/entity.py:183`, iterates `ENTITY_SCHEMAS`),
`tests/test_field_coverage.py` (iterates `ENTITY_SCHEMAS` for every field of
every type), and `tools/story_export.py` `_frontmatter_for` (merges `extra`,
hardcodes no value key). Do not add a hand-maintained list for any of these.

---

## Phase 1 — Schema and validators

No reads, no views, no data. The data shape only.

- [x] `core/constants.py` `ENTITY_SCHEMAS["project"]`: `value` → `story_value`,
      `value_at_open` → `story_value_at_open`, `value_at_close` →
      `story_value_at_close`
- [x] `ENTITY_SCHEMAS["character"]`: `arc_value*` → `character_value*`
- [x] `ENTITY_SCHEMAS["arc_beat"]`: add `character_value_at_open` /
      `character_value_at_close` (`optional: True`, default `"Not set"`)
- [x] `ENTITY_SCHEMAS["act" / "sequence" / "scene"]`: **remove** the `value`
      key; **add** `shift` (string, default `"Shift not recorded"`) and `y`
      (number, default `0.0`)
- [x] `ENTITY_SCHEMAS["project"]`: add `shift` and `y` (same shape)
- [x] `core/db.py` `_PROJECT_DEFAULTS`: derived as `ENTITY_SCHEMAS["project"]`
      minus `_PROJECT_TITLE_PAGE_FIELDS` — an explicit exclusion set, so the
      subset stays deliberate and the two files can no longer disagree on a
      value. The `get_project_summary` payload builder now iterates
      `_PROJECT_DEFAULTS` instead of hand-listing the same 12 keys, so
      coverage is structural rather than asserted after the fact.
- [x] `core/entity.py` validators: retarget `character` enum checks to
      `character_value_at_open` / `_close`; add the same two for `arc_beat`;
      add `_validate_numeric(frontmatter, "y", …)` and the −1.0…+1.0 range
      check to `act` / `sequence` / `scene` / `project`
- [x] `REQUIRED_FIELDS`: **unchanged.** `arc_beat` already requires `shift` and
      `y`; the new charge fields are optional. Do not add them.
- [x] **No continuity check of any kind.** Both candidates were tried and
      rejected — the cross-scene rule and the arc-endpoint rule. See the
      Continuity section for why, and for the `no_cast`-on-beat proposal that was
      also declined as already expressible. Do not build a sibling-aware reader
      for this purpose.

**Assumptions to verify before editing:**

### Field descriptions are the instruction — write them as such

**This is the single highest-leverage change in the phase, and it is not
cosmetic.** `story_describe` returns `meta["description"]` **verbatim**
(`tools/story_describe.py:31`), so these strings are the only instruction the
model gets about what to write. Today they are:

```
scene  value_at_open  'One of: positive, negative, mixed, ironic'    (41 chars)
arc_beat y            'Value charge (-1.0 to +1.0)'                   (27 chars)
```

The first says *which words are legal* and not *which value is being charged* —
so a model filling a scene cannot tell whether to write the story's charge or a
character's. **That gap is the entire bug, expressed as a missing sentence.**
The rename changes which key holds the value; the description is what stops the
model putting the wrong charge in the right key.

Each track's fields describe **their own** derivation. No cross-references
between tracks — the model must never be told to consult the other one, because
the correspondence is a writing process, not a fact (see
`value-system-issue.md` decision 3). Story-side fields describe the story value;
character-side fields describe the character's value; neither mentions the other.

**Story side** — `project` (`story_value*`) and `act`/`sequence`/`scene`
(`value_at_open`/`_close`, `shift`, `y`):

| field | description |
|---|---|
| `story_value` | "The story's thematic value (e.g. 'Trust'). Stated once, here; scenes inherit it." |
| `story_value_at_open` | "Charge on the story value as the story opens. One of: positive, negative, mixed, ironic." |
| `story_value_at_close` | "Charge on the story value as the story closes. One of: positive, negative, mixed, ironic." |
| `value_at_open` (scene/seq/act) | "Charge on the story value entering this scene. One of: positive, negative, mixed, ironic." |
| `value_at_close` (scene/seq/act) | "Charge on the story value leaving this scene. One of: positive, negative, mixed, ironic." |
| `shift` | "How the story value turns here, in the story's language (e.g. 'trust → suspicion')." |
| `y` | "Ending charge on the story value after this scene's turn, −1.0 to +1.0. The point the story-value curve passes through." |

**Character side** — `character` (`character_value*`) and `arc_beat`
(`character_value_at_open`/`_close`, `shift`, `y`):

| field | description |
|---|---|
| `character_value` | "The value this character's arc explores (e.g. 'Freedom'). May differ from the story's." |
| `character_value_at_open` (character) | "Charge on this character's value where their arc begins. One of: positive, negative, mixed, ironic." |
| `character_value_at_close` (character) | "Charge on this character's value where their arc ends. One of: positive, negative, mixed, ironic." |
| `character_value_at_open` (beat) | "Charge on this character's value entering this beat. One of: positive, negative, mixed, ironic." |
| `character_value_at_close` (beat) | "Charge on this character's value leaving this beat. One of: positive, negative, mixed, ironic." |
| `shift` (beat) | "How this character's value turns at this beat, in dramatic language (e.g. 'suspicious doubt → active defiance')." |
| `y` (beat) | "Ending charge on this character's value after this beat's turn, −1.0 to +1.0. The point the arc curve passes through." |

Note the deliberate overlaps, which are **not** redundancy:

- `y` is defined **identically** for both tracks, because it means the same
  thing in both: the ending charge, the point a curve passes through. The model
  must not learn two rules for one number. The *scope* is carried by the key it
  sits on, which is the whole design.
- `character_value` may differ from the story's — stated once, on the character
  field, as permission rather than instruction. It does not say *how* they
  relate, because that is the judgement the plugin refuses to make.
- The `shift` descriptions differ **only** in whose value turns ("the story
  value" / "this character's value"). Same shape, same example format, so the
  model learns one pattern.

- [x] Every description above lands verbatim in `ENTITY_SCHEMAS`
- [x] **Test that pins the wording, not just the key names.** A rename that
      leaves `value_at_open` reading "One of: positive, negative, mixed,
      ironic" passes every structural test and still ships the bug, because the
      model is the only consumer and no assertion can see it. Assert each
      value-field description names the value it charges — i.e. contains
      "story value" or "this character's value" — and that `y` mentions
      "Ending" and "curve". That is the cheapest possible guard against
      regressing to a bare enum list. → `TestValueSchema` in `tests/test_core.py`
      (31 tests: 17 charge descriptions, 5 `y`, 5 `shift`, plus shape/coverage).
- [x] The test must fail if a description is shortened to a bare enum, and pass
      only when the derivation is stated. Keep it to a substring check per field
      — a golden-string snapshot would break on every rewording and train people
      to update the snapshot instead of the meaning. → **verified by experiment**:
      reverting `scene.value_at_open` and `scene.y` to their old wording fails
      3 of the 31; restoring the wording passes all 31.

- [x] `_omit` drops keys *still at their schema default*, so a `shift` default
      of `"Shift not recorded"` disappears from the base map rather than
      appearing as noise on all 7 scenes. Confirm in `core/entity.py`.
      → **Confirmed in code**: `_omit` compares each value against the default
      dict its *caller* passes, so the story-container builders must list
      `shift`/`y` defaults to drop them. The mechanism is unchanged; listing
      them is phase 3's edit.
- [x] ~~`unfilled_fields` skips fields at their default, so an unfilled `y` is
      not reported as a gap~~ — **VERIFIED, and HALF WRONG. Corrected below.**
      - `y` is a `number`, and `unfilled_fields` skips numbers unconditionally
        (`core/entity.py:205`). So an unfilled `y` is never a gap row. ✅
      - `shift` is **not** skipped. The verification quoted here was run before
        `shift` existed on these types, so it had nothing to observe. Now that
        it is added, an unfilled `shift` **is** a gap row on all five types —
        exactly like `action` and `arc_type`, which use the same
        placeholder-default pattern. This is correct behaviour, not a defect:
        a scene with no recorded shift is a real gap in the story-value track.
        Asserted in `test_unfilled_fields_curve_fields`.
      - The gap map did list `value`, `value_at_open`, `value_at_close` for
        scenes and acts, so **removing `value` removes one gap row** per
        container, and `shift` adds one. Net zero for containers; still worth
        asserting in phase 4.
- [x] ~~No hand-written list of project fields exists outside
      `_PROJECT_DEFAULTS` and `ENTITY_SCHEMAS`~~ — **VERIFIED.** Only those
      two, plus the tools' *readers* (phase 3/4). `story_export` hardcodes no
      value key; `unfilled_fields` and `test_field_coverage.py` iterate the
      schema.

**Finding — the two default sources agree today, exactly.** Diffed
`_PROJECT_DEFAULTS` against `ENTITY_SCHEMAS["project"]`:

```
in dict, not in schema : []                     ← nothing extra to lose
in schema, not in dict : author, contact, credit, draft, draft_date,
                         name, screenplay_title, status
value mismatches on shared keys : none
```

The 8 extra schema keys are the **title-page block** (plus `name`/`status`).
So the two sources are not two opinions about one thing — the dict is a
*deliberate subset*: the fields worth omitting from a payload, excluding the
screenplay-only ones. That is the reason it exists, and it is a real reason, so
**it is not simply deleted.** See the resolution below.

**Edge to pin, not a live bug:** the filter at `db.py:305` is
`v != _PROJECT_DEFAULTS.get(k)`. A key present in the `project` dict but
*absent* from `_PROJECT_DEFAULTS` would make `.get()` return `None`, and
`v != None` is always true, so the key would be emitted **always**, unfilled or
not. → **Closed by construction, not by assertion.** The payload dict is now
built by iterating `_PROJECT_DEFAULTS`, so a key cannot be in the payload
without being in the defaults. The residual assertion that the *exclusion set*
is still deliberate (defaults ∪ title-page == the whole project schema, no
overlap, no value drift) is
`test_project_defaults_cover_the_whole_project_schema`.

**Check:** `python -m pytest tests/test_core.py tests/test_arcs.py -q` — expect
the schema-shape tests to pass and the *value-reading* tests to fail (they are
phase 4's job). Record which fail; a failure outside that set is a finding.

**Check result — 122 passed, 0 failed.** No value-reading test lives in these
two files, so the expectation of "reading tests fail here" did not hold; the
first real reading failures appear in the full suite below. Five tests did
fail and all five were schema-shape assertions on removed/renamed keys, i.e.
phase 1's own job, not a finding:

- `test_arcs.py::test_character_schema_has_arc_fields` — asserted `arc_value`.
- `test_core.py::TestUnfilledFields::{test_unfilled_fields_scene_location,
  test_unfilled_fields_skips_status, test_unfilled_fields_sequence,
  test_unfilled_fields_act}` — passed `"value"` in the extra dict and asserted
  it came back. Retargeted to `value_at_open`.

**Full suite after phase 1: 655 passed, 2 failed** — both expected downstream
work, both in phase 3/4's scope:

- `test_value_ownership.py::test_base_map_still_carries_the_project_value` —
  asserts `value`/`value_at_open`/`value_at_close` in the project payload. The
  keys are now `story_value*`; repointing it is phase 4's listed edit.
- `test_story_load_views.py::TestUnfilledView::test_answers_what_next` — the
  top gap for a character is now `character_value_at_close` (the fixture notes
  still carry the pre-rename `arc_value_at_close`, so the new field reads as
  unfilled). Resolves when phase 2 migrates the fixture.

Two further stale hand-written `"value"` references were found and fixed here
rather than deferred, because they name a field that no longer exists and both
broke schema-driven tests: `tests/test_field_coverage.py` `_sample_value`
(unreachable branch) and `test_edit_all_field_types`'s scene edit payload.

---

## Phase 2 — Hand migration of the data (once, by hand, no migration function)

Plugin is undeployed; every project is a test project. No `_migrate_*`, no
dual-key reader, no shim. Readers accept exactly one key name so a stale key
fails loudly.

- [x] Back up each DB: `cp story.db story.db.pre-storyvalue-migration`
      (the `pre-valuekey-migration` backup is from the *earlier* rename and does
      not cover this one) → done for both the live project and the fixture.
      (`*.db` is gitignored, but the suffixed backup is not matched by that
      pattern, so the fixture's copy shows as untracked — it is a local
      artifact, not something to commit.)
- [x] Live project `/media/theww/AI/TWW/hermes-story-architect/projects/browser-verification-test`:
  - [x] `project.md` + `.story/index.yaml`: `value*` → `story_value*`
  - [x] `characters/kael.md`, `characters/mira.md` + `index.yaml`:
        `arc_value*` → `character_value*`
  - [x] `acts/`, `sequences/`, `scenes/`: **remove** the `value:` line
        (garden-day, garden-dream on `Hope`; the-door-closes on `Freedom` —
        this is symptom 3 resolving, not a loss to recover from)
  - [x] record `Hope` as Mira's `character_value` → **NOT DONE, on the user's
        decision.** Mira already had `arc_value: Trust` and her two beats read
        `fear → tentative trust` → `tentative trust → grounded faith`: a
        coherent Trust arc. `Hope` came only from the two garden scenes'
        `value:` key — the field being deleted as symptom 3. Asked; the user
        chose **keep `Trust`**, straight rename only, and let the garden
        `Hope` be dropped. So Mira is `character_value: Trust`.
- [x] Test fixture `tests/fixtures/save-the-children/` — the **same** edits:
      project.md, `characters/dr-elena-voss.md` (`character_value: Redemption`),
      act-1.md, seq-discovery.md, 3 scenes, and `.story/index.yaml` (37 hits)
- [x] Then re-import each project and read the values back. A rename that looks
      correct in the DB proves nothing until an import cycle has run over it,
      because import rebuilds the DB from Markdown. → **both cycles run and
      verified by reading the DB out**:
      - live: `project {story_value: Trust, open: positive, close: ironic}`,
        `kael {character_value: Freedom}`, `mira {character_value: Trust}`,
        all 6 scenes / 1 act / 1 sequence carry `value_at_open`/`_close` and
        **no** `value` key.
      - fixture: same shape, `dr-elena-voss {character_value: Redemption}`.

**Assumptions to verify:**
- [x] `story_import` does not resurrect a removed `value:` line from a stale
      `index.yaml`. Delete from **both**, not one. → **Verified, and the
      premise is stronger than stated: no code reads `index.yaml` at all.**
      `story_import._import_all` walks `project.md` plus the entity folders and
      `memory.md`; a tree-wide grep for `index.yaml` outside `tests/` and
      `skills/` returns nothing. So `index.yaml` cannot resurrect anything — it
      is a hand-maintained graph, not an import input. It was migrated anyway
      (it is the project graph a human and the model read, and leaving 37 stale
      keys in it would be a lie), but the reason is accuracy, not correctness
      of the import.
- [x] A scene note whose only removed key is `value` still imports cleanly —
      check `_extra_for` does not require the key to exist. → **Verified.**
      `_extra_for` (`tools/story_import.py:419`) iterates what is *present* in
      the frontmatter against a per-type skip set; it never requires a key. The
      six live scenes and three fixture scenes imported cleanly without it.

**Check:** grep the whole tree including `tests/fixtures/` for `arc_value` and
`value_at_open` — every remaining hit must be a *new-name* consumer, not an old
key. Then `python -m pytest tests/ -q` and triage: every failure here is either
phase 3/4 work queued early or a migration miss. Fix the misses now.

**Check result — 654 passed, 3 failed. No migration miss.**
Grep over the data tree (`.md` + `.yaml`, both projects) for `arc_value` and a
bare `value:` key: **zero hits**. What remains is all phase 3/4 consumer code
(`core/db.py` read paths, `src/dashboard/js/*`), phase 6 skill prose, historical
`tasks/task_1x*/` documents, and the excluded `docs/html_ui_dashboard/`
artifacts — no data, no test.

The three failures, all phase 3/4 work queued early:
- `test_value_ownership.py::test_base_map_still_carries_the_project_value` —
  phase 4's listed repoint.
- `test_story_load_views.py::TestStoryValueView::test_returns_value_at_project_and_act_level`
  — phase 4's `_view_story_value` work; it surfaced only after the fixture
  stopped feeding the view a container `value` key.
- `test_story_load_views.py::TestUnfilledView::test_answers_what_next` — was
  failing after phase 1 and is **now fixed by this phase's fixture migration**,
  as predicted: the character's top gap is `character_value_at_close` precisely
  because the fixture still held the pre-rename key.

One fix made here rather than deferred, because it had gone **vacuous** rather
than merely stale: `tests/test_arcs.py::test_validate_character_arc_value_enums`
fed `arc_value_at_open` to the validator, which after the rename simply ignores
that key — so it asserted "no warnings" on input nothing reads. Renamed to
`test_validate_character_value_enums`, repointed, and given a negative case
(`sideways` must warn) so it can no longer pass by being ignored.

`tests/test_soft_delete.py:183` also names `arc_value`, and is left alone: it is
phase 4's listed edit.

---

## Phase 3 — Read paths (base map + dashboard data)

- [x] `core/db.py` `_build_character` (`:519`): `arc_value*` → `character_value*`
- [x] `core/db.py` `_omit` default set for the character (`:524`): retarget the
      keys, or the renamed fields are always emitted
- [x] `core/db.py` project branch (`:296`): `value*` → `story_value*` — **already
      done by phase 1**; the payload builder iterates `_PROJECT_DEFAULTS`, so
      the renamed keys followed for free. No edit, verified in the pin.
- [x] `core/db.py` `get_character_arcs` (`:726`) and the two dashboard beat
      builders (`:1036`, `:1070`): surface `character_value_at_open` / `_close`
      and the new `shift` / `y` on story containers
- [x] `src/dashboard/js/`: `char.arc_value` → `char.character_value` in
      `arc-graph.js:187`, `network.js:135`, `panel-manager.js:28`
- [x] `src/dashboard/js/data-load.js:27` sample: `value*` → `story_value*`
- [x] `src/dashboard/js/views/story.js:40-42` reads `p.value` /
      `p.value_at_open` / `p.value_at_close` — retarget. (The plan cited `:2`;
      the reads are at `:40-42`.)

**Extra, not in the checklist** — `panels/entity-panels.js:459` read
`scene.value` / `scene.value_open` / `scene.value_close`. The last two were
renamed in the *earlier* `value_open` → `value_at_open` task, so this line has
been dead code for a task, silently rendering no value arc on any scene panel.
Repointed to `value_at_open` / `_close`. It is in scope: it is a read path for a
renamed key, and fixing it was cheaper than deferring a line that names three
fields no longer in existence.

**Assumptions to verify:**
- [x] The dashboard's character payload comes from `get_dashboard_data`, so
      phase 3 is a *different* function from `get_project_summary`. Renaming one
      and not the other is the classic split-brain. Grep both builders for every
      renamed key and confirm each hit is in the right function.
      → **Verified, and the split-brain was real in the other direction.**
      `get_project_summary` and `get_dashboard_data` are genuinely separate
      builders and both had `arc_value` hits, both now retargeted. The
      dashboard builder needed no *new* work for the story side: `_entity_dict`
      merges every `extra` key to top level, so scenes/acts/sequences pick up
      `shift` and `y` the moment they are written, with no hand-list. Verified
      by reading `get_dashboard_data` output, not by reading the code.
- [x] The base map's hash does **not** change from adding `shift`/`y` to scene /
      act / sequence, because `_omit` drops defaults. If it does, scenes with a
      filled `shift` now cost base-view tokens — pin the growth rate, do not
      assume it. → **Confirmed: it does not.** Pinned before and after; the only
      movement is the intended one (below).
- [x] `data-load.js` `loadSampleData` is genuinely exercised by a test
      (`tests/test_story_dashboard_integration.py` mentions the normaliser).
      If nothing loads it, the fix is deleting the sample, not renaming it.
      → **Half wrong.** `test_story_dashboard_integration.py:153` only lists the
      *string* `"loadSampleData"` among handler names for a `DASH.` prefix
      check; it never calls it and never feeds it to `normalise`. So the sample
      is not a test surface. It is, however, a live user-facing button
      (`index.html:44`, "Preview with sample data"), so it was **renamed, not
      deleted** — deleting a working feature to satisfy an assumption the
      assumption got wrong is the wrong trade.

**Check:** pin the base view byte-identically (hash before/after) *except* for
the intended project-key rename; assert the top-level key set. If the hash moves
for any other reason, stop and find out why.

**Check result — the hash moved, and only for the intended reason.**

| | before | after |
|---|---|---|
| sha256 | `e304ced1…` | `ba6b7915…` |
| bytes | 4716 | 4828 (+112) |
| chars/scene | 1572.0 | 1609.3 (+2.4%) |

The project-key rename is **not** in this delta — it landed in phase 1, so
"before" already reads `story_value*`. The +112 bytes are the three
`character_value*` keys on the one fixture character that has them
(`dr-elena-voss`). That is the rename *fixing* a silent data loss: before this
phase the base map read `arc_value` from a DB that no longer stores it, so it
fell through to the schema default and `_omit` dropped the key — the character
who carries the fixture's only arc had **no value in the base map at all**. The
growth is the payload becoming truthful, not a new cost.

Scene/act/sequence key sets are byte-identical before and after, which is the
`shift`/`y` claim above confirmed rather than assumed: `_omit` drops them at
their defaults, so an unfilled curve field costs nothing.

**Full suite: 654 passed, 3 failed** — the same three as phase 2, all phase 4's
listed edits. No phase 3 regression.

---

## Phase 4 — Views

- [x] `tools/story_load.py` `_view_story_value`: scene/sequence/act branches
      read `value*` — retargeted to `value_at_open`/`_close` (unchanged names)
      and **`shift` + `y` added**; the `value` key is gone from the payload.
      All three branches were byte-identical dict literals, so they now share
      one `_value_fields(extra)` helper — three copies of a four-field dict is
      how they drifted apart in the first place.
- [x] project branch: `story_value` key already matched the new field name —
      **asserted, not assumed**, in `test_view_story_value_key_is_the_schema_field`
- [x] `_view_arc`: beats gain `character_value_at_open` / `_close` — **satisfied
      by phase 3's `get_character_arcs` edit**, no change needed here. Verified
      by reading a real arc view, not by reading the diff.
- [x] `view='unfilled'`: the drift row. `core/db.py` `get_value_drift` + a
      `value_drift` key in the view. Reports `{id, type, descendants_with_charges}`
      and nothing else — it states a *missing* field, never proposes a value.
- [x] `tests/test_value_ownership.py` — repointed, and added:
  - [x] no container payload contains a `value` key
  - [x] the project payload's `story_value` equals the schema field (view ↔
        schema agreement asserted against `ENTITY_SCHEMAS` directly)
  - [x] **at least one** container carries a real `shift` and a real `y`
        (`assert any(...)`, on containers *and* on scenes) — plus a re-measured
        growth assertion
- [x] `tests/test_soft_delete.py:183` asserts `"arc_value"` in a fields list —
      repointed to `character_value`
- [x] `tests/test_field_coverage.py` — schema-driven, self-adjusted. Confirmed
      by running it (24 passed), not assumed.

**Assumption to verify:** `story_value` view's scene list is asserted
key-for-key against the DB (`test_value_ownership.py:87`) — adding two fields
per scene changes the payload size, so the **growth** assertion (chars/scene
ceiling) must be re-measured, not just re-run. → **Done, and the first
measurement failed.** See below.

### Growth: measured twice, because the first number was wrong

The plan asked for a re-measure. Measuring produced a result nobody expected:

| | chars/scene |
|---|---|
| base view (for comparison) | 20.0 |
| `story_value`, unfilled scene, first attempt | **124.75** |
| `story_value`, unfilled scene, after the fix below | 106.75 |
| `story_value`, fully recorded scene (the real ceiling) | 174.75 |

**The first 124.75 was a defect, not a cost.** The view was emitting the schema
*placeholder* `"Shift not recorded"` on every unfilled scene, plus `y: 0.0` —
40 scenes would have cost ~800 chars of noise that reads as if the shift had
been written down. That is the same "present but always the default" lie the
plan flags in `_PROJECT_DEFAULTS`, reappearing in a new place. `_value_fields`
now applies the same rule every builder in `core/db.py` follows via `_omit`: a
field still at its default is reported as the type's empty, not its placeholder.

**The 174.75 ceiling is inherent and accepted.** A recorded scene costs ~175
chars because the view's entire job is to carry four value fields per container.
The base view's per-scene budget (20) does not apply — the value view is opt-in
and filterable by act, which is the trade the views exist to make. The test
ceiling is set at 200: loose on purpose, because it is a leak alarm, not a
budget. What it catches is a field added twice or a placeholder reintroduced.

**Second measurement the first one would have hidden:** a guess of 60 (written
before measuring) failed at 124.75 and would *also* have failed at the true
174.75. The number in the test is the measured one.

### Two findings while doing this

**1. A second vacuous test, same failure mode as phase 2's.**
`tests/test_core.py::test_non_event_with_empty_values_is_valid` fed
`value_open`/`value_close` to the validator — names dropped in the *earlier*
`value_open` → `value_at_open` rename, so the validator ignored them and the
test asserted "no warnings" on input nothing read. Repointed, and given a second
case (a *filled* charge on a `non-event` scene) so it can no longer pass by being
ignored. This is now the third instance of the pattern in this task; it is worth
grepping for after every rename, and the plan says so.

**2. The fixture had no `shift`/`y`, so the required assertion would have been
vacuous.** The plan's "at least one container carries a real `shift` and a real
`y`" cannot pass against a fixture where every value field is empty — it would
have passed for exactly the reason the test exists to catch. The fixture's five
story containers were given `shift` and `y` consistent with the charges they
already carried (`shift` in the story's language, `y` the ending charge, e.g.
`central-room-night` closes `positive` → `y: 0.6`).

**One extra fix, in scope:** the `view` enum description in `SCHEMA` said
`"'arc' = one character's beats"` and `"'story_value' = value arc across the
structure"` — scope-free, i.e. the exact ambiguity this task exists to remove,
in the only text the model reads for picking a view. Both now name their track
("the story's own value", "one character's arc beats").

**Full suite: 665 passed, 0 failed** (was 654 passed / 3 failed). All three
pre-existing failures resolved; +11 new tests.

### Verified against the live project, not only the fixture

A clean re-import of `browser-verification-test` (`.story/` deleted, rebuilt
from Markdown) confirms the readers survive the round trip:

- `story_value`: `Trust  positive → ironic`; every container reads its own
  charge; **no container carries a `value` key**
- **`value_drift` fires on the real symptom-2 case**:
  `seq-confrontation` is empty while its 3 scenes carry charges. `act-2` is not
  listed, correctly — its only sequence is itself uncharged, so it has no
  charged descendants. The detection works on the case that motivated it.
- `arc` view: beats carry `character_value_at_open` / `_close` (empty, since the
  live beats predate the field) alongside `shift` and `y`
- base view: 1102.5 chars/scene on a 6-scene project

**Deferred:** the live project's story containers have no `shift`/`y` and its
beats have no `character_value_at_*`. The fields are read correctly and the
unfilled view reports them, so nothing is broken — but the data does not yet
exercise them. Filling a real project's creative fields is the author's call,
not this task's.

---

## Phase 5 — Graph

- [x] `src/dashboard/js/graph/arc-graph.js`: second plot source. Scenes in
      story order are the same polyline on a different x-axis — **one graph
      engine, two sources.** No second renderer: the story series reuses
      `arcXScale`/`arcYScale`/`catmullRomPath` and the same `arc-line` class.
- [x] Tooltip: `shift` already has an element (`index.html:24`, `tt-shift`) —
      **verified, no markup added.** `showArcTooltip` reads `dataset.label`,
      `.char`, `.shift`, `.y`, and the story dots populate all four, so the
      existing tooltip renders a story point with no change to
      `index.html` or `graph.css`. Pinned by
      `test_story_points_carry_the_tooltip_data`, which reads the emitted SVG
      and was verified to fail when `data-shift` is dropped.
- [x] `arc-graph.js:77-81` sanity warnings operate on `char.arc_beats_list`;
      the story series needs its own or none. **None, and that is the decision
      rather than an omission.** "Flat arc — nothing dramatic happens" and
      ">0.8 jump, consider splitting" are judgements about a *character's*
      dramatic arc; a story value is allowed to hold steady across an act, and
      firing on that is the crying-wolf failure the rejected continuity checks
      would have caused. Pinned both ways by
      `test_story_heuristics_are_not_borrowed_from_the_character_checks` (a
      deliberately flat story line produces no warning) and
      `test_character_warnings_still_fire` (the checks were scoped, not deleted).

**Assumption to verify — RESOLVED, and it changes this phase.** The question
was whether a scene's `y` is the charge at the turn or an average across the
scene. **Decided: the ending charge, identical to a beat's `y`.** A scene
therefore plots as a curve exactly as a character arc does, which is the point
— the story value gets a readable line rather than a list of words.

What the sweep found while confirming it: that rule is **already stated for
beats and enforced nowhere**.

- `skills/story-theory/references/values.md:382` — "**The `y` value is the
  ENDING charge after this beat's shift.** If the shift is 'positive → mixed'
  and the character started at +1.0, the `y` is where they land (e.g., +0.3)."
- The schema description in `core/constants.py:181` says only "Value charge
  (-1.0 to +1.0)" — it does **not** say *ending*, and `story_describe` returns
  that description verbatim to the model.
- No test asserts it. Grepping for the semantics across `skills/`, `tests/`,
  `core/`, `tools/` returns only prose in that one skill file.

So the rule the whole graph depends on lives in a skill document while the
field the model actually reads carries a weaker description. **Fix the schema
description as part of phase 1** — this is the mechanism by which the model
learns what to write, and a scene `y` means the same thing as a beat `y`:

> "Ending value charge for this scene, after its shift (-1.0 to +1.0). The
> point the story-value curve passes through at this scene."

- [x] Same wording intent for `arc_beat.y` and the four container `y` fields, so
      `story_describe` gives the model one rule, not two.
      → **Already landed in phase 1** (the "Ending charge … the point the curve
      passes through" wording is on `scene.y` and `arc_beat.y`, pinned by
      `test_y_description_states_the_ending_charge`). The four container `y`
      fields no longer exist — revision 2 removed them. Nothing to retarget.
- [x] Add the missing test: a beat whose `shift` is `positive → mixed` and whose
      `y` is `+0.3` is consistent; the same beat with `y = -0.3` is not. Assert
      the *rule is documented in the schema description*, since that is what
      reaches the model — a test on the skill file tests nothing at runtime.
      → **Done, and the gap it found was one step further than the plan
      thought.** See "The sign convention" below: the phase-1 wording says
      *ending* charge but never says which **sign**, so `positive` and
      `-0.3` were still reconcilable. That is now stated and pinned.

**Consequence for the plot:** because every point is an *ending* charge, the
series is a polyline through scene-ending charges, and a scene with
`value_at_open = positive`, `value_at_close = negative` contributes a segment
that *drops* — the staircase reading only appears if you plot open and close
separately. Pick one when drawing: **the ending-charge curve** (one point per
scene, matching the beat graph) is the default, because it is the same engine
and the same mental model. Do not plot both without a reason — two stories on
one axis is how the current conflation started.
→ **Implemented as specified**: one point per scene, `value_at_open`/`_close`
are not plotted, and the curve is drawn first so the character arcs read on
top of it.

### The sign convention — a gap the plan did not name

The plan's test brief says a beat with `shift: positive → mixed` and
`y: +0.3` is consistent while `y: -0.3` is not. Getting to that required
answering a question the schema had not asked: **which way round?**
`positive` and `negative` are charge *words*; `y` is a *number*. Phase 1's
wording fixed *when* the charge is sampled (the ending) but not how the word
maps to the sign — so a model could write `positive` on one line and `-0.3`
on the next and satisfy every rule the schema states.

Fixed in the description, on both curve entities, identically:

> "…, -1.0 to +1.0, signed like the charge word: positive is above zero,
> negative below, mixed and ironic in between."

**No validator, and deliberately so.** Checking a charge word against a number
at runtime is a continuity check, and this task rejected both of those on the
ground that a machine cannot judge whether a charge and a number agree — it
can only be told. The rule belongs where the model reads it, and the test
asserts it is *there*, in `test_y_description_states_the_sign_convention`.

### The x-scale used to place two scenes on one pixel — FIXED

`sceneT` originally spanned each act band edge to edge
(`idxInAct / (countInAct - 1)`), so an act's last scene and the next act's
first both landed on the shared band edge: two dots stacked on one x, with the
beat positions inheriting the same collision.

Fixed by seating each scene at the **centre** of its slot within the band:

```js
return (info.actIdx + (info.idxInAct + 0.5) / info.countInAct) / actCount;
```

A band now owns `[actIdx, actIdx+1)` exclusively, so the two can never be
equal. It also subsumes the old single-scene special case (`0.5`, unchanged)
and stays monotone in `(actIdx, idxInAct)`.

Two options were rejected: a global scene index loses the act bands, which are
the point of the layout; nudging only the colliding pair is a special case that
re-breaks on the next structure.

**Re-measured on the real page** (every dot moves, so this was not assumed):

| | before | after |
|---|---|---|
| story polyline x | `42, 155, 268` | `79.7, 155, 230.3` |
| band 1 spans | 42–268 | 42–268 |
| beat dots | 3, same collision | 3, all distinct |
| scene labels | 3 | 3 |
| JS exceptions | 0 | 0 |

Dots stay inside their act band — which is more correct than before, where a
beat at an act's edge sat on the divider line itself. No `y` value changed.

**The guard needed two scenes on *both* sides of a boundary.** The first
version of `test_no_two_scenes_share_an_x` used a one-scene act in the middle,
which centres at `0.5` and never touches an edge — so it passed against the
broken code. The old `countInAct > 1 ? … : 0.5` special case is exactly what
hid the bug, and the test had to reproduce the shape that exposes it. Verified
by reverting the fix: **2 tests go red**, `test_no_two_scenes_share_an_x` and
`test_story_points_are_in_story_order`.


### What the graph does with a scene that has no `y`

Nothing. `storySeries` filters on `typeof y === 'number'`, so an unrecorded
charge is not drawn as a point at `0.0`. `0.0` is a value a writer can choose;
a missing `y` is not the same statement, and plotting it would invent a
measurement. Pinned by `test_scene_without_a_y_is_not_plotted`.

### Also changed, not in the checklist

- **The empty state no longer keys on characters alone.** It read
  `chars.length === 0` and returned, so a project mid-write — scenes charged,
  no arc designed yet — showed nothing at all despite having a story curve to
  draw. Now `chars.length === 0 && storyPts.length === 0`, and the copy says
  "No value trajectories" rather than "No arc trajectories". Pinned by
  `test_story_line_draws_without_any_character_arcs` and
  `test_no_curve_at_all_still_shows_the_empty_state`.
- **Scene x-axis labels** were emitted only for scenes carrying beats. A scene
  with a story point and no beat was an unlabelled dot on the axis. Now
  labelled if it has either. Verified on the real page: all three fixture
  scenes are labelled.
- **The inline scene→act mapping was extracted** to `DASH.scenePositions` /
  `DASH.sceneT` so the story series positions identically to the beats by
  construction rather than by a second copy of the arithmetic that could drift.


---

## Continuity: REJECTED on BOTH tracks. No value continuity checks ship.

**Two attempts were made and both are rejected. Neither is in the plan.**

**Attempt 1 — cross-scene, structural.** A scene's `value_at_open` must equal
the previous scene's `value_at_close`. Proposed as a validator. **Wrong**: value
can move *consequentially*, with no turn on screen.

```
scene A  (x present)  x's value: negative → positive
scene B  (no x)       something happens in the world
scene C  (x present)  x opens negative again — B moved him, off screen
```

Open(C) ≠ close(A) is *correct* here. The live data contains exactly this case,
which is how the error was caught — and it is the decisive evidence:

```
garden-day    cast=[]  closes mixed
garden-dream  cast=[]  opens  positive
```

Those are **the only two scenes in the project with an empty cast**, and they
are precisely the pair that "breaks". An earlier reading called it a hole in the
story line; it is a scene where the line moves with nothing on screen to turn it.

**Attempt 2 — within one character's beats.** A character's
`character_value_at_open` / `_close` should match their first and last beat.
This survived a while because it is stated as prose in
`skills/story-theory/references/values.md:398`. **Also rejected.** The argument
that killed it: this inverts where consequential drift is possible. The premise
of the A/B/C case is that consequential change is invisible *at character level*
— which means a character's value can legitimately move between two of their own
beats, exactly as at structural level. Checking the character track for
continuity while exempting the story track is backwards: the story track is the
one where every scene exists and is recorded, so it is the track where the check
*could* hold; the character track is the one where it cannot.

**The general reason, which is stronger than either case: a story is written
incrementally.** One scene exists at a time, and the beginning and end are not
yet fixed. There is no "start" or "end" to check against until the author says
so, so any programmatic continuity check is asserting a shape the work does not
have yet. Continuity is **an assessment made by reasoning — the assistant and
the user, together, as the story is built.** A problem the moment it exists is
how the form gets shaped: curving a statue, not a spec being policed.

A machine check here is not merely wrong, it is *actively harmful*: it fires on
valid work, and a check that cries wolf on valid work trains the author to
ignore the signal for every real problem. This is the `scene.no_cast` lesson
already recorded in this repo — when a detector can fire on a legitimate design
choice, the answer is not to soften the detector but to have no detector.

**What this means concretely — do not build:**
- no cross-scene `value_at_open` vs previous `value_at_close` check
- no arc-endpoint vs first/last-beat check
- no sibling-aware reader in `core/db.py` for the purpose of continuity
- no suppression flag for either (a flag for a check that should not exist)

The `unfilled` view's **drift row** (a container with no charge whose children
carry charges) survives — it reports a *missing* field, which is true at every
stage of writing, not a *wrong* one. Unfilled is knowable; consistent is not.

### Off-screen consequence: already expressible, no new field

The A/B/C case prompted a proposal to add `no_cast` to `arc_beat`. **Not built,
and not needed** — verified against the schema:

- `arc_beat.character` is **required** (`core/constants.py:32`) and is the beat's
  **`parent_id`** (`core/entity.py:144`). A beat *is* "this character's beat";
  it cannot exist without naming one.
- `arc_beat.scene` is likewise required, so a beat always names a scene.
- `scene.no_cast` already exists (`constants.py:134`, honoured at `db.py:671`)
  and already means "this scene deliberately has no characters".

So the off-screen case is already writable: the beat names the character and the
scene, and the scene's own cast is a separate recorded fact. A beat sitting in a
scene its character is absent from is simply a beat whose scene has no cast —
expressed today by `no_cast` on the scene, no new field required. A `no_cast`
*on the beat* would assert a contradiction: a character absent from a beat that
requires a character.

Recorded so this is not re-proposed. The general form: **absence is recorded
where the absence is** — on the scene, by the field that already means it.

---

## Phase 6 — `values.md` only (skills are being rewritten from scratch)

**Scope decision: the skills are a full rewrite, so this phase touches exactly
one file.** Everything else in `skills/` is deliberately left alone.

Verified, not assumed — `_register_skills` (`__init__.py:226`) registers
**only** `skills/hermes-story-architect/SKILL.md`. The comment at `:162` calls
the rest "legacy sub-skills". So `story-loader/`, `story-editor/` and
`story-theory/SKILL.md` are **not loaded at runtime**; they are reference
material in the repo. That means:

| file | old-name hits | action |
|---|---|---|
| `story-theory/references/values.md` | 12 | **fix — the one file in scope** |
| `story-loader/references/index-format.md` | 8 | leave — not loaded, and the rewrite supersedes it |
| `story-editor/references/index-format.md` | 4 | leave — same |
| the other 7 files | 0 | nothing to do |

Do not patch the two `index-format.md` files. They are dead at runtime and the
rewrite replaces them; editing them is work that gets thrown away.

**But `values.md` is not a field-name reference to be renamed — it is the
source material for the new theory skill, and those are different jobs.** The
rewrite reads it to *build a skill*, so it must be *correct*, not merely
up-to-date. A rename pass would leave it structurally wrong in the way that
matters: it teaches one track (`arc_value` beside `value`, which is the
conflation this whole task exists to remove) and it is the document the new
skill inherits its misconceptions from.

- [x] Read it against `value-system-issue.md` and fix the **model**, not the
      spellings: two tracks, one vocabulary, scope in the field name, value word
      inherited downward, charge per entity
      → §8 rewritten from a one-track field table (which listed the character as
      "None ❌ Missing") into the two-track model, with the field table read
      off `ENTITY_SCHEMAS` rather than memory. §3's conclusion, §5, §6, §7.5 and
      §10 all taught "each level names its own value" or "the character arc is
      not a separate thing" — the conflation, in five places, none of them a
      field name.
- [x] Retarget the field names in the same pass (12 hits) — unavoidable, but the
      reason is correctness, not consistency
      → all 12 gone; `grep arc_value|value_open|value_close` → 0
- [x] Keep the McKee-derived theory (value hierarchy, arc types, positive/
      negative/mixed/ironic). That is the valuable part and it survives the
      redesign intact — the *theory* was never wrong, only the schema's account
      of it
- [x] Add the "ending charge" rule for `y` (currently only at `:382`) into the
      beat-file schema block, since that block is what the new skill will quote
      → moved up to the beat-field table, and the **sign convention** went in
      with it (see the finding below)
- [x] Retarget the checklist at `:398` to the new field names
      → the two lines were `arc_value_at_open` matches first beat / `arc_value_at_close`
      matches last beat. Those are **not** retargeted — they are the rejected
      arc-endpoint continuity rule, in prose. Deleted, and replaced with the
      reason, so it is not re-added.
- [x] Add the inheritance rule in the form a writer meets it: *a scene cannot
      introduce a second theme — that is a character value, or a `plot`
      concern*
- [x] **Do not add** the rejected cross-scene continuity rule, and do not
      describe consequential drift as an error. If the theory mentions
      off-screen consequence at all, it is a legitimate device — that is the
      correction from this session
      → stated positively under the checklist. Drafted once as "each beat's
      `character_value_at_open` matches the previous beat's `_close`" and
      **removed before landing** — that is the same rejected rule in a stricter
      form, and it would have taught the model to police valid work.

**Deliberately not in this phase:** the new theory skill itself, and any edit to
`hermes-story-architect/SKILL.md` beyond the field names the rename invalidates
(it has 0 old-name hits, so nothing to do unless the rewrite lands first).

**Check:** grep `values.md` for `arc_value` — zero hits. And read it once as
"would this teach the model the two-track distinction correctly?", which is the
only test that matters for a source document.

---

## Phase 7 — Full verification

- [x] `python -m pytest tests/ -q` — all green. **672 passed** (671 + 1 added
      here). No test was changed to accommodate a code change; the one edit was
      a stale measured constant in a comment (below).
- [x] Base-view hash pinned; top-level key set asserted
      → **sha256 `ba6b7915e544`, 4828 bytes**, byte-identical to phase 3's
      post-rename value. Phases 4.5 and 5 therefore cost **zero** base-view
      tokens. Re-measured, not carried forward.
      → The top-level key set was asserted **nowhere** in the suite. Added
      `test_base_view_top_level_keys_are_pinned` — this is the phase's own item
      and it was genuinely missing. It fires if a container regains a value
      field; verified by re-adding `shift` to `act` and watching
      `test_story_value_view_carries_a_real_shift_and_curve` go red, then
      restoring `core/constants.py` and re-confirming 672.
- [x] Growth rate re-measured (chars per scene, ceiling per the skill)
      → **153.75, not the 174.75 recorded in the test comment.** The pinned
      number no longer reproduced, so I chased it rather than re-running the
      test: one fully recorded scene is 151 chars
      (`{"id", "title", "value_at_open", "value_at_close", "shift", "y"}`) plus
      the list separator. 174.75 was measured when act/sequence still carried
      `shift`/`y`, so it counted container overhead against scenes. Comment
      updated to the true number; the 200 ceiling is unchanged and still a leak
      alarm, not a budget.
- [x] Live project: `rsync -a` (no `--delete`) to
      `~/.hermes/plugins/hermes-story-architect`, **restart Hermes**, then
      exercise every view through `tool_call` — a tool call before the restart
      silently runs the old code
      → **rsync done**, `values.md` verified byte-identical at the destination.
      **Restart and the `tool_call` exercise are NOT done** — the user took the
      live test as independent work. Everything below was verified by running
      the real handlers against the real data instead, which is what the
      restart would have loaded anyway.
- [x] Import cycle over the live project, then re-read the values: the rename
      survived Markdown → DB → Markdown
      → Run on a **byte-identical copy** of `browser-verification-test` with
      `.story/` deleted, so the live DB was never at risk. All four views read
      back clean:
      - project: `story_value{Trust}`, open `positive`, close `ironic`; no `value` key
      - `kael {character_value: Freedom}`, `mira {character_value: Trust}`; no `arc_value` anywhere
      - act/sequence: charges only. scenes: charges + `shift`/`y`
      - `value_drift` fires on `seq-confrontation` (3 charged descendants) —
        symptom 2 of the original issue, still detected
      - `arc` view: beats carry `character_value_at_open`/`_close` (empty — the
        live data predates the field), plus `shift` and `y`
- [x] Update `value-system-issue.md` status and the skill's
      `references/story-value-vs-character-value.md`
      → status → "built and verified", pointing at the plan. The **field table
      in that file was stale**: it still showed `shift`/`y` on `project`/`act`/
      `sequence`, i.e. the shape revision 2 removed. Corrected, with a pointer
      to revision 2 — a status line saying "read the table" while the table
      contradicts the code is worse than no status line.
      → `references/story-value-vs-character-value.md` **did not exist**; the
      skill dir held only `SKILL.md`. Written as the two-track reference the
      rewrite inherits, and `SKILL.md` gained a five-line "Two value tracks"
      section pointing at it (it had 0 old-name hits, so nothing there was
      invalidated — this is new, not a rename fix).


---

## Revision 2 — `shift` and `y` are scene-and-beat only

Phases 1–4 added `shift` and `y` to `project`, `act`, `sequence` and `scene`.
**That was wrong and is being undone.** They now exist **only on `scene` and
`arc_beat`**.

### Why: two kinds of data were being asked to do one job

`value_at_open` / `_close` and `shift` / `y` are not four readings of one thing.
They are two different *kinds*:

| | what it is | when it becomes knowable |
|---|---|---|
| `value_at_open` / `_close` on **act/sequence** | an **expectation** — where this stretch of the story is *meant* to land | **in advance**, while designing the arc structurally |
| `value_at_open` / `_close` on **scene** | the **actual** — where the value really is, given what got written | only once the scene exists |
| `shift` | the dramaturgical reading of a turn, in the story's language | only once the turn is written |
| `y` | the ending charge, the point a curve passes through | only once the turn is written |

At act and sequence level, `shift` and `y` could only be the model **predicting
scenes that do not exist yet** — a number with no observation behind it. That is
not a measurement, and it is not a plan either. It is a guess wearing the
costume of a fact, which is the one thing this whole redesign exists to remove.

So the level carries the semantics: **act/sequence = intention, scene = what
happened.** `shift` and `y` belong only where a turn actually happens, because
they *describe* a turn.

### The live data already agreed, before anyone argued about it

Filled values in `browser-verification-test` at the time of the revision:

```
project   story_value='Trust'                        (no shift, no y)
act-1     value_at_open/close filled                 (no shift, no y)
act-2     (nothing)
seq-discovery  value_at_open/close filled            (no shift, no y)
seq-confrontation  (nothing)
all 6 scenes  value_at_open/close filled             (no shift, no y yet)
all 6 arc_beat  shift AND y filled                  ← the only ones
```

**Every `shift` and `y` written in this project is on a beat. None is on a
project, act, sequence or scene.** The model was not ignoring the new fields —
it was declining to fill them, because there is nothing to observe yet at those
levels. A field the writer consistently leaves empty is a field asking the
wrong question.

(Scenes have no `shift`/`y` yet either, but that is *recency*: scenes are
drafted later than beats, and phase 4 hand-filled the fixture rather than the
live project. Scenes keep both fields.)

### What it does NOT change

- **`value_at_open` / `_close` stay on all three container levels.** They are
  the one field with a job at every level, and the expectation/actual split
  needs both sides to exist.
- **The field names stay the same on act/sequence and scene.** Not
  `value_expected_at_open`. The distinction is carried by *the entity level* and
  by the view's structure, not by the key name — a fourth vocabulary for the
  same concept is a worse trade than an ambiguity the view resolves.
- **The graph still works.** The story curve is drawn from scene `y`, which is
  where the points are. A second copy at act level was never used by the plot;
  it was only ever a field to fill.
- **The project still declares the whole shape** via
  `story_value_at_open` / `_close` — the expectation at the outermost level,
  which is exactly the "set in advance" case.

### To implement (undo, not build)

- [x] `core/constants.py`: remove `shift` and `y` from `ENTITY_SCHEMAS` for
      `project`, `act`, `sequence`. Keep them on `scene` and `arc_beat`.
- [x] `core/entity.py`: drop the `y` numeric/range validators added for
      `project`/`act`/`sequence` in phase 1; keep the scene and beat ones.
- [x] `core/db.py`: `_PROJECT_DEFAULTS` — no edit needed. It is *derived* from
      `ENTITY_SCHEMAS["project"]` minus `_PROJECT_TITLE_PAGE_FIELDS` (phase 1's
      fix for the hand-copied duplicate), so removing the keys from the schema
      removed them here. The `value*` → `story_value*` rename had already landed.
- [x] `tools/story_load.py` `_view_story_value`: `_value_fields` now takes the
      entity type and an explicit field list, so the scene branch
      (`_SCENE_CURVE`) and the act/sequence branch (`_CONTAINER_CHARGES`) can no
      longer drift into the same four-field shape. The project branch's
      `**_value_fields(pro)` was removed entirely: `project` has no
      `value_at_open`/`shift`/`y` keys at all (it is `story_value_at_open`), so
      it was emitting four empty defaults and nothing else. The view's `SCHEMA`
      description was retargeted to match.
- [x] **`tests/test_value_ownership.py:118` —
      `test_story_value_view_carries_a_real_shift_and_curve` must be DELETED,
      not fixed.** It asserts `any(d.get("shift") for d in containers)` and
      `any(d.get("y") for d in containers)` over acts+sequences. That is the
      plan's old "the curve must not be silently empty" guard, and it can only
      pass because phase 4 hand-filled the *fixture* at act level. Against the
      live project it fails today. It is asserting a lie over a lie. Replace it
      with the scene-level half only:
      `assert any(sc.get("shift") for sc in scenes)` and the same for `y` —
      which is the guard's real purpose, since scenes are where the curve comes
      from.
- [x] `tests/test_value_ownership.py:114` asserts `shift` and `y` are in
      `ENTITY_SCHEMAS["scene"]` — still true after the change; leave it.
- [x] Revert the act/sequence `shift`/`y` rows that phase 4 wrote into
      `tests/fixtures/save-the-children/` and any `index.yaml`.
      → `project.md`, `acts/act-1.md`, `sequences/seq-discovery.md` reverted.
      **The `index.yaml` needed no edit**: phase 4 never wrote container
      `shift`/`y` there (verified by scanning every `shift:`/`y:` line under the
      `project`/`acts`/`sequences` blocks) — only beats carry them.
- [x] Live project: no data change needed — there is nothing to remove.
- [x] Gate: **665 passing**, same as before the revision. If the count drops,
      the deletion above missed a reader.

**Check:** grep for a container-level `shift`/`y` reader — the only remaining
readers of those keys should be the **scene** branch of the value view, the
scene read in `get_project_summary`/`get_dashboard_data`, and the beat paths.

---

## Phase 4.5 — Revision 2: remove `shift`/`y` from project, act, sequence

**This phase exists because Revision 2 was decided after phases 1–4 landed, and
it must run BEFORE phase 5.** Not for tidiness — for two concrete dependencies:

- **Phase 5 (graph) would build against a shape about to change.** The story
  series is *already* scene-based by construction: `arc-graph.js:53` groups
  `DASH.story.scenes` by act and sorts by `order` to build the x-axis, and the
  only `y` it reads is `b.y` off beats (`:77`, `:116`, `:126`). So act/sequence
  `y` was never an input to the plot — it is only a field to fill. Building
  against it now means building on a schema that shrinks again next week.
- **Phase 6 (`values.md`) would document a four-entity shape that is about to
  become two.** It is the source material for a from-scratch skill rewrite, so
  documenting the wrong shape is worse than documenting none.

The undo list is in [Revision 2](#revision-2--shift-and-y-are-scene-and-beat-only)
above. Gate: **665 passing** — the same count as before this phase. A drop means
a reader was missed; a rise means something was added that should not have been.

**Check:** grep for a container-level `shift`/`y` reader. The only remaining
readers of those keys should be the **scene** branch of the value view, the scene
read in `get_project_summary` / `get_dashboard_data`, and the beat paths.

---

## Sequencing rationale

Schema first so the data can hold the distinction; then the data, so the readers
have something real to read; then readers, then views, then graph, then
`values.md`. **Do not start with the views** — they will encode a guess, and the
whole point of the redesign is that the guess was wrong.

Phases 3 and 4 are separable and could run in one session. Phase 6 is one file
and can run alongside phase 5.

**Phase 6 wants to be LAST, and that is now a dependency, not a preference.**
The skills are being rewritten from scratch using `values.md` as source
material. If `values.md` is corrected *before* the schema lands, it documents
fields the code does not have yet, and the new skill is written against a schema
that does not exist. If it is corrected *after*, it is corrected against real
code and real test output. So: schema → data → readers → views → graph →
`values.md` → (your rewrite, whenever you like).

Phase 2 must not start before phase 1 (there is nothing to migrate to) and its
verification overlaps phase 1's failures.

---

## Open questions — all three answered

1. **`docs/html_ui_dashboard/`** — **RESOLVED: leave them alone.** They are
   historical build artifacts, not sources. Nothing generates them, nothing
   reads them at runtime, and they are not in the phase checklist. A stale field
   name in a 2025 snapshot of a generated file is not a defect. Excluded from all
   greps below for that reason — do not "fix" them and do not count them as
   findings.

2. **`_PROJECT_DEFAULTS`** — **RESOLVED: do not delete it; your instinct about
   the title page was right.** Diffed the two sources:

   ```
   in dict, not in schema : []
   in schema, not in dict : author, contact, credit, draft, draft_date,
                            name, screenplay_title, status
   value mismatches        : none
   ```

   The 8 extra keys are exactly the **screenplay title-page block** (plus
   `name`/`status`). So the dict is a *deliberate subset* — the fields eligible
   for omission, excluding the screenplay-only ones — not a stale copy. A plain
   derive would change which keys the `db.py:305` filter can drop, so it is not
   safe as "obviously equivalent". Keep the subset; make it *intentional* (derive
   minus an explicit title-page exclusion), and add the coverage assertion so a
   field added to one source and not the other cannot pass silently.

3. **A scene's `y`** — **RESOLVED: the ending charge, same as a beat's `y`.** The
   story value becomes a curve. See the phase-5 note for what that rules out
   (do not also plot open and close — one line, one story).

   The sweep also surfaced a related defect worth fixing in the same pass:
   the "ending charge" rule for beats is documented **only** in
   `skills/story-theory/references/values.md:382` and enforced nowhere, while
   the schema description the model actually reads (`core/constants.py:181`)
   says merely "Value charge (-1.0 to +1.0)". Four entity types are about to
   inherit that weak description, so the rule moves into the schema.

---

## Final Briefs

### Phases 1 & 2 complete

**Status: both phases done. 654 passed, 3 failed — all three are phase 3/4
consumer code, none is a schema or migration defect.**

Schema renamed, validators retargeted, both projects migrated by hand, and both
verified through a real import cycle (Markdown → DB → read back).

#### What landed

| file | change |
|---|---|
| `core/constants.py` | `story_value*` on project, `character_value*` on character and arc_beat, `value` removed from act/sequence/scene, `shift`+`y` on all five curve entities, every description rewritten to name the value it charges |
| `core/entity.py` | character + arc_beat enums retargeted; `_validate_y` extracted and applied to all five; the duplicated range check is gone |
| `core/db.py` | `_PROJECT_DEFAULTS` derived from the schema minus an explicit title-page exclusion; the project payload builder now iterates it instead of hand-listing 12 keys |
| tests | `TestValueSchema` (31 new), `test_unfilled_fields_curve_fields`, `test_validate_character_value_enums` |
| fixture + live project | `.md` and `index.yaml` migrated; DBs backed up |

#### Three things worth knowing

1. **A pre-verified claim in the plan was wrong.** "`shift` at default is not a
   gap row" was checked before `shift` existed on those types, so it had nothing
   to observe. An unfilled `shift` **is** a gap row — correct, and the same as
   `action` and `arc_type`. `y` is genuinely never a gap (numbers are skipped).
   Corrected in the plan; the test asserts the real behaviour.

2. **A stale test had gone vacuous, not merely old.**
   `test_validate_character_arc_value_enums` fed `arc_value_at_open` to a
   validator that now ignores that key, so it asserted "no warnings" on input
   nothing reads. Repointed and given a negative case so it cannot pass by being
   ignored again. This is the failure mode a rename causes quietly, and it is
   worth grepping for after the next one.

3. **`index.yaml` is not an import input.** No code reads it; `story_import`
   walks the `.md` files only. It was migrated anyway — it is the project graph
   a human and the model read, and 37 stale keys in it would be a lie — but the
   plan's stated reason (import would resurrect them) does not hold.

#### Deferred

- **`Mira: Hope` not recorded** — the user's call, `Trust` kept. Rationale in the
  phase 2 checklist; it is a data decision, not a missed step.
- **`tests/test_soft_delete.py:183`** names `arc_value`. Left for phase 4, which
  already lists it.
- **`docs/html_ui_dashboard/`** — excluded by the plan's resolved open question;
  not touched, not counted as findings.
- **Base-view hash / growth rate** — phase 3 and 7. Not measured here.

#### Next

Phase 3 (read paths). The base-map project branch is already partly done by the
payload refactor above, but `_build_character`, the dashboard beat builders and
all of `src/dashboard/js/` still read the old keys — that is the remaining work
before the view tests can pass.

### Phases 3 & 4 complete

**Status: both done. 665 passed, 0 failed** (654 passed / 3 failed at the start
of phase 3; all three were this work). +11 new tests.

The two tracks are now separate end to end: schema (phases 1–2), base map,
dashboard payload, dashboard JS, `story_value` view, `arc` view, `unfilled`
drift row.

#### What landed

| file | change |
|---|---|
| `core/db.py` | `_build_character` + its `_omit` set retargeted; `get_character_arcs` and the two dashboard beat builders surface `character_value_at_open`/`_close`; new `get_value_drift` |
| `tools/story_load.py` | `_view_story_value` retargeted, `shift`+`y` added, three duplicated dict literals collapsed into `_value_fields`; `value_drift` key; view descriptions now name their track |
| `src/dashboard/js/` | `arc-graph.js`, `network.js`, `panel-manager.js` → `character_value`; `views/story.js` + `data-load.js` → `story_value*`; `panels/entity-panels.js` repointed |
| tests | 4 new in `test_value_ownership.py`, 3 in `test_unfilled_truncation.py`, 1 in `test_core.py`; `test_soft_delete.py`, `test_story_load_views.py`, fixture migrated |
| fixture | `shift`/`y` added to all 5 story containers |

#### Four things worth knowing

1. **The base map was silently dropping the character value.** Before phase 3,
   `_build_character` read `arc_value` from a DB that no longer stores it, fell
   through to the schema default, and `_omit` removed the key — the fixture's
   only character with a designed arc had **no value in the base map at all**.
   Base-view growth is +112 bytes and that is the whole cost.

2. **The growth re-measure caught a real defect, which is why the plan asked
   for it.** The `story_value` view emitted the placeholder
   `"Shift not recorded"` on every unfilled scene. Fixed by applying the same
   default-suppression rule `core/db.py` already uses. Measured ceiling for a
   fully recorded scene: **174.75** chars/scene (base view: 20.0). The test
   threshold is 200 — a leak alarm, not a budget. My first guess of 60 was wrong
   twice over; the pinned number is the measured one.

3. **The drift row works on the case that motivated it.** Re-importing the live
   project, `value_drift` reports `seq-confrontation`: no charge, while its 3
   scenes carry charges. Symptom 2 of the original issue, now visible.

4. **Two vacuous tests found, not one.** Phase 2 caught
   `test_validate_character_arc_value_enums`; phase 4 caught
   `test_non_event_with_empty_values_is_valid`, which had been feeding
   `value_open`/`value_close` — names dropped in an *earlier* task — so it
   asserted "no warnings" on input nothing read. **A rename silently voids the
   tests that mention it.** Grep for the old name after every one; two of three
   finds here were invisible to the suite.

#### Also fixed, not in the checklist

- `panels/entity-panels.js:459` read `scene.value_open`/`value_close` — dead
  since the *earlier* rename, so no scene panel had shown a value arc for a
  whole task. Three fields that no longer existed, on a line nothing flagged.
- The `view` enum description in `story_load.SCHEMA` was scope-free
  ("one character's beats", "value arc across the structure") — the exact
  ambiguity this task removes, in the only text the model reads to pick a view.
- The `unfilled` "top gap" test asserted a fixed field name (`goals_long`). Now
  asserts the *property* (top count == max, and > 1), because the fixture's data
  legitimately changed the answer.

#### Deferred

- **Live project `shift`/`y` and beat `character_value_at_*` are unfilled.** The
  readers handle them and `unfilled` reports them, so nothing is broken — but
  the data does not exercise them. Filling a real project's creative fields is
  the author's call.
- **`skills/` old names** — `story-theory/references/values.md`,
  `story-editor|story-loader/references/index-format.md`. Phase 6, not mine.
- **`tasks/task_14/arc-panel-demo.html`** and
  `tasks/task_23/.../relationship-ui.patch.js` carry `arc_value`. Historical
  task artifacts, like the other `tasks/task_1x*/` documents.
- **`docs/html_ui_dashboard/`** — excluded by the plan's resolved open question.
- **Base-view hash / plugin sync / restart / `tool_call` exercise** — phase 7.

#### Next

Phase 5 (graph). `arc-graph.js` gets a second plot source: scenes in story order
are the same polyline on a different x-axis — one engine, two sources. The
`y`-as-ending-charge rule the graph depends on is already in the schema
descriptions from phase 1, so the data contract is in place. Note the
heuristics at `arc-graph.js:77-81` (flat arc, >0.8 jump) are character
judgements and must not be silently applied to the story series.

### Phase 4.5 complete — `shift`/`y` are scene-and-beat only

**Status: 658 passed, 0 failed.** The gate said 665; the 7-test difference is
entirely removed parametrizations, reconciled below. Nothing was deleted by
accident and no reader was missed.

#### What changed

| file | change |
|---|---|
| `core/constants.py` | `shift`/`y` removed from `project`, `act`, `sequence` (6 lines) |
| `core/entity.py` | `_validate_y` dropped for those three types; kept for scene + arc_beat |
| `tools/story_load.py` | `_value_fields(extra, entity_type, fields)`; `_CONTAINER_CHARGES` / `_SCENE_CURVE`; project branch's `**_value_fields(pro)` deleted; view `SCHEMA` text retargeted |
| `tests/test_value_ownership.py` | the container half of the shift/curve guard deleted, scene half kept **plus a negative guard** |
| `tests/test_core.py` | `_CURVE_ENTITIES`; 3 parametrizations retargeted; new `test_only_scenes_and_beats_carry_the_curve_fields` |
| fixture | `project.md`, `acts/act-1.md`, `sequences/seq-discovery.md` reverted |

#### Three things worth knowing

1. **The gate arithmetic: 665 → 658, fully accounted for.** 8 parametrizations
   disappeared with the fields (act/sequence `y` × 1, `y` description × 3,
   `shift` description × 3, unfilled-curve × 1… precisely: −8) and 1 test was
   added, so **665 − 8 + 1 = 658**. The drop is the shape shrinking, not a
   reader being missed — the intended reading of the gate.

2. **The project branch was dead code, not just wrong.** `**_value_fields(pro)`
   emitted `value_at_open`, `value_at_close`, `shift`, `y` for the project — and
   `project` has *none* of those four keys (its fields are `story_value_at_open`
   / `_close`). So the top level of the view was carrying four empty defaults.
   Revision 2's removal made it structurally impossible to keep, and it is gone
   rather than narrowed. Also caught: the view's `SCHEMA` description still told
   the model "each container's charge, shift and curve point".

3. **The rewritten guard now also fails on a payload, not just the schema.**
   Verified by experiment: re-adding `shift` to `act` in the schema turns **two**
   tests red — `test_only_scenes_and_beats_carry_the_curve_fields` (schema) and
   `test_story_value_view_carries_a_real_shift_and_curve` (payload). Before this
   phase, nothing would have failed on a container regaining the field. The
   experiment was reverted and the suite re-confirmed at 658.

#### Verified, not assumed

- **Base view is byte-identical before and after**: sha256 `f98033353b25`, 7212
  bytes, 1202.0 chars/scene on the 6-scene live project. Removing the fields
  cost zero base-view tokens. (The plan's 1102.5 figure predates unrelated later
  edits; measured both sides in this session, same tree.)
- **Import cycle over the live project** (`.story/` deleted, rebuilt from
  Markdown, read back): project top level = `story_value{,_at_open,_at_close}`
  only; acts/sequences = charges only; scenes = all four. Clean round trip.
- **Live project needed no data change**, as predicted: every `shift`/`y` in
  `browser-verification-test` is on a beat.
- **`index.yaml` needed no edit** — phase 4 never wrote container `shift`/`y`
  there. Confirmed by scanning every `shift:`/`y:` line under the
  `project`/`acts`/`sequences` blocks; only beats carry them.
- **Reader grep (the phase's own check)**: every remaining `shift`/`y` reader is
  a beat path (`db.py:721` `get_character_arcs`, `:1092` the `arc_beat` branch,
  `:1174` `scene_beats`) or the scene branch of the value view. Scene/act/
  sequence read through `_entity_dict`'s merge, which needs no hand-list.

#### Process note — a mistake I made and recovered

To test the guard, I re-added `shift` to `act` and then reverted with
`git checkout -- core/constants.py`. **That reverted to HEAD, and phases 1–4 were
never committed** — it destroyed the file. Recovered in full from the earlier
stash commit (`f50e6279`, still reachable as an unreachable object), and
verified: all six edited files md5-match the stash, `arc_value` is gone from
the schema, all `story_value`/`character_value` renames are present, and the
suite is green at 658. **No work was lost, and the recovered file is the state I
intended** — but the lesson stands: this repo's phases are uncommitted, so
`git checkout --` on a source file is a destructive act here. Revert edits by
re-patching, or stash first.

#### Deferred

- **Live project scenes have no `shift`/`y`** and its beats no
  `character_value_at_*`. The readers handle them and `unfilled` reports them;
  filling a real project's creative fields is the author's call.
- **Phase 5 (graph), phase 6 (`values.md`), phase 7 (full verification)** —
  untouched, as scoped. Phase 5 now builds against a two-level curve shape.

#### Next

Phase 5 (graph): one engine, two sources, story series from **scene** `y` only.

### Phase 5 complete — the story value is a curve

**Status: 671 passed, 0 failed** (was 658). +13 tests, no deletions.

The asymmetry that opened this task — *the character arc has a plottable
curve, the story value has only discrete words* — is closed. The story value
now draws as a line through its scenes, on the same engine as the character
arcs.

#### What landed

| file | change |
|---|---|
| `src/dashboard/js/graph/arc-graph.js` | `scenePositions` / `sceneT` / `storySeries` extracted and shared; the story polyline + dots; the empty state widened; scene x-axis labels extended |
| `src/dashboard/css/graph.css` | `.story-line`, `.story-point`, non-clickable legend item |
| `core/constants.py` | the **sign convention** added to `scene.y` and `arc_beat.y` descriptions |
| `tests/test_arc_graph_story_series.py` | **new, 11 tests** — runs the real JS in node against a stub DOM |
| `tests/test_core.py` | `test_y_description_states_the_sign_convention` (×2) |

#### The tests actually execute the graph

Every pre-existing "test" of this file read it as a string. `arc-graph.js` is
JS in a single-page dashboard, so string-matching it proves nothing about
whether it draws. The new file loads it into node with a stub DOM, calls
`buildArcGraph()`, and asserts on the emitted SVG — the same payload the
browser gets, from the same real backend read.

**Each guard was verified to fail when the code is broken**, by patching the
source and re-running:

| broken | tests that went red |
|---|---|
| story series removed | 5 |
| missing `y` plotted as `0.0` | 3 |
| story-order sort removed | 1 |
| empty state reverted to chars-only | 3 |
| `data-shift` dropped from story dots | 1 |

The sort case is the one worth reporting: **the first version of that test
was vacuous.** It asserted story ordering against the fixture, whose scenes
*arrive* already sorted — so it passed whether or not the sort existed, which
is the same failure mode as the two stale tests phases 2 and 4 found. Rewritten
against a deliberately shuffled input, where it fails when the sort is removed.

#### Three findings

1. **The sign convention was unstated, and the graph is where it bites.**
   Phase 1 fixed *when* `y` is sampled (the ending charge) but never said how
   the charge *word* maps to the *sign*. `positive` and `-0.3` were mutually
   reconcilable under every rule the schema stated — and a beat plotted on the
   wrong side of the line is invisible as an error. Now stated identically on
   both curve entities and pinned. **No validator added**, deliberately: a
   charge-word/number agreement check is a continuity check, and this task
   rejected both of those.

2. **The empty state would have hidden the story curve entirely.** It keyed on
   `chars.length === 0` and returned early — so a project mid-write, scenes
   charged and no arc designed yet, showed nothing despite having a curve to
   draw. That is the exact project this redesign is for. Now either track alone
   renders.

3. **The x-scale collision is fixed, and the first guard for it was itself
   vacuous.** Seating scenes at the centre of their slot removes the
   overlap — see the phase section for the measurement. Worth reporting
   because writing the guard *wrong* reproduced the original bug's hiding
   place: a one-scene act centres at 0.5 and never touches a band edge, so a
   test built on one passes against the broken code. Two scenes on **both**
   sides of a boundary is the shape that exposes it.

#### Verified on the real page, not only in node

Assembled the fixture's dashboard and ran it in headless Chrome, switching to
the arc tab through the app's own `switchGraphTab`:

- story polyline `79.7,194.4 → 155,79.2 → 230.3,104.8` — one point per
  scene, in story order, y values `-0.30 / +0.60 / +0.40` matching the fixture
- both series in one SVG: the white story line and Dr. Elena Voss's
- legend leads with the story value word (`Trust`), then the characters
- all three scenes labelled on the x-axis
- **no JS exceptions** in the console

The live project (`browser-verification-test`) renders with 2 character lines,
6 beat dots and **no story line** — correct, and expected: none of its 6 scenes
has a `y` yet.

#### Deferred

- **Live project scenes have no `shift`/`y`**, so the story curve does not draw
  on it. The readers and the graph both handle them; filling a real project's
  creative fields is the author's call. Unchanged from phase 4's deferral.
- **Phase 6 (`values.md`) and phase 7 (full verification)** — untouched, as
  scoped. Phase 7's `rsync` + restart + `tool_call` exercise has not been run
  against the installed plugin.
- **`values.md:382`'s ending-charge rule is now duplicated in the schema.**
  Not a conflict — the schema is what reaches the model, the skill file is
  prose for a human. Phase 6 rewrites that file; it may want to point at the
  schema rather than restate it.

#### Next

Phase 6: `skills/story-theory/references/values.md` only, read against
`value-system-issue.md` — fix the *model* (two tracks, one vocabulary, scope in
the field name), not the spellings.


### Phases 6 & 7 complete — `values.md` corrected, task verified

**Status: 672 passed, 0 failed** (was 671). +1 test. No product code touched.

#### Phase 6 — the one file, read against the design

`skills/story-theory/references/values.md` is the source material the new theory
skill is written from, so it had to be *correct*, not merely renamed. The 12
field-name hits were the cheap half. The expensive half was that the document
taught **one** value concept, in five places that were not field names:

| was | now |
|---|---|
| §8 a field table listing the character as "None ❌ Missing" | the two-track model, table read off `ENTITY_SCHEMAS` |
| §3 "values are independent at each level" | one word per track, inherited; size is what grows |
| §5 "the character arc is NOT a separate thing" | two tracks, recorded independently |
| §6 controlling idea, scope unstated | named as the *story* track, read from `story_value_at_*` |
| §7.5 "act values need not match project values" | a scene may not name a different value at all |
| §10 beat example on a story value word | on the character's own value |

The McKee theory is intact — hierarchy, P/C/CD/NN, arc types. Only the schema's
account of it changed. The writer-facing inheritance rule is in §8: a scene
cannot introduce a second theme; that is a character value, or a `plot` concern.

#### Four findings

1. **The checklist's two "continuity" lines were the rejected rule in prose.**
   `arc_value_at_open` matches first beat / `_close` matches last beat is
   attempt 2 of the two rejected continuity checks, already documented as
   rejected. They were not retargeted — deleted, and replaced with the reason so
   it is not re-added. A near-miss worth reporting: I first wrote "each beat's
   open matches the previous beat's close" as a replacement, which is the same
   rule in stricter form, and removed it before landing.

2. **The sign convention had a hole only the examples could fill.** Phase 5
   stated *when* `y` is sampled and which sign a charge word takes, but the
   document's own worked example had `shift: "positive → negative"` with
   `y: 0.8` — a direct contradiction, in the one example a model copies. Fixed
   to `-0.8`, and the derivation table's `positive → negative` row relaxed from
   "-1.0, only for crisis" to "-0.8, or -1.0 at crisis" so the example is inside
   the rule rather than exempt from it.

3. **`ironic: true` was documented; no such field exists.** §12 told the model to
   mark irony with a flag. `ironic` is a charge *word*; there is no boolean.
   Corrected — irony rides the charge word and the shift line, `y` holds the
   true charge.

4. **The phase-7 growth number no longer reproduced.** The test comment pinned
   174.75 chars/scene, measured back when act/sequence still carried
   `shift`/`y`, so it charged container overhead to scenes. True figure is
   **153.75** (one recorded scene = 151 chars + separator). The 200 ceiling is
   unchanged — it is a leak alarm, not a budget — but the number beside it was
   wrong and is now the measured one.

#### Verified, not assumed

- `grep arc_value|value_open|value_close` in `values.md` → **0**.
- **Base view: sha256 `ba6b7915e544`, 4828 bytes — byte-identical to phase 3.**
  Phases 4.5, 5, 6 and 7 cost zero base-view tokens. Re-measured, not carried.
- **The top-level key set was asserted nowhere.** This phase's own item, and it
  was genuinely missing: `test_base_view_top_level_keys_are_pinned` added.
  Verified it bites — re-adding `shift` to `act` turns the schema guard red,
  then `core/constants.py` restored and 672 re-confirmed.
- **Import cycle over the live project**, on a byte-identical copy with
  `.story/` deleted so the live DB was never at risk: project
  `story_value{Trust}` positive→ironic, `kael{Freedom}`, `mira{Trust}`, no
  `value` key on any container, no `arc_value` anywhere, and `value_drift` still
  firing on `seq-confrontation` (3 charged descendants) — the symptom that
  motivated the task.
- rsync to `~/.hermes/plugins/hermes-story-architect`, `values.md` confirmed
  byte-identical at the destination.

#### Two stale documents found, both fixed here

- **`value-system-issue.md`'s field table still showed the pre-revision-2
  shape** — `shift`/`y` on `project`/`act`/`sequence`. Its new status line says
  "read the table", so the table contradicting the code was worse than no status
  line. Corrected, with a pointer to revision 2.
- **`references/story-value-vs-character-value.md` did not exist** — the skill
  dir held only `SKILL.md`. Written as the two-track reference the rewrite
  inherits, and `SKILL.md` gained a short "Two value tracks" section pointing at
  it. It had 0 old-name hits, so this is new material, not a rename fix.

#### Deferred

- **Restart + `tool_call` exercise** — the live test, which the user took as
  independent work. The rsync is done, so a restart is all that remains. Every
  view was instead verified by running the real handlers against the real data.
- **Live project scenes have no `shift`/`y`, beats no `character_value_at_*`** —
  unchanged from phase 4. The readers handle them and `unfilled` reports them;
  filling a real project's creative fields is the author's call. Note the live
  beats' `shift` lines are value-word pairs (`"suspicious doubt → active
  defiance"`), not charge-word pairs, so they do not map to `y`'s sign
  convention as the fixture's do. That is data, not schema, and the plugin does
  not police it.
- **The two `index-format.md` files** (`story-editor`, `story-loader`) still
  carry 12 old-name hits between them. Left alone per the plan: not loaded at
  runtime, and the rewrite replaces them.
- **`docs/html_ui_dashboard/`** — excluded by the plan's resolved open question.

#### Next

Nothing in this task. The remaining work is the from-scratch skills rewrite,
which now has a corrected source document and a two-track reference to inherit.
