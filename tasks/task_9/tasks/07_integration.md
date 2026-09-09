# Task 9.5: Integration

> Verify the new lexer feeds correctly into `index.py` and `screenplay.py`.

---

## What to Verify

1. **`test_core.py::TestIndexGeneration`** — index generation works with new lexer
2. **`test_fountain_lexer.py::TestIndexIntegration`** — minimal project test

## Gate

```bash
python -m pytest tests/test_fountain_lexer.py::TestIndexIntegration tests/test_core.py -v
```

All tests must pass.

## What This Catches

- Lexer output format matches what `screenplay.py` expects
- `extract_scenes()` returns data that `index.py` can consume
- Character matching works end-to-end
- Scene counts are correct

## Notes

- `test_core.py` already passes with the old `screenplay.py` — this verifies the new lexer doesn't break it
- If `test_core.py` fails, the issue is likely in `screenplay.py` not adapting to lexer output format
- The minimal project in `TestIndexIntegration` creates a project from scratch — verifies the full pipeline
