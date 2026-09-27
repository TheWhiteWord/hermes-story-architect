# Task 28 — Implementation plan: draft staging

**Status: all six phases implemented.** Baseline 679 → **758**, green at
every phase boundary (680 / 703 / 711 / 737 / 758). Design of record is
`draft-staging-design.md`; the intended chat interaction and the seven
presentation decisions are in `chat-preview.md`.

Each phase below opens with its **Status: DONE** block — what shipped, which
assumptions did not hold, and what the check was — followed by the original
plan text it was written against, kept for the record.

**Baseline: 679 tests passing** on `dev` at `a838bb0`, working tree clean apart
from this task folder. Every phase ends with the full suite green. A phase that
needs a new baseline number states it.

---

## Rule for every phase

Each phase opens with **Assumptions to verify** — claims made *before* looking
at the code. Verify each against the code before relying on it. Being wrong is
a finding to report, not a surprise to absorb silently.

Each phase ends with a check that would fail if the phase's logic broke. If a
phase turns out to be a one-liner, it still needs its check, because the next
phase builds on it.

**Stop and ask** if a verified assumption contradicts this plan, if a phase's
check passes for the wrong reason, or if implementing a phase turns out to
require touching something listed here as out of scope.

---

## Phase 1 — The table and its migration

### Status: DONE

`ensure_drafts_table` in `core/db.py`, called unconditionally
from `get_db`. Suite: **680** (679 + 1 new).

*Assumption 1 was wrong in detail, harmlessly.* Besides `story_resolve`, three
readers open their own connection and were not listed: `story_load.py:85`,
`story_dashboard.py:305`, and three helpers inside `core/db.py` itself
(`get_unfilled_map`, `get_character_arcs`, `get_value_drift`). All are
read-only and none of them reads `drafts`; only `get_db` needs the migration.

*One deviation from the plan.* `ensure_drafts_table` uses `conn.execute`, not
`executescript` — the latter issues an implicit `COMMIT`, which would close a
transaction a caller had open. The table is one statement, so `execute` is
enough.

*One deviation from the design.* `ensure_drafts_table` is called
**unconditionally**, not inside the `entities`-exists branch. The soft-delete
migration is conditional because there is nothing to migrate on a fresh DB;
for `drafts` the table is wanted on every project either way, and one
`CREATE TABLE IF NOT EXISTS` no-op per open is the same cost.

The smallest thing that works: the `drafts` table exists on every project DB,
old and new. No tool yet.

**Assumptions to verify**

1. `get_db` (`core/db.py:71`) is the single entry point for every connection —
   no tool opens `sqlite3.connect` directly against `story.db`.
   *Check:* grep for `sqlite3.connect` outside `core/db.py` and
   `tools/story_resolve.py` (which does open one, read-only, for fuzzy
   project matching — confirm it is genuinely read-only and needs nothing).
2. `ensure_soft_delete_columns` is the right precedent to copy, and calling a
   new sibling from `get_db` will not slow the read path measurably.
   *Check:* `CREATE TABLE IF NOT EXISTS` on every open is one no-op statement.
   If the read-path cost shows up, gate it on a `sqlite_master` lookup — but
   measure before adding a second query.
3. The fixture DB (`tests/fixtures/save-the-children/.story/story.db`) has no
   `drafts` table, so it exercises the migration path for free.
   *Check:* list `sqlite_master` on the fixture (it has only the four known
   tables plus FTS shadows).

**Do**

- `ensure_drafts_table(conn)` in `core/db.py`, mirroring
  `ensure_soft_delete_columns`: the `CREATE TABLE IF NOT EXISTS drafts (...)`
  from the design, called from `get_db` next to the existing call.
- Do **not** add `drafts` to `has_schema()` — that function answers "is this a
  story project", and drafts are not part of that. Adding it would make every
  read-only tool's `has_schema` branch change behaviour.

**Check** — `tests/test_legacy_db_migration.py` gets a sibling test: a DB
written without the `drafts` table is repaired on `get_db`, and
`test_connection_lifecycle.py` still passes (every connection closed).

**Out of scope:** the tool, the ops, the renderer.

---

## Phase 2 — Core: stage, list, discard

### Status: DONE

`core/drafts.py`: `validate_ops`, `stage`, `list_drafts`,
`discard`, plus `diff_ops` for the restage. Suite: **703**.

All four assumptions held. Notes:

