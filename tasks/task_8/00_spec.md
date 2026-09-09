# Task 8: Replace screenplay-tools with Better Fountain Port

> Spec for porting Better Fountain's lexer/parser to Python, removing the `screenplay-tools` dependency.

---

## 1. Token Types (from Better Fountain)

All 14 Fountain conventions + structural tokens:

| Token Type | Fountain Syntax | Regex (from `afterwriting-parser.js`) | Scene Boundary? | Notes |
|------------|----------------|--------------------------------------|-----------------|-------|
| `title_page` | `Title: value` | `^(title\|credit\|author[s]?\|source\|notes\|draft date\|date\|watermark\|contact( info)?\|revision\|copyright\|font\|tl\|tc\|tr\|cc\|br\|bl\|header\|footer)\:.*` | ❌ Metadata | Key-value pairs before first scene heading. Position tracked (cc, bl, br, etc.) |
| `section` | `# Act` / `## Seq` | `^[ \t]*(#+)(?: *)(.*)` | ❌ Metadata | Hierarchical structure. Level = number of `#`. Nested under parent sections |
| `synopsis` | `= summary` | `^[ \t]*(?:\=(?!\=+))(.*)` | ❌ Metadata | Single-line summary, attached to nearest section/scene |
| `scene_heading` | `INT. ROOM - DAY` / `.FORCED` | `^[ \t]*([.](?![.])|(?:[*]{0,3}_?)(?:int\|ext\|est\|int[.]?\/ext\|i[.]?\/e)[. ])(.+?)(#[-.0-9a-z]+#)?$` | ✅ **YES** | Starts new scene. May have scene number suffix `#1#`. Forced headings start with `.` |
| `transition` | `CUT TO:` / `FADE OUT.` | `^[ \t]*((?:FADE (?:TO BLACK\|OUT)\|CUT TO BLACK)\.\|.+ TO\:\|^TO\:)$` | ❌ | Upper-case, ends with `TO:` or `FADE TO BLACK.` etc. |
| `action` | Any paragraph | `^(.+)` (fallback) | ❌ | Default for non-matching lines. Forced action starts with `!` |
| `character` | `KAEL` / `@McCONNOR` | `^[ \t]*(?![#!]|((\[\[))\|(SUPERIMPOSE:))(((?!@)[^\p{Ll}\r\n]*?\p{Lu}[^\p{Ll}\r\n]*?)\|((@)[^\r\n]*?))(\(.*\))?(\s*\^)?$` | ❌ | ALL CAPS (no lowercase). May have `(extension)` and `^` for dual dialogue. `@` prefix forces character names with lowercase |
| `dialogue` | Text after character | `^[ \t]*([*_]+[^\p{Ll}\p{Lo}\p{So}\r\n]*)(\^?)?(?:\n(?!\n+))([\s\S]+)` | ❌ | Follows character or parenthetical. May contain inline notes `[[ ]]` |
| `parenthetical` | `(direction)` | `^[ \t]*(\(.+\))$` | ❌ | Line wrapped in `()`. Only valid inside dialogue (after character or dialogue) |
| `centered` | `> text <` | `^[ \t]*(?:> *)(.+)(?: *<)(\n.+)*` | ❌ | Rare. Brackets stripped for display |
| `page_break` | `===` | `^\={3,}$` | ❌ | 3+ equals signs |
| `note` | `[[ note ]]` | Inline: `(?:\[{2}(?!\[+))([\s\S]+?)(?:\]]{2}(?!\[+))` | ❌ | Inline notes within action/dialogue. Also standalone `[[ ]]` lines |
| `boneyard` | `/* comment */` | `(\/\*(?:(?!\*\/)[\s\S])*\*\/)` | ❌ | Multi-line comments. State-based: everything between `/*` and `*/` is ignored |
| `lyric` | `~song~` | `^(\~.+)` | ❌ | Starts with `~`. Displayed as `*text*` |
| `dual_dialogue_begin` | (structural) | — | ❌ | Inserted when `^` character cue found. Marks start of dual dialogue block |
| `dual_dialogue_end` | (structural) | — | ❌ | Inserted at end of dual dialogue (empty line or new character) |
| `separator` | Empty line | — | ❌ | Structural: ends dialogue state, resets context |

---

## 2. Scene Boundary Rules

**Only `scene_heading` creates a new scene.**

A scene boundary is triggered when:
1. A line matches `SCENE_HEADING_RE` (starts with `INT.`, `EXT.`, `EST.`, `INT./EXT.`, `I/E.`)
2. OR a line matches `FORCED_SCENE_HEADING_RE` (starts with `.` followed by alphanumeric)

**What does NOT create a scene:**
- `section` (`# Act`) — metadata, hierarchical structure
- `synopsis` (`= summary`) — metadata
- `page_break` (`===`) — visual break, not a scene
- `transition` (`CUT TO:`) — stays within current scene
- `separator` (empty line) — structural only

