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
python -m pytest tests/test_fountain_lexer.py -k "duration" -v
```

Or compare against `expected_output.json` — `token['time']` values should match.

## Notes

- Duration is set on `dialogue` and `action` tokens
- Inline notes `[[ ]]` reduce effective text length for duration
- Track `result['lengthAction']` and `result['lengthDialogue']` totals
- Track `lengthActionSoFar` / `lengthDialogueSoFar` for per-scene duration
