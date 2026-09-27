# Task 28 — Implementation plan: draft staging

**Status: plan only.** Nothing implemented. Design of record is
`draft-staging-design.md`; the intended chat interaction and the seven
presentation decisions are in `chat-preview.md`. Read the design first — this
file only says *in what order*, and *what to check before each step*.

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

## Phase 5 — The preview renderer

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

## Phase 6 — Shape validation

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
