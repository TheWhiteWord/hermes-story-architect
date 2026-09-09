# Task 9.2: Duration Calculation

> Port `calculateDialogueDuration()` and timing for action/dialogue tokens.

---

## What to Implement

1. **`calculate_dialogue_duration(dialogue)`** — estimate dialogue duration in seconds
2. **`process_dialogue_block(token)`** — set `token['time']` for dialogue
3. **`process_action_block(token)`** — set `token['time']` for action

## Algorithm (from JS)

```python
def calculate_dialogue_duration(dialogue):
    duration = 0
    sanitized = re.sub(r'[^\w]', '', dialogue)
    duration += (len(sanitized) / 3) * 0.1945548
    punctuation = re.findall(r'([.!?:] )|(, )', dialogue)
    if punctuation:
        duration += 0.75 * len([p for p in punctuation if p[0]])  # . ! ? :
        duration += 0.3 * len([p for p in punctuation if p[1]])  # ,
    return duration
```

Action duration: `(text_length - notes_length) / 20`

## Gate

```bash
python -m pytest tests/test_fountain_lexer.py::TestDuration -v
```

Or compare against `expected_output.json` — `token['time']` values should match.

## Notes

- Duration is set on `dialogue` and `action` tokens
- Inline notes `[[ ]]` reduce effective text length for duration
- Track `result['lengthAction']` and `result['lengthDialogue']` totals
- Track `lengthActionSoFar` / `lengthDialogueSoFar` for per-scene duration

---

## Final Report

### Summary
Fixed `calculate_dialogue_duration()` in `core/fountain_lexer.py` to match Better Fountain's JS behavior exactly.

### Root Cause
The original Python port used `re.findall(r'(\.|\?|\!|\:) |(\, )', text)` with capture groups, then tried to classify matches by checking which capture group was non-empty. This is **not** what the JS does.

JS uses `dialogue.match(/(\.|\?|\!|\:) |(\, )/g)` which returns **full match strings** (not capture groups). The JS code then blindly applies:
- `punct[0].length * 0.75` (first match = period)
- `punct[1].length * 0.3` (second match = comma)

### Fix
Changed `re.findall` to use non-capturing groups and match the JS indexing:
```python
punct = re.findall(r'(?:\.|\?|\!|\:) |\, ', text)
if punct:
    duration += 0.75 * len(punct[0])
    if len(punct) > 1:
        duration += 0.3 * len(punct[1])
```

### Verification
- Gate: `python -m pytest tests/test_fountain_lexer.py::TestDuration -v` → **4/4 passed**
- `lengthAction` total: 34.4 (matches BF)
- `lengthDialogue` total: 28.908950399999995 (matches BF)
- All `token['time']` values match `expected_output.json`

### Out of Scope
- Dual dialogue token alignment (separate bug, not duration-related)
- Scene duration tracking (`lengthActionSoFar`/`lengthDialogueSoFar` already exist in the code)
