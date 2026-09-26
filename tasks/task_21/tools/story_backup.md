# story_backup — KEEP

`tools/story_backup.py` (45 lines)

## What it does
Copies `.story/story.db` to `.story/story_{YYYYmmdd_HHMMSS}.db`.

## Findings

The whole file:

1. Resolves the vault path (the correct one-liner form), resolves the project, checks the DB exists, `shutil.copy2`, returns the path. Nothing to argue with.
2. **Not mentioned in `story_describe`.** Invisible to the agent. If the agent is meant to be able to back up before a risky operation, it can't discover that it can.
3. **Never called by any other tool.** `story_import` wipes the DB without calling it; `story_edit`'s `delete_entity` hard-deletes without calling it. The tool that prevents data loss exists but is not wired to the operations that risk it. **This is the highest-leverage wiring in the whole review** — see below.
4. Backups accumulate with no pruning. A project edited daily accumulates one file per edit forever. Not urgent; a count-based cleanup in export/import would be enough.
5. No `--keep N`. Not needed.

## Work
1. **Wire it in.** Call `story_backup` automatically at the start of `story_import`'s wipe path, and require (or suggest) it before `story_edit`'s `delete_entity`. ~5 lines total, and it converts the two data-loss tools from "dangerous" to "recoverable".
2. Add it to `story_describe` so the agent knows it exists.
3. Optional: prune old backups on backup (keep the last N).

## Note on merging
Tempting to fold this into `story_export` ("project, mode: export|backup"). **Don't** — backing up without exporting is the safe, common operation, and merging couples a 5-line safe action to a 230-line complex one. The cost of the separate tool is one schema entry; the benefit is that the dangerous path (`import`) can't be reached by accident while backing up.
