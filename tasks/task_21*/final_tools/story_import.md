# story_import

✅ **Finalized.** Source: `tools/story_import.py`. Tests: `tests/test_import_safety.py` (8 tests).
Full suite 361 passed. No existing test needed changing.

The only tool that reads Markdown, and the only one that can **destroy work**. It deletes every row
in the database and rebuilds from the Markdown files. Because the database is the source of truth
and Markdown is only its projection, anything that exists *only* in the database is lost.

## Parameters

| Param | Type | Required | Notes |
|---|---|---|---|
| `project` | string | yes | Slug, name, or path |
| `dry_run` | boolean | no | Report what would be lost. Changes nothing. |
| `confirm` | boolean | see below | Required to proceed when work is at risk |

## How the guard behaves

| Situation | What happens |
|---|---|
| `dry_run: true` | Full report, **nothing changes** |
| Work at risk, no `confirm` | **Refuses**, and saves a backup first |
| Work at risk, `confirm: true` | Imports, and returns the backup path |
| Nothing at risk | Imports normally — no friction |

The common case (a project that matches its Markdown) never asks for confirmation.

## Example — the real sequence

**1. Look before leaping**
```json
{"project": "stc", "dry_run": true}
```
```json
{"entities_in_db": 30, "would_be_destroyed": ["nova"], "dry_run": true,
 "warning": "1 entities exist ONLY in the database and would be DESTROYED: nova",
 "next_step": "Run story_export first to keep them, or story_backup to save a restorable copy. Then re-run with confirm=true to import anyway."}
```

**2. Without `confirm` it stops**
```json
{"success": false,
 "error": "Refusing to import: 1 entities exist only in the database and would be destroyed.",
 "would_be_destroyed": ["nova"],
 "action_required": "A backup was saved. Run story_export to keep these entities in Markdown, then re-run with confirm=true to import anyway.",
 "hint": "Run with dry_run=true first to see this report before doing anything."}
```

**3. With consent it proceeds**
```json
{"success": true, "message": "Imported stc", "backup_created": "story_20260926_001849.db"}
```

**Every successful import returns a backup path.** The wipe is never irreversible.

## What "at risk" means, precisely

An entity is at risk when it is in the database and **has no Markdown note behind it**. An entity
created at runtime with `story_create` has no `.md` — that is exactly the set the wipe deletes.

`project` rows and arc beats are exempt: the project always re-imports, and arc beats live in
`arcs/{character}/{beat}.md` (keyed `{char}-{beat}`, and sometimes stored typed as `character`).

The check is deliberately **one-directional**. An entity with a note file is never reported as at
risk, even if the importer keys it differently. A missed warning only means the guard stays quiet;
a false "you will lose data" would block every legitimate re-import. That failure mode actually
occurred while building this — the first version reported 11 false positives on the fixture and
blocked all 14 round-trip tests — and is now pinned by
`test_no_false_positive_on_clean_project`.

## Errors

| Condition | Response |
|---|---|
| Project markdown missing and no DB project | `{"error": "Project markdown not found and no project DB exists"}` |
| Invalid `memory.md` | `{"error": "Invalid story memory: ..."}` |

## A second path: memory only

If `project.md` is absent but a project row exists, the tool imports **only** `memory.md` and leaves
every other table untouched. It is the one non-destructive use of this tool.

## Precedence, which is handled well

Existing DB memory is written back after a wipe, and `memory.md` wins if present. That was already
right and is unchanged.

## What was fixed

1. **The data loss is no longer silent.** Reproduced first: a character created with `story_create`
   was simply gone after a re-import, and the tool reported `success: true`.
2. **`dry_run`** — full report, no changes.
3. **Refusal without `confirm`**, with a backup taken at the moment of refusal.
4. **A backup on every successful import**, returned as `backup_created`.
5. Dead imports removed (`list_sections`/`get_section`/`empty_memory` in three functions that never
   used them).
