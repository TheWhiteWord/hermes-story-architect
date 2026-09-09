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
