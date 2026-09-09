# Task 9.3: HTML Generation

> Port `tokens_to_html()` to convert tokens to formatted HTML.

---

## What to Implement

1. **`tokens_to_html(tokens)`** — convert token list to HTML string
2. **`fountain_to_html(text)`** — convenience wrapper (parse + tokens_to_html)

## Token-to-HTML Mapping (from JS)

| Token | HTML Wrapper | CSS Class |
|-------|--------------|-----------|
| `scene_heading` | `<h3>` | `haseditorline` + `data-scenenumber` + `data-position` |
| `transition` | `<h2>` | `haseditorline` |
| `dual_dialogue_begin` | `<div>` | `dual-dialogue` |
| `dialogue_begin` | `<div>` | `dialogue` (+ `left`/`right` if dual) |
| `character` | `<h4>` | `haseditorline` |
| `parenthetical` | `<p>` | `haseditorline parenthetical` |
| `dialogue` | `<p>` | `haseditorline` |
| `dialogue_end` | `</div>` | (closes dialogue div) |
| `dual_dialogue_end` | `</div></div>` | (closes both) |
| `section` | `<p>` | `haseditorline section` + `data-position` + `data-depth` |
| `synopsis` | `<p>` | `haseditorline synopsis` |
| `lyric` | `<p>` | `haseditorline lyric` |
| `note` | `<p>` | `haseditorline note` |
| `boneyard_begin` | `<!-- ` | (HTML comment start) |
| `boneyard_end` | ` -->` | (HTML comment end) |
| `page_break` | `<hr />` | (horizontal rule) |
| `action` | `<span>` | `haseditorline` (first in block gets `<p>` wrapper) |
| `centered` | `<span>` | `haseditorline centered` |

## Action Block Wrapping

- First action token in a block: `<p><span class="haseditorline">text</span>`
- Subsequent action tokens: `<span class="haseditorline">text</span>`
- Centered tokens within action: no extra `<p>` needed
- Separator after action: closes `</p>` if next token is not action/separator/centered

## Gate

```bash
python -m pytest tests/test_fountain_lexer.py::TestHtmlRendering -v
```

All tests must pass.

## Notes

- The test checks for `fountain-scene_heading`, `fountain-character`, `fountain-dialogue`, `fountain-action` in output
- These are CSS class prefixes, not the same as BF's `haseditorline` — check what the test actually expects
- The test uses single-token lists, so action block wrapping may not be fully tested
