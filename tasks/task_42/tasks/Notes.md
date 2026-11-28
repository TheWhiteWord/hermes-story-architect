# Task 42 — Notes

Cross-task record for draft versioning, branching, diff and merge.
One section per task. Each task reads every earlier section before it starts,
and writes its findings into the sections of the tasks they affect.

Rules for entries: a finding is a fact about the code or the spec that a later
task would otherwise have to rediscover. State the fact, where it was verified,
and what it changes. No narration.

---

## T0 — Branch off `dev`, ruff config, formatting

### Findings
- Baseline at `dev` @ `610cf06`: `1744 passed, 1 failed`. The failure is
  `tests/test_no_hermes_imports.py::test_no_hermes_imports` — `app/server.py`
  mentions `adapters.hermes.chat_backend` in a local import. Pre-existing, by
  owner decision not this feature's concern. Every boundary check in later
  tasks compares against **1744 passed / 1 failed**; a count that moves down is
  a regression.
- `build_registry()` output is byte-identical before and after the reformat, so
  no agent-facing tool schema changed. Verified by dumping the registry to JSON
  on both trees and diffing.
- `ruff format` **also rewrites Python code fences inside `.md` files**: 83
  documents under `tasks/` would be reformatted. `tasks/` is excluded from ruff
  for this reason.

### Deviations
- The spec's T0 line reads "`ruff` config; apply formatting". A `[tool.ruff]`
  block already existed at `dev` (`line-length=100`, `target-version=py311`,
  `select=["E","F"]`); T0 therefore adds only the pin and the `tasks/` exclude,
  rather than introducing a config.
- Scope of the `ruff` work is format only, by owner decision. 263 `ruff check`
  findings remain after formatting and are **not** this task's. A later commit
  owns them.

### Issues
- Ruff was neither installed nor pinned at `dev`, so `ruff format` was not
  reproducible: 0.15.8 and 0.17.6 reformat a different set of 6 files. Pinned to
  `0.15.8` in the `dev` extra. A future ruff upgrade is its own commit with its
  own reformat, not a side effect of an unrelated task.
- Of the 263 remaining findings, 113 of the 127 `E501`s are string literals
  (prompt text, SQL, regexes) that the formatter cannot split. Adding `E501` to
  the ignore list is the standing ruff guidance when the formatter owns line
  length; not done here, since it belongs with the lint-backlog commit.
- Six `F841` findings in `src/` are worth reading, not deleting:
  `core/db.py:858 plot_scopes`, `chat/service.py:191 cancelled`,
  `adapters/hermes/setup.py:333 gateway_ok`, `core/fountain_lexer.py:437
  emptytitlepage`, `core/fountain_validator.py:200 prev_line_num`,
  `tools/story_load.py:299 act_extra`. Each is assigned and never read; at least
  two read like an unimplemented check. Line numbers are post-format. Carry them
  to the lint-backlog commit with this note.

---

## T1 — Restore guard

### Findings
- A role collision is only reachable because the validator counts live scenes
  only (`core/entity.py:1119`, `e.is_deleted=0`). The fix is in `restore`, not
  there: the validator is right to let a live scene take a role nobody is using.
- A trashed scene's `plot_<role>` rows are readable only from the `relations`
  table. The `live_relations` view hides every row either end of which is
  deleted, so `restore_check`'s collision scan must not use it. Verified by the
  two-trashed-holders test, which finds nothing through the view.
- `_get_next_order_db` (`core/writes.py:1154`) counts live rows only, by design —
  a soft-deleted child's key is meant to be reused. The reissue is not a bug; the
  tie it creates on restore was. Reproduced: keys `1,2,3`, delete 3, create → 3
  again, restore → two live rows on key 3, order decided by id string.
- `reorder()` (`core/writes.py:1009`) is the only writer of `order_key` that
  takes a complete sibling list, and it renumbers `1..n` live rows. Any
  post-restore placement goes through it rather than writing keys directly.
- `validate_scene_dramatic_role` (`core/entity.py:1139`) allows `plot_role` with
  empty `plot_roles`, so a scene that loses its only role in a `take` stays valid.
  No follow-up decision is needed for the loser.
- Batch checks must all run against the state the batch started in, before any
  write. Interleaved, a target's collision was judged after an earlier target had
  moved the role, and the caller's resolution was silently dropped.