* **Draft ids** follow `backup_database`'s pattern: a second-granularity
  timestamp with a counter suffix. A 4-hex id from the design's `d-3f2a`
  example would need a collision loop anyway, and the timestamp is sortable —
  which is what makes `list` order by `created_at` meaningful.
* **`_find_entity_id_db` does no fuzzy matching** for `edit`/`delete`: the
  non-arc branch is a bare `WHERE type=? AND id=?`. Only `arc_beat` has a
  `LIKE '%-slug'` fallback, so the identity mapping is exact for every type an
  edit op can target except arc beats — where the fallback is the documented
  behaviour anyway.
* **`prev_ops` is a straight copy**, as assumed.
* The diff walks the op lists rather than indexing them by key. A batch may
  hold two ops on the same entity (two field edits to one location, say) and a
  dict would collapse them, silently reporting one as added and one as
  dropped. `test_a_batch_may_hold_two_ops_on_the_same_entity` covers it.
* A reorder has no single target entity, so the diff names it by its item
  count (`reorder sequence (3 items)`) rather than inventing an entity id.

**The plan as written**

Read/write the draft row. No commits yet. This is where the op format gets
proved against the real schemas.

**Assumptions to verify**

1. An op can be dispatched to `story_create.handler` / `story_edit.handler`
   with only the argument translation the design lists — no other required
   field. *Check:* `story_create` requires `entity_type, slug, project,
   frontmatter`; `story_edit` requires `action, target, summary`. An op must
   supply all of them or the replay fails on a missing key, not on a
   validation error.
2. `story_edit`'s `target` needs `entity_type` **and** `slug`, and `slug` is
   the entity **id** (which for the fixture is not always the slug: scene ids
   are `central-room-day`). Ops carry `entity_id`; the translation to `slug`
   is an identity mapping, but *verify* `_find_entity_id_db` does not do
   fuzzy matching that could resolve a different entity.
3. Draft id generation does not collide. *Check:* what does the plugin already
   use for ids? `backup_database` uses a timestamp with a counter suffix.
   Follow that pattern rather than inventing a third.
4. `prev_ops` on restage is a straight copy of the previous JSON — no
   normalisation needed, because ops are produced by the same agent each time
   and compared structurally.

**Do**

- `core/drafts.py`: `stage`, `list`, `discard`, plus the op validation
  (shape-only, per the design) and the `prev_ops` restage diff.
- `stage` writes **nothing** to `entities` / `sections` / `relations`.

**Check** — guard tests 1, 3, 4 and 7 from the design. Test 1 is the important
one: row counts in all three tables identical before and after a stage.

---

## Phase 3 — Commit

### Status: DONE

`commit`, `sorted_ops`, `_dispatch`, `_call` in
`core/drafts.py`. Suite: **711**.

* **Assumption 1 held and still holds**: `story_create` is autocommit
  (`story_create.py:205`), `story_edit` wraps each call in its own
  `BEGIN`/`COMMIT` (`:374/:438`, `:509/:515`). The batch is therefore not one
  transaction, and the design's per-op guarantee is the right one.
* **Assumption 2 was wrong, and it is why `_call` exists.** Both handlers
  index their required args *before* their first `try` — `story_edit.handler`
  reads `args["action"]`, `args["target"]`, `args["summary"]` at lines 93-96,
  `story_create.handler` reads `args["entity_type"]`, `args["slug"]`,
  `args["frontmatter"]` at 96-98. A missing key raises out of the handler
  rather than returning `{"error": ...}`, and an exception mid-batch would
  leave the loop reporting nothing about what had already landed. `validate_ops`
  should catch these first; `_call` is the backstop that turns an escape into
  the same `{"error": ...}` shape as any other failure.
* **Assumption 3 held.** `_delete_entity` without `confirm` returns a report
  carrying `"error": "Delete refused without confirm..."` and deletes nothing
  (`:702-728`) — that is the refusal the loop would have hit. The synthesised
  `confirm: True` carries the comment saying why it is not a bypass.
  `test_a_committed_delete_soft_deletes_and_is_reversible` asserts the delete
  is still a flag with its sections intact.
* **Assumption 4 held.** `sorted_ops` is a stable sort keyed on `OP_ORDER`.

*Reported per the plan's "report if":* the failure path names what landed
using only what the handlers return, so nothing reaches into them. No
constraint here.

**The plan as written**

The risky phase. Everything above is bookkeeping; this writes.

**Assumptions to verify — all four, before any code**

