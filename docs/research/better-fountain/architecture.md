# Better Fountain — Complete Architecture Research

> Source: `/home/davide/.vscode/extensions/piersdeseilligny.betterfountain-1.14.2/out/`
> Compiled from TypeScript → JavaScript. All paths below are under `out/`.

---

## 1. File Map

| File | Role |
|------|------|
| `afterwriting-parser.js` | **Core parser** — regex definitions, token creation, line classification, HTML generation |
| `token.js` | Token factory — `create_token()` |
| `helpers.js` | Token helper methods (`is()`, `name()`, `location()`, etc.) |
| `utils.js` | Utility functions (slugify, dialogue duration, location parsing, scene numbering, etc.) |
| `configloader.js` | Configuration loading from VS Code settings |
| `scenenumbering.js` | Scene numbering schema (standard, alphanumeric) |
| `statistics.js` | Statistics computation (characters, locations, duration, readability) |
| `commands.js` | VS Code commands (export PDF, jump to, shift scenes, etc.) |
| `extension.js` | Extension entry point — wires everything together |
| `providers/StaticHtml.js` | Static HTML export command |
| `providers/Preview.js` | Live preview webview panel |
| `providers/Outline.js` | Outline tree view (sections, scenes, notes, synopses) |
| `providers/Characters.js` | Characters tree view |
| `providers/Locations.js` | Locations tree view |
| `providers/Completion.js` | Autocomplete provider |
| `providers/Folding.js` | Folding range provider |
| `providers/Symbols.js` | Document symbol provider |
| `providers/Scene.js` | Scene tree item |
| `pdf/pdf.js` | PDF generation orchestration |
| `pdf/liner.js` | Line wrapping and page breaking for PDF |
| `pdf/print.js` | Print profiles (A4, US Letter) with margins, max widths |
| `webviews/preview.html` | Live preview HTML template + CSS |
| `webviews/common.css` | Shared CSS (status bar) |
| `assets/staticexport.html` | Static HTML export template |

---

## 2. Token Types — Complete Classification

### 2.1 Token Structure (`token.js`)

Every token is created via `create_token(text, cursor, line, new_line_length, type)`:

```javascript
{
    text: string,           // The raw text content
    type: string,           // One of the types below
    start: number,          // Character offset start
    end: number,            // Character offset end
    line: number,           // Line number in source
    ignore: boolean,        // If true, token is skipped in output
    number: string,         // Scene number (scene_heading only)
    dual: string,           // "left" | "right" | undefined (dual dialogue)
    html: string,           // Processed HTML (populated during HTML generation)
    level: number,          // Section depth (section only)
    time: number,           // Duration in seconds (action/dialogue)
    character: string,      // Character name (dialogue tokens)
    index: number,          // Sort index (title page tokens)
    takeNumber: number,     // Sequential take number (character tokens)
    original_line: number,  // Original 1-based line number
    is: function(...args),  // Type check helper
    is_dialogue: function(),
    name: function(),       // Character name without parenthetical
    location: function(),   // Scene heading location
    has_scene_time: function(time),
    location_type: function() // "int" | "ext" | "mixed" | "other"
}
```

### 2.2 All Token Types

| Token Type | Description | Source Pattern |
|------------|-------------|----------------|
| `scene_heading` | Scene heading | `INT.`, `EXT.`, `INT./EXT.`, `I/E`, `EST.`, or forced with `.` prefix |
| `transition` | Transition | `FADE TO BLACK.`, `CUT TO BLACK.`, `TO:`, or `> text` |
| `character` | Character name | All-caps line (with optional `@` force, `^` for dual, parenthetical extension) |
| `dialogue` | Dialogue text | Line following character/parenthetical in dialogue state |
| `parenthetical` | Parenthetical | Line wrapped in `( )` during dialogue state |
| `action` | Action/description | Default fallback — any non-empty line that doesn't match other patterns |
| `section` | Section heading | Line starting with `#` (1-6 levels) |
| `synopsis` | Synopsis | Line starting with `=` (not `==`) |
| `centered` | Centered text | `> text <` |
| `note` | Inline note | `[[text]]` (processed inline, not a standalone token type) |
| `boneyard_begin` | Comment block start | `/*` |
| `boneyard_end` | Comment block end | `*/` |
| `page_break` | Page break | `===` (3+ equals signs) |
| `lyric` | Lyric/song | Line starting with `~` |
| `dual_dialogue_begin` | Dual dialogue start | Created when `^` is found on character name |
| `dual_dialogue_end` | Dual dialogue end | Created at end of dual dialogue block |
| `dialogue_begin` | Dialogue block start | Created before first character token |
| `dialogue_end` | Dialogue block end | Created after last dialogue token |
| `separator` | Empty line | Created for blank lines between tokens |