### Deviations
- Spec §8 offers three position resolutions ("after its old neighbour [default] /
  before the next / pick a position"). By owner decision the restore always takes
  the first and reports it in `placed`; only the role collision is refused for a
  decision. The reason: "after its old neighbour" is the only option carrying
  information, and a refusal would dead-end the Trash tab until T13 builds a
  position picker.
- Spec §8 says `restore` "returns an error". It returns a dict carrying
  `code=restore_needs_decision` and `collisions`, which `story_admin` passes
  through as JSON — the refusal is data the agent can act on, and the HTTP route
  turns the same dict into a 409. `restore_many` still raises `RestoreRefused`
  for a batch, because there the payload is per-target.

### Issues
- `restore` (single) does not apply `restore_check`'s structural blockers — a
  parent still in the trash — and did not before this task. The dashboard route
  checks first; the agent's path does not. Unchanged here because it is not this
  feature's guard, but a T11 agent tool that restores must not rely on it.
- `ruff check` reports a pre-existing `F401` in `tools/story_admin.py`
  (`purge_cutoff`, imported and unused at `dev`). Part of T0's 263-finding
  backlog, not touched here.
- `tests/test_live_relations.py` pins the exact set of raw `relations` reads with
  a count per file — currently `core/db.py` 1 (the view's definition),
  `core/integrity.py` 2 (the oracle), `core/trash.py` 3 (the restore guard). A
  new legitimate read means updating that registry **and** its docstring reason,
  because the assertion message alone does not tell the next reader why the count
  moved.
- The Trash tab's UI work landed in this task, not T13: the refusal it introduces
  would otherwise make a collided scene unrestorable from the browser. The panel
  now sends `resolutions`; the `placed` result is still not surfaced.

---

## T2 — `load_database_in_place`, `apply_op` public

### Findings
- `reorder()` now accepts `project_path=None` when the caller supplies `conn`
  (`core/writes.py:1009`, with an assert spelling out the contract). T1 needed
  it to renumber from inside `restore`'s transaction. An `apply_op` that issues a
  reorder inside the executor's transaction uses the same form; do not reopen a
  second connection for it.
- `reorder()` takes a **complete** sibling list and renumbers `1..n`  — it does
  not verify completeness (`F13`). Inside a transaction it will happily number a
  partial list, so the completeness assertion belongs to the caller (T7's
  planner). Extracting `apply_op` must not move that responsibility into the
  already-public function.
- `core.backups.load_database_in_place(project_path, source, *, safety_label)`
  copies a **checked** file into the live database and returns the safety
  backup's path. Source validation (integrity, entities table, schema version)
  stays in `restore_backup`; the loader owns the target-missing refusal, the
  page-size refusal (before the safety backup, as before), the copy, the
  migration and the post-copy integrity check. T3's branch switch calls it with
  a snapshot or parked head and `safety_label="before-switch"`; it must still
  run `restore_backup`'s source checks itself, since the loader does not.
- `core.drafts.apply_op(project_path, op, conn=None)` is the former `_dispatch`,
  renamed only. It returns a refusal as `{"error": …}` via `_call` and never
  raises for a refused write; `commit`'s loop and the merge executor both key on
  that. `sorted_ops` and `OP_ORDER` are untouched.

### Deviations
- The loader takes the safety backup (decision in the T2 task file). The spec
  describes the extraction as "extracted into a function that takes any
  validated source file"; the safety backup had to land on one side of the split
  and the loader is the side T3 needs it on.

### Issues

---

## T3 — `history.db` and `store.py`

### Findings
- Branch switch calls `core.backups.load_database_in_place(project_path, source,
  safety_label="before-switch")` to copy a snapshot or a parked head into the
  live database. **Corrected in T3:** it is called with `safety_label=None`, and
  the parked head is the safety net (see Deviations). Source validation is no
  longer a gap: T3 extracted `core.backups.check_source(source, label)` and the
  switch runs it on the parked head first.
- Two strings inside the loader said `"cannot be restored in place"` (page size)
  and `"failed its integrity check after the restore"`. **T3 reworded both**
  ("copied into this project", "after the copy"). The earlier note here claimed
  two `tests/test_backups.py` assertions pinned the old wording — **that was
  wrong**: both pin only `match="page size"` (lines 314, 413), so the reword
  needed no test change. Verified by grepping the assertions, not assumed.
- `restore_backup` takes its safety backup inside the loader, so a caller that
  wants a labelled "before" state gets it from the same call. Unchanged by T3;
  `restore_backup` still passes `"before-restore"`.
- `versions.token(payload)` (`core/versions.py:15`) is the repo's one
  canonical-JSON → short-sha256 function, and its docstring already says the
  caller decides what to hash. `core/history/fingerprint.py` is a second caller,
  not a second implementation.
- `FROM live_relations` does **not** count as a raw `relations` read:
  `tests/test_live_relations.py:328`'s pattern is
  `(?<!DELETE )\b(?:FROM|JOIN)\s+relations\b` and `_` is a word character, so the
  view never matches. A fingerprint or diff can read the view freely; a
  `FROM relations` would need a registry edit.
- A new `src/` file that calls `datetime.now(` / `.isoformat(` fails
  `tests/test_utc_stamps.py:283` until it is added to `LOCAL_TIME_ALLOWED` with a
  reason. `core/history/store.py` is registered for a snapshot id's timestamp
  (an identifier, like a draft id's).
- **Trashing an entity DOES move the fingerprint**, though §4.4 says the trash is
  excluded. Reason: a delete drops the trashed entity's references out of the
  live `extra`s that named it and hides its relations, so `live_extra`/the
  `live_relations` view return different content. "Trash excluded" means the
  trashed row's own columns, `extra` and sections are not hashed — verified: a
  rename inside the bin moves nothing, and delete+restore returns to the same
  hash. Anything that reads §4.4 as "a delete is not a change" is wrong.
- A staged draft takes an **automatic backup** (`core/trash.py:209`,
  `:1365` via `create_backup(automatic=True)`) — unrelated to this feature, but
  it is why a test asserting "no backup was taken" must start from an empty
  backup list.
- SQLite creates `-wal`/`-shm` beside a file **before** it discovers the file is
  read-only, so one read-write open of a frozen draft leaves two empty files.
  They are harmless to the draft's bytes but are exactly the debris that makes a
  later reader open a stale view. `store._drop_sidecars` sweeps them on every
  write and a test pins it.
- `store.delete_branch` prunes by **reachability** (walk `snapshot_parents` from
  every branch's `base_snapshot_id`), not by `snapshots.branch_id`. §4.3 says
  "reachable from no remaining branch head and not an ancestor of any remaining
  snapshot"; ownership would delete a draft a merge brought into a surviving
  branch.

### Deviations
- **Switch takes no safety backup** (owner decision). §4.3 asks for one *and* a
  park. The park is byte-for-byte the pre-switch state and is addressable by
  branch name, while `prune_automatic_backups` keeps the newest
  `AUTO_BACKUPS_KEPT` of `kind="automatic"` regardless of label — a
  `before-switch` copy would evict a daily one. `load_database_in_place` grew
  `safety_label=None`. Undo is switching back.
- **Switch refuses while the head has an open staged draft** (owner decision).
  §4.3 is silent. A staged draft lives only in `story.db` and is deliberately not
  part of a draft, so the copy would destroy it. The parked head keeps its
  drafts, so switching back restores them; only the destructive direction is
  refused. Carrying them to the target is not an option — the ops were validated
  against the old head's ids.
- **Snapshot files are `chmod 0444`** (owner decision), as §4.3 asks. Deletion is
  by directory, so delete-branch/delete-snapshot still work.
- A branch's id is slugged from its name **once** and survives a rename (§4.3
  calls the name a label). `heads/<branch_id>.db` therefore reads
  `heads/main.db`. Renaming does not move files or snapshot rows.
- `snapshot_parents` is written by `save_snapshot`, which turns
  `branches.pending_merge_parents` into a second parent row and clears it (§7.9).
  Nothing sets that column until T8; the column and the writer exist now because
  §4.2 puts them in this schema.
- `merge_sessions` is created here and left empty — §4.2 lists it in the T3
  schema, so T9 extends a table rather than migrating one in.
- The `heads/<branch>.db` of the branch being switched **to** is deleted after
  the copy: its head is the live database now, and a stale duplicate left behind
  would be what a later switch loaded.

### Issues
- **Safety copies share the 20-slot automatic cap with the daily backup.** Still
  true of `restore_backup` (`before-restore` copies evict daily ones); T3's
  switch avoids adding to it by not taking a backup at all. If the daily history
  matters on a heavily-restored project, the cap needs to count kinds
  separately — not this feature's change.
- Backups stay the escape hatch worth keeping when `history.db` is what broke: a
  draft is a file plus a manifest row, so losing the manifest orphans it, while
  `restore_backup` on a plain `story_*.db` needs only the app. Do not delete the
  backup path on the grounds that drafts cover it.
- `switch` refuses on any `status='open'` draft row, including one staged by the
  agent and never shown to the user. That is deliberate (the alternative is
  silent loss), but T10's route must relay the id list, or the refusal reads as
  an unexplained dead end in the UI.
- `head_state()` opens `story.db` through `get_db`, which **migrates** it. That is
  correct for the live database (it is what every reader does) and must never be
  pointed at a draft file — the migration would rewrite a frozen draft. T4's
  `ProjectView` is the copy-in, copy-out path for drafts.

---

## T4 — `ProjectView` and the logical entity

### Findings
- **A draft file is `chmod 0444` and SQLite writes `-wal`/`-shm` beside it BEFORE
  it discovers the file is read-only.** So one read-write open of a draft (what
  `get_db` would do) leaves two empty files beside a frozen draft, and a `-wal`
  beside a snapshot is what makes a later reader see a stale view of it.
  `store._drop_sidecars` sweeps them after every history write, and
  `tests/test_history_store.py` pins it. `core.history.view.project_view` copies
  the draft out with the backup API and never opens it in place; its test asserts
  the snapshot directory is byte-for-byte unchanged across a read.
- `fingerprint.of_project` and `store.head_state` go through `get_db`, which
  **migrates**. That is right for the live database and wrong for a draft: the
  migration would rewrite a frozen file. Anything that reads a draft goes through
  `project_view`'s copy; the view validates the draft with `check_source` and lets
  `get_db` migrate the copy.
- `core/history/store.py` is registered in `LOCAL_TIME_ALLOWED`
  (`tests/test_utc_stamps.py`) for a snapshot id's timestamp. A new
  `core/history/*.py` that needs `datetime.now`/`.isoformat` must add itself with
  a reason or the stamp guard fails. **T4 added no such file**: neither `view.py`
  nor `logical.py` reads the clock.
- Snapshot ids are `s-<stamp>[-n]`, so a draft's file is
  `history/snapshots/s-<stamp>.db`. `project_view` takes a snapshot id, not a
  path, and resolves it through `store.snapshot_file`.
- `FROM live_relations` is free of the raw-relations registry
  (`tests/test_live_relations.py:328`), so `logical.materialize` reads the view
  with no registry edit. A raw `FROM relations` would need one.
- **The fixture has one `extra` key no schema declares: `project.memory`.** It is
  live content (`story_memory` is an agent-facing tool, `story_export` writes it
  to `.story/memory.md`, a write moves the fingerprint) but `create_entity`
  refused the key, so a logical-entity round trip could be exact and still drop
  it. **Settled in T4, option A** (owner): `memory` is declared on `project` as
  an `object` field, hidden from the entity form and skipped by
  `unfilled_fields`, since `story_memory` writes it one entry at a time.
- **Act order was content the fingerprint ignored.** `reorder(act)` is refused,
  but `edit_entity` accepts `order` on an act and four readers sort by
  `order_key`, so an act-only reorder was refused by `save_snapshot` as "Nothing
  has changed". **Settled in T4, option A** (owner): `act` is in
  `fingerprint.ORDERED_TYPES`. Renumbering acts without reordering still hashes
  stable, which is why the per-parent id list was already the right
  serialization.
- **`create_entity` auto-numbers scenes and sequences, and does not number acts.**
  It numbers a child from the live sibling set, so a rebuild in id order gives a
  different story order than the source. `logical.rebuild_copy` therefore sorts
  children by the parent's declared order; `materialize` drops a scene's or
  sequence's `order` field (order is the id list) and keeps an act's.
- **`create_entity` creates every standard section heading**, so a materializer
  that emits only the headings it found cannot round-trip a state whose empty
  rows were pruned. `logical.materialize` normalizes to `standard_sections(type)`
  with `""` for a missing body.
- `edit_entity` and `delete_entity` both need more than the obvious arguments:
  `delete_entity(project_path, type, id, summary, confirm=True)` refuses without
  `confirm`, returning `would_delete` as a preview rather than deleting. A probe
  that omits it silently tests nothing.

### Deviations
- **`memory` is declared, form-hidden and unfilled-suppressed, not given a form
  field** (owner decision, F-1 option A). The spec's §5.1 defines the logical
  entity through the schema, so declaring it is the smallest change that makes
  it part of the shape; a form field would imply an author edits it there, which
  is not how it is written.
- **`materialize` now hides references to trashed entities** (T6, decision A).
  T4 shipped it reading raw `extra` and raw `location_id`/`parent_id`, which made
  it the only reader that showed a dead id — `core/references.py`'s docstring
  states the rule it was breaking. `extra` goes through `live_extra`, the
  `REFERENCE_COLUMNS` values through `live_column`. The round-trip gate is
  unaffected (the fixture holds no trash); `tests/test_history_diff.py` pins the
  trash behaviour.
- **`act` joins `ORDERED_TYPES` while `reorder()` still refuses acts** (owner
  decision, F-2 option A). `order` remains an act field for writes, and the
  per-parent id list carries the same fact for the hash — two views of one
  ordering, both read from `order_key`.

### Issues
- **The T3 fingerprint changed for any project with more than one act**, because
  `act` order is now hashed. A project with a single act is unaffected (a
  one-element list). This is a hash value change only: `history.db` stores
  fingerprints, so a draft saved before this commit will not match a recomputed
  fingerprint of the same state. Pre-publication, and no migration is needed —
  but a stale `changed` flag on an old draft is expected, not a bug.
- §4.3's "views are cached per session" is not implemented: `project_view` copies
  per block with no cache. T10 owns sessions and is where a cache belongs.

---

## T5 — `refmap`

### Findings
- **22 reference sites over 10 entity types.** Five are declared by none of the four
  mechanisms (`ref`, `REFERENCE_*`, relation kind, bespoke validator); probed with a
  dangling slug, four are **accepted** by `create_entity`: `sequence.primary_plot`,
  `location.variant_of`, `relationship.characters[]`, `relationship.scenes[]`. The fifth,
  `value_turns[].value`, is refused by `validate_scene_value_turns`. `sequence.primary_plot`
  is declared by nothing at all — that is the module's justification.
- **`value_turns[].value` stores the value's display NAME, not its id.** Verified: a turn
  for value `free-will` (name `Free Will`) stores `"Free Will"`; writing `"free-will"` is
  refused ("is not a defined value"). So `refmap.rewrite` takes `by_id` and `by_name` as
  SEPARATE lookup spaces — a merged dict lets a name equal to another entity's id rewrite
  the wrong site. Both directions are pinned.
- **`plot.<role>` (six lists) are the same relation rows as `scene.plot_roles`**, read from
  the plot side, and `logical.materialize` emits both. One authored role edit therefore
  shows as **two** changed fields (probe: `plot_roles[].description` → differences at
  `scene.plot_roles` and `plot.inciting_incident`). They are `computed`, so `edit_entity`
  reports `success` with `skipped_read_only=['climax']` and changes nothing.
  `refmap.DERIVED` is the exclusion list.
- **`scene.act_id` is gone as a field. DERIVED at read time from the scene's sequence.**
  It was a denormalized copy that drifted and could be made to name a different act than
  its sequence's. Now: not in `ENTITY_SCHEMAS["scene"]`, rejected as an unrecognised field
  by every writer, absent from `extra`, absent from scene notes on export, and supplied by
  `db.get_dashboard_data` from the parent chain for every reader. `refmap.DERIVED` still
  lists it because it appears in the materialized shape — a merge must never rewrite it.
- **`scene.scene_beats` is a declared `ref` that is `computed` and absent from the shape** —
  the only one of the seven `ref`s that is missing from `materialize` output. `plot.<role>`
  and `plot_roles` are relation-backed, so `materialize` fills them after the computed
  filter (`logical.py:131`).
- **The write path accepts an entity that no longer says what it is**: `sequence_id=""`,
  `beats=[]`, `characters=[]` are all accepted. So `required` in refmap is §7.4.2's
  decision, not a fact derived from what the code refuses.
- **An empirical sweep of `materialize` output cannot catch an unused reference field.** A
  new site on `project` with no fixture value fails nothing; one whose default holds a real
  id is caught. The declared-ref walk is the other half and is not optional.
- `location.variant_of` is the one site the fixture never exercises (zero
  `location_variant` rows; the world counterpart has one).

### Deviations
- **`Site.checked_by` records the validator, or `None`** rather than a boolean "declared".
  Nine sites have no validator; the test names the exact set, so a new unchecked site cannot
  join it quietly.
- **No storage field on a `Site`.** T7 emits drafts ops by field name, so `extra` vs column
  vs relation is invisible to it; the pinning test resolves each site against the maps.

### Issues

---

## T6 — Diff

### Findings
- `live_relations` hides every relation row either end of which is deleted, so
  "trash ignored" (§6.1) comes for free on the relation path. A raw `FROM relations`
  read does not: a trashed scene still holds its `plot_<role>` rows and its
  cast rows. Read the view, or filter `is_deleted` explicitly.
- **Order is NOT part of `logical.materialize`'s output.** It returns
  `{id: {id, type, fields, sections}}`; child order lives in
  `logical.order_of(conn)` as a per-parent id list. A diff that compares only the
  materialized shapes reports a pure reorder as **no change** — pair both sides
  with `order_of`. (`order_of` reads the same rows and tie-break as
  `fingerprint`, so the two cannot disagree.)
- **Act order is in BOTH shapes**: an `order` field on the act *and* the `act:`
  entry of `order_of`. §5.2 puts it in the act's fields, so `diff._order` skips
  every `act:` key — reporting both makes two items of one authored edit.
  **Corrected here:** the pre-task note said a diff of shapes alone cannot see an
  act reorder and implied the order list was the only place it lives. `diff`
  reports it as `field:act:<id>:order`, verified by test.
- **§6.1's element-wise list diff covers FOUR fields, not one.** This section
  previously claimed "only `character_scene` cast is a plain id list". **That was
  wrong.** `REFERENCE_LISTS = ("characters", "scenes")` and all four of
  `plot.characters`, `scene.characters`, `relationship.characters`,
  `relationship.scenes` are plain id lists in the shape. `diff._list_sites`
  derives the set from `refmap` (a site declared `field[]`) rather than
  restating it, so a new list site joins the element diff automatically.
  Probed: swapping `["kael","mira"]` for `["mira","kael"]` yields
  `added: []`, `removed: []` and no item.
- **The other list/bespoke shapes are whole-value** and are not taught their
  structure: `scene.plot_roles` (`[{plot, role, description}]`), a plot's role
  lists (`[{scene_id, description}]`), `scene_beats.beats` (`[{action, reaction,
  gap}]`), `relationship.perspectives` (keyed object), `project.memory` (object of
  four lists). Only `perspectives{}` is a *reference* site among these; the rest
  hold no id at the top level except inside entries the diff reports whole. A
  merge item that must act on one entry resolves it through `refmap`'s concrete
  path, not through a finer diff.
- Two **live** siblings can already share an `order_key`: a delete frees a key,
  `_get_next_order_db` reissues it, and a restore leaves the pair in place. So the
  child order must be serialized as the `(order_key, id)` id list (§4.4's
  fingerprint does this too), never as the raw key values — two states that
  differ only in which of two tied siblings sorts first would otherwise diff as
  equal.
- `tests/test_live_relations.py` pins every raw `relations` read with a count
  per file. `diff` reads no raw `relations` (it goes through `materialize`), so it
  needed no registry entry.
- **`logical.materialize` was the one reader that showed trashed ids.** Probed:
  after trashing `mira`, `scene.characters` = `["kael"]` (relation-backed, the
  view filters) but `relationship.characters` = `["kael","mira"]` and a
  `location.world` kept its dead `parent_id`. `core/references.py` states the
  reader rule; `logical` did not apply it. **Fixed in T6** (decision A):
  `extra` goes through `live_extra`, `REFERENCE_COLUMNS` values through
  `live_column`. A trashed *reference column* now reads `""`, matching what a
  reader shows.
- **Trashing an entity therefore DOES move a diff**, exactly as T3 found it moves
  the fingerprint, and for the same reason. A delete reads as: the entity
  `removed`, plus a field change on every live entity whose `extra` list or
  reference column named it. That is correct — a reader's state changed — but a
  merge planner that expands "removed entity" must not also emit ops for those
  cascade rows, or one delete becomes many.
- **One authored role edit appears as TWO changed fields** in the raw shapes:
  `scene.plot_roles` (the authored side) and the plot's six
  `setups`/`inciting_incident`/… lists (the read side). `refmap.DERIVED["plot"]`
  is the exclusion list, verified in T5, and `diff._derived` reads it rather than
  restating it. Pinned: a role description edit yields exactly
  `field:scene:central-room-day:plot_roles` and leaves the plot `unchanged`.
- **`get_screenplay_text` drops every scene whose `Content` is empty**:
  `_screenplay_rows` filters `s.body != ''`. A heading-only scene is a scene in
  the entity view and would vanish from a script view built on the composer.
  `diff` composes per scene from the materialized fields with the existing
  `scene_heading`, and a test pins the joined output equal to
  `get_screenplay_text` on the fixture, so the two cannot drift.
- **`scene.act_id` and `scene.order` are not in the shape** (T4/T5). A scene's
  act reaches `diff` through its sequence's `act_id`; its position through
  `order_of`. `diff._placement` returns `{act, sequence, position}` (1-based).

### Deviations
- §6.1 asks for section diffs with `difflib`; `diff.text_diff` returns the
  unified-diff **line list**, not a formatted string, so a reader (JSON, a view)
  decides how to render it.
- §7.2's items are emitted by the diff as they are discovered (keys plus the
  type/id/name that identify them). The change payload is **not** repeated on the
  item: it is already in `entities` / `order` under the same key, and duplicating
  a section body onto its item sends it twice to every consumer.
- The item key is `kind:type:id[:name]` (`entity:scene:x`, `field:character:kael:name`,
  `section:…`, `order:scene:<sequence_id>`). Not in the spec; chosen so a stored
  decision (§7.5, T9) can be keyed on it and survive a re-plan.

### Issues
- `compare` loads both states in full (two `materialize` + `order_of` passes) and
  deep-copies nothing, so comparing a large project twice in one request costs two
  full materializations. Acceptable at this data size; `ProjectView` caching (T10)
  is where a session-level cache belongs.
- A scene whose parent sequence is missing from the order lists gets
  `position: None` and is absent from `_story_order`, so it appears only through
  the `removed`/`added` path. The write path refuses a scene without a live
  sequence, so this is unreachable today.


---

## T7 — Planner

### Findings
- `logical.rebuild_copy(entities, order, dest)` creates a whole materialized shape
  through `create_entity`, but it sorts by an `order` mapping. A plan bringing ONE
  entity has no such mapping and must not invent one: `create` the entity and let
  the reorder step settle its position.
- D6 ("trashed in target") reuses the restore guard. `restore_check(conn, id)`
  already reports `collisions` (a singular role held by a live scene, with the
  holder and the two choices) and `placement` (another live sibling on the same
  `order_key`). The planner's D6 decision and D4/D3 expansions map onto those two
  payloads; it does not need a second collision scan.
- A plan that applies several ops has the same hazard `restore_many` had: a
  check evaluated after an earlier op moved the state it depended on reports the
  wrong thing. Evaluate every decision against the plan's starting state, then
  emit the ordered ops.
- **The D4 "to verify" is settled.** §7.5 asked whether a scene that loses its
  only plot role to `Theirs` stays valid. It does:
  `validate_scene_dramatic_role` (`core/entity.py:1139`) accepts
  `dramatic_role='plot_role'` or empty with an empty `plot_roles`, and
  `validate_scene_plot_roles` only rejects a *singular* role held twice. The
  loser needs no follow-up decision (no mark-as-transition, no
  assign-another-role): its beats, cast and other plots' roles are untouched, and
  T1's `take` resolution performs exactly this write.
- **D6 must not double-place.** `core.trash.restore` already settles the restored
  row's position (renumbers the parent through `reorder`, reports `placed`). A D6
  plan that also emits a `reorder` for the same parent renumbers it twice, and
  the second is built from a list the planner computed before the restore ran.
  Take the restore's `placed` as the outcome and emit no reorder for that parent.
- **`refmap` is the reference source: `iter_references(type, fields)` and
  `rewrite(type, fields, by_id=…, by_name=…)`.** Paths are concrete
  (`value_turns[0].effects[1].character`), so the decision key can name the entry.
  `by_name` is a SEPARATE lookup space: `value_turns[].value` holds the value's
  display name, not its id, so a D1 keep-both on a value maps by name and an id
  mapping must never be used for it.
- **The plot's six `<role>` lists are `refmap.DERIVED`.** A role change is an edit
  of `scene.plot_roles`; nothing may emit an op against `plot.setups` and friends,
  because they are `computed` and `edit_entity` returns `success` with
  `skipped_read_only` while changing nothing — a silent no-op in a merge.
- **The diff already excludes the derived role lists**, and so must the planner's
  dependency expansion: `diff.compare`'s `entities` carries no derived field, so a
  role edit arrives as exactly one item, `field:scene:<id>:plot_roles`. Reading
  the plot's role list as a second item reintroduces the no-op op.
- **Selecting a removed entity must not also emit ops for its cascade edits.**
  Trashing an entity reads as the entity `removed` **plus** a field change on
  every live entity whose `extra` list or reference column named it (T6 Findings;
  the same mechanism moves the fingerprint). One authored delete therefore arrives
  as several items; the planner's removal expansion (§7.4) covers the beats and
  optional cleanup, and must not turn those cascade rows into per-field ops — the
  delete already produced them.
- **`diff.compare(a, b)` returns `{entities, order, items, script}` and the item
  key is stable**: `entity:<type>:<id>`, `field:<type>:<id>:<name>`,
  `section:<type>:<id>:<name>`, `order:scene:<sequence_id>`. Decisions are keyed
  on it (§7.5), so a re-plan must not renumber them. The change payload lives in
  `entities` / `order` under the same key, not on the item.
- **A scene's script row is a lens with `items` already resolved**
  (`_scene_items`): the scene's own item, its changed fields and sections, and its
  sequence's order item. Selecting at script level (§7.2) unions those; it must
  not recompute the grouping.
- **`diff._list_sites` derives the element-diffed fields from `refmap`** (a site
  declared `field[]`): the four plain id lists are `plot.characters`,
  `scene.characters`, `relationship.characters`, `relationship.scenes`. A
  `{"a","b","added","removed"}` change is a set change — a reordered cast list is
  not a change and yields no item, so a plan cannot offer to reorder a cast list.

### Deviations
- **D9 was added to §7.5's catalogue** (owner decision, D-T7-B): an entity deleted on one
  side and edited on the other has no row in §7.3's table and no decision in §7.5. Keep
  mine (default: the deletion stands, incoming edits dropped), take theirs (restore then
  edit — undoes a user's deletion), keep the deletion (same outcome, offered explicitly).
  §7.5's list is D1–D9 from here on; T8 T9 T10 read the ninth.
- **§7.5's D3 is a proposal, not a decision.** When the target can host the child, the
  planner emits the placement it computed and registers nothing. D3 is only raised when
  the container is genuinely absent from the target and cannot be brought. A proposal
  never blocks Apply, so `decisions[]` is not "everything the plan chose".
- **D5 and D8 are marked `optional`** and default to their non-destructive choice
  (bring / keep). `open` is computed from non-optional decisions only, so neither can
  hold Apply. They still appear in `decisions[]` for the UI to show.

### Issues
- **`merge_base` takes one candidate on a criss-cross tie and sets `imprecise`.** T9 and
  T10 must surface that flag to the user; the planner accepts whatever base it is given
  and cannot tell a guess from a certain one. Verified:
  `tests/test_history_store.py::test_a_criss_cross_history_is_reported_imprecise`.

### Facts verified while implementing (probes on this branch)

- **`create_entity` refuses an id that exists OR is in the trash.** D6 cannot be
  "create the incoming entity"; a trashed id must go through `trash.restore` first.
  Confirmed: `ValueError: Entity already exists: character/mira`.
- **`_check_roles` must return the list to write, not mutate it.** `plot_roles` arrives
  as a whole value (D-T7-C), so D4's `mine` has to strip the colliding entry from the
  payload *before* the op is built. A function that only records the choice silently
  ships the collision and `create_entity` then refuses it at apply time.
- **D4's `theirs` needs a `release` edit before the create** (§7.7.2's "edits that
  release roles" phase). `create_entity` validates singular roles against live scenes, so
  a create that takes a role still held is refused: `PlotRoleError: Plot 'the-resistance'
  already has its inciting_incident on scene 'central-room-day'`. `_emit_release` emits a
  plain `edit` op stripping the entry; it is keyed `release` internally so the executor
  can order it, and it is an ordinary `edit` in the public vocabulary.
- **A plan can create the same id twice.** A dependency walk (`_resolve` → `_emit_create`)
  and a directly selected item both reach the same entity when a new sequence's act is
  also selected. `_emit_create` is idempotent through `ctx.planned_creates`; without the
  guard the op list carries two creates and the second is refused at apply.
- **`_settle_orders`' completeness assert is reachable and worth keeping.** A duplicate
  sibling row (two entities sharing an order key) makes the emitted list longer than the
  live set, and `reorder` would renumber the partial list silently (F13). The assert now
  has a test that trips it deliberately; no well-formed plan reaches it.
- **Placement needs both neighbours.** `_place` looks for the source predecessor first and
  falls back to the successor. A scene that is first in its parent in `theirs` has no
  predecessor, so only the successor branch places it — testing one half leaves the other
  unverified.
- **`diff.compare_states(a, b)`** exists so the planner compares each side once. It takes
  already-loaded `State`s; `diff.compare(path_a, path_b)` remains the file-opening entry.
- **`store.merge_base` returns `{"base": None, "imprecise": False}` when nothing is
  shared**, which is the shape a cross-project draft produces. The planner never calls it
  (it takes paths); refusing the pair is the caller's job.

### Review finding (post-T9): a selected role move left the plot with no holder
- Selecting both halves of a role move (the arriving scene and the old holder's
  `plot_roles` edit) raised a false D4 and the default answer, `mine`, stripped the
  arriving scene's role while the holder's edit stripped the other: the plot ended with
  **no** inciting incident. Probed end to end on the fixture through `session.apply`
  (`holders=[]`); `theirs`/`replace` were unaffected. The existing D4 tests only ever
  selected one half.
- Fixed in `plan._check_roles` through `_released_by_selection`: a holder whose own
  `plot_roles` item is selected, and whose incoming value lacks the role, is released
  (a `release` op, no decision). A holder whose release is not selected still raises D4.
- Not covered, and a T10/T13 concern: unticking the arriving scene while keeping the
  holder's edit also leaves the plot with no holder. Nothing refuses it (no validator
  requires a role), so the workspace should warn ("`<plot>` will have no
  `<role>`") rather than the planner block it.

### Review finding (post-T9): planning a deleted entity's field item crashed

- `plan` raised `KeyError` when ours deleted an entity, theirs edited it, and the
  selection included that entity's `field:`/`section:` item. `_resolve_change` read
  `ctx.o[0][entity_id]`, and the entity is absent from ours by definition.
- Reachable from any caller that selects the diff's items wholesale: `diff.compare`
  emits the field item for `theirs` regardless of the delete, so a UI "select all"
  reaches it. T10's preview route would have turned it into a 500.
- **Fixed in T10** (`2f54179`): `_change_item` returns None when the entity is absent
  from ours. The `D9` entity item already owns the delete and its cascade rows (T6), so
  the item was never meant to exist. Guarding `_resolve_change` instead stops the crash
  but emits an `edit` against a deleted entity — rejected.

---

## T8 — Executor

### Findings
- The plan's ops come from `diff.items` (T6): `entity:<type>:<id>` for a create or
  a remove, `field:…`, `section:…`, `order:scene:<parent>`. An `entity:` item
  carries no fields — the content is in `diff.compare`'s `entities` row — so the
  executor must pair the item key with that row rather than expecting a payload.
- **A removal expansion is one delete, not a field change per cascade row.**
  Trashing an entity makes the diff report the entity `removed` *and* a field
  change on every live entity that named it (T6 Findings). Emitting ops for those
  cascade items as well deletes once and then edits the referrers with the value
  the delete already produced.
- A restore executed by the merge is `core.trash.restore(..., resolutions=[…])`
  with the `take`/`drop` the D4 decision chose. It resolves the role and settles
  the position in the same transaction as the flag clear, so the executor does
  not need a separate reorder step after an incoming scene that lands on a taken
  key.
- `restore` returns `code=restore_needs_decision` and writes nothing when a
  collision has no resolution. The executor must treat that return as a failed
  dry run mapped back to the D4 item, not as a success with a missing role.
- A `restore` op is not in the agent-visible op vocabulary (`OP_ORDER`), and
  `_dispatch` (`core/drafts.py:692`) has no `restore` branch — it dispatches
  `create`/`edit`/`delete`/`reorder` to `core.writes` and `purge` straight to
  `core.trash.purge_deleted`. So there is precedent for an op reaching
  `core.trash`, but `apply_op` will be the first caller of `trash.restore` from an
  op. §7.7's "restore is internal to the executor" means the executor calls
  `core.trash.restore` itself; do not add a `restore` kind to the public op
  vocabulary, which is what the agent's `story_draft` schema is built from.
- `reorder` inside the executor's transaction passes `project_path=None` and the
  live `conn`; it does not open a connection per op.
- Position is already settled by a restore and already released by a delete;
  the executor's own ordering work is the §7.7 order (restores → edits that
  release roles → deletes → creates → other edits → reorders) and the
  complete-sibling-list rule from F13, nothing more.
- §7.9's "complete merge" has its storage ready: `branches.pending_merge_parents`
  exists and `store.save_snapshot` already turns it into a second
  `snapshot_parents` row and clears it. The executor's only job is to append the
  source's snapshot id to that column; it must not insert into
  `snapshot_parents` directly, or a save would double-write the parent.
- `store.save_snapshot` takes the history lock (`BEGIN IMMEDIATE` on
  `history.db`) for its whole body. A complete merge that sets
  `pending_merge_parents` and then saves **must not hold its own connection to
  `history.db`** across that call — it would deadlock against itself. Set the
  column in one history transaction, commit, then call `save_snapshot`.
- `store.switch` refuses on any `status='open'` draft. Applying a plan inside one
  transaction on the live database needs no switch; if the executor ever
  sequences one after a merge, it must land after the commit, not inside it.
- `refmap.rewrite` returns a NEW `fields` dict and never mutates the incoming
  items, so an executor can rewrite an item and still compare against what the
  plan was computed from.
- **The plan's ops carry their own `op` kind, and `release` is an `edit`.** T7 emits
  `op` strings `create`/`edit`/`delete`/`reorder` plus an internal `restore`, and a
  D4 "take theirs" arrives as an ordinary `edit` stripping the role from the losing
  scene. Ordering it before the create is the executor's job (§7.7.2); the plan emits
  the ops in that order already, so preserve it rather than re-sorting by kind.
- **`plan()` returns ops even when `ready` is False.** Defaults are already applied, so
  `ops` is the default plan — the executor must gate on `ready` and refuse to apply an
  unready plan, or it will silently drop content on an unanswered D1/D2/D4/D9.

### Deviations
- **§7.8's non-current-branch target is T9's** (owner decision, D-T8-A). `execute.apply`
  takes a project path and covers the live database only. The parked-head target needs
  a branch-addressed pre-merge draft, and `store.save_snapshot` only freezes the live
  `story.db`; T9 owns `target_branch_id`, so it owns that too.
- **Every plan op carries a `source` key**: the item key whose expansion emitted it
  (`entity:<type>:<id>`, `field:…`, `order:<child_type>:<parent>`). §7.7.3 wants a
  failure mapped to "the decision or item that produced it", and no other field can do
  it — a D4 `theirs` release op edits the scene that HOLDS the role while the decision
  belongs to the scene ARRIVING, so matching on the op's `(type, id)` names the wrong
  item. `_explain` looks up `source` first, then the op's own entity key.
- **`plan()` returns `fingerprint`**, the target's state at plan time. §7.7.4 says the
  plan stores it; putting it on the return means a caller cannot pass the wrong one.
- **`core.trash.restore(..., conn=None)`** — the `own_conn` shape `reorder` got in T2.
  Without it an executor's single transaction is impossible (`database is locked`).
  Every existing caller is unchanged.
- **`apply` holds `store.locked` (the manifest `BEGIN IMMEDIATE`) for its whole body**
  (§4.5), and the restore point + `record_pending_parent` run on that same connection.
  `record_pending_parent` therefore takes an optional `conn`; calling it without one
  from inside the lock deadlocks — mutation-verified.
- **The restore point is a normal history draft** labelled "Before merge", taken after
  the stale check and before the content transaction. When the head already equals its
  base draft, that draft is reported as the restore point instead of writing a second
  identical one (`created: False`).
- **`record_pending_parent` writes only `branches.pending_merge_parents`.** Inserting a
  `snapshot_parents` row there would make `save_snapshot` write the same parent twice.
  Verified: after a complete merge, the next save's `parents` is
  `[baseline, source]`.

### Issues
- **A refused merge records no parent**, and that needed its own test: recording the
  source before running the ops leaves a parent row for a merge that never landed, so
  the source's changes would never be offered again. Mutation-verified.
- `dry_run` copies the target per call (backup API into a temp project). That is the
  same cost the drafts flow already pays (F6), and it is what makes the verdict exact,
  but T10 must not call it on every keystroke in a decision form.
- `_run` stops at the first failure. A plan with two independent bad ops therefore
  reports one, and the second appears on the next dry run. Deliberate — later ops were
  planned against a state where the failed one had landed — but a UI that says "N
  problems" would be lying.
- **`execute.apply` does not take a pre-merge draft when the head is clean and no
  manifest exists**: it adopts first (`_adopt`), which freezes the current state as
  Draft 1, and reports that as the baseline. Correct, but the label is "Draft 1", not
  "Before merge" — a caller that shows the label must not imply a merge-specific draft
  was taken.

### Environment note (not a defect in this task)

- **The suite cannot be run in one `pytest tests/` invocation on this host.** Past
  roughly 30-40% the process enters `D` state with `wchan = jbd2_log_wait_commit` and
  never returns. Proven to be the environment, not this change: `git stash -u` to the
  clean T7 commit (`8ffe8b8`) hangs identically at the same point. The reported
  count is therefore from two chunks over the same tree:
  `1829 passed, 1 failed` (everything, with `test_manual_edits.py` and the three
  history files excluded) plus `156 passed` (those four files) = **1985 passed,
  1 failed**. The failure is the baseline's `test_no_hermes_imports`. A fresh
  `TMPDIR` does not help, so it is not the scratch directory filling up.

---

## T9 — Persistent merge sessions

### Findings
- **The `merge_sessions` table already exists**, created by T3 verbatim from
  §4.2 (`id, target_branch_id, source_ref, base_snapshot_id, target_fingerprint,
  selection, decisions, status, created_at, updated_at`) and left empty. T9
  writes rows; it does not migrate the table in. `history.db`'s `MIGRATIONS` list
  is empty, at `BASELINE = 1`.
- A session's stored decisions are keyed by item path; T1's `resolutions` shape
  (`{plot, role, choice: drop|take}`) is the value a D4 decision writes. Persist
  the shape as-is — the executor hands it straight to `core.trash.restore`, so a
  session that round-trips through the manifest must not rename `choice`.
- `restore_needs_decision` is a refusal *result*, not an exception, and it
  carries `collisions`. If a session records "unresolved" it must record which
  collision, not only that apply failed.
- `store._locked` is the pattern for any new history transaction: `BEGIN
  IMMEDIATE` up front and hold it over the file moves. Writing a session row is a
  plain manifest write and needs only `store.connect` + `core.db.transaction`.
- Timestamps in `history.db` come from `core.clock.now_iso()`, like every other
  stored stamp. A new `core/history/*.py` that calls `datetime.now` directly
  fails `tests/test_utc_stamps.py` until registered in `LOCAL_TIME_ALLOWED`.
- **T8 put the executor's whole body under `store.locked`** (the manifest
  `BEGIN IMMEDIATE`, §4.5), and `store.record_pending_parent` and
  `store.restore_point` take a `conn` for that reason. A session operation that
  writes the manifest while calling `apply` must not already hold that lock, and
  must not take it a second time.
- **`apply(project_path, planned, *, parent_source=None, label=…)` is the whole
  interface T9 needs.** It returns `applied` / `refused` (`stale_plan`, or
  `failures` with `item` + `decision`) / `blocked` (`open`), plus `baseline` and
  `parents`. A session stores `planned["fingerprint"]` to re-derive the stale
  check, and `status` is already the value for `merge_sessions.status`.
- **§7.8's other target is T9's** (T8 decision D-T8-A): merging into a
  NON-current branch needs the parked head copied into a scratch project,
  applied, and written back — plus a pre-merge draft for THAT branch, which
  `store.save_snapshot` cannot take because it freezes the live `story.db` only.
  `store._park(project_path, src, dest)` and `store._freeze(..., source=…)` are
  the copy primitives; a `save_head_snapshot(project_path, branch_id, label)`
  built on them is what is missing.
- **`execute.apply` cannot simply be pointed at a scratch copy of a parked head.**
  Verified: apply takes the manifest lock and calls `store.restore_point`, which
  calls `_adopt`, so on a scratch project holding only `.story/story.db` it
  **creates a fresh `history.db` and `history/` inside the scratch dir** and
  adopts the copy as a brand-new project (`baseline.created == False`, a
  throwaway "Draft 1" as the restore point). Data-wise harmless — the copy IS
  the head — but the real branch gets no pre-merge draft and the scratch
  manifest is discarded. T9 must take the branch's draft **before** copying
  (`save_head_snapshot`), and needs a way to run the ops on the scratch copy
  without `apply`'s restore-point/adopt step (`_run(scratch, planned, conn=…)`
  is that path) — or pass an explicit "no restore point, caller has one" flag.
  Whichever it picks, one test must assert the scratch dir gains no `history.db`.
