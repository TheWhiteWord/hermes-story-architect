# Deep Research: Dependency Libraries

> Verified APIs, constraints, and integration notes for each dependency.

---

## 1. screenplay-tools (Fountain parsing)

**Source**: https://github.com/wildwinter/screenplay-tools (MIT, v0.0.10, 22 stars, 142 commits)

### Python API (verified from docs + source)

```python
from screenplay_tools.fountain.parser import Parser
from screenplay_tools.fountain.writer import Writer
from screenplay_tools.fountain.callbackparser import CallbackParser
from screenplay_tools.fountain.formatHelper import FormatHelper

# Parse a Fountain file
parser = Parser()
parser.addText(open("screenplay.md").read())
script = parser.script  # Script object

# Access elements
for element in script.elements:
    print(element.type)   # HEADING, ACTION, CHARACTER, DIALOGUE, etc.
    print(element.text)   # The text content
    # For CHARACTER elements: element.name, element.extension (e.g., "O.S.")
    # For HEADING elements: element.sceneNumber

# Write back to Fountain
writer = Writer()
fountain_text = writer.write(script)

# Callback parser (groups dialogue with characters)
class MyCallback(CallbackParser):
    def onSceneHeading(self, text, sceneNumber=None):
        print(f"Scene: {text}")
    def onDialogue(self, character, parenthetical, line, extension=None):
        print(f"{character}: {line}")

cb = MyCallback()
cb.addText(fountain_text)
```

### What this means for us

- **Read**: Parse screenplay.md → extract scenes, characters per scene, dialogue
- **Write**: Insert new scene → modify script.elements → writer.write() → back to Fountain
- **Scene targeting**: Iterate elements, find HEADINGs, slice by scene
- **Round-trip**: Writer preserves formatting, scene numbers, boneyard

### Constraints

- Writer outputs standard Fountain — indentation may differ from input
- Scene numbers (`#1a#`) are preserved
- Boneyard (comments `/* ... */`) and notes (`[[ ... ]]`) are supported

### Integration plan

```python
def get_scene_elements(script, scene_id):
    """Extract elements for a single scene from a parsed script."""
    elements = []
    in_target = False
    for el in script.elements:
        if el.type == "HEADING":
            if in_target:
                break
            # Match by scene number or heading text
            if matches_scene(el, scene_id):
                in_target = True
        if in_target:
            elements.append(el)
    return elements

def insert_scene(script, new_fountain_text, position="end"):
    """Insert a new scene into the script."""
    new_parser = Parser()
    new_parser.addText(new_fountain_text)
    new_elements = new_parser.script.elements
    
    if position == "end":
        script.elements.extend(new_elements)
    else:
        # Insert at specific index
        script.elements[position:position] = new_elements
    
    return script
```

---

## 2. python-frontmatter (YAML frontmatter)

**Source**: https://python-frontmatter.readthedocs.io (MIT, v1.3.0, 423 stars)

### Python API (verified from docs)

```python
import frontmatter

# Load a note
post = frontmatter.load("characters/mara.md")

# Access metadata
print(post['name'])       # "Mara Chen"
print(post['story_role']) # "Protagonist"
print(post.get('age', 0)) # 34

# Access content (body)
print(post.content)       # The markdown body (without frontmatter)

# Modify metadata
post['age'] = 35
post['new_field'] = 'value'

# Serialize back
output = frontmatter.dumps(post)
# Returns: ---\nname: Mara Chen\nage: 35\n---\n\n## Personality\n...

# Write back to file
with open("characters/mara.md", "w") as f:
    frontmatter.dump(post, f)
```

### What this means for us

- **Read**: Load character note → extract frontmatter (for index) + content (for retrieval)
- **Update**: Modify frontmatter (e.g., add relationship) → dump back
- **Round-trips cleanly**: Preserves body content exactly, reformats frontmatter

### Constraints

- `dumps()` reformats YAML (key order may change)
- Content is everything after `---` (including `##` headmatter)
- Supports YAML, JSON, TOML handlers (we use YAML)
- No built-in section extraction — we need our own regex parser for that