---

## 3. Line Classification — Regex Definitions

All regex patterns are in `afterwriting-parser.js` lines 29-55:

```javascript
exports.regex = {
    // Title page: key: value pairs
    title_page: /(title|credit|author[s]?|source|notes|draft date|date|watermark|contact( info)?|revision|copyright|font|tl|tc|tr|cc|br|bl|header|footer)\:.*/i,
    
    // Section: one or more # followed by text
    section: /^[ \t]*(#+)(?: *)(.*)/,
    
    // Synopsis: = followed by text (not ==)
    synopsis: /^[ \t]*(?:\=(?!\=+) *)(.*)/,
    
    // Scene heading: .prefix, INT., EXT., INT./EXT., I/E, EST.
    scene_heading: /^[ \t]*([.](?![.])|(?:[*]{0,3}_?)(?:int|ext|est|int[.]?\/ext|i[.]?\/e)[. ])(.+?)(#[-.0-9a-z]+#)?$/i,
    
    // Scene number: #number# at end of scene heading
    scene_number: /#(.+)#/,
    
    // Transition: FADE TO BLACK., CUT TO BLACK., XXX TO:, TO:, > text
    transition: /^[ \t]*((?:FADE (?:TO BLACK|OUT)|CUT TO BLACK)\.|.+ TO\:|^TO\:$)|^(?:> *)(.+)/,
    
    // Dialogue: starts with _ or * (emphasis), optional ^, followed by text
    dialogue: /^[ \t]*([*_]+[^\p{Ll}\p{Lo}\p{So}\r\n]*)(\^?)?(?:\n(?!\n+))([\s\S]+)/u,
    
    // Character: all-caps (with optional @ force), optional parenthetical, optional ^
    character: /^[ \t]*(?![#!]|(\[\[)|(SUPERIMPOSE:))(((?!@)[^\p{Ll}\r\n]*?\p{Lu}[^\p{Ll}\r\n]*?)|((@)[^\r\n]*?))(\(.*\))?(\s*\^)?$/u,
    
    // Parenthetical: text wrapped in parentheses
    parenthetical: /^[ \t]*(\(.+\))$/,
    
    // Action: any non-empty line (fallback)
    action: /^(.+)/g,
    
    // Centered: > text <
    centered: /^[ \t]*(?:> *)(.+)(?: *<)(\n.+)*/g,
    
    // Page break: 3+ equals signs
    page_break: /^\={3,}$/,
    
    // Line break: exactly 2 spaces
    line_break: /^ {2}$/,
    
    // Inline note: [[text]]
    note_inline: /(?:\[{2}(?!\[+))([\s\S]+?)(?:\[]{2}(?!\[+))/g,
    
    // Emphasis: _text_, *text**, **text**, ***text***, etc.
    emphasis: /(_|\*{1,3}|_\*{1,3}|\*{1,3}_)(.+)(_|\*{1,3}|_\*{1,3}|\*{1,3}_)/g,
    
    // Bold+Italic+Underline: _***text***_ or ***_text_***
    bold_italic_underline: /(_{1}\*{3}(?=.+\*{3}_{1})|\*{3}_{1}(?=.+_{1}\*{3}))(.+?)(\*{3}_{1}|_{1}\*{3})/g,
    
    // Bold+Underline: _**text**_ or **_text_**
    bold_underline: /(_{1}\*{2}(?=.+\*{2}_{1})|\*{2}_{1}(?=.+_{1}\*{2}))(.+?)(\*{2}_{1}|_{1}\*{2})/g,
    
    // Italic+Underline: _*text*_ or *_*text*_
    italic_underline: /(?:_{1}\*{1}(?=.+\*{1}_{1})|\*{1}_{1}(?=.+_{1}\*{1}))(.+?)(\*{1}_{1}|_{1}\*{1})/g,
    
    // Bold+Italic: ***text***
    bold_italic: /(\*{3}(?=.+\*{3}))(.+?)(\*{3})/g,
    
    // Bold: **text**
    bold: /(\*{2}(?=.+\*{2}))(.+?)(\*{2})/g,
    
    // Italic: *text*
    italic: /(\*{1}(?=.+\*{1}))(.+?)(\*{1})/g,
    
    // Link: [text](url)
    link: /(\[?(\[)([^\[]*\[?[^\[]*\]?[^\[]*)(\])(\()(.+?)(?:\s+(["'])(.*?)\4)?(\)))/g,
    
    // Lyric: ~text
    lyric: /^(\~.+)/g,
    
    // Underline: _text_
    underline: /(_{1}(?=.+_{1}))(.+?)(_{1})/g,
};
```