- `merge_sessions.target_fingerprint` should hold `planned["fingerprint"]`
  verbatim — that is the value `execute.apply` compares, so a session that stores
  anything else (a re-hash, a truncated hash) makes its own stale check wrong.
- **T9 implemented: the "missing" `save_head_snapshot` was not added.** The bullet
  above proposed one; what landed is `store._save(..., branch_id=…, head=…)` and
  `store.restore_point(..., branch_id=…, head=…)`, where `head` is a *project
  directory* holding the copy at `.story/story.db`. Same capability, no second
  function — and `restore_point` reuses its "head unchanged → the base draft IS the
  restore point" rule, which a purpose-built saver would have had to repeat.
- **T9 implemented: `_run` is called as `_run(scratch, planned)`, with no `conn`.**
  The bullet above wrote `_run(scratch, planned, conn=…)`; passing a connection is for
  a caller already inside a content transaction, and the parked-target path is not —
  it runs on a throwaway copy, so each op opens its own connection there. The scratch
  still gains no manifest, which is the assertion that test makes.

- **`store._park` read its source `immutable=1`, which ignores an un-checkpointed
  `-wal`.** A branch switch made while any other connection held `story.db` open
  parked the database as of the last checkpoint, dropping the committed writes after
  it. Probed: a second connection wrote and committed, the live database read the row,
  the parked head did not. Fixed in T9's own commit: `_open_source(source, frozen=…)`
  opens a live database `mode=ro` and a frozen draft `immutable`. **The distinction is
  load-bearing in both directions** — `mode=ro` creates `-wal`/`-shm` beside a 0444
  draft (probed), so a single reader for both would reintroduce T4's debris. Any new
  copy-from-file path must say which kind of file it is reading.
