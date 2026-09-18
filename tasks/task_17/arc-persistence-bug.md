# Arc Persistence Bug — story_create Returns Success But Entities Don't Persist

**Status:** Open
**Discovered:** 2026-09-18 during dashboard-live-test project build
**Severity:** High (blocks arc creation for all characters except the first)
**Branch:** sqlite-migration

## Problem

`story_create` tool returns `{"success": true, "message": "Created arc: ..."}` but the arc entity does NOT persist in the project's `.story/story.db`. The tool reports success while the DB write silently fails.

## Reproduction

1. Create a project with characters, acts, sequences, scenes
2. Create an arc for a character via `story_create` (e.g., `test-hero-1`) — **succeeds**, arc persists ✓
3. Create a second arc for the same or different character (e.g., `administrator-1`) — **tool returns success**, but DB shows 0 new arc entities and 0 new arc_beat relations

## Verified State

**DB path:** `/media/theww/AI/TWW/hermes-story-architect/projects/dashboard-live-test/.story/story.db`

After 6 arc creation calls (3 for test-hero, 3 for administrator, 3 for outsider — all returned success):
- `SELECT COUNT(*) FROM entities WHERE type='arc' AND is_deleted=0` → **3** (only the first 3 test-hero arcs)
- `SELECT COUNT(*) FROM relations WHERE kind='arc_beat'` → **3** (only test-hero's beats)
- The administrator and outsider arcs are completely absent

## What Works

- Direct Python call to `handler(args)` from `tools/story_create.py` — **works correctly**, arc persists
- `test_core.py::TestNoteCreation` — **11/11 pass** (entity creation verified via DB queries in test harness)
- Arc creation for the FIRST character (test-hero) — **works**

## What Fails

- Arc creation for SUBSEQUENT characters (administrator, outsider) — **silently fails**
- The tool returns success but no data lands in the DB
- No error is raised; the handler's `except` block may be swallowing the real error

## Suspected Root Causes

1. **Transaction nesting:** `get_db` was changed to autocommit mode (`isolation_level=None`), but the handler's `except` block still calls `ROLLBACK` — in autocommit mode this is a no-op, but if the INSERT itself fails silently (e.g., due to a constraint violation that's being caught), the error is swallowed and the handler returns success anyway.

2. **Stale data cleanup interaction:** The handler has accumulated multiple patches for clearing stale sections/relations from soft-deleted entities. The arc-specific cleanup (`DELETE FROM relations WHERE from_id=? AND kind='arc_beat'`) was removed, but other cleanup logic may be interfering.

3. **Hermes tool execution context:** The handler works when called directly in Python but fails when called through the Hermes tool layer. This suggests the issue may be in how Hermes passes arguments, handles the connection, or manages transactions around tool execution.

4. **The `except Exception as e` block at line 207-209** catches all exceptions, calls `ROLLBACK` (which may fail silently in autocommit mode), and returns `{"error": str(e)}` — but the tool may be interpreting this as success if the error message doesn't match expected patterns.

## Related Files

- `tools/story_create.py` — entity creation handler (accumulated patches)
- `core/entity.py` — `columns_for_insert`, `relations_for_insert`
- `core/db.py` — `get_db` (autocommit mode), `create_schema`, `has_schema`
- `tasks/task_17/soft-delete-recreate-issue.md` — related soft-delete issue (deferred)

## Action Items

1. Read `tools/story_create.py` handler in full and trace the exact flow for arc creation
2. Check if the `except` block is swallowing the real error
3. Verify whether the Hermes tool layer is passing arguments correctly
4. Add a test that creates arcs for MULTIPLE characters and verifies all persist
5. Consider removing the accumulated patches and rebuilding the handler from a known-good state