---

## 4. Parser State Machine

The parser processes lines sequentially with a state machine:

### States

| State | Description |
|-------|-------------|
| `normal` | Default — classifying script tokens |
| `title_page` | Processing title page key-value pairs |
| `dialogue` | After a character name — expecting dialogue/parenthetical |
| `dual_dialogue` | After a `^` character — dual dialogue mode |
| `ignore` | Inside a `/* */` comment block |

### Classification Order (in `normal` state)

1. **Empty line** → `separator` (or skip if merging)
2. **Title page** (if not started and matches `title_page` regex)
3. **Line break** (exactly 2 spaces) → skip
4. **Scene heading** → `scene_heading`
5. **Action with `!` prefix** → `action` (forced)
6. **Centered** (`> text <`) → `centered`
7. **Transition** → `transition`
8. **Synopsis** (`= text`) → `synopsis`
9. **Section** (`# text`) → `section`
10. **Page break** (`===`) → `page_break`
11. **Character** (all-caps + next line not empty) → `character`, state → `dialogue`
12. **Fallback** → `action`

### Classification Order (in `dialogue` state)

1. **Parenthetical** (`(text)`) → `parenthetical`
2. **Everything else** → `dialogue`

---

## 5. Scene Boundaries

### What Creates a Scene Boundary

A scene boundary is created by:

1. **Scene heading** — any line matching `scene_heading` regex:
   - `INT. LOCATION - TIME`
   - `EXT. LOCATION - TIME`
   - `INT./EXT. LOCATION - TIME`
   - `EST. LOCATION`
   - `.FORCED SCENE HEADING` (dot prefix forces any line)
   - Optional scene number suffix: `#1#`, `#A#`, `#1A#`

2. **Section heading** — lines starting with `#` (1-6 levels):
   - `# Act 1` (level 1)
   - `## Sequence A` (level 2)
   - `### Scene Group` (level 3+)

3. **Page break** — `===` (3+ equals signs)

4. **Config: `each_scene_on_new_page`** — inserts a `page_break` before each scene heading (except the first)

### Scene Structure

Each scene is tracked in `result.properties.scenes[]`:

```javascript
{
    scene: "1",           // Scene number (string)
    text: "INT. CAFE - DAY", // Scene heading text
    line: 42,             // Line number
    actionLength: 0,      // Duration of action (seconds)
    dialogueLength: 0     // Duration of dialogue (seconds)
}
```

### Scene Numbering

- Auto-incremented starting from 1
- Can be overridden with `#number#` suffix in scene heading
- Supports standard numbering: `1`, `2`, `3`, ... or `A1`, `A2`, `B1`, etc.
- Scene numbering schema in `scenenumbering.js`

---

## 6. HTML Export — Token Wrapping

### 6.1 HTML Generation (`afterwriting-parser.js` lines 558-737)

When `generate_html` is `true`, the parser produces `result.scriptHtml` and `result.titleHtml`.

### 6.2 Token-to-HTML Mapping

| Token Type | HTML Wrapper | CSS Class |
|------------|--------------|-----------|
| `scene_heading` | `<h3>` | `haseditorline` + `data-scenenumber` + `data-position` |
| `transition` | `<h2>` | `haseditorline` |
| `dual_dialogue_begin` | `<div>` | `dual-dialogue` |
| `dialogue_begin` | `<div>` | `dialogue` (+ `left`/`right` if dual) |
| `character` | `<h4>` | `haseditorline` |
| `parenthetical` | `<p>` | `haseditorline parenthetical` |
| `dialogue` | `<p>` | `haseditorline` |
| `dialogue_end` | `</div>` | (closes dialogue div) |
| `dual_dialogue_end` | `</div></div>` | (closes both dialogue and dual-dialogue divs) |
| `section` | `<p>` | `haseditorline section` + `data-position` + `data-depth` |
| `synopsis` | `<p>` | `haseditorline synopsis` |
| `lyric` | `<p>` | `haseditorline lyric` |
| `note` | `<p>` | `haseditorline note` |
| `boneyard_begin` | `<!-- ` | (HTML comment start) |
| `boneyard_end` | ` -->` | (HTML comment end) |
| `page_break` | `<hr />` | (horizontal rule) |
| `action` | `<span>` | `haseditorline` (first in block gets `<p>` wrapper) |
| `centered` | `<span>` | `haseditorline centered` |

