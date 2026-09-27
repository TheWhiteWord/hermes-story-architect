# Task 29 — Move write functions to `core/`, expose `story_admin`

**Status: plan, verified against the code 2026-09-27.** Not implemented.
Task 28 shipped drafts (`core/drafts.py` 669 lines, `tools/story_draft.py`
104 lines); suite is at **758 passing**.

Design note with the reasoning is `tool-surface-split.md`. This file is the
ordered build.

---

## Why this is bigger than unregistering two tools

Decided: **delete `story_create` and `story_edit` entirely**, move the write
functions into `core/`, and have `core/drafts.py` call `core` directly.

The verification found the reason that is right, and it is not aesthetics.
`core/drafts.py` currently reaches **up** into the tools layer in two places:

```python
core/drafts.py:389    from tools import story_create, story_edit
core/drafts.py:615    from tools.story_edit import _preview_edit
```

That is the only place in `core/` that imports from `tools/` — every other
`core/` module is clean, and all of `tools/` imports downward into `core/`.
So the layer inversion exists solely because of task 28's commit loop, and
moving the functions to `core/` is what removes it.

After this task: `core/` never imports `tools/`, and `story_draft` is the only
registered tool that authors entity content.

---

## Target surface

**`story_draft`** — unchanged. `stage` / `commit` / `discard` / `list`. Its
op vocabulary already covers create, edit, delete, reorder, which is the whole
of entity authoring.

**`story_admin`** — five actions, none of them proposals:

| action | moves from | notes |
|---|---|---|
| `create_project` | `story_create._create_project` (`:274`) | takes `root_path`, not `project` — the project does not exist yet |
| `purge` | `story_edit._purge_deleted` (`:561`) | `purge_confirm` + 30-day age floor, unchanged |
| `restore` | `story_edit._restore_entity` (`:626`) | exact inverse of soft delete |
| `list_projects` | **new** | enumerate project folders under `root_path/projects` |
| `delete_project` | **new** | remove a project folder; `backup_database` first, like `story_import` does |

`list_projects` and `delete_project` are **new code, not a move** — nothing in
the plugin covers them today (verified: no `delete_project` /
`list_project` anywhere in the repo). They are admin operations: a project is a
directory with a `.story/story.db` in it. `delete_project` must take a typed
confirmation string for the same reason `purge` does, and must call
`backup_database` before removing anything.

**`story_create` and `story_edit` are deleted.** Not deprecated, not aliased —
the plugin has not shipped.

---

## What moves where

Write functions into `core/`, keeping the bodies as they are:

| from | to | body |
|---|---|---|
| `story_create.handler` entity branch | `core/writes.py: create_entity()` | unchanged logic |
| `story_create._create_project` | `core/writes.py: create_project()` | unchanged |
| `story_create._validate_sequence_exists`, `_get_next_order_db` | `core/writes.py` | private helpers |
| `story_edit._edit_note_db` | `core/writes.py: edit_entity()` | unchanged |
| `story_edit._delete_entity` | `core/writes.py: delete_entity()` | unchanged |
| `story_edit._reorder` | `core/writes.py: reorder()` | unchanged |
| `story_edit._find_entity_id_db`, `_purge_references`, `_default_for` | `core/writes.py` | private helpers |
| `story_edit._purge_deleted`, `_restore_entity` | `tools/story_admin.py` | stay in tools; they take `args` |
| `story_edit._preview_edit` | `core/writes.py: current_values()` | `core/drafts.py:615` already wants this |

**The handler shape changes.** `handler(args, **kwargs) -> str` exists to be a
tool boundary. In `core/` these become plain functions returning `dict` and
raising on failure — the `json.dumps` / `{"error": ...}` string convention
exists only because a tool must return a string. `core/drafts.py:_call` (`:435`)
already unwraps that JSON; after this it calls the dict-returning function
directly and the unwrapping disappears.

**Purge and restore stay in `tools/story_admin.py`** rather than moving to
`core/`. They are genuinely admin-only, never draftable, and have no other
caller — moving them would put dead code in `core/` for no gain.

---

## Phases

Work in this order. Each ends with the full suite green.

