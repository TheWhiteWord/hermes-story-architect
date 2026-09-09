# Task 9.4: Scene Extraction

> Port `extract_scenes()` to produce scene data matching Better Fountain output.

---

## What to Implement

1. **`extract_scenes(screenplay_content)`** — extract scenes from Fountain content
2. **`extract_scene_content(fountain, scene_index)`** — extract full text for a scene by index

## Output Format

```python
{
    "id": 1,                          # Scene number (1-based)
    "heading": "INT. ROOM - DAY",     # Raw heading text
    "number": "1",                    # Scene number (string)
    "characters": ["KAEL", "MIRA"],   # Raw character text (extensions preserved)
    "content": "...",                 # Raw fountain text (ALL tokens)
}
```

## Gate

```bash
python -m pytest tests/test_fountain_lexer.py::TestSceneExtraction -v
```

All tests must pass.

## Notes

- `extract_scenes` uses `parse()` internally
- `content` includes ALL token types: action, character, dialogue, parenthetical, transition, centered, note, page_break
- `characters` are raw character text from `character` tokens (extensions like `(V.O.)` are preserved)
- Dual dialogue: `^` is stripped from character text, `dual_dialogue_begin` token marks the block
- `extract_scene_content` returns the full raw text for a specific scene (heading + all tokens until next heading)
- Scene 6 (OPENING TITLES) includes centered text `THE END` and page break
- Scene 7 includes dual dialogue (`MIRA ^`)
- All 9 scenes are tested — ensure your implementation handles all content types

---

## Final Report

### Status: ✅ COMPLETED

### Changes Made

**File:** `core/fountain_lexer.py`

**Fix:** `extract_scene_content()` — replaced `float('inf')` with `len(lines)` as the end slice index for the last scene. `float('inf')` is not a valid Python slice index and raised `TypeError` when accessing scene 8 (the final scene).

```python
# Before
end_line = scenes[scene_index + 1]['line'] if scene_index + 1 < len(scenes) else float('inf')

# After
end_line = scenes[scene_index + 1]['line'] if scene_index + 1 < len(scenes) else len(lines)
```

### Test Results

| Test | Result |
|------|--------|
| `TestSceneExtraction` (4 tests) | ✅ 4/4 passed |
| `test_fountain_lexer.py` (78 tests) | ✅ 78/78 passed |
| `test_core.py` (19 tests) | ✅ 19/19 passed |

### Notes

- `extract_scenes()` in `core/screenplay.py` already worked correctly — no changes needed.
- The bug only manifested on the last scene (index 8) because `float('inf')` was only used as the fallback when `scene_index + 1 >= len(scenes)`.
- All 9 scenes verified: headings, characters, dual dialogue, transitions, centered text, page break, and inline notes all handled correctly.