### 6.3 Action Block Wrapping

Action tokens are wrapped in `<p>` tags with special logic:
- First action token in a block: `<p><span class="haseditorline">text</span>`
- Subsequent action tokens: `<span class="haseditorline">text</span>`
- Centered tokens within action: no extra `<p>` needed
- Separator after action: closes `</p>` if next token is not action/separator/centered

### 6.4 Inline Text Processing (`lexer` function)

The `lexer()` function processes inline formatting:

```javascript
var htmlreplacements = {
    link: '<a href="$6">$3</a>',
    note: '<span class="note">$1</span>',
    line_break: '<br />',
    bold_italic_underline: '<span class="bold italic underline">$2</span>',
    bold_underline: '<span class="bold underline">$2</span>',
    italic_underline: '<span class="italic underline">$2</span>',
    bold_italic: '<span class="bold italic">$2</span>',
    bold: '<span class="bold">$2</span>',
    italic: '<span class="italic">$2</span>',
    underline: '<span class="underline">$2</span>',
};
```

Processing order:
1. Replace inline notes `[[text]]` → `<span class="note">text</span>`
2. Replace escaped `\*` → `[star]` and `\_` → `[underline]`
3. Replace newlines → `<br />`
4. Process emphasis styles in order: `underline`, `italic`, `bold`, `bold_italic`, `italic_underline`, `bold_underline`, `bold_italic_underline`
5. Restore `[star]` → `*` and `[underline]` → `_`
6. Trim (except for `action` type)

---

## 7. CSS Classes Reference

### 7.1 Token CSS Classes (from `preview.html` and `staticexport.html`)

```css
/* Scene headings */
.page h3 {
    font-weight: bold;
}
.numberonleft h3:before {
    opacity: 0.4;
    content: attr(data-scenenumber);
    font-weight: 700;
    left: -45px;
    position: absolute;
}
.numberonright h3:after {
    opacity: 0.4;
    content: attr(data-scenenumber);
    font-weight: 700;
    right: -45px;
    position: absolute;
}

/* Dialogue */
#workspace #script .page div.dialogue {
    margin-left: auto;
    margin-right: auto;
    width: 68%;
}
#workspace #script .page div.dialogue h4 {
    margin-bottom: 0;
    margin-left: 23%;
}
#workspace #script .page div.dialogue p.parenthetical {
    margin-bottom: 0;
    margin-top: 0;
    margin-left: 11%;
}
#workspace #script .page div.dialogue p {
    margin-bottom: 0;
    margin-top: 0;
}

/* Dual dialogue */
#workspace #script .page div.dual-dialogue {
    margin: 2em 0 .9em 2%;
    width: 95%;
}
#workspace #script .page div.dual-dialogue div.dialogue {
    display: inline-block;
    margin: 0;
    width: 45%;
}
#workspace #script .page div.dual-dialogue div.dialogue.right {
    float: right;
}

/* Centered */
#workspace #script .page span.centered {
    text-align: center;
    width: 92.5%;
    display: block;
}

/* Section */
#workspace #script .page p.section {
    opacity: 0.2;
    margin-left: -30px;
}

/* Synopsis */
#workspace #script .page p.synopsis {
    opacity: 0.4;
    font-style: italic;
    margin-left: -20px;
}

/* Inline formatting */
#workspace #script .page span.italic { font-style: italic; }
#workspace #script .page span.bold { font-weight: 700; }
.note { opacity: 0.5; font-style: italic; }
.underline { text-decoration: underline; }

/* Title page */
div#titlepage {
    display: grid;
    height: calc(100% - 200px);
    width: 100%;
    grid-template-columns: 1fr 1fr 1fr 1fr 1fr 1fr;
    grid-template-rows: 200px 1fr 300px;
}
.titlepagesection[data-position='tl'] { grid-column-start: 1; grid-column-end: 3; }
.titlepagesection[data-position='tc'] { grid-column-start: 3; grid-column-end: 5; text-align: center; }
.titlepagesection[data-position='tr'] { grid-column-start: 5; grid-column-end: 7; text-align: right; }
.titlepagesection[data-position='cc'] { grid-column-start: 1; grid-column-end: 7; text-align: center; align-self: center; }
.titlepagesection[data-position='bl'] { grid-column-start: 1; grid-column-end: 4; align-self: end; }
.titlepagesection[data-position='br'] { grid-column-start: 4; grid-column-end: 7; text-align: right; align-self: end; }

/* Page layout */
#workspace #script .page {
    border: 1px solid transparent;
    border-radius: 2px;
    cursor: text;
    letter-spacing: 0 !important;
    font-family: betterfountain-screenplayfont;
    line-height: 107.5%;
    margin-bottom: 25px;
    position: relative;
    text-align: left;
    width: 100%;
    z-index: 200;
    box-shadow: 0px 0px 28px 0px rgba(0,0,0,0.25);
    box-sizing: border-box;
}
#workspace #script.dpi100 .innerpage {
    max-width: 577px;
    margin-top: 100px;
    margin-bottom: 100px;
    margin-left: auto;
    margin-right: auto;
    padding-left: 42px;
    padding-right: 42px;
}
```