- **A parked-target merge must not use `execute.apply`.** Confirmed by probe on this
  branch: `apply` on a scratch project holding only `.story/story.db` writes a fresh
  `history.db` + `history/` inside it, adopts the copy (`baseline.created == False`,
  label "Draft 1"), and leaves the real branch with no pre-merge draft. `session.py`
  therefore takes the manifest lock once, calls `store.restore_point(...,
  branch_id=…, head=scratch)`, runs `execute._run(scratch, planned)` and writes back
  with `store._park`. `tests/test_history_session.py` asserts no scratch the merge
  makes gains a `history.db` or `history/` tree.
- **A session must not hold the manifest lock across `execute.apply`.** `execute.apply`
  takes `store.locked` itself, so a caller already holding it deadlocks on
  `BEGIN IMMEDIATE` — hit and fixed while building `session.apply`. The rule: session
  reads use `store.connect`, the parked path takes `store.locked` and passes its `conn`
  down (`restore_point`, `record_pending_parent`), the live path takes no lock at all,
  and the row's status is written afterwards in its own short transaction.
- **`session.py` stores inputs, never a plan.** `show`/`preview`/`apply` each re-plan
  from the row, so nothing can go stale between them. Consequence for T10 and T11: a
  route or tool that wants "the plan" calls `session.show` (or `preview`), and there is
  no stored op list to read — do not add one.
