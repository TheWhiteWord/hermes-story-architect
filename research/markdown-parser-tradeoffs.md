# Markdown Parser Tradeoffs

> Comparing regex section extraction vs marktripy AST-based editing.

---

## The Options

### Option A: Regex Section Parser

```python
import re

SECTION_RE = re.compile(r'^(##\s+.+)$', flags=re.MULTILINE)

def load_section(body: str, section: str) -> str:
    parts = SECTION_RE.split(body)
    for i in range(1, len(parts), 2):
        heading = parts[i].strip().lstrip('#').strip()
        body_text = parts[i + 1].strip() if i + 1 < len(parts) else ""
        if heading.lower() == section.lower():
            return f"## {heading}\n{body_text}"
    return ""
```

**Pros:**
- Zero dependencies
- Simple, predictable, easy to debug
- Works perfectly for our structured notes (clear `##` headings, no nesting edge cases)
- Fast enough for our scale

**Cons:**
- Fragile against edge cases (headings inside code blocks, nested lists, etc.)
- No round-trip guarantee — if we modify a section, we do string replacement
- Would need to be extended for more complex manipulation

---

### Option B: marktripy (AST-based)

**Source**: https://github.com/twardoch/marktripy (MIT, v1.0.3)

Built on `markdown-it-py` and `mistletoe`. Provides unified AST with:
- `parse_markdown(text)` → AST
- `render_markdown(ast)` → Markdown
- `ast.walk()` traversal
- Node types: `heading`, `paragraph`, `list`, `code_block`, etc.
- Clean node structure: `type`, `children`, `attrs`, `content`, `meta`

**Pros:**
- Robust against all Markdown edge cases
- Round-trip: parse → modify → render without losing formatting
- Built on well-maintained libraries (`markdown-it-py`)
- Clean API for heading manipulation (`node.type == "heading"`, `node.level`)
- Future-proof for more sophisticated manipulation

**Cons:**
- Newer library, less battle-tested
- Adds a dependency (and its transitive deps: markdown-it-py, mistletoe)
- Round-trip may reformat our content (could be good or bad)
- Overkill for simple section extraction
- Performance: slightly slower than regex (but negligible for our scale)

**marktripy's own backstory** (from PyPI docs) discusses the Python Markdown ecosystem:
- `markdown`: Original, extensible, complex API
- `markdown2`: Faster, less extensible
- `mistune`: Fast, supports AST, limited round-trip
- `marko`: Good AST, newer, less ecosystem
- `markdown-it-py`: Best plugin system (used by marktripy as one backend)
- No single library perfectly addressed: clean AST manipulation + round-trip + extensibility + performance

---

## Recommendation

### Use regex as the default.

**Why:** Our notes are structured and predictable. We control the format. Edge cases (headings in code blocks, nested lists inside sections) won't happen because we enforce the convention. Regex is zero-dependency, simple, and does exactly what we need.

### Keep marktripy as an optional enhancement.

**Why:** If we later need to:
- Modify sections in place and write back cleanly (round-trip)
- Handle more complex Markdown structures
- Add custom syntax extensions

We can add it then. The section parser interface (`load_section()`, `list_sections()`) is abstracted, so we can swap the implementation without changing the rest of the code.

---

## Implementation Strategy

1. **Abstract the parser** behind a simple interface:

```python
class MarkdownParser:
    def list_sections(self, content: str) -> list[str]: ...
    def get_section(self, content: str, section: str) -> str: ...
    def replace_section(self, content: str, section: str, new_body: str) -> str: ...
```

2. **Implement RegexParser** (default): zero dependencies, fast, simple.

3. **Optionally implement MarktripyParser**: same interface, AST-based round-trip.

4. **Make it configurable**: in `config.yaml`, set `parser: regex` or `parser: marktripy`.

This way we start simple and have an escape hatch if we need more power.

---

## Updated Dependency Table

| Library | Purpose | Needed? | Notes |
|---------|---------|---------|-------|
| `screenplay-tools` | Fountain parse + write | **Yes** | Round-trip editing |
| `python-frontmatter` | YAML frontmatter | **Yes** | Load/modify/dump |
| `rapidfuzz` | Fuzzy name matching | **Yes** | Typo tolerance |
| `vis-network` | Graph visualization | **Yes** | Dashboard (JS) |
| `marktripy` | Markdown AST editing | Optional | Round-trip section editing |
| `screenplain` | Fountain export | No | Not needed yet |
| `jouvence` | Fountain parse | No | No writer |
| `mrkdwn_analysis` | Section extraction | No | Regex is sufficient |

### Final requirements.txt

```
rapidfuzz>=3.0
python-frontmatter>=1.0
screenplay-tools>=0.0.10
# marktripy>=1.0.3  # optional, for round-trip editing
```