1. **Atomicity claim.** `story_create` really is autocommit with no
   transaction, and `story_edit` really does `BEGIN`/`COMMIT` per call.
   *Verified during design* (`story_create.py:203`, `story_edit.py:374/438`)
   — re-verify at implementation time, because a fix landing in between
   changes the guarantee.
2. **Handlers return, never raise.** Every error path in both handlers
   `return json.dumps({"error": ...})`. A handler that raises would escape the
   commit loop. *Check:* read every `return` in `story_create.handler` and
   `_edit_note_db`; note the ones inside `try/except` that re-raise.
3. **`delete_entity` needs `confirm: true`** and the commit loop synthesises
   it. *Check:* read the confirm gate; find what it returns when `confirm` is
   absent, because that is the refusal the loop must not hit.
4. **Op sort is stable and sufficient.** Sort by kind (create, edit, delete,
   reorder) and, within a kind, preserve the order the agent wrote. A draft
   that creates two scenes and references the first from the second depends on
   that.

**Do**

- `commit` in `core/drafts.py`: sort, dispatch, check each return, stop on the
  first `{"error": ...}`, keep the draft row, report what landed.
- The `confirm: true` synthesis for `delete`, with a comment saying *why* it
  is not a safety bypass.

**Check** — guard tests 2, 5 and 6. Test 6 (a `create` carrying `cast`
produces relation rows) is the one that catches the relations-inside-frontmatter
trap; a draft that lost its relations would pass every other test.

**Report if:** the failure path cannot report *which* ops landed without
reaching into the handlers for more than they return.

---

## Phase 4 — The tool and its three registration sites

### Status: DONE

`tools/story_draft.py`, registered in `__init__.py` and
`plugin.yaml`, `TOOLS` + `11 → 12`, and the dashboard hook gated on a commit.
Suite: **737**.

* **Assumption 1 held** (already resolved in the plan): `register(ctx)` is the
  registration path; the manifest is still required.
* **Assumption 2 held, and the trap was live.** The hook reads `result` and
  `kwargs["args"]`, and a *stage* response carries `success: True` — which is
  the same shape `story_edit` and `story_create` return. Left ungated, every
  staged draft would have regenerated the dashboard for a change the user had
  not accepted. The gate is `data.get("success") and data.get("committed")`;
  `commit` returns `committed: True` only on full success, so a **partial
  failure does not redraw either** — the project is in a mixed state the user
  has not seen, and the draft row is the resume token. Four tests drive the
  real hook with a real result payload.
* **Assumption 3 held** — same `ctx.register_tool` call as the other eleven.

*New test, as the plan asked:* `TestManifestMatchesRegistration` reads
`plugin.yaml` and compares `provides_tools` to what `register()` actually
handed the ctx. Nothing else compared them. To make it shareable, the
`registered` fixture moved to module level.

**Manual end-to-end** (real fixture project, the three-op batch from
`chat-preview.md`):

```
before        {'entities': 29, 'sections': 139, 'relations': 11}
staged        {'success': True, 'draft_id': 'd-20260927-143451', 'op_count': 3}
after stage   {'entities': 29, 'sections': 139, 'relations': 11}   ← unchanged
restage diff  {"added": [], "dropped": ["reorder scene (4 items)"], "changed": []}
after restage {'entities': 29, 'sections': 139, 'relations': 11}   ← still unchanged
commit        {'success': true, 'committed': true, 'applied': [create, edit]}
after commit  {'entities': 30, 'sections': 147, 'relations': 13}
relations     [('mira-tells-kael','kael','character_scene'),
               ('mira-tells-kael','mira','character_scene')]
mood          ('claustrophobic warmth',)
open drafts   0
```

Staging and restaging wrote nothing; the commit landed the scene with **both
cast relations** and the location edit, and the draft row was consumed.

---

## Phase 5 — The preview renderer

### Status: DONE

`render_preview_md` in `core/drafts.py`, reused by the stage
response; `_commit_report` for the commit response. Suite: **758**.

* **Assumption 1 held.** `story_export._frontmatter_for` builds a frontmatter
  dict for a `.md` file and `core/screenplay.py` is Fountain — neither
  produces a preview block. New renderer.
* **Assumption 2 held, and the denominator rule matters.** The count is over
  non-`computed` fields only, so it matches what the model was ever offered.
  A real render: `12 of 23 fields set`.