### 7.2 Page Dimensions (A4 @ 100 DPI)

```
Page width: 8.27in (827px)
Page height: 11.7in (1170px)
Font size: 16px
Line height: 107.5%
Lines per page: 57
Left margin: 1.5in
Right margin: 1in
Top margin: 1in
Bottom margin: 1in
```

### 7.3 Token Widths (A4)

| Token | Feed (indent) | Max Width |
|-------|---------------|-----------|
| `scene_heading` | 1.5in | 58 chars |
| `action` | 1.5in | 58 chars |
| `character` | 3.5in | 33 chars |
| `parenthetical` | 3.0in | 26 chars |
| `dialogue` | 2.5in | 36 chars |
| `transition` | 0.0in | 58 chars |
| `centered` | 1.5in | 58 chars |
| `synopsis` | 0.5in | 58 chars |
| `section` | 0.5in | 58 chars |

---

## 8. Title Page System

### 8.1 Title Page Keys

```javascript
exports.titlePageDisplay = {
    title: { position: 'cc', index: 0 },
    credit: { position: 'cc', index: 1 },
    author: { position: 'cc', index: 2 },
    authors: { position: 'cc', index: 3 },
    source: { position: 'cc', index: 4 },
    watermark: { position: 'hidden', index: -1 },
    font: { position: 'hidden', index: -1 },
    header: { position: 'hidden', index: -1 },
    footer: { position: 'hidden', index: -1 },
    notes: { position: 'bl', index: 0 },
    copyright: { position: 'bl', index: 1 },
    revision: { position: 'br', index: 0 },
    date: { position: 'br', index: 1 },
    draft_date: { position: 'br', index: 2 },
    contact: { position: 'br', index: 3 },
    contact_info: { position: 'br', index: 4 },
    br: { position: 'br', index: -1 },
    bl: { position: 'bl', index: -1 },
    tr: { position: 'tr', index: -1 },
    tc: { position: 'tc', index: -1 },
    tl: { position: 'tl', index: -1 },
    cc: { position: 'cc', index: -1 }
};
```

### 8.2 Title Page Positions

| Position | Grid Location |
|----------|---------------|
| `tl` | Top left (columns 1-2) |
| `tc` | Top center (columns 3-4) |
| `tr` | Top right (columns 5-6) |
| `cc` | Center (columns 1-7, centered vertically) |
| `bl` | Bottom left (columns 1-3) |
| `br` | Bottom right (columns 4-6) |
| `hidden` | Not displayed (used for config: font, watermark, header, footer) |

### 8.3 Title Page HTML Generation

```javascript
// Title page sections
for (const section of Object.keys(result.title_page)) {
    result.title_page[section].sort(sort_index);
    titlehtml.push(`<div class="titlepagesection" data-position="${section}">`);
    
    for (const current_token of result.title_page[section]) {
        switch (current_token.type) {
            case 'title':
                titlehtml.push(`<h1 class="haseditorline titlepagetoken" id="sourceline_${line}">${html}</h1>`);
                break;
            case 'header':
            case 'footer':
                // Stored for later use
                break;
            default:
                titlehtml.push(`<p class="${type} haseditorline titlepagetoken" id="sourceline_${line}">${html}</p>`);
        }
    }
    titlehtml.push('</div>');
}
```

---

## 9. Dual Dialogue

### 9.1 Syntax

```
CHARACTER 1
(dialogue)

CHARACTER 2 ^
(dialogue)
```

The `^` suffix on a character name indicates dual dialogue.

### 9.2 Token Flow

1. First `character` token → `dual: "left"`
2. Second `character` token with `^` → `dual: "right"`
3. Parser converts previous `dialogue_begin` → `dual_dialogue_begin`
4. All previous dialogue tokens get `dual: "left"`
5. New dialogue tokens get `dual: "right"`

### 9.3 HTML Output

```html
<div class="dual-dialogue">
    <div class="dialogue left">
        <h4>CHARACTER 1</h4>
        <p>Dialogue text</p>
    </div>
    <div class="dialogue right">
        <h4>CHARACTER 2</h4>
        <p>Dialogue text</p>
    </div>
</div>
```

