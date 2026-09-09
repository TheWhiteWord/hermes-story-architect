# Task 9: Fountain Lexer Port — Fidelity Analysis

> Assessment of how faithfully `core/fountain_lexer.py` ports Better Fountain's `afterwriting-parser.js`.

---

## What's Faithful

| Component | Status | Notes |
|-----------|--------|-------|
| Regex patterns | ✅ Exact | Copied verbatim from JS lines 29-55 |
| Token structure | ✅ Exact | Same fields as `token.js` |
| `trim_character_extension` | ✅ Exact | Same regex |
| `trim_character_force_symbol` | ✅ Exact | Same regex |
| State machine skeleton | ✅ Partial | States exist but transitions incomplete |
| Classification order | ✅ Partial | Normal state order matches |
| `create_token()` | ✅ Exact | Same logic |

---

## What's Broken

### 1. `parse_location_information` — BUG

**JS** (utils.js line 62-74):
```javascript
let splitLocationFromTime = scene_heading[2].match(/(.*)[-–—−](.*)/);
return {
    name: splitLocationFromTime ? splitLocationFromTime[1].trim() : scene_heading[2].trim(),
    time_of_day: splitLocationFromTime ? splitLocationFromTime[2].trim() : ""
};
```

**Python** (line 75-86):
```python
split = re.search(r'[-–—−](.*)', location_text)
return {
    'name': split.group(1).strip() if split else location_text.strip(),
    'time_of_day': split.group(1).strip() if split else '',
}
```

**Problem:** Regex `r'[-–—−](.*)'` captures AFTER the dash as group(1). JS uses `/(.*)[-–—−](.*)/` where group(1) is BEFORE the dash. Result: `name` and `time_of_day` are **swapped**. Every scene heading produces wrong location data.

---

### 2. Boneyard State Handling — BUG

**JS** (lines 277-286):
```javascript
if (nested_comments && state !== "ignore") {
    cache_state_for_comment = state;
    state = "ignore";
}
else if (state === "ignore") {
    state = cache_state_for_comment;  // restore previous state
}
```

**Python** (line 163-166):
```python
if nested_comments > 0 and state != 'ignore':
    state = 'ignore'
elif state == 'ignore' and nested_comments == 0:
    state = 'normal'  # always resets to normal
```

**Problem:** If you're in `dialogue` state and hit a `/* */` block, JS remembers you were in dialogue and resumes after. Python resets to `normal`, so the next line won't parse as dialogue. Multi-line comments inside dialogue break parsing.

---

### 3. Empty Line / Separator Handling — INCOMPLETE

**JS** (lines 291-301):
```javascript
var skip_separator = (cfg.merge_multiple_empty_lines && last_was_separator) || 
                     (ignoredLastToken && ...);
if (skip_separator || state === "title_page") {
    continue;  // skip pushing this separator
}
```

**Python** (line 173-183):
```python
if text.strip() == '' and text != '  ':
    # ... close dialogue ...
    thistoken['type'] = 'separator'
    last_was_separator = True
    push_token(thistoken)  # always pushes
```

**Problem:** No `skip_separator` logic. Consecutive empty lines produce multiple separator tokens instead of merging. `ignoredLastToken` tracking exists but does nothing.

---

### 4. Scene Heading — INCOMPLETE

**JS** (lines 342-394):
- Creates `StructToken` objects
- Tracks in `result.properties.structure` (hierarchical)
- Calls `updatePreviousSceneLength()` for duration tracking
- Tracks locations via `slugify(parseLocationInformation(...))` in a Map
- Pushes `page_break` token if `cfg.each_scene_on_new_page`

**Python** (lines 206-220):
- Appends a flat dict to `result['properties']['scenes']`
- No structure tracking
- No duration tracking
- No location tracking
- No `page_break` insertion

---

### 5. Dual Dialogue — INCOMPLETE

**JS** (lines 454-491):
When `^` found on character cue:
1. Walks backward through tokens
2. Marks all previous dialogue tokens as `dual: "left"`
3. Converts `dialogue_begin` → `dual_dialogue_begin`
4. Removes trailing `dialogue_end`
5. Sets `dual_right = True`

