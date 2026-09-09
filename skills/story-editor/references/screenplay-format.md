# Fountain Format Reference

> How to write and edit screenplays in Fountain format. The LLM must follow
> these conventions so the screenplay parses correctly and renders properly
> in the dashboard.

---

## The Golden Rule

**Make it look like a screenplay.** Fountain is plaintext that reads like a
script. Every line must follow the conventions below, or the parser will
misclassify it.

---

## Core Elements

### Scene Headings

```
INT. LOCATION - TIME OF DAY
EXT. LOCATION - TIME OF DAY
```

**Rules:**
- Must start with `INT.`, `EXT.`, `EST.`, `INT./EXT.`, or `I/E.`
- Followed by a space, then location, then ` - `, then time of day
- Must have a blank line before AND after
- Case insensitive (but UPPERCASE recommended for readability)
- Optional scene numbers: `INT. HOUSE - DAY #1A#`

**Examples:**
```
INT. MARA'S APARTMENT - NIGHT
EXT. THE INSTITUTE - DAY
INT./EXT. RONNA'S CAR - NIGHT [DRIVING]
EST. CITY - NIGHT
```

**Forced scene heading** (for locations that don't start with INT/EXT):
```
.SNIPER SCOPE POV
```
The leading `.` is removed in formatted output.

---

### Character Cues

```
                CHARACTER NAME
```

**Rules:**
- Must be ALL CAPS (at least one letter, no lowercase)
- Must have a blank line before
- No blank line after (dialogue follows immediately)
- Can be indented with tabs/spaces (not required)
- Extensions allowed: `(V.O.)`, `(O.S.)`, `(CONT'D)`, `(on the radio)`
- Must include at least one alphabetical character (`R2D2` works, `23` doesn't)

**Examples:**
```
                STEEL
                MARA (CONT'D)
                @McCLANE
```

**Forced character cue** (for names with lowercase):
```
                @McCLANE
```
The `@` is removed in formatted output.

**Dual dialogue** (two characters speaking simultaneously):
```
                BRICK
        Screw retirement.

                STEEL ^
        Screw retirement.
```
The `^` must be the last character on the line.

---

### Dialogue

```
                DIALOGUE TEXT
```

**Rules:**
- Follows a character cue or parenthetical
- Can have manual line breaks
- Can include empty lines within a dialogue block
- No blank line between character and dialogue

**Examples:**
```
                STEEL
        The man's a myth!

                SANBORN
        A good 'ole boy. You know, loves the Army, blood runs green.
        Country boy. Seems solid.
```

---

### Parentheticals

```
                (parenthetical direction)
```

**Rules:**
- Wrapped in `()`
- Follows a character cue or dialogue
- Indented in formatted output

**Examples:**
```
                STEEL
            (starting the engine)
        So much for retirement!

                STEEL
            (oh crap)
        Hello...
```

---

### Action / Description

```
Action text describes what happens.
```

**Rules:**
- Any paragraph that doesn't match other elements
- Can be multiple lines
- Tabs/spaces preserved (tabs = 4 spaces)
- Vertical whitespace preserved
- Can be forced with `!` to prevent misinterpretation

**Examples:**
```
They drink long and well from the beers.

And then there's a long beat.
Longer than is funny.
Long enough to be depressing.

The men look at each other.
```

**Forced action** (when text looks like a character cue):
```
                !SHOUTING
        Get out of here!
```

---

### Transitions

```
                CUT TO:
                FADE OUT.
                DISSOLVE TO:
```

**Rules:**
- Must be ALL CAPS
- Must end with `TO:`, `TO BLACK.`, or `OUT.`
- Must have blank line before AND after
- Can be forced with `>`

**Examples:**
```
                CUT TO:

                FADE OUT.

                >Burn to White.
```

---

## Advanced Elements

### Emphasis

```
*italics*
**bold**
***bold italics***
_underline_
```

**Rules:**
- Follows Markdown rules (except `_` = underline, not italic)
- Can combine: `***_bold italics_***`
- Escape with `\*` to prevent formatting
- Spaces around emphasis characters are meaningful

**Examples:**
```
_Steel's face FILLS the *Leupold Mark 4* scope_
He dialed *69 and then 23*, and then hung up.
Steel enters the code on the keypad: **\*9765\***
```

---

### Centered Text

```
> CENTERED TEXT <
```

**Rules:**
- Wrapped in `> <`
- Leading spaces not preserved

**Example:**
```
> THE END <
```

---

### Lyrics

```
~La la la, singing here~
```

**Rules:**
- Each line starts with `~`
- Always forced (no automatic detection)

---

### Notes

```
[[This is a note]]
```

**Rules:**
- Wrapped in `[[ ]]`
- Preserved but not displayed in formatted output

---

### Boneyards (Comments)

```
/* This is a comment */
```

**Rules:**
- Wrapped in `/* */`
- Removed from formatted output

---

### Sections

```
# Section heading
## Sub-section
```

**Rules:**
- Starts with `#` (up to 6 levels)
- Used for outline/structure

---

### Synopses

```
= Synopsis text
```

**Rules:**
- Starts with `=`
- Used for scene/section summaries

---

### Title Page

```
Title:    Script Title
Credit:   Written by
Author:   Author Name
Source:   Story by Someone
Contact:  contact@example.com
```

**Rules:**
- At the top of the file
- `key: value` format
- Keys: Title, Credit, Author, Authors, Source, Draft date, Date, Contact, Copyright, Notes, Revision

---

## Complete Example

```
Title:    _**BRICK & STEEL**_
          _**FULL RETIRED**_
Credit:   Written by
Author:   Stu Maschwitz
Source:   Story by KTM
Draft date: 1/20/2012

# Act I

= Set up the characters and the story.

INT. DAVE'S APARTMENT - DAY

Dave is standing in the open window looking out at the pouring rain.

                DAVE
            (cheerfully)
        Nice day for it!

                CUT TO:

EXT. BRICK'S POOL - DAY

Steel, in the middle of a heated phone call:

                STEEL
        They're coming out of the woodwork!
            (pause)
        No, everybody we've put away!
            (pause)
        Point Blank Sniper?

.SNIPER SCOPE POV

From what seems like only INCHES AWAY. _Steel's face FILLS the *Leupold Mark 4* scope_.

                STEEL
        The man's a myth!

Steel turns and looks straight into the cross-hairs.

                STEEL
            (oh crap)
        Hello...

                CUT TO:

.OPENING TITLES

> BRICK BRADDOCK <
& DICK STEEL IN <

> BRICK & STEEL <
FULL RETIRED <

SMASH CUT TO:

EXT. WOODEN SHACK - DAY

COGNITO, the criminal mastermind, is SLAMMED against the wall.

                COGNITO
        Woah woah woah, Brick and Steel!

                STEEL
        Who's coming after us?

COGNITO
Everyone's coming after you mate! Scorpio, The Boy Band, Sparrow, Point Blank Sniper...

                CUT TO:

INT. GARAGE - DAY

BRICK and STEEL get into Mom's PORSCHE, Steel at the wheel.

                BRICK
        This is everybody we've ever put away.

                STEEL
            (starting the engine)
        So much for retirement!

They speed off. To destiny!

                CUT TO:

EXT. PALATIAL MANSION - DAY

> BURN TO PINK.

> THE END <
```

---

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Character not ALL CAPS | `DAVE` not `Dave` |
| No blank line before character | Add blank line |
| No blank line before scene heading | Add blank line |
| Parenthetical not in `()` | `(pause)` not `pause` |
| Transition doesn't end with `TO:` | `CUT TO:` not `CUT` |
| Scene heading without INT/EXT | `INT. HOUSE - DAY` not `HOUSE - DAY` |
| Blank line between character and dialogue | Remove blank line |
| Lowercase in character name | Use `@` prefix or make ALL CAPS |

---

## Forced Elements Reference

| Prefix | Forces | Example |
|--------|--------|---------|
| `.` | Scene Heading | `.SOMEWHERE` |
| `@` | Character | `@McCLANE` |
| `!` | Action | `!SHOUTING` |
| `>` | Transition | `>Burn to White` |
| `~` | Lyric | `~Singing~` |

---

## When Writing New Screenplays

1. Start with Title Page (optional)
2. Use `#` for acts/sections
3. Write scenes with proper headings
4. Character cues: ALL CAPS, blank line before
5. Dialogue: no blank line after character
6. Parentheticals: wrapped in `()`
7. Action: full width paragraphs
8. Transitions: ALL CAPS, ending in `TO:`

## When Editing Existing Screenplays

1. Read the current screenplay first
2. Parse with `screenplay-tools` Parser to understand structure
3. Use `screenplay-tools` Writer for round-trip (preserves formatting)
4. Follow the same conventions as new writing
5. Validate with `fountain_validator.py` before saving
