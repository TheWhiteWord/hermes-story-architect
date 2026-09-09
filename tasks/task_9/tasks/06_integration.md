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

## Data Flow

The parser produces rich output. `index.py` is a **minimal consumer** — it only extracts what it needs:

| Parser output | Consumed by index.py? |
|---------------|----------------------|
| `scene["heading"]` | ✅ Yes |
| `scene["characters"]` | ✅ Yes (matched to slugs) |
| `scene["id"]` | ✅ Yes |
| `scene["content"]` | ❌ No (not needed for index) |
| `scene["content_html"]` | ❌ No |
| `scene["number"]` | ❌ No |
| Duration data | ❌ No |
| Dual dialogue | ❌ No |
| Parentheticals | ❌ No |
| Transitions | ❌ No |
| Notes | ❌ No |

**This is expected.** The index is a summary graph, not a full document store. The rich content is available via `extract_scenes()` for other consumers (dashboard, editor) to use. The integration test verifies the pipeline works, not that every data point is consumed.

## Location Matching

`match_location()` exists in `screenplay.py` and is tested in `test_core.py`, but `index.py` doesn't call it. The location field is always empty.

**This is a gap.** The integration task should wire up location matching:

```python
# In index.py, after character matching:
slug = match_location(scene["location"], index["locations"])
if slug:
    scene["location"] = slug
```

This ensures the index properly connects scenes to locations, not just characters.

---

## Final Report

**Status: COMPLETE — Gate GREEN**

### Gate Result
```
python -m pytest tests/test_fountain_lexer.py::TestIndexIntegration tests/test_core.py -v
============================== 20 passed in 0.06s ==============================
```

Full suite: **97/97 passed**.

### Changes Made

The gate already passed at task start — the integration between lexer, `screenplay.py`, and `index.py` was functional. The task noted one gap: `match_location()` was imported but never called, leaving `scene["location"]` always empty.

**`core/screenplay.py`** — `extract_scenes()` now populates `scene["location"]` by calling `extract_location()` on the scene heading:
```python
'location': extract_location(token.get('text') or '') or '',
```

**`core/index.py`** — wired up `match_location()` to match the extracted location string to a location slug (same pattern as character matching):
```python
loc_slug = match_location(scene.get("location", ""), index["locations"]) if scene.get("location") else ""
```

### What Was Skipped

- No new tests added — existing tests cover the integration path.
- No new abstractions — reused existing `match_location()` and `extract_location()`.
- No changes to `test_core.py` — it already passes with the new lexer.
