# Task 9.1: Tokenize — Full Parser

> Port `parse()` state machine to produce token list matching Better Fountain.

---

## What to Implement

1. **`parse(text)`** — full parser with state machine
2. **`tokenize(text)`** — wrapper returning `parse(text)['tokens']`

## State Machine

States: `normal`, `dialogue`, `dual_dialogue`, `title_page`, `ignore`

### Normal State Classification Order
1. Empty line → `separator` (or skip if merging)
2. Title page (if not started and matches `title_page` regex)
3. Line break (exactly 2 spaces) → skip
4. Scene heading → `scene_heading`
5. Action with `!` prefix → `action` (forced)
6. Centered (`> text <`) → `centered`
7. Transition → `transition`
8. Synopsis (`= text`) → `synopsis`
9. Section (`# text`) → `section`
10. Page break (`===`) → `page_break`
11. Character (all-caps + next line not empty) → `character`, state → `dialogue`
12. Fallback → `action`

### Dialogue State
1. Parenthetical (`(text)`) → `parenthetical`
2. Everything else → `dialogue`

## Critical: Boneyard State Caching

```python
# CORRECT (JS)
if nested_comments > 0 and state != 'ignore':
    cache_state_for_comment = state  # SAVE
    state = 'ignore'
elif state == 'ignore' and nested_comments == 0:
    state = cache_state_for_comment  # RESTORE (not always 'normal')
```

## Critical: Dual Dialogue Lookback

When `^` found on character cue:
1. Walk backward through `result['tokens']`
2. Mark all `dialogue`/`character`/`parenthetical` tokens as `dual: "left"`
3. Convert `dialogue_begin` → `dual_dialogue_begin`
4. Remove trailing `dialogue_end`
5. Set `dual_right = True`

## Gate

```bash
python -m pytest tests/test_fountain_lexer.py::TestTokenization -v
```

All tests must pass.

## Expected Output Reference

`tests/fixtures/save-the-children/expected_output.json` — the `tokens` array is ground truth.

## Notes

- Track `current_depth` for section nesting
- Track `scene_number` (auto-increment, override with `#number#`)
- Track `previous_character` for dialogue tokens
- Track `last_character_index` for dual dialogue lookback
- Track `title_page_started` and `last_title_page_token`
- Track `ignored_last_token` and `last_was_separator`
- Scene heading: strip leading `.`, extract scene number suffix
- Section: set `level` = number of `#`
- Synopsis: attach to nearest section/scene (via `latestSectionOrScene`)
- Title page: use `titlePageDisplay` for positioning

---

## Final Report

### Gate Result
```
python -m pytest tests/test_fountain_lexer.py::TestTokenization -v
============================== 12 passed in 0.05s ==============================
```

### What was done

Rewrote `parse()` in `core/fountain_lexer.py` as a faithful Better Fountain port. The function had the state machine skeleton but was missing the key data-producing logic.

**Root-cause fixes (5):**

1. **Title page tokens not stored** — Added `TITLE_PAGE_DISPLAY` positioning table (from BF `titlePageDisplay`). Title page tokens now get `index` set and are pushed to `result['title_page'][position]` (cc, bl, br, etc.) instead of being silently dropped after type assignment.

2. **Structure tree never built** — Added `latestSectionOrScene()`, `latest_section()`, and full `StructToken`-style tree construction. Sections nest inside sections, scenes nest inside the correct section. Synopses attach to nearest section/scene via `latestSectionOrScene(current_depth + 1, ...)`.

3. **Notes never extracted** — Added `process_inline_note()` (from BF line 229). `[[notes]]` are now extracted from action/dialogue text and attached to the nearest section/scene's `notes` array. Irrelevant note text length is subtracted from duration calculations.

4. **Boneyard state caching broken** — Fixed: `cache_state_for_comment` now saves the previous state *before* entering `ignore`, and restores it on exit. Previously it always restored to `'normal'`, breaking state if boneyard appeared inside dialogue.

5. **Dual dialogue lookback missing** — When `^` is found on a character cue, code now walks backward through `result['tokens']`, marks prior `dialogue`/`character`/`parenthetical` tokens as `dual: "left"`, converts `dialogue_begin` → `dual_dialogue_begin`, and removes trailing `dialogue_end`.

**Supporting additions:**
- `process_action_block()` / `process_dialogue_block()` — duration calculation + note stripping
- `calculate_dialogue_duration()` — BF's `(len/3)*0.1945548 + punctuation` formula
- `slugify()` — for location slug keys
- `update_previous_scene_length()` — per-scene action/dialogue duration tracking
- `take_count` — `takeNumber` assignment on character cues
- `cfg` parameter with sensible defaults (print_notes, use_dual_dialogue, etc.)

### Files modified
- `core/fountain_lexer.py` — `TITLE_PAGE_DISPLAY` table + full `parse()` rewrite

### Out of scope (pre-existing failures, later tasks)
- `TestHtmlRendering` (5 tests) — `tokens_to_html()` not yet ported
- `TestSceneExtraction::test_scene_characters` — `extract_scenes()` integration
- `TestCharacterExtension::test_with_caret` — `trim_character_extension()` regex
