# story_import — HARDEN (P1, data-loss risk)

`tools/story_import.py` (371 lines)

## What it does
Walks the Markdown vault → wipes `relations`/`sections`/`entities` → re-imports everything. Also has a narrow "import memory only" path when `project.md` is absent.

Correct in intent (Markdown → DB is the one legitimate Markdown boundary) and the round-trip is tested. The problem is that it is **destructive and unguarded**.

## Findings

1. **`_clear_all` deletes every row before importing** (line 96–98). Anything created via `story_create` or `story_edit` since the last export — i.e. **all runtime work** — is destroyed. The DB is authoritative; Markdown is the stale projection. Re-importing "to fix something" silently reverts the project to its last export.
2. **No dry-run, no confirm, no backup.** Given the tool above returns "Database not found. Run story_import first" for unrelated errors (see `story_search.md`), an agent following that advice **destroys the project**. This is the worst failure chain in the toolset.
3. **Memory preservation is handled well** (lines 37, 78–83) — existing DB memory is written back after a wipe, and `memory.md` wins if present. That is the right precedence and it should be the model for the rest of the tool.
4. **Inconsistent relation coverage.** `_insert_relations` handles scene/plot/location/world. It does **not** handle `relationship` — `characters` and `perspectives` for relationships are dumped into `extra` by `_extra_for` and never become rows. That is consistent with `core/constants.py:187` ("frontmatter-only"), so it round-trips — but it means relationship data lives in a different storage layer from scene data, and `_RELATION_FIELDS["relationship"]` is `{}` while the schema has the fields. See cross-cutting #5.
5. **`_insert_relations` uses `INSERT OR IGNORE`, but there is no unique constraint** on `(from_id, to_id, kind)` — so `OR IGNORE` does nothing and duplicate relations are inserted on re-import of a scene with a repeated character. Check the schema; if there's no unique index, add one or drop the pretense.
6. **`_columns_for` duplicates `columns_for_insert`** (`core/entity.py:225`) with a *different* skip-set strategy. Two field-mapping implementations, already divergent (e.g. `arc_beat` `scene` handling).
7. **Dead imports** in three functions (`frontmatter`, `list_sections`, `get_section`, `empty_memory` imported and unused).
8. **Half-transactioned early-exit path** (lines 56–67): the memory-only path does `conn.close()` inside the `try` and returns, while the `except` also closes — fragile but currently correct. Worth simplifying while in there.

## Work (priority order)
1. **`dry_run: true`** — report what would be deleted/imported, change nothing. Cheapest possible protection, biggest possible save.
2. **Require `confirm: true` when `_clear_all` would drop rows** that are not in the Markdown (i.e. real runtime work). Or: back up to `.story/story_{ts}.db` automatically before wiping. `story_backup` already does the copy.
3. Add a unique index on `relations(from_id, to_id, kind)`, or stop pretending `OR IGNORE` works.
4. Make `_columns_for` call `columns_for_insert`. Delete the duplicate.
5. Delete the dead imports.

## Open question
Should import be **merge** rather than wipe? Merge (upsert per entity) preserves runtime-only entities and is arguably more correct, but silently keeps stale entities that were deleted in Markdown. Wipe + dry-run + backup is simpler and more predictable. **I'd keep wipe, add the guard.** Tell me if you want merge semantics.
