# Task 29 — Tool surface: split authoring from admin

**Status: design note, not a plan.** Nothing implemented. Independent of task
28, but **blocked by it** — see *Sequencing*.

**Origin:** the question task 28 raised. Once `story_draft` exists, what are
`story_create` and `story_edit` *for*? Their names claim entity authoring; if
drafts do the authoring, the names are lies.

---

## The observation

Once drafting exists, entity authoring happens in exactly one place. What
remains in the two legacy tools is three capabilities that are deliberately
**not** proposals:

| capability | today | draftable? | why not |
|---|---|---|---|
| create entity | `story_create` | **yes** | that is what drafts are for |
| `edit_note` / `delete_entity` / `reorder` | `story_edit` | **yes** | same |
| **create project** | `story_create` (separate branch, `story_create.py:108`) | **no** | a project that does not exist has no `story.db` to hold a draft |
| **`purge`** | `story_edit(action="purge")` | **no** | irreversible; `purge_confirm` must contain the literal `DELETE <slug>` |
| **`restore`** | `story_edit(action="restore")` | **no** | recovery from a purge/delete, not a proposal |

So `story_create` would be a tool that cannot create, and `story_edit` a tool
whose surviving actions are `purge` and `restore`. Three operations, sharing
nothing but "dangerous, infrequent, and never staged".

## The target surface

**`story_draft`** — the only way to author entity content. `stage` / `commit` /
`discard` / `list`.

**`story_admin`** — the three operations above, as an `action` enum:

```
story_admin(action="create_project" | "purge" | "restore", ...)
```

One tool. The name says what the three have in common without needing a
sentence of explanation, and an operation that requires typing
`DELETE <project-slug>` is one you want visibly separated from ordinary
authoring.

## What moves where

The write functions **stay put**. Task 28's commit loop dispatches into
`story_create.handler` and `story_edit.handler`; if those handlers moved into
`story_draft`, commit would be calling itself. What moves is the *tool
surface* — the `SCHEMA`, the action enum, the registration — not the code that
does the work.

- `_purge_deleted` (`story_edit.py:561`) and `_restore_entity` (`:626`) move to
  `tools/story_admin.py`. Their bodies are unchanged; they already take
  `(project_path, target, args)`.
- `_create_project` (`story_create.py:274`) moves likewise. It takes
  `(slug, frontmatter_data, root_path)` — note it uses `root_path`, not
  `project`, because the project does not exist yet. That asymmetry is real and
  must survive the move.
- `_delete_entity` (`:674`) **stays in the draft path** — soft delete is
  draftable, per task 28's op vocabulary. `story_draft` commit calls it with a
  synthesised `confirm: true`.

## Sequencing — required, and independent of task 28's plan

**Do this after drafts ship. That ordering is fixed; the reasoning is not
evidence-based, it is a bypass.**

The earlier version of this note argued the split should wait until drafts had
been used for a while, so the cut could be driven by observation rather than
prediction. **That argument is wrong.** A tool the model can call is a
procedure the model can skip:

- Leaving `story_create` registered means "stage first, commit on confirmation"
  is a *suggestion*. Suggestions are exactly what gets dropped under time
  pressure — and the confirmation loop task 28 builds is worthless if the back
  door is open beside it.
- Leaving `story_edit` registered means `edit_note`, `delete_entity` and
  `reorder` stay reachable directly, so the same bypass exists for edits.

That is not a naming concern. It is the feature's guarantee.

So the split is **required**, and it stays a **separate task** only because it
is a self-contained piece of work that task 28's plan does not need to
complete. Task 28 ships drafts; this task closes the bypass afterwards. If the
two are ever reordered, this one goes **first** — drafts without it are a
suggestion, and this without drafts has nothing to route.

### What the split does and does not save on schema size

The schema-size argument is real but much smaller than it first appears.
Measured: `story_create` 14,667 chars, `story_edit` 2,680, `story_load` 1,934,
`story_describe` 519 — `story_create` is roughly half the total across all
eleven tools.

But the split does **not** remove that 14,667. The entity field schema moves
into `story_draft`'s create op, which needs the same fields. Net saving is
`story_edit`'s 2,680.

The genuine benefit is structural, not quantitative: once split,
**`story_draft` is the only tool whose schema mentions entity fields at all.**
One place to keep accurate, and no second tool whose field descriptions can
drift out of sync with the first. That is worth having — as a consequence of
closing the bypass, not as an argument for it.

## Cost, when it happens

**No backward compatibility to preserve — the plugin has not shipped.** So this
is a rename-and-move, not a deprecation. No shims, no alias tools, no
compatibility layer, no migration for existing users. Whatever the split
breaks, it breaks now and gets fixed now.

What is left is ordinary work, not compatibility overhead:

- `plugin.yaml` `provides_tools`: remove `story_create` and `story_edit`, add
  `story_admin`. Net tool count unchanged (11 → 11 with `story_draft`).
- `__init__.py`: unregister both, register `story_admin`. The dashboard
  `post_tool_call` hook tuple (`:206`) references `story_edit` and `story_create`
  by name and must be updated — and must then decide whether a *committed draft*
  refreshes it (task 28 already requires that gate).
- `tests/test_plugin_registration.py`: `TOOLS` list and the count assertion.
- **~14 test files** import or exercise `story_create` / `story_edit`.
  `test_purge.py`, `test_edit_safety.py`, `test_soft_delete.py`,
  `test_delete_cascade.py` and `test_create_sections.py` need real edits; the
  rest need import fixes. That is a morning's mechanical work, and the tests
  are the thing that makes the split verifiable at all.
- One one-time data move: the `save-the-children` project used for development
  testing. Nothing in the schema changes, so it needs no migration — but if the
  split ever does touch stored data, that project is the only thing to fix up.

## Assumptions to verify before implementing

1. `purge`, `restore` and `_create_project` have no dependency on the
   `edit_note` / `delete_entity` / `reorder` code paths beyond what is already
   in `tools/story_edit.py`. *Check:* read `_purge_deleted` and `_restore_entity`
   for calls into the other helpers.
2. `_purge_deleted` uses `conn` from `get_db` directly and does not assume a
   prior `BEGIN` from a sibling action.
3. Nothing outside the plugin calls these handlers by name — `__init__.py` and
   the tests are the whole surface. *Check:* grep for
   `story_create.handler` / `story_edit.handler` outside `tools/__init__.py`.

## Out of scope

- Renaming `story_draft`. It is correct.
- Merging `purge` and `restore` into a single "manage deleted entities" action.
  Two actions, one enum, no reason to complicate.
- Moving the write functions out of `tools/story_create.py` /
  `tools/story_edit.py` into `core/`. That is a tidier architecture and worth
  doing eventually, but it is not what this task is about — and task 28's
  commit loop depends on those handlers being callable where they are.