---

## 10. Inline Comments (Boneyard)

### 10.1 Syntax

```
/* This is a comment
   that spans multiple lines */
```

### 10.2 Processing

- `/*` → `boneyard_begin` token → `<!-- ` in HTML
- `*/` → `boneyard_end` token → ` -->` in HTML
- Nested comments supported via `nested_comments` counter
- State set to `ignore` while inside comment block

---

## 11. Inline Notes

### 11.1 Syntax

```
This is text[[with an inline note]] continues here.
```

### 11.2 Processing

- Extracted during parsing via `processInlineNote()`
- Stored in `level.notes[]` for the current section/scene
- Replaced with `<span class="note">text</span>` in HTML
- If `cfg.print_notes` is false, notes are removed from token text
- Notes contribute to `irrelevantTextLength` for duration calculation

---

## 12. Configuration Options

From `configloader.js`:

| Option | Type | Description |
|--------|------|-------------|
| `embolden_scene_headers` | boolean | Bold scene headings in preview |
| `embolden_character_names` | boolean | Bold character names |
| `show_page_numbers` | boolean | Show page numbers |
| `split_dialogue` | boolean | Split dialogue across pages |
| `print_title_page` | boolean | Include title page |
| `print_profile` | string | "a4" or "usletter" |
| `double_space_between_scenes` | boolean | Extra blank line between scenes |
| `print_sections` | boolean | Show sections |
| `print_synopsis` | boolean | Show synopses |
| `print_actions` | boolean | Show action |
| `print_headers` | boolean | Show scene headings |
| `print_dialogues` | boolean | Show dialogue |
| `number_sections` | boolean | Number sections |
| `use_dual_dialogue` | boolean | Enable dual dialogue |
| `print_notes` | boolean | Show notes |
| `print_header` | string | Page header text |
| `print_footer` | string | Page footer text |
| `print_watermark` | string | Watermark text |
| `scenes_numbers` | string | "left", "right", "both", or "none" |
| `each_scene_on_new_page` | boolean | Page break before each scene |
| `merge_empty_lines` | boolean | Merge consecutive empty lines |
| `print_dialogue_numbers` | boolean | Show dialogue take numbers |
| `create_bookmarks` | boolean | Create PDF bookmarks |
| `invisible_section_bookmarks` | boolean | Invisible section bookmarks |
| `text_more` | string | "(MORE)" text |
| `text_contd` | string | "(CONT'D)" text |
| `text_scene_continued` | string | Scene continuation text |
| `scene_continuation_top` | boolean | Scene continuation at top |
| `scene_continuation_bottom` | boolean | Scene continuation at bottom |
| `synchronized_markup_and_preview` | boolean | Sync scroll between editor and preview |
| `preview_theme` | string | "paper", "vscode", or "dark" |
| `preview_texture` | boolean | Show paper texture |
| `parenthetical_newline_helper` | boolean | Auto-newline after parenthetical |

---

## 13. Statistics System

### 13.1 Character Statistics

```javascript
{
    name: string,
    color: string,          // Hex color based on name hash
    speakingParts: number,  // Number of dialogue blocks
    secondsSpoken: number,  // Total dialogue duration
    averageComplexity: number, // Readability grade level
    monologues: number,     // Dialogue > 30 seconds
    wordsSpoken: number     // Total word count
}
```

### 13.2 Location Statistics

```javascript
{
    name: string,
    color: string,
    scene_numbers: number[],
    scene_lines: number[],
    number_of_scenes: number,
    times_of_day: string[],
    interior_exterior: "int" | "ext" | "mixed" | "other"
}
```

### 13.3 Duration Calculation

**Dialogue duration** (`calculateDialogueDuration`):
- Base: `(text_length / 3) * 0.1945548` seconds
- Punctuation: `.!?:` + 0.75s, `,` + 0.3s

**Action duration**:
- `(text_length - notes_length) / 20` seconds

---

## 14. Code to Port — File by File

### 14.1 Core Parser (`afterwriting-parser.js`)

**Functions to port:**
- `lexer(s, type, replacer, titlepage)` — inline text processing
- `parse(original_script, cfg, generate_html)` — main parser
- `processInlineNote(text, linenumber)` — inline note extraction
- `processDialogueBlock(token)` — dialogue duration calculation
- `processActionBlock(token)` — action duration calculation
- `updatePreviousSceneLength()` — scene duration tracking
- `latestSectionOrScene(depth, condition)` — structure navigation

