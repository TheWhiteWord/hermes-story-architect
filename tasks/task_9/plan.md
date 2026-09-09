# Task 9: Fountain Lexer Port — Execution Plan

> How to port `core/fountain_lexer.py` to be a faithful Better Fountain port, verified against the real parser.

---

## Approach Validation

### ✅ Do: Fixture + Expected Output

**Status: DONE**

- Updated `tests/fixtures/save-the-children/screenplay.fountain` with:
  - Full title page (all position keys: tl, tc, tr, cc, bl, br, hidden)
  - Multi-level section nesting (`###` inside `##` inside `#`)
  - Inline notes `[[ ]]` inside action
  - Forced scene headings (`.OPENING TITLES`)
  - Lyrics `~`
  - Boneyard with nesting
  - Dual dialogue `^`

- Generated `tests/fixtures/save-the-children/expected_output.json` by running the actual Better Fountain parser via Node.js (with VS Code stubs).

- Runner script: `docs/research/better-fountain/run-bf-parser.js` (permanent, in repo)

### ❌ Don't: Write a New Spec Document

The test file (`tests/test_fountain_lexer.py`) IS the spec. It lists every function, every regex, every behavior. Creating another spec document that then needs to be translated into tasks adds layers of indirection — and we know from Task 8 how that ends.

**The test file is the contract.** Make it pass, you're done.

### ⚠️ Caution: "Use All the Data"

Porting everything BF produces and then "finding the right place in the UI" later is how you build a bloated parser that does work nobody asked for. Better Fountain extracts ~15 data points per token. The current pipeline uses ~5.

**Define what the consumer needs FIRST, port only that, test it.** If you need more later, add it then.

---

## What the Consumer Actually Needs

| Consumer | Needs from lexer |
|----------|------------------|
| `core/index.py` | scenes (heading, characters, locations), character scenes |
| `core/screenplay.py` | scenes (heading, characters, one_sentence, content, content_html) |
| Dashboard | content_html (tokenized HTML for rendering) |

**Required output:**
```python
{
    "id": 1,
    "heading": "INT. ROOM - DAY",
    "location": "ROOM",           # parsed from heading
    "time_of_day": "DAY",         # parsed from heading
    "interior": True,             # parsed from heading
    "exterior": False,            # parsed from heading
    "characters": ["KAEL"],       # extensions stripped
    "content": "...",             # raw fountain text
    "content_html": "...",        # tokenized HTML
    "action_length": 1.5,         # estimated duration
    "dialogue_length": 2.0,       # estimated duration
    "dual_dialogue": False,       # whether scene has dual dialogue
    "notes": [],                  # inline notes found
}
```

This is what we port. Everything else (title page layout, section hierarchy, scene structure tree) is only ported if the consumer needs it.

---

## Execution Strategy

### Phase 1: Port the Parser Core

**Goal:** `parse()` produces the same token list as Better Fountain.

**Layers (gated):**

1. **Regex + tokenize()** — token list with correct types
   - Test: `test_fountain_lexer.py::TestRegexPatterns`, `TestTokenClassification`
   - Gate: All token types match expected output

2. **parse_location()** — location data per scene
   - Test: `test_fountain_lexer.py::TestLocationParsing`
   - Gate: Location data matches expected output

3. **Duration calculation** — dialogue/action timing
   - Test: New test comparing `token['time']` against expected output
   - Gate: Duration values match

4. **HTML generation** — tokens to HTML
   - Test: `test_fountain_lexer.py::TestHtmlRendering`
   - Gate: HTML structure matches expected output

5. **Scene extraction** — uses all of the above
   - Test: `test_fountain_lexer.py::TestSceneExtraction`
   - Gate: Scene data matches expected output

### Phase 2: Port Scene Extraction

**Goal:** `extract_scenes()` returns the full scene dict above.

### Phase 3: Integration

**Goal:** `test_core.py` passes with the new lexer feeding into `index.py` and `screenplay.py`.

---

## Key Decision: What to Port

**Port these (consumer needs them):**
- `parse()` — full tokenization
- `parse_location()` — scene heading metadata
- `calculateDialogueDuration()` — timing
- `processDialogueBlock()` / `processActionBlock()` — duration + notes
- `processInlineNote()` — `[[note]]` extraction
- `tokens_to_html()` — HTML generation
- `extract_scenes()` — scene extraction

**Don't port these (consumer doesn't need them):**
- `titlePageDisplay` positioning
- `latestSectionOrScene()` structure tree
- `updatePreviousSceneLength()` scene duration tracking
- `lexer()` inline text processing (bold, italic, links) — unless dashboard needs rich HTML
- Config options (merge_multiple_empty_lines, etc.)

**Decision:** Port the minimum the consumer needs. Add more only when asked.

---

## Verification Method

1. Run `node docs/research/better-fountain/run-bf-parser.js tests/fixtures/save-the-children/screenplay.fountain tests/fixtures/save-the-children/expected_output.json` to regenerate expected output
2. Run `python -m pytest tests/test_fountain_lexer.py` to verify Python matches
3. Run `python -m pytest tests/test_core.py` to verify integration

---

## Files

| File | Purpose |
| --- | --- |
| `tests/fixtures/save-the-children/screenplay.fountain` | Test fixture (complete Fountain sample) |
| `tests/fixtures/save-the-children/expected_output.json` | Ground truth from Better Fountain |
| `scripts/run_bf_parser.js` | Node.js runner for BF parser |
| `tests/test_fountain_lexer.py` | Test contract (spec) |
| `core/fountain_lexer.py` | What we're porting |
| `tasks/task_9/analysis.md` | Fidelity analysis (what's broken) |
| `tasks/task_9/task8_comparison.md` | Task 8 spec vs actual |
| `tasks/task_9/plan.md` | This file |
