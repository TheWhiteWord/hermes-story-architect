# Task 28 — Draft staging: propose changes, commit on confirmation

**Status: design of record.** Nothing implemented. This file states *what* to
build, so an implementer does not have to re-derive it.

**Origin:** design discussion. The agent must currently write to the DB the
moment it creates or edits an entity, but entity work is iterative — an entity
is discussed, half-formed, revised, and only then agreed. `story_load` already
has `view="unfilled"` (what is still incomplete), so incompleteness is a
first-class concept; what is missing is the distinction between *agreed but
thin* and *not yet agreed*.

---

## The problem

Three gaps, in increasing order of how much they hurt:

1. The agent commits before the user has seen the result.
2. Section prose exists as a notepad for thinking, but has no link to a
   *proposed* set of field values.
3. **Screenwriting is never one entity.** A new scene implies a location, two
   character-appearance relations, a sequence `order_key`, and a
   `value_at_close` that must agree with the sequence's `value_at_open`. That
   is one decision, six changes, five entities. Per-entity staging would mean
   staging six drafts and asking the user to confirm six times.

Gap 3 decides the design. A per-entity mechanism does not survive contact with
real use.

## The design

**One table, per project, keyed by draft id, holding a list of ops.**

```sql
CREATE TABLE IF NOT EXISTS drafts (
    id         TEXT PRIMARY KEY,   -- e.g. d-3f2a
    ops        JSON NOT NULL,      -- current op list
    prev_ops   JSON,               -- op list before the last restage, for the diff
    summary    TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);
```

`prev_ops` exists for one reason: a restage must show what changed since the
last one, or "don't resequence" silently drops a queued op and the user cannot
tell it was dropped rather than never proposed. See the presentation decisions
in `chat-preview.md`; it is the only one of the seven that changes the data
model.

The table lives in the project's own `story.db`, so a draft is scoped to an
existing project and draft ids are unique within it by construction.

An op mirrors what the existing tools already accept, so staging is the same
computation as `dry_run` with a different sink:

```json
[{"op": "create",  "type": "scene", "slug": "threshold",
  "frontmatter": {"sequence_id": "act-one", "cast": ["kael"]},
  "sections": {"Notes": "..."},
  "summary": "New threshold scene"},
 {"op": "edit",    "entity_type": "location", "entity_id": "central-room",
  "data": {"mood": "claustrophobic"}, "summary": "Tighter room"},
 {"op": "delete",  "entity_type": "character", "entity_id": "mira",
  "summary": "Cut Mira"},
 {"op": "reorder", "entity_type": "sequence", "ordered_ids": ["...", "..."],
  "summary": "Resequence act one"}]
```

Three shape facts, each verified against the code — an op that gets these
wrong is silently dropped at commit:

- **Relations live inside `frontmatter`, not in a `relations` key.**
  `story_create` has no `relations` argument; `relations_for_insert`
  (`core/entity.py:300`) derives relation rows from the merged frontmatter.
  An op passing a separate `relations` list would lose every relation.
- **`project` is nested differently per op.** `story_create` reads top-level
  `args["project"]`; `story_edit` reads `target["project"]`
  (`tools/story_edit.py:99`). The commit loop owns this translation, not the
  caller.
- **`summary` is required** by `story_edit` (`"required": ["action","target","summary"]`).
  Every edit and delete op carries one. A create op carries one for the
  agent-facing message.

### Op vocabulary

| op | replays to | notes |
|---|---|---|
| `create` | `story_create.handler` | `type` + `slug` + `frontmatter` + `sections` |
| `edit` | `story_edit.handler(action="edit_note")` | `entity_type` + `entity_id` + flat `data` |
| `delete` | `story_edit.handler(action="delete_entity")` | reversible; `restore` already exists |
| `reorder` | `story_edit.handler(action="reorder")` | `entity_type` + `ordered_ids` |

`delete` is in the vocabulary because a discussion routinely concludes that
something should go away, and a draft that cannot express that forces the agent
to break out of the staging flow for a direct write.

### One mechanism covers every case

| Case | Ops | Effect on `entities` |
|---|---|---|
| staged create | `[{op:create}]` | nothing — the row does not exist yet |
| staged edit | `[{op:edit}]` | nothing — the row is untouched |
| staged batch | any mix | nothing |

A staged create occupies nothing: no other entity can reference it until
commit, because the row does not exist. Mid-discussion that is correct; a draft
that must be referenced by a committed entity has to be committed first.

## Tool surface

**A dedicated `story_draft` tool**, a peer of `story_create` / `story_edit`.

`action`: `stage` | `commit` | `discard` | `list`

- `stage` takes the op list, returns `{draft_id, preview_md, validation}`
- `commit` / `discard` take `draft_id`
- `list` returns `{id, summary, created_at}` for every open draft

`story_create` and `story_edit` are **unchanged** — they keep writing to the DB
directly, for the cases where the user asked for exactly that.

Why a dedicated tool and not a `draft` param on the existing two:

- A batch draft spans a create, an edit and a reorder. It has no valid
  `target` for `story_edit` (which requires one `entity_type` + `slug`) and no
  valid `action` on either tool. The case that justifies the whole design is
  the one the param cannot express.
- The op list is a different JSON shape than any existing tool accepts.
  Squeezing it into `story_create`'s flat `frontmatter` or `story_edit`'s flat
  `data` is a hack, not a fit.
- Draft lifecycle is about the *proposal*, not the entity. Folding it into
  `story_edit`'s five-value `action` enum makes every reader of that enum ask
  "is a draft an edit?"
- `story_create`'s schema is a generated blob covering every field of every
  entity type. A batch op list on top of that is noise.
- Discoverability: `story_draft(action=list)` at session start is one obvious
  call.

Costs accepted: one more registration (bump the count in
`tests/test_plugin_registration.py:86` from 11 to 12), and one more tool to
describe in the skill.

## Commit replays the existing handlers

Commit does **not** re-implement writes. It dispatches each op in-process to
the handler the tool already exposes, so the agent makes **one** call to commit
and the number of agent-visible tools involved in saving is one.

```python
for op in sorted_ops:            # create, edit, delete, reorder
    r = dispatch(op)             # -> story_create.handler / story_edit.handler
    if json.loads(r).get("error"):
        return partial_failure(r, landed)   # draft row KEPT
delete_draft_row(draft_id)
```

### The guarantee: atomic per op, resumable per batch

`story_create` runs in autocommit mode with no transaction
(`tools/story_create.py:203` — *"there is no open transaction"*); `story_edit`
wraps each call in its own `BEGIN`/`COMMIT`. Each handler also opens and
closes its own connection, which `tests/test_connection_lifecycle.py` asserts
is deliberate. So a multi-op draft **cannot** be one transaction without
threading a shared connection through every write path in the plugin — and
that refactor is not worth buying.

What commit actually guarantees:

- **Each op is atomic.** An op either fully applies or does not.
- **The batch is resumable.** On failure the draft row is **kept**, and the
  response names exactly which ops landed. Nothing is lost: every applied write
  was individually valid. The agent re-stages the remainder and commits again;
  ops that already landed refuse correctly (a `create` whose slug now exists
  fails on uniqueness).

The failure mode is a *temporarily inconsistent* project, not lost work, and
the draft row is the resume token. This is a better guarantee than
all-or-nothing for an iterative workflow, where partial progress is the normal
case rather than the exception.

### Three things the commit loop must get right

- **Ordering.** Creates before edits before deletes before reorders, or a
  draft that creates a scene then sets its `order_key` fails on an unknown id.
  Sort inside commit; do not make the caller get it right.
- **The delete confirmation.** `delete_entity` requires `confirm: true`. The
  commit loop synthesises it. This is correct — the user confirming the draft
  *is* the confirmation — but it must be an explicit line with a comment saying
  why, or a later reader will take it for a safety bypass.
- **Staleness.** A draft staged yesterday commits against today's DB. A
  `create` op whose slug was taken since errors out, which is correct. An
  `edit` op silently overwrites whatever changed in the interim.
  `ponytail:` no staleness check. Add an expected-`from` per field at stage
  time and refuse on mismatch if this ever bites — it has a real ceiling
  (every commit fails on a stale-but-harmless field) and an upgrade path.

## Presentation

`stage` and `commit` both return a **ready-to-paste markdown block** in the tool
result — the same information `_preview_edit` returns today, rendered for a
human rather than a model. The agent relays it because the skill tells it to.

No Hermes hook, no `ctx.dispatch_tool`, no preview pane. The tool result *is*
the presentation. Check `tools/story_export.py` `_frontmatter_for` and
`core/screenplay.py` for an existing renderer before writing a new one — one
renderer, two callers.

## Validation

**At stage time: shape only.** Required fields present, enum values legal, slug
format. All checkable on the in-memory merged frontmatter, with no DB write.

**Not at stage time: cross-entity references.** `validate_plot_characters`,
`validate_scene_act_id`, `validate_arc_parents` (`core/entity.py:347-393`) each
open their own connection and read committed state, so a staged create's slug is
not there yet and every cross-op reference in a batch would report a false
error. Those surface at commit, where the earlier op has already landed. This is
`dry_run` over the op list with the reference checks deliberately skipped.

## Migration

`has_schema()` (`core/db.py:145`) checks only
`entities/relations/sections/sections_fts`, and read-only tools never call
`create_schema()`. Every existing project would therefore have no `drafts`
table — the same regression `tests/test_legacy_db_migration.py` exists for.

Add `ensure_drafts_table(conn)` alongside `ensure_soft_delete_columns`, called
from `get_db` so it runs on open, plus a legacy-DB test beside it.

## Consequences to accept

