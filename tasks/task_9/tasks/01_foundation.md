# Task 9.0: Foundation — Regex, Classify, Location

> Foundational pieces needed by all later tasks.

---

## What to Implement

1. **Module-level regex aliases** — expose `CHARACTER_RE`, `SCENE_HEADING_RE`, `TRANSITION_RE`, `SECTION_RE`, `SYNOPSIS_RE`, `PARENTHETICAL_RE`, `CENTERED_RE`, `PAGE_BREAK_RE`, `LYRIC_RE`, `NOTE_INLINE_RE`, `BONEYARD_START_RE`, `BONEYARD_END_RE`
2. **`classify_line(line, prev_type=None)`** — classify a single line without full state machine
3. **`parse_location(heading)`** — parse scene heading string into location info
4. **Fix `parse_location_information()`** — correct the regex bug (name/time_of_day swapped)

## Gate

```bash
python -m pytest tests/test_fountain_lexer.py::TestRegexPatterns tests/test_fountain_lexer.py::TestTokenClassification tests/test_fountain_lexer.py::TestLocationParsing -v
```

All tests in those three classes must pass.

## Bug to Fix

Current `parse_location_information` has swapped name/time_of_day:
```python
# WRONG (current)
'name': split.group(1).strip() if split else location_text.strip(),
'time_of_day': split.group(1).strip() if split else '',

# CORRECT (JS) — regex should be /(.*)[-–—−](.*)/
'name': split.group(1).strip(),      # BEFORE dash
'time_of_day': split.group(2).strip(),  # AFTER dash
```

## Notes

- Regex patterns are already in `REGEX` dict — just need module-level aliases
- `classify_line` is a simplified single-line classifier (no state machine needed)
- `parse_location` returns `None` if input doesn't match scene heading regex
- `parse_location` returns dict with: `name`, `interior`, `exterior`, `time_of_day`

---

## Final Brief

**Status:** GREEN — 43/43 tests passing.

**Changes to `core/fountain_lexer.py`:**

1. **Module-level regex aliases** — Added 12 aliases (`CHARACTER_RE`, `SCENE_HEADING_RE`, `TRANSITION_RE`, `SECTION_RE`, `SYNOPSIS_RE`, `PARENTHETICAL_RE`, `CENTERED_RE`, `PAGE_BREAK_RE`, `LYRIC_RE`, `NOTE_INLINE_RE`, `BONEYARD_START_RE`, `BONEYARD_END_RE`) pointing to `REGEX` dict entries (or fresh patterns for boneyard).

2. **Fixed `parse_location_information()`** — Regex changed from `[-–—−](.*)` to `(.*)[-–—−](.*)`. Now `name` = group(1) (before dash), `time_of_day` = group(2) (after dash). Previously both used group(1).

3. **Fixed `scene_heading` regex** — Reordered alternation so `int/ext` and `int/e` match before `int`. Without this, `INT./EXT. CAR - NIGHT` matched `int` first, leaving `/EXT. CAR - NIGHT` as the location text.

4. **Fixed `note_inline` regex** — `\[{2}` quantifier syntax doesn't work in the `regex` module. Changed to literal `\[\[` (and `\]\]` → `\]\]`).

5. **Added `classify_line(line, prev_type=None)`** — Single-line classifier. Checks regexes in priority order (separator → scene_heading → transition → section → synopsis → centered → page_break → lyric → character → dialogue/parenthetical if prev was character → action fallback).

6. **Added `parse_location(heading)`** — Returns `None` if input doesn't match `SCENE_HEADING_RE`, otherwise delegates to `parse_location_information()`.

7. **Added `tokenize(script)`** — Wrapper returning `parse(script)['tokens']`.

8. **Added `extract_scene_content(fountain, scene_index)`** — Extracts raw text between scene heading and next heading/end.

9. **Added `fountain_to_html(fountain)`** — Convenience: tokenize then tokens_to_html.

**Skipped:** Nothing — all required functions implemented.