* **Assumption 3 held, with one correction.** The `before` value comes from
  `story_edit._preview_edit` — reused, not re-derived, because that function
  already knows whether a field lives in a column, in `extra` or in a section.
  The correction: the fixture's `the-central-room` has `extra = {}`, so its
  `mood` is genuinely unset. The first render produced `` `mood`:  → ``, which
  reads as a rendering fault rather than as "this was empty". It now renders
  `_not set_`.

**Deviation from the plan's wording.** The plan says one renderer reused by
both responses; decision 4 says commit is terse. Those pull against each other,
and the plan's own check ("the rendered block contains each op kind's marker")
is a *stage*-time check. So: `render_preview_md` for stage (the full
presentation), `_commit_report` for commit (a one-line-per-op outcome, with
partial failure getting the full warning). One renderer per audience, not one
for both.

**Manual read-as-a-user** — full block rendered and inspected, real fixture
project. Staging and restaging left 29/139/11 unchanged; the restage printed
`· － reorder scene (4 items)`; the commit reported
`✅ create scene/mira-tells-kael` and `✅ edit location/the-central-room`
without repeating the field table; a forced partial failure printed
`⚠️ Partly saved` with the resume instruction.

## Phase 6 — Shape validation

### Status: DONE

`validate_shape` in `core/drafts.py`, surfaced as
`validation` on the stage response. Suite: **758** (21 new tests in
`tests/test_draft_preview.py`).

* **Assumption 1 held** — `validate_entity(entity_type, frontmatter)` is pure.
* **Assumption 2 held exactly.** `core/entity.py` has three `get_db` calls, at
  lines 349, 366 and 389 — `validate_scene_act_id`, `validate_arc_parents`,
  `validate_plot_characters`, the three the design names. Nothing else opens a
  connection, so nothing else is out.

**A real bug this phase found, in my own code.** `validate_entity` checks
required fields with `field not in frontmatter`. `validate_shape` validates the
frontmatter *merged over the schema defaults* (the correct thing — it is what
`story_create` will actually write), and a merge puts every schema field in the
dict. So the required-field check was **inert**: it could never fire. Required
fields are now checked on their merged *value* — present-but-empty is the real
failure, and it is the one the merge hides. Caught by
`test_a_missing_required_field_is_measured_on_the_merged_frontmatter`, which
was written to assert the merge and failed for the wrong reason.

**The `chat-preview.md` mock is not valid input, and the validator is right.**
The mock writes `value_at_open: "hope"`, but `VALUE_CHARGES` is
`["positive", "negative", "mixed", "ironic"]` (`core/constants.py:12`). The
renderer reports both as findings. The plan's closing note warned about the
mock's *ids*; its *field values* are wrong too. Recorded as
`test_the_chat_preview_mock_would_not_pass_validation` so nobody later
"fixes" the validator to match the mock.

The plan's own checks, both asserted rather than merely absent: a stage with a
bad enum and a missing required field reports both, and a cross-entity
reference to an id created by a later op in the same batch reports nothing
(`test_a_valid_cross_entity_reference_that_does_not_exist_yet_is_silent`).

---

## The plan as written — phases 4 to 6

Kept for the record. The status blocks above are what actually shipped; what
follows is the text each phase was written against.

### Phase 4 — The tool and its three registration sites

**Assumptions — one resolved, two still open**

1. ~~`provides_tools` is read by the loader~~ **RESOLVED 2026-09-27, against
   the Hermes source at `~/.hermes/hermes-agent/hermes_cli/`:**

   `provides_tools` is **not** the registration mechanism for this plugin. The
   gate at `plugins_loader.py:304` applies only to deferred **platform**
   plugins shipping a top-level `tools.py` with a `register_tools(ctx)`; this
   plugin is `kind: backend` and has neither. For it, `register(ctx)` in
   `__init__.py` is the only path that registers a tool.

   The manifest entry is still **required**, because three readers consume it:
   - `plugins_activation.py:62` builds the plugin's `deferred.tools` list from
     `provides_tools` **unioned with what actually registered** — so a name
     declared but never registered is *reported as a tool this plugin has*.
   - `plugins_cmd.py:858` (`_get_plugin_toolset_key`) falls back to the
     manifest on disk to resolve the toolset for `platform_toolsets`.
   - `plugin_validate.py:445` checks declared names against built-in
     collisions.

   Timing: registration at **load** time via `__init__.py`; the manifest is
   read at **reporting and validation** time. Both are exercised by a test.