**Python** (lines 261-265):
```python
if thistoken['text'].endswith('^'):
    state = 'dual_dialogue'
    dual_right = True
    thistoken['dual'] = 'right'
```

**Problem:** No lookback. Previous dialogue tokens never get `dual: "left"`. `dialogue_begin` never becomes `dual_dialogue_begin`. The left side of dual dialogue is lost.

---

### 6. Sections — INCOMPLETE

**JS** (lines 418-437):
- Creates `StructToken` with `section: true`
- Nests children under parent sections
- Tracks hierarchy via `latestSectionOrScene()`

**Python** (lines 239-244):
```python
thistoken['type'] = 'section'
current_depth = thistoken['level']
```

**Problem:** No `StructToken` creation, no nesting, no hierarchy. `current_depth` is set but never used to build structure.

---

### 7. Synopsis — INCOMPLETE

**JS** (lines 409-416):
```javascript
var level = latestSectionOrScene(current_depth + 1, () => true);
if (level) {
    level.synopses = level.synopses || [];
    level.synopses.push({ synopsis: thistoken.text, line: thistoken.line });
}
```

**Python:** No synopsis tracking at all.

---

### 8. HTML Generation — INCOMPLETE

**JS** (lines 558-743): ~185 lines, handles all 18 token types:
- Title page HTML with grid positioning
- Script HTML with full token-to-HTML mapping
- Action block wrapping logic
- Dual dialogue div structure
- Section, synopsis, note, boneyard, lyric, page break

**Python** (lines 359-401): ~40 lines, handles 8 types:
- scene_heading, transition, dialogue_begin, character, parenthetical, dialogue, dialogue_end, page_break

**Missing:** section, synopsis, note, boneyard, lyric, centered (partial), title page, dual_dialogue_begin/end.

---

## What's Missing Entirely

| Function | JS Source | Purpose |
|----------|-----------|---------|
| `lexer()` | afterwriting-parser.js:93-115 | Inline text processing (bold, italic, links, notes) |
| `calculateDialogueDuration()` | utils.js:145-162 | Dialogue timing estimate |
| `processDialogueBlock()` | afterwriting-parser.js:251-261 | Duration + inline note extraction for dialogue |
| `processActionBlock()` | afterwriting-parser.js:262-271 | Duration + inline note extraction for action |
| `processInlineNote()` | afterwriting-parser.js:229-250 | `[[note]]` extraction |
| `latestSectionOrScene()` | afterwriting-parser.js:202-228 | Section/scene structure navigation |
| `updatePreviousSceneLength()` | afterwriting-parser.js:192-201 | Scene duration tracking |
| `titlePageDisplay` | afterwriting-parser.js:56-79 | Title page position layout |
| `takeCount` | afterwriting-parser.js:191 | Dialogue take numbers |
| `cache_state_for_comment` | afterwriting-parser.js:173 | State preservation during boneyard |
| Config options | configloader.js | `merge_multiple_empty_lines`, `each_scene_on_new_page`, etc. |

---

## Verdict

**The port is ~40% faithful.** It has the right skeleton — regex patterns, token structure, state machine shape, classification order. But it's missing the majority of the functionality that makes Better Fountain useful:

- **Structure tracking** (sections, scenes, hierarchy)
- **Inline processing** (bold, italic, links, notes)
- **Duration calculation** (dialogue/action timing)
- **Dual dialogue** (lookback, left/right marking)
- **HTML generation** (full token-to-HTML mapping)
- **Boneyard state caching** (preserving dialogue state across comments)

The `parse_location_information` bug alone would produce wrong data for every scene heading.

**Recommendation:** Not worth fixing incrementally. The missing 60% is tightly coupled — you can't add HTML generation without structure tracking, which needs `latestSectionOrScene`, which needs `StructToken`, which needs the full rewrite anyway. Start from the JS line-by-line and port it completely.