- **The session stamps every re-plan with its stored `target_fingerprint`, not a fresh
  read.** Without it the stale check compares a plan against itself and can never
  refuse; mutation-verified (two tests fail when the plan is stamped from a live read).
- **A complete merge from an unsaved head is refused** (owner decision). `_source_draft`
  returns a draft id only for `kind == "snapshot"`, and `apply(complete=True)` raises
  "A complete merge needs a saved draft as its source" for a branch source. Cherry-pick
  from a head works and records no parent.
- **`store.get_branch` refuses before opening a manifest that does not exist**, so a
  listing or a session on a project this feature has never touched writes nothing.
  Anything that needs a branch to exist must call `store.adopt` first.
- **`store._save` and `store.restore_point` grew `branch_id`/`head`**, matching the
  `conn`-parameter pattern T2 established. `head` is a *project directory* holding the
  copy at `.story/story.db`, which is why `restore_point` can freeze a non-current
  branch's draft at all — `save_snapshot` only ever reads the live database.
- **`execute._stale` is now `execute.stale`** (public), so a session asks the same
  question `apply` asks rather than duplicating the comparison.

### Deviations

- **The session's source ref stores a resolved `base_snapshot_id`** alongside `kind`
  and `id`. §4.2 says `source_ref JSON`; the resolved draft is what `merge_base` walks
  from, and resolving it once at `start` is what makes the base a property of the
  session rather than of the current call.
