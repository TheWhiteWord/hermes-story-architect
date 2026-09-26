# story_memory — KEEP AS IS

`tools/story_memory.py` (102 lines) · `core/db.py:103–205` (memory policy) · `core/constants.py` (categories/limits)

## What it does
`add` / `remove` / `replace` one entry in one of four categories of `project.extra.memory`, with validation and char/entry limits.

## Findings

**This is the best tool in the set. Use it as the template for the others.**

1. **Real, actionable errors.** Every failure returns the current entries, the category, the usage figure, and an `action_required` string telling the agent what to do next. Compare `story_search`'s `"Database not found"` — same failure class, opposite quality.
2. **Validation at the boundary.** Non-empty, length-capped, duplicate-checked on add, category-checked, unknown-action-checked. No unvalidated input reaches the DB.
3. **Idempotent add.** Re-adding an existing entry returns success without a write.
4. **Constants live in one place** (`MEMORY_CATEGORIES`, `MEMORY_CHAR_LIMIT`, `MEMORY_ENTRY_LIMIT`) and policy in `core/db.py` (`validate_memory`, `memory_serialized_length`). No magic numbers, no policy duplicated in the tool.
5. **The only tool that consistently uses the compact `kwargs.get("vault_path")` form** in one line instead of a five-line block.
6. **Returns `usage` on every response**, so the agent always knows its budget. Nice.

## Small things (not worth changing)
- `except (KeyError, TypeError, ValueError)` at the end is now largely unreachable given the explicit checks above. Harmless.
- It never calls `story_backup`. For a low-risk append-only store that's fine.

## Recommendation
Use this file as the reference when fixing the others. Specifically, the `_error(...)` helper pattern — *error + current state + what to do* — is the standard the rest of the toolset should meet.
