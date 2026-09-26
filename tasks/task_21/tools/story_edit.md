# story_edit — FIX + RENAME (P1)

`tools/story_edit.py` (349 lines) · `core/entity.py:152 _RELATION_FIELDS`

## What it does
Action protocol: `edit_note` (upsert fields/sections/relations), `delete_entity`, `reorder`. All DB-native, all transactional. **The refactor to DB is done properly** — this is the best-structured tool in the set.

## Findings

1. **The action is named `edit_note` and there are no notes.** It writes `entities` / `entities.extra` / `relations` / `sections`. The name is a file-era leftover and actively misleads. Rename to `update_entity` (and update `story_describe` at the same time — see `story_describe.md`).
2. **No dry-run.** For an LLM writing on behalf of a human, "show me the diff" is the single most valuable missing feature. The tool already computes `column_updates` / `extra_updates` / `section_updates` as separate dicts before applying them — a `dry_run: true` flag that returns those dicts and the relation deletes/inserts is ~15 lines. **Highest value-per-line change in this review.**
3. **No confirmation on `delete_entity`.** It is a hard delete with no undo and no backup call. Non-structural children are cascade-deleted silently. For a tool a human is watching, this needs either a `confirm` flag or a soft-delete. `story_backup` exists and is never called from here.
4. **Relation handling is not symmetric with `core/entity.py`.** `story_edit` writes relation fields for *any* field in `_RELATION_FIELDS`; `relations_for_insert` (`core/entity.py:264`) special-cases `plot_setup`/`plot_payoff` to read `scene_id`+`description` from dicts, but `story_edit` reads `scene_id`/`description` for *every* list kind. For scene `characters` (a list of plain strings) the dict branch is dead code; for `plot_crisis`/`plot_climax` the two implementations disagree about whether a dict is expected. **Real inconsistency, not cosmetic.**
5. **Section bodies are overwritten wholesale, and only upserted — never deleted.** A section removed from the agent's intent survives. Probably fine; worth being deliberate.
6. **`summary` is required but unused** beyond echoing into the message. Cheap to keep (good for the human reading the transcript), but it shouldn't be required.
7. **Descriptions still say "frontmatter"** (line 24, line 157 of describe) — file-era language, same class as #1.
8. **Reorder is scene/sequence only** and requires the full ordered list. Correct and safe (validates same-parent). Acts can't be reordered. Probably intentional; confirm.

## Work
1. `dry_run: true` → return the computed updates without writing. (Do this first.)
2. Rename `edit_note` → `update_entity`; drop "frontmatter"/"note" wording everywhere.
3. Make `delete_entity` call `story_backup` first, or require `confirm: true`.
4. Unify relation writing: have `story_edit` call `relations_for_insert` instead of reimplementing it. One implementation, both call sites agree.

## Open question
Is hard delete ever right? Soft delete (a `deleted` flag filtered out of every read) costs a WHERE clause in ~6 readers. Given "assist a human", you may want it — but it's a real cost, and `story_backup` + `dry_run` may be enough. Your call.