- **`apply` marks the row after the merge, not inside its transaction.** §7.7.4 asks
  for the ops to be all-or-none; the status is bookkeeping about an operation that has
  already committed, and nesting it would either deadlock (live) or hold the manifest
  lock across a second `BEGIN IMMEDIATE` (parked).
- **`discard` keeps the row** and sets `status='discarded'` rather than deleting it. A
  deleted row cannot answer "was this merge ever attempted", and the table is small.

### Issues

---

## T10 — HTTP routes

### Decisions (owner, T10)
- **No cache for read-only views.** Per-request copies (7 ms; diff 18 ms). §4.3 amended.
- **One shared error helper** for the HTTP envelope, extracted before `history.py`, with the three existing copies switched and no behaviour change.
- **Decision keys stay in the path**, percent-encoded by the client. `session.set_decision` rejects a key with no `#D<n>` and a key that is not in the current plan, listing the valid ones. Before this, any key was stored and ignored (a typo returned 200 and left the decision open).
- **History routes resolve the project by exact slug (404).** `resolve_project` fuzzy-matches at 75/100 and stays for the agent's tools. Other destructive HTTP routes share the exposure; moving the whole HTTP layer to the strict resolver is a separate commit.

### Findings (from the post-T9 review; verified by running a merge on the fixture)
- **A decision's `a`/`b` are theirs/mine, in that order, unlabelled** (`plan._change_item`
  builds `D2`'s detail as `a=theirs, b=mine`), while the item beside it says
  `theirs`/`ours`. A route that returns decisions as they are makes the UI guess which
  side is which. **Fixed in T10** (`85ed841`): the detail carries `theirs` and `ours`.
- **`set_decision` accepted any key** and stored it: a typo returned success and left the
  decision open, which reads to a caller as an answer that did nothing. **Fixed in T10**
  (`4ef042d`): a malformed key and a well-formed key the fresh plan does not hold are
  both refused, with different messages. The second is "is not asked (yet)", not a bad
  key, because answering one decision can raise another — a `D2` chosen `theirs` on
  `plot_roles` raises `entity:scene:<id>#D4`, verified by re-planning under every option.
  `tests/test_history_session.py` pins both.
- **`store.head_state` describes the current branch only.** The branch graph wants an
  "in progress, N changes" tip for every branch, and a parked head has no `changed`
  flag. T10 needs a function that compares a parked head's fingerprint with its base
  draft (the same comparison `head_state` makes for the live one), and a change count
  from `diff.compare` between the base draft and the head.
- **A scene row in `diff.compare()['script']` can be `status: unchanged` and still carry
  items**: a role or field change moves no script text, but `items` lists it. The script
  view must draw a marker from `items`, not from `status`.
- **`list_branches` carries `counts` per draft, `parents` per draft and
  `pending_merge_parents` per branch**, which is enough to draw the graph (solid parent
  edges, a dashed edge for a pending parent). A "picked from" edge (§7.9 cherry-pick) is
  stored nowhere: an applied session records its source in `merge_sessions.source_ref`
  with `status='applied'`, so the dashed edge is derived from those rows.
- **Cost on the fixture:** `session.show` ~16 ms, `session.preview` ~13 ms. Both
  re-plan and the preview copies the target, so the §T8 rule stands: the preview is an
  explicit action, never a form change.
- `session.show` re-plans on every call, so a client holding a stale selection sees the
  planner's answer, not its own: decisions are keyed by `<item>#<code>` and survive.