### Phase 1 — `core/writes.py`, no deletions yet

**DONE.** `core/writes.py` (new): `create_project`, `create_entity`, `edit_entity`,
`current_values`, `delete_entity`, `reorder`, `preview_reorder`; private
`_check_slug`, `_validate_sequence_exists`, `_get_next_order_db`,
`_find_entity_id_db`, `_default_for`, `_purge_references`. `tests/test_writes.py`
(new, 34 tests) calls all of them directly. Suite **792 passing** (758 + 34).

**Decision taken (the plan said "every error becomes raise"; that was wrong as
written).** Split by *whether the payload is the point*:
- **Errors raise `ValueError`.** Nothing is lost — the message carries what the
  key used to (`valid_types` → "Valid types: …", `unrecognised_keys` →
  "Unrecognised … edit key(s): …" plus the valid examples). No
  exception-subclass machinery to carry data a sentence already held.
- **Previews and refusals return a dict.** `delete_entity` without `confirm`
  and the structural-children refusal return `would_delete` / `cascade_children`
  / `blocking_children`, because the payload *is* the refusal. Keeping them is
  the no-loss-of-functionality choice.

`_preview_reorder` was **not** in the move table; per decision it moved to
`core/writes.py:preview_reorder` rather than dying with the tool. Its only
caller is `story_edit`, which Phase 4 deletes — **deferred: re-check at Phase 4
whether anything still calls it, and drop it if not.**

`_check_slug` is a new shared helper: the old code validated the slug in
`story_create.handler` *before* branching to the project branch, so a project
slug was a path-traversal guard. Split into two entry points that would have
dropped it. `create_project` now validates too (tested).

### Phase 2 — Point `core/drafts.py` at `core/writes.py`

**DONE.** `_dispatch` calls `core.writes` directly; `_current_values` calls
`writes.current_values`. **`core/` no longer imports `tools/` anywhere** — the
layer inversion this task exists to remove is gone. `tools/story_create.py` and
`tools/story_edit.py` are untouched and still registered, so both
implementations coexist until Phase 4.

Suite **793 passing**. All three checks in the plan hold: the 79 draft tests
pass, `test_manifest_and_registration_agree` passes (tool surface unchanged),
and the delete-op test passes — the `confirm=True` synthesis moved to the
`delete_entity` call site in `_dispatch` with its reasoning comment intact.

What disappeared, as predicted: all three tool-boundary translations. `_dispatch`
went from building a JSON `args` dict per op to a one-line call per op, and
`_call` went from `json.loads(handler(args))` to `fn(*args)`. The op docstrings
that explained the translations are gone because there are no translations left
to explain.

**Added `test_core_never_imports_tools`** — an AST scan of `core/*.py`. The
whole point of the task is that the layering is now one-directional, and nothing
else would fail if someone reached back up again. Verified it *fails* on an
injected `from tools import story_create` and names the offending file, so it is
a real guard and not a tautology.

### Phase 3 — `tools/story_admin.py`, registered

**DONE.** `tools/story_admin.py` (new, 5 actions). `_purge_deleted` and
`_restore_entity` moved in from `story_edit` unchanged; `_create_project` is a
thin call into `core.writes.create_project`; `list_projects` and `delete_project`
are new. Registered in `__init__.py` (emoji 🗂️) and added to `plugin.yaml` in
the same change — `test_manifest_and_registration_agree` enforces that they
cannot drift. Suite **817 passing**.

`delete_project` takes a typed `delete_confirm` string, not a boolean: a flag is
something the model can set by itself, and this destroys every entity in a
project. Tested that a *right-shaped* confirm naming a *different* project is
still refused.

**Bug found and fixed while writing it.** `backup_database` writes its snapshot
into `project_path/.story/`. For `delete_project` that snapshot would be
destroyed by the very `rmtree` it was taken to protect — a backup that cannot
survive the operation is not a backup. `_backup_outside` takes the same
WAL-safe snapshot and relocates it to `<root>/backups/<slug>_<stamp>.db` before
the delete. Verified end to end: after the delete, the backup exists *outside*
the tree and still opens with its rows intact.