- **Every reader is untouched.** Drafts are not in `entities`, so
  `story_load`, `story_search`, `story_retrieve`, export and the dashboard need
  no changes at all. This is why a draft is a separate table rather than a flag
  on `entities`: a flag would have to be filtered into ~40 query sites, and on
  an edit it would hide a live entity from the project for the duration of a
  conversation about one field.
- **Projects are not draftable.** `_create_project` is a separate code path
  with a different arg shape, and a project that does not exist has no DB to
  hold a draft. `stage` refuses `type: "project"` with a clear error; project
  creation stays a direct `story_create` call.
- **Commit must refresh the dashboard.** The `post_tool_call` hook in
  `__init__.py:206` matches a fixed tuple that does not include `story_draft`,
  so a committed draft would otherwise change the DB and leave the dashboard
  stale. Add `story_draft` to the tuple **and** gate on the result indicating a
  commit — a *staged* draft must not regenerate the dashboard for a change the
  user has not accepted.
- **`story_import` leaves drafts alone.** `_clear_all` (`tools/story_import.py:208`)
  deletes from an explicit list — `relations`, `sections`, `entities` — and
  `drafts` is not in it, so drafts survive an import untouched. `memory` is
  already preserved the same way (`existing_memory` at `:144`, re-attached at
  `:188`); drafts need no special handling.
  A draft holding `op:create` for an entity that existed only in the DB is
  recreated on commit. That is the draft working, not data loss.
- **`story_backup` includes drafts** — `Connection.backup()` copies the whole
  file. Free, and correct.
- **Drafts survive `/new`**, but the agent must call `action=list` at session
  start to see them. That instruction goes in the skill.
- **Drafts do not expire.** A stale draft is inert; purging is a `discard`
  call. Do not add a TTL until it annoys you.
- **An edit op cannot touch a soft-deleted entity** — `_find_entity_id_db`
  filters `is_deleted=0`. Correct behaviour, but a draft staged before a
  delete commits into a refusal. Rare enough to leave.

## Guard tests

1. `stage` writes nothing to `entities`, `sections` or `relations` — assert row
   counts identical before and after.
2. `commit` of a failing multi-op draft keeps the draft row and names the ops
   that landed. (Per-op atomicity, per the guarantee above — not all-or-nothing.)
3. `discard` removes the draft and leaves the DB unchanged.
4. `stage` twice on the same `draft_id` **replaces** the op list rather than
   appending. Staging is a proposal, not a queue. The replaced list lands in
   `prev_ops` and the response reports the added / dropped / changed ops.
5. `commit` orders ops create → edit → delete → reorder, so a draft that
   creates a scene and then sets its `order_key` commits cleanly.
6. A staged batch with a `create` carrying `cast` produces relation rows —
   relations come from frontmatter, and an op that lost them would pass every
   other test.
7. A legacy DB with no `drafts` table is repaired on `get_db`.
8. Source grep: `is_draft` appears **nowhere** in `core/` or `tools/`. If it
   ever does, the design has drifted into the flag approach and lost edit
   staging.

## Three registration sites

`story_draft` must be registered in **three** places, not two. Missing the
first two is easy to do because `__init__.py` is where the real work happens.

1. **`__init__.py`** — `ctx.register_tool(...)` next to `story_create`.
2. **`plugin.yaml`** — add `story_draft` to `provides_tools`. This is not
   mentioned in the `provides_skills` / `provides_hooks` blocks, so it is easy
   to miss; skipped, the tool may register in code yet never reach the model.
3. **`tests/test_plugin_registration.py`** — add `"story_draft"` to the `TOOLS`
   list (line 27) **and** bump `len(registered) == 11` to `12` (line 86).
   Bumping the count alone is not enough: that list is what drives the four
   parametrised schema tests (has parameters, has description, `required` is a
   list, every property described). Without the list entry the new tool passes
   none of them.

## Implementation order

1. `ensure_drafts_table` in `core/db.py`, called from `get_db`; legacy test.
2. `core/drafts.py`: `stage` / `commit` / `discard` / `list`, the op sort, the
   dispatch loop, the partial-failure response, and the `prev_ops` restage
   diff.
3. `tools/story_draft.py`: `SCHEMA` + `handler`; register at all three sites
   above; add `story_draft` to the dashboard hook tuple with a commit gate.
4. Markdown renderer, to the seven decisions in `chat-preview.md` — one
   function, reused by the preview paths.
5. Guard tests 1–8.
6. Stage-time shape validation.

## Deferred: skill text

**Deliberately not part of this implementation.** Skill text is written once
the mechanics are settled and the app is complete, as its own piece of work.

It matters, though, so it is recorded here rather than forgotten: the other
eleven tools are self-describing (`story_describe` for fields, `story_load` for
structure), but there is no schema path to *"when should I stage rather than
write directly"* — and that judgement is the whole feature. Without it the tool
will ship working and unused. `SKILL.md` is 58 lines with a `references/`
subdir, so this is a short section plus a reference file.

Minimum content when it happens: when to stage versus write directly,
`action=list` at session start, and how to read a partial-failure response.