- The trash routes are the shape to copy for a core refusal: the core returns a
  dict with `error` **plus** a `code` (`restore_needs_decision`) and its payload
  (`collisions`), and the route maps it to `409` with
  `{"error": {code, message, …payload}}` (`app/routes/trash.py:56`,
  `_restore_refusal`). §10's "existing error shape" is that envelope;
  `_err(status, code, message, **extra)` (`app/routes/trash.py:31`) is the helper,
  defined locally in that module and not yet shared.
- A refusal that a caller must act on carries its payload at the **top level of
  the error object**, not nested under a second key — `collisions` and `blockers`
  sit beside `code` and `message`, and the dashboard reads them there.
- `restore_many` raises `RestoreRefused` for a batch while `restore` returns a
  dict; the route catches the exception and folds `refused[*].collisions` into one
  list. A merge route that applies a planned batch will hit the same split.
- **The history API is all `ValueError` for a refusal, and there is no refusal
  payload yet.** `store.save_snapshot` (nothing changed), `switch` (open drafts,
  already current, no parked head), `branch_from` (missing draft, duplicate
  name), `delete_branch` (current branch) and `delete_snapshot` (a branch's
  latest draft) all raise `ValueError` with an actionable message, following the
  core convention (§9). The routes map them to `409`/`400` with the envelope
  above; a `switch` refusal must carry the open draft ids *as data*, because the
  message alone is not something the UI can act on.
- `store.list_branches(project_path)` is the whole `GET /history/` payload already
  — branches (`is_current` included) and snapshots with `parents`. `head_state`
  adds `changed`. T10 computes `changes_since_save` from that flag; nothing new
  needs storing.
- `list_projects` (`app/services.py:16`) opens each project's `story.db` with a
  bare `sqlite3.connect` to read the name. Enriching it with
  `current_draft`/`branch_count`/`last_saved` means opening `history.db` too, per
  project, on every landing-page call. `history.db` may not exist yet (a project
  never touched by this feature) — treat a missing manifest as "no history", and
  do **not** call `store.adopt` from a listing, which would write during a read.
- **The merge routes have three result shapes to translate, not one.**
  `execute.apply` returns `status` `applied` / `refused` / `blocked`;
  `execute.dry_run` returns `clean` / `refused`. `blocked` carries `open` (the
  unanswered decision keys) and `refused` carries either `code: "stale_plan"`
  (§7.7.4 — the route should 409 and tell the client to re-plan) or `failures[]`
  with `op`, `error`, `item` and `decision`. §10's error envelope has room for all
  of it; the stale case is the one a client must handle differently from a bad op.
- **`apply` blocks: it holds the manifest lock and copies the target for its
  restore point.** A `POST /merges/{id}/apply` is not a cheap request, and
  `POST /merges/{id}/preview` (a dry run) copies the whole target per call. The
  preview must be triggered by an explicit action, never by a form change.

### Deviations
- **A preview reporting unanswered decisions is a 200, not a 409.** §10 lists the
  route without a status; §T7.7.4 says a stale plan is a 409, and that is kept. But
  `blocked` is the dry run *doing its job* — it reports which decisions to answer,
  and the workspace renders them. A 409 would make an ordinary incomplete plan look
  like a failed request. Only `refused` (stale plan, or ops that would fail) is a 409,
  and it carries `failures[]`.
- **A malformed decision key is a 422 from a `DecisionKeyError`, not a 409.**
  `session.set_decision` raises `DecisionKeyError(ValueError)` so a boundary can tell
  "this key will never be valid as sent" from "a valid request the rules declined".
  Both messages already existed; only the type is new. T11 should catch the type, not
  parse the message.
- **`changes_since_save` is a count, `head_state`'s `changed` is a bool.** The landing
  page's "N changes since Draft 3" needs the number; `listing.summary` diffs to get it,
  so a clean head costs one fingerprint and only a dirty one pays for a copy.

### Issues
- **`..` in a history path is answered by Starlette before the route** (404
  `{"detail": "Not Found"}`, not our envelope). The slug guard still rejects any
  separator, so the behaviour is safe; only the body shape differs from ours. Not
  worth a custom router — recording it so nobody reads the odd body as a bug in the
  slug rule.
- **A D4 raised by a D2 has an item key that is never a diff item** (`entity:scene:x`
  for a scene that exists on all sides). The first version of the "not yet asked"
  check keyed off the plan's item list and therefore never fired for the chained case.
  It now keys off the decision list alone, which is the only thing that can be true;
  the distinction is carried by the message, not by a second lookup.

---

## T11 — Agent tools

### Findings
- `story_admin`'s `restore` now refuses a singular-role collision with
  `code=restore_needs_decision` and an optional `resolutions` array
  (`[{plot, role, choice: drop|take}]`). The `story_history` / `story_merge`
  modules must not restate this: the refusal names the fix, and the role
  decision is the user's.
- `core.trash.restore` (single) still does not apply structural blockers (a
  parent in the trash). The dashboard route checks `restore_check` first. A new
  tool that restores must check it too, or the refusal text it relays will not
  match what the app would do.
- `story_history` has its whole surface ready as plain functions:
  `store.list_branches` (branches + drafts + parents), `store.head_state`
  (`changed`, the base draft), `store.save_snapshot`, `store.branch_from`,
  `store.switch`. They take a *project path* and raise `ValueError`.
- **`switch` is not safe to expose as an agent action before T12.** It replaces
  the live database, refuses on open staged drafts, and has no approval card
  until T12. §11's "until the card exists, those actions are UI-only" applies:
  `story_history` gets `list`, `save`, `branch`; `switch` and the deletes wait.
- A `switch` refusal for open drafts carries the draft ids only inside the
  message. An agent tool must surface them verbatim — the fix is
  commit-or-discard, which the agent cannot do on the user's behalf.
- **A merge tool call is `plan` then `apply`, two calls, not one.** The plan is
  what §11's confirmation gate shows (its `ops`, `decisions`, `open`, and a
  `dry_run` verdict); `apply` takes that same dict back plus the idempotency the
  fingerprint gives. `apply` returns `status: "blocked"` with the `open` decision
  keys when the user has not answered — the tool must relay those keys, not
  paraphrase them, because `story_merge.suggest` is keyed on them.

### Deviations
### Issues

---

## T12 — Agent approval card

### Findings
- A scene that loses its only plot role to a `take` stays valid
  (`core/entity.py:1139`), so an approval card never needs a follow-up prompt for
  the losing scene.
- The core's refusal carries everything the card draws: the collision's `message`
  is written in the repo's agent-facing style and names the fix, `holder` names
  the other scene, and `choices` says what to offer. The card renders those; it
  must not invent a third option.

### Deviations
### Issues

---

## T13 — UI

### Findings
- The Trash tab's own restore path is already wired for the guard: a collided
  row carries a "needs a decision" chip, the panel draws the two choices, and
  `restoreKeys` sends `resolutions`. What T13 adds is the *history* workspace's
  version of the same decision, not the Trash tab's.
- `GET /api/projects/{slug}/trash` carries `restore.collisions` on every row,
  next to `restore.blockers` and `restore.placement`.
- `POST /trash/restore` and `POST /trash/{etype}/{eid}/restore` accept
  `resolutions: {target_id: [{plot, role, choice}]}`. `choice` is `drop` or
  `take`; the payload's `choices` per collision is what to offer.
- `restore` and `restore_many` return `placed` when the row's position was taken
  while it was in the trash: `{position, after, was_taken_by}` (single) or a list
  (batch). The Trash tab does not surface it yet — it says how many came back,
  not where the scene landed.

### UI patch 1 — the projects page (done; written by the design side, not an agent)
Scope: `web/js/history-api.js`, `history-graph.js`, `projects.js`, `css/projects.css`,
`tests/projects_harness.js` + `tests/test_projects_ui.py`. `core.js` lost the old
`showPicker`; `projects.js` defines it. Open, Switch and open, Save draft, Branch from
here, Rename, Delete (branch and draft) and the graph are done. Compare, Read and Merge
are the next patches and are not drawn until they work.

- **Backend fixes the UI exposed** (own commits): a project with no history could never
  save its first draft (`_save` adopted, compared the head with the Draft 1 it had just
  written, refused, and the rollback undid the adoption; the message named a draft that
  did not exist). The tests adopted first. And the project listing now carries
  `current_branch`.
- **Opening a project is `location.hash` + `reload()`** (`DASH.openProject`). The old
  picker's links only changed the hash and loaded nothing. The page rewrites `#app`, as
  the old picker did, so it is a boot state: `openProjects()` reloads to return to it.
- **Mutating routes need the `X-White-Words: 1` header** (`server.py`, a CSRF guard); a
  curl without it gets `missing_custom_header`. `DASH.historyApi` sends it.
- **`sw.js` does not cache** (it only exists so Chrome offers Install). No cache bump is
  needed when static files change; an ordinary reload picks them up.
- **Rendering is pure** (state in, markup out) and every id travels as a `data-*`
  attribute, never in a handler, as `trash.js` does; the harness checks both.
- **The delete-branch dialog cannot give the exact count of drafts that will go** (§4.3):
  no route previews it, so the text says what is kept and the result is a toast. A
  `dry_run` on `DELETE /branches/{id}` would fix it.
