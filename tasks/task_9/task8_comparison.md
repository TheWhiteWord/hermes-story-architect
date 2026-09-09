# Task 8 Spec vs. Actual Implementation

> Comparison of what Task 8 specified vs. what was actually built in `core/fountain_lexer.py`.

---

## Summary

**~25% of the spec was implemented.** The skeleton (regex, token structure, state machine shape) is there, but most substance is missing.

---

## Section-by-Section Analysis

### 1. Token Types (14 conventions)

| Token | Spec | Actual | Status |
|-------|------|--------|--------|
| `title_page` | Position tracking, multi-line values | Basic regex only, no position tracking | ⚠️ Partial |
| `section` | Hierarchical with children | Flat, no nesting | ❌ Missing |
| `synopsis` | Attach to parent section/scene | Basic parsing, no attachment | ❌ Missing |
| `scene_heading` | Scene number suffix `#1#` | Regex exists, not integrated | ⚠️ Partial |
| `transition` | Full regex | Basic regex works | ✅ Done |
| `action` | Fallback | Works | ✅ Done |
| `character` | `@` prefix, extensions | Regex works, basic parsing | ✅ Done |
| `dialogue` | After character | Works | ✅ Done |
| `parenthetical` | In dialogue state | Works | ✅ Done |
| `centered` | `> text <` | Works | ✅ Done |
| `page_break` | `===` | Works | ✅ Done |
| `note` | Inline `[[ ]]` extraction | Regex exists, no extraction | ❌ Missing |
| `boneyard` | Multi-line, nested, state-based | Basic multi-line, buggy state | ⚠️ Buggy |
| `lyric` | `~` prefix | Works | ✅ Done |
| `dual_dialogue_begin/end` | Structural tokens | Not created | ❌ Missing |
| `separator` | Empty line | Works | ✅ Done |

**Score: 7/15 fully done, 3/15 partial, 5/15 missing**

---

### 2. Scene Boundary Rules

| Requirement | Actual |
|-------------|--------|
| Only `scene_heading` creates scene | ✅ Correct |
| Auto-increment scene number | ✅ Correct |
| Manual override with `#1#` | ⚠️ Regex exists, not integrated |

---

### 3. Metadata Tokens

| Requirement | Actual |
|-------------|--------|
| Title page position tracking (`titlePageDisplay`) | ❌ Not implemented |
| Section nesting (hierarchical) | ❌ Not implemented |
| Synopsis attachment to parent | ❌ Not implemented |

---

### 4. Character Name Extraction

| Requirement | Actual |
|-------------|--------|
| `trimCharacterForceSymbol()` | ✅ Implemented |
| `trimCharacterExtension()` | ✅ Implemented |
| `@` prefix handling | ✅ In regex |

**Score: 3/3 done**

---

### 5. Dual Dialogue

| Requirement | Actual |
|-------------|--------|
| State changes to `dual_dialogue` | ✅ Basic |
| Previous tokens marked `dual: "left"` | ❌ No lookback |
| `dialogue_begin` → `dual_dialogue_begin` | ❌ Not done |
| `dual_dialogue_end` on empty line | ✅ Exists |

**Score: 2/4 done**

---

### 6. Boneyard and Note Handling

| Requirement | Actual |
|-------------|--------|
| Multi-line comments | ✅ Basic support |
| Nested comments (counter) | ✅ Counter exists |
| State preservation (`cache_state_for_comment`) | ❌ Buggy — always resets to `normal` |
| Inline note extraction `[[ ]]` | ❌ Not implemented |

**Score: 2/4 done (1 buggy)**

---

### 7. Dashboard Requirements (Section 8)

The spec defines required fields for scene extraction. Here's what `extract_scenes()` actually returns:

| Field | Spec | Actual |
|-------|------|--------|
| `id` | ✅ | ✅ |
| `heading` | ✅ | ✅ |
| `heading_slug` | ✅ | ❌ |
| `location` | ✅ | ❌ |
| `time_of_day` | ✅ | ❌ |
| `interior` | ✅ | ❌ |
| `exterior` | ✅ | ❌ |
| `characters` | ✅ | ✅ |
| `content` | ✅ | ✅ |
| `content_html` | ✅ | ⚠️ Simplified (8 token types vs 18) |
| `action_length` | ✅ | ❌ |
| `dialogue_length` | ✅ | ❌ |
| `dual_dialogue` | ✅ | ❌ |
| `notes` | ✅ | ❌ |

**Score: 5/14 fully present**

---

### 8. Migration Plan (Section 9)

| Phase | Description | Status |
|-------|-------------|--------|
| Phase 1 | Port the Lexer | ⚠️ ~40% done |
| Phase 2 | Port Scene Extraction | ⚠️ Simplified version |
| Phase 3 | Update Index | ✅ Done (uses screenplay.py) |
| Phase 4 | Update Dashboard HTML/CSS | ❌ Not done |
| Phase 5 | Remove screenplay-tools | ✅ Already removed from pyproject.toml |

---

### 9. Test Requirements (Section 10)

| Test | Status |
|------|--------|
| Token type classification | ❌ Fails (imports missing functions) |
| Scene boundary detection | ❌ Fails |
| Character name extraction | ❌ Fails |
| Dual dialogue | ❌ Fails |
| Boneyard | ❌ Fails |
| Inline notes | ❌ Fails |
| Title page | ❌ Fails |
| Section nesting | ❌ Fails |
| Forced headings | ❌ Fails |
| Transition | ❌ Fails |

**Score: 0/10 passing**

---

### 10. Acceptance Criteria (Section 12)

| Criterion | Status |
|-----------|--------|
| All 14 token types classified | ⚠️ Partial |
| Scene boundaries match BF | ⚠️ Partial |
| Character names extracted | ✅ Yes |
| Dual dialogue tracked | ❌ No |
| Boneyard stripped | ⚠️ Partial |
| Inline notes extracted | ❌ No |
| Title page parsed | ❌ No |
| Section hierarchy preserved | ❌ No |
| screenplay-tools removed | ✅ Yes |
| All existing tests pass | ❌ No |
| New lexer tests pass | ❌ No |
| Dashboard renders correctly | ❌ No |

**Score: 3/12 fully met**

---

## What the Spec Got Right

The spec's **Section 7 (Current Implementation Gaps)** is essentially the same as my Task 9 analysis. It correctly identified:
- Section nesting missing
- Synopsis attachment missing
- Dual dialogue incomplete
- Boneyard state handling buggy
- Inline notes missing

The spec was accurate about what needed to be done. The problem is execution didn't match the spec.

---

## Bottom Line

| Category | Spec Items | Done | Partial | Missing |
|----------|-----------|------|---------|---------|
| Token types | 15 | 7 | 3 | 5 |
| Scene boundaries | 3 | 2 | 1 | 0 |
| Metadata tokens | 3 | 0 | 0 | 3 |
| Character extraction | 3 | 3 | 0 | 0 |
| Dual dialogue | 4 | 2 | 0 | 2 |
| Boneyard/notes | 4 | 2 | 0 | 2 |
| Dashboard fields | 14 | 5 | 1 | 8 |
| Migration phases | 5 | 2 | 2 | 1 |
| Tests | 10 | 0 | 0 | 10 |
| Acceptance criteria | 12 | 3 | 0 | 9 |
| **TOTAL** | **73** | **26** | **7** | **40** |

**Implementation rate: ~36% done, ~9% partial, ~55% missing**

The spec was a good contract. It just wasn't followed.
