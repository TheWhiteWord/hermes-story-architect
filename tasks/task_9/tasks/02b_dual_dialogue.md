# Task 9.2b: Fix Dual Dialogue Alignment

> Fix the dual dialogue state machine so token count/order matches Better Fountain exactly.

---

## Bug

When a dual dialogue block (`CHARACTER ^`) is followed by an empty line, Python pushes a `separator` token that BF doesn't produce. This shifts all subsequent tokens by 1 position, causing cascading mismatches.

**Example:**
```
ELENA
Because the door was always open.

                MIRA ^
        Because the door was always open.
```

The empty line between ELENA's dialogue and MIRA's dual dialogue cue produces a `separator` in Python but not in BF.

---

## What to Fix

In `core/fountain_lexer.py`, `parse()` function, empty line handling:

**Current (buggy):**
```python
if text.strip() == '' and text != '  ':
    # ... close dialogue ...
    thistoken['type'] = 'separator'
    last_was_separator = True
    push_token(thistoken)
    continue
```

**Fix:** When in `dual_dialogue` state, don't push a separator for the empty line between the two speakers. The empty line is part of the dual dialogue block, not a structural separator.

---

## Gate

```bash
python -c "
import json
from core.fountain_lexer import parse

data = json.load(open('tests/fixtures/save-the-children/expected_output.json'))
text = open('tests/fixtures/save-the-children/screenplay.fountain').read()
result = parse(text)

# Token count must match
assert len(result['tokens']) == len(data['tokens']), \
    f'Token count mismatch: {len(result[\"tokens\"])} != {len(data[\"tokens\"])}'

# Token types must match in order
for i, (actual, expected) in enumerate(zip(result['tokens'], data['tokens'])):
    assert actual['type'] == expected['type'], \
        f'Token {i} type mismatch: {actual[\"type\"]} != {expected[\"type\"]}'

print('PASS: Token count and order match BF exactly')
"
```

---

## Notes

- Only fix the dual dialogue alignment. Don't refactor other parts of the parser.
- The fix is a small conditional in the empty line handler — check `state == 'dual_dialogue'` and skip the separator push.
- After the fix, re-run the gate for Task 9.2 (Tokenize) to verify no regressions.

---

## Final Report

**Status:** GREEN — gate passes, no regressions.

**Root cause:** The task description's diagnosis was wrong. The bug was NOT in the empty-line handler pushing a spurious separator. The actual bug was in the dual dialogue lookback loop: BF uses `splice(temp_index)` which removes ALL tokens from that index onward (including the separator pushed for the empty line between speakers), but Python used `pop(temp_index)` which only removes one token.

**Fix:** Changed `result['tokens'].pop(temp_index)` → `result['tokens'] = result['tokens'][:temp_index]` in the dual dialogue lookback loop (line ~537).

**Verification:**
- Gate: PASS (151 tokens = 151 tokens, types match in order)
- Regression: 59/59 tests pass (TestRegexPatterns, TestTokenClassification, TestTokenization, TestLocationParsing, TestDuration)
