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
