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
    "characters": ["KAEL", "MIRA"],   # Unique character names (extensions stripped)
    "location": "",                   # Parsed location (from parse_location)
    "content": "...",                 # Raw fountain text (preserves formatting)
    "content_html": "...",            # Tokenized HTML with CSS classes
}
```

## Gate

```bash
python -m pytest tests/test_fountain_lexer.py::TestSceneExtraction -v
```

All tests must pass.

## Notes

- `extract_scenes` uses `parse()` internally
- `content` is the raw text of the scene (heading + all tokens until next heading)
- `content_html` is the HTML rendering of all tokens (via `tokens_to_html`)
- `characters` are extracted from `character` tokens, with extensions stripped
- `extract_scene_content` returns just the text content for a specific scene
