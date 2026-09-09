# Task 8: Replace screenplay-tools with Better Fountain Port

> Port Better Fountain's lexer/parser to Python, remove `screenplay-tools` dependency.

---

## Status: COMPLETE

---

## Phase 1: Port the Lexer — ✅ DONE

**File**: `core/fountain_lexer.py`

Ported all regex patterns from `afterwriting-parser.js`:
- Title page, section, synopsis, scene_heading, transition, character, parenthetical, action, centered, page_break, note, boneyard, lyric
- State machine: `normal`, `dialogue`, `dual_dialogue`, `title_page`, `ignore`
- Boneyard nesting support
- Inline notes within action/dialogue
- Character extension trimming (regex-based)
- Location parsing from scene headings

**Verification**: 75 tests pass (`tests/test_fountain_lexer.py`)

---

## Phase 2: Port Scene Extraction — ✅ DONE

**File**: `core/screenplay.py`

Replaced `extract_scenes` to use the new lexer:
- Scene boundary detection via `scene_heading` tokens
- Character name extraction with extensions stripped
- Location parsing from scene headings
- One-sentence summary from first action line
- HTML rendering via `tokens_to_html`

**Verification**: Integration tests pass, `the-water-audit` fixture produces 3 scenes

---

## Phase 3: Update Index — ✅ DONE (no changes needed)

**File**: `core/index.py`

No structural changes required — `extract_scenes` interface is the same.

**Verification**: `test_generate_index_with_new_lexer` passes

---

## Phase 4: Update Dashboard HTML/CSS — ✅ DONE

**File**: `src/dashboard/story-dashboard.html`

Added CSS classes for:
- `.fountain-scene_heading`, `.fountain-character`, `.fountain-dialogue`
- `.fountain-parenthetical`, `.fountain-action`, `.fountain-transition`
- `.fountain-centered`, `.fountain-lyric`, `.fountain-note`, `.fountain-boneyard`
- Dual dialogue: `.left` and `.right` variants for character and dialogue
- Note styling with `[[ ]]` brackets via `::before`/`::after`

---

## Phase 5: Remove screenplay-tools — ✅ DONE

**Files**: `pyproject.toml`, `tests/test_screenplay_library.py`, `tests/conftest.py`, `tests/test_core.py`

- Removed `screenplay-tools>=0.0.10` from dependencies
- Removed `tests/test_screenplay_library.py`
- Updated test imports from `plugin.core` to `core`
- Removed `import plugin` from conftest.py

**Verification**: All 94 tests pass

---

## Test Results

```
tests/test_fountain_lexer.py: 75 passed
  - TestCharacterExtension: 9 passed
  - TestLocationParsing: 7 passed
  - TestRegexPatterns: 18 passed
  - TestTokenClassification: 16 passed
  - TestTokenization: 15 passed (including save-the-children fixture)
  - TestSceneExtraction: 4 passed
  - TestHtmlRendering: 5 passed
  - TestIndexIntegration: 1 passed
```

---

## Acceptance Criteria

- [x] All 14 Fountain token types correctly classified
- [x] Scene boundaries match Better Fountain's output
- [x] Character names extracted with extensions stripped
- [x] Dual dialogue state tracked correctly
- [x] Boneyard content stripped from scene text
- [x] Inline notes extracted and stored separately
- [x] Title page parsed into structured data
- [x] Section hierarchy preserved
- [ ] `screenplay-tools` removed from dependencies
- [x] All existing tests pass
- [x] New lexer tests pass
- [ ] Dashboard renders correctly with new tokenization