### Integration plan

```python
import frontmatter
import re

def load_character_frontmatter(path):
    """Load frontmatter for index generation."""
    post = frontmatter.load(path)
    return {
        'name': post.get('name', ''),
        'story_role': post.get('story_role', ''),
        'one_sentence': post.get('one_sentence', ''),
        'scenes': post.get('scenes', []),
        'relationships': post.get('relationships', []),
        'goals': post.get('goals', {}),
        'knowledge': post.get('knowledge', []),
        'sections': post.get('sections', []),
    }

def load_character_body(path, section=None):
    """Load body, optionally extracting a single section."""
    post = frontmatter.load(path)
    if section is None:
        return post.content
    return extract_section(post.content, section)

def update_frontmatter(path, key, value):
    """Update a single frontmatter field."""
    post = frontmatter.load(path)
    post[key] = value
    with open(path, "w") as f:
        frontmatter.dump(post, f)
```

---

## 3. Regex Section Parser (built-in, no dependency)

Since `python-frontmatter` returns the body as a string, we extract `##` sections with regex:

```python
import re
from pathlib import Path

SECTION_RE = re.compile(r'^(##\s+.+)$', flags=re.MULTILINE)

def load_section(note_path: str, section: str) -> str:
    """Load a single ## section from a markdown note body."""
    # Read full note, split frontmatter
    content = Path(note_path).read_text()
    # Remove frontmatter (between --- markers)
    if content.startswith('---'):
        _, _, body = content.split('---', 2)
    else:
        body = content
    
    # Split on ## headings
    parts = SECTION_RE.split(body)
    # parts[0] = preamble (before first ##)
    # parts[1], parts[3], ... = headings
    # parts[2], parts[4], ... = content after headings
    
    for i in range(1, len(parts), 2):
        heading = parts[i].strip().lstrip('#').strip()
        body_text = parts[i + 1].strip() if i + 1 < len(parts) else ""
        if heading.lower() == section.lower():
            return f"## {heading}\n{body_text}"
    return ""

def list_sections(note_path: str) -> list[str]:
    """List all ## section headings in a note."""
    content = Path(note_path).read_text()
    if content.startswith('---'):
        _, _, body = content.split('---', 2)
    else:
        body = content
    return SECTION_RE.findall(body)
```

### Why not mrkdwn_analysis?

`mrkdwn_analysis` (PyPI: `markdown-analysis`) provides:
- Header detection (ATX + Setext)
- Section identification
- Paragraph extraction
- Link/image/table extraction

But for our use case, we only need section extraction — a 10-line regex parser is sufficient. Adding a dependency for this is overkill.

### Why not marktripy?

`marktripy` returned zero search results. It may be very new, obscure, or not exist. Even if it does, regex section extraction is simpler and has zero dependencies.

**Decision**: Use regex section parser. No external dependency needed for Markdown section extraction.

---

## 4. Obsidian StoryLine Plugin (Reference)

**Source**: https://github.com/PixeroJan/obsidian-storyline (TypeScript, Obsidian API)

### What it does

- Scene boards (index cards)
- Character management (with frontmatter)
- Location management
- Plot grids
- Timeline with chronological + narrative order
- Word count tracking

### What we can learn

1. **Character view**: Modal/panel showing all character notes with frontmatter fields
2. **Scene list**: Flat list of scenes with metadata (location, characters, word count)
3. **Timeline**: Drag-and-drop chronological ordering
4. **Plot visualization**: Color-coded plot threads across scenes

### What we cannot use