**Data structures to port:**
- `exports.regex` — all regex patterns
- `exports.titlePageDisplay` — title page layout
- `htmlreplacements` — inline formatting HTML templates
- `result` object structure — parse result

### 14.2 Token System (`token.js`)

**Functions to port:**
- `create_token(text, cursor, line, new_line_length, type)` — token factory

### 14.3 Helpers (`helpers.js`)

**Functions to port:**
- `trimCharacterExtension(character)` — remove parenthetical from character name
- `trimCharacterForceSymbol(character)` — remove `@` prefix
- `addForceSymbolToCharacter(characterName)` — add `@` if lowercase present
- `parseLocationInformation(scene_heading)` — parse scene heading components
- `calculateDialogueDuration(dialogue)` — estimate dialogue duration
- `isMonologue(seconds)` — check if dialogue is a monologue (>30s)
- `slugify(text)` — URL-friendly slug
- `wordToColor(word)` — generate color from word hash
- `secondsToString(seconds)` — format seconds as HH:MM:SS
- `secondsToMinutesString(seconds)` — format as MM:SS

### 14.4 Scene Numbering (`scenenumbering.js`)

**Functions to port:**
- `generateSceneNumbers(currentSceneNumbers, schema)` — generate scene numbers
- `makeSceneNumberingSchema(type)` — create numbering schema
- `StandardSceneNumberingSchema` class — standard numbering

### 14.5 Statistics (`statistics.js`)

**Functions to port:**
- `createCharacterStatistics(parsed)` — character stats
- `createLocationStatistics(parsed)` — location stats
- `createSceneStatistics(parsed)` — scene stats
- `createDurationStatistics(parsed)` — duration stats
- `getLengthChart(parsed)` — length over time chart data
- `locationtype(val)` — classify location type
- `locationtime(val)` — normalize time of day

### 14.6 HTML Generation (from `afterwriting-parser.js`)

**Code blocks to port:**
- Title page HTML generation (lines 564-596)
- Script HTML generation (lines 606-737)
- Action block wrapping logic (lines 616-647)
- Token-to-HTML switch statement (lines 648-718)

### 14.7 CSS (from `preview.html` and `staticexport.html`)

**CSS blocks to port:**
- Page layout (`.page`, `.innerpage`, `#script`)
- Dialogue layout (`div.dialogue`, `div.dual-dialogue`)
- Title page grid (`div#titlepage`, `.titlepagesection`)
- Token styling (`h2`, `h3`, `h4`, `p`, `span`)
- Inline formatting (`.bold`, `.italic`, `.underline`, `.note`)
- Scene number styling (`.numberonleft`, `.numberonright`)
- Section and synopsis styling
- Header/footer styling

---

## 15. Key Algorithms

### 15.1 Scene Heading Parsing

```javascript
const parseLocationInformation = (scene_heading) => {
    // scene_heading[1] = int/ext prefix
    // scene_heading[2] = location and time
    let splitLocationFromTime = scene_heading[2].match(/(.*)[-–—−](.*)/);
    return {
        name: splitLocationFromTime ? splitLocationFromTime[1].trim() : scene_heading[2].trim(),
        interior: scene_heading[1].indexOf('I') != -1,
        exterior: scene_heading[1].indexOf('EX') != -1 || scene_heading[1].indexOf('E.') != -1,
        time_of_day: splitLocationFromTime ? splitLocationFromTime[2].trim() : ""
    };
};
```

### 15.2 Character Name Extraction

```javascript
const trimCharacterExtension = (character) => 
    character.replace(/[ \t]*(\(.*\))[ \t]*([ \t]*\^)?$/, "");

const trimCharacterForceSymbol = (character) => 
    character.replace(/^[ \t]*@/, "");
```

### 15.3 Dialogue Duration Estimation

```javascript
const calculateDialogueDuration = (dialogue) => {
    var duration = 0;
    var sanitized = dialogue.replace(/[^\w]/gi, '');
    duration += ((sanitized.length) / 3) * 0.1945548;
    var punctuationMatches = dialogue.match(/(\.|\?|\!|\:) |(\, )/g);
    if (punctuationMatches) {
        if (punctuationMatches[0]) duration += 0.75 * punctuationMatches[0].length;
        if (punctuationMatches[1]) duration += 0.3 * punctuationMatches[1].length;
    }
    return duration;
};
```

### 15.4 Inline Note Processing

