# B2 — Replace `story_load.py` `structure_only` with Projection

**Goal:** Remove `structure_only` parameter. Return full index by default — the LLM gets what it needs, caller decides what to project.

## Why

With unified index, there's no separate structure file to load. The `structure_only` param existed only to select between two files. Now there's one file. Filter at the consumer, not at the source.

## Current State

`tools/story_load.py`:
- Lines 15-18: `structure_only` schema param
- Lines 39-40: lazy mode comment
- Lines 41-50: `structure_only` branch reads `structure-index.yaml` separately

## Changes

1. **`tools/story_load.py`**:
   - Remove `structure_only` from `SCHEMA["properties"]`
   - Remove lines 41-50 (the entire `if args.get("structure_only", False):` branch)
   - Update the comment on line 39-40 (remove "lazy mode" reference)
   - The default path now reads `index.yaml` and returns the full unified index
   - No need for projection logic — the full index IS the response

2. **Verify** no other tool or skill calls `story_load` with `structure_only: true`.

## Verification Checklist

- [x] `story_load` with just `project` returns full index (navigation + dramatic metadata)
- [x] `story_load` no longer accepts `structure_only` parameter (schema updated)
- [x] Response contains `index`, `project`, `memory` keys
- [x] No code reads `structure-index.yaml` in `story_load.py`

## Notes

- Depends on Phase A
- The "lazy loading" concept (returning structure separately) is dead — one call gets everything
- Skills reference `structure_only` — will be updated in Phase E

## Completion

Removed `structure_only` param from SCHEMA, removed the lazy-mode branch that read `structure-index.yaml`, removed stale "lazy mode" comment. Tool now loads the unified index and returns the full data.
