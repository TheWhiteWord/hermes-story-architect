# story_export

✅ **Finalized.** Source: `tools/story_export.py`. Tests: `tests/test_export_sweep.py` (10).
Full suite 389 passed. No existing test needed changing.

Writes the whole database out to Markdown. The **mirror** of `story_import`.

## Parameters

| Param | Type | Required |
|---|---|---|
| `project` | string | yes |

## The writing side was already correct

Import → export → wipe DB → re-import is byte-identical:

```
entities   identical: True (33 rows)
sections   identical: True (287 rows)
relations  identical: True (12 rows)
```

Including a character created at runtime with `story_create` — it exports, survives the wipe, and
comes back. Aware of the two awkward cases already handled: `character_scene` relations are stored
from the character side, and plot beats carry a `note` alongside the scene id.

## The bug: export could write, but never stop

An entity deleted from the database left its `.md` behind. The next `story_import` read that file
and **resurrected it**:

```
delete kael from db → export → kael.md still there → reimport → kael is back
```

A delete that doesn't survive a round trip is not a delete. The database is the source of truth;
export has to mirror it in both directions.

## The fix: a manifest, not a guess

The first version swept *any* `.md` in a managed folder that the export hadn't just written. That
deleted a hand-authored note the database had never seen — export would eat the user's own writing.

So the sweep only considers files listed in **`.story/exported.json`**, the paths the last export
wrote. It can only ever remove what this tool created:

| Situation | Result |
|---|---|
| File in the manifest, no longer in the DB | Removed |
| Hand-authored note, never exported | **Untouched** |
| First export ever (no manifest) | Sweeps nothing |
| Corrupt manifest | Ignored, export succeeds |
| Second export, nothing changed | `files_removed: []` |

Emptied `arcs/{character}/` folders are pruned too.

## I introduced a project-deleting bug here

The manifest stores project-relative paths; the set it was compared against held absolute ones, so
**nothing ever matched** and the second export deleted all 34 notes of the whole project. It passed
`test_round_trip_preserves_data`, which only checks a *single* export.

Caught by re-running the real sequence rather than trusting the suite. It is now pinned by
`test_second_export_removes_nothing` and `test_repeated_exports_keep_every_note`, and
`test_corrupt_manifest_is_ignored_not_fatal` covers the degenerate case.

Worth remembering: **a test that exports once cannot catch an export that is wrong on the second
run.** Every idempotency bug lives in the gap between run 1 and run 2.

## Response

```json
{"success": true, "message": "Exported stc",
 "files_written": 34, "files_removed": []}
```

`files_removed` is the honest signal — non-empty means notes were deleted, and the paths say which.

## Design decision: no recycle bin

`test_round_trip.py` already asserted it: *"No recycle bin with hard delete — soren.md is simply
absent."* The `_recycle-bin` folder appears in the fixture and is skipped by import, but nothing in
the code creates it. That is a deliberate hard delete, so the sweep matches it rather than inventing
a second convention.

## Not a backup

The tool description says so and it matters: export writes readable notes, `story_backup` copies
the database. Export cannot restore field values the Markdown format does not carry.