`list_projects` is a pure directory listing — **no database is opened**, per the
flag. `resolve_project` connects per candidate to recover a display name, which
is right when there is one project to resolve and wrong for an enumeration on a
root holding hundreds. Verified by spying on `sqlite3.connect` (0 calls) and
kept as a test.

### Phase 4 — Delete `story_create` and `story_edit`

**Assumptions to verify**

1. **Every** test file that imports them is updated. Verified count: 24 files
   reference the names, and the pattern is overwhelmingly
   `from tools.story_create import handler as create_handler` (12+ sites in
   `test_core.py` alone). *Check:* grep and enumerate every import site, then
   convert each to `core.writes`. `test_core.py` (27 refs) and `test_arcs.py`
   (14) are the two big ones.
2. `test_story_describe.py` has its own `ALL_TOOLS` list (`:15`) that is
   **missing `story_draft`** — a gap task 28 left. Fix it in this phase, and
   check the same list for the new `story_admin`.
3. `test_plugin_registration.py`'s `TOOLS` (`:28`) and the count `12` must
   become 11 and include `story_admin`.
4. `__init__.py`'s dashboard hook tuple (`:216`) names `story_edit` and
   `story_create` by string. They must be removed, leaving
   `("story_dashboard", "story_memory", "story_draft")`. *Check:* read the
   `elif` chain at `:226-239` — the `story_draft` commit gate must survive
   untouched.
5. `tools/__init__.py` (`:13-14`) imports both modules.

**Check** — the full suite green at **fewer tests than 758 but the same
pass count** on everything that was not a duplicate. Any test that was only
covering a tool-boundary string format and no longer has a subject should be
deleted, not ported. State the new number and say why it moved.

### Phase 5 — Close the bypass, verify end to end

**Assumptions to verify**

1. The model genuinely cannot reach the authoring path. *Check:* after
   registration, assert `story_create` and `story_edit` are absent from both
   `register()`'s output and `plugin.yaml`. This is the point of the task.
2. `core/drafts.py`'s user-facing strings still name a tool that exists. Two
   places reference the old names in text the **model reads**:
   `core/drafts.py:92` (`"Call story_create(entity_type='project') directly."`)
   and `:552` (`story_edit(action="restore")` in the delete preview). Both
   must point at `story_admin`. *Check:* grep `core/drafts.py` and
   `tools/story_draft.py`'s SCHEMA description — the latter also tells the
   model to use drafts "instead of story_create / story_edit", which is now
   a reference to tools it cannot see.

**Check** — a manual end-to-end against a real project: stage a batch, confirm
nothing changed, commit, confirm it did, and confirm a project creation and a
purge still work through `story_admin`. Then confirm the model-facing tool
list is 11 and contains no authoring path.

**Result — both assumptions hold, verified by execution rather than by eye.**

*Assumption 1* was true but **unenforced**: nothing in the suite asserted it,
so a future change could have reopened the path silently. `TestNoDirectAuthoringPath`
now asserts both names are absent from `register()`'s output, from
`plugin.yaml`, and from disk. It was checked against an injected
`tools/story_create.py` and failed as it should — a guard that cannot fail is
decoration.

*Assumption 2* was already satisfied by Phase 4. `core/drafts.py:92` and `:538`
and `story_draft`'s SCHEMA all name `story_admin`, which exists. The pointer
cannot dangle: `set(registered) == set(TOOLS)` already pins the tool set.

**End-to-end: 21/21 against the real handlers on a real project on disk.**

| Step | Result |
|---|---|
| `create_project` | project folder + database created |
| stage a 2-entity batch | **no entity rows written (1 → 1), no prose written**, 452-char preview returned for the user to read |
| commit | both entities and their prose landed |
| delete via draft, then `restore` | flagged, not removed; restore brought it back |
| `list_projects` | finds the project without opening a database |
| `delete_project` | refused without `delete_confirm`, removed with it, project survived the refusal |
| `purge` | refused without `purge_confirm`; **a confirmed purge still spared a fresh delete** — the 30-day age floor held — and removed it at `older_than_days=0` |

