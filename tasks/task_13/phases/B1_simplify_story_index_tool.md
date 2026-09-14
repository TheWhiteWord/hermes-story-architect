# B1 — Simplify `story_index.py` Tool

**Goal:** Remove structure index generation/writing from the `story_index` tool. Returns only the unified index.

## Why

After Phase A, there's no structure index to generate or write. The tool currently calls functions that no longer exist.

## Current State

`tools/story_index.py`:
- Line 4: imports `generate_structure_index, write_structure_index`
- Lines 55-58: generates + writes structure index
- Line 61: pops `_full_scenes`
- Line 72: includes `structure_index` in response

## Changes

1. **`tools/story_index.py`**:
   - Remove `generate_structure_index, write_structure_index` from import (line 4)
   - Remove lines 55-58 (structure index generation/writing)
   - Remove line 61 (`index.pop("_full_scenes", None)`)
   - Remove `"structure_index": structure_index` from response dict (line 72)
   - Update import to only `generate_index, write_index`

## Verification Checklist

- [x] `story_index` tool returns successfully
- [x] Response contains `index` key with full data (navigation + dramatic)
- [x] Response does NOT contain `structure_index` key
- [x] No `structure-index.yaml` file is written to disk
- [x] `generate_structure_index` not imported in `tools/story_index.py`

## Notes

- Depends on Phase A completion
- This is a consumer of the core generator — verifies the tool layer works with unified index

## Completion

Removed `generate_structure_index`/`write_structure_index` imports, structure index generation/writing block, `_full_scenes` pop, and `structure_index` from response dict. Tool now generates and writes only the unified index.