- **Formatting debt that is not from this patch:** `ruff format --check` flags
  `core/history/listing.py`, `core/history/session.py` and `tests/test_history_routes.py`.
  It belongs in its own formatting commit.
- **Known failure:** `tests/test_no_hermes_imports.py` (a `hermes` string in
  `app/config.py`); fails without this patch too.

Manual checks (a real browser; none of these can be run by pytest):
1. Projects page lists every project; a project with no history says "No drafts saved yet".
2. Expand a project with no history, Save first draft: it becomes Draft 1 on `main`.
3. Branch from here, with and without "switch and open": the second lands in the
   writing view on the new branch.
4. Rename to an existing name: the sentence from the server shows inside the dialog.
5. Delete is disabled for the current branch and for a draft a branch starts from.
6. Switch and open on another branch: the writing view shows that branch's data.
7. Click a graph node: its row in the lists flashes.

### UI patch 2 — the draft chip, and what the Oz demo showed about the graph
- **The graph on the demo's history** (10 drafts, 4 branches, two real merges) was wider
  than the panel, so the newest drafts were off-screen, and every merge was drawn twice.
  Branch names are now a fixed column beside the scrolling canvas, the graph opens at its
  newest drafts and keeps where the reader scrolled it, and columns are narrower.
- **`picked_from` listed complete merges.** `graph._PICKED` took every applied session,
  but a complete merge's source is a parent of the draft saved next, already a solid
  edge. `_picked_from` now drops a pick whose source is in the branch's lineage. Until
  that save, a complete merge is still a pick *and* a `pending_merge_parents` entry; the
  graph draws the pending edge only.
- **`GET /history/status`** (new): `listing.summary` for this project plus
  `next_draft_number`, the `Draft {seq}` an unnamed save will get. It is what the chip
  reads, because `GET /history/` computes every branch's tip.
- **The chip is in all ten `.view-header-actions`**, painted by `draft-chip.js` after
  `loadDashboard`. It re-reads on view change, window focus, the SSE `update` event and
  after any successful non-GET to this project (chat aside), through one `fetch` wrapper:
  entity forms, the script editor, reorder and trash each have their own API helper, so
  fetch is the only place that sees every write. It is a courtesy and never holds a
  write up.
- **Chip click** stores `ww:expand` and calls `DASH.openProjects()`; the projects page
  opens that card with its history showing.
- **Save dialog is shared** (`history-dialogs.js`), with the field helpers the compare
  and merge screens will use.
- Not covered by pytest, checked in Chromium on the Oz demo: the chip in the Script and
  Trash headers at 1000px, save from the chip, the chip after a write from the page.

### UI patch 3 — read a draft, compare two drafts
Scope: `GET /history/read/{ref}/entities` (new, `logical.index`), `web/js/text-diff.js`,
`drafts-common.js`, `reader.js`, `compare.js`, the Read and Compare links on the projects
page, and 44 more harness checks (96).

- **Routes are hashes on the projects page:** `#/drafts/<slug>/read/<ref>` and
  `#/drafts/<slug>/compare/<a>/<b>`, refs as `snapshot:<id>` / `branch:<id>`, each part
  URI-encoded. Boot already sends any hash that is not `#/p/…` to the projects page, so a
  reload on a compare URL works. `hashchange` re-routes; leaving a sub-page re-reads the
  list, because drafts may have been saved in between.
- **Why a new route:** the diff names an added or removed entity by id only, and a reader
  needs a list. The index is id, type, name, one sentence; a scene's beats borrow their
  scene's title.
- **Reading is a reader page, not the whole app read-only.** The writing views are all
  built on the dashboard payload; a read-only mode would need a dashboard for a ref and a
  flag through ten views. The reader shows the screenplay and every entity.
- **The diff the server returns is whole values, not word diffs.** Sections get a line
  diff in the browser (`text-diff.js`: common head and tail trimmed, LCS between, a
  delete-then-add fallback past 160,000 cells, unchanged runs folded to two lines of
  context). The server's own unified `diff` on script rows is not used, so both tabs
  render alike.
- **Ids inside values are shown as names** (a cast list, a plot role's plot) with the id in
  the tooltip. It matches any string equal to an entity id; an unlucky free-text value
  equal to an id would be shown as that entity's name. None in the demo; ids are slugs.
- **Selection is not here yet.** The merge workspace (next patch) adds ticks to the same
  rows and a Review merge button; until then there is nothing to tick.
- Not covered by pytest, checked in Chromium on the Oz demo: pickers, swap, the unchanged
  scenes toggle, back to the list with history still open, Read from a draft row.

### UI patch 4 — script display, and the merge workspace
**Applies on top of UI patch 3** (read and compare, already on this branch). Eight commits: backend for the script views, the script display, two planner
fixes, the typed-value channel, the pre-merge draft's name, and the workspace.

**Script display (asked for after reviewing patch 3)**
- The reader shows the screenplay through the Script view's own pipeline (`screenplay.render_html`,
  the Fountain lexer, `screenplay.css`), scene numbers included. A scene's number is its
  rank among scenes that have text (`db._screenplay_rows` leaves out empty `Content`); the
  scene/sequence numbering problem is not touched.
- `render_html` escapes token text after lexing. `app/stats.py` builds the Script view's
  `scriptHtml` through `tokens_to_html` **without** escaping, so a scene containing `<`
  becomes markup there. Pre-existing and out of scope; worth its own fix.
- Compare's script tab sets each scene as a screenplay and diffs it by block (`scene_script`
  blocks, which the diff now returns as `blocks`), with the heading pinned and unchanged
  runs folded. The entities tab no longer repeats a scene's `Content`: it counts the
  lines and links to the script tab. Other sections still diff there.

**Merge workspace** (`merge.js`, route `#/drafts/<slug>/merge/<session>`; started from
Compare when A is a branch's open draft)
- Items are the planner's three-way items, grouped by entity, with ticks; the script tab is
  a lens (a scene ticks all of its bringable items). Changes that exist only on your side
  are hidden behind a counted toggle. Decisions sit in a panel above, one card per
  decision, with the editors for typed answers. Preview is explicit; Apply opens a
  confirmation listing the operations and the complete-merge choice (off by default).
- **Backend found missing and added:** a decision answer carried only a `choice`, so the
  "Custom" outcomes in §7.3/§7.5 had nowhere to put a value (`custom` silently applied
  theirs; keep-both always used `<id>-2`). Answers now carry an optional `value`:
  D2 custom = the typed field or section value; D4 custom = a role from `PLOT_ROLES`;
  D1 keep-both = `{id, fields, sections}`; D7 custom = an id list (a partial list is
  completed). A value the plan cannot use sets `decision.error`, keeps the decision open
  and falls back to the default behaviour.
- **Planner fixes:** a conflict nobody selected no longer raises a decision or blocks Apply;
  selecting one part of an entity reaches decisions about the entity itself (D9).
- The draft saved before a merge is named for its source ("Before merge from Experiment 1").

**Deviations from the spec, and gaps, stated plainly**
- **D3's chosen option is not consumed by the planner** (`pick`, `after-predecessor`,
  `before-successor` are in the catalogue and nothing reads them); a scene is always placed
  by the default proposal. The workspace therefore shows D3 as information, with no
  buttons. A placement override for a scene arriving into an existing sequence has no
  decision at all. This is the main thing left of §7.5.
- **Operation summaries use ids** ("Release inciting_incident in the-humbug from
  the-audience"), and D7's message names the sequence by id. The cards use names; the
  summaries are the server's text.
- **No chat is docked on this page.** The mock-up showed one; chat belongs to the writing
  view and is not mounted on the projects page. See the hook below.
- Opening the URL of a discarded or applied merge shows that it is closed.

**The Ask Hermes hook (for T11)**
- Every decision card has an "Ask Hermes about this" button that calls
  `DASH.askHermes(ctx)`. `merge.js` defines a stub only when nothing else has (it shows
  that Hermes cannot see merges from this page yet). `ctx` is `{slug, session, decision,
  subject, target, source}`: `decision` is the planner's decision as returned by
  `GET /merges/{id}`, `subject` a sentence naming what it is about.
- T11 needs to: (1) give the agent the merge context (`chat/context.py` attachment kind,
  e.g. `merge_decision` with the session id and decision key); (2) decide where the chat
  lives for this page (mount the existing chat panel on the projects page, or open the
  project's chat in an overlay), then define `DASH.askHermes` to open it with that
  attachment; (3) have `story_merge suggest` call `PUT /merges/{id}/decisions/{key}` with
  `set_by: "agent-suggested"` and a `value` where the choice takes one.
- The UI side of a suggestion is done: a decision whose `set_by` is `agent-suggested` shows
  "suggested by Hermes" with an Accept button (which re-sends the same choice and value as
  `user`); the other options stay available. Verified in Chromium against the real route.
- Nothing applies from a suggestion: `ready` stays false until a person answers.

Not covered by pytest, checked in Chromium on the Oz demo with a scripted scenario (field
and section conflicts, a role collision, the same id added on both sides, an order
conflict, delete against edit): ticking, each decision card, typed values for D1/D2/D4/D7,
the script lens, Preview, Apply with a complete merge, Accept on a suggestion, Discard, and
the database afterwards (the typed id and name, the typed sentence, the one inciting
incident, the restored character, the pending merge parent).

### Deviations
### Issues