Model-facing list: **11 tools**, no authoring path. `story_draft` is the only
route to a create, edit, delete or reorder.

**One finding worth keeping.** The age floor is invisible unless you test for
it: a confirmed `purge` on a just-deleted entity returns `success: True` with
`purged: []`. That is correct — the entity is still restorable — but a caller
checking only the success flag would read it as "purged". The empty `purged`
list is the signal, and it is the right one.

---

## Deferred

- **Skill text.** Still its own work, once the app is complete. Two rules must
  be written down when it happens: *stage when the change is still being
  decided, write directly when the user has already decided* — and the second
  is now moot for authoring, since there is no direct authoring path. What
  remains is: `story_admin` is never staged, and projects cannot be drafted.
- **Staleness detection** on edit ops. `ponytail:` no check.
- **Draft TTL.** A stale draft is inert.

## Out of scope

- Renaming `story_draft`. It is correct.
- Moving `purge` / `restore` into `core/`. They are admin-only with no other
  caller; `core/` should not hold code nothing in `core/` calls.
- Any backward compatibility. Nothing has shipped.

---

# Final brief — Phases 1, 3, 4, 5

**Status: complete.** 814 passing (811 after Phase 4, +3 for the Phase 5 canary).

## The test number, and why it moved

819 → 811. Every drop is accounted for; none is lost coverage.

| Δ | Cause |
|---|---|
| −2 | `test_story_describe`'s enum parametrize: the `story_create` and `story_edit` params died with the modules. The guard still runs for `story_retrieve` / `story_describe`. |
| −4 | `test_plugin_registration`'s `TOOLS` 13 → 11, across two parametrized tests. |
| −2 | `preview_reorder` and its two tests — see below. |
| +3 | `TestNoDirectAuthoringPath`, the Phase 5 canary. |

## What Phase 4 actually removed

`tools/story_create.py` and `tools/story_edit.py`, their `register()` calls,
the `tools/__init__` imports, the `plugin.yaml` entries, and the two dead
names in the dashboard-refresh tuple. Verified for real, not just by test:
`register()` emits 11 tools and neither deleted name appears.

**Model-facing text was repointed, not left dangling.** `story_draft`'s
description now reads as the only way to create, edit or reorder an entity —
it previously told the model to prefer draft over create/edit, which after
the deletion would have been a preference with nothing to prefer over.
`restore` and `create_project` now name `story_admin`.

## `preview_reorder` — resolved, not deferred

Phase 1 flagged this for re-check. `story_edit` was its only caller and the
draft preview renders a reorder inline (`_render_reorder`), so nothing calls
it. Dropped, per the plan's own instruction.

## Two things the plan's assumptions did not anticipate

1. **`test_plugin_registration` asserted a hardcoded `13`.** It was not in
   the plan's list of things to update, and it failed only after the files
   were gone. It now compares against the `TOOLS` list, so dropping a tool
   can never silently desync it again.
2. **A layer-inversion guard earned its keep.** `test_core_never_imports_tools`
   (an AST scan) is what proves `core/` no longer reaches up into `tools/`.
   It was verified to fail on an injected import, so it is a real guard and
   not decoration.

## Deferred — out of scope, needs your call

**`skills/story-editor/` and `skills/story-loader/` are unregistered
directories that document the deleted tools.** Neither appears in
`provides_skills` nor in `_register_skills`, so nothing loads them today —
they were already dead before this task. They now also describe a tool
surface that no longer exists. The registered skill,
`skills/hermes-story-architect/`, is clean.

I did not touch them: they are not in the plan, and deleting skill
directories is a structural decision that is yours. Either remove them or
rewrite them against the draft-based surface.

## Note on a boundary I crossed deliberately

Phase 5 owns the `core/drafts.py` model-facing strings. I fixed two of them
anyway, because Phase 4 deleted the tools they named and leaving them would
have meant closing my phase with the plugin pointing at nothing.

## Method note

Two scripted conversion passes were reverted. Regex cannot find the end of a
nested dict argument; the first mangled `str(tmp_path)` and the second ate
the variables its own output depended on. The pattern that held throughout
is that a converter's output must be checked against a real run rather than
trusted because it parsed.