**Scene numbering:**
- Auto-increment: `scene_number` starts at 1, increments per heading
- Manual override: `#1#` suffix on heading → use that number
- Scene number is stored on the `scene_heading` token

---

## 3. Metadata Tokens (not scenes)

These tokens are structural/metadata and should NOT be treated as scene content:

| Token | Handling |
|-------|----------|
| `title_page` | Parse into key-value dict. Position tracked via `titlePageDisplay` (cc, bl, br, tl, tc, tr, hidden) |
| `section` | Hierarchical. Level = `#` count. Nested: `###` inside `##` inside `#` |
| `synopsis` | Attached to nearest parent section/scene |
| `separator` | Structural only, no content |

**Title page detection:** Starts when first `key: value` line appears before any scene heading. Ends when first non-title-page line (or first scene heading) is encountered.

---

## 4. Character Name Extraction

### Raw character cue formats:
```
KAEL
KAEL (CONT'D)
KAEL (V.O.)
KAEL (O.S.)
KAEL (on the radio)
@McCONNOR
KAEL ^            (dual dialogue)
```

### Extraction logic (from `utils.js`):

1. **Trim force symbol:** Remove leading `@` → `trimCharacterForceSymbol()`
2. **Trim extension:** Remove `(anything)` and optional trailing `^` → `trimCharacterExtension()`
   - Regex: `/[ \t]*(\(.*\))[ \t]*([ \t]*\^)?$/`
3. **Result:** `KAEL (CONT'D)` → `KAEL`

### Important: The `^` suffix
- Appears on the **second** character cue in dual dialogue
- Must be stripped from character name
- Triggers dual dialogue state (previous dialogue becomes `dual:left`, this one `dual:right`)

---

## 5. Dual Dialogue

### Syntax:
```
                BRICK
        Screw retirement.

                STEEL ^
        Screw retirement.
```

### How Better Fountain handles it:
1. When `^` is found on a character cue:
   - State changes to `dual_dialogue`
   - All previous tokens in current dialogue block get `dual = "left"`
   - The new character gets `dual = "right"`
   - `dialogue_begin` token becomes `dual_dialogue_begin`
2. Empty line or new non-dual character ends dual dialogue → `dual_dialogue_end`

### For our port:
- Track `dual_right` state
- When `^` found: mark previous dialogue tokens as `left`, current as `right`
- Store `dual` field on character/dialogue tokens: `"left"`, `"right"`, or `undefined`

---

## 6. Boneyard and Note Handling