```javascript
const processInlineNote = (text, linenumber) => {
    let irrelevantTextLength = 0;
    if (match = text.match(new RegExp(exports.regex.note_inline))) {
        var level = latestSectionOrScene(current_depth + 1, () => true);
        if (level) {
            level.notes = level.notes || [];
            for (let i = 0; i < match.length; i++) {
                match[i] = match[i].slice(2, match[i].length - 2);
                level.notes.push({ note: match[i], line: thistoken.line });
                irrelevantTextLength += match[i].length + 4;
            }
        }
    }
    return irrelevantTextLength;
};
```

---

## 16. Data Flow Summary

```
Input: Fountain text string
        ↓
    Split into lines
        ↓
    For each line:
        1. Strip inline comments (/* */)
        2. Create token with create_token()
        3. Classify based on regex + state
        4. Update state (normal/dialogue/dual_dialogue)
        5. Track scene/section structure
        6. Calculate duration (action/dialogue)
        7. Extract inline notes
        ↓
    Post-processing:
        - Tidy separators
        - Generate HTML (if requested)
        - Calculate statistics
        ↓
    Output: {
        title_page: { tl, tc, tr, cc, bl, br, hidden },
        tokens: [...],
        scriptHtml: "...",
        titleHtml: "...",
        lengthAction: number,
        lengthDialogue: number,
        properties: {
            sceneLines: [],
            scenes: [],
            sceneNames: [],
            titleKeys: [],
            firstTokenLine: number,
            fontLine: number,
            characters: Map,
            locations: Map,
            structure: []
        }
    }
```

---

## 17. Key Observations for Porting

1. **Regex patterns are the foundation** — all classification depends on the regex definitions in `exports.regex`. These are the most critical piece to port accurately.

2. **State machine is simple** — only 5 states, with `normal` and `dialogue` being the primary ones.

3. **HTML generation is tightly coupled** — the parser generates HTML directly. For our app, we may want to separate parsing from rendering.

4. **Inline processing is separate** — the `lexer()` function handles all inline formatting (bold, italic, links, notes, etc.).

5. **Scene boundaries are explicit** — scene headings and section headings create clear boundaries. The parser tracks these in `result.properties.structure`.

6. **Dual dialogue is complex** — requires lookback and token type changes. Consider simplifying or deferring.

7. **Title page is a separate system** — parsed differently from the script, with its own layout grid.

8. **CSS is page-oriented** — designed for US Letter/A4 page layout. Our app may need different styling.

9. **Statistics are computed post-parse** — all statistics functions take the parsed result as input.

10. **Configuration drives behavior** — many features are configurable (dual dialogue, scene numbering, print options, etc.).

---

## 18. Code Blocks to Port — Checklist

### Critical (Parser Core)
- [ ] `exports.regex` — all regex patterns
- [ ] `create_token()` — token factory
- [ ] `parse()` — main parser function
- [ ] `lexer()` — inline text processing
- [ ] `processInlineNote()` — inline note extraction
- [ ] `processDialogueBlock()` — dialogue processing
- [ ] `processActionBlock()` — action processing
- [ ] `updatePreviousSceneLength()` — scene duration tracking
- [ ] `latestSectionOrScene()` — structure navigation

### Important (Token Helpers)
- [ ] `trimCharacterExtension()` — character name cleanup
- [ ] `trimCharacterForceSymbol()` — @ symbol removal
- [ ] `addForceSymbolToCharacter()` — @ symbol addition
- [ ] `parseLocationInformation()` — scene heading parsing
- [ ] `calculateDialogueDuration()` — dialogue timing
- [ ] `isMonologue()` — monologue detection
- [ ] `slugify()` — URL slug generation
- [ ] `wordToColor()` — color generation
- [ ] `secondsToString()` — time formatting
- [ ] `secondsToMinutesString()` — time formatting

### Useful (Statistics)
- [ ] `createCharacterStatistics()` — character stats
- [ ] `createLocationStatistics()` — location stats
- [ ] `createSceneStatistics()` — scene stats
- [ ] `createDurationStatistics()` — duration stats
- [ ] `getLengthChart()` — length chart data
- [ ] `locationtype()` — location classification
- [ ] `locationtime()` — time normalization

### Nice to Have (Scene Numbering)
- [ ] `generateSceneNumbers()` — scene number generation
- [ ] `makeSceneNumberingSchema()` — schema creation
- [ ] `StandardSceneNumberingSchema` class

### HTML/CSS
- [ ] Token-to-HTML mapping (switch statement)
- [ ] Action block wrapping logic
- [ ] Title page HTML generation
- [ ] CSS classes for all token types
- [ ] Page layout CSS
- [ ] Dialogue/dual-dialogue CSS
- [ ] Title page grid CSS

---

*End of research document.*
