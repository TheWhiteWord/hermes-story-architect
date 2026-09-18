# Soft-Delete Re-Create Issue — DEFERRED

**Status:** Deferred
**Discovered:** 2026-09-18 during dashboard-live-test project build
**Severity:** Medium (blocks re-creation of soft-deleted entities)

## Problem

When an entity is soft-deleted (`is_deleted=1`) and then re-created via `story_create`, the INSERT fails with `UNIQUE constraint failed` because:

1. **Entity PK conflict:** The soft-deleted row still occupies the PK. The create handler's uniqueness check was fixed to exclude soft-deleted rows, but the actual INSERT still conflicts.
2. **Stale relations:** Soft-deleted entities leave behind relations (e.g., `arc_beat`, `character_scene`) that block re-creation when the new entity has the same ID.
3. **Stale sections:** Sections from the soft-deleted entity remain and conflict with new section inserts.

## Root Cause

`story_delete_entity` sets `is_deleted=1` but does not cascade-delete related rows in `sections` or `relations`. The `story_create` handler was patched to clear stale sections/relations before insert, but the cleanup logic has been fragile and incomplete across multiple fix attempts.

## Affected Flow

- `story_delete_entity` → soft-deletes entity → relations/sections remain
- `story_create` (same ID) → INSERT fails on PK or relation/sections UNIQUE constraints

## Agreed Solution Direction

Fix `story_create` to **hard-delete** any soft-deleted entity with the same ID (and its cascaded sections/relations) before inserting the new entity. This is the cleanest approach — soft-delete is a UI-level concept; re-creation should fully replace.

Alternatively, fix `story_delete_entity` to hard-delete when the entity is being permanently removed (but this loses the recycle-bin semantics).

## Notes

- Multiple incremental patches to `story_create.py` were applied during the dashboard-live-test build, each fixing one edge case but revealing another. The accumulated patches are in the `sqlite-migration` branch.
- The `get_db` connection was changed to autocommit mode (`isolation_level=None`) to avoid nested-transaction errors.
- Arc creation specifically was blocked by stale `arc_beat` relations referencing the character slug (`test-hero`) as `from_id`.

## Related Files

- `tools/story_create.py` — entity creation with stale-data cleanup
- `tools/story_edit.py` — soft-delete handler
- `core/db.py` — `get_db` connection setup
- `core/entity.py` — `columns_for_insert` (arc ID construction fix)