### Boneyard (`/* ... */`):
- **Multi-line:** Everything between `/*` and `*/` is ignored
- **Nested comments:** Supported via `nested_comments` counter
- **State-based:** Parser enters `ignore` state during boneyard
- **For our port:** Strip boneyard content entirely (don't include in scene content)

### Inline Notes (`[[ ... ]]`):
- **Within action/dialogue:** Preserved but tracked separately
- **Standalone:** Line containing only `[[ note ]]`
- **For our port:** 
  - Option A: Strip from content, store as metadata on section/scene
  - Option B: Preserve in content but mark with type `note`
  - **Recommendation:** Option A for scene content (clean text), Option B for full tokenization

### Decision for dashboard:
- **Boneyard:** Strip completely (it's a comment, not content)
- **Notes:** Preserve in tokenized output as `note` type, but strip from raw scene content for display

---

## 7. Current Implementation Gaps

The existing `fountain_lexer.py` is a simplified version. What's missing:

| Feature | Current | Needed |
|---------|---------|--------|
| Title page parsing | ✅ Basic regex | ✅ Position tracking, multi-line values |
| Section nesting | ❌ Flat | ✅ Hierarchical with children |
| Synopsis attachment | ❌ | ✅ Attach to parent section/scene |
| Scene number extraction | ❌ | ✅ Parse `#1#` suffix |
| Forced scene heading (`.`) | ✅ Basic | ✅ Full regex |
| Character `@` prefix | ❌ | ✅ Force symbol handling |
| Character extension trim | ❌ Basic split | ✅ Regex-based `(V.O.)` etc. |
| Dual dialogue `^` | ❌ | ✅ Full state machine |
| Boneyard multi-line | ❌ Single-line only | ✅ Nested comment support |
| Inline notes `[[ ]]` | ❌ Standalone only | ✅ Within action/dialogue |
| Lyric `~` | ✅ | ✅ |
| Centered `> <` | ✅ | ✅ |
| Page break `===` | ✅ | ✅ |
| Transition regex | ✅ Basic | ✅ Full (FADE TO BLACK, etc.) |

---

## 8. What We Need for the Dashboard

### Scene extraction must provide:
```python
{
    "id": 1,                          # Scene number
    "heading": "INT. ROOM - DAY",     # Raw heading text
    "heading_slug": "int-room-day",   # For anchors/links
    "location": "ROOM",               # Parsed location
    "time_of_day": "DAY",             # Parsed time
    "interior": True,                 # INT vs EXT
    "exterior": False,
    "characters": ["KAEL", "MIRA"],   # Unique character names (extensions stripped)
    "content": "...",                 # Raw Fountain text (preserves formatting)
    "content_html": "...",            # Tokenized HTML with CSS classes
    "action_length": 1.5,             # Estimated duration (seconds)
    "dialogue_length": 2.0,           # Estimated duration (seconds)
    "dual_dialogue": False,           # Whether scene contains dual dialogue
    "notes": [],                      # Inline notes found in scene
}
```

### Tokenization for HTML rendering:
- Each line → `<p class="fountain-{type}">escaped text</p>`
- CSS handles indentation per type
- Scene heading → `<h3>` with data attributes
- Character → `<h4>` with dual class if applicable
- Dialogue → `<p>` with character reference

---

## 9. Migration Plan

### Phase 1: Port the Lexer (`core/fountain_lexer.py`)
- Port all regex patterns from `afterwriting-parser.js`
- Implement state machine: `normal`, `dialogue`, `dual_dialogue`, `title_page`, `ignore`
- Handle boneyard nesting
- Handle inline notes within action/dialogue
- Extract character extensions with regex
- **Verification:** Tokenize `screenplay.fountain`, print all tokens with types

### Phase 2: Port Scene Extraction (`core/screenplay.py`)
- Replace `extract_scenes` to use new lexer
- Parse scene heading metadata (location, time, interior/exterior)
- Track dual dialogue state
- Strip boneyard from content
- **Verification:** Run on test fixture, verify scene count and character extraction

### Phase 3: Update Index (`core/index.py`)
- Use new scene extraction
- No structural changes needed (interface is the same)
- **Verification:** Generate index, verify character scenes populated

### Phase 4: Update Dashboard HTML/CSS
- Use new token types for rendering
- Add dual dialogue CSS classes
- Add note styling
- **Verification:** Open dashboard in preview pane, verify formatting

### Phase 5: Remove screenplay-tools dependency
- Remove from `pyproject.toml`
- Remove `tests/test_screenplay_library.py`
- Update any remaining imports
- **Verification:** `pip install -e .` succeeds, all tests pass

---

## 10. Test Requirements

### Unit tests (`tests/test_fountain_lexer.py`):
1. **Token type classification:** Every token type correctly identified
2. **Scene boundary detection:** Scene headings split correctly
3. **Character name extraction:** Extensions stripped, `@` prefix handled
4. **Dual dialogue:** `^` suffix triggers dual state
5. **Boneyard:** Multi-line comments stripped, nesting works
6. **Inline notes:** `[[ ]]` extracted from action/dialogue
7. **Title page:** Key-value pairs parsed, position tracked
8. **Section nesting:** Hierarchical structure preserved
9. **Forced headings:** `.SCENE` recognized as scene heading
10. **Transition:** `CUT TO:`, `FADE TO BLACK.` recognized

### Integration test:
- Use `tests/fixtures/the-water-audit/screenplay.fountain`
- Verify 3 scenes extracted
- Verify characters `MARA`, `OAK`, `CAPTAIN` found
- Verify location extraction works

---

## 11. Open Questions

1. **Boneyard in scene content:** Strip completely or preserve as `<!-- HTML comment -->`?
   - Decision: Strip from raw content, don't include in `content_html`

2. **Inline notes in scene content:** Preserve or strip?
   - Decision: Strip from `content` (clean text), include in `notes` array

3. **Title page in scene extraction:** Include as scene 0 or separate?
   - Decision: Separate. `extract_scenes()` returns only scenes, title page handled by separate parser

4. **Section hierarchy in scene extraction:** Include sections as scene metadata?
   - Decision: Yes, attach nearest section to each scene

5. **Dual dialogue rendering:** Side-by-side or sequential?
   - Decision: Sequential with CSS classes (simpler, side-by-side is complex)

---

## 12. Acceptance Criteria

- [ ] All 14 Fountain token types correctly classified
- [ ] Scene boundaries match Better Fountain's output
- [ ] Character names extracted with extensions stripped
- [ ] Dual dialogue state tracked correctly
- [ ] Boneyard content stripped from scene text
- [ ] Inline notes extracted and stored separately
- [ ] Title page parsed into structured data
- [ ] Section hierarchy preserved
- [ ] `screenplay-tools` removed from dependencies
- [ ] All existing tests pass
- [ ] New lexer tests pass
- [ ] Dashboard renders correctly with new tokenization