2. The dashboard hook's `post_tool_call` receives enough to distinguish a
   commit from a stage. *Check:* re-read `__init__.py:205-222` — it gets
   `tool_name`, `result` and `kwargs["args"]`. A committed response must be
   distinguishable from a staged one; design the response shape so it is
   (`committed` key present, or `success` + `draft_id` absent).
3. `ctx.register_tool` accepts the same kwargs as the other eleven.
   Trivially true — it is the same call.

**Do**

- `tools/story_draft.py`: `SCHEMA` + `handler`, delegating to `core/drafts.py`.
- Register in all three places: `__init__.py`, `plugin.yaml`
  `provides_tools`, and `TOOLS` + the count `11 → 12` in
  `tests/test_plugin_registration.py`.
- Add `story_draft` to the dashboard hook tuple, gated on a commit.

**Check** — the full existing suite plus the four parametrised schema tests
now covering `story_draft`. Plus a new test asserting **the manifest's
`provides_tools` set equals the set `register()` actually registered** —
nothing makes that check today, and it is the only thing that catches both
failure modes (a declared tool that does not exist, a registered tool nobody
declared). Then a manual end-to-end against a real project: stage a batch,
confirm nothing changed, commit, confirm it did.

---

### Phase 5 — The preview renderer

The part the user actually sees. Build it against `chat-preview.md`, not
against imagination.

**Assumptions to verify**

1. There is no existing entity→markdown renderer to reuse. *Checked during
   design* — `story_export._frontmatter_for` builds a frontmatter dict for a
   `.md` file, and `core/screenplay.py` handles Fountain. Neither produces the
   preview block. If a renderer turns out to exist, use it.
2. `story_describe` already reports which fields a type expects, and the
   "6 of 22 fields set" count can be computed from `ENTITY_SCHEMAS` plus the
   op's frontmatter without a DB read. *Check:* count only non-`computed`
   fields, so the denominator matches what the model was ever offered.
3. The `before` value in an edit diff is available at stage time. *Check:*
   `_preview_edit` (`story_edit.py:127`) already reads the current value for
   every field — reuse its lookup, do not re-derive it.

**Do**

- One `render_preview_md(...)` in `core/drafts.py` (or a sibling module if it
  grows), producing the seven decisions' output.
- Reused by the stage and commit responses.

**Check** — a test asserting the rendered block contains each op kind's marker
and the field count; and the manual end-to-end above, reading the output as a
user would.

---

### Phase 6 — Shape validation

Last, because it is the only phase that can be wrong harmlessly.

**Assumptions to verify**

1. Required-field and enum checks can run on the in-memory merged frontmatter
   without a DB. *Check:* `core/entity.validate_entity` takes
   `(entity_type, frontmatter)` and no connection — confirm it is not
   already half-wired to the DB.
2. The validators excluded at stage time are exactly
   `validate_plot_characters`, `validate_scene_act_id`, `validate_arc_parents`.
   *Check:* grep for every `get_db` inside `core/entity.py`; any validator that
   opens a connection is out.

**Do**

- Shape findings into the stage response's `validation` field. Cross-entity
  checks stay at commit.

**Check** — a stage with a bad enum and a missing required field reports both;
a stage with a valid cross-entity reference that does not exist *yet* reports
nothing (that is the design's deliberate omission, and it should be asserted,
not merely absent).

---

## Follow-up: task 29, closing the bypass

Once drafts exist, `story_create` and `story_edit` are left holding a direct
path to the same writes, plus three operations that are deliberately not
proposals — project creation, `purge` and `restore`. They should collapse into
one `story_admin` tool, leaving `story_draft` as the only way to author entity
content.

**This is required, not optional.** A tool the model can call is a procedure it
can skip: while `story_create` is registered, "stage first, commit on
confirmation" is a suggestion, and the confirmation loop this plan builds is
worthless with the back door open beside it.

It is a **separate task** — self-contained, and not needed to complete this
plan — but if the two are ever reordered, task 29 goes **first**. Details in
`tasks/task_29/tool-surface-split.md`.

Nothing in this plan depends on it. The write functions do not move — commit
dispatches into `story_create.handler` and `story_edit.handler`, so moving them
into the draft tool would make commit call itself. Task 29 unregisters the two
tools; the functions stay callable.

## Deferred, not in this plan

- **Skill text.** Its own work, once the app is complete. The tool will ship
  working and underused until then; that is accepted.
- **Staleness detection** on `edit` ops. `ponytail:` no check — add an
  expected-`from` per field if it ever bites.
- **Draft TTL / expiry.** A stale draft is inert; `discard` removes it.
- **A `story_draft` for project creation.** Out of scope by decision.