- Obsidian Plugin API (we're Hermes preview pane, not Obsidian)
- TypeScript (we're Python + HTML/JS)

### Integration plan for Stage 4

Review StoryLine's UI patterns:
- How it renders character cards
- How it handles scene navigation
- How it visualizes plot threads

---

## 5. Jouvence (Fountain alternative)

**Source**: https://github.com/ludovicchabant/Jouvence (MIT, Python)

### API

```python
from jouvance.parser import FountainParser
from jouvance.html import HtmlDocumentRenderer

parser = FountainParser()
document = parser.parse(path_to_file)
renderer = HtmlDocumentRenderer()
renderer.render_doc(document, output_file)
```

### Why not use it

- Renders to HTML/terminal, but **not** back to Fountain
- No writer — we can't round-trip
- `screenplay-tools` has both Parser AND Writer — better for editing

**Decision**: Use `screenplay-tools` for Fountain parsing/writing. Jouvence is not needed.

---

## 6. vis-network (Dashboard visualization)

**Source**: https://unpkg.com/vis-network (MIT/Apache 2.0, v10.1.2)

### Offline usage

```html
<!-- Load from local file (after downloading once) -->
<script src="vis-network.min.js"></script>
<link href="vis-network.min.css" rel="stylesheet">
```

Or via CDN (requires internet on first load, cached after).

### Integration plan

- Single HTML file for the preview pane
- Load from CDN in development
- Download local copy for production (offline support)
- Nodes: characters (colored by role), locations, worlds
- Edges: relationships (labeled with feeling), scene memberships

---

## Revised Dependency Table

| Library | Purpose | License | Needed? | Notes |
|---------|---------|---------|---------|-------|
| `screenplay-tools` | Fountain parse + write | MIT | **Yes** | Round-trip editing |
| `python-frontmatter` | YAML frontmatter | MIT | **Yes** | Load/modify/dump |
| `rapidfuzz` | Fuzzy name matching | MIT | **Yes** | Typo tolerance |
| `vis-network` | Graph visualization | MIT/Apache | **Yes** | Dashboard (JS) |
| `screenplain` | Fountain export | MIT | No | Export only, not needed yet |
| `jouvence` | Fountain parse | MIT | No | No writer, can't round-trip |
| `marktripy` | Markdown AST | — | No | Doesn't exist / obscure |
| `mrkdwn_analysis` | Section extraction | MIT | No | Regex is sufficient |

### Final requirements.txt

```
rapidfuzz>=3.0
python-frontmatter>=1.0
screenplay-tools>=0.0.10
```

vis-network is loaded via CDN/local in the HTML dashboard, not pip.

---

## Answers to Open Questions (from plan)

### Q: Fountain syntax — strict subset or full Fountain?

**Answer**: Full Fountain. `screenplay-tools` handles the full spec. Subsetting would mean fighting the parser.

### Q: Relationships — frontmatter array or separate note?

**Answer**: Frontmatter `relationships:` array. Keeps everything in one place, no separate file to maintain. The array is small (2-5 entries per character) and the body's `## Relationships` section provides the depth.

### Q: Story Memory — auto-generated or manual?

**Answer**: Auto-generated by Hermes after each edit. When Hermes applies an edit (e.g., new scene, character update), it also updates `.story/memory.md` with the relevant continuity findings. The writer can correct it later.

### Q: Edit history — where to store?

**Answer**: `.story/history.md` in the project folder, gitignored. Contains: timestamp, action type, target, summary, before/after excerpts, continuity findings. STARC stores in Qt settings (binary), but we don't have that. A file is portable and inspectable.

### Q: Multi-project — how does Hermes know which is active?

**Answer**: Active project is set in conversation context. "Load project the-water-audit" → Hermes remembers it for the session. Optional: a `.story/active-project` pointer file for persistence across sessions. Priority: conversation context > pointer file > ask user.

### Q: Index staleness — auto-regenerate when?

**Answer**: Auto-regenerate after every edit (the skill does it as part of the apply flow). Also regenerate on project load (to catch manual edits). Manual trigger: "reindex project" command.

### Q: marktripy vs regex for section editing?

**Answer**: Regex. `marktripy` doesn't appear to exist or is very obscure. Our regex parser handles section extraction and insertion cleanly. For round-trip editing (modify a section and write back), we use `python-frontmatter` for frontmatter + string replacement for body sections.