## Note on the mock

`chat-preview.md` invents ids (`act-one`, `central-room`) that do not exist.
The fixture uses `act-1`, `the-central-room`, `seq-discovery`. The renderer
takes ids as given, so this does not affect the code — but a test written from
the mock will fail on a missing entity, and the real ids are above.

**Its field values are wrong too, which the ids note did not cover.** The mock
writes `value_at_open: "hope"` and `value_at_close: "doubt"`, but
`VALUE_CHARGES` (`core/constants.py:12`) is
`["positive", "negative", "mixed", "ironic"]`. The renderer reports both as
findings, correctly. A test copied from the mock's frontmatter will fail on the
validator, not on the entity. `test_the_chat_preview_mock_would_not_pass_validation`
in `tests/test_draft_preview.py` pins this so nobody later relaxes the
validator to make the mock pass.


---

# Final brief

**All six phases complete. Suite 679 → 758, green at every phase boundary
(680 / 703 / 711 / 737 / 758).**

**What shipped**

| Phase | File | What |
|---|---|---|
| 1 | `core/db.py` | `ensure_drafts_table` + `DRAFTS_SQL`, called from `get_db` |
| 2 | `core/drafts.py` | `validate_ops`, `stage`, `list_drafts`, `discard`, `diff_ops` |
| 3 | `core/drafts.py` | `commit`, `sorted_ops`, `_dispatch`, `_call` |
| 4 | `tools/story_draft.py` | `SCHEMA` + `handler`; 3 registration sites; hook gate |
| 5 | `core/drafts.py` | `render_preview_md`, `_commit_report`, `_render_*` |
| 6 | `core/drafts.py` | `validate_shape` → the stage response's `validation` |

79 new tests: `test_drafts.py` (31), `test_story_draft_tool.py` (23),
`test_draft_preview.py` (21), plus the manifest check and the legacy-migration
test.

**Six assumptions did not hold** — each found by checking the code, each
recorded in its phase:

1. **P1/A1** — three read-only readers open their own `sqlite3.connect` beyond
   the two the plan listed (`story_load.py:85`, `story_dashboard.py:305`, and
   three helpers in `core/db.py`). None needs `drafts`.
2. **P1/A2** — `executescript` issues an implicit `COMMIT`; used `execute`.
3. **P3/A2** — **the one that mattered.** Both write handlers index their
   required args *before* their first `try`, so a missing key raises out of
   `handler` instead of returning `{"error": ...}`. Mid-batch that would have
   aborted the loop and reported nothing about what had already landed.
4. **P4/A2** — the dashboard trap was live: a stage response is
   `{"success": true, …}`, identical in shape to a real write, so the hook
   would have redrawn for unaccepted changes.
5. **P5/A3** — the `before` value was available, but the fixture's location
   has `extra = {}`, so a first render showed an empty gap before the arrow.
6. **P6/A1** — `validate_entity`'s required-field check is *inert* under a
   schema merge (`field not in frontmatter` can never fire once every field is
   in the dict). Required fields are now checked on their merged value.

**Two places the plan's own source material was wrong**, both recorded as tests
so they are not "corrected" later:

- The `chat-preview.md` mock writes `value_at_open: "hope"`, but `VALUE_CHARGES`
  is `["positive", "negative", "mixed", "ironic"]`. The validator is right.
- The plan asked for one renderer reused by both responses, while decision 4
  says commit is terse. Resolved as one renderer *per audience*.

**Deferred, unchanged from the design** — nothing here blocks the six phases:

- **Staleness detection** on `edit` ops. `ponytail:` no check — add an
  expected-`from` per field if it ever bites.
- **Draft TTL / expiry.** A stale draft is inert; `discard` removes it.
- **Skill text.** Its own work. The `story_draft` schema description now says
  to relay `preview_md` verbatim and to report `validation`, so the tool is not
  silent, but the *judgement* of when to stage still lives in `SKILL.md`.
- **A `story_draft` for project creation.** Out of scope by decision.

**Follow-up outside this task:** task 29 (collapse `story_create` /
`story_edit` into `story_admin` and close the bypass) is still *required* and
still separate; while both stay registered, staging is a suggestion rather than
the only path.

**Naming note.** `list_drafts`, not `list` — it shadows a builtin, and every
other public function in `core` is `verb_noun` (`get_project_memory`,
`search_sections`, `backup_database`). The tool's JSON key is still `list`,
which is what the model sees.

